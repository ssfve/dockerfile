# -*- coding: utf-8 -*-
"""
Created on Wed May 18 15:05:27 2016

@author: planat
"""

import subprocess

KAFKA_PATH = "/opt/mount1/kafka_2.10-0.9.0.0/"

kafka_cmd_list_topics = [KAFKA_PATH+"bin/kafka-topics.sh","--list","--zookeeper","localhost:2181"]
proc = subprocess.Popen(kafka_cmd_list_topics, 
                        stdout=subprocess.PIPE,
                        )
(proc_stdout, proc_err) = proc.communicate()

print ("proc-stdout:%s" % proc_stdout)
