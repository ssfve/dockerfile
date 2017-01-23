# -*- coding: utf-8 -*-
"""
Created on Wed May 04 14:31:14 2016

@author: planat
"""
import requests


'''
Kairos DB. Cleanup metrics
'''
hostname = "http://c2t08977.itcs.hpecorp.net:9090/api/v1/"
#http://c4t19765.itcs.hpecorp.net:8080/api/v1/metric/vpl_heartRate-rate
headers = {'content-type': 'application/json'}

hostnames_list = ["http://c2t08977.itcs.hpecorp.net:9090/api/v1/", "http://C2t08978.itcs.hpecorp.net:9090/api/v1/"]
for hostname in hostnames_list:
    print ("-------------- delete group-0 ----------------")
    metric_list = ["raw_calorie_calories","raw_distance_current_motion","raw_distance_pace","raw_distance_speed","raw_distance_total_distance","raw_gsr_resistance","raw_gy_flights_ascended","raw_gy_flights_descended","raw_gy_rate","raw_gy_stepping_gain","raw_gy_stepping_loss","raw_gy_steps_ascended","raw_gy_steps_descended","raw_gy_total_gain","raw_gy_total_loss","raw_gyroscope_x","raw_gyroscope_y","raw_gyroscope_z","raw_heartRate_quality","raw_heartRate_rate","raw_rrInterval_interval","raw_skinTemperature_temperature","raw_uv_index_uv"]
    for metric_item in metric_list:
        kairosdb_url = hostname + "metric/" + metric_item
        resp = requests.delete(kairosdb_url,headers=headers)
        if resp.status_code != 204:
            print("POST ERROR /tasks/ {} %s" % format(resp.status_code)) 
        print("DELETED metric %s. Status code:%s" % (kairosdb_url,resp.status_code));
    
    print ("-------------- delete group-1 ----------------")
    metric_list = ["raw_altimeter_flights_ascended","raw_altimeter_flights_descended","raw_altimeter_rate","raw_altimeter_stepping_gain","raw_altimeter_stepping_loss","raw_altimeter_steps_ascended","raw_altimeter_steps_descended","raw_altimeter_total_gain","raw_altimeter_total_loss"]
    for metric_item in metric_list:
        kairosdb_url = hostname + "metric/" + metric_item
        resp = requests.delete(kairosdb_url,headers=headers)
        if resp.status_code != 204:
            print("POST ERROR /tasks/ {} %s" % format(resp.status_code)) 
        print("DELETED metric %s. Status code:%s" % (kairosdb_url,resp.status_code));
    
    print ("-------------- delete group-2 ----------------")
    metric_list = ["novelty_detection" ,"har_prediction"]
    for metric_item in metric_list:
        kairosdb_url = hostname + "metric/" + metric_item
        resp = requests.delete(kairosdb_url,headers=headers)
        if resp.status_code != 204:
            print("POST ERROR /tasks/ {} %s" % format(resp.status_code)) 
        print("DELETED metric %s. Status code:%s" % (kairosdb_url,resp.status_code));
    
    print ("-------------- delete group-3 ----------------")
    metric_list = ["raw_accelerometer_x","raw_accelerometer_y","raw_accelerometer_z","raw_ambientLight_brightness","raw_barometer_air_pressure","raw_barometer_temperature"]
    for metric_item in metric_list:
        kairosdb_url = hostname + "metric/" + metric_item
        resp = requests.delete(kairosdb_url,headers=headers)
        if resp.status_code != 204:
            print("POST ERROR /tasks/ {} %s" % format(resp.status_code)) 
        print("DELETED metric %s. Status code:%s" % (kairosdb_url,resp.status_code));

print("cleanup done")
