# -*- coding: utf-8 -*-
"""
Author: Chen-Gang He
Creation Date: 2016-04-18
Purpose: To process data from Apache Kafka and apply data model built offline and send prediction back to Kafka
"""
from __future__ import print_function
import subprocess
import sys, uuid, random
import re

import time
from pyspark import SparkContext
from pyspark.streaming import StreamingContext
from pyspark.streaming.kafka import KafkaUtils
from pyspark.mllib.tree import RandomForest, RandomForestModel
from pyspark.mllib.regression import LabeledPoint
from pyspark.ml.feature import StringIndexer, VectorIndexer
from pyspark.sql import SQLContext, Row
from pyspark.sql import HiveContext
# from pyspark.sql import SparkSession

import json
import kafka
import rta_constants
import logging
import logging.config
import os
import ConfigParser
import pickle
from pandas import *
import pandas as pd
import uuid
from pyspark.sql.functions import col, lag, avg
from pyspark.sql.window import Window
from sklearn.naive_bayes import GaussianNB
from sklearn.cross_validation import cross_val_score

APP_PREFIX_NAME = "har_randomForest_"


# ==============================================================================
# Function
# ==============================================================================
def data_predict_input_rdd_factory(data_rdd, in_sensor_type):
    """Static factory where sensor data rdd will be transformed to make RDD as input of random forrest data model, and
    return rdd as input of data model.
    Args:
        data_rdd (rdd): rdd
        in_sensor_type (str): valid sensor type name. Possible valid value should be
         ["accelerometer", "gyroscope", "altimeter", "ambientLight", "barometer", "calorie", "distance","uv", "contact",
          "pedometer", "skinTemperature", "heartRate", "gsr", "rrinterval"]
    Returns:
        rdd
    """
    if in_sensor_type == "accelerometer":
        return data_rdd.map(lambda x: LabeledPoint(0, [float(x["x"]), float(x["y"]), float(x["z"])])) \
            .map(lambda x: x.features)
    elif in_sensor_type == "gyroscope":
        return data_rdd.map(lambda x: LabeledPoint(0, [float(x["x"]), float(x["y"]), float(x["z"])])) \
            .map(lambda x: x.features)
    elif in_sensor_type == "altimeter":
        return data_rdd.map(lambda x: LabeledPoint(0, [float(x["flightsAscended"]), float(x["flightsDescended"]),
                                                       float(x["rate"]), float(x["steppingGain"]),
                                                       float(x["steppingLoss"]), float(x["stepsAscended"]),
                                                       float(x["stepsDescended"]), float(x["totalGain"]),
                                                       float(x["totalLoss"])
                                                       ])).map(lambda x: x.features)
    elif in_sensor_type == "distance":
        return data_rdd.map(lambda x: LabeledPoint(0, [float(x["currentMotion"]), float(x["pace"]), float(x["speed"]),
                                                       float(x["totalDistance"])])) \
            .map(lambda x: x.features)
    else:
        return None


def send_partition(iter):
    """Send records in EACH partition to Kafka topci
    Args:
        iter (iterator):
    Returns:
        None
    """
    global result_topic, predict_result_broker_list
    # Connection object is created for EACH RDD PARTITION
    producer = kafka.KafkaProducer(bootstrap_servers=[predict_result_broker_list])
    send_counts = 0
    for record in iter:
        try:
            future = producer.send(result_topic, json.dumps(record))
        except Exception, e:
            print("Error: %s" % str(e))
        else:
            send_counts += 1
    producer.close()
    print("The count of prediction results which were sent IN THIS PARTITION is %d.\n" % send_counts)

def get_spark_session_instance(spark_context):
    if ('sqlContextSingletonInstance' not in globals()):
        globals()['sqlContextSingletonInstance'] = SQLContext(spark_context)
    return globals()['sqlContextSingletonInstance']

def get_spark_session_instance_hive(spark_context):
    if ('sqlContextSingletonInstance' not in globals()):
        globals()['sqlContextSingletonInstance'] = HiveContext(spark_context)
    return globals()['sqlContextSingletonInstance']


# def handle_ts(x):
#     return {"eventId":x["eventId"],"deviceType":x["deviceType"],"deviceid":x["deviceid"],\
#             "eventtype":x["eventtype"],"timestamp":x["timestamp"],"userid":x["userid"],\
#             "trainingMode":x["trainingMode"],\
#             "timestamp":int(x['timestamp'])/window_seconds}

def process_data_sk(rdd, user_data_model_dict,in_sensor_type,in_user_list,window_seconds):
    '''
    This is specific method for sklearn process data
    Args:
        data_rdd (rdd): rdd
        in_sensor_type (str): valid sensor type name. Possible valid value should be
         ["accelerometer", "gyroscope", "altimeter", "ambientLight", "barometer", "calorie", "distance","uv", "contact",
          "pedometer", "skinTemperature", "heartRate", "gsr", "rrinterval"]
    Returns:
        rdd
    '''
    if rdd.isEmpty():
        app_logger.debug("    NO data coming from Apache Kafka with %s:%s ...", " ".join(data_brokers),
                         " ".join(data_topics))
        return
    global data_brokers, data_topics, sensor_type_2_processed, process_start_time, app_name
    app_logger.debug("    %s" %(get_elapsed_time(process_start_time, time.time(), app_name)))
    # Filter out NULL records or without valid user ID which are in JSON format and have key named "userid"
    valid_data_message = rdd.filter(lambda x: x != "").map(lambda x: json.loads(x)) \
        .filter(lambda x: x["userid"] in in_user_list)
    # print (in_user_list)
    # print (valid_data_message.collect())
    # Skip the process if there is no sensor record with valid user ID.
    if valid_data_message.isEmpty():
        app_logger.debug("There is NO sensor record with valid user list %s in current RDD.",
                         in_user_list)
        return
    # # Get all users in RDD and filter out NULL records which are in JSON format and have key named "userid"
    # user_list = valid_data_message.map(lambda x: x["userid"]).distinct().collect()
    # handle sensor_type data
    if in_sensor_type == 'accelerometer':
        sqlContext = get_spark_session_instance(rdd.context)
        for user in in_user_list:
            allDataFrame = sqlContext.createDataFrame(valid_data_message)
            allDataFrame.registerTempTable("allData")
            handle_data = sqlContext.sql("SELECT deviceid,userid,rint(timestamp/"+str(window_seconds)+") as timestamp,x, y , z,eventtype from allData")
            handle_data.registerTempTable("hadle_data")
            filtered = sqlContext.sql("SELECT deviceid,userid, timestamp, x, y, z,eventtype FROM hadle_data WHERE eventtype LIKE 'accelerometer'")
            filtered.registerTempTable("filtered")
            remDup = filtered.dropDuplicates()
            remDup.registerTempTable("remDup")
            #**For streaming, don't group by activity as activity is not known.
            #sqlContext is HiveContext not SparkContext
            features = sqlContext.sql("SELECT deviceid,userid, timestamp,avg(x) as avg_acc_x,avg(y) as avg_acc_y,avg(z) as avg_acc_z, variance(x) as variance_acc_x,variance(y) as variance_acc_y,variance(z) as variance_acc_z, corr(x, y) as corr_xy, corr(x, z) as corr_xz, corr(y, z) as corr_yz, stddev(x) as std_acc_x, stddev(y) as std_acc_y, stddev(z) as std_acc_z FROM remDup GROUP BY deviceid,userid,timestamp ORDER BY deviceid,userid,timestamp")
            features.registerTempTable("features")
            #replace NA values with 0
            fillNa = features.na.fill(0.0)
            fillNa.registerTempTable("fillNa")
            #select features and label only
            featLabel = sqlContext.sql("SELECT deviceid,userid,timestamp, avg_acc_x, avg_acc_y, avg_acc_z, variance_acc_x, variance_acc_y, variance_acc_z, corr_xy, corr_xz, corr_yz, std_acc_x, std_acc_y, std_acc_z FROM fillNa")
            featLabel.registerTempTable("featLabel")
            df = featLabel.toPandas()
            feature_test = df[['avg_acc_x', 'avg_acc_y','avg_acc_z', 'variance_acc_x', 'variance_acc_y', 'variance_acc_z', 'corr_xy', 'corr_xz', 'corr_yz', 'std_acc_x', 'std_acc_y', 'std_acc_z']]
            app_logger.info('Starting to predict %s data....',in_sensor_type)
            user_predict_result = user_data_model_dict[user].predict(feature_test)
            df['result'] = user_predict_result
            df['processor_name'] = "har_randomforest_"+in_sensor_type
            df['eventId'] = [str(uuid.uuid4()) for i in range(len(user_predict_result))]
            df_new = pd.DataFrame(df,columns=['eventId','processor_name','timestamp','userid','result'])
            # rename df columns name
            df_new.colums = ['eventId','processor_name','time_stamp','userid','result']
            # covert pandas df as rdd
            rdd = sqlContext.createDataFrame(df_new).map(lambda x:{"eventId":x[0],"processor_name":x[1],"time_stamp":int(x[2])*window_seconds,"userid":x[3],"result":x[4]})
            rdd.foreachPartition(send_partition)
    elif in_sensor_type == 'gyroscope':
        sqlContext = get_spark_session_instance(rdd.context)
        for user in in_user_list:
            allDataFrame = sqlContext.createDataFrame(valid_data_message)
            allDataFrame.registerTempTable("allData")
            handle_data = sqlContext.sql("SELECT deviceid,userid,rint(timestamp/"+str(window_seconds)+") as timestamp,x, y , z,eventtype from allData")
            handle_data.registerTempTable("hadle_data")
            filtered = sqlContext.sql("SELECT deviceid,userid, timestamp, x, y, z,eventtype FROM hadle_data WHERE eventtype LIKE 'gyroscope'")
            filtered.registerTempTable("filtered")
            remDup = filtered.dropDuplicates()
            remDup.registerTempTable("remDup")
            #**For streaming, don't group by activity as activity is not known.
            #sqlContext is HiveContext not SparkContext
            features = sqlContext.sql("SELECT deviceid,userid, timestamp,avg(x) as avg_acc_x,avg(y) as avg_acc_y,avg(z) as avg_acc_z, variance(x) as variance_acc_x,variance(y) as variance_acc_y,variance(z) as variance_acc_z, corr(x, y) as corr_xy, corr(x, z) as corr_xz, corr(y, z) as corr_yz, stddev(x) as std_acc_x, stddev(y) as std_acc_y, stddev(z) as std_acc_z FROM remDup GROUP BY deviceid,userid,timestamp ORDER BY deviceid,userid,timestamp")
            features.registerTempTable("features")
            #replace NA values with 0
            fillNa = features.na.fill(0.0)
            fillNa.registerTempTable("fillNa")
            #select features and label only
            featLabel = sqlContext.sql("SELECT deviceid,userid,timestamp, avg_acc_x, avg_acc_y, avg_acc_z, variance_acc_x, variance_acc_y, variance_acc_z, corr_xy, corr_xz, corr_yz, std_acc_x, std_acc_y, std_acc_z FROM fillNa")
            featLabel.registerTempTable("featLabel")
            df = featLabel.toPandas()
            feature_test = df[['avg_acc_x', 'avg_acc_y','avg_acc_z', 'variance_acc_x', 'variance_acc_y', 'variance_acc_z', 'corr_xy', 'corr_xz', 'corr_yz', 'std_acc_x', 'std_acc_y', 'std_acc_z']]
            app_logger.info('Starting to predict %s data....',in_sensor_type)
            user_predict_result = user_data_model_dict[user].predict(feature_test)
            df['result'] = user_predict_result
            df['processor_name'] = "har_randomforest_"+in_sensor_type
            df['eventId'] = [str(uuid.uuid4()) for i in range(len(user_predict_result))]
            df_new = pd.DataFrame(df,columns=['eventId','processor_name','timestamp','userid','result'])
            # rename df columns name
            df_new.colums = ['eventId','processor_name','time_stamp','userid','result']
            # covert pandas df as rdd
            rdd = sqlContext.createDataFrame(df_new).map(lambda x:{"eventId":x[0],"processor_name":x[1],"time_stamp":int(x[2])*window_seconds,"userid":x[3],"result":x[4]})
            rdd.foreachPartition(send_partition)
    elif in_sensor_type == 'barometer':
        sqlContext = get_spark_session_instance_hive(rdd.context)
        for user in in_user_list:
            allDataFrame = sqlContext.createDataFrame(valid_data_message)
            allDataFrame.registerTempTable("allData")
            handle_data = sqlContext.sql("SELECT deviceid,userid, timestamp as devicets,rint(timestamp/"+str(window_seconds)+") as timestamp,airPressure as air_pres, temperature as air_temp,eventtype from allData")
            handle_data.registerTempTable("hadle_data")
            # app_logger.debug('handle data ########')
            # handle_data.show()
            filtered = sqlContext.sql("SELECT deviceid,userid, timestamp, devicets,air_pres, air_temp,eventtype FROM hadle_data WHERE eventtype LIKE 'barometer'")
            filtered.registerTempTable("filtered")
            # app_logger.debug('filtered table####')
            remDup = filtered.dropDuplicates()
            remDup.registerTempTable("remDup")
            
            #define group to carry out function in (no activity in streaming data)
            #userid,activity,featurename,windowtsseconds
            group = ["userid", "timestamp"]
            w = (Window().partitionBy(*group).orderBy("devicets"))
            v_diff = col("air_pres") - lag("air_pres", 1).over(w)
            t_diff = col("devicets") - lag("devicets", 1).over(w)
            slope = v_diff / t_diff
            addSlopeAP = remDup.withColumn("slopeAirPres", slope)
            #GET SLOPE OF AIR TEMPERATURE
            group = ["userid", "timestamp"]
            w = (Window().partitionBy(*group).orderBy("devicets"))
            v_diff = col("air_temp") - lag("air_temp", 1).over(w)
            t_diff = col("devicets") - lag("devicets", 1).over(w)
            slope = v_diff / t_diff
            slopes = addSlopeAP.withColumn("slopeAirTemp", slope)
            new = slopes.na.fill(0.0)
            new.registerTempTable("new")
            featLabel = sqlContext.sql("SELECT timestamp, userid, avg(slopeAirPres) as avg_slopeAirPres, avg(slopeAirTemp) as avg_slopeAirTemp FROM new GROUP BY timestamp,userid ORDER BY timestamp")
            featLabel.registerTempTable("featLabel")
            df = featLabel.toPandas()
            feature_test = df[['avg_slopeAirPres', 'avg_slopeAirTemp']]
            app_logger.info('Starting to predict %s data....',in_sensor_type)
            user_predict_result = user_data_model_dict[user].predict(feature_test)
            df['result'] = user_predict_result
            df['processor_name'] = "har_randomforest_"+in_sensor_type
            df['eventId'] = [str(uuid.uuid4()) for i in range(len(user_predict_result))]
            df_new = pd.DataFrame(df,columns=['eventId','processor_name','timestamp','userid','result'])
            # rename df columns name
            df_new.colums = ['eventId','processor_name','time_stamp','userid','result']
            # covert pandas df as rdd
            rdd = sqlContext.createDataFrame(df_new).map(lambda x:{"eventId":x[0],"processor_name":x[1],"time_stamp":int(x[2])*window_seconds,"userid":x[3],"result":x[4]})
            rdd.foreachPartition(send_partition)
    else:
        return None

def process_data(rdd, user_data_model_dict, user_list_broadcast):
    global data_brokers, data_topics, sensor_type_2_processed, process_start_time, app_name
    app_logger.debug("    %s" %(get_elapsed_time(process_start_time, time.time(), app_name)))
    if rdd.isEmpty():
        app_logger.debug("    NO data coming from Apache Kafka with %s:%s ...", " ".join(data_brokers),
                         " ".join(data_topics))
        return
    # Filter out NULL records or without valid user ID which are in JSON format and have key named "userid"
    valid_data_message = rdd.filter(lambda x: x != "").map(lambda x: json.loads(x)) \
        .filter(lambda x: x["userid"] in user_list_broadcast.value)

    # Skip the process if there is no sensor record with valid user ID.
    if valid_data_message.isEmpty():
        app_logger.debug("There is NO sensor record with valid user list %s in current RDD.",
                         user_list_broadcast.value)
        return

    # Get all users in RDD and filter out NULL records which are in JSON format and have key named "userid"
    user_list = valid_data_message.map(lambda x: x["userid"]).distinct().collect()

    # Loop each user in each RDD to apply corresponding data model built offline
    for user in user_list:
        # Identify messages for a given user ID
        user_data = valid_data_message.filter(lambda x: x["userid"] == user)
        # Get all features to predicts
        user_data_predict_input = data_predict_input_rdd_factory(user_data, sensor_type_2_processed)
        # Apply data model to corresponding users
        user_predict_result = user_data_model_dict[user].predict(user_data_predict_input)
        # Zip predict result with index number and prediction result
        user_predict_result_index = user_predict_result.zipWithIndex().map(lambda x: (x[1], x[0]))
        # print(user_predict_result_index.take(4))
        # Zip user's data with index number and its data
        user_data_index = user_data.zipWithIndex().map(lambda x: (x[1], x[0]))
        # Join user's data with prediction results
        user_data_predict = user_data_index.join(user_predict_result_index) \
            .map(lambda x: {"eventId": x[1][0]["eventId"], "processor_name": "har_randomforest_" + x[1][0]["eventtype"],
                            "time_stamp": x[1][0]["timestamp"], "userid": x[1][0]["userid"], "result": x[1][1]
                            })
        user_data_predict.cache()
        # print("User ID: %s, the count of records predicted in THIS RDD is %d" % (user, user_data_predict.count()))
        app_logger.info("    User ID: %s, the count of records predicted in THIS RDD is %d", user,
                        user_data_predict.count())
        app_logger.debug("    The first 4 prediction results: %s", user_data_predict.take(4))
        # Result is dumped back to Kafka
        user_data_predict.foreachPartition(send_partition)


def construct_logger(in_logger_file_path):
    """Instantiate and construct logger object based on log properties file by default. Otherwise logger object will be
    constructed with default properties.
    Args:
        in_logger_dir_path (str): path followed by file name where logger properties/configuration file resides
    Returns:
        logger object
    """
    if os.path.exists(in_logger_file_path):
        logging.config.fileConfig(in_logger_file_path)
        logger = logging.getLogger(os.path.basename(__file__))
    else:
        # If logger property/configuration file doesn't exist,
        # and logger object will be constructed with default properties.
        logger = logging.getLogger(os.path.basename(__file__))
        logger.setLevel(logging.DEBUG)
        # Create a new logger file
        logger_file_path_object = open(in_logger_file_path, 'a+')
        logger_file_path_object.close()
        # create a file handler
        handler = logging.FileHandler(in_logger_file_path)
        handler.setLevel(logging.INFO)
        # create a logging format
        formatter = logging.Formatter('[%(asctime)s - %(name)s - %(levelname)s] %(message)s')
        handler.setFormatter(formatter)
        # add the handlers to the logger
        logger.addHandler(handler)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        logger.warning("The logger configuration file %s doesn't exist, "
                       "so logger object will be constructed with default properties.", in_logger_file_path)
    return logger

def parse_user_data_model_for_sk(model_path,ls_data_model_str):
    """This is specific method for sklearn 
    Parse result of file system of model files, and return a tuple (set, dictionary)
    dictionary with (user_id, sensor_type): data_model_path
    a set of users
    Args:
        model_path (str): storing model file's path
        ls_data_model_str (str): result string from hadoop ls command
    Returns:
        tuple
    """
    in_user_sensor_type_2_data_model_path = {}
    in_user_id_set = set()
    for line in ls_data_model_str.split("\n"):
        data_model_path = model_path+'/'+line
        fields = line.split('_')
        if len(fields)==5:
            user_id = fields[2]
            in_user_id_set.add(user_id)
            sensor_type = fields[1]
            in_user_sensor_type_2_data_model_path[(user_id,sensor_type)] = data_model_path
    return (in_user_id_set, in_user_sensor_type_2_data_model_path)

def parse_user_data_model(ls_data_model_str):
    """Parse result of hadoop filesystem command, and return a tuple (set, dictionary)
    dictionary with (user_id, sensor_type): data_model_path
    a set of users
    Args:
        ls_data_model_str (str): result string from linux ls command
    Returns:
        tuple
    """
    in_user_sensor_type_2_data_model_path = {}
    in_user_id_set = set()
    for line in ls_data_model_str.split("\n"):
        fields = [field.strip() for field in line.split(" ") if field.strip() != ""]
        if len(fields) == 8:
            data_model_path = fields[-1]
            data_model_name = data_model_path.split("/")[-1]
            # print(data_model_name)
            user_id = model_extension_pattern_obj.sub("", data_model_name.split("_")[1])
            in_user_id_set.add(user_id)
            sensor_type = data_model_name.split("_")[0]
            # print(user_id, sensor_type)
            in_user_sensor_type_2_data_model_path[(user_id, sensor_type)] = data_model_path
            # print(in_user_sensor_type_2_data_model_path)
    return (in_user_id_set, in_user_sensor_type_2_data_model_path)


def get_elapsed_time(in_starttime_in_second, in_end_time_in_second, in_process_step_name):
    """Return elapsed time including hours, minutes and seconds.
    Args:
       in_starttime_in_second (int): elapsed time in seconds since UNIX epoch time
       in_end_time_in_second (int): elasped time in seconds since UNIX epoch time
       in_process_step_name (str): Nmae of process
    Return:
        rdd
    """
    duration_in_seconds = in_end_time_in_second - in_starttime_in_second
    out_second = int(duration_in_seconds) % 60
    minutes_amount = int(duration_in_seconds) // 60
    out_minute = minutes_amount % 60
    hours_amount = minutes_amount // 60
    return "    Total elapsed time of {} : {} Hours {} Minutes {} Seconds.\n".format(in_process_step_name, hours_amount
                                                                                     , out_minute, out_second)


if __name__ == "__main__":
    process_start_time = time.time()
    # Get all valid sensor type list
    valid_sensor_type_list = rta_constants.SENSORS_ACTIVITY_TYPE
    valid_sensor_type_list.extend(rta_constants.SENSORS_PHYSIO_TYPE)
    valid_predict_type = rta_constants.PREDICT_TYPE

    # Check if arguments are valid
    if len(sys.argv) != 3:
        print("Usage: rta_processor_simple.py <sensor type> <predict type>\nValid sensor type list: ",
              " ".join(valid_sensor_type_list), file=sys.stderr)
        print ('\nValid predict_type: '+' '.join(valid_predict_type))
        sys.exit(-1)
    elif sys.argv[1] not in valid_sensor_type_list or sys.argv[2] not in valid_predict_type:
        print("Usage: rta_processor_simple.py <sensor type> <predict type>\nValid sensor type list: ",
              " ".join(valid_sensor_type_list), file=sys.stderr)
        print ('\nValid predict_type: '+' '.join(valid_predict_type))
        sys.exit(-1)
    else:
        sensor_type_2_processed = sys.argv[1]
        predict_type = sys.argv[2]
        app_name = APP_PREFIX_NAME + sensor_type_2_processed

    # Construct logger object
    app_logger = construct_logger(rta_constants.PROPERTIES_LOG_FILE)
    # globals()['logger'] = construct_logger(rta_constants.PROPERTIES_LOG_FILE)
    app_logger.info("==> Start real-time analysis processor for sensor type %s...", sensor_type_2_processed)
    app_logger.debug("    Log file will be stored in %s", rta_constants.PROPERTIES_LOG_FILE)

    # Load necessary variables
    try:
        app_logger.info("==> Start loading necessary variables ...")
        config_parser = ConfigParser.ConfigParser()
        config_parser.read(rta_constants.PROPERTIES_FILE)
        predict_result_broker_list = config_parser.get(rta_constants.FRAMEWORK_NAME, "kafka.host_port")
        result_topic = config_parser.get(app_name, "kafka.data.out.topic")
        data_brokers = predict_result_broker_list
        data_topics_str = config_parser.get(app_name, "kafka.data.in.topics")
        data_topics = [topic for topic in data_topics_str.split(";") if topic != ""]
        streaming_batch_interval = int(config_parser.get(rta_constants.FRAMEWORK_NAME, "spark.batch_duration"))
        window_seconds = int(config_parser.get(rta_constants.SKLEARN,'window_seconds'))
    except Exception as ex:
        app_logger.error("    Failed to load Kafka properties with ERROR(%s).", str(ex))
        sys.exit(1)
    else:
        app_logger.debug("    predict_result_broker_list: %s", predict_result_broker_list)
        app_logger.debug("    predict_result_topic: %s", result_topic)
        app_logger.debug("    data_topics: %s", data_topics)
        app_logger.debug("    data_brokers: %s", data_brokers)
        app_logger.debug("    streaming_batch_interval: %d", streaming_batch_interval)
        app_logger.debug("    window seconds (Only for sklearn predict): %d", window_seconds)
        app_logger.info("    Finish loading necessary variables")

    try:
        # Construct Spark context
        app_logger.info("==> Construct Spark context with name: %s", app_name)
        sc = SparkContext(appName=app_name)
        ssc = StreamingContext(sc, streaming_batch_interval)

        if predict_type =='sklearn':
            PROJECT_FOLDER = config_parser.get(rta_constants.SKLEARN,'project_models_folder')
            # PROJECT_FOLDER = '/opt/mount1/rta-hc/integration/rta-hc-framework-master/data-models'
            if not(os.path.exists(PROJECT_FOLDER)):
                app_logger.error("    Data model home path(%s) DOES NOT exist.", PROJECT_FOLDER)
                sys.exit(-1)
            # cmd_1 = subprocess.Popen(["cd",PROJECT_FOLDER],shell=True,stdout=subprocess.PIPE)
            os.chdir(PROJECT_FOLDER)
            ls_data_model = subprocess.Popen(["ls"],shell=True,stdout=subprocess.PIPE)
            (ls_data_model_result,err) = ls_data_model.communicate()
            app_logger.debug('model path list is here**************')
            app_logger.debug(ls_data_model_result)
            user_id_set, user_sensor_type_2_data_model_path = parse_user_data_model_for_sk(PROJECT_FOLDER,ls_data_model_result)
            app_logger.info("    Data models in file system(%s) are available, and model name and its user ID are "
                                "parsed SUCCESSFULLY!", PROJECT_FOLDER)
            app_logger.debug('user_id_set is here############')
            app_logger.debug(user_id_set)
            app_logger.debug('sensor is here############')
            app_logger.debug(user_sensor_type_2_data_model_path)
            user_data_model_dict = dict()

        elif predict_type =='spark':
            # Check data models in HDFS
            app_logger.info("==> Check if data model folders exist in HDFS and get data model paths and valid user list")
            model_extension_pattern = ur'''(\.mdl)|(\.MDL)|(\.Mdl)'''
            model_extension_pattern_obj = re.compile(model_extension_pattern)
            # model_extension_pattern_obj.sub("", "accelerometer_vincent.planat@hpe.com_FEA_.MDL")
            ls_data_model = subprocess.Popen(["hadoop", "fs", "-ls", rta_constants.DATA_MODEL_HOME_PATH],
                                             stdout=subprocess.PIPE)
            (ls_data_model_result, err) = ls_data_model.communicate()
            if ls_data_model_result == "":
                app_logger.error("    Data model home path(%s) DOES NOT exist.", rta_constants.DATA_MODEL_HOME_PATH)
                sys.exit(-1)
            else:
                user_id_set, user_sensor_type_2_data_model_path = parse_user_data_model(ls_data_model_result)
                app_logger.info("    Data models in HDFS(%s) are available, and model name and its user ID are "
                                "parsed SUCCESSFULLY!", rta_constants.DATA_MODEL_HOME_PATH)

            # Get valid user list and broadcast across Spark worker
            app_logger.info("==> Get valid user list and broadcast acroos Spark workers ...")
            # user_list = sc.broadcast(["chen-gangh@hpe.com", "vincent.planat@hpe.com"])
            user_list = sc.broadcast(list(user_id_set))
            app_logger.debug("    valid user list: %s", user_list.value)

            # Load data models built offline in HDFS, and Build a dictionary which contains User id and its data model
            app_logger.info("==> Load data models built offline in HDFS "
                            "and build dictionary with user ID and its data model ...")
            user_data_model_dict = dict()

        # determine use which way to do load the model file
        if predict_type =='spark':
            for u in user_id_set:
                try:
                    dm = user_sensor_type_2_data_model_path[(u, sensor_type_2_processed)]
                except KeyError:
                    app_logger.warn("    There is NO data model in %s for user ID: %s and sensor type: %s !!",
                                    rta_constants.DATA_MODEL_HOME_PATH, u, sensor_type_2_processed)
                else:
                    data_model = RandomForestModel.load(sc, dm)
                    user_data_model_dict[u] = data_model
            if len(user_data_model_dict) == 0:
                app_logger.error("    There is NO data model in %s for user ID list: %s and sensor type: %s !! EXIT",
                                 rta_constants.DATA_MODEL_HOME_PATH, u, sensor_type_2_processed)
                sys.exit(-1)
        elif predict_type =='sklearn':
            for u in user_id_set:
                try:
                    dm = user_sensor_type_2_data_model_path[(u, sensor_type_2_processed)]
                except KeyError:
                    app_logger.warn("    There is NO data model in %s for user ID: %s and sensor type: %s !!",
                                    PROJECT_FOLDER, u, sensor_type_2_processed)
                else:
                    app_logger.debug('Dm is here###### %s',dm)
                    load_model = pickle.load(open(dm, 'rb'))
                    user_data_model_dict[u] = load_model

            app_logger.debug('User data model list are available: ')
            app_logger.debug(user_data_model_dict)
            if len(user_data_model_dict) == 0:
                app_logger.error("    There is NO data model in %s for user ID list: %s and sensor type: %s !! EXIT",
                                 PROJECT_FOLDER, u, sensor_type_2_processed)
                sys.exit(-1)

        # Use direct approach to receive messages from Apache Kafka
        app_logger.info("==> Use direct approach to receive messages from Apache Kafka ...")
        kvs = KafkaUtils.createDirectStream(ssc, data_topics, {"metadata.broker.list": data_brokers})
        # 2nd data element is message in each records when using direct approach with Kafka [None, message]
        lines = kvs.map(lambda x: x[1])
        # Apply all transformation and prediction logic
        app_logger.info("==> Start processing % sensor type data ...", sensor_type_2_processed)
        if predict_type =='spark':
            lines.foreachRDD(lambda rdd: process_data(rdd, user_data_model_dict, user_list))
        elif predict_type =='sklearn':
            app_logger.info('==> Start sklearn model processing %s sensor type data ...',sensor_type_2_processed)
            lines.foreachRDD(lambda rdd:process_data_sk(rdd, user_data_model_dict, sensor_type_2_processed,list(user_id_set),window_seconds))
        ssc.start()
        ssc.awaitTermination()
    except KeyboardInterrupt:
        app_logger.debug("    %s\n    %s" % ("Skip", get_elapsed_time(process_start_time, time.time(), app_name)))
    except Exception as e:
        process_end_time = time.time()
        app_logger.error("    %s\n    %s" %(e.message, get_elapsed_time(process_start_time, process_end_time, app_name)))
