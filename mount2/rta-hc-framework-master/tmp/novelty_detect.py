
## Imports
from pyspark import SparkConf, SparkContext
from pyspark.streaming import StreamingContext
from pyspark.streaming.kafka import KafkaUtils
from ConfigParser import SafeConfigParser
from  bisect import bisect_left
import rta_constants



from kafka import KafkaProducer
import rta_constants
import logging
import json
import sys

APP_NAME = "novelty_detect"
VERSION_VAL = "0.2_31032016"
# Must be retrieved from the models name in /tmp
USER_LIST = ["vincent.planat@hpe.com","user2@hpe.com"]

logging.config.fileConfig(rta_constants.PROPERTIES_LOG_FILE)
logger = logging.getLogger()

      
class NoveltyDetect:
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
        # used by the buffer algorithm to remember when the last proc was done
        # updated each time the buffer is processed and cleaned.
        self.schedule_time = 0      
        self.buffers_map = dict()                 # {"sensorName":sensor_buffer_dict}                                   

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
        if (not config_parser.has_option(APP_NAME, "sensor_ref_timestamp")):
            logger.error("properties file %s mal-formated. Missing attribut: sensor_ref_timestamp in section %s. Exit" % (rta_constants.PROPERTIES_FILE,APP_NAME))
            sys.exit(-1)
        if (not config_parser.has_option(APP_NAME, "buffer_time_window")):
            logger.error("properties file %s mal-formated. Missing attribut: buffer_time_window in section %s. Exit" % (rta_constants.PROPERTIES_FILE,APP_NAME))
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
        self.sensor_ref_timestamp    = config_parser.get(APP_NAME, "sensor_ref_timestamp")
        self.buffer_time_window      = int(config_parser.get(APP_NAME, "buffer_time_window"))
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
        NoveltyDetect.g_ssc = StreamingContext(sc, int(self.spark_batch_duration))        
        kafka_in_topics = dict(zip(self.kafka_data_in_topics.split(";"), [1]*len(self.kafka_data_in_topics.split(";"))))
        kafka_in_topics[self.kafka_ctrl_topic] = 1
        kafka_stream = KafkaUtils.createStream(NoveltyDetect.g_ssc, self.kafka_host_consumer, self.kafka_group, kafka_in_topics).map(lambda x: x[1])
        kafka_stream.foreachRDD(lambda rdd: self.process_data(rdd))
        logger.debug("buffer_time_window:%d kafka consuler host:%s  group:%s topics:%s" % (self.buffer_time_window,self.kafka_host_consumer,self.kafka_group,kafka_in_topics));

        #self.current_state = rta_constants.RTA_PROCESSOR_STATE_INITIALIZED
        logger.debug("skip the rta_manager and set the PROCESSOR_STATE to STARTED")        
        self.current_state = rta_constants.RTA_PROCESSOR_STATE_STARTED
        
        # start the kafka stream. Both ctrl and data are sequenced at the same rythm
        NoveltyDetect.g_ssc.start()
        NoveltyDetect.g_ssc.awaitTermination()


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
        NoveltyDetect.g_ssc.stop(True, False)
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
            selected_data = self.process_rt_data(val_rdd)
            logger.debug("selected_data_set:%s" % {i:selected_data[i] for i in selected_data.keys()})
        
        return

    def process_rt_data(self,val_rdd):
        """
            update the buffers with rdd content
            1) check if schedule_time == 0 meaning that this is the first time we process anything
                if Yes then set schedule_time to the oldest event timestamp of buffer identified by  sensor_ref_timestamp (rta.properties)
            
            2) Select the buffer with the smallest nb of event (lowest frequency) ==> lowest_freq_buffer
            
            3) (While ...) process the buffer as long as we find something to do 
                In lowest_freq_buffer do we have events betweens scheduletime & scheduletime + self.buffer_time_window ?
                (No) exit the While
                (Yes)
                    Scan all the buffer and update the selected_data_set with the value of each buffer
                    This include buffer cleanup with data older than newest_ts_lowfreq_buffer (same time ref for all buffers)
                Move the schedule_time ahead: buffer_time_window
        """
        # result_data_set will contain the set of data, in each buffer, whose timestamp is the closest to schedule_time
        # {"userId":[event,event], "userId":[event,event]}
        #   event is: {[eventid,deviceType,deviceId ]
        result_data_set = dict()

        # update the buffers_map with the rdd content (several json sensor msgs)
        self.update_buffers(val_rdd)
                    
        # If this is the first invokation we need to align the schedule_time to
        # the the oldest event timestamp of buffer identified by  sensor_ref_timestamp (rta.properties)
        if (self.schedule_time == 0):
           sensor_sorted_ts = sorted(self.buffers_map[self.sensor_ref_timestamp].keys())
           self.schedule_time = sensor_sorted_ts[0]
           logger.debug("initialize schedule_time:%d . Reference sensor is:%s" % (self.schedule_time,self.sensor_ref_timestamp))

        # what is the buffer with the smallest nb of event (lowest frequency) ==> lowest_freq_buffer
        # I will us it as a time reference for schedule_time with buffer_time_window increment
        # buffers_size is a dictionary {size-of-bufferName:bufferName}
        buffers_size = {len(self.buffers_map[buffer_name]):buffer_name for buffer_name in self.buffers_map}
        buffers_size_sorted = sorted(buffers_size.keys())
        lowest_freq_buffer_name = buffers_size[buffers_size_sorted[0]]
        lowest_freq_buffer =  self.buffers_map[lowest_freq_buffer_name]
        logger.debug("The lowest freq buffer is:%s   with size:%d" %(lowest_freq_buffer_name,len(lowest_freq_buffer)))
        
        
        for userId in USER_LIST:
            # process the buffer as long as we find something to do  
            # we have to loop through the different users
        
            # filter by userId
            logger.debug("processing user:%s" % userId)
            lowest_freq_userid_buffer = {i:lowest_freq_buffer[i] for i in lowest_freq_buffer if lowest_freq_buffer[i][2] == userId }
            if (len(lowest_freq_userid_buffer) == 0):
                logger.debug("   the buffer filtering based userId:%s resulted into a empty buffer. Skip and go to next userId" % userId)
                continue
            buffer_processing = True
            while (buffer_processing == True):
                # In lowest_freq_userid_buffer do we have events betweens scheduletime & self.buffer_time_window ?
                # filter by userId
                sorted_ts = sorted(lowest_freq_userid_buffer.keys())
                scan_ts = long(self.schedule_time + self.buffer_time_window)
                newest_ts_lowfreq_buffer = self.find_closest_ts(sorted_ts,scan_ts,rta_constants.CLOSEST_CHOICE_BACKW)
                logger.debug("   find the closest timestamp of:%d in lowest_freq_buffer_name:%s.  Result:%d" % (scan_ts,lowest_freq_buffer_name,newest_ts_lowfreq_buffer))
                if (newest_ts_lowfreq_buffer == -1):
                    # This is not the time to process anything..
                    # so we return and wait the next buffer update
                    buffer_processing = False
                    logger.debug("   The timestamp:%d used to search for event in buffer is above the max timestamp in lowest_freq_buffer_name:%s. So nothing to process" %(scan_ts, lowest_freq_buffer_name))
    
                else:
                    # Scan all the buffer and update the result_data_set with the value of each buffer
                    for buffer_name in self.buffers_map:
                        buffer_val = self.buffers_map[buffer_name]
                        # filter by user_id                        
                        buffer_val = {i:buffer_val[i] for i in buffer_val if buffer_val[i][2] == userId }
                        if len(buffer_val) != 0:
                            sorted_ts_buffer = sorted(buffer_val.keys())   
                            # http://integers.python.codesolution.site/57044-5673-from-list-integers-get-number-closest-given-value.html)            
                            closest_ts = self.find_closest_ts(sorted_ts_buffer, newest_ts_lowfreq_buffer,rta_constants.CLOSEST_CHOICE_BACKW_FORW)
                            if (closest_ts != -1):
                                if (len(result_data_set) >0):
                                    list_selected_event = result_data_set[userId]
                                else:
                                    list_selected_event = []

                                list_selected_event.append(buffer_val[closest_ts])
                                result_data_set[userId] = list_selected_event

                            else:
                                logger.debug("   the timestamp:%d is above the buffer:%s. Nothing to retrieve. Skip" % (newest_ts_lowfreq_buffer, buffer_name))
    
                            # cleanup  buffer. We remove the data that are older than newest_ts_lowfreq_buffer
                            # create a new dictionary with cleaned data
                            closest_ts = self.find_closest_ts(sorted_ts, self.schedule_time,rta_constants.CLOSEST_CHOICE_BACKW)
                            new_buffer_val = {i:buffer_val[i] for i in buffer_val if (i>newest_ts_lowfreq_buffer and buffer_val[i][2] == userId)}
                            logger.debug("   cleanup done: buffer:%20s previous-size:%d     current-size:%d for time_stamp:%d" % (buffer_name, len(buffer_val), len(new_buffer_val), newest_ts_lowfreq_buffer))
                            self.buffers_map[buffer_name] = new_buffer_val
    
                        else:
                            logger.debug("   This buffer %s is empty. Skip it" % buffer_name)
                                        
                    # move the schedule_time ahead and reset the selected_data_set dictionary
                    self.schedule_time = self.schedule_time + self.buffer_time_window
                    
        # check missing event and replace by None
        # {['eventid': dfedfdf, 'hr_rate': 4343], None} should be replaced by {['eventid': dfedfdf, 'hr_rate': 4343], ['eventid':None, 'hr_rate':None]}   
        #for user_val in result_data_set:
            #result_data_set[user_val] = self.fill_in_none(result_data_set[user_val])
            #logger.debug("user_val:%s  size of list of events: %d" % (user_val,len(list_events)))

        result_data_set = self.prepare_result_json(result_data_set)  
    
        return result_data_set

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


    def find_closest_ts(self,list_ts, ts,choice):
        '''
        return the closest value of the list.
        3 choice for processing the search, Backward & forward, backward, forward
        Example
            sorted_ts = [1200, 1300, 1500, 1700]
            find_closest_ts(1260,sorted_ts,rta_constants.CLOSEST_CHOICE_BACKW_FORW)       ==> 1300
            find_closest_ts(1260,sorted_ts,rta_constants.CLOSEST_CHOICE_BACKW)            ==> 1200
            find_closest_ts(1260,sorted_ts,rta_constants.CLOSEST_CHOICE_FORW)             ==> 1300
            '''
        if (ts > sorted(list_ts)[-1]):
            return -1
        pos = bisect_left(list_ts, ts)
        if pos == 0:
            return list_ts[0]
        if pos == len(list_ts):
            return list_ts[-1]
        before = list_ts[pos - 1]
        after = list_ts[pos]    
        if (choice == rta_constants.CLOSEST_CHOICE_BACKW_FORW):
            if after - ts < ts - before:
               return after
            else:
               return before
        elif (choice == rta_constants.CLOSEST_CHOICE_BACKW):
            return before
        elif (choice == rta_constants.CLOSEST_CHOICE_FORW):
            return after
        else:
            logger.debug("find_closest_ts unknow choice:",choice)
            return None


    '''
    def fill_in_none(self,list_events):
        # build the existing list of eventType  
        existing_eventype = []
        reference_eventype = ["har_predict_aggr","skinTemperature","heartRate","gsr","rrinterval"]
        for event in list_events:
            if "har_predict_aggr" in event:
                existing_eventype.append("har_predict_aggr")
            elif "skinTemperature" in event:
                existing_eventype.append("skinTemperature")
            elif "heartRate" in event:
                existing_eventype.append("heartRate")
            elif "gsr" in event:
                existing_eventype.append("gsr")
            elif "rrinterval" in event:
                existing_eventype.append("rrinterval")
        
            
        result_missing = [x for x in reference_eventype if x not in existing_eventype]
        for i in range(0,(len(result_missing))):
            if (result_missing == "har_predict_aggr"):
                #event = [jsonObj["eventId"],jsonObj["processor_name"],jsonObj["userid"],jsonObj["activity"],jsonObj["time_stamp"]]
                #list_events.append(None)
    '''

    def prepare_result_json(self,processing_data_set):
        '''
            This method is used to prepare the content before ending the databuffer processing
            The result of the databuffer is a dict of a list of JSON event.
            The order is specific (constraint of COng code for novelty detection)
                 'Skin Temparature', 'GSR', 'Heart-Rate', 'rrinterval' (index 0 --> 3)
                 index 4 is for the har_predict_aggr event
            The following method is preparing this JSON output.
            In addition it detect missing events and replace by None values
        
        '''
        for user_val in processing_data_set:
            list_events = processing_data_set[user_val]
            
            logger.debug("prepare result json for :%s" % list_events)  
            # initialize a fixe size list                                  
            list_of_json = [None] * 5
            for event in list_events:
                if "har_predict_aggr" in event:
                    data_json = [ {"eventId" : event[0], "processor_name": "har_predict_aggr", "activity": event[3], "userid": event[2], "time_stamp": event[4]}]
                    list_of_json[4] = data_json
                if "skinTemperature" in event:
                    data_json = [ {"eventId" : event[0], "deviceType":"msband2","deviceid":"b81e905908354542","eventtype":"skinTemperature","timestamp" : event[5], "userid": event[2], "trainingMode":"SITTING","temperature":event[7]}]
                    list_of_json[0] = data_json
                if "heartRate" in event:
                    data_json = [ {"eventId" : event[0], "deviceType":"msband2","deviceid":"b81e905908354542","eventtype":"heartRate","timestamp" : event[5], "userid": event[2], "trainingMode":"SITTING","rate":event[7], "quality": event[8]}]
                    list_of_json[2] = data_json
                if "gsr" in event:
                    data_json = [ {"eventId" : event[0], "deviceType":"msband2","deviceid":"b81e905908354542","eventtype":"gsr","timestamp" : event[5], "userid": event[2], "trainingMode":"SITTING","resistance":event[7]}]
                    list_of_json[1] = data_json
                if "rrinterval" in event:
                    data_json = [ {"eventId" : event[0], "deviceType":"msband2","deviceid":"b81e905908354542","eventtype":"rrinterval","timestamp" : event[5], "userid": event[2], "trainingMode":"SITTING","interval":event[7]}]
                    list_of_json[3] = data_json

            # What is missing ?            
            # Detect missing event and replace by None value
            # build the list of missing events ==> result_missing
            existing_eventype = []
            reference_eventype = ["har_predict_aggr","skinTemperature","heartRate","gsr","rrinterval"]
            for event in list_events:
                if "har_predict_aggr" in event:
                    existing_eventype.append("har_predict_aggr")
                elif "skinTemperature" in event:
                    existing_eventype.append("skinTemperature")
                elif "heartRate" in event:
                    existing_eventype.append("heartRate")
                elif "gsr" in event:
                    existing_eventype.append("gsr")
                elif "rrinterval" in event:
                    existing_eventype.append("rrinterval")
            result_missing = [x for x in reference_eventype if x not in existing_eventype]
            logger.debug("missing list:%s" % result_missing)
            for missing_elem in result_missing:
                if missing_elem == "har_predict_aggr":
                    data_json = [ {"eventId" : None, "processor_name":None, "activity":None, "userid": None, "time_stamp": None}]
                    list_of_json[4] = data_json
                if missing_elem =="skinTemperature":
                    data_json = [ {"eventId" : None, "deviceType":None,"deviceid":None,"eventtype":None,"timestamp" : None, "userid": None, "trainingMode":None,"temperature":0.0}]
                    list_of_json[0] = data_json
                if missing_elem =="heartRate":
                    data_json = [ {"eventId" : None, "deviceType":None,"deviceid":None,"eventtype":None,"timestamp" : None, "userid": None, "trainingMode":None,"rate":0.0, "quality": None}]
                    list_of_json[2] = data_json
                if missing_elem =="gsr":
                    data_json = [ {"eventId" : None, "deviceType":None,"deviceid":None,"eventtype":None,"timestamp" : None, "userid": None, "trainingMode":None,"resistance":0.0}]
                    list_of_json[1] = data_json
                if missing_elem =="rrinterval":
                    data_json = [ {"eventId" : None, "deviceType":None,"deviceid":None,"eventtype":None,"timestamp" : None, "userid": None, "trainingMode":None,"interval":0.0}]
                    list_of_json[3] = data_json
                
                
            processing_data_set[user_val] = list_of_json

                
                
                
                
            logger.debug(" --- missing list:%s" % result_missing)





        return processing_data_set

        '''

        [[u'5d0320cb-90f4-43e0-a4b1-77c7e5c430d7', u'msband2', u'vincent.planat@hpe.com', u'b81e905908354542', u'heartRate', 1461250997001, u'SITTING', 64, 1], 
        [u'1ab2aa15-b4ec-4f35-8407-be2182638f03', u'msband2', u'vincent.planat@hpe.com', u'b81e905908354542', u'gsr', 1461250997078, u'SITTING', 337445], 
        [u'2971a569-cb05-4305-b5e0-0ccc1a55cd09', u'msband2', u'vincent.planat@hpe.com', u'b81e905908354542', u'rrinterval', 1461250996069, u'SITTING', 1.2013300793720962]]}
        
        {"eventId":"b810f6f9-36e5-4ce4-b690-49c3d594fd20","deviceType":"msband2","deviceid":"b81e905908354542","eventtype":"heartRate","timestamp":1457003459013,"userid":"vincent.planat@hpe.com","trainingMode":"SITTING","rate":"73","quality":1}
        {"eventId":"e690960a-aa21-45b2-88bf-7a86544fe184","deviceType":"msband2","deviceid":"b81e905908354542","eventtype":"gsr","timestamp":1457003461894,"userid":"vincent.planat@hpe.com","trainingMode":"SITTING","resistance":6488}
        {"eventId":"bc637a1d-a686-434d-8ec2-42d1ac950b72","deviceType":"msband2","deviceid":"b81e905908354542","eventtype":"rrinterval","timestamp":1457003458509,"userid":"vincent.planat@hpe.com","trainingMode":"SITTING","interval":0.8296}
        
        
        '''



    def update_buffers(self,val_rdd):
        '''
        This method update the buffers_map with the values received from the rdd_val
        '''
        data_payload = val_rdd.collect()
        for value in data_payload:
            # check if the rdd is for the controler or not.
            try:
                jsonObj = json.loads(value)
            except ValueError:
                logger.debug("val rdd is not valid JSON. No processing to do")
                return
            # jsonObj is a list. Need to retrieve the fisrt and unique value [{.....}] 
            jsonObj = jsonObj[0]
            
            # define a sensorType. Depends on type of rdd we get (Activity or Physio)
            if 'processor_name' in jsonObj:
                sensorType = jsonObj['processor_name']
            elif 'eventtype' in jsonObj:
                sensorType = jsonObj['eventtype']
            else:
                logger.error("Can't retrieve a processor_nae or eventtype from inpu rdd. Skip the rdd value");
                continue
                
            # check if a buffer for this sensor has already been created                 
            if not sensorType in self.buffers_map:           
                self.buffers_map[sensorType] =  {}

            # update the buffer
            buffer_val = self.buffers_map[sensorType]
            
            # {"eventId": "ce360a04-660b-4600-80b8-74f63398fc4b", "processor_name": "har_predict_aggr", "userid": "vincent.planat@hpe.com", 
            #    "activity": "WALKING_UP", "time_stamp": 1457003525741}
            if ('processor_name' in jsonObj and jsonObj["processor_name"] == "har_predict_aggr"): 
                sensorVals = [jsonObj["eventId"],jsonObj["processor_name"],jsonObj["userid"],jsonObj["activity"],jsonObj["time_stamp"]]
                buffer_val[jsonObj["time_stamp"]] = sensorVals
                logger.debug("updated buffer:%s" % sensorType)

            # skinTemp        
            # {"eventId":"3b549f48-0d64-496d-8097-f5442468ab1c","deviceType":"msband2","deviceid":"b81e905908354542","eventtype":"skinTemperature",
            #  "timestamp":1456939587501,"userid":"vincent.planat@hpe.com","trainingMode":"SITTING","temperature":30.809999}            
            elif ('eventtype' in jsonObj and jsonObj["eventtype"] == rta_constants.SENSORS_PHYSIO_TYPE[0]): 
                sensorVals = [jsonObj["eventId"],jsonObj["deviceType"],jsonObj["userid"],jsonObj["deviceid"],jsonObj["eventtype"],jsonObj["timestamp"],jsonObj["trainingMode"],jsonObj["temperature"]]
                buffer_val[jsonObj["timestamp"]] = sensorVals
                logger.debug("updated buffer:%s" % sensorType)

            # gsr
            #{"eventId":"1ab78221-847c-4b4f-97ba-3dac5ff333cf","deviceType":"msband2","deviceid":"b81e905908354542","eventtype":"gsr",
            # "timestamp":1456939591481,"userid":"vincent.planat@hpe.com","trainingMode":"SITTING","resistance":340330}                
            elif ('eventtype' in jsonObj and jsonObj["eventtype"] == rta_constants.SENSORS_PHYSIO_TYPE[2]): 
                sensorVals = [jsonObj["eventId"],jsonObj["deviceType"],jsonObj["userid"],jsonObj["deviceid"],jsonObj["eventtype"],jsonObj["timestamp"],jsonObj["trainingMode"],jsonObj["resistance"]]
                buffer_val[jsonObj["timestamp"]] = sensorVals
                logger.debug("updated buffer:%s" % sensorType)

            # heartRate
            #{"eventId":"7c573cbd-510f-4361-9282-4f3616b27e20","deviceType":"msband2","deviceid":"b81e905908354542","eventtype":"heartRate",
            # "timestamp":1456939604898,"userid":"vincent.planat@hpe.com","trainingMode":"SITTING","rate":"85","quality":0}
            elif ('eventtype' in jsonObj and jsonObj["eventtype"] == rta_constants.SENSORS_PHYSIO_TYPE[1]): 
                sensorVals = [jsonObj["eventId"],jsonObj["deviceType"],jsonObj["userid"],jsonObj["deviceid"],jsonObj["eventtype"],jsonObj["timestamp"],jsonObj["trainingMode"],jsonObj["rate"],jsonObj["quality"]]
                buffer_val[jsonObj["timestamp"]] = sensorVals
                logger.debug("updated buffer:%s" % sensorType)

            # rrinterval
            # {"eventId":"dc5f7142-0efa-4998-a862-784bd0f8720d","deviceType":"msband2","deviceid":"b81e905908354542","eventtype":"rrinterval",
            # "timestamp":1456939644347,"userid":"vincent.planat@hpe.com","trainingMode":"SITTING","interval":0.597312}
            elif ('eventtype' in jsonObj and jsonObj["eventtype"] == rta_constants.SENSORS_PHYSIO_TYPE[3]):                 
                sensorVals = [jsonObj["eventId"],jsonObj["deviceType"],jsonObj["userid"],jsonObj["deviceid"],jsonObj["eventtype"],jsonObj["timestamp"],jsonObj["trainingMode"],jsonObj["interval"]]
                buffer_val[jsonObj["timestamp"]] = sensorVals
                logger.debug("updated buffer:%s" % sensorType)
                            

if __name__ == "__main__":

    myProcessor = NoveltyDetect()
    
