
# Startup
* The process that need to run in backgroup are the following.
* For more information about these process look at the [installation page here](installation.md)

## startup commands

|            | System |    Main Analytic                 |
|------------|--------|----------------------------------|
| HDFS       |Main Analytic. <br> Used by `processor_simple` & `process_aggr`|`cd /opt/mount1/hadoop-2.7.3/bin` <br> `sbin/start-dfs.sh`  |
| tomcat     |Main Storage. |`cd /opt/mount1/apache-tomcat-7.0.61` <br> `bin/catalina.sh start`                                                            |
| kafka      |Main Storage & Analytic|`cd /opt/mount1/kafka_2.10-0.9.0.0` <br> `bin/zookeeper-server-start.sh config/zookeeper.properties &` <br> `bin/kafka-server-start.sh config/server.properties &`  |
| spark      |Main storage & Analtytics|`cd /opt/mount1/spark-1.6.1-bin-hadoop2.6` <br> `sbin/start-all.sh`                                                        |
| cassandra  |Main storage | `cassandra &`                                                                                                             |
| supervisor |Main storage & Analtytics| `supervisord -n &`                                                                                                        |
| kairosDB   |Main storage | `cd /opt/mount1/kairosdb` <br> `bin/kairosdb.sh start`                                                                    |
| Grafana    |Main storage | `start sudo service grafana-server restart`                                                                               |


## stop commands

### Framework

| System     | Command                                                                                                                |
|------------|------------------------------------------------------------------------------------------------------------------------|
| HDFS       | `cd /opt/mount1/hadoop-2.7.3/bin`,`sbin/stop-dfs.sh`                                                                   |
| tomcat     | `PIDS= $(ps -ef | grep catalina | grep -v grep | awk '{print $2}')`<br> kill -s TERM $PIDS                             |
| kafka      | `PIDS=$(ps ax | grep -i 'kafka\.Kafka' | grep java | grep -v grep | awk '{print $1}')` <br> kill -s TERM $PIDS         |
| spark      | `cd /opt/mount1/spark-1.6.1-bin-hadoop2.6` <br> `sbin/stop-all.sh`                                                     |
| cassandra  | `PIDS=$(ps -ef | grep "cassandra.service.CassandraDaemon" | grep -v grep | awk '{print $1}')`  <br> kill -s TERM $PIDS |
| supervisor | `PIDS=$(ps -ef | grep "supervisor" | grep -v grep | awk '{print $1}')`,kill -s TERM $PIDS                              |
| kairosDb   | `cd /opt/mount1/kairosdb`,`bin/kairosdb.sh stop`                                                                       |
| Grafana    | `sudo service grafana-server stop`                                                                                     |

### Application
* All the components (`rta_process_simple`, `har_predict_aggr`, `raw_writter`, `novelty_detector`) can be stop by killing the process
```
`PIDS=$(ps -ef | grep <process name> | grep -v grep | awk '{print $1}')`  
kill -s TERM $PIDS
```

## who runs where

|process                  | ITG(c9t17308) | ITG(C2t08977) | DEV(C9t21193) | DEV(C2t08978) |
|-------------------------|---------------|---------------|---------------|---------------|
|kafka zookeeper server   | X             |               | X             |               |
|kafka server             | X             |               | X             |               |
|spark master             | X             | X             | X             | X             |
|spark worker             | X             | X             | X             | X             |
|processor accelerometer  | X             |               | X             |               |
|processor gyroscope      | X             |               | X             |               |
|processor barometer      | X             |               | X             |               |
|processor aggregator     | X             |               | X             |               |
|cassandra                |               | X             |               | X             |
|kairosDb server          |               | X             |               | X             |
|grafana server           |               | X             |               | X             |
|tomcat server            |               | X             |               | X             |
|novelty detector         |               | X             |               | X             |
|raw writter              |               | X             |               | X             |

# Models training

3 models are required by the solution

* Models for individual sensor processor (processor_simple.py)
  * The first version of the processor is using Randomforest for all the sensors. this resulted into a poor performance in classification. This approach requires HDFS as spark RF needs Hadoop to retrieve model from.
  * The new version is using sklearn based model. This approach use spark for streaming the traffic but all processing is done by pandas frames in python
* Model for aggregator
  * The first version is using Randomforest model loaded on HDFS.
* Model for novelty detection (BBN model)
  * Using python based BBN model.


Models must be trained for each user. A .csv file matching a "labbeled" activity must have been generated. The way to do it is to perform activity during ~1/2h 1h, collect the traffic on mysql (using the java servlet) and export the result to .csv. (Need to document on github from tiddlywiki)
The above procedure is described in [section raw-to-csv](../Others/raw-to-csv.md)

## simple classifier & aggregator

### V1.0 RandomForest (using HDFS).
Version 1.0 of the prototype rely, for the processor_simple and the aggregator, on HDFS based models.
These models are located under `/tmp/models` HDFS directory.

Configuration

* HDFS location is defined as a constant into the model_generator script (meaning that the rta_constants.py value is not used ..?)

* go to a user hadoop directory and copy the source csv file in it. One sample is available from github `data4model` directory

From here **(as hadoop)**

  - `hadoop fs -mkdir /tmp`
  - `hadoop fs -mkdir /tmp/models`
  - `hadoop fs -put rawmsband_24032016.csv /tmp`

move to the `$PROJECT_LOCATION`:

   * `cd $PROJECT_LOCATION/src`

Train models for gyroscope, altimeter, distance, accelerometer (`/tmp/rawmsband_24032016.csv` is the location in hadoop file system)

Notes

* version 1.0: do not use the `spark` parameter at the end
* version 1.1: use `spark` or `sklear` as below

Commands

   * `spark-submit --master local[4] --deploy-mode client model_generator.py feature accelerometer vincent.planat@hpe.com /tmp/rawmsband_24032016.csv spark`
   * `spark-submit --master local[4] --deploy-mode client model_generator.py feature gyroscope vincent.planat@hpe.com /tmp/rawmsband_24032016.csv spark`
   * `spark-submit --master local[4] --deploy-mode client model_generator.py feature distance vincent.planat@hpe.com /tmp/rawmsband_24032016.csv spark`
   * (optional not used) `spark-submit --master local[4] --deploy-mode client model_generator.py feature altimeter vincent.planat@hpe.com /tmp/rawmsband_24032016.csv spark`

Train model for har_aggregator

   * `spark-submit --master local[4] --deploy-mode client model_generator.py aggregation vincent.planat@hpe.com /tmp/rawmsband_24032016.csv`

Note:

* When HDFS was part of the hortonWorks then the model was directly created into HDFS.
* With a standalone install of HDFS it is created into /tmp/models (of Linux filesystem)
  * In this case need to do: `hadoop fs -put accelerometer_vincent.planat\@hpe.com_FEA_.MDL /tmp/models`

Check with `hadoop fs -ls /tmp/models`

```
drwxr-xr-x   - hadoop hadoop  0 2016-05-04 08:36 /tmp/models/accelerometer_vincent.planat@hpe.com_FEA_.MDL
drwxr-xr-x   - hadoop hadoop  0 2016-05-04 08:48 /tmp/models/aggregation_vincent.planat@hpe.com_AGR_.MDL
drwxr-xr-x   - hadoop hadoop  0 2016-05-05 06:48 /tmp/models/altimeter_vincent.planat@hpe.com_FEA_.MDL
drwxr-xr-x   - hadoop hadoop  0 2016-05-09 09:09 /tmp/models/distance_vincent.planat@hpe.com_FEA_.MDL
drwxr-xr-x   - hadoop hadoop  0 2016-05-04 08:42 /tmp/models/gyroscope_vincent.planat@hpe.com_FEA_.MDL
```
* check size : `hadoop fs -du -s /tmp/models/altimeter_vincent.planat@hpe.com_FEA_.MDL`

### V1.1 sklearn & spark (using HDFS)
* On version 1.1 of the prototype we introduce new models using sklearn library
* **HDFS is still needed but only as a source to the model training.** The resulting model is in a flat-file format.
* `har_predict_aggr` and `rta_process_simple` are coupled together. The reason is that
    * if the `<train_model>` is `spark` then the models are all RF based and we need an aggregator that will using a buffering mechanism to select the data and predict the har
    * if the `<train_model>` is `sklearn` then the data are subject to a timewindow 'sequencing' for generating the `rta_process_simple` models which forces us to use also specific model (`sklearn`) for the `har_predict_aggr`
* Usage is the following
```
Usage: model_generator <model_type> <activity_sensor> <user_id> <data_set.csv> <train_model>
  <model_type> : feature | aggregator
  <train_model> : spark | sklearn
         <train_model> = spark. Then <model_type> can be feature | aggregator
         <train_model> = sklearn. Then <model_type> is not considered.
              All models (simple and aggr) are generated
```
#### **If the `<train_model>` is `spark`**
* HDFS is used to store the resulting models
* `feature` and `aggregator` are supported.
* HDFS location is defined as a constant into the model_generator script (meaning that the rta_constants.py value is not used ..?)
* Example of command for `feature`
    * `spark-submit --master local[4] --deploy-mode client model_generator.py feature accelerometer vincent.planat@hpe.com /tmp/rawmsband_24032016.csv spark`
    * `spark-submit --master local[4] --deploy-mode client model_generator.py feature gyroscope vincent.planat@hpe.com /tmp/rawmsband_24032016.csv spark`
    * `spark-submit --master local[4] --deploy-mode client model_generator.py feature barometer vincent.planat@hpe.com /tmp/rawmsband_24032016.csv spark`
* Example of command for `aggregator`
    * `spark-submit --master local[4] --deploy-mode client model_generator.py aggregator vincent.planat@hpe.com /tmp/rawmsband_24032016.csv spark`

#### **If the `<train_model>` is `sklearn`**
* `feature` and `aggregator` are supported.
* sklearn model path is defined as a constant into the model_generator script
* for the `aggregator` option
    * we need to set a list of sensors used by the aggr.
    * a prerequisite is to have the individual model (`feature`) already generated
* result under the `$PROJECT_LOCATION/data-models`
* The `.txt` files are used as intermediate result for input to the `aggregator`
* Example of command for `feature`
* **The source File** must exist on HDFS. Use for example `hadoop fs -put /tmp/rawmsband_24032016.csv`

```
spark-submit --master local[4] --deploy-mode client model_generator.py feature accelerometer vincent.planat@hpe.com /tmp/rawmsband_24032016.csv sklearn

spark-submit --master local[4] --deploy-mode client model_generator.py feature gyroscope vincent.planat@hpe.com /tmp/rawmsband_24032016.csv sklearn

spark-submit --master local[4] --deploy-mode client model_generator.py feature barometer vincent.planat@hpe.com /tmp/rawmsband_24032016.csv sklearn
```

```
-rw-r--r-- 1 root   root     7477 Sep  8 11:53 sk_aggrLabelPred_vincent.planat@hpe.com_accelerometer.txt
-rw-r--r-- 1 root   root     7256 Sep  8 11:54 sk_aggrLabelPred_vincent.planat@hpe.com_gyroscope.txt
-rw-r--r-- 1 root   root     7158 Sep  8 11:59 sk_aggrLabelPred_vincent.planat@hpe.com_barometer.txt
-rw-r--r-- 1 root   root   251846 Sep  8 11:53 sk_accelerometer_vincent.planat@hpe.com_FEA_.MDL
-rw-r--r-- 1 root   root   280398 Sep  8 11:54 sk_gyroscope_vincent.planat@hpe.com_FEA_.MDL
-rw-r--r-- 1 root   root     1927 Sep  8 11:59 sk_barometer_vincent.planat@hpe.com_FEA_.MDL
```

* Example of command for `aggregator` (must have ran the `feature` before)
```
spark-submit --master local[4] --deploy-mode client model_generator.py aggregator accelerometer,gyroscope,barometer vincent.planat@hpe.com /tmp/rawmsband_24032016.csv sklearn
```
* result under the `$PROJECT_LOCATION/data-models`.
```
sk_aggr_vincent.planat@hpe.com_labelEncoder
sk_aggr_vincent.planat@hpe.com_ohEncoder
sk_aggr_vincent.planat@hpe.com_mnbModel
```

## BNN model for novelty detection (no HDFS)

* copy the user bnn file to the `src` directory
*  ` rm bnn_vincent_planat\@hpe_com*`
*  `cp data-models/bnn_vincent_platnat@hpe_com.bif src`

* *Take care of line ending Linux (use sublime text for update)*


## HDFS help
copy to local file system the whole stuff (for others tests without HDFS)

		  hadoop fs -copyToLocal /tmp/models/accelerometer_vincent.planat@hpe.com_FEA_.MDL .
		  hadoop fs -copyToLocal /tmp/models/aggregation_vincent.planat@hpe.com_AGR_.MDL .
		  hadoop fs -copyToLocal /tmp/models/altimeter_vincent.planat@hpe.com_FEA_.MDL .
		  hadoop fs -copyToLocal /tmp/models/distance_vincent.planat@hpe.com_FEA_.MDL .
		  hadoop fs -copyToLocal /tmp/models/gyroscope_vincent.planat@hpe.com_FEA_.MDL .


# Starting the analytic
Depending on the target system some process must be up and running before the analytic can start smoothly.
[Refer to who runs where table here](#who-runs-where).

## ITG V1.0
### c9t17308.itcs.hpecorp.net
The supervisor is now encapsulating these commands. So for information only

```
nohup spark-submit --master spark://16.250.25.6:7077 --executor-memory 2G --driver-memory 512M --total-executor-cores 1 --jars ../libs/spark-streaming-kafka-assembly_2.10-1.6.0.jar rta_processor_simple.py accelerometer 1>../log/rta_processor_accel.log 2>&1 &

nohup spark-submit --master spark://16.250.25.6:7077  --executor-memory 2G --driver-memory 512M --total-executor-cores 1 --jars ../libs/spark-streaming-kafka-assembly_2.10-1.6.0.jar rta_processor_simple.py gyroscope 1>../log/rta_processor_gyro.log 2>&1 &

nohup spark-submit --master spark://16.250.25.6:7077 --executor-memory 2G --driver-memory 512M --total-executor-cores 1 --jars ../libs/spark-streaming-kafka-assembly_2.10-1.6.0.jar rta_processor_simple.py distance 1>../log/rta_processor_distance.log 2>&1 &

nohup spark-submit --master spark://16.250.25.6:7077 --executor-memory 2G --driver-memory 512M --total-executor-cores 1 --jars ../libs/spark-streaming-kafka-assembly_2.10-1.6.0.jar har_predict_aggr_ensemble.py voting 1>../log/har_predict_aggr_ensemble.log 2>&1 &
```

### c2t08977.itcs.hpecorp.net
The supervisor is now encapsulating these commands. So for information only

```
nohup spark-submit --master spark://16.254.5.214:7077 --executor-memory 6G --driver-memory 512M --total-executor-cores 3 --jars /opt/mount1/rta-hc/integration/rta-hc-framework-master/libs/spark-streaming-kafka-assembly_2.10-1.6.0.jar raw_writer.py 1>../log/raw_writer.log 2>&1 &

nohup spark-submit --master spark://16.254.5.214:7077 --executor-memory 4G  --driver-memory 512M --total-executor-cores 1 --jars "../libs/spark-streaming-kafka-assembly_2.10-1.6.0.jar" --py-files "rta_constants.py,rta_datasets.py" novelty_detect.py 1>../log/novelty_detect.log 2>&1 &
```

## ITG V1.1
### c9t17308.itcs.hpecorp.net
The supervisor is now encapsulating these commands. So for information only

```
nohup /opt/mount1/spark-1.6.1-bin-hadoop2.6/bin/spark-submit --master spark://16.250.25.6:7077 --executor-memory 2G --driver-memory 512M --total-executor-cores 1 --jars ../libs/spark-streaming-kafka-assembly_2.10-1.6.0.jar rta_processor_simple_1_1.py accelerometer sklearn 1>../log/rta_processor_accel.log 2>&1 &

nohup /opt/mount1/spark-1.6.1-bin-hadoop2.6/bin/spark-submit --master spark://16.250.25.6:7077  --executor-memory 2G --driver-memory 512M --total-executor-cores 1 --jars ../libs/spark-streaming-kafka-assembly_2.10-1.6.0.jar rta_processor_simple_1_1.py gyroscope sklearn 1>../log/rta_processor_gyro.log 2>&1 &

nohup /opt/mount1/spark-1.6.1-bin-hadoop2.6/bin/spark-submit --master spark://16.250.25.6:7077 --executor-memory 2G --driver-memory 512M --total-executor-cores 1 --jars ../libs/spark-streaming-kafka-assembly_2.10-1.6.0.jar rta_processor_simple_1_1.py barometer sklearn 1>../log/rta_processor_barometer.log 2>&1 &

nohup /opt/mount1/spark-1.6.1-bin-hadoop2.6/bin/spark-submit --master spark://16.250.25.6:7077 --executor-memory 2G --driver-memory 512M --total-executor-cores 1 --jars ../libs/spark-streaming-kafka-assembly_2.10-1.6.0.jar har_predict_aggr_ensemble_1_1.py naivebayes 1>../log/har_predict_aggr_ensemble.log 2>&1 &

```

### c2t08977.itcs.hpecorp.net
The supervisor is now encapsulating these commands. So for information only

```
Similar to 1.0
```

## DEV 1.0
### c9t21193.itcs.hpecorp.net

```
nohup /opt/mount1/spark-1.6.1-bin-hadoop2.6/bin/spark-submit --master spark://16.250.7.135:7077 --executor-memory 2G --driver-memory 512M --total-executor-cores 1 --jars /opt/mount1/rta-hc/integration/rta-hc-framework-master/libs/spark-streaming-kafka-assembly_2.10-1.6.0.jar /opt/mount1/rta-hc/integration/rta-hc-framework-master/src/rta_processor_simple_1_1.py accelerometer sklearn 1>../log/rta_processor_accel.log 2>&1 &

nohup /opt/mount1/spark-1.6.1-bin-hadoop2.6/bin/spark-submit --master spark://16.250.7.135:7077 --executor-memory 2G --driver-memory 512M --total-executor-cores 1 --jars /opt/mount1/rta-hc/integration/rta-hc-framework-master/libs/spark-streaming-kafka-assembly_2.10-1.6.0.jar /opt/mount1/rta-hc/integration/rta-hc-framework-master/src/rta_processor_simple_1_1.py barometer sklearn 1>../log/rta_processor_barometer.log 2>&1 &

nohup /opt/mount1/spark-1.6.1-bin-hadoop2.6/bin/spark-submit --master spark://16.250.7.135:7077 --executor-memory 2G --driver-memory 512M --total-executor-cores 1 --jars /opt/mount1/rta-hc/integration/rta-hc-framework-master/libs/spark-streaming-kafka-assembly_2.10-1.6.0.jar /opt/mount1/rta-hc/integration/rta-hc-framework-master/src/rta_processor_simple_1_1.py gyroscope sklearn 1>../log/rta_processor_gyro.log 2>&1 &

nohup /opt/mount1/spark-1.6.1-bin-hadoop2.6/bin/spark-submit --master spark://16.250.7.135:7077 --executor-memory 2G --driver-memory 512M --total-executor-cores 1 --jars /opt/mount1/rta-hc/integration/rta-hc-framework-master/libs/spark-streaming-kafka-assembly_2.10-1.6.0.jar /opt/mount1/rta-hc/integration/rta-hc-framework-master/src/har_predict_aggr_ensemble_1_1.py naivebayes 1>../log/har_predict_aggr_ensemble.log 2>&1 &
```

# Using the traffic generator
* Example of command line:
```
python traffic_generate.py -u "vincent.planat@hpe.com" -p "/opt/mount1/temp/1_msbandraw_062016.txt" -s "http://C2t08978.itcs.hpecorp.net:9797/simpleiothttp2kafka/raw_msband_v2" -d 620000 -l 20
```

* Usage details
```
  "-u", "--nb_users", type=str, help="Users to be simulated to send traffic JSON data, and it"
                                                       "should be enclosed by double quote and delimitered by "
                                                       "pipeline sign like "
                                                       "\"chen-gangh@hpe.com|he_chengang@hotmail.com",
"-p", "--traffic_ref_path", type=str,
                    help="the file system path where the traffic reference files are stored", default="./",

"-d", "--test_duration", type=int, help="(ms) Life_time of each individual user thread"
                                                            " (the same for all of them)", default=10000)
"-l", "--lambd_inv", type=int, help="The average duration (in seconds) between each user thread"
                                                        " startup (poisson distribution)", default=3)

"-s", "--servlet_post_url", type=str, help="acquisition Servlet URL",
              default="http://c2t08977.itcs.hpecorp.net:9797/simpleiothttp2kafka/raw_msband_v2")
```


# Periodic cleanup

* Clean kairosDB data
   * stop mobile apps
   * ` python cleaner_db.py`

* Clean Cassandra data
```
cqlsh c2t08977.itcs.hpecorp.net -e "truncate iot_hc.raw_gsr;"
cqlsh c2t08977.itcs.hpecorp.net -e "truncate iot_hc.raw_accelerometer;"
cqlsh c2t08977.itcs.hpecorp.net -e "truncate iot_hc.raw_skintemperature;"
cqlsh c2t08977.itcs.hpecorp.net -e "truncate iot_hc.raw_gyroscope;"
cqlsh c2t08977.itcs.hpecorp.net -e "truncate iot_hc.raw_calorie;"
cqlsh c2t08977.itcs.hpecorp.net -e "truncate iot_hc.har_prediction;"
cqlsh c2t08977.itcs.hpecorp.net -e "truncate iot_hc.raw_distance;"
cqlsh c2t08977.itcs.hpecorp.net -e "truncate iot_hc.novelty_detect;"
cqlsh c2t08977.itcs.hpecorp.net -e "truncate iot_hc.raw_altimeter;"
cqlsh c2t08977.itcs.hpecorp.net -e "truncate iot_hc.raw_heartrate;"
cqlsh c2t08977.itcs.hpecorp.net -e "truncate iot_hc.raw_rrinterval;"
cqlsh c2t08977.itcs.hpecorp.net -e "truncate iot_hc.raw_uv;"
cqlsh c2t08977.itcs.hpecorp.net -e "truncate iot_hc.raw_ambientlight;"
cqlsh c2t08977.itcs.hpecorp.net -e "truncate iot_hc.raw_hdhld;"
cqlsh c2t08977.itcs.hpecorp.net -e "truncate iot_hc.raw_barometer;"
```

# Security Gateway monitoring

    Server: c9t17617.itcs.hpecorp.net
    Monitoring query
    ----------------
		select * from l7_analytics.access_log
		where l7_req_time >= DATE_ADD(NOW(),INTERVAL -1 DAY)
		and url not like '%/monitor/%'
		and url not like '%favicon.ico'
		and url like '%iot%'
		order by l7_req_time desc;
