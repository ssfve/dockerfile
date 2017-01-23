'''
Created on Mar 22, 2016

@author: planat
'''


from pyspark import SparkConf, SparkContext
from pyspark.streaming import StreamingContext
from pyspark.streaming.kafka import KafkaUtils
from kafka import KafkaProducer

from datetime import datetime


from ConfigParser import SafeConfigParser
import rta_constants
import logging.config
import sys
import json
import requests


"""
Status (25/03)
 - switched back to the CreateStream has the Direct stream is not working on new DEV (HortonWorks) kafka 6667
 - Working with KairosDB
 - Must look at the Cassandra DB size ...

bin/kafka-console-producer.sh --broker-list c4t19765.itcs.hpecorp.net:9092 --topic iot_msband2_accel
spark-submit --jars ../../spark-1.6.0-bin-hadoop2.6/lib/spark-streaming-kafka-assembly_2.10-1.6.0.jar kairosdb_writer.py
 
Module Constants definition
"""
VERSION_VAL = "0.5.0.5"
APP_NAME = "raw_writer"


logging.config.fileConfig(rta_constants.PROPERTIES_LOG_FILE)
logger = logging.getLogger(APP_NAME)

class kairosDbWriter:
    
    def __init__(self):
        self.datapoints = []
        self.nb_json_element = 0;

        logger.info("%s version: %s" % (APP_NAME,VERSION_VAL))
        # load properties from the rta.properties (use the APP_NAME as a section name)
        config_parser = SafeConfigParser()
        config_parser.read(rta_constants.PROPERTIES_FILE)
    
        # the same group name cannot be used by diff consumer as we need a pub/sub mechanism
        # kafka_group             = config_parser.get(rta_constants.FRAMEWORK_NAME, "kafka.group")
        self.kafka_host_consumer     = config_parser.get(rta_constants.FRAMEWORK_NAME, "zookeeper.host_port")
        self.kafka_host_producer     = config_parser.get(rta_constants.FRAMEWORK_NAME, "kafka.host_port")
        self.kafka_group             = APP_NAME        
        self.kafka_data_in_topics    = config_parser.get(APP_NAME, "kafka.data.in.topics").replace(" ","").strip(';')        
        self.spark_nb_threads        = config_parser.get(rta_constants.FRAMEWORK_NAME, "spark.nb_threads")
        self.spark_batch_duration    = config_parser.get(rta_constants.FRAMEWORK_NAME, "spark.batch_duration")
        self.kairosdb_url           = config_parser.get(rta_constants.FRAMEWORK_NAME, "kairosdb.url")
        self.post_size_max          = int(config_parser.get(rta_constants.FRAMEWORK_NAME, "kairosdb.post.size"))

        # kafka client producer (for sending back data result - not control). Used in process_data()
        self.data_producer = KafkaProducer(bootstrap_servers=self.kafka_host_producer)
        
        
        # initialize the spark Context
        logger.debug("initializing Processor spark context");
        conf = SparkConf().setAppName(APP_NAME)
        # On yar cluster the deploy mode is directly given by the spark-submit command. 
        #    spark-submit --master yarn --deploy-mode cluster
        # conf = conf.setMaster("local[*]")
        sc   = SparkContext(conf=conf)
        
        '''
        kafka Stream configuration for data input
            connect to the kafka topics (ctrl and data)
            Split topics into a dict e.g. {'topic1': 1, 'topic2': 1}
            add the control topic
        '''
        logger.debug("initializing kafka stream context for sensors data");
        kairosDbWriter.g_ssc = StreamingContext(sc, int(self.spark_batch_duration))        
        kafka_in_topics = dict(zip(self.kafka_data_in_topics.split(";"), [1]*len(self.kafka_data_in_topics.split(";"))))
        kafka_stream = KafkaUtils.createStream(kairosDbWriter.g_ssc, self.kafka_host_consumer, self.kafka_group, kafka_in_topics).map(lambda x: x[1])
        kafka_stream.foreachRDD(lambda rdd: self.process_data(rdd))
        logger.debug("Version:%s kafka consuler host:%s  group:%s topics:%s" % (VERSION_VAL,self.kafka_host_consumer,self.kafka_group,kafka_in_topics));
        logger.debug("limit the execution to physiological dataset")

        
        # start the kafka stream. Both ctrl and data are sequenced at the same rythm
        kairosDbWriter.g_ssc.start()
        kairosDbWriter.g_ssc.awaitTermination()



    def process_data(self,val_rdd):
        '''
            [{"name":"accelerometer-x","timestamp":1458632210606,"value":"0.991211","tags":{"deviceid":"b81e905908354542","userid":"vincent.planat@hpe.com"}},{"name":"accelerometer-y","timestamp":1458632210606,"value":"-0.027588","tags":{"deviceid":"b81e905908354542","userid":"vincent.planat@hpe.com"}},{"name":"accelerometer-z","timestamp":1458632210606,"value":"0.015625","tags":{"deviceid":"b81e905908354542","userid":"vincent.planat@hpe.com"}}] 
            {"eventId":"7e4b654e-3672-4f20-a35b-b49db451f3d3","deviceType":"msband2","deviceid":"b81e905908354542","eventtype":"accelerometer","timestamp":1458792660000,"userid":"vincent.planat@hpe.com","trainingMode":"SITTING","x":-1.006104,"y":-0.01416,"z":0.043213}
            '''
        if (val_rdd.isEmpty()):
            logger.debug("empty val rdd")
            return
                
        data_payload = val_rdd.collect()
        logger.debug( "collect size %d" % len(data_payload))
        
        for value in data_payload:
            # check if the rdd is for the controler or not.
            try:
                val_msg_json = json.loads(value)
            except ValueError:
                logger.debug("val rdd is not valid JSON:%s" % value)
                return
        
            #logger.debug("json in:%s"%val_msg_json)        
        
            # I accumulate a numb of data before sending the POST to KairosDB
            # This avoid stressing too much the KairosDB Rest interface. post_size_max is customizable
            # if I'm < post_size_max I accumulate            
            self.nb_json_element = self.nb_json_element + 1
            if (self.nb_json_element <= self.post_size_max):
                self.update_datapoints(val_msg_json)
            
            # it's time to push the content to kairosDb
            else:
                headers = {'content-type': 'application/json'}
                json_datapoints = json.dumps(self.datapoints)
                #logger.debug(json_datapoints);   
                resp = requests.post(self.kairosdb_url, data=json_datapoints,headers=headers)
                if resp.status_code != 204:
                    logger.error('POST /tasks/ {}'.format(resp.status_code)) 
                logger.debug("datapoints posted to kairosDb %s" % resp.status_code);
                # cleanup buffer & restart from the latest one
                self.datapoints = []                  
                self.nb_json_element = 1
                self.update_datapoints(val_msg_json)


    def get_ms_timestamp(self):
        delta = datetime.now() - datetime(1970, 1, 1)
        return(delta.total_seconds() * 1000)


    def update_datapoints(self, json_msg):
        metric_name = json_msg['eventtype']
        # accelerometer


        if metric_name ==  "accelerometer":
            kairos_row = {"name":"raw_"+metric_name+"_x","timestamp":int( self.get_ms_timestamp()),"value":json_msg['x'],"tags":{"deviceid":json_msg['deviceid'],"userid":json_msg['userid']}}
            self.datapoints.append(kairos_row)
            kairos_row = {"name":"raw_"+metric_name+"_y","timestamp":json_msg['timestamp'],"value":json_msg['y'],"tags":{"deviceid":json_msg['deviceid'],"userid":json_msg['userid']}}
            self.datapoints.append(kairos_row)
            kairos_row = {"name":"raw_"+metric_name+"_z","timestamp":json_msg['timestamp'],"value":json_msg['z'],"tags":{"deviceid":json_msg['deviceid'],"userid":json_msg['userid']}}
            self.datapoints.append(kairos_row)
        # altimeter
 
        # ambientLight
        
        # barometer
        
        # calorie
        
        # contact
        
        # distance
        
        
        # gyroscope
        # {"eventId":"1303fcc0-9949-4b25-ba83-07f74bbf80df","deviceType":"msband2","deviceid":"b81e905908354542","eventtype":"gyroscope","timestamp":1458815256889,"userid":"vincent.planat@hpe.com","trainingMode":"NONE","x":33.079269,"y":-28.993902,"z":16.158537}
        elif metric_name ==  "gyroscope":
            kairos_row = {"name":"raw_"+metric_name+"_x","timestamp":json_msg['timestamp'],"value":json_msg['x'],"tags":{"deviceid":json_msg['deviceid'],"userid":json_msg['userid']}}
            self.datapoints.append(kairos_row)
            kairos_row = {"name":"raw_"+metric_name+"_y","timestamp":json_msg['timestamp'],"value":json_msg['y'],"tags":{"deviceid":json_msg['deviceid'],"userid":json_msg['userid']}}
            self.datapoints.append(kairos_row)
            kairos_row = {"name":"raw_"+metric_name+"_z","timestamp":json_msg['timestamp'],"value":json_msg['z'],"tags":{"deviceid":json_msg['deviceid'],"userid":json_msg['userid']}}
            self.datapoints.append(kairos_row)
        
        # hdhld
        
        # gsr
        elif metric_name ==  "gsr":
        # {"eventId":"e690960a-aa21-45b2-88bf-7a86544fe184","deviceType":"msband2","deviceid":"b81e905908354542","eventtype":"gsr","timestamp":1457003461894,"userid":"vincent.planat@hpe.com","trainingMode":"SITTING","resistance":6488}
            kairos_row = {"name":"raw_"+metric_name+"_resistance","timestamp":json_msg['timestamp'],"value":json_msg['resistance'],"tags":{"deviceid":json_msg['deviceid'],"userid":json_msg['userid']}}
            self.datapoints.append(kairos_row)

        # heartRate
        elif metric_name ==  "heartRate":
        # {"eventId":"2bb7da45-18ed-4453-a00d-3ebafc88b985","deviceType":"msband2","deviceid":"b81e905908354542","eventtype":"heartRate","timestamp":1457003507802,"userid":"vincent.planat@hpe.com","trainingMode":"SITTING","rate":"69","quality":1}
            #kairos_row = {"name":"vpl_"+metric_name+"-rate","timestamp":json_msg['timestamp'],"value":json_msg['rate'],"tags":{"deviceid":json_msg['deviceid'],"userid":json_msg['userid']}}
            kairos_row = {"name":"raw_"+metric_name+"_rate","timestamp":int( self.get_ms_timestamp()),"value":json_msg['rate'],"tags":{"deviceid":json_msg['deviceid'],"userid":json_msg['userid']}}
            self.datapoints.append(kairos_row)
            kairos_row = {"name":"raw_"+metric_name+"_quality","timestamp":json_msg['timestamp'],"value":json_msg['quality'],"tags":{"deviceid":json_msg['deviceid'],"userid":json_msg['userid']}}
            self.datapoints.append(kairos_row)
        
        # rrinterval
        elif metric_name ==  "rrinterval":
            rrIntervalMetric = "raw_rrInterval_interval"
        # {"eventId":"e087c4c7-d230-405f-b8f2-a18bd276d910","deviceType":"msband2","deviceid":"b81e905908354542","eventtype":"rrinterval","timestamp":1457003501853,"userid":"vincent.planat@hpe.com","trainingMode":"SITTING","interval":1.061888}
            kairos_row = {"name":rrIntervalMetric,"timestamp":json_msg['timestamp'],"value":json_msg['interval'],"tags":{"deviceid":json_msg['deviceid'],"userid":json_msg['userid']}}
            self.datapoints.append(kairos_row)

        # pedometer
        
        # skinTemperature
        elif metric_name ==  "skinTemperature":
        # {"eventId":"86101df8-d6c5-4c3c-b12f-11066090f802","deviceType":"msband2","deviceid":"b81e905908354542","eventtype":"skinTemperature","timestamp":1457003464715,"userid":"vincent.planat@hpe.com","trainingMode":"SITTING","temperature":30.879999}
            kairos_row = {"name":"raw_"+metric_name+"_temperature","timestamp":json_msg['timestamp'],"value":json_msg['temperature'],"tags":{"deviceid":json_msg['deviceid'],"userid":json_msg['userid']}}
            self.datapoints.append(kairos_row)

        # uv
        
        else:
            pass
                

if __name__ == "__main__":


    myProcessor = kairosDbWriter()

         