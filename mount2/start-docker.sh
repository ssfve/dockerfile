#!/bin/bash -

# change hostname in rta.properties need to be done after docker run
sed -i.bak 's?hpe-smartwatch-03?'$HOSTNAME'?' /opt/rta_hc/rta-hc-framework-master/conf/rta.properties

# start tomcat
$TOMCAT_HOME/bin/catalina.sh start

# start ssh
ssh-keygen -q -t rsa -f ~/.ssh/id_rsa -N ''
ssh-keygen -q -t ecdsa -f ~/.ssh/id_ecdsa -N ''
cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys
cat ~/.ssh/id_ecdsa.pub >> ~/.ssh/authorized_keys
chmod og-wx ~/.ssh/authorized_keys
/usr/sbin/sshd

# config kafka topics
$KAFKA_HOME/bin/zookeeper-server-start.sh $KAFKA_HOME/config/zookeeper.properties &
sleep 1m

$KAFKA_HOME/bin/kafka-server-start.sh $KAFKA_HOME/config/server.properties &
sleep 1m

$KAFKA_HOME/bin/kafka-topics.sh --create --zookeeper 0.0.0.0:2181 --partitions 1 --replication-factor 1 --topic iot_har_novelty_detect
$KAFKA_HOME/bin/kafka-topics.sh --create --zookeeper 0.0.0.0:2181 --partitions 1 --replication-factor 1 --topic iot_har_predict_aggr
$KAFKA_HOME/bin/kafka-topics.sh --create --zookeeper 0.0.0.0:2181 --partitions 1 --replication-factor 1 --topic iot_processor_ctrl
$KAFKA_HOME/bin/kafka-topics.sh --create --zookeeper 0.0.0.0:2181 --partitions 1 --replication-factor 1 --topic iot_msband2_accel
$KAFKA_HOME/bin/kafka-topics.sh --create --zookeeper 0.0.0.0:2181 --partitions 1 --replication-factor 1 --topic iot_msband2_ambientLight
$KAFKA_HOME/bin/kafka-topics.sh --create --zookeeper 0.0.0.0:2181 --partitions 1 --replication-factor 1 --topic iot_msband2_barometer
$KAFKA_HOME/bin/kafka-topics.sh --create --zookeeper 0.0.0.0:2181 --partitions 1 --replication-factor 1 --topic iot_msband2_calorie
$KAFKA_HOME/bin/kafka-topics.sh --create --zookeeper 0.0.0.0:2181 --partitions 1 --replication-factor 1 --topic iot_msband2_contact
$KAFKA_HOME/bin/kafka-topics.sh --create --zookeeper 0.0.0.0:2181 --partitions 1 --replication-factor 1 --topic iot_msband2_distance
$KAFKA_HOME/bin/kafka-topics.sh --create --zookeeper 0.0.0.0:2181 --partitions 1 --replication-factor 1 --topic iot_msband2_gsr
$KAFKA_HOME/bin/kafka-topics.sh --create --zookeeper 0.0.0.0:2181 --partitions 1 --replication-factor 1 --topic iot_msband2_gyroscope
$KAFKA_HOME/bin/kafka-topics.sh --create --zookeeper 0.0.0.0:2181 --partitions 1 --replication-factor 1 --topic iot_msband2_hdhld
$KAFKA_HOME/bin/kafka-topics.sh --create --zookeeper 0.0.0.0:2181 --partitions 1 --replication-factor 1 --topic iot_msband2_heartRate
$KAFKA_HOME/bin/kafka-topics.sh --create --zookeeper 0.0.0.0:2181 --partitions 1 --replication-factor 1 --topic iot_msband2_pedometer
$KAFKA_HOME/bin/kafka-topics.sh --create --zookeeper 0.0.0.0:2181 --partitions 1 --replication-factor 1 --topic iot_msband2_rrInterval
$KAFKA_HOME/bin/kafka-topics.sh --create --zookeeper 0.0.0.0:2181 --partitions 1 --replication-factor 1 --topic iot_msband2_skinTemperature
$KAFKA_HOME/bin/kafka-topics.sh --create --zookeeper 0.0.0.0:2181 --partitions 1 --replication-factor 1 --topic iot_msband2_uv

# start cassandra and create tables
/usr/sbin/cassandra -f &
sleep 1m

cqlsh -e "source '/opt/rta_hc/iot_hc_schema.cql'"

# start kairosdb
$KAIROSDB_HOME/bin/kairosdb.sh start

# start hdfs
$HADOOP_HOME/bin/hdfs namenode -format
$HADOOP_HOME/sbin/start-dfs.sh

# start grafana
cd /usr/share/grafana
# service grfana-server start
/usr/sbin/grafana-server --pidfile=/var/run/grafana-server.pid --config=/etc/grafana/grafana.ini cfg:default.paths.data=/var/lib/grafana cfg:default.paths.logs=/var/log/grafana cfg:default.paths.plugins=/var/lib/grafana/plugins &

# IMPORTANT! the container needs this line to persist DO NOT DELETE
tail -f $TOMCAT_HOME/logs/catalina.out

