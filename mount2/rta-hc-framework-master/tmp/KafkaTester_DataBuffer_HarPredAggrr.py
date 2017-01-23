# -*- coding: utf-8 -*-
"""
Created on Mon Apr 18 14:17:37 2016

@author: planat
"""

from kafka import KafkaClient, SimpleProducer
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


#SENSORS_ACTIVITY_TYPE   = ["accelerometer","gyroscope","altimeter","ambientLight","barometer","calorie","distance","uv","contact","pedometer"]

#SENSORS_ACTIVITY_TYPE       = ["accelerometer"]
#SENSORS_ACTIVITY_TYPE_EXCEL       = [1]
#SENSORS_ACTIVITY_PERIOD     = [3000]  # in ms
SENSORS_ACTIVITY_TYPE             = ["accelerometer","gyroscope"]
SENSORS_ACTIVITY_TYPE_EXCEL       = [1,2]
SENSORS_ACTIVITY_PERIOD           = [1000,2800]  # in ms
#SENSORS_ACTIVITY_TYPE       = ["accelerometer","gyroscope","altimeter"]
#SENSORS_ACTIVITY_TYPE_EXCEL       = [1,2,3]
#SENSORS_ACTIVITY_PERIOD     = [500,3000,5000]  # in ms
ACTIVITY_LIST = ["WALKING","SITTING","WALKING_UP","WALKING_DOWN"]
TEST_DURATION = 25000
TRAFFIC_FILE = "result_excel.csv"
USER_LIST = ["vincent.planat@hpe.com","user2@hpe.com","user3@hpe.com"]


logging.config.fileConfig(rta_constants.PROPERTIES_LOG_FILE)
logger = logging.getLogger()


class testerBuffer:
    def __init__(self):
        self.kafka_producer = 'c4t19764.itcs.hpecorp.net:9092'
        self.kafka_topic = 'iot_har_predict_aggr'

        kafka =  KafkaClient(self.kafka_producer)
        self.producer = SimpleProducer(kafka)

        self.file_result = open(TRAFFIC_FILE, 'w')


        # Start threading
        threads = []
        for i in range(len(SENSORS_ACTIVITY_TYPE)):
            t = threading.Thread(target=self.worker_dataBuffer,args=(i,),name="processor_%s"%SENSORS_ACTIVITY_TYPE[i])
            threads.append(t)
            t.start()

    def send_message(self,msg_val):
        self.producer.send_messages(self.kafka_topic,  msg_val) 


    def get_ms_timestamp(self):
        delta = datetime.now() - datetime(1970, 1, 1)
        return(delta.total_seconds() * 1000)

        

#producer.send_messages("test", "This is message sent from python client " + str(datetime.now().time()) )
#producer.send_messages("test",  data_string)
    def worker_dataBuffer(self,processor_id):
        # {"eventId" : "UIID-value", "processor_name": "har_randomforest_accelerometer", "time_stamp" : 1457003525741, 
        # "userid":vincent.planat@hpe.com”, "result", "WALKING" }
        processor_name = "har_randomforest_%s" % SENSORS_ACTIVITY_TYPE[processor_id]
        period_ms = SENSORS_ACTIVITY_PERIOD[processor_id]
        ref_start_time = datetime.now()
        thread_name = threading.currentThread().getName()
        while (True):   
            logger.debug("Worker:%s   ms:%d" % (thread_name, self.get_ms_timestamp()))
            eventId = str(uuid.uuid4())      
            sleep_duration =  float(period_ms/1000.)  
            time_stamp = self.get_ms_timestamp()
            result  = ACTIVITY_LIST[random.randint(1,4)-1]
            user_id = USER_LIST[random.randint(1,len(USER_LIST))-1]
            data_json = [ {"eventId" : eventId, "processor_name": processor_name, "time_stamp" : int(time_stamp), "userid":user_id, "result": result } ]
            #data_json = [ { 'a':'A', 'b':(2, 4), 'c':3.0 } ]
            data_string = json.dumps(data_json)
            self.send_message(data_string)
            self.file_result.write("%d;%d\n" % (int(time_stamp), SENSORS_ACTIVITY_TYPE_EXCEL[processor_id]))
            delta_process= datetime.now() - ref_start_time
            delta_process_ms = delta_process.total_seconds() * 1000
            if (delta_process_ms > TEST_DURATION):
                self.file_result.close()
                sys,exit(0)

            time.sleep(sleep_duration)
                

my_tester = testerBuffer()
        
