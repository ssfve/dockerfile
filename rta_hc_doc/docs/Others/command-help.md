
# System maintenance

## docker

```
docker ps
docker exec -it ID /bin/bash


``

## Spark
* **remove non empty directory**
  `hadoop fs -rm  -R `


## Kafka
* **start servers**:
      `bin/zookeeper-server-start.sh config/zookeeper.properties &`
      `bin/kafka-server-start.sh config/server.properties &`

* **list topics**: `bin/kafka-topics.sh --list --zookeeper localhost:2181`
* **create topic**: `bin/kafka-topics.sh --create --zookeeper localhost:2181 --partitions 1 --replication-factor 1 --topic xxx_topic_name`
* **delete topic**: `bin/kafka-topics.sh --zookeeper localhost:2181 --delete --topic iot_ms_band`
* **consume topic**: `bin/kafka-console-consumer.sh --zookeeper localhost:2181 --topic iot_msband2_accel`
* **produce topic**: `bin/kafka-console-producer.sh --broker-list localhost:9092 --topic iot_msband2_accel`


* **config a new kafka seed_provider**
      1. Copy server.properties in config folder and name it with server-1.properties 
      2. Modify below properties in server-1.properties
      · make unique number for this broker
        broker.id=1
      · Update unique port for this broker
        listeners=PLAINTEXT://:9093
      · Update correct hostname for this broker
        host.name=c9t21193.itcs.hpecorp.net
      · To allow deletion of topic
        delete.topic.enable=true
      · Zookeeper hostname and port
        zookeeper.connect=c9t21193.itcs.hpecorp.net:2181
      · log directory. Note that you must make sure there is sufficient space to contain log in this folder.
        log.dirs=/opt/mount1/kafka/kafka_2.10-0.9.0.1/kafka-logs-1
      · Optional: Default number of partition for each topic
        num.partitions=1
      3. Start this broker
        nohup bin/kafka-server-start.sh config/server-1.properties &
      4. Example of creating topic with multiple partitions.

         bin/kafka-topics.sh --create --zookeeper localhost:2181 --replication-factor 1 --partitions 4 --topic my-replicated-topic
      5. Check details of topic
        [root@c9t21193 kafka_2.10-0.9.0.1]# bin/kafka-topics.sh --describe --zookeeper localhost:2181 --topic my-replicated-topic
        Topic:my-replicated-topic       PartitionCount:4        ReplicationFactor:1     Configs:
                Topic: my-replicated-topic      Partition: 0    Leader: 1       Replicas: 1     Isr: 1
                Topic: my-replicated-topic      Partition: 1    Leader: 0       Replicas: 0     Isr: 0
                Topic: my-replicated-topic      Partition: 2    Leader: 1       Replicas: 1     Isr: 1
              Topic: my-replicated-topic      Partition: 3    Leader: 0       Replicas: 0     Isr: 0 


## Kairosdb

**cleaner**

This will delete all metrics on both primary and secondary system

* login to: `c9t17308.itcs.hpecorp.net`
* `cd /opt/mount1/rta-hc/integration/rta-hc-framework-master/src`
* `python kairos_metrics_cleaner.py`


    	[hadoop@c9t17308 src]$ python kairos_metrics_cleaner.py
    	-------------- delete group-0 ----------------
    	DELETED metric http://c2t08977.itcs.hpecorp.net:9090/api/v1/metric/raw_calorie_calories. Status code:204
    	DELETED metric http://c2t08977.itcs.hpecorp.net:9090/api/v1/metric/raw_distance_current_motion. Status code:204
    	DELETED metric http://c2t08977.itcs.hpecorp.net:9090/api/v1/metric/raw_distance_pace. Status code:204
		etc ...

## Cassandra
* **cassandra cleaner**

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

* **cassandra table size**

	`cqlsh c2t08977.itcs.hpecorp.net -e "select count(*) from iot_hc.raw_gsr;"`


* **Ambari**
* start ambari: `ambari-server start`
