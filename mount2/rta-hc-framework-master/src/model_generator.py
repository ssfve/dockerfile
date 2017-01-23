'''
Created on Mar 31, 2016

@author: sy

31-Mar  SY  Extraction from Cong's code as initial skeleton.
31-Mar  SY  1st Creation of model generator.
            Implemented save models function.
04-Apr  SY  Implemented logging capability
            Adding logging information.
            Changing implementation to suite design, taking in activity_type, saving each model at once.
05-Apr  SY  Adding filter to match user_id with input data.
08-Apr  SY  Implemented additional flag for ensemble prediction model training module.
            Flag called <model_type> containing value: feature | aggregation
03-Aug  Sakina Add one parameter to decide which way data model would be trained and stored
16-Spet Vpl update to support the new "sklearn" paramter to integrate Grainne's code
'''

## Imports

# Need to transfer the data to LabeledPoint format
from pyspark.mllib.regression import LabeledPoint
from pyspark import SparkConf, SparkContext , HiveContext
from pyspark.mllib.tree import RandomForest
from pyspark.sql import SQLContext , Row, functions ,Window , HiveContext
from pyspark.sql.window import Window
from pyspark.sql.functions import col, lag, avg
from ConfigParser import SafeConfigParser
from pyspark.ml.feature import StringIndexer, VectorIndexer
from sklearn.ensemble import RandomForestClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.cross_validation import cross_val_score
from sklearn import preprocessing
from sklearn.preprocessing import OneHotEncoder
from sklearn.naive_bayes import MultinomialNB


from pandas import *

#from pandas import *

# Import unicodedata for transferring unicode to string
import unicodedata
import sys
import os
import json
import uuid
import random
import logging
import logging.config
import rta_constants
import numpy as np
import pickle

## Module Constants
## 03-Aug Sakina : to modify the mode path , Add two variables for train model
APP_NAME = "Model_Generator"
FRAMEWORK_NAME = "framework"
VERSION_VAL = "0.31"
MODEL_EXT = ".MDL"
MODEL_EXT_FEATURE = "FEA"
MODEL_EXT_AGGREGATION = "AGR"
MODEL_TYPE_FEATURE = "feature"
MODEL_TYPE_AGGREGATION = "aggregator"
TRAIN_MODEL_SKLEARN='sklearn'
TRAIN_MODEL_SPARK='spark'
MODEL_SKLEARN_NAME_PRX='sk'

logging.config.fileConfig(rta_constants.PROPERTIES_LOG_FILE)
logger = logging.getLogger(APP_NAME)
config_parser = SafeConfigParser()
config_parser.read(rta_constants.PROPERTIES_FILE)
lst_sensor_act_type = rta_constants.SENSORS_ACTIVITY_TYPE
# this is used for spark for hdfs
MODEL_PATH = "/tmp/models"
# this is used for sklearn on local
PROJECT_FOLDER = config_parser.get(rta_constants.SKLEARN,'project_models_folder')

logger.debug("%s : Get started ...", APP_NAME)
conf = SparkConf().setAppName(APP_NAME)
#conf = SparkConf().setMaster("local").setAppName(APP_NAME)
sc = SparkContext(conf=conf)
sqlContext = SQLContext(sc)
field_delimiter = ','
windowSeconds=int(config_parser.get(rta_constants.SKLEARN,'window_seconds'))*1000

## Main module.
def process_model_spark(mt, a_s, ds, mid):
    # mt  : Model type
    # a_s : Activity sensor type
    # ds  : HDFS path to data soruce
    # mid : Model id
    
    print "Configured model type : %s" % mt
    logger.debug("%s : Configured model type : %s", APP_NAME, mt)

    print "Start to model generator (Ver : %s)...\nActivity Sensor : %s\nSOURCE : %s\nID : %s" % (VERSION_VAL, a_s, ds, mid)
    logger.debug("%s : Start to model generator (Ver : %s), Activity Sensor: %s, SOURCE : %s, ID : %s ...", APP_NAME, VERSION_VAL, a_s, ds, mid)

    # Load data which is stored in ds in Hadoop, using comma as delimiter and 
    # eliminate records whose trainingmode/label is NONE
    #
    # The column order should be 
    # [1]   ACTIVITY_TRAIN          TIME_STAMP_MS           USER_ID             
    # [4]   ACCEL_X                 ACCEL_Y                 ACCEL_Z         
    # [7]   AMBLGT_BRIGHTNESS       BRM_AIRPRESSURE         BRM_TEMPERATURE     
    # [10]  GYRO_X                  GYRO_Y                  GYRO_Z   
    # [13]  CAL_CALORIES            DST_CURR_MOTION         DST_PACE            
    # [16]  DST_SPEED               DST_TOTAL_DISTANCE      ALT_FLIGHTS_ASCENDED  
    # [19]  ALT_FLIGHTS_DESCENDED   ALT_RATE                ALT_STEPPING_GAIN   
    # [22]  ALT_STEPPING_GAIN_LOSS  ALT_STEPPING_ASCENDED   ALT_STEPPING_DESCENDED
    # [25]  ALT_STEPPING_DESCENDED  ALT_TOTAL_LOSS
    
    # test_source = "/tmp/raw_msband_current/version1/rawmsband_24032016.csv"
    
    data = sc.textFile(ds) \
            .map(lambda line: line.split(",")) \
            .filter(lambda line: len(line)>1 and unicodedata.normalize('NFKD',line[2]).encode('ascii', 'ignore')[1:-1] != "NONE") \
                    .filter(lambda line: line[5] == mid) \
                    .map(lambda line: [line[2],line[4], line[5], line[11], line[12], line[13], line[14],line[15], line[16], line[18], \
                                line[19], line[20], line[25], line[27], line[28],line[29], line[30], line[31],line[32], line[33], \
                                line[34], line[35], line[36], line[37],line[38], line[39]]) \
                                .collect()

    print "Reading in data source completed."
    logger.debug("%s : Reading in data source completed.", APP_NAME)

    print "Validating data with input user_id : %s completed." % mid
    logger.debug("%s : Validating data with input user_id : %s completed.", APP_NAME, mid)

    print "Start training model process ..."
    logger.debug("%s : Start training model process ...", APP_NAME)
    # logger.debug("%s : Start training model process using %s obs ...", APP_NAME, str(data.count()))

    # Remove data columns which is having 0 in sum. (Sum of features == 0)
    k_remove = []
    k = 0
    for value in data:
        i = 0
        sum_val = 0.0
        for val in value:
            i = i + 1
            if i>3:
                val=float(val)
                sum_val = sum_val + val
        if sum_val == 0.0:
            k_remove.append(k)
        k = k + 1
    m = 0
    for j in k_remove:
        data.remove(data[j-m])
        m = m + 1

    print "Complete cleaning up source data ..."
    logger.debug("%s : Complete cleaning up source data ...", APP_NAME)
    
    # Create a dictionary for dealing with different users
    data_rdd_id = {}
    # Set the user id as the key of the data_rdd_id dictionary
    for file_csv in data:
        value_key = unicodedata.normalize('NFKD',file_csv[2]).encode('ascii', 'ignore')[1:-1]
        if value_key in data_rdd_id.keys():
            data_rdd_id[value_key].append(file_csv)
        else:
            data_rdd_id[value_key] = [file_csv]
    
    # Store all the keys/userid in a list
    data_rdd_key = []
    for key in data_rdd_id.keys():
        data_rdd_key.append(key)

    # Since currently, only have one userid which is Vincent's email
    # user_id =  "vincent.planat@hpe.com"
    user_id =  mid[1:-1]

    # Transfer SITTING, WALKING, WALKING_UP, WALKING_DOWN to 0, 1, 2, 3 to fit the 
    # random forest parameter requirements  
    for row in data_rdd_id[user_id]:
        value_key = unicodedata.normalize('NFKD',row[0]).encode('ascii', 'ignore')[1:-1]        
        if value_key == rta_constants.RTA_ACTIVITY_SITTING:            
            row[0] = 0        
        if value_key == rta_constants.RTA_ACTIVITY_WALKING:
            row[0] = 1        
        if value_key == rta_constants.RTA_ACTIVITY_WALKING_UP:
            row[0] = 2
        if value_key == rta_constants.RTA_ACTIVITY_WALKING_DOWN:
            row[0] = 3
    
    # Covert the list format to RDD
    data_rdd_user = sc.parallelize(data_rdd_id[user_id])

    # Split the data into training and test sets (25% held out for testing)
    # We can use 100% for this training model if want.
    (trainingData, testData) = data_rdd_user.randomSplit([0.75, 0.25])

    # Since the dataset is imbalanced, below few lines is doing oversampling of walking_up and walking_down instances
    traindata = trainingData.collect()

    # Create walking_up and walking_down list to store the index of these two activties in the whole training dataset
    wu = []
    wd = []
    wu_index = 0
    wd_index = 0
    # Use to get the count of walking and sitting instances respectively 
    w_count = 0
    s_count = 0     
    for row in traindata:
        #value_key = unicodedata.normalize('NFKD',row[0]).encode('ascii', 'ignore')[1:-1]
        value_key = row[0]
        if value_key == 0:
            s_count = s_count + 1
        if value_key == 1:
            w_count = w_count + 1
        if value_key == 2:
            wu.append(wu_index)
        if value_key == 3:
            wd.append(wd_index)
        wu_index = wu_index + 1
        wd_index = wd_index + 1
    # Get the average of walking and sitting records 
    limit = round((w_count + s_count)/2)
    wu_count = len(wu)
    wd_count = len(wd)
    # Get the number of records which needs to be oversampled for walking_up and walking_down respectively  
    wu_diff = limit - wu_count
    wd_diff = limit - wd_count
    # Randomly select walking_down and walking_up records from the existing datasets and append them to the whole dataset to make the entire dataset more balanced
    while wu_diff > 0:
        traindata.append(traindata[random.choice(wu)])
        wu_diff = wu_diff - 1
    while wd_diff > 0:
        traindata.append(traindata[random.choice(wd)])
        wd_diff = wd_diff - 1
    # Convert list back to RDD
    trainingData = sc.parallelize(traindata)
    # Create a SQLcontext so that it is able to be transfer to pandas dataframe    
    
    sqlContext = SQLContext(sc)
    testData = sqlContext.createDataFrame(testData.collect())
    testData = testData.toPandas()
    col_names = testData.columns
    # Replace the 0 values with None
    for n, row in testData.iterrows():
        i = 0
        for val in col_names:
            i = i + 1
            if i > 3:
                value_t = float(testData.ix[n, val])
                if value_t == 0.0:
                    testData.set_value(n, val, np.nan)
    
    print "Preparing training data set ..."
    logger.debug("%s : Preparing training data set  ...", APP_NAME)
    
    # Fill the NONE with last non-NONE values
    testData = testData.sort_index(ascending=True)
    testData = testData.fillna(method='pad')
    # Drop the records who still have NONE
    testData = testData.dropna(axis=0, how='any')
    # Convert the dataset back to RDD
    testData = sqlContext.createDataFrame(testData)
    testData = testData.rdd

    # Create accelerometer training dataset, ACCEL_X    ACCEL_Y    ACCEL_Z
    accel_rdd_LP_total = trainingData.filter(lambda x : (float(x[3])+float(x[4])+float(x[5]))!=0.0).map(lambda x : LabeledPoint(x[0], [x[3], x[4], x[5]])).collect() 
    accel_rdd_LP_total = sc.parallelize(accel_rdd_LP_total)
    # Create gyroscope training dataset, GYRO_X    GYRO_Y    GYRO_Z
    gyro_rdd_LP_total = trainingData.filter(lambda x : (float(x[9])+float(x[10])+float(x[11]))!=0.0).map(lambda x : LabeledPoint(x[0], [x[9], x[10], x[11]])).collect()   
    gyro_rdd_LP_total = sc.parallelize(gyro_rdd_LP_total)
    # Create altimeter training dataset, ALT_FLIGHTS_ASCENDED    ALT_FLIGHTS_DESCENDED    ALT_RATE    ALT_STEPPING_GAIN    ALT_STEPPING_GAIN_LOSS    ALT_STEPPING_ASCENDED    ALT_STEPPING_DESCENDED    ALT_STEPPING_DESCENDED    ALT_TOTAL_LOSS
    alti_rdd_LP_total = trainingData.filter(lambda x : (float(x[17])+float(x[18])+float(x[19])+float(x[20])+float(x[21])+float(x[22])+float(x[23])+float(x[24])+float(x[25]))!=0.0).map(lambda x : LabeledPoint(x[0], [x[17], x[18], x[19], x[20], x[21], x[22], x[23], x[24], x[25]])).collect()   
    alti_rdd_LP_total = sc.parallelize(alti_rdd_LP_total)
    # Create ablight training dataset, AMBLGT_BRIGHTNESS
    ablight_rdd_LP_total = trainingData.filter(lambda x : (float(x[6]))!=0.0).map(lambda x : LabeledPoint(x[0], [x[6]])).collect()   
    ablight_rdd_LP_total = sc.parallelize(ablight_rdd_LP_total)
    # Create brm training dataset, BRM_AIRPRESSURE    BRM_TEMPERATURE
    brm_rdd_LP_total = trainingData.filter(lambda x : (float(x[7])+float(x[8]))!=0.0).map(lambda x : LabeledPoint(x[0], [x[7], x[8]])).collect()   
    brm_rdd_LP_total = sc.parallelize(brm_rdd_LP_total)
    # Create calories training dataset, CAL_CALORIES
    cal_rdd_LP_total = trainingData.filter(lambda x : (float(x[12]))!=0.0).map(lambda x : LabeledPoint(x[0], [x[12]])).collect()   
    cal_rdd_LP_total = sc.parallelize(cal_rdd_LP_total)
    # Create distance training dataset, DST_CURR_MOTION    DST_PACE    DST_SPEED    DST_TOTAL_DISTANCE
    dst_rdd_LP_total = trainingData.filter(lambda x : (float(x[13])+float(x[14])+float(x[15])+float(x[16]))!=0.0).map(lambda x : LabeledPoint(x[0], [x[13], x[14], x[15], x[16]])).collect()   
    dst_rdd_LP_total = sc.parallelize(dst_rdd_LP_total)

    # Train a RandomForest model.
    # Empty categoricalFeaturesInfo indicates all features are continuous.
    # Note: Use larger numTrees in practice.
    # Setting featureSubsetStrategy="auto" lets the algorithm choose.
    # Build accelerometer model

    # Check which model_type is acquiring.
    logger.debug("%s : Start training models, model type : %s ...", APP_NAME, mt)

    ## Perform steps for model type == FEATURE
    if (mt == MODEL_TYPE_FEATURE):        
        curr_model = None

        if(a_s == "accelerometer"):
            # Build Accel model
            logger.debug("%s : Training Accel model ...", APP_NAME)
            print "Training Accel model ..."
            model_accel = RandomForest.trainClassifier(accel_rdd_LP_total, numClasses=4, categoricalFeaturesInfo={},
                                                        numTrees=40, featureSubsetStrategy="auto",
                                                        impurity='gini', maxDepth=10, maxBins=50)
            curr_model = model_accel

        elif(a_s == "gyroscope"):
            # Build gyro model
            logger.debug("%s : Training Gyro model ...", APP_NAME)
            print "Training Gyro model ..."
            model_gyro = RandomForest.trainClassifier(gyro_rdd_LP_total, numClasses=4, categoricalFeaturesInfo={},
                                                         numTrees=40, featureSubsetStrategy="auto",
                                                         impurity='gini', maxDepth=10, maxBins=50)
            curr_model = model_gyro

        elif(a_s == "altimeter"):
            # Build altimeter model
            logger.debug("%s : Training Alti model ...", APP_NAME)
            print "Training Alti model ..."
            model_alti = RandomForest.trainClassifier(alti_rdd_LP_total, numClasses=4, categoricalFeaturesInfo={},
                                                         numTrees=40, featureSubsetStrategy="auto",
                                                         impurity='gini', maxDepth=10, maxBins=50)
            curr_model = model_alti

        elif(a_s == "ambientLight"):
            # Build ablight model
            logger.debug("%s : Training Ablight model ...", APP_NAME)
            print "Training Ablight model ..."
            model_ablight = RandomForest.trainClassifier(ablight_rdd_LP_total, numClasses=4, categoricalFeaturesInfo={},
                                                             numTrees=40, featureSubsetStrategy="auto",
                                                             impurity='gini', maxDepth=10, maxBins=50)
            curr_model = model_ablight

        elif(a_s == "barometer"):
            # Build brm model
            logger.debug("%s : Training Brm model ...", APP_NAME)
            print "Training Brm model ..."
            model_brm = RandomForest.trainClassifier(brm_rdd_LP_total, numClasses=4, categoricalFeaturesInfo={},
                                                         numTrees=40, featureSubsetStrategy="auto",
                                                         impurity='gini', maxDepth=10, maxBins=50)
            curr_model = model_brm

        elif(a_s == "calorie"):
            # Build calories model
            logger.debug("%s : Training Cal model ...", APP_NAME)
            print "Training Cal model ..."
            model_cal = RandomForest.trainClassifier(cal_rdd_LP_total, numClasses=4, categoricalFeaturesInfo={},
                                                         numTrees=40, featureSubsetStrategy="auto",
                                                         impurity='gini', maxDepth=10, maxBins=50)
            curr_model = model_cal

        elif(a_s == "distance"):
            # Build distance model 
            logger.debug("%s : Training Dst model ...", APP_NAME)
            print "Training Dst model ..."
            model_dst = RandomForest.trainClassifier(dst_rdd_LP_total, numClasses=4, categoricalFeaturesInfo={},
                                                         numTrees=40, featureSubsetStrategy="auto",
                                                         impurity='gini', maxDepth=10, maxBins=50)
            curr_model = model_dst


        if(curr_model is not None):
            # Save and load model
            print "Saving RainForest classification models : %s ..." % a_s
            logger.debug("%s : Saving RainForest classification models :  %s ...", APP_NAME, a_s)

            model_save_fp = "%s/%s_%s_%s_%s" % (MODEL_PATH, a_s, mid[1:-1], MODEL_EXT_FEATURE, MODEL_EXT)
            curr_model.save(sc, model_save_fp)

            print "Saving RainForest classification models completed successfuly to : %s" % model_save_fp
            logger.debug("%s : Saving RainForest classification models completed successfuly to : %s", APP_NAME, model_save_fp)
        
        else:
            logger.debug("%s : Current model == None !!", APP_NAME)
    

    ## Perform steps for model type == AGGREGATION
    elif (mt == MODEL_TYPE_AGGREGATION):

        ## Ensemble prediction models required all models to be trained at the first place.
        print "Training Accel model ..."
        logger.debug("%s : Training Accel model ...", APP_NAME)
        model_accel = RandomForest.trainClassifier(accel_rdd_LP_total, numClasses=4, categoricalFeaturesInfo={},
                                                        numTrees=40, featureSubsetStrategy="auto",
                                                        impurity='gini', maxDepth=10, maxBins=50)
        
        print "Training Gyro model ..."
        logger.debug("%s : Training Gyro model ...", APP_NAME)
        model_gyro = RandomForest.trainClassifier(gyro_rdd_LP_total, numClasses=4, categoricalFeaturesInfo={},
                                                         numTrees=40, featureSubsetStrategy="auto",
                                                         impurity='gini', maxDepth=10, maxBins=50)

        print "Training Alti model ..."
        logger.debug("%s : Training Alti model ...", APP_NAME)
        model_alti = RandomForest.trainClassifier(alti_rdd_LP_total, numClasses=4, categoricalFeaturesInfo={},
                                                         numTrees=40, featureSubsetStrategy="auto",
                                                         impurity='gini', maxDepth=10, maxBins=50)
        
        print "Training Ablight model ..."
        logger.debug("%s : Training Ablight model ...", APP_NAME)
        model_ablight = RandomForest.trainClassifier(ablight_rdd_LP_total, numClasses=4, categoricalFeaturesInfo={},
                                                         numTrees=40, featureSubsetStrategy="auto",
                                                         impurity='gini', maxDepth=10, maxBins=50)
        
        print "Training Brm model ..."
        logger.debug("%s : Training Brm model ...", APP_NAME)
        model_brm = RandomForest.trainClassifier(brm_rdd_LP_total, numClasses=4, categoricalFeaturesInfo={},
                                                         numTrees=40, featureSubsetStrategy="auto",
                                                         impurity='gini', maxDepth=10, maxBins=50)
        
        print "Training Cal model ..."
        logger.debug("%s : Training Cal model ...", APP_NAME)
        model_cal = RandomForest.trainClassifier(cal_rdd_LP_total, numClasses=4, categoricalFeaturesInfo={},
                                                         numTrees=40, featureSubsetStrategy="auto",
                                                         impurity='gini', maxDepth=10, maxBins=50)
        
        print "Training Dst model ..."
        logger.debug("%s : Training Dst model ...", APP_NAME)
        model_dst = RandomForest.trainClassifier(dst_rdd_LP_total, numClasses=4, categoricalFeaturesInfo={},
                                                         numTrees=40, featureSubsetStrategy="auto",
                                                         impurity='gini', maxDepth=10, maxBins=50)
        
        print "Completed training all models ..."
        logger.debug("%s : Completed training all models ...", APP_NAME)
        print "Getting prediction results for all models ..."
        logger.debug("%s : Getting prediction results for all models ...", APP_NAME)

        print "Predict Accel result ..."
        logger.debug("%s : Predict Accel result ...", APP_NAME)
        predictions_accel = model_accel.predict((sc.parallelize(testData.map(lambda x: LabeledPoint(x[0],[x[3], x[4], x[5]])).collect())).map(lambda x: x.features))

        print "Predict Gryo result ..."
        logger.debug("%s : Predict Gyro result ...", APP_NAME)
        predictions_gyro = model_gyro.predict(sc.parallelize(testData.map(lambda x: LabeledPoint(x[0],[x[9], x[10], x[11]])).collect()).map(lambda x: x.features))

        print "Predict Alti result ..."
        logger.debug("%s : Predict Alti result ...", APP_NAME)
        predictions_alti = model_alti.predict(sc.parallelize(testData.map(lambda x: LabeledPoint(x[0],[x[17], x[18], x[19], x[20], x[21], x[22], x[23], x[24], x[25]])).collect()).map(lambda x: x.features))
        
        print "Predict Ablight result ..."
        logger.debug("%s : Predict Ablight result ...", APP_NAME)        
        predictions_ablight = model_ablight.predict(sc.parallelize(testData.map(lambda x: LabeledPoint(x[0],[x[6]])).collect()).map(lambda x: x.features))

        print "Predict Brm result ..."
        logger.debug("%s : Predict Brm result ...", APP_NAME)
        predictions_brm = model_brm.predict(sc.parallelize(testData.map(lambda x: LabeledPoint(x[0],[x[7], x[8]])).collect()).map(lambda x: x.features))

        print "Predict Cal result ..."
        logger.debug("%s : Predict Cal result ...", APP_NAME)
        predictions_cal = model_cal.predict(sc.parallelize(testData.map(lambda x: LabeledPoint(x[0],[x[12]])).collect()).map(lambda x: x.features))

        print "Predict Dst result ..."
        logger.debug("%s : Predict Dst result ...", APP_NAME)
        predictions_dst = model_dst.predict(sc.parallelize(testData.map(lambda x: LabeledPoint(x[0],[x[13], x[14], x[15], x[16]])).collect()).map(lambda x: x.features))
        
        # Merge all the prediction results together
        print "Merge all the prediction results together ..."
        logger.debug("%s : Merge all the prediction results together ...", APP_NAME)
        labelsAndPredictions_accel = (sc.parallelize(testData.map(lambda x: LabeledPoint(x[0],[x[3], x[4], x[5]])).collect())).map(lambda lp: lp.label).zip(predictions_accel)
        labelsAndPredictions_temp = labelsAndPredictions_accel.zip(predictions_gyro)
        labelsAndPredictions_temp = labelsAndPredictions_temp.zip(predictions_alti)
        labelsAndPredictions_temp = labelsAndPredictions_temp.zip(predictions_ablight)
        labelsAndPredictions_temp = labelsAndPredictions_temp.zip(predictions_brm)
        labelsAndPredictions_temp = labelsAndPredictions_temp.zip(predictions_cal)
        labelsAndPredictions_temp = labelsAndPredictions_temp.zip(predictions_dst)

        # Build ensemble dataset for training
        print "Build ensemble dataset for training ..."
        logger.debug("%s : Build ensemble dataset for training ...", APP_NAME)
        ensemble_data_rdd = labelsAndPredictions_temp \
                                .map(lambda x : LabeledPoint(x[0][0][0][0][0][0][0], [x[0][0][0][0][0][0][1], x[0][0][0][0][0][1], x[0][0][0][0][1], x[0][0][0][1], x[0][0][1], x[0][1], x[1]])).collect()
        ensemble_data_rdd = sc.parallelize(ensemble_data_rdd)
        
        print "Traing Ensemble model ..."
        logger.debug("%s : Traing Ensemble model ...", APP_NAME)
        model_ensemble = RandomForest.trainClassifier(ensemble_data_rdd, numClasses=4, categoricalFeaturesInfo={0:4, 1:4, 2:4, 3:4, 4:4, 5:4, 6:4},
                                                      numTrees=50, featureSubsetStrategy="auto",
                                                      impurity='gini', maxDepth=16, maxBins=60)

        # Save the model        
        model_save_fp = "%s/%s_%s_%s_%s" % (MODEL_PATH, "aggregation", mid[1:-1], MODEL_EXT_AGGREGATION, MODEL_EXT)

        print "Saving ENSEMBLE classification models : %s ..." % model_save_fp
        model_ensemble.save(sc, model_save_fp)

        print "Saving ENSEMBLE classification models completed successfuly."
        logger.debug("%s : Saving ENSEMBLE classification models completed successfuly to : %s", APP_NAME, model_save_fp)

####################################################################################
####################################################################################
####################################################################################

def process_model_sklearn(mt, a_s, ds, mid):
    """
        # mt  : Model type              feature | aggregator
        # a_s : Activity sensor type
        # ds  : HDFS path to data soruce
        # mid : Model id (userId)
    
        # Main logic
        #   - look at the a_s. Must contains at least 1 sensor.
        #   - for each sensor
        #       - process the individual classifier model. --> data-models/sk_xxx.mdl based on the first 50% of source data
        #       - produce the input data (using the other 50%) for the aggregator
        #   - generate the aggregator model
    """    
    sensor_list = a_s.split(field_delimiter)
    user_id = mid[1:-1]  # remove the first and last "

    # Generate models for simple classifiers
    if (mt == MODEL_TYPE_FEATURE):
        logger.debug("%s : Start to model generator (Ver : %s), Activity Sensor: %s, SOURCE : %s, ID : %s ...", APP_NAME, VERSION_VAL, a_s, ds, mid)
    
        rawData_1 = sc.textFile(ds).map(lambda Row: Row.replace('"','')).map(lambda Row: Row.split(field_delimiter))
        rawData_2 = rawData_1.filter(lambda p: Row(len(p)>1 and unicodedata.normalize('NFKD',p[2]).encode('ascii', 'ignore')[1:-1] != "NONE")).filter(lambda p:Row(p[5] == mid))
        # map data to columns for sqlContext usage
        data = rawData_2.map(lambda p: Row(userid=p[5],activity=p[2],featurename=p[10],devicets=p[4],windowtsseconds=(int(p[4])/windowSeconds),acc_x=p[11],acc_y=p[12],acc_z=p[13],gyr_x=p[18],gyr_y=p[19],gyr_z=p[20])).toDF()
    
        logger.debug("%s : Reading in data source completed.", APP_NAME)
        logger.debug("%s : Validating data with input user_id : %s completed.", APP_NAME, mid)
    
        data.registerTempTable("RawData")
    
        for sensor_val in sensor_list:
            logger.debug("######################################################################")
            logger.debug("Start training model individual classifier for sensor list:%s" % sensor_val)
            # Processing accelerometer
            if (sensor_val == lst_sensor_act_type[0]):
                curr_model = process_accl_sklearn(user_id)
            # Processing gyroscope
            if (sensor_val == lst_sensor_act_type[1]):
                curr_model = process_gyro_sklearn(user_id)
            # Processing barometer
            elif (sensor_val == lst_sensor_act_type[4]):
                curr_model = process_brm_sklearn(user_id,mid)
    
            # Saving model for simple classifier
            if (curr_model is not None):
                logger.debug("%s : Saving classification models :  %s ...", APP_NAME, a_s )
                model_save_fp = "%s/%s_%s_%s_%s_%s" % (PROJECT_FOLDER, MODEL_SKLEARN_NAME_PRX, sensor_val, user_id, MODEL_EXT_FEATURE, MODEL_EXT)
                pickle.dump(curr_model, open(model_save_fp, 'wb'))
                logger.debug("%s : Saving classification models completed successfully to : %s", APP_NAME, model_save_fp)
            else:
                logger.debug("%s : Current model for simple classifier == None !!", APP_NAME)
    

    # Generate models for aggregator
    # we need at least 2 sensor to make any aggregation
    if (mt == MODEL_TYPE_AGGREGATION and len(sensor_list) > 1):
        '''        
        Generate the aggregation model based on the file created by the process_xxx_sklearn() 
        for a given user we will have at the end
            sk_aggrLabelPred_vincent.planat@hpe.com_accelerometer.txt
            sk_aggrLabelPred_vincent.planat@hpe.com_gyroscope.txt
            sk_aggrLabelPred_vincent.planat@hpe.com_barometer.txt
            sk_aggr_vincent.planat@hpe.com_labelEncoder
            sk_aggr_vincent.planat@hpe.com_ohEncoder
            sk_aggr_vincent.planat@hpe.com_mnbModel
        '''
        
        pred_df_list = []

        for sensor_val in sensor_list:
            file_path_val = PROJECT_FOLDER+"/sk_aggrLabelPred_"+user_id+"_"+sensor_val+".txt" 
            if (os.path.exists(file_path_val)):
                obj_df = pandas.read_csv(file_path_val)
                obj_df.columns = ['colNum', 'label', sensor_val, 'window']
                del obj_df['colNum']
                pred_df_list.append(obj_df)
            else:
                logger.error("file:%s does not exist. Can't proceed to aggregation. Exit")
                sys.exit(-1)
                
    
        print ("All required files are loaded.")
    
        #concatanate using window and label by key
        trainData = pandas.concat([df.set_index(['window', 'label']) for df in pred_df_list],axis=1).reset_index()    
    
        #drop rows with missing values - FOR TRAINING ONLY
        data_no_missing = trainData.dropna(axis=0)
        
        #convert labels to integers LABELENCODER
        label_encoder = preprocessing.LabelEncoder()
    
        #dataFeat = data_no_missing[['Accpred', 'Gyrpred', 'Barpred']]
        dataFeat = data_no_missing[sensor_list]
        
        dataLabel = data_no_missing['label']
        
        # Note. Niot aligned with the framework convention.
        # But this order is required by grainne Code
        temp_labels = ["SITTING", "WALKING", "WALKING_DOWN", "WALKING_UP", "Z"]
        labelModel = label_encoder.fit(temp_labels)
    
        # Saving label_encoder to file    
        pickle.dump(labelModel, open (PROJECT_FOLDER+"/sk_aggr_"+user_id+"_labelEncoder", "wb"))
        
        intIndexedAllFeat = dataFeat.apply(labelModel.transform)
        one_hot_encoder = OneHotEncoder(sparse = False)
    
        #save encModel
        one_hot_encoder_model = one_hot_encoder.fit(intIndexedAllFeat)
        pickle.dump(one_hot_encoder_model, open(PROJECT_FOLDER+"/sk_aggr_"+user_id+"_ohEncoder", 'wb'))
    
        allDataFeat = one_hot_encoder_model.transform(intIndexedAllFeat)
        dataLabel = data_no_missing['label'].ravel()
    
        #MULTINOMIAL NAIVE BAYES
        mnb = MultinomialNB()
        mnbModel = mnb.fit(allDataFeat, dataLabel)
    
        pickle.dump(mnbModel, open(PROJECT_FOLDER+"/sk_aggr_"+user_id+"_mnbModel", 'wb'))

    return

# Individual classifier
#######################
def process_gyro_sklearn(user_id):
        gyro_filtered = sqlContext.sql("SELECT userid, activity, featurename, devicets, windowtsseconds, gyr_x, gyr_y, gyr_z FROM RawData WHERE activity NOT LIKE 'NONE' AND featurename LIKE 'gyroscope' ORDER BY devicets")
        gyro_remDup = gyro_filtered.dropDuplicates()
        gyro_remDup.registerTempTable("gyro_remDup")
        #**For streaming, don't group by activity as activity is not known.
        #sqlContext is HiveContext not SparkContext
        gyro_features = sqlContext.sql("SELECT userid,activity,featurename,windowtsseconds,avg(gyr_x) as avg_gyr_x,avg(gyr_y) as avg_gyr_y,avg(gyr_z) as avg_gyr_z, variance(gyr_x) as variance_gyr_x,variance(gyr_y) as variance_gyr_y,variance(gyr_z) as variance_gyr_z, corr(gyr_x, gyr_y) as corr_xy, corr(gyr_x, gyr_z) as corr_xz, corr(gyr_y, gyr_z) as corr_yz, stddev(gyr_x) as std_gyr_x, stddev(gyr_y) as std_gyr_y, stddev (gyr_z) as std_gyr_z FROM gyro_remDup GROUP BY userid,activity,featurename,windowtsseconds ORDER BY userid,activity,featurename,windowtsseconds")
        gyro_features.registerTempTable("gyro_features")
        #replace NA values with 0
        gyro_fillNa = gyro_features.na.fill(0.0)
        gyro_fillNa.registerTempTable("gyro_fillNa")
        #select features and label only
        gyro_featLabel = sqlContext.sql("SELECT windowtsseconds, activity, avg_gyr_x, avg_gyr_y, avg_gyr_z, variance_gyr_x, variance_gyr_y, variance_gyr_z, corr_xy, corr_xz, corr_yz, std_gyr_x, std_gyr_y, std_gyr_z  FROM gyro_fillNa")
        gyro_featLabel.registerTempTable("gyro_featLabel")
        # fill any NA values with 0.0
        gyro_featLabel1 = gyro_featLabel.na.fill(0.0)
        
        # we need to split the data in 50/50.
        # first 50% will be for generating the simple classifier model
        # second 50% will be used to create sk_aggrLabelPred_ txt file used by the aggregation model generation
        splitSeed = 5043
        (featureData, AggregationData) = gyro_featLabel1.randomSplit([0.5, 0.5], splitSeed)
        featureData.registerTempTable("featureData")
        AggregationData.registerTempTable("AggregationData")
    
        featureData = featureData.toPandas()
        AggregationData_pd = AggregationData.toPandas()
    
        
        #gyro_allData = gyro_df4.toPandas()
        #split dataFrames into features, label, and window
        ##ALL DATA - FOR CROSS VALIDATION
        gyro_allDataFeat = featureData[['avg_gyr_x', 'avg_gyr_y','avg_gyr_z', 'variance_gyr_x', 'variance_gyr_y', 'variance_gyr_z', 'corr_xy', 'corr_xz', 'corr_yz', 'std_gyr_x', 'std_gyr_y', 'std_gyr_z']]
        #gyro_allDataLabel = gyro_allData[['label']]
        gyro_allDataLabel = featureData[['activity']]
        #gyro_allDataLabelWindow = featureData[['windowtsseconds']]
        #####RANDOM FOREST######
        #gyro_forest = RandomForestClassifier(max_depth=15, n_estimators = 32)
        gyro_forest = RandomForestClassifier()
        # Train Model
        logger.debug("%s : Training Gyro model ...", APP_NAME)
        #gyro_Y = gyro_allDataLabel['label'].ravel()
        gyro_Y = gyro_allDataLabel['activity'].ravel()
        model_gyro = gyro_forest.fit(gyro_allDataFeat,gyro_Y)
        # set model to be saved
        
    
        # produce the lavelPredAggr File for Aggregation
        testDataFeat = AggregationData_pd[['avg_gyr_x', 'avg_gyr_y','avg_gyr_z', 'variance_gyr_x', 'variance_gyr_y', 'variance_gyr_z', 'corr_xy', 'corr_xz', 'corr_yz', 'std_gyr_x', 'std_gyr_y', 'std_gyr_z']]
        testDataLabel = AggregationData_pd[['activity']]
        testDataLabelWindow = AggregationData_pd[['windowtsseconds']]
        predictions = pandas.DataFrame(model_gyro.predict(testDataFeat))
    
        labelPred = pandas.concat([testDataLabel, predictions], axis=1)    
        labelPredWindow = pandas.concat([labelPred, testDataLabelWindow], axis=1)
    
        # produce the file 
        labelPredWindow.to_csv(PROJECT_FOLDER+"/sk_aggrLabelPred_"+user_id+"_"+lst_sensor_act_type[1]+".txt")

        #sc.stop()
        return(model_gyro)
    
    

def process_accl_sklearn(user_id):
    accl_filtered = sqlContext.sql("SELECT userid, activity, featurename, devicets, windowtsseconds, acc_x, acc_y, acc_z FROM RawData WHERE featurename LIKE 'accelerometer' ORDER BY devicets")
    accl_filtered.registerTempTable("accl_filtered")
    #Remove duplicate rows
    accl_remDup = accl_filtered.dropDuplicates()
    accl_remDup.registerTempTable("accl_remDup")
    #sqlContext is HiveContext not SparkContext
    accl_features = sqlContext.sql("SELECT userid,activity,featurename,windowtsseconds,avg(acc_x) as avg_acc_x,avg(acc_y) as avg_acc_y,avg(acc_z) as avg_acc_z, variance(acc_x) as variance_acc_x,variance(acc_y) as variance_acc_y,variance(acc_z) as variance_acc_z, corr(acc_x, acc_y) as corr_xy, corr(acc_x, acc_z) as corr_xz, corr(acc_y, acc_z) as corr_yz, stddev(acc_x) as std_acc_x, stddev(acc_y) as std_acc_y, stddev(acc_z) as std_acc_z FROM accl_remDup GROUP BY userid,activity,featurename,windowtsseconds ORDER BY userid,activity,featurename,windowtsseconds")
    accl_features.registerTempTable("accl_features")
    #replace NA values with 0
    accl_fillNa = accl_features.na.fill(0.0)
    accl_fillNa.registerTempTable("accl_fillNa")
    #select features and label, window
    accl_featLabel = sqlContext.sql("SELECT windowtsseconds, activity, avg_acc_x, avg_acc_y, avg_acc_z, variance_acc_x, variance_acc_y, variance_acc_z, corr_xy, corr_xz, corr_yz, std_acc_x, std_acc_y, std_acc_z FROM accl_fillNa")
    accl_featLabel.registerTempTable("accl_featLabel")
    # fill any NA values with 0.0
    accl_featLabel1 = accl_featLabel.na.fill(0.0)

    # update vpl 06/09 (Grainne recommendations)
    ################################
    #Converts strings to integers, based on frequency of String.
    #accl_labelIndexer = StringIndexer(inputCol="activity", outputCol="label")

    #Important to save this as model, and use same model on future data so that Mapping of integers is the same
    #accl_indexerModel = accl_labelIndexer.fit(accl_featLabel)

    #use indexerModel to transform data
    #accl_df4 = accl_indexerModel.transform(accl_featLabel)
    #accl_df4.registerTempTable("accl_df4")
    #accl_allData = accl_df4.toPandas()
    
    accl_featLabel1.registerTempTable("accl_featLabel1")
    #Specify where to split
    splitSeed = 5043
    (featureData, AggregationData) = accl_featLabel1.randomSplit([0.5, 0.5], splitSeed)
    featureData.registerTempTable("featureData")
    AggregationData.registerTempTable("AggregationData")

    featureData_pd = featureData.toPandas()
    AggregationData_pd = AggregationData.toPandas()


    #split dataFrames into features, label, and window
    ##ALL DATA 
    accl_allDataFeat = featureData_pd[['avg_acc_x', 'avg_acc_y','avg_acc_z', 'variance_acc_x', 'variance_acc_y', 'variance_acc_z', 'corr_xy', 'corr_xz', 'corr_yz', 'std_acc_x', 'std_acc_y', 'std_acc_z']]
    
    #accl_allDataLabel = accl_allData[['label']]
    accl_allDataLabel = featureData_pd[['activity']]
    #accl_allDataLabelWindow = accl_allData[['windowtsseconds']]

    #####RANDOM FOREST######
    #define classifier
    #accl_forest = RandomForestClassifier(max_depth=15, n_estimators = 32)
    accl_forest = RandomForestClassifier()
    # Train Model
    logger.debug("%s : Training Accel model ...", APP_NAME)
    #accl_Y = accl_allDataLabel['label'].ravel()
    accl_Y = accl_allDataLabel['activity'].ravel()
    model_accel = accl_forest.fit(accl_allDataFeat, accl_Y)
    # set model to be saved
    #curr_model = model_accel
     
    # produce the lavelPredAggr File for Aggregation
    testDataFeat = AggregationData_pd[['avg_acc_x', 'avg_acc_y','avg_acc_z', 'variance_acc_x', 'variance_acc_y', 'variance_acc_z', 'corr_xy', 'corr_xz', 'corr_yz', 'std_acc_x', 'std_acc_y', 'std_acc_z']]
    testDataLabel = AggregationData_pd[['activity']]
    testDataLabelWindow = AggregationData_pd[['windowtsseconds']]
    predictions = pandas.DataFrame(model_accel.predict(testDataFeat))

    labelPred = pandas.concat([testDataLabel, predictions], axis=1)    
    labelPredWindow = pandas.concat([labelPred, testDataLabelWindow], axis=1)

    # produce the file 
    labelPredWindow.to_csv(PROJECT_FOLDER+"/sk_aggrLabelPred_"+user_id+"_"+lst_sensor_act_type[0]+".txt")

    return(model_accel)
    #sc.stop()

# Generate Barometer model for individual classifier
#def process_brm_sklearn(mt, a_s, ds, mid):
def process_brm_sklearn(user_id, mid):
    hiveContext = HiveContext(sc)
    brm_rawData_1 = sc.textFile(ds).map(lambda Row: Row.replace('"','')).map(lambda Row: Row.split(field_delimiter))
    brm_rawData_2 = brm_rawData_1.filter(lambda p: Row(len(p) > 1 and unicodedata.normalize('NFKD', p[2]).encode('ascii', 'ignore')[1:-1] != "NONE")).filter(lambda p: Row(p[5] == mid)).toDF()
        
    # map data to columns for sqlContext usage
    brm_data = brm_rawData_2.map(lambda p: Row(userid=p[5],activity=p[2],featurename=p[10],devicets=p[4],windowtsseconds=(int(p[4])/windowSeconds),air_pres=p[15],air_temp=p[16])).toDF()
    brm_data.registerTempTable("RawData")
    brm_filtered = hiveContext.sql("SELECT userid,activity,featurename,devicets,windowtsseconds,air_pres,air_temp FROM RawData WHERE activity NOT LIKE 'NONE' AND featurename LIKE 'barometer' ORDER BY devicets")
    brm_remDup = brm_filtered.dropDuplicates()
    brm_remDup.registerTempTable("brm_remDup")
    
    # Define groups and windowspec
    brm_group = ["userid", "activity", "featurename", "windowtsseconds"]
    brm_w = (Window().partitionBy(*brm_group).orderBy("devicets"))
    # GET SLOPE OF AIR PERS
    brm_v_diff = col("air_pres") - lag("air_pres", 1).over(brm_w)
    brm_t_diff = col("devicets") - lag("devicets", 1).over(brm_w)
    brm_slope_1 = brm_v_diff / brm_t_diff
    brm_addSlopeAP_1 = brm_remDup.withColumn("slopeAirPres", brm_slope_1)
    # GET SLOPE OF AIR TEMPERATURE
    brm_v_diff = col("air_temp") - lag("air_temp", 1).over(brm_w)
    brm_t_diff = col("devicets") - lag("devicets", 1).over(brm_w)
    brm_slope_2 = brm_v_diff / brm_t_diff
    brm_addSlopeAP_2 = brm_addSlopeAP_1.withColumn("slopeAirTemp", brm_slope_2)
    brm_new = brm_addSlopeAP_2.na.fill(0.0)
    brm_new.first()
    brm_new.registerTempTable("brm_new")
    brm_featLabel = hiveContext.sql("SELECT activity,windowtsseconds,avg(slopeAirPres) as avg_slopeAirPres,avg(slopeAirTemp) as avg_slopeAirTemp FROM brm_new GROUP BY activity,featurename,windowtsseconds ORDER BY windowtsseconds")
    brm_featLabel.registerTempTable("brm_featLabel")
    
    # update vpl 06/09 (Grainne recommendations)
    ################################
    #brm_labelIndexer = StringIndexer(inputCol="activity", outputCol="label")
    
    #Important to save this as model, and use same model on future data so that Mapping of integers is the same
    #brm_indexerModel = brm_labelIndexer.fit(brm_featLabel)
    
    #use indexerModel to transform data
    #brm_df4 = brm_indexerModel.transform(brm_featLabel)
    
    # brm_df4.registerTempTable("brm_df4")
    brm_featLabel.registerTempTable("brm_featLabel")
    
    # Splitting data. 50% for generating the simple classifier, 50% for the aggregation models
    splitSeed = 5043     
    (featureData, AggregationData) = brm_featLabel.randomSplit([0.5, 0.5], splitSeed)            
    featureData.registerTempTable("featureData")
    AggregationData.registerTempTable("AggregationData")

    # Generating the simple classifier models
    #########################################

    #brm_allData = brm_df4.toPandas()
    brm_allData = featureData.toPandas()
    ################################        
    brm_allDataFeat = brm_allData[['avg_slopeAirPres', 'avg_slopeAirTemp']] 
    
    # update vpl 06/09 (Grainne recommendations)
    #brm_allDataLabel = brm_allData[['label']]
    brm_allDataLabel = brm_allData[['activity']]

    brm_gnb = GaussianNB()
    # Train Model
    logger.debug("%s : Training Brm model ...", APP_NAME)

    # update vpl 06/09 (Grainne recommendations)
    #brm_Y = brm_allDataLabel['label'].ravel()
    brm_Y = brm_allDataLabel['activity'].ravel()
    
    model_bar = brm_gnb.fit(brm_allDataFeat, brm_Y)
    # set model to be saved
    #curr_model_simple_classifier = model_bar    
    
    # Generating the Input file for Aggregation classifier models
    #############################################################
    #print("Grainne ---")
    #print (AggregationData.shape())
    
    AggregationData_pd = AggregationData.toPandas()
    
    testDataFeat = AggregationData_pd[['avg_slopeAirPres', 'avg_slopeAirTemp']]
    testDataLabel = AggregationData_pd[['activity']]
    testDataLabelWindow = AggregationData_pd[['windowtsseconds']]

    predictions = pandas.DataFrame(model_bar.predict(testDataFeat))

    labelPred = pandas.concat([testDataLabel, predictions], axis=1)
    labelPredWindow = pandas.concat([labelPred, testDataLabelWindow], axis=1)

    labelPredWindow.to_csv(PROJECT_FOLDER+"/sk_aggrLabelPred_"+user_id+"_"+lst_sensor_act_type[4]+".txt")
    
    #sc.stop()
    return (model_bar)

###########################################################################################################################################
## Main model start
###########################################################################################################################################
## Starting of main module [ Add one more agurement for this script ]
if __name__ == '__main__':
    print('Usage: model_generator <model_type> <activity_sensor> <user_id> <data_set.csv> <train_model>')
    print('<model_type> : feature | aggregator')
    print('<train_model> : spark | sklearn')
    print('       <train_model> = spark. Then <model_type> can be feature | aggregator')
    print('       <train_model> = sklearn. Then <model_type> is not considered. All models (simple and aggr) are generated')
    print('output is located in folder:%s' % PROJECT_FOLDER)
    
    if (len(sys.argv) != 6):
        print('5 parameteres are required. Refer to Usage')
        logger.debug('5 parameteres are required. Refer to Usage')
        sys.exit(-1)

    # load input parameteres
    model_type = sys.argv[1]
    act_sensor = sys.argv[2]
    user_id = sys.argv[3]
    ds = sys.argv[4]
    train_model = sys.argv[5]
    
    act_sensor_list = act_sensor.split(field_delimiter)

    # if train_model is spark ac_sensor should not contain a list of sensor
    if (train_model == TRAIN_MODEL_SPARK and len(act_sensor_list)>1):
        logger.error("For Spark train_model activity_sensor must be limited to 1 sensor max")
        sys.exit(-1)

    # Check act_sensor is in correct case.
    # Check if <activity_sensor> is in correct setting.        
    logger.debug("Checking the sensor list")        
    if len(act_sensor_list) == 0:
        logger.error("sensor list: %s is empty. Exiting" % act_sensor_list)
        sys.exit(-1)
    # checking that all value in sensor_list are referenced correctly
    for sensor_val in act_sensor_list:
        if not any(sensor_val in item for item in lst_sensor_act_type):
            print("sensor value: %s is is not referenced. Exit" % sensor_val)
            logger.error("sensor value: %s is is not referenced. Exit" % sensor_val)
            sys.exit(-1)
    logger.info("sensor list is OK")

    # checking the model_type
    if (model_type != MODEL_TYPE_FEATURE and model_type != MODEL_TYPE_AGGREGATION):
        logger.debug("Invalid model_type (feature | aggregator). Refer to usage")        
        print("Invalid model_type (feature | aggregator). Refer to usage")        
        sys.exit(-1)
        
    # checking .csv file
    if (not os.path.exists(ds)):        
        logger.debug("Invalid <data_set.csv>. File does not exist")        
        print("Invalid <data_set.csv>. File does not exist")        
        sys.exit(-1)
    
    # Adding "" to front and end of user_id as data is surrounding by quote.
    user_id = "\"" + user_id + "\""
    logger.debug("%s : Chosen training model type : %s", APP_NAME, train_model)

    if (train_model==TRAIN_MODEL_SPARK):
        process_model_spark(model_type, act_sensor, ds, user_id )
    elif (train_model == TRAIN_MODEL_SKLEARN):
        process_model_sklearn(model_type, act_sensor, ds, user_id )
    else:
        logger.error("%s : Invalid <train_model> : %s", APP_NAME, train_model )
        print "%s : Valid training model type : spark | sklearn ", APP_NAME
        logger.debug("%s : Valid training model type should be : spark | sklearn ", APP_NAME )
        sys.exit(-1)
