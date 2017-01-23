# HAR enhancement Specifications

## Objective

**The current approach is working as below**

* individual processors `rta_processor_simple.py` are working in parallel and produce independently an activity recognition (sitting, walking etc ...)
* Each `rta_processor_simple.py` is acting on a specific real-time traffic: `gyroscope`, `accelerometer`, `distance` coming from kafka topics:`iot_msband2_xxx`
  * We have at the moment 3 `rta_processor_simple.py`
    * `rta_processor_simple.py gyroscope`
    * `rta_processor_simple.py distance`
    * `rta_processor_simple.py accelerometer`
* The `rta_processor_simple.py` is loading, when it starts, a random forest model from HDFS
  * `hadoop fs -ls /tmp/models`
  ```
      drwxr-xr-x   - hadoop hadoop  0 2016-05-04 08:36 /tmp/models/accelerometer_vincent.planat@hpe.com_FEA_.MDL
      drwxr-xr-x   - hadoop hadoop  0 2016-05-04 08:48 /tmp/models/aggregation_vincent.planat@hpe.com_AGR_.MDL
      drwxr-xr-x   - hadoop hadoop  0 2016-05-05 06:48 /tmp/models/altimeter_vincent.planat@hpe.com_FEA_.MDL
      drwxr-xr-x   - hadoop hadoop  0 2016-05-09 09:09 /tmp/models/distance_vincent.planat@hpe.com_FEA_.MDL
      drwxr-xr-x   - hadoop hadoop  0 2016-05-04 08:42 /tmp/models/gyroscope_vincent.planat@hpe.com_FEA_.MDL
  ```
* Each `rta_processor_simple.py`, when it receives new traffic, queries this randomForest for getting an HAR prediction.
* The `rta_processor_simple.py` produces the result on a specific kafka topic: `iot_har_predict_aggr`
* The randomForest models have been trained by the `model_generator.py` script
* The following command must be launched, for example, when training a accelerometer model from the rawmsband_24032016.csv
  * `spark-submit --master local[4] --deploy-mode client model_generator.py feature accelerometer vincent.planat@hpe.com /tmp/rawmsband_24032016.csv`
  * For more information about how the models are trained refer to the startup page of this Wiki [see here](../Install/start.md)

**The problem we are facing is the following**

* We are training a model using **raw data** `rawmsband_24032016.csv`.
* No feature extraction is done prior to this training phase (like mean, standard deviation etc ...)
* This result into an unstable model when predicting the HAR (Human Activity Recognition)

**Solution**

* A new development has been tested by a colleague in Irland (Grainne) which demonstrates:
  * The feature extraction using Spark ( from lines 0:62)
  * The transformation of these data to data frame (pandas)
  * The usage of scikit learn libs to query the classifier.
* This approach is not exactly the same as the one we have implemented in our prototype.
  * It **does not use**  Spark ML classifier for predicting the Activity but rather the scikit libs
  * It is justified by the fact that all the sensors are not well applicable to randomForest model. For example for the barometer/altimeter the Gaussian Naïve Bayes is much more accurate. This model is not available in Spark
* This development is available on github (see the _Grainne code Github for HAR new modules_ in [About/Link page](../index.md) )
* This example requires a raw data file called `rawmsband_24032016.txt`. This file can be found [into the main github repo into the data4model folder](https://github.hpe.com/vincent-planat/rta-hc-framework/tree/master/data4model)
* The objective of the current work is to integrate this development into the existing framework
* The chosen approach (not using Spark ML for real-time classifier execution) has different impact
  * (-) The models are stored on a flat system. Distribution accross the cluster is not available through the HDFS data lake anymore
  * (-) loose some scalability provided by Spark parrallel execution
  * (+) Accuracy increase
* As we are now clearly understanding the technical +/- of the pure Spark ML approach (which was one of the objectives of the POC) and as we need to prove functionality (HAR accuracy) we will follow the approach proposed by Grainne in the Github code.


**Working directions**

* 2 modules of the existing framework must be updated
  * `model_generator.py`:
    * This module must be updated to produce the new randomforest models trained based on the extracted features
    * The overall logic of this module must not be touched.
      * Input & output parameters remain the same
      * Output model is pushed to Linux File System.
      * The model path will be modified to keep the existing model
        * Actually we have: `/tmp/models` (in HDFS)
        * We will store these new models in `{PROJECT_FOLDER}/data-models` (on file system)
  * `rta_processor_simple.py`
    * Loading the new model (from  `{PROJECT_FOLDER}/data-models`)
    * Creating real-time extracted features
      * Currently this module get the raw values from the Kafka topic and submit these one to the randomForest model
      * As the new model will be trained with extracted features the module
        * must compute the expected features based on the real-time data
    * submit these real-time features to the new model


**Working Environment**

* As detailed in the [setup page of this Wiki](../Install/setup.md) we have 2 environment: ITG and DEV.
* All the current development and unit test will be done on the _DEV_ environment
