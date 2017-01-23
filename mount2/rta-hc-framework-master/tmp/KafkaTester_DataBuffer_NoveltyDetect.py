# -*- coding: utf-8 -*-
"""
Created on Mon Apr 18 14:17:37 2016

@author: planat
"""

import threading
import json
from datetime import datetime
import logging.config
import rta_constants
from datetime import datetime, date, time
import time
import uuid
import random
import sys
from kafka import KafkaProducer



#SENSORS_ACTIVITY_TYPE   = ["accelerometer","gyroscope","altimeter","ambientLight","barometer","calorie","distance","uv","contact","pedometer"]

#SENSORS_ACTIVITY_TYPE       = ["accelerometer"]
#SENSORS_ACTIVITY_TYPE_EXCEL       = [1]
#SENSORS_ACTIVITY_PERIOD     = [3000]  # in ms
SENSORS_ACTIVITY_TYPE             = ["har_predict_aggr","skinTemperature", "gsr", "heartRate", "rrinterval"]
#SENSORS_ACTIVITY_TYPE_EXCEL       = [1,2,3,4,5]
SENSORS_ACTIVITY_PERIOD           = [1000,1000,1010,1000,1010]  # in ms


#SENSORS_ACTIVITY_TYPE             = ["accelerometer","gyroscope"]
#SENSORS_ACTIVITY_PERIOD           = [1000,2800]  # in ms

#SENSORS_ACTIVITY_TYPE       = ["accelerometer","gyroscope","altimeter"]
#SENSORS_ACTIVITY_TYPE_EXCEL       = [1,2,3]
#SENSORS_ACTIVITY_PERIOD     = [500,3000,5000]  # in ms
ACTIVITY_LIST = ["WALKING","SITTING","WALKING_UP","WALKING_DOWN"]
TEST_DURATION = 5000
TRAFFIC_FILE = "result_excel.csv"
USER_LIST = ["vincent.planat@hpe.com","user2@hpe.com","user3@hpe.com"]


logging.config.fileConfig(rta_constants.PROPERTIES_LOG_FILE)
logger = logging.getLogger()


class testerBuffer:
    def __init__(self):
        self.kafka_producer = 'c4t19764.itcs.hpecorp.net:9092'
        self.kafka_topic = 'iot_har_novelty_detect'

        # kafka client producer (for sending back data result - not control). Used in process_data()
        self.producer = KafkaProducer(bootstrap_servers=self.kafka_producer)

        #self.file_result = open(TRAFFIC_FILE, 'w')

        # Start threading
        threads = []
        for i in range(len(SENSORS_ACTIVITY_TYPE)):
            t = threading.Thread(target=self.worker_dataBuffer,args=(i,),name="processor_%s"%SENSORS_ACTIVITY_TYPE[i])
            threads.append(t)
            t.start()

    def send_message(self,msg_val):
        self.producer.send(self.kafka_topic,  msg_val) 


    def get_ms_timestamp(self):
        delta = datetime.now() - datetime(1970, 1, 1)
        return(delta.total_seconds() * 1000)

        

#producer.send_messages("test", "This is message sent from python client " + str(datetime.now().time()) )
#producer.send_messages("test",  data_string)
    def worker_dataBuffer(self,processor_id):

        # from har_predict_aggr
        # {"eventId": "ce360a04-660b-4600-80b8-74f63398fc4b", "processor_name": "har_predict_aggr", "userid": "vincent.planat@hpe.com", 
        #    "activity": "WALKING_UP", "time_stamp": 1457003525741}
        if processor_id == 0:
            processor_name = "har_predict_aggr"
            period_ms = SENSORS_ACTIVITY_PERIOD[processor_id]
            ref_start_time = datetime.now()
            thread_name = threading.currentThread().getName()
            while (True):   
                logger.debug("Worker:%s   ms:%d" % (thread_name, self.get_ms_timestamp()))
                eventId = str(uuid.uuid4())      
                sleep_duration =  float(period_ms/1000.)  
                time_stamp = self.get_ms_timestamp()
                activity  = ACTIVITY_LIST[random.randint(1,4)-1]
                user_id = USER_LIST[random.randint(1,len(USER_LIST))-1]
                data_json = [ {"eventId" : eventId, "processor_name": processor_name, "userid":user_id, "activity": activity, "time_stamp" : int(time_stamp) } ]
                data_string = json.dumps(data_json)
                self.send_message(data_string)
                #self.file_result.write("%d;%d\n" % (int(time_stamp), SENSORS_ACTIVITY_TYPE_EXCEL[processor_id]))
                delta_process= datetime.now() - ref_start_time
                delta_process_ms = delta_process.total_seconds() * 1000
                if (delta_process_ms > TEST_DURATION):
                    #self.file_result.close()
                    sys,exit(0)    
                time.sleep(sleep_duration)

        # skinTemp        
        # {"eventId":"3b549f48-0d64-496d-8097-f5442468ab1c","deviceType":"msband2","deviceid":"b81e905908354542","eventtype":"skinTemperature",
        #  "timestamp":1456939587501,"userid":"vincent.planat@hpe.com","trainingMode":"SITTING","temperature":30.809999}
        elif processor_id == 1:
            event_type = "skinTemperature"
            training_mode = "SITTING"
            period_ms = SENSORS_ACTIVITY_PERIOD[processor_id]
            ref_start_time = datetime.now()
            thread_name = threading.currentThread().getName()
            while (True):   
                logger.debug("Worker:%s   ms:%d" % (thread_name, self.get_ms_timestamp()))
                eventId = str(uuid.uuid4())      
                sleep_duration =  float(period_ms/1000.)  
                time_stamp = self.get_ms_timestamp()
                temperature  = random.random() * 39
                user_id = USER_LIST[random.randint(1,len(USER_LIST))-1]
                data_json = [ {"eventId" : eventId, "deviceType": "msband2", "deviceid":"b81e905908354542", "eventtype":event_type, "timestamp" : int(time_stamp), "userid":user_id, "trainingMode":training_mode,"temperature": temperature  } ]
                data_string = json.dumps(data_json)
                self.send_message(data_string)
                # self.file_result.write("%d;%d\n" % (int(time_stamp), SENSORS_ACTIVITY_TYPE_EXCEL[processor_id]))
                delta_process= datetime.now() - ref_start_time
                delta_process_ms = delta_process.total_seconds() * 1000
                if (delta_process_ms > TEST_DURATION):
                    #self.file_result.close()
                    sys,exit(0)
                time.sleep(sleep_duration)

        # gsr
        #{"eventId":"1ab78221-847c-4b4f-97ba-3dac5ff333cf","deviceType":"msband2","deviceid":"b81e905908354542","eventtype":"gsr",
        # "timestamp":1456939591481,"userid":"vincent.planat@hpe.com","trainingMode":"SITTING","resistance":340330}
        elif processor_id == 2:
            event_type = "gsr"
            training_mode = "SITTING"
            period_ms = SENSORS_ACTIVITY_PERIOD[processor_id]
            ref_start_time = datetime.now()
            thread_name = threading.currentThread().getName()
            while (True):   
                logger.debug("Worker:%s   ms:%d" % (thread_name, self.get_ms_timestamp()))
                eventId = str(uuid.uuid4())      
                sleep_duration =  float(period_ms/1000.)  
                time_stamp = self.get_ms_timestamp()
                resistance  = random.randint(335000, 342000)
                user_id = USER_LIST[random.randint(1,len(USER_LIST))-1]
                data_json = [ {"eventId" : eventId, "deviceType": "msband2", "deviceid":"b81e905908354542", "eventtype":event_type, "timestamp" : int(time_stamp), "userid":user_id, "trainingMode":training_mode,"resistance": resistance  } ]
                data_string = json.dumps(data_json)
                self.send_message(data_string)
                # self.file_result.write("%d;%d\n" % (int(time_stamp), SENSORS_ACTIVITY_TYPE_EXCEL[processor_id]))
                delta_process= datetime.now() - ref_start_time
                delta_process_ms = delta_process.total_seconds() * 1000
                if (delta_process_ms > TEST_DURATION):
                    #self.file_result.close()
                    sys,exit(0)
                time.sleep(sleep_duration)

        # heartRate
        #{"eventId":"7c573cbd-510f-4361-9282-4f3616b27e20","deviceType":"msband2","deviceid":"b81e905908354542","eventtype":"heartRate",
        # "timestamp":1456939604898,"userid":"vincent.planat@hpe.com","trainingMode":"SITTING","rate":"85","quality":0}
        elif processor_id == 3:
            event_type = "heartRate"
            training_mode = "SITTING"
            period_ms = SENSORS_ACTIVITY_PERIOD[processor_id]
            ref_start_time = datetime.now()
            thread_name = threading.currentThread().getName()
            while (True):   
                logger.debug("Worker:%s   ms:%d" % (thread_name, self.get_ms_timestamp()))
                eventId = str(uuid.uuid4())      
                sleep_duration =  float(period_ms/1000.)  
                time_stamp = self.get_ms_timestamp()
                rate  = random.randint(60,90)
                quality = random.randint(0,1)
                user_id = USER_LIST[random.randint(1,len(USER_LIST))-1]
                data_json = [ {"eventId" : eventId, "deviceType": "msband2", "deviceid":"b81e905908354542", "eventtype":event_type, "timestamp" : int(time_stamp), "userid":user_id, "trainingMode":training_mode,"rate": rate, "quality": quality  } ]
                data_string = json.dumps(data_json)
                self.send_message(data_string)
                # self.file_result.write("%d;%d\n" % (int(time_stamp), SENSORS_ACTIVITY_TYPE_EXCEL[processor_id]))
                delta_process= datetime.now() - ref_start_time
                delta_process_ms = delta_process.total_seconds() * 1000
                if (delta_process_ms > TEST_DURATION):
                    #self.file_result.close()
                    sys,exit(0)
                time.sleep(sleep_duration)

        # rrinterval
          # {"eventId":"dc5f7142-0efa-4998-a862-784bd0f8720d","deviceType":"msband2","deviceid":"b81e905908354542","eventtype":"rrinterval",
          # "timestamp":1456939644347,"userid":"vincent.planat@hpe.com","trainingMode":"SITTING","interval":0.597312}
        elif processor_id == 4:
            event_type = "rrinterval"
            training_mode = "SITTING"
            period_ms = SENSORS_ACTIVITY_PERIOD[processor_id]
            ref_start_time = datetime.now()
            thread_name = threading.currentThread().getName()
            while (True):   
                logger.debug("Worker:%s   ms:%d" % (thread_name, self.get_ms_timestamp()))
                eventId = str(uuid.uuid4())      
                sleep_duration =  float(period_ms/1000.)  
                time_stamp = self.get_ms_timestamp()
                interval  = random.uniform(0.5, 1.5)
                user_id = USER_LIST[random.randint(1,len(USER_LIST))-1]
                data_json = [ {"eventId" : eventId, "deviceType": "msband2", "deviceid":"b81e905908354542", "eventtype":event_type, "timestamp" : int(time_stamp), "userid":user_id, "trainingMode":training_mode,"interval": interval  } ]
                data_string = json.dumps(data_json)
                self.send_message(data_string)
                # self.file_result.write("%d;%d\n" % (int(time_stamp), SENSORS_ACTIVITY_TYPE_EXCEL[processor_id]))
                delta_process= datetime.now() - ref_start_time
                delta_process_ms = delta_process.total_seconds() * 1000
                if (delta_process_ms > TEST_DURATION):
                    #self.file_result.close()
                    sys,exit(0)
                time.sleep(sleep_duration)

        else:
            print "not coded yet"                

my_tester = testerBuffer()
        
