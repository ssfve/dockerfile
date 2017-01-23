# -*- coding: utf-8 -*-
"""
Author: Wu Jun-Yi(junyi.wu@hpe.com)
Creation Date: 2016-09-29
Purpose: To manage all of the processors start and stop from cmd line
"""

import cmd
import os
import subprocess
import rta_constants
import logging
import logging.config
import sys
import ConfigParser
from flask import request
import psutil
from flask import Flask, jsonify, render_template
import socket
import time
import signal
import ctypes
# from websocket import create_connection
import threading
import multiprocessing

libc = ctypes.CDLL("libc.so.6")


class TailThread(threading.Thread):
    def __init__(self,processor):
        threading.Thread.__init__(self)
        self.processor = processor
        # self.saved_file = saved_file
        # self.what_data = what_data

    def run(self):
        try:
            tail_job = ProcessWeb()
            tail_job.do_tail(self.processor)
        except Exception, e:
            print e

    def stop(self):
        self.thread_stop = True

class ProcessInfo:
    process_ls = []
    def __init__(self,name):
        self.name = name
        self.search_result = 0
        self.search_criteria_list = []
        self.pid = ''
    
    '''
        The index is the index in the list of the psutil cmdline() list. 
        From 0 --> len(cmdline()-1)
    '''
    def get_host_name(self):
        return socket.gethostname()

    
    def addSearchCriteria(self,index,regex):
        search_criteria = {}
        search_criteria["index"] = index
        search_criteria["regex"] = regex        
        self.search_criteria_list.append(search_criteria)

    def incrementSearchResult(self):
        self.search_result += 1;

    def getSearchCriteriaList(self):
        return self.search_criteria_list

    def check_host_is_exist(self):
        config_parser = ConfigParser.ConfigParser()
        config_parser.read(rta_constants.PROPERTIES_FILE)
        valid_monitoring_list = config_parser.get(rta_constants.PLATFORM_MON, "hosts_list")
        host_name = self.get_host_name()
        # print host_name
        # print type(valid_monitoring_list)
        valid_monitoring_list = eval(valid_monitoring_list)
        # print valid_monitoring_list['hosts_list']
        valid_hosts_list = []
        hosts_mapping = {}
        for item in valid_monitoring_list['hosts_list']:
            valid_hosts_list.append(item['hostname'])
            hosts_mapping[item['hostname']] = item['procs_profile']

        # print hosts_mapping
        # print valid_hosts_list

        if host_name in valid_hosts_list:
            return True
        else:
            return False

    def handle_parameter(self):
        config_parser = ConfigParser.ConfigParser()
        config_parser.read(rta_constants.PROPERTIES_FILE)
        valid_monitoring_list = config_parser.get(rta_constants.PLATFORM_MON, "hosts_list")
        host_name = self.get_host_name()
        # print host_name
        # print type(valid_monitoring_list)
        valid_monitoring_list = eval(valid_monitoring_list)
        # print valid_monitoring_list['hosts_list']
        valid_hosts_list = []
        hosts_mapping = {}
        for item in valid_monitoring_list['hosts_list']:
            valid_hosts_list.append(item['hostname'])
            hosts_mapping[item['hostname']] = item['procs_profile']

        if hosts_mapping.has_key(host_name):
            # vpl 09/11
            #property_file_type = hosts_mapping[host_name].split('-')
            #file_name = 'rta_'+property_file_type[0]+'_'+property_file_type[1]+'.properties'
            file_name = 'rta_'+hosts_mapping[host_name]+'.properties'
            file_path = rta_constants.PROPERTIES_FILE_PATH+file_name
            file_object = open(file_path)
            try:
                all_the_text = file_object.read()
                process_dict = eval(all_the_text)
            finally:
                file_object.close()

            process_ls = []
            # provision the process to monitor
            process_list = []
            process_list.append(host_name)

            for k,v in process_dict.items():
                if v[0] == 1:
                    process_ls.append({k:v})
            # print (process_ls)

            for item in process_ls:
                for k,v in item.items():
                    obj_name = ProcessInfo(k)
                    for i in range(1,len(v)):
                        obj_name.addSearchCriteria(v[i]['index'],v[i]['regex'])
                    process_list.append(obj_name)
            # need to add the other process here
            return process_list
        else:
            return False

    def extract_process(self,process_list):
        ####################################################################
        # Load all the running process
        running_procs = []
        for p in psutil.process_iter():
            running_procs.append(p)

        # Scan all the running process
        for run_proc in running_procs:
            try:
                proc_cmdline = run_proc.cmdline()
                pid = run_proc.pid
                # print ("testing cmdLine\n%s" % proc_cmdline)
                
                # Scan all the processInfo instance and check if matchs with run_proc
                for proc_val in process_list:
                    # retrieve the list of search criteria
                    search_criteria_list = proc_val.getSearchCriteriaList()

                    # for each of them is it matching the proc_cmdLine value ?
                    # a criteria_val is a dict.["index"] and "regex"]
                    # if all the criteria in search_criteria_list matches then we founded
                    success_count = 0
                    for criteria_val in search_criteria_list:
                        # print("criterial_val[index]:%d     criterial_val[regex]:%s" %(criteria_val["index"],criteria_val["regex"]))
                    
                        # check if the len of the proc_cmdline is enough for adressing the criteria_val["index"]
                        #    and matching criteria
                        if ((len(proc_cmdline) >= (criteria_val["index"]+1)) and (proc_cmdline[criteria_val["index"]].find(criteria_val["regex"]))>=0):
                            #print("the process:%s is matching criteria_val:%s" % (proc_cmdline,criteria_val))
                            success_count += 1
                    
                    # if I have the same number of success_count as the number of search_criteria 
                    # then I increment the searchResult count for the processInfo object
                    if success_count == len(search_criteria_list):
                        #print("all criteria for process:%s are mapping" %proc_val.name)
                        proc_val.incrementSearchResult()
                        # print 'pid is here ####'
                        # print pid
                        proc_val.pid = pid
                    
            except Exception as ex:
                print("    Failed to run process cmdline iteration with ERROR(%s).", str(ex))
                sys.exit(1)
        return process_list

class ProcessWeb():
    config_parser = ConfigParser.ConfigParser()
    config_parser.read(rta_constants.PROPERTIES_FILE)
    spark_master_url = config_parser.get(rta_constants.FRAMEWORK_NAME, "spark.master_url")
    general_path_project = config_parser.get(rta_constants.FRAMEWORK_NAME, "path.general.project")
    general_path_log = general_path_project+'/log'
    accl_log = general_path_log +'/'+ config_parser.get(rta_constants.FRAMEWORK_NAME, "name.accl.log")
    gyro_log = general_path_log +'/'+ config_parser.get(rta_constants.FRAMEWORK_NAME, "name.gyro.log")
    baro_log = general_path_log +'/'+ config_parser.get(rta_constants.FRAMEWORK_NAME, "name.baro.log")
    aggr_log = general_path_log +'/'+ config_parser.get(rta_constants.FRAMEWORK_NAME, "name.aggr.log")
    raw_writer_log = general_path_log +'/'+ config_parser.get(rta_constants.FRAMEWORK_NAME, "name.raw.writer.log")
    novelty_log = general_path_log +'/'+ config_parser.get(rta_constants.FRAMEWORK_NAME, "name.novelty.log")
    default_log = general_path_log +'/'+ config_parser.get(rta_constants.FRAMEWORK_NAME, "name.default.log")

    # general_path_project = '/opt/rta_hc/rta-hc-framework-master'
    # # log files setting
    # general_path_log = general_path_project+'/log/'
    # accl_log = general_path_log + 'rta_processor_accel.log'
    # gyro_log = general_path_log + 'rta_processor_gyro.log'
    # baro_log = general_path_log + 'rta_processor_baro.log'
    # aggr_log = general_path_log + 'har_predict_aggr_ensemble.log'
    # raw_writer_log = general_path_log + 'raw_writer.log'
    # novelty_log = general_path_log + 'novelty_detect.log'
    # default_log = general_path_log + 'rta.log'

    # processor install path setting
    general_path_hadoop = ''
    general_path_spark = config_parser.get(rta_constants.FRAMEWORK_NAME, "path.spark")
    general_path_kafka = config_parser.get(rta_constants.FRAMEWORK_NAME, "path.kafka")
    general_path_kafka_properties = 'config/server.properties'
    general_path_zookeeper = config_parser.get(rta_constants.FRAMEWORK_NAME, "path.zookeeper")
    general_path_zookeeper_properties = 'config/zookeeper.properties'
    general_path_rta_pid = config_parser.get(rta_constants.FRAMEWORK_NAME, "path.rta.pid")
    general_path_kairosDB = config_parser.get(rta_constants.FRAMEWORK_NAME, "path.kairosDB")
    general_path_tomcat = config_parser.get(rta_constants.FRAMEWORK_NAME, "path.tomcat")

    cmd_start_kafka = general_path_kafka+'/bin/kafka-server-start.sh'+' '+general_path_kafka+'/'+general_path_kafka_properties+' &'
    cmd_stop_kafka = general_path_kafka+'/bin/kafka-server-stop.sh'+' '+general_path_kafka+'/'+general_path_kafka_properties+' &'

    cmd_start_zookeeper = general_path_zookeeper+'/bin/zookeeper-server-start.sh'+' '+general_path_zookeeper+'/'+general_path_zookeeper_properties+' &'
    cmd_stop_zookeeper = general_path_zookeeper+'/bin/zookeeper-server-stop.sh'

    cmd_start_spark = general_path_spark+'/sbin/start-all.sh'
    cmd_stop_spark = general_path_spark+'/sbin/stop-all.sh'

    cmd_start_cassandra = 'cassandra &'
    cmd_stop_cassandra = 'ps -ef | grep "cassandra.service.CassandraDaemon" | grep -v grep | awk "{print $1}"'

    cmd_start_kairosDB = general_path_kairosDB+'/bin/kairosdb.sh start'
    cmd_stop_kairosDB = general_path_kairosDB+'/bin/kairosdb.sh stop'

    cmd_start_grafana = 'sudo service grafana-server start'
    cmd_stop_grafana = 'sudo service grafana-server stop'

    cmd_start_tomcat = general_path_tomcat + '/bin/catalina.sh start'
    cmd_stop_tomcat = general_path_tomcat + '/bin/catalina.sh stop'
    # ps ax | grep -i 'catalina' | grep -v grep | awk '{print $1}'

    cmd_start_flask =  general_path_project+'/src/'+ 'python platform_mngt_web.py'
    
    cmd_stop_spark_master = general_path_spark+'/sbin/stop-master.sh'
    cmd_start_spark_master = general_path_spark+'/sbin/start-master.sh'
    cmd_stop_spark_worker = general_path_spark+'/sbin/stop-slaves.sh'
    cmd_start_spark_worker = general_path_spark+'/sbin/start-slaves.sh'
    cmd_start_accl_processor = 'python '+general_path_project+'/src/rta_wrapper.py -sh "'+general_path_project+'" -sn "rta_processor_simple_1_1.py accelerometer sklearn"'+' 1>../log/'+accl_log+' 2>&1'
    # cmd_start_accl_processor = '/opt/mount1/spark-1.6.1-bin-hadoop2.6/bin/spark-submit --master spark://16.250.7.135:7077 --executor-memory 2G --driver-memory 512M --total-executor-cores 1 --jars /opt/mount1/rta-hc/integration/rta-hc-framework-master/libs/spark-streaming-kafka-assembly_2.10-1.6.0.jar /opt/mount1/rta-hc/integration/rta-hc-framework-master/src/rta_processor_simple_1_1.py accelerometer sklearn'
    cmd_stop_accl_processor = "/bin/bash -c 'kill -s SIGTERM `cat "+general_path_rta_pid+"/rta_processor_simple_1_1_accelerometer_sklearn.pid"+"`'"
    cmd_start_gyro_processor = 'python '+general_path_project+'/src/rta_wrapper.py -sh "'+general_path_project+'" -sn "rta_processor_simple_1_1.py gyroscope sklearn"'+' 1>../log/'+gyro_log+' 2>&1'
    cmd_stop_gyro_processor = "/bin/bash -c 'kill -s SIGTERM `cat "+general_path_rta_pid+"/rta_processor_simple_1_1_gyroscope_sklearn.pid"+"`'"
    cmd_start_baro_processor = 'python '+general_path_project+'/src/rta_wrapper.py -sh "'+general_path_project+'" -sn "rta_processor_simple_1_1.py barometer sklearn"'+' 1>../log/'+baro_log+' 2>&1'
    cmd_stop_baro_processor = "/bin/bash -c 'kill -s SIGTERM `cat "+general_path_rta_pid+"/rta_processor_simple_1_1_barometer_sklearn.pid"+"`'"
    cmd_start_aggr_naiv = 'python '+general_path_project+'/src/rta_wrapper.py -sh "'+general_path_project+'" -sn "har_predict_aggr_ensemble_1_1.py naivebayes"'+' 1>../log/'+aggr_log+' 2>&1'
    cmd_stop_aggr_naiv = "/bin/bash -c 'kill -s SIGTERM `cat "+general_path_rta_pid+"/har_predict_aggr_ensemble_1_1_naivebayes.pid"+"`'"

    cmd_start_raw_writer = general_path_spark+"/bin/spark-submit --master spark://10.3.35.93:7077 --executor-memory 6G --driver-memory 512M --total-executor-cores 3 --jars "+general_path_project+"/libs/spark-streaming-kafka-assembly_2.10-1.6.0.jar "+general_path_project+"/src/raw_writer.py 1>../log/"+raw_writer_log+" 2>&1 &"
    cmd_stop_raw_writer = "ps ax |grep -i 'java' |grep -i 'raw_writer.py' | grep -v grep | awk '{print $1}'"
    cmd_start_novelty_detector = general_path_spark+'/bin/spark-submit --master spark://16.254.5.214:7077 --executor-memory 4G  --driver-memory 512M --total-executor-cores 1 --jars "../libs/spark-streaming-kafka-assembly_2.10-1.6.0.jar" --py-files "rta_constants.py,rta_datasets.py" '+general_path_project+'/src/novelty_detect.py 1>../log/'+novelty_log+' 2>&1 &'
    cmd_stop_novelty_detector ="ps ax |grep -i 'java' |grep -i 'novelty_detect.py' | grep -v grep | awk '{print $1}'"

    def shutdown_server(self):
        func = request.environ.get('werkzeug.server.shutdown')
        print func
        if func is None:
            raise RuntimeError('Not running with the Werkzeug Server')
        func()

    def mapping_covert(self,processor):
        mapping_list = {    
                'spark<spark_master>':'spark',
                'spark<spark_worker>':'spark',
                'kafka':'kafka',
                'zookeeper':'zookeeper',
                'cassandra':'cassandra',
                'kairosDb':'kairosDb',
                'grafana':'grafana',
                'tomcat':'tomcat',
                'raw_writer':'raw_writer',
                'novelty':'novelty',
                'accl_processor':'accl_processor',
                'baro_processor':'baro_processor',
                'gyro_processor':'gyro_processor',
                'aggr_processor':'aggr_processor',
        }
        if mapping_list.has_key(processor):
            return mapping_list[processor]
        else:
            return False

    def construct_logger(self,in_logger_file_path):
        """Instantiate and construct logger object based on log properties file by default. Otherwise logger object will be
        constructed with default properties.
        Args:
            in_logger_dir_path (str): path followed by file name where logger properties/configuration file resides
        Returns:
            logger object
        """
        if os.path.exists(in_logger_file_path):
            logging.config.fileConfig(in_logger_file_path)
            logger = logging.getLogger(os.path.basename(__file__))
        else:
            # If logger property/configuration file doesn't exist,
            # and logger object will be constructed with default properties.
            logger = logging.getLogger(os.path.basename(__file__))
            logger.setLevel(logging.DEBUG)
            # Create a new logger file
            logger_file_path_object = open(in_logger_file_path, 'a+')
            logger_file_path_object.close()
            # create a file handler
            handler = logging.FileHandler(in_logger_file_path)
            handler.setLevel(logging.INFO)
            # create a logging format
            formatter = logging.Formatter('[%(asctime)s - %(name)s - %(levelname)s] %(message)s')
            handler.setFormatter(formatter)
            # add the handlers to the logger
            logger.addHandler(handler)
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.DEBUG)
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
            logger.warning("The logger configuration file %s doesn't exist, "
                            "so logger object will be constructed with default properties.", in_logger_file_path)
        return logger

    def get_running_status(self):
        """get currenly running processor list
        Returns:
            False - this list is null and not
            list = list of processors
        """
        obj = ProcessInfo('jobs')
        process_list = obj.handle_parameter()
        if process_list:
            # get the hostname
            hostname = process_list[0]
            del process_list[0]
            process_list = obj.extract_process(process_list)
            # print 'dict is here$$$$$'
            dict_processor = []
            for proc_val in process_list:
                if proc_val.search_result ==0:
                    dict_processor.append({'processor':proc_val.name,'status':'Stopped','PID':str(proc_val.pid)})

                elif proc_val.search_result >=1:
                    dict_processor.append({'processor':proc_val.name,'status':'Running','PID':str(proc_val.pid)})
                    # dict_processor[proc_val.name] = 'Running'
                # print ("|%-20s|%-5s|"%(proc_val.name,proc_val.search_result))
            # print dict_processor
            return dict_processor
        else:
            return False

    def do_list(self,line):
        """list
        list all the configured processor status
        """
        app_logger = self.construct_logger(rta_constants.PROPERTIES_LOG_FILE)
        obj = ProcessInfo('jobs')
        process_list = obj.handle_parameter()
    
        if process_list:
            # get the hostname
            hostname = process_list[0]
            del process_list[0]
            process_list = obj.extract_process(process_list)
            # print 'dict is here$$$$$'
            # sys.exit(1)
            dict_processor = []
            for proc_val in process_list:
                if proc_val.search_result ==0:
                    dict_processor.append({'processor':proc_val.name,'status':'Stopped','PID':str(proc_val.pid)})

                elif proc_val.search_result >=1:
                    dict_processor.append({'processor':proc_val.name,'status':'Running','PID':str(proc_val.pid)})
                    # dict_processor[proc_val.name] = 'Running'
                # print ("|%-20s|%-5s|"%(proc_val.name,proc_val.search_result))
            # print dict_processor
            print('##############################################')
            print('PID  #'+' Processor                    #'+' Status')
            print('##############################################')
            spark_ls = []
            for processor in dict_processor:
                if processor.get('processor') == 'spark<spark_worker>' or processor.get('processor') == 'spark<spark_master>':
                    spark_ls.append(processor)
                    del dict_processor[dict_processor.index(processor)]
            # print dict_processor
            for processor in dict_processor:
                space_pid = 7 - len(processor.get('PID'))
                space_name = 30 - len(processor.get('processor'))
                print str(processor.get('PID'))+space_pid*' '+processor.get('processor') + space_name*' '+ processor.get('status')
                    # space_num = 30 - len(k)
                    # print k + space_num*' '+v
            print 7*' '+'spark'
            for item in spark_ls:
                space_pid = 8 - len(item.get('PID'))
                space_name = 29 - len(item.get('processor').split('<')[1].split('>')[0])
                print str(item.get('PID'))+space_pid*' '+item.get('processor').split('<')[1].split('>')[0] + space_name*' '+ item.get('status')
            print('##############################################')
        else:
            print("cmd is not support from this host")

    def set_pdeathsig(self,sig=signal.SIGTERM):
        def callable():
            return libc.prctl(1, sig)
        return callable

    # tail the log file refer to log file type
    def do_tail(self,processor):
        if processor == 'accl_processor':
            logfile = self.accl_log
        elif processor == 'baro_processor':
            logfile = self.baro_log
        elif processor == 'gyro_processor':
            logfile = self.gyro_log
        elif processor == 'aggr_processor':
            logfile = self.aggr_log
        elif processor == 'raw_writer':
            logfile = self.raw_writer_log
        elif processor == 'novelty':
            logfile = self.novelty_log
        else:
            logfile = self.default_log
        
        config_parser = ConfigParser.ConfigParser()
        config_parser.read(rta_constants.PROPERTIES_FILE)
        log_lines = config_parser.get(rta_constants.PLATFORM_MON, "log_lines")

        p = subprocess.Popen(['tail','-'+str(log_lines),logfile],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=False)
        stdout,stderr = p.communicate()
        return stdout
        # proc = subprocess.Popen(["tail","-f",logfile],stdout=subprocess.PIPE, shell=True)
        # print('server connected')
        # ws_server = "ws://"+socket.gethostbyname(socket.gethostname())+":8000/websocket/"
        # ws = create_connection(ws_server)   # create websocket connection
        # print 'output tail -f'
        
        # for line in iter(proc.stdout.readline,''):
        #     print line
        #     time.sleep(1)                           # Don't need this just shows the text streaming
        #     yield line.rstrip()# 
            
        # for line in info:  #按行遍历
        #     line = line.strip('\r\n')
        #     print line
        # with p.stdout:
        #     for line in iter(p.stdout.readline, b''):
        #         print line
        # p.wait()
        # p = 0
        # while True:
        #     f = open("log.txt", "r+")
        #     f1 = open("result.txt", "a+")
     
        #     #定位指针
        #     f.seek(p, 0)
     
        #     filelist = f.readlines()
        #     if filelist:
        #         for line in filelist:
        #             #对行内容进行操作
        #             f1.write(line*10)
        #             print line
     
        #     #获取文件当前位置
        #     p = f.tell()

        #     print 'now p ', p
        #     f.close()
        #     f1.close()
        #     time.sleep(1)

    def do_start(self,processor):
        """start [processor]
        start the name of processor
        available processor list
        [spark]          -->  Engine data processing
        [kafka]          -->  Data pipelines and streaming
        [flask]          -->  Integration webserver
        [zookeeper]      -->  Zookeeper central service
        [cassandra]      -->  Cassandra real-time database
        [kairosDb]       -->  Time Series Database on Cassandra
        [grafana]        -->  Grafana realtime series dashboard
        [tomcat]         -->  Java servlet server
        [raw_writer]     -->  Raw data writer on cassandra
        [novelty]        -->  Novelty detection for Healthcare
        [accl_processor] -->  Accelerometer HAR classifier
        [baro_processor] -->  Barometer HAR classifier
        [gyro_processor] -->  Gyroscope HAR classifier 
        [aggr_processor] -->  Aggregation HAR classifier
        """
        app_logger = self.construct_logger(rta_constants.PROPERTIES_LOG_FILE)
        running_dict = {}
        for item in self.get_running_status():
            running_dict[item.get('processor')]=item.get('status')

        if processor == 'spark':
            if running_dict:
                if running_dict['spark<spark_worker>'] != 'Running' and running_dict['spark<spark_master>'] != 'Running':
                    try:
                        cmd_line = self.cmd_start_spark
                        cmd = subprocess.Popen([cmd_line],shell=True,stdout=subprocess.PIPE)
                        (output,err) = cmd.communicate()
                        # app_logger.info('*********output logging **************')
                        print(output)
                        return('spark has been started!')
                    except Exception as ex:
                        return("    Failed to run processor with ERROR(%s).", str(ex))
                        sys.exit(1)
                else:
                    if running_dict['spark<spark_worker>'] == 'Running' or running_dict['spark<spark_master>'] == 'Running':
                        return('Spark Server is running!! please trying to stop it before it starts.')
                        
            else:
                return('You don\'t have permmission to run command from this host.')
                

        elif processor == 'tomcat':
            if running_dict.has_key('tomcat') and running_dict['tomcat'] != 'Running':
                try:
                    cmd_line = self.cmd_start_tomcat
                    # print('staring tomcat server------->')
                    # print cmd_line
                    cmd = subprocess.Popen([cmd_line],shell=True,stderr=subprocess.PIPE)
                    (output,err) = cmd.communicate()
                    
                    # app_logger.info('*********output logging **************')
                    print(output)
                    return('tomcat has been started!')
                except Exception as ex:
                    return("    Failed to run processor with ERROR(%s).", str(ex))
                    sys.exit(1)
            else:
                if not running_dict.has_key('tomcat'):
                    return('You don\'t have permmission to run command from this host.')
                    
                else:
                    return('Tomcat Server is running!! please trying to stop it before it start.')
                    
        elif processor == 'flask':
            if running_dict.has_key('flask') and running_dict['flask'] != 'Running':
                try:
                    cmd_line = self.cmd_start_flask
                    # print('staring tomcat server------->')
                    # print cmd_line
                    cmd = subprocess.Popen([cmd_line],shell=True,stderr=subprocess.PIPE)
                    (output,err) = cmd.communicate()
                    
                    # app_logger.info('*********output logging **************')
                    print(output)
                    return('flask webserver has been started!')
                except Exception as ex:
                    return("    Failed to run processor with ERROR(%s).", str(ex))
                    sys.exit(1)
            else:
                if not running_dict.has_key('flask'):
                    return('You don\'t have permmission to run command from this host.')
                    
                else:
                    return('Flask webserver is running!! please trying to stop it before it start.')

        elif processor == 'novelty':
            if running_dict.has_key('novelty') and running_dict['novelty'] != 'Running' and running_dict['spark<spark_worker>'] == 'Running' and running_dict['spark<spark_master>'] == 'Running':
                try:
                    cmd_line = self.cmd_start_novelty_detector
                    # print('staring novelty------->')
                    # print cmd_line
                    cmd = subprocess.Popen([cmd_line],shell=True,stderr=subprocess.PIPE)
                    # (output,err) = cmd.communicate()
                    
                    # app_logger.info('*********output logging **************')
                    return('novelty has been started!')
                    
                except Exception as ex:
                    return("    Failed to run processor with ERROR(%s).", str(ex))
                    sys.exit(1)
            else:
                if not running_dict.has_key('novelty'):
                    return('You don\'t have permmission to run command from this host.')
                    
                elif running_dict['novelty'] == 'Running':
                    return('novelty processor is running!! please trying to stop it before it start.')
                    
                elif running_dict['spark<spark_worker>'] == 'Stopped' or running_dict['spark<spark_master>'] == 'Stopped':
                    return('Please start spark first!')
                    

        elif processor == 'raw_writer':
            if running_dict.has_key('raw_writer') and running_dict['raw_writer'] != 'Running' and running_dict['spark<spark_worker>'] == 'Running' and running_dict['spark<spark_master>'] == 'Running':
                try:
                    cmd_line = self.cmd_start_raw_writer
                    # print('staring raw_writer------->')
                    # print cmd_line
                    cmd = subprocess.Popen([cmd_line],shell=True,stderr=subprocess.PIPE)
                    # (output,err) = cmd.communicate()
                    
                    # app_logger.info('*********output logging **************')
                    # print(output)
                    return('raw_writer has been started!')
                except Exception as ex:
                    return("    Failed to run processor with ERROR(%s).", str(ex))
                    sys.exit(1)
            else:
                if not running_dict.has_key('raw_writer'):
                    return('You don\'t have permmission to run command from this host.')
                    
                elif running_dict['raw_writer'] == 'Running':
                    return('raw_writer processor is running!! please trying to stop it before it start.')
                    
                elif running_dict['spark<spark_worker>'] == 'Stopped' or running_dict['spark<spark_master>'] == 'Stopped':
                    return('Please start spark first!')
                    

        elif processor == 'cassandra':
            if running_dict.has_key('cassandra') and running_dict['cassandra'] != 'Running':
                try:
                    cmd_line = self.cmd_start_cassandra
                    # print('starting cassandra------->')
                    # print cmd_line
                    cmd = subprocess.Popen([cmd_line],shell=True,stderr=subprocess.PIPE)
                    # (output,err) = cmd.communicate()
                    
                    # app_logger.info('*********output logging **************')
                    # print(output)
                    return ('cassandra has been started!')
                except Exception as ex:
                    return("    Failed to run processor with ERROR(%s).", str(ex))
                    sys.exit(1)
            else:
                if not running_dict.has_key('cassandra'):
                    return('You don\'t have permmission to run command from this host.')
                    
                else:
                    return('cassandra Server is running!! please trying to stop it before it start.')
                    

        elif processor == 'kairosDb':
            if running_dict.has_key('kairosDb') and running_dict['kairosDb'] != 'Running' and running_dict['cassandra']=='Running':
                try:
                    cmd_line = self.cmd_start_kairosDB
                    # print('staring kairosDB------->')
                    # print cmd_line
                    cmd = subprocess.Popen([cmd_line],shell=True,stderr=subprocess.PIPE)
                    (output,err) = cmd.communicate()
                    
                    # app_logger.info('*********output logging **************')
                    return('kairosDb has been started!')
                    
                except Exception as ex:
                    return("    Failed to run processor with ERROR(%s).", str(ex))
                    sys.exit(1)
            else:
                if not running_dict.has_key('kairosDb'):
                    return('You don\'t have permmission to run command from this host.')
                    
                elif running_dict['cassandra']=='Stopped':
                    return('cassandra required starting before kairosDb is running!')
                     
                elif running_dict['kairosDB'] == 'Running':
                    return('kairosDB Server is running!! please trying to stop it before it starts.')
                    

        elif processor == 'grafana':
            if running_dict.has_key('grafana') and running_dict['grafana'] != 'Running' and running_dict['kairosDb']=='Running':
                try:
                    cmd_line = self.cmd_start_grafana
                    # print('staring grafana------->')
                    # print cmd_line
                    cmd = subprocess.Popen([cmd_line],shell=True,stderr=subprocess.PIPE)
                    (output,err) = cmd.communicate()
                    # app_logger.info('*********output logging **************')
                    print(output)
                    return('grafana has been started!')
                except Exception as ex:
                    return("    Failed to run processor with ERROR(%s).", str(ex))
                    sys.exit(1)
            else:
                if not running_dict.has_key('grafana'):
                    return('You don\'t have permmission to run command from this host.')
                    
                elif running_dict['kairosDb']=='Stopped':
                    return('kairosDb required starting before grafana is running!')
                     
                elif running_dict['grafana'] == 'Running':
                    return('grafana Server is running!! please trying to stop it before it starts.')
                    

        elif processor == 'kafka':
            if running_dict.has_key('kafka') and running_dict['kafka'] != 'Running' and running_dict['zookeeper']=='Running':
                try:
                    cmd_line = self.cmd_start_kafka
                    # print('staring kafka------->')
                    print cmd_line
                    cmd = subprocess.Popen([cmd_line],shell=True,stderr=subprocess.PIPE)
                    # (output,err) = cmd.communicate()
                    # print (output)
                    return ('Kafka has been started!')
                    # app_logger.info('*********output logging **************')
                    # print(output)
                except Exception as ex:
                    return("    Failed to run processor with ERROR(%s).", str(ex))
                    sys.exit(1)
            else:
                if not running_dict.has_key('kafka'):
                    return('You don\'t have permmission to run command from this host.')
                    
                elif running_dict['zookeeper']=='Stopped':
                    return('zookeeper required starting before kafka is running!')
                    
                elif running_dict['kafka'] == 'Running':
                    return('Kafka Server is running!! please trying to stop it before it starts.')
                    
    
        elif processor == 'zookeeper':
            if running_dict.has_key('zookeeper') and running_dict['zookeeper'] != 'Running':
                try:
                    cmd_line = self.cmd_start_zookeeper
                    # print('staring zookeeper------->')
                    # print (cmd_line)
                    cmd = subprocess.Popen([cmd_line],shell=True,stderr=subprocess.PIPE,preexec_fn=self.set_pdeathsig(signal.SIGTERM))
                    # (output,err) = cmd.communicate()
                    # print (output)
                    return ('zookeeper has been started!')
                except Exception as ex:
                    return("    Failed to stop processor with ERROR(%s).", str(ex))
                    sys.exit(1)
            else:
                if not running_dict.has_key('zookeeper'):
                    return('You don\'t have permmission to run command from this host.')
                    
                else:
                    return('Zookeeper Server is running!! please trying to stop it before it starts.')
                    

        elif processor == 'accl_processor':
            if running_dict:
                if running_dict['accl_processor'] != 'Running' and running_dict['spark<spark_worker>'] == 'Running' and running_dict['spark<spark_master>'] == 'Running' and running_dict['zookeeper'] == 'Running' and running_dict['kafka'] == 'Running':
                    try:
                        cmd_line = self.cmd_start_accl_processor
                        cmd = subprocess.Popen([cmd_line],shell=True,stderr=subprocess.PIPE)
                        return('accelerometer processor has been started!')
                    except Exception as ex:
                        return("    Failed to run processor with ERROR(%s).", str(ex))
                        sys.exit(1)
                else:
                    if running_dict['accl_processor'] == 'Running':
                        return('Accelerometer processor is running!! please trying to stop it before it starts.')
                        
                    elif running_dict['spark<spark_worker>'] == 'Stopped' or running_dict['spark<spark_master>'] == 'Stopped':
                        return('Please start spark first!')
                        
                    elif running_dict['zookeeper'] == 'Stopped':
                        return('Please start zookeeper server first!')
                        
                    elif running_dict['kafka'] == 'Stopped':
                        return('Please start kafka server first!')
                        
            else:
                return('You don\'t have permmission to run command from this host.')
                sys.exit(1)

        elif processor == 'baro_processor':
            if running_dict:
                if running_dict['baro_processor'] != 'Running' and running_dict['spark<spark_worker>'] == 'Running' and running_dict['spark<spark_master>'] == 'Running' and running_dict['zookeeper'] == 'Running' and running_dict['kafka'] == 'Running':
                    try:
                        cmd_line = self.cmd_start_baro_processor
                        cmd = subprocess.Popen([cmd_line],shell=True,stderr=subprocess.PIPE)
                        return('barometer processor has been started!')
                    except Exception as ex:
                        return("    Failed to run processor with ERROR(%s).", str(ex))
                        sys.exit(1)
                else:
                    if running_dict['baro_processor'] == 'Running':
                        return('Barometer processor is running!! please trying to stop it before it starts.')
                        
                    elif running_dict['spark<spark_worker>'] == 'Stopped' or running_dict['spark<spark_master>'] == 'Stopped':
                        return('Please start spark first!')
                        
                    elif running_dict['zookeeper'] == 'Stopped':
                        return('Please start zookeeper server first!')
                        
                    elif running_dict['kafka'] == 'Stopped':
                        return('Please start kafka server first!')
                        
            else:
                return('You don\'t have permmission to run command from this host.')
                sys.exit(1)

        elif processor == 'gyro_processor':
            if running_dict:
                if running_dict['gyro_processor'] != 'Running' and running_dict['spark<spark_worker>'] == 'Running' and running_dict['spark<spark_master>'] == 'Running' and running_dict['zookeeper'] == 'Running' and running_dict['kafka'] == 'Running':
                    try:
                        cmd_line = self.cmd_start_gyro_processor
                        cmd = subprocess.Popen([cmd_line],shell=True,stderr=subprocess.PIPE)
                        return('gyroscope processor has been started!')
                    except Exception as ex:
                        return("    Failed to run processor with ERROR(%s).", str(ex))
                        sys.exit(1)
                else:
                    if running_dict['gyro_processor'] == 'Running':
                        return('Gyroscope processor is running!! please trying to stop it before it starts.')
                        
                    elif running_dict['spark<spark_worker>'] == 'Stopped' or running_dict['spark<spark_master>'] == 'Stopped':
                        return('Please start spark first!')
                        
                    elif running_dict['zookeeper'] == 'Stopped':
                        return('Please start zookeeper server first!')
                        
                    elif running_dict['kafka'] == 'Stopped':
                        return('Please start kafka server first!')
                        
            else:
                return('You don\'t have permmission to run command from this host.')
                sys.exit(1)

        elif processor == 'aggr_processor':
            if running_dict:
                if running_dict['aggr_processor'] != 'Running' and running_dict['spark<spark_worker>'] == 'Running' and running_dict['spark<spark_master>'] == 'Running' and running_dict['zookeeper'] == 'Running' and running_dict['kafka'] == 'Running':
                    try:
                        cmd_line = self.cmd_start_aggr_naiv
                        cmd = subprocess.Popen([cmd_line],shell=True,stderr=subprocess.PIPE)
                        return('Aggregator processor has been started!')
                    except Exception as ex:
                        return("    Failed to run processor with ERROR(%s).", str(ex))
                        sys.exit(1)
                else:
                    if running_dict['aggr_processor'] == 'Running':
                        return('Aggregator processor is running!! please trying to stop it before it starts.')
                        
                    elif running_dict['spark<spark_worker>'] == 'Stopped' or running_dict['spark<spark_master>'] == 'Stopped':
                        return('Please start spark first!')
                        
                    elif running_dict['zookeeper'] == 'Stopped':
                        return('Please start zookeeper server first!')
                        
                    elif running_dict['kafka'] == 'Stopped':
                        return('Please start kafka server first!')
                        
            else:
                return ('You don\'t have permmission to run command from this host.')
                sys.exit(1)

        else:
            return ('Please type correct command! ')

    def do_stop(self,processor):
        """stop [processor] 
        Stop the name of processor
        available processor list
        [spark]          -->  Engine data processing
        [kafka]          -->  Data pipelines and streaming
        [zookeeper]      -->  Zookeeper central service
        [flask]          -->  Integration webserver
        [cassandra]      -->  Cassandra real-time database
        [kairosDb]       -->  Time Series Database on Cassandra
        [grafana]        -->  Grafana realtime series dashboard
        [tomcat]         -->  Java servlet server
        [raw_writter]    -->  Raw data writer on cassandra
        [novelty]        -->  Novelty detection for Healthcare
        [accl_processor] -->  Accelerometer HAR classifier
        [baro_processor] -->  Barometer HAR classifier
        [gyro_processor] -->  Gyroscope HAR classifier 
        [aggr_processor] -->  Aggregation HAR classifier
        """
        app_logger = self.construct_logger(rta_constants.PROPERTIES_LOG_FILE)
        running_dict = {}
        runnind_pids = {}
        for item in self.get_running_status():
            running_dict[item.get('processor')]=item.get('status')
            runnind_pids[item.get('processor')]=item.get('PID')
        if processor == 'spark':
            if running_dict.has_key('spark<spark_master>') and running_dict.has_key('spark<spark_master>') and (running_dict['spark<spark_master>']=='Running' or running_dict['spark<spark_worker>']=='Running'):
                try:
                    cmd_line = self.cmd_stop_spark
                    cmd = subprocess.Popen([cmd_line],shell=True,stdout=subprocess.PIPE)
                    (output,err) = cmd.communicate()
                    # print('*********output logging **************')
                    print(output)
                    return ('Spark has been stopped!')
                    
                except Exception as ex:
                    return("    Failed to stop processor with ERROR(%s).", str(ex))
                    sys.exit(1)
            else:
                if not (running_dict.has_key('spark<spark_master>') or running_dict.has_key('spark<spark_master>')):
                    return('You don\'t have permmission to run command from this host.')
                    
                elif running_dict['spark<spark_master>']!='Running' or running_dict['spark<spark_worker>']!='Running':
                    return('Spark server is already stopped! No action need to do!')
                    

        elif processor == 'tomcat':
            if running_dict.has_key('tomcat') and running_dict['tomcat'] == 'Running':
                try:
                    pid = runnind_pids.get('tomcat')
                    if not pid:
                        return ("No Tomcat server to stop")
                        # sys.exit(1)
                        
                    else:
                        kill_cmd = "kill -s TERM "+pid
                        os.popen(kill_cmd)
                        print "Executed:"+kill_cmd
                        return ('Tomcat server has been stopped!')

                except Exception as ex:
                    return("    Failed to stop Tomcat server with ERROR(%s).", str(ex))
                    sys.exit(1)
            else:
                if not running_dict.has_key('tomcat'):
                    return('You don\'t have permmission to run command from this host.')
                    
                else:
                    return('Tomcat server is already stopped! No action need to do!')
                    

        elif processor == 'kairosDb':
            if running_dict.has_key('kairosDb') and running_dict['kairosDb'] == 'Running':
                try:
                    cmd_line = self.cmd_stop_kairosDB
                    # print 'stopping kairosDB------>'
                    # print cmd_line
                    cmd = subprocess.Popen([cmd_line],shell=True,stderr=subprocess.PIPE)
                    (output,err) = cmd.communicate()
                    # print (cmd.pid)
                    # print('*********output logging **************')
                    print (output)
                    return('Stopped kairosDB server')
                    
                except Exception as ex:
                    return("    Failed to stop processor with ERROR(%s).", str(ex))
                    sys.exit(1)
            else:
                if not running_dict.has_key('kairosDb'):
                    return('You don\'t have permmission to run command from this host.')
                    
                else:
                    return('KairosDB Server is already stopped! No action need to do!')
                    

        elif processor == 'cassandra':
            if running_dict.has_key('cassandra') and running_dict['cassandra'] == 'Running':
                try:
                    pid = runnind_pids.get('cassandra')
                    if not pid:
                        return ("No cassandra server need to stop")
                        # sys.exit(1)
                        
                    else:
                        kill_cmd = "kill -s TERM "+pid
                        os.popen(kill_cmd)
                        print "Executed:"+kill_cmd
                        return('Stopped cassandra server')
                        
                except Exception as ex:
                    return("    Failed to stop processor with ERROR(%s).", str(ex))
                    sys.exit(1)
            else:
                if not running_dict.has_key('cassandra'):
                    return('You don\'t have permmission to run command from this host.')
                    
                else:
                    return('Cassandra is already stopped! No action need to do!')
                    

        elif processor == 'grafana':
            if running_dict.has_key('grafana') and running_dict['grafana'] == 'Running':
                try:
                    cmd_line = self.cmd_stop_grafana
                    # print 'stopping grafana------>'
                    # print cmd_line
                    cmd = subprocess.Popen([cmd_line],shell=True,stderr=subprocess.PIPE)
                    (output,err) = cmd.communicate()
                    # print (cmd.pid)
                    # print('*********output logging **************')
                    return('Stopped grafana server')
                    
                except Exception as ex:
                    return("    Failed to stop processor with ERROR(%s).", str(ex))
                    sys.exit(1)
            else:
                if not running_dict.has_key('grafana'):
                    return('You don\'t have permmission to run command from this host.')
                    
                else:
                    return('Grafana server is already stopped! No action need to do!')
                    

        elif processor == 'kafka':
            if running_dict.has_key('kafka') and running_dict['kafka'] == 'Running':
                try:
                    pid = runnind_pids.get('kafka')
                    if not pid:
                        return ("No kafka server to stop")
                        # sys.exit(1)
                        
                    else:
                        kill_cmd = "kill -s TERM "+pid
                        os.popen(kill_cmd)
                        print "Executed:"+kill_cmd
                        return('Kafka has been stopped')
                    # print('*********output logging **************')
                    # cmd_line = self.cmd_stop_kafka
                    # print cmd_line
                    # cmd_line = "ps ax | grep -i 'kafka\.Kafka' | grep java | grep -v grep | awk '{print $1}'"
                    # cmd_line ="ps ax > larry.txt"
                    # runjob.run_processor(cmd_line)
                    # # cmd_line = "ps ax | grep -i 'zookeeper' | grep -v grep | awk '{print $1}'"
                    # # print cmd_line
                    # # os.popen(cmd_line)
                    # sys.exit(1)
                    # print process_ls

                    # (status, output) = commands.getstatusoutput(cmd_line)
                    # print status, output
                    # sys.exit(1)

                    # f = open('larry.txt','r')
                    # f.close()
                    # result = list()  
                    # for line in f.readlines():   
                    #     print line
                    #     result.append(line)  
                    # print result  
                    # sys.exit(1)
                    # ps_cmd = "ps ax"
                    # regex_search = re.compile(".*kafka\.Kafka config\/server\.properties")

                    # # Retrieve the result of ps ax into a list
                    # procc_list=os.popen(ps_cmd).readlines()
                    # print procc_list
                    # # filter each element of the list and keep only the one matching the regex
                    # procc_line = filter(regex_search.match,procc_list)
                    # print procc_line
                    # the resulting procc_line is a list of 1 element.
                    # We scan this elem (for elem in procc_line) and split its content using a space seperator
                    # pid = [elem.split(' ')[0] for elem in procc_line]
                    # The first ([0]) one is the pid we are looking for
                    # print ("result:%s" % pid[0])
                    # ps_list = []
                    # for item in process_ls:
                    #     if item.find('org.apache.zookeeper.server.quorum.QuorumPeerMain'):
                    #         ps_list.append(item)
                    # print ps_list
                    # print pid_str.split(' ')[0]
                    # sys.exit(1)
                    # Check if the PIDS variable is empty
                    
                except Exception as ex:
                    return("    Failed to stop processor with ERROR(%s).", str(ex))
                    sys.exit(1)
            else:
                if not running_dict.has_key('kafka'):
                    return('You don\'t have permmission to run command from this host.please check with your administrator')
                    
                else:
                    return('Kafka Server is already stopped! No action need to do!')
                    

        elif processor == 'zookeeper':
            if running_dict.has_key('zookeeper') and running_dict['zookeeper'] == 'Running':
                try:
                    pid = runnind_pids.get('zookeeper')
                    if not pid:
                        return ("No zookeeper server to stop")
                        # sys.exit(1)
                        
                    else:
                        kill_cmd = "kill -s TERM "+pid
                        os.popen(kill_cmd)
                        print "Executed:"+kill_cmd
                        return('Zookeeper has been stopped')
                        
                except Exception as ex:
                    return("    Failed to stop processor with ERROR(%s).", str(ex))
                    sys.exit(1)
            else:
                if not running_dict.has_key('zookeeper'):
                    return('You don\'t have permmission to run command from this host.')
                    
                else:
                    return('Zookeeper Server is already stopped! No action need to do!')
                    

        elif processor == 'accl_processor':
            if running_dict.has_key('accl_processor') and running_dict['accl_processor'] == 'Running':
                try:
                    cmd_line = self.cmd_stop_accl_processor
                    cmd = subprocess.Popen([cmd_line],shell=True,stderr=subprocess.PIPE)
                    return ('accl_processor has been stopped!')
                    
                except Exception as ex:
                    return("    Failed to stop processor with ERROR(%s).", str(ex))
                    sys.exit(1)
            else:
                if not running_dict.has_key('accl_processor'):
                    return('You don\'t have permmission to run command from this host.')
                    
                else:
                    return('Accelerometer processor is already stopped! No action need to do!')
                    

        elif processor == 'gyro_processor':
            if running_dict.has_key('gyro_processor') and running_dict['gyro_processor'] == 'Running':
                try:
                    cmd_line = self.cmd_stop_gyro_processor
                    cmd = subprocess.Popen([cmd_line],shell=True,stderr=subprocess.PIPE)
                    return ('gyro_processor has been stopped!')
                    
                except Exception as ex:
                    return("    Failed to stop processor with ERROR(%s).", str(ex))
                    sys.exit(1)
            else:
                if not running_dict.has_key('gyro_processor'):
                    return('You don\'t have permmission to run command from this host.')
                    
                else:
                    return('Gyroscope processor is already stopped! No action need to do!')
                    

        elif processor == 'baro_processor':
            if running_dict.has_key('baro_processor') and running_dict['baro_processor'] == 'Running':
                try:
                    cmd_line = self.cmd_stop_baro_processor
                    cmd = subprocess.Popen([cmd_line],shell=True,stderr=subprocess.PIPE)
                    return ('baro_processor has been stopped!')
                    
                except Exception as ex:
                    return("    Failed to stop processor with ERROR(%s).", str(ex))
                    sys.exit(1)
            else:
                if not running_dict.has_key('baro_processor'):
                    return('You don\'t have permmission to run command from this host.')
                    
                else:
                    return('Barometer processor is already stopped! No action need to do!')
                    

        elif processor == 'aggr_processor':
            if running_dict.has_key('aggr_processor') and running_dict['aggr_processor'] == 'Running':
                try:
                    cmd_line = self.cmd_stop_aggr_naiv
                    cmd = subprocess.Popen([cmd_line],shell=True,stderr=subprocess.PIPE)
                    return ('aggr_processor has been stopped!')
                    
                except Exception as ex:
                    return("    Failed to stop processor with ERROR(%s).", str(ex))
                    sys.exit(1)
            else:
                if not running_dict.has_key('aggr_processor'):
                    return('You don\'t have permmission to run command from this host.')
                    
                else:
                    return('Aggregator processor is already stopped! No action need to do!')
                    

        elif processor == 'raw_writer':
            if running_dict.has_key('raw_writer') and running_dict['raw_writer'] == 'Running':
                try:
                    pid = runnind_pids.get('raw_writer')
                    if not pid:
                        return ("No raw_writer processor need to stop")
                        # sys.exit(1)
                        
                    else:
                        kill_cmd = "kill -s TERM "+pid
                        os.popen(kill_cmd)
                        print "Executed:"+kill_cmd
                        return('raw_writer processor has been stopped')
                        
                except Exception as ex:
                    return("    Failed to stop processor with ERROR(%s).", str(ex))
                    sys.exit(1)
            else:
                if not running_dict.has_key('raw_writer'):
                    return('You don\'t have permmission to run command from this host.')
                    
                else:
                    return('Raw_writer processor is already stopped! No action need to do!')
                    

        elif processor == 'novelty':
            if running_dict.has_key('novelty') and running_dict['novelty'] == 'Running':
                try:
                    pid = runnind_pids.get('novelty')
                    if not pid:
                        return ("No novelty processor need to stop")
                        # sys.exit(1)
                        
                    else:
                        kill_cmd = "kill -s TERM "+pid
                        os.popen(kill_cmd)
                        print "Executed:"+kill_cmd
                        return ('novelty has been stopped!')
                        
                except Exception as ex:
                    return("    Failed to stop processor with ERROR(%s).", str(ex))
                    sys.exit(1)
            else:
                if not running_dict.has_key('novelty'):
                    return('You don\'t have permmission to run command from this host.')
                    
                else:
                    return('Novelty_detector processor is already stopped! No action need to do!')
        
        elif processor == 'flask':
            if running_dict.has_key('flask') and running_dict['flask'] == 'Running':
                try:
                    pid = runnind_pids.get('flask')
                    if not pid:
                        return ("No flask processor need to stop")
                        # sys.exit(1)
                        
                    else:
                        kill_cmd = "kill -s TERM "+pid
                        os.popen(kill_cmd)
                        print "Executed:"+kill_cmd
                        return ('Flask has been stopped!')
                        
                except Exception as ex:
                    return("    Failed to stop processor with ERROR(%s).", str(ex))
                    sys.exit(1)
            else:
                if not running_dict.has_key('flask'):
                    return('You don\'t have permmission to run command from this host.')
                    
                else:
                    return('flask is already stopped! No action need to do!')          

        else:
            return ('You don\'t have permmission to run command from this host.')

    def do_exit(self, line):
        """
        Exit the RTA command line
        """
        return True

if __name__ == "__main__":
    pass
