# -*- coding: utf-8 -*-
"""
Author: Wu Jun-Yi(junyi.wu@hpe.com)
Creation Date: 2016-09-10
Purpose: To monitoring processors status
"""

import psutil
import sys
from flask import Flask, jsonify, render_template, request,redirect, session, url_for
import rta_constants
import logging
import logging.config
import os
import ConfigParser
import socket
from platform_mngt_lib import ProcessWeb,ProcessInfo,TailThread
from werkzeug.serving import run_simple
import thread
# from flask_socketio import SocketIO
# from websocket_srv import WebSocketServer
import subprocess
# from websocket import create_connection

app = Flask(__name__)
# app.config['HOST'] = socket.gethostbyname(socket.gethostname())
# app.config['PORT'] = 8889

# socketio = SocketIO(app)

# socket_server = WebSocketServer()

# @app.route('/log')
# def log():
    
@app.route('/log')
def log():
    logtype = str(request.args.get('logtype'))
    print('logtype = ',logtype)

    # print ('starting to web tail!!!!')
    run = ProcessWeb()
    output = run.do_tail(logtype)
    print output
    # print 'stdout : ',stdout
    # print 'stderr : ',stderr
    # print('server connected')
    # ws_server = "ws://"+socket.gethostbyname(socket.gethostname())+":8000/websocket/"
    # ws = create_connection(ws_server)   # create websocket connection
    # print 'output tail -f'
    # filter out the null value in log list
    lines = output.strip().split('\n')
    for item in lines:
        if item.strip()=='':
            lines.remove(item)
    print lines
    return render_template('log.html',log=lines)

@app.route('/tail')
def tail():
    print ('starting to tail!!!!')
    processor = str(request.args.get('job'))
    
    # p = subprocess.Popen(['tail','-f','/opt/mount1/rta-hc/integration/rta-hc-framework-master/log/rta_processor_accel.log'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=False)
    # send data to log page
    
    # ws.send(line)
    # redirect(url_for('web'))
    # thread = TailThread(processor)
    # thread.start()
    # thread.join()
    # run.do_tail(processor)
    return jsonify(result='sucess')
    # return render_template('log.html')

@app.route('/result')
def result():
    print ('starting to routing!!!!')
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
        spark_ls= []     
        for processor in dict_processor:
            if processor.get('processor') == 'spark<spark_worker>' or processor.get('processor') == 'spark<spark_master>':
                spark_ls.append(processor)
                del dict_processor[dict_processor.index(processor)]
        
        return render_template('proc_table.html', result = dict_processor,hostname=hostname,spark_ls=spark_ls)
    else:
        return render_template('error.html')

@app.route('/run')
def run():
    run_job = ProcessWeb()
    print("start to run job...")
    processor = str(request.args.get('job'))
    print processor
    processor = run_job.mapping_covert(processor)
    print processor
    result = run_job.do_start(processor)
    print result
    return jsonify(result=result)

@app.route('/shutdown', methods=['POST'])
def shutdown():
    run_job = ProcessWeb()
    run_job.shutdown_server()
    return 'Server shutting down...'

@app.route('/stop')
def stop():
    print("stop the job...")
    run_job = ProcessWeb()
    processor = str(request.args.get('job'))
    print processor
    processor = run_job.mapping_covert(processor)
    print processor
    result = run_job.do_stop(processor)
    return jsonify(result=result)

if __name__ == "__main__":
    process = ProcessInfo('jobs')
    status = process.check_host_is_exist()
    if not status:
        print ('This host is not able to monitoring!!')
        sys.exit(1)
    else:
        host_name = process.get_host_name()
        host_ip = socket.gethostbyname(socket.gethostname())
        # socketio.run(app)
        run_simple(host_ip, 8889, app, use_reloader=True)
        # start websocket server on port=8000
        # socket_server.run()

    
    

