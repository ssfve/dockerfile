'''
Created on Mar 14, 2016

@author: zhangcon
'''
'''
Created on Mar 10, 2016

@author: zhangcon
'''




from pyspark import SparkConf, SparkContext
    
APP_NAME = "Spark Streaming test_cz"
conf = SparkConf().setAppName(APP_NAME)
conf = conf.setMaster("local[*]")
sc   = SparkContext(conf=conf)

data = sc.textFile("data/raw_msband_current_10032016_1.csv").map(lambda line: line.split(",")).filter(lambda line: len(line)>1 and line[2] != "NONE").map(lambda line: [line[2],line[4], line[5], line[11], line[12], line[13], line[14],line[15], line[16],
                                                                                                                                          line[18],line[19], line[20], line[25], line[27], line[28],line[29], line[30],
                                                                                                                                          line[31],line[32], line[33], line[34], line[35], line[36], line[37],line[38], line[39]]).collect()
def process_data(data): 
    #import pandas as pd
    import json
    from pyspark.mllib.regression import LabeledPoint
    
    for value in data:
        k = 0
        i = 0
        sum_val = 0.0
        for val in value:
            i = i + 1
            if i>3:
                sum_val = sum_val + float(val)
        k = k+1
        if sum_val == 0.0:
            data.remove(value)
    
    data_rdd_id = {}
    
    for file_csv in data:
        if file_csv[2] in data_rdd_id.keys():
            data_rdd_id[file_csv[2]].append(file_csv)
        else:
            data_rdd_id[file_csv[2]] = [file_csv]
    
    data_rdd_key = []
    for key in data_rdd_id.keys():
        data_rdd_key.append(key)
       
    user_id =  "vincent.planat@hpe.com"
    
    # transfer SITTING, WALKING, WALKING_UP, WALKING_DOWN to 0, 1, 2, 3 to fit the random forest parameter requirements  
    col_num = 0
    for row in data_rdd_id[user_id]:
        col_num = len(row)
        for i in range(col_num):
                if row[i] == 'SITTING':
                    row[i]=0
                elif row[i] == 'WALKING':
                    row[i]=1
                elif row[i] == 'WALKING_UP':
                    row[i]=2
                elif row[i] == 'WALKING_DOWN':
                    row[i]=3  
                    
    data_rdd_user = sc.parallelize(data_rdd_id[user_id])
    
    #import random forest library
    from pyspark.mllib.tree import RandomForest
    import uuid  
    # Split the data into training and test sets (25% held out for testing)
    (trainingData, testData) = data_rdd_user.randomSplit([0.75, 0.25])
    #print type(testData)
    accel_rdd_LP_total = trainingData.filter(lambda x : (float(x[3])+float(x[4])+float(x[5]))!=0.0).map(lambda x : LabeledPoint(x[0], [x[3], x[4], x[5]])).collect() 
    accel_rdd_LP_total = sc.parallelize(accel_rdd_LP_total)
    gyro_rdd_LP_total = trainingData.filter(lambda x : (float(x[9])+float(x[10])+float(x[11]))!=0.0).map(lambda x : LabeledPoint(x[0], [x[9], x[10], x[11]])).collect()   
    gyro_rdd_LP_total = sc.parallelize(gyro_rdd_LP_total)
    alti_rdd_LP_total = trainingData.filter(lambda x : (float(x[17])+float(x[18])+float(x[19])+float(x[20])+float(x[21])+float(x[22])+float(x[23])+float(x[24])+float(x[25]))!=0.0).map(lambda x : LabeledPoint(x[0], [x[17], x[18], x[19], x[20], x[21], x[22], x[23], x[24], x[25]])).collect()   
    alti_rdd_LP_total = sc.parallelize(alti_rdd_LP_total)
    ablight_rdd_LP_total = trainingData.filter(lambda x : (float(x[6]))!=0.0).map(lambda x : LabeledPoint(x[0], [x[6]])).collect()   
    ablight_rdd_LP_total = sc.parallelize(ablight_rdd_LP_total)
    brm_rdd_LP_total = trainingData.filter(lambda x : (float(x[7])+float(x[8]))!=0.0).map(lambda x : LabeledPoint(x[0], [x[7], x[8]])).collect()   
    brm_rdd_LP_total = sc.parallelize(brm_rdd_LP_total)
    cal_rdd_LP_total = trainingData.filter(lambda x : (float(x[12]))!=0.0).map(lambda x : LabeledPoint(x[0], [x[12]])).collect()   
    cal_rdd_LP_total = sc.parallelize(cal_rdd_LP_total)
    dst_rdd_LP_total = trainingData.filter(lambda x : (float(x[13])+float(x[14])+float(x[15])+float(x[16]))!=0.0).map(lambda x : LabeledPoint(x[0], [x[13], x[14], x[15], x[16]])).collect()   
    dst_rdd_LP_total = sc.parallelize(dst_rdd_LP_total)
    
    # Train a RandomForest model.
    #  Empty categoricalFeaturesInfo indicates all features are continuous.
    #  Note: Use larger numTrees in practice.
    #  Setting featureSubsetStrategy="auto" lets the algorithm choose.
    model_accel = RandomForest.trainClassifier(accel_rdd_LP_total, numClasses=4, categoricalFeaturesInfo={},
                                         numTrees=11, featureSubsetStrategy="auto",
                                         impurity='gini', maxDepth=6, maxBins=32)
# predict directly without testing, the accuracy is low about 55%    
#     testData_accel_LP_rdd_pred = testData.map(lambda x: (x[3], x[4], x[5])).collect()
#     testData_accel_LP_rdd_pred = sc.parallelize(testData_accel_LP_rdd_pred)
#     predictions_accel = model_accel.predict(testData_accel_LP_rdd_pred)
     
    # Evaluate model on test instances and compute test error
#     testData_accel_LP_rdd = testData.map(lambda x: LabeledPoint(x[0],[x[3], x[4], x[5]])).collect()
#     testData_accel_LP_rdd = sc.parallelize(testData_accel_LP_rdd)
#     predictions_accel = model_accel.predict(testData_accel_LP_rdd.map(lambda x: x.features))
#     labelsAndPredictions_accel = testData_accel_LP_rdd.map(lambda lp: lp.label).zip(predictions_accel)
    predictions_accel = model_accel.predict((sc.parallelize(testData.map(lambda x: LabeledPoint(x[0],[x[3], x[4], x[5]])).collect())).map(lambda x: x.features))
    labelsAndPredictions_accel = (sc.parallelize(testData.map(lambda x: LabeledPoint(x[0],[x[3], x[4], x[5]])).collect())).map(lambda lp: lp.label).zip(predictions_accel)
    #testErr_accel = labelsAndPredictions_accel.filter(lambda (v, p): v != p).count() / float(testData.count())
    #print('Accel Test Error = ' + str(testErr_accel))
    #print('Learned classification forest model:')
    #print(model_accel.toDebugString())
    # Save and load model
    #model.save(sc, "myModelPath")
    #sameModel = RandomForestModel.load(sc, "myModelPath")
    
    # output the accel prediction results
    # accel_pred = []
    # for value in predictions_accel.collect():
    #     if value == 0.0:
    #         accel_pred.append('SITTING')
    #     elif value == 1.0:
    #         accel_pred.append('WALKING')
    #     elif value == 2.0:
    #         accel_pred.append('WALKING_UP')
    #     elif value == 3.0:
    #         accel_pred.append('WALKING_DOWN')   
    # 
    # test_timestamp = testData.map(lambda x : x[1]).collect()   
    # import json      
    # import uuid  
    # from json import JSONEncoder
    # from uuid import UUID
    # JSONEncoder_olddefault = JSONEncoder.default
    # def JSONEncoder_newdefault(self, o):
    #     if isinstance(o, UUID): return str(o)
    #     return JSONEncoder_olddefault(self, o)
    # JSONEncoder.default = JSONEncoder_newdefault
    # 
    # with open('accel_pred_resluts.json', 'w') as fp:
    #     for i in range(len(accel_pred)):
    #         newdata = {"processor_name": "har_randomforest_Accel", "query_id": uuid.uuid4(), "time_stamp": test_timestamp[i], "accel_result":accel_pred[i]}
    #         json.dump(newdata, fp)
    #         fp.write('\n')
    
    
    model_gyro = RandomForest.trainClassifier(gyro_rdd_LP_total, numClasses=4, categoricalFeaturesInfo={},
                                         numTrees=11, featureSubsetStrategy="auto",
                                         impurity='gini', maxDepth=6, maxBins=32)
        
    # Evaluate model on test instances and compute test error
#     testData_gyro_LP_rdd = testData.map(lambda x: LabeledPoint(x[0],[x[9], x[10], x[11]])).collect()
#     testData_gyro_LP_rdd = sc.parallelize(testData_gyro_LP_rdd)
#     predictions_gyro = model_gyro.predict(testData_gyro_LP_rdd.map(lambda x: x.features))
#     labelsAndPredictions_gyro = testData_gyro_LP_rdd.map(lambda lp: lp.label).zip(predictions_gyro)
    predictions_gyro = model_gyro.predict(sc.parallelize(testData.map(lambda x: LabeledPoint(x[0],[x[9], x[10], x[11]])).collect()).map(lambda x: x.features))
    #labelsAndPredictions_gyro = sc.parallelize(testData.map(lambda x: LabeledPoint(x[0],[x[9], x[10], x[11]])).collect()).map(lambda lp: lp.label).zip(predictions_gyro)
    #testErr_gyro = labelsAndPredictions_gyro.filter(lambda (v, p): v != p).count() / float(testData.count())
    #print('Gyro Test Error = ' + str(testErr_gyro))
    #print('Learned classification forest model:')
    #print(model_accel.toDebugString())
    # Save and load model
    #model.save(sc, "myModelPath")
    #sameModel = RandomForestModel.load(sc, "myModelPath")
    
    model_alti = RandomForest.trainClassifier(alti_rdd_LP_total, numClasses=4, categoricalFeaturesInfo={},
                                         numTrees=11, featureSubsetStrategy="auto",
                                         impurity='gini', maxDepth=6, maxBins=32)
         
    # Evaluate model on test instances and compute test error
#     testData_alti_LP_rdd = testData.map(lambda x: LabeledPoint(x[0],[x[17], x[18], x[19], x[20], x[21], x[22], x[23], x[24], x[25]])).collect()
#     testData_alti_LP_rdd = sc.parallelize(testData_alti_LP_rdd)
#     predictions_alti = model_alti.predict(testData_alti_LP_rdd.map(lambda x: x.features))
#     labelsAndPredictions_alti = testData_alti_LP_rdd.map(lambda lp: lp.label).zip(predictions_alti)
    predictions_alti = model_alti.predict(sc.parallelize(testData.map(lambda x: LabeledPoint(x[0],[x[17], x[18], x[19], x[20], x[21], x[22], x[23], x[24], x[25]])).collect()).map(lambda x: x.features))
    #labelsAndPredictions_alti = sc.parallelize(testData.map(lambda x: LabeledPoint(x[0],[x[17], x[18], x[19], x[20], x[21], x[22], x[23], x[24], x[25]])).collect()).map(lambda lp: lp.label).zip(predictions_alti)
    #testErr_alti = labelsAndPredictions_alti.filter(lambda (v, p): v != p).count() / float(testData.count())
    #print('Alti Test Error = ' + str(testErr_alti))
    #print('Learned classification forest model:')
    #print(model_accel.toDebugString())
    # Save and load model
    #model.save(sc, "myModelPath")
    #sameModel = RandomForestModel.load(sc, "myModelPath")
     
    model_ablight = RandomForest.trainClassifier(ablight_rdd_LP_total, numClasses=4, categoricalFeaturesInfo={},
                                         numTrees=11, featureSubsetStrategy="auto",
                                         impurity='gini', maxDepth=6, maxBins=32)
         
    # Evaluate model on test instances and compute test error
#     testData_ablight_LP_rdd = testData.map(lambda x: LabeledPoint(x[0],[x[6]])).collect()
#     testData_ablight_LP_rdd = sc.parallelize(testData_ablight_LP_rdd)
#     predictions_ablight = model_ablight.predict(testData_ablight_LP_rdd.map(lambda x: x.features))
#     labelsAndPredictions_ablight = testData_ablight_LP_rdd.map(lambda lp: lp.label).zip(predictions_ablight)
    predictions_ablight = model_ablight.predict(sc.parallelize(testData.map(lambda x: LabeledPoint(x[0],[x[6]])).collect()).map(lambda x: x.features))
    #labelsAndPredictions_ablight = sc.parallelize(testData.map(lambda x: LabeledPoint(x[0],[x[6]])).collect()).map(lambda lp: lp.label).zip(predictions_ablight)
    #testErr_ablight = labelsAndPredictions_ablight.filter(lambda (v, p): v != p).count() / float(testData.count())
    #print('ablight Test Error = ' + str(testErr_ablight))
    #print('Learned classification forest model:')
    #print(model_accel.toDebugString())
    # Save and load model
    #model.save(sc, "myModelPath")
    #sameModel = RandomForestModel.load(sc, "myModelPath")
     
    model_brm = RandomForest.trainClassifier(brm_rdd_LP_total, numClasses=4, categoricalFeaturesInfo={},
                                         numTrees=11, featureSubsetStrategy="auto",
                                         impurity='gini', maxDepth=6, maxBins=32)
         
    # Evaluate model on test instances and compute test error
#     testData_brm_LP_rdd = testData.map(lambda x: LabeledPoint(x[0],[x[7], x[8]])).collect()
#     testData_brm_LP_rdd = sc.parallelize(testData_brm_LP_rdd)
#     predictions_brm = model_brm.predict(testData_brm_LP_rdd.map(lambda x: x.features))
#     labelsAndPredictions_brm = testData_brm_LP_rdd.map(lambda lp: lp.label).zip(predictions_brm)
    predictions_brm = model_brm.predict(sc.parallelize(testData.map(lambda x: LabeledPoint(x[0],[x[7], x[8]])).collect()).map(lambda x: x.features))
    #labelsAndPredictions_brm = sc.parallelize(testData.map(lambda x: LabeledPoint(x[0],[x[7], x[8]])).collect()).map(lambda lp: lp.label).zip(predictions_brm)
    #testErr_brm = labelsAndPredictions_brm.filter(lambda (v, p): v != p).count() / float(testData.count())
    #print('brm Test Error = ' + str(testErr_brm))
    #print('Learned classification forest model:')
    #print(model_accel.toDebugString())
    # Save and load model
    #model.save(sc, "myModelPath")
    #sameModel = RandomForestModel.load(sc, "myModelPath")
     
    model_cal = RandomForest.trainClassifier(cal_rdd_LP_total, numClasses=4, categoricalFeaturesInfo={},
                                         numTrees=11, featureSubsetStrategy="auto",
                                         impurity='gini', maxDepth=6, maxBins=32)
         
    # Evaluate model on test instances and compute test error
#     testData_cal_LP_rdd = testData.map(lambda x: LabeledPoint(x[0],[x[12]])).collect()
#     testData_cal_LP_rdd = sc.parallelize(testData_cal_LP_rdd)
#     predictions_cal = model_cal.predict(testData_cal_LP_rdd.map(lambda x: x.features))
#     labelsAndPredictions_cal = testData_cal_LP_rdd.map(lambda lp: lp.label).zip(predictions_cal)
    predictions_cal = model_cal.predict(sc.parallelize(testData.map(lambda x: LabeledPoint(x[0],[x[12]])).collect()).map(lambda x: x.features))
    #labelsAndPredictions_cal = sc.parallelize(testData.map(lambda x: LabeledPoint(x[0],[x[12]])).collect()).map(lambda lp: lp.label).zip(predictions_cal)
    #testErr_cal = labelsAndPredictions_cal.filter(lambda (v, p): v != p).count() / float(testData.count())
    #print('cal Test Error = ' + str(testErr_cal))
    #print('Learned classification forest model:')
    #print(model_accel.toDebugString())
    # Save and load model
    #model.save(sc, "myModelPath")
    #sameModel = RandomForestModel.load(sc, "myModelPath")
     
    model_dst = RandomForest.trainClassifier(dst_rdd_LP_total, numClasses=4, categoricalFeaturesInfo={},
                                         numTrees=11, featureSubsetStrategy="auto",
                                         impurity='gini', maxDepth=6, maxBins=32)
         
    # Evaluate model on test instances and compute test error
#     testData_dst_LP_rdd = testData.map(lambda x: LabeledPoint(x[0],[x[13], x[14], x[15], x[16]])).collect()
#     testData_dst_LP_rdd = sc.parallelize(testData_dst_LP_rdd)
#     predictions_dst = model_dst.predict(testData_dst_LP_rdd.map(lambda x: x.features))
#     labelsAndPredictions_dst = testData_dst_LP_rdd.map(lambda lp: lp.label).zip(predictions_dst)
    predictions_dst = model_dst.predict(sc.parallelize(testData.map(lambda x: LabeledPoint(x[0],[x[13], x[14], x[15], x[16]])).collect()).map(lambda x: x.features))
    #labelsAndPredictions_dst = sc.parallelize(testData.map(lambda x: LabeledPoint(x[0],[x[13], x[14], x[15], x[16]])).collect()).map(lambda lp: lp.label).zip(predictions_dst)
    #testErr_dst = labelsAndPredictions_dst.filter(lambda (v, p): v != p).count() / float(testData.count())
    #print('Dst Test Error = ' + str(testErr_dst))
    #print('Learned classification forest model:')
    #print(model_accel.toDebugString())
    # Save and load model
    #model.save(sc, "myModelPath")
    #sameModel = RandomForestModel.load(sc, "myModelPath")
    
    
    labelsAndPredictions_temp = labelsAndPredictions_accel.zip(predictions_gyro)
    labelsAndPredictions_temp = labelsAndPredictions_temp.zip(predictions_alti)
    labelsAndPredictions_temp = labelsAndPredictions_temp.zip(predictions_ablight)
    labelsAndPredictions_temp = labelsAndPredictions_temp.zip(predictions_brm)
    labelsAndPredictions_temp = labelsAndPredictions_temp.zip(predictions_cal)
    labelsAndPredictions_temp = labelsAndPredictions_temp.zip(predictions_dst)
    
    #for value in labelsAndPredictions_temp.collect():
    #    print value
    ensemble_data_rdd = labelsAndPredictions_temp.map(lambda x : LabeledPoint(x[0][0][0][0][0][0][0], [x[0][0][0][0][0][0][1], x[0][0][0][0][0][1], x[0][0][0][0][1], x[0][0][0][1], x[0][0][1], x[0][1], x[1]])).collect()
    ensemble_data_rdd = sc.parallelize(ensemble_data_rdd)
    (train_ensemble, test_ensemble) = ensemble_data_rdd.randomSplit([0.75, 0.25])
    
    model_ensemble = RandomForest.trainClassifier(train_ensemble, numClasses=4, categoricalFeaturesInfo={},
                                                  numTrees=16, featureSubsetStrategy="auto",
                                                  impurity='gini', maxDepth=6, maxBins=32)
    
    predictions_ensemble = model_ensemble.predict(test_ensemble.map(lambda x: x.features))
    labelsAndPredictions_ensemble = test_ensemble.map(lambda lp : lp.label).zip(predictions_ensemble)
    testErr_ensemble = labelsAndPredictions_ensemble.filter(lambda (v,p): v != p).count()/float(test_ensemble.count())
    print('ensemble Test Error = ' + str(testErr_ensemble))
     
#     y_actu = pd.Series(test_ensemble.map(lambda lp: lp.label).collect(),name='Actual')
#     y_pred = pd.Series(predictions_ensemble.collect(), name='Predicted')
#     # df_confusion = pd.crosstab(y_actu, y_pred).apply(lambda r: 100.0 * r/r.sum())
#     df_confusion = pd.crosstab(y_actu, y_pred)
#     print 'confusion table of all data with labels, 0: SITTING, 1: WALKING, 2: WALKING_UP, 3: WALKING_DOWN'
#     print df_confusion
#     #print('Learned classification forest model:')
#     #print(model.toDebugString())
    ensemble_pred = []
    for value in predictions_ensemble.collect():
                if value == 0.0:
                    ensemble_pred.append('SITTING')
                elif value == 1.0:
                    ensemble_pred.append('WALKING')
                elif value == 2.0:
                    ensemble_pred.append('WALKING_UP')
                elif value == 3.0:
                    ensemble_pred.append('WALKING_DOWN')   

    test_timestamp = testData.map(lambda x : x[1]).collect()   
            
    from json import JSONEncoder
    from uuid import UUID
    JSONEncoder_olddefault = JSONEncoder.default
    def JSONEncoder_newdefault(self, o):
        if isinstance(o, UUID): return str(o)
        return JSONEncoder_olddefault(self, o)
    JSONEncoder.default = JSONEncoder_newdefault
    
    with open('ensemble_result.json', 'w') as fp:
        for i in range(len(ensemble_pred)):
            newdata = {"processor_name": "har_randomforest_ensemble", "query_id": uuid.uuid4(), "time_stamp": test_timestamp[i], "accel_result":ensemble_pred[i]}
            json.dump(newdata, fp)
            fp.write('\n')

process_data(data)
