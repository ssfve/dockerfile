
## Imports
from pyspark import SparkConf, SparkContext
from pyspark.streaming import StreamingContext
from pyspark.streaming.kafka import KafkaUtils
from ConfigParser import SafeConfigParser
from rta_datasets import SensorsDataset

from kafka import KafkaProducer
import rta_constants
import logging
import json
import sys
import uuid
import os

APP_NAME = "har_randomForest_accelerometer"
VERSION_VAL = "0.2_31032016"
SENSOR_TYPE = APP_NAME.split("_")[2]

logging.config.fileConfig(rta_constants.PROPERTIES_LOG_FILE)
logger = logging.getLogger(APP_NAME)
            
class HarAlgoSensor:
    """ 
    Opened
     - Fix process_data() which is actually only processing the first rdd (line ~199). 
         Whe should have data_payload = val_rdd.collect() and then for value in data_payload (exp of kairosDb_writer.py)
    
    
    Skeleton code for a processor 
            This code is launched by the rta_manager.py.
            At init phase it starts its own controller thread
            Then it listens to kafka topic(s) (spark streaming) and executes control command 
    """

    # For handling spark streamcontext.
    g_ssc = None    

    def __init__(self):
        # used to store the processor state
        self.current_state = None
        
        logger.debug("initializing Processor");
        # load properties from the rta.properties (use the APP_NAME as a section name)
        config_parser = SafeConfigParser()
        config_parser.read(rta_constants.PROPERTIES_FILE)
        
        # check the consistency of the APP_NAME section in rta.properties
        if (not config_parser.has_section(APP_NAME)):
            logger.error("properties file %s mal-formated. Missing section %s. Exit" % (rta_constants.PROPERTIES_FILE,APP_NAME))
            sys.exit(-1)        
        if (not config_parser.has_option(APP_NAME, "kafka.data.in.topics")):
            logger.error("properties file %s mal-formated. Missing attribut: kafka.data.in.topics in section %s. Exit" % (rta_constants.PROPERTIES_FILE,APP_NAME))
            sys.exit(-1)
        if (not config_parser.has_option(APP_NAME, "kafka.data.out.topic")):
            logger.error("properties file %s mal-formated. Missing attribut: kafka.data.out.topic in section %s. Exit" % (rta_constants.PROPERTIES_FILE,APP_NAME))
            sys.exit(-1)
        if (not config_parser.has_section(rta_constants.FRAMEWORK_NAME)):
            logger.error("properties file %s mal-formated. Missing section %s. Exit" % (rta_constants.PROPERTIES_FILE,rta_constants.FRAMEWORK_NAME))
            sys.exit(-1)
        if (not config_parser.has_option(rta_constants.FRAMEWORK_NAME, "kafka.host_port")):  
            logger.error("properties file %s mal-formated. Missing attribut: kafka.host_port in section %s. Exit" % (rta_constants.PROPERTIES_FILE,rta_constants.FRAMEWORK_NAME))
            sys.exit(-1)
        if (not config_parser.has_option(rta_constants.FRAMEWORK_NAME, "zookeeper.host_port")):  
            logger.error("properties file %s mal-formated. Missing attribut: zookeeper.host_port in section %s. Exit" % (rta_constants.PROPERTIES_FILE,rta_constants.FRAMEWORK_NAME))
            sys.exit(-1)
        if (not config_parser.has_option(rta_constants.FRAMEWORK_NAME, "kafka.control.topic")):  
            logger.error("properties file %s mal-formated. Missing attribut: kafka.control.topic in section %s. Exit" % (rta_constants.PROPERTIES_FILE,rta_constants.FRAMEWORK_NAME))
            sys.exit(-1)
        if (not config_parser.has_option(rta_constants.FRAMEWORK_NAME, "spark.nb_threads")):  
            logger.error("properties file %s mal-formated. Missing attribut: spark.nb_threads in section %s. Exit" % (rta_constants.PROPERTIES_FILE,rta_constants.FRAMEWORK_NAME))
            sys.exit(-1)
        if (not config_parser.has_option(rta_constants.FRAMEWORK_NAME, "spark.batch_duration")):  
            logger.error("properties file %s mal-formated. Missing attribut: spark.batch_duration in section %s. Exit" % (rta_constants.PROPERTIES_FILE,rta_constants.FRAMEWORK_NAME))
            sys.exit(-1)
                
        # retrieve config parameters
        # vpl. With DirectStream we need to use the 9092 port (or 6667 on DEV)
        self.kafka_host_consumer     = config_parser.get(rta_constants.FRAMEWORK_NAME, "zookeeper.host_port")
        self.kafka_host_producer     = config_parser.get(rta_constants.FRAMEWORK_NAME, "kafka.host_port")
        self.kafka_group             = APP_NAME        
        self.kafka_ctrl_topic        = config_parser.get(rta_constants.FRAMEWORK_NAME, "kafka.control.topic")
        self.kafka_data_in_topics    = config_parser.get(APP_NAME, "kafka.data.in.topics").replace(" ","").strip(';')        
        self.kafka_data_out_topic    = config_parser.get(APP_NAME, "kafka.data.out.topic")
        self.spark_nb_threads        = config_parser.get(rta_constants.FRAMEWORK_NAME, "spark.nb_threads")
        self.spark_batch_duration    = config_parser.get(rta_constants.FRAMEWORK_NAME, "spark.batch_duration")
        
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
        HarAlgoSensor.g_ssc = StreamingContext(sc, int(self.spark_batch_duration))        
        kafka_in_topics = dict(zip(self.kafka_data_in_topics.split(";"), [1]*len(self.kafka_data_in_topics.split(";"))))
        kafka_in_topics[self.kafka_ctrl_topic] = 1
        kafka_stream = KafkaUtils.createStream(HarAlgoSensor.g_ssc, self.kafka_host_consumer, self.kafka_group, kafka_in_topics).map(lambda x: x[1])
        kafka_stream.foreachRDD(lambda rdd: self.process_data(rdd))
        logger.debug("kafka consuler host:%s  group:%s topics:%s" % (self.kafka_host_consumer,self.kafka_group,kafka_in_topics));

        self.current_state = rta_constants.RTA_PROCESSOR_STATE_INITIALIZED
        
        # start the kafka stream. Both ctrl and data are sequenced at the same rythm
        HarAlgoSensor.g_ssc.start()
        HarAlgoSensor.g_ssc.awaitTermination()


    def on_get_status(self,query_id):
        """
            send back to the control_msg topic the current status of this processor
        """
        logger.debug("get status query: %s" % self.current_state)
        return_val = "{\"control_msg\":\"get_processor_status\",\"processor_name\" : \""+APP_NAME+"\",\"query_id\" : \""+str(query_id)+"\", \"answer\" : \""+self.current_state+"\"}"
        
        self.data_producer.send(self.kafka_ctrl_topic,return_val)
        return


    def on_start(self,query_id):
        """
            Method invoked by the ProcessorControler on reception of a start order on the control kafka topic
        """
        if not self.check_state_change(rta_constants.RTA_PROCESSOR_ORDER_START):
            logger.error("State transition forbidden. From %s to START" % self.current_state)
            return
        
        logger.debug("processor start")
        self.current_state = rta_constants.RTA_PROCESSOR_STATE_STARTED
        return

    
    def on_pause(self,query_id):
        """
            Method invoked by the ProcessorControler on reception of a pause order on the control kafka topic
            We cannot stop the streaming as it is also receiving control_msg 
            As a consequence the process data will check the status and if on Paused then do not process the data
        """
        if not self.check_state_change(rta_constants.RTA_PROCESSOR_ORDER_PAUSE):
            logger.error("State transition forbidden. From %s to PAUSE" % self.current_state)
            return

        logger.debug("processor pause")
        self.current_state = rta_constants.RTA_PROCESSOR_STATE_PAUSED
        return

    
    def on_stop(self,query_id):
        """
            Method invoked by the ProcessorControler on reception of a stop order on the control kafka topic
        """
        if not self.check_state_change(rta_constants.RTA_PROCESSOR_ORDER_STOP):
            logger.error("State transition forbidden. From %s to STOP" % self.current_state)
            return

        logger.debug("processor stop")
        self.current_state = rta_constants.RTA_PROCESSOR_STATE_STOPPED
        return
    
    def on_destroy(self,query_id):
        """
            Method invoked by the ProcessorControler on reception of a destroy order on the control kafka topic
        """
        if not self.check_state_change(rta_constants.RTA_PROCESSOR_ORDER_DESTROY):
            logger.error("State transition forbidden. From %s to DESTROY" % self.current_state)
            return

        logger.debug("processor destroy")
        self.current_state = rta_constants.RTA_PROCESSOR_STATE_DESTROYED

        # Ending context.
        # HarAlgoSensor.g_ssc.stop(True, True)
        HarAlgoSensor.g_ssc.stop(True, False)
        return


    def process_data(self,val_rdd):
        """
            this method is in charge of processing any rdd. We have 2 types of rdd
                - control rdd (on the control_msg topic)
                - data rdd
            1) check if rdd is empty
            2) check if rdd for control or not 
        """
        
        if (val_rdd.isEmpty()):
            logger.debug("empty val rdd")
            return
            
        # check if the rdd is for the controler or not.
        try:
            # We are using now CreateDirectStream which does not return the same format of rdd
            val_msg_json = json.loads(val_rdd.take(1)[0])
            #val_msg_json = json.loads(val_rdd.take(1)[0][1])
        except ValueError:
            logger.debug("val rdd is not valid JSON. No processing to do")
            return

        #val_msg_json = json.loads(val_rdd.take(1)[0])
        if  ('control_msg' in val_msg_json):
            self.process_ctrl_cmd(val_rdd)
            return
        # this is a sensor data
        else:            
            if (not self.current_state == rta_constants.RTA_PROCESSOR_STATE_STARTED):
                logger.debug("Not in STARTED STATE. Cannot proces data")
                return        
            self.process_rt_data(val_rdd)
        
        return

    def process_rt_data(self,val_rdd):
        """
            rdd have been captured on Kafka consumer topics listed in the 
                rta.properties files (section for this processor)
            At this stage, the process_data() must 
             - look into the rdd and get the sensorType.
             - invoke the data_set.add_xxx(rdd)
             - invoke the analytic logic for this processor
             - The result of this analytic is sent to the a Kafka client
                Example 
                    self.data_producer
                    msg={'toto':'vale'}
                    jd = json.dumps(msg)
                    kafka_producer.send_messages(self.kafka_data_out_topic, jd)
        """

        
    def process_ctrl_cmd(self,ctrl_rdd):
        """
            Invoked on reception of message on the ctrl command kafka topic
            0) check if rdd is Empty. Check format of query cmd (JSON)
            1) check if the processor name matches with config
            2) check if its a response to get_process_status
            3) extract content of the rdd received as a json 
                {"control_msg": "get_processor_status", "processor_name": "har_randomForest_accelerometer", "query_id" : "qwewqr-fsdfsd-1234"}
            4) invoke the self.caller.on_xxx() method based on the ctrl_msg  
        """
        if (ctrl_rdd.isEmpty()):
            logger.debug("empty Ctrl command")
            return

        # We are using now CreateDirectStream which does not return the same format of rdd
        ctrl_msg_json = json.loads(ctrl_rdd.take(1)[0])
        #ctrl_msg_json = json.loads(ctrl_rdd.take(1)[0][1])
        
        if  ((not 'control_msg' in ctrl_msg_json) |
            (not 'processor_name' in ctrl_msg_json) |
            (not 'query_id' in ctrl_msg_json)):
            logger.error(" one(s) of control_msg key(s) mal-formated %s:" % ctrl_msg_json)
            return

        if ((ctrl_msg_json['control_msg'] == "get_processor_status") & 
            ('answer' in ctrl_msg_json)):
            logger.debug("This is an answer to get_process_status query. Skip")
            return

        if (not ctrl_msg_json['processor_name'] == APP_NAME):
            logger.debug("processor_name: %s not for processor: %s" % (ctrl_msg_json['processor_name'],APP_NAME))
            return

        # invoke the on_xxx() methods                
        if ctrl_msg_json['control_msg'] ==  "get_processor_status":
            self.on_get_status(ctrl_msg_json['query_id']) 
        elif ctrl_msg_json['control_msg'] ==  "start_processor":
            self.on_start(ctrl_msg_json['query_id'])
        elif ctrl_msg_json['control_msg'] ==  "stop_processor":
            self.on_stop(ctrl_msg_json['query_id'])
        elif ctrl_msg_json['control_msg'] ==  "pause_processor":
            self.on_pause(ctrl_msg_json['query_id'])
        elif ctrl_msg_json['control_msg'] ==  "destroy_processor":
            self.on_destroy(ctrl_msg_json['query_id'])
        else:
            logger.error("could not recognize ctrl_msg: %s" % ctrl_msg_json['control_msg'])
    
    def check_state_change(self,change_order):
        """
        Check the authorized state order based on current state.
        Authorized list is
            INITIALIZE from STOPPED
            START from INITIALIZED
            PAUSE from STARTED
            START from PAUSED
            STOP from PAUSED
            DESTROY from INITIALIZED 
        """
        if (
            ((self.current_state == rta_constants.RTA_PROCESSOR_STATE_STOPPED) & 
             (change_order == rta_constants.RTA_PROCESSOR_ORDER_INITIALIZE)) |
            ((self.current_state == rta_constants.RTA_PROCESSOR_STATE_INITIALIZED) & 
             (change_order == rta_constants.RTA_PROCESSOR_ORDER_START)) |
            ((self.current_state == rta_constants.RTA_PROCESSOR_STATE_STARTED) & 
             (change_order == rta_constants.RTA_PROCESSOR_ORDER_PAUSE)) |
            ((self.current_state == rta_constants.RTA_PROCESSOR_STATE_PAUSED) & 
             (change_order == rta_constants.RTA_PROCESSOR_ORDER_START)) |
            ((self.current_state == rta_constants.RTA_PROCESSOR_STATE_PAUSED) & 
             (change_order == rta_constants.RTA_PROCESSOR_ORDER_STOP)) |
            ((self.current_state == rta_constants.RTA_PROCESSOR_STATE_INITIALIZED) & 
             (change_order == rta_constants.RTA_PROCESSOR_ORDER_DESTROY))
             ):
                return True
        else:
            return False




if __name__ == "__main__":

    myProcessor = HarAlgoSensor()
    
