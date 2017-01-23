# -*- coding: utf-8 -*-

"""
Created on Mar 22, 2016
Purpose: Capture traffic from kafka queues and save to Cassandra

@author: Joanne Lynch
@author: Chen-Gang He
        1> Create superclass GenericSensor and its subclass based on different sensor type
        in order to define different attributes and methods like INSERT query based on different sensor type
        2> On April 3th, added determine_datapoint_key, append_karrios_data_points and issue_insert_query_karrios
        to enable it to insert data to KarriosDB.
        2016-05-13
        1> issue_insert_query_karrios: replace json.dumps to parameter
        2> removed unnecessary import packages and commented lines
        3> refined documentation more to make it more concise and clear
        4> Lowered all sensor type names in SensorFactory to avoid mis-matching
        5> Changed constants in this script to use corresponding ones in rta_constants.py
        6> Used SensorFactory to construct all sub-classes to contain them in sensor_object_dict to avoid hard code to
        construct all, which makes it more flexible
        7> Used one loop to post the rest of data points in self.karios_data_point_list in the end to make it more
        flexible
        8> Added valid_data to forEachRdd before writing data to Cassandra or KariosDB to filter or transformation or
        validate if there is any record in current RDD
        9> Used logger to make more use-friendly logs in main part
        10> Tested all sensors for Cassandra tables
        11> Commented conf.setMaster("local[*]") to use Yarn mode
        2016-05-16
        1> Refactored set_sensor method for all sensors in subclass to remove repeated assignments for attributes
        and append_karrios_data_points and issue_insert_query_casssandra in superclasss.
        Instead, use super key to assign attributes in supperclass
        2> Replace if-elif-else in process_data with use of sensor_object_dict to remove many repeated if-elif-else
        codes;
        2016-05-25
        1> Removed commented and unnecessary codes
        2> Added try-except logic to process_data in case whole process will be crashed due to
        there is no sensor object instance for new sensor type name from incoming events from Kafka queue.
"""

## Spark Application - execute with spark-submit

## Imports
import json
import logging
import logging.config
import re
import sys
import uuid
from ConfigParser import SafeConfigParser

import requests
import time
from cassandra.cluster import Cluster
from pyspark import SparkConf, SparkContext
from pyspark.streaming import StreamingContext
from pyspark.streaming.kafka import KafkaUtils

import rta_constants

## Module Constants
APP_NAME = "raw_writer"
VERSION_VAL = "0.11"
# DISABLE_SENSOR_SET = set(["hdhld", "contact", "pedometer"])
DISABLE_SENSOR_SET = set(["accelerometer", "gyroscope", "altimeter", "ambientlight", "barometer", "calorie", "distance",
                         "uv", "contact", "pedometer", "hdhld"])

# ==============================================================================
# Class
# ==============================================================================
class GenericSensor(object):
    """ Keep common attributes for snesor, and provides generic method for different sensor.

    Args:
        None

    Attributes:
        __event_id (str): uuid value in string for uniquely identify an event in sensor
        attr_2_column_mapping (dict): Stands for mapping between instance attribute and (column name in Cassandra
         table, data type)
        karrios_data_points_list (list): a list of data points (dict) in Karrios data point:
        for example: one data point is {'timestamp': 1456939614201L, 'name': 'raw_gy_steps_ascended', 'value': 4408,
        'tags': {'user_id': u'vincent.planat@hpe.com', 'event_type': u'altimeter',
        'event_id': u'664df9f0-f838-4059-8cf2-470586a3f2af', 'training_mode': u'SITTING', 'device_type': u'msband2',
        'device_id': u'b81e905908354542'}}
    """

    def __init__(self):
        self.__event_id = ""
        self.__device_type = ""
        self.__device_id = ""
        self.__event_type = ""
        self.__timestamp = ""
        self.__user_id = ""
        self.__training_mode = ""
        self.karrios_data_points_list = []
        self.attr_2_column_mapping = dict()
        self.attr_2_column_mapping["__event_id"] = ("event_id", "uuid")
        self.attr_2_column_mapping["__device_type"] = ("device_type", "text")
        self.attr_2_column_mapping["__device_id"] = ("device_id", "text")
        self.attr_2_column_mapping["__event_type"] = ("event_type", "text")
        self.attr_2_column_mapping["__timestamp"] = ("time_stamp", "bigint")
        self.attr_2_column_mapping["__user_id"] = ("user_id", "text")
        self.attr_2_column_mapping["__training_mode"] = ("training_mode", "text")

    def get_sensor(self):
        """Return attributes of the instance
        Returns:
            str
        """
        pass

    def set_sensor(self, **kwargs):
        """Set attributes of the instance
            Args:
                **kwargs(dict): a dictionary of argument key and value pairs
        Returns:
            None
        """
        self.__event_id = kwargs.get("eventId", "977c9b9a-9a02-4e1e-830b-7fdbc754f987")
        self.__device_type = kwargs.get("deviceType", "NA")
        self.__device_id = kwargs.get("deviceid", "NA")
        self.__event_type = kwargs.get("eventtype", "NA")
        self.__timestamp = kwargs.get("timestamp", "NA")
        self.__user_id = kwargs.get("userid", "NA")
        self.__training_mode = kwargs.get("trainingMode", "NA")

    def issue_insert_query_cassandra(self, table_name, cassandra_session_obj):
        """Set attributes of the instance
            Args:
                table_name(str): name of table in Cassandra, which is used for metric name in Karrios.
                cassandra_session_obj(cassandra session object): reference to Cassandra session object
        Returns:
            None
        """
        value_list = []
        insert_clause = ""
        value_clause = ""
        # Loop through attributes in the self object and generate INSERT query and issue the query
        for key in self.__dict__.keys():
            # Only get attributes of self object for polymorphism
            # if key.startswith("_" + self.__class__.__name__):
            if key.startswith("_" ):
                # Only get attributes starting with "__" in instance
                instance_attribute_name = key.replace("_" + self.__class__.__name__, "").replace("_GenericSensor", "")
                # print instance_attribute_name
                insert_clause = insert_clause + ", " + self.attr_2_column_mapping[instance_attribute_name][0]
                value_clause += "%s, "
                value_list.append(self.__dict__[key] if self.attr_2_column_mapping[instance_attribute_name][1] != "uuid"
                                  else uuid.UUID(self.__dict__[key]))
        insert_query = "INSERT INTO " + table_name + "(" + insert_clause.strip(", ") + ") VALUES (" + \
                       value_clause.strip(", ") + ")"
        # print insert_query
        # Issue the query
        cassandra_session_obj.execute_async(insert_query, value_list)

    @staticmethod
    def determine_datapoint_key(re_compile, column_name, column_data_type):
        """Determine which key in Karrios data point is regarding column name and data type and return key in data
        point. Categorise data as values, tags or timestamps.
        Args:
            column_name(str): name of table in Cassandra, which is used for metric name in Karrios.
            column_data_type(str): data type of column in Cassandra
            re_compile(reference to re.compile): reference to method of re.compile
        Returns:
            str: validate value is "tags", "value", "timestamp" and None
        """
        # Data type is numeric
        data_type_pattern = ur'''(float)|(doulbe)|(int)|(long)|(byte)|(bigint)'''
        data_type_pattern_obj = re_compile(data_type_pattern)
        data_type_search_obj = data_type_pattern_obj.search(column_data_type.strip().lower())
        # column name is timestamp or time_stamp
        column_name_pattern = ur'''^(timestamp)|(time_stamp)$'''
        column_name_pattern_obj = re_compile(column_name_pattern)
        column_name_search_obj = column_name_pattern_obj.search(column_name.strip().lower())
        if data_type_search_obj and not column_name_search_obj:
            # data type is numeric and column name is not timestamp or time_stamp
            return "value"
        elif not data_type_search_obj and not column_name_search_obj:
            return "tags"
        elif column_name_search_obj:
            return "timestamp"
        else:
            return None

    def append_karrios_data_points(self, table_name, re_compile):
        """Append Karrios data points to self.karrios_data_points_list based on incoming input
            Args:
                table_name(str): name of table in Cassandra, which is used for metric name in Karrios.
                for example, Karrios metric name is "raw_accelerometer_x" if table_name is
                "accelerometer" and column name is "x"
                re_compile(reference to re.compile): reference to method of re.compile
        Returns:
            None
        """
        tags_dict = {}
        timestamp_tuple = ()
        data_point_dict_list = []
        # Get tags of karrios data points
        for attr in self.__dict__.keys():
            # Filter private attributes in base class due to name mangling to
            # get private attributes in self object
            # if attr.startswith("_" + self.__class__.__name__):
            if attr.startswith("_"):
                # Only get attributes starting with "__" in instance
                instance_attribute_name = attr.replace("_" + self.__class__.__name__, "").replace("_GenericSensor", "")
                instance_attribute_column_name = self.attr_2_column_mapping[instance_attribute_name][0]
                instance_attribute_column_datatype = self.attr_2_column_mapping[instance_attribute_name][1]
                instance_attribute_value = self.__dict__[attr]
                datapoint_key = self.determine_datapoint_key(re_compile, \
                                                             instance_attribute_column_name,
                                                             instance_attribute_column_datatype)
                if datapoint_key == "tags":
                    tags_dict[instance_attribute_column_name] = instance_attribute_value
                elif datapoint_key == "value":
                    metric_name_tuple = ("name", table_name + "_" + instance_attribute_column_name)
                    value_tuple = ("value", instance_attribute_value)
                    data_point_dict = dict([metric_name_tuple, value_tuple])
                    data_point_dict_list.append(data_point_dict)
                # print data_point_dict
                elif datapoint_key == "timestamp":
                    timestamp_tuple = ("timestamp", instance_attribute_value)
        # Add tags and timestamp to each data point dict
        for data_point_dict in data_point_dict_list:
            data_point_dict["tags"] = tags_dict
            data_point_dict["timestamp"] = timestamp_tuple[1]
            # logger.debug(data_point_dict)
            self.karrios_data_points_list.append(data_point_dict)

    def issue_insert_query_karrios(self, rest_post_obj, json_dumps, karrios_rest_url, max_number_of_datapoints,
                                   force_send_flag=False):
        """Insert max number of Karrios data points to KarriosDB if force_send_flag is set to false
            Args:
                rest_post_obj(requests): reference to requests package object
                json_dumps(reference to json.dumps): reference to method "dumps" in json package
                karrios_rest_url(str): restful port of KarriosDB
                max_number_of_datapoints(int): max number of data points to be inserted to KarriosDB
                force_send_flag(Optional: boolean): indicates if all data points should be dumped regardless
                of max_number_of_datapoints
        Returns:
            None
        """
        headers = {'content-type': 'application/json'}
        number_of_data_points = len(self.karrios_data_points_list)
        remain_data_point_index = 0
        if force_send_flag:
            if number_of_data_points > 0:
                json_data = json.dumps(self.karrios_data_points_list)
                remain_data_point_index = number_of_data_points
            else:
                json_data = ""
                remain_data_point_index = 0
        else:
            if number_of_data_points >= max_number_of_datapoints:
                json_data = json_dumps(self.karrios_data_points_list[:max_number_of_datapoints])
                remain_data_point_index = max_number_of_datapoints
            else:
                json_data = ""
                remain_data_point_index = 0
        if json_data != "":
            resp = rest_post_obj.post(karrios_rest_url, data=json_data, headers=headers)
            if resp.status_code != 204:
                pass
                # logger.debug("datapoints posted to kairosDb %s" % (resp.status_code))
                # else:
                # logger.debug("successful")
        # Reset self.karrios_data_points_list
        self.karrios_data_points_list = self.karrios_data_points_list[remain_data_point_index:]


class Hdhld(GenericSensor):
    def __init__(self):
        super(Hdhld, self).__init__()
        self.__handheld_activity = None
        self.__handheld_activity_confidence = None
        self.__handhel_lat = None
        self.__handhel_long = None
        self.attr_2_column_mapping["__handheld_activity"] = ("handheld_activity", "text")
        self.attr_2_column_mapping["__handheld_activity_confidence"] \
            = ("handheld_activity_confidence", "int")
        self.attr_2_column_mapping["__handhel_lat"] = ("handhel_lat", "float")
        self.attr_2_column_mapping["__handhel_long"] = ("handhel_long", "float")

    def get_sensor(self):
        print ("eventId: %s, deviceType: %s, deviceid: %s, eventtype: %s, " \
               "timestamp: %s, userid: %s, trainingMode: %s, handheldActivity: %s, " \
               "handheldActivityConfidence: %d, handhelLat %f, handhel_long %f" % (
                   self.__event_id, self.__device_type, self.__device_id,
                   self.__event_type, self.__timestamp, self.__user_id,
                   self.__training_mode, self.__handheld_activity,
                   self.__handheld_activity_confidence,
                   self.__handhel_lat,
                   self.__handhel_long))

    def set_sensor(self, **kwargs):
        super(Hdhld, self).set_sensor(**kwargs)
        self.__handheld_activity = kwargs.get("handheldActivity", "NA")
        self.__handheld_activity_confidence = kwargs.get("handheldActivityConfidence", 0)
        self.__handhel_lat = kwargs.get("handhelLat", 0.0)
        self.__handhel_long = kwargs.get("handhelLong", 0.0)


class Accelerometer(GenericSensor):
    def __init__(self):
        super(Accelerometer, self).__init__()
        self.__x = None
        self.__y = None
        self.__z = None
        self.attr_2_column_mapping["__x"] = ("x", "float")
        self.attr_2_column_mapping["__y"] = ("y", "float")
        self.attr_2_column_mapping["__z"] = ("z", "float")

    def set_sensor(self, **kwargs):
        super(Accelerometer, self).set_sensor(**kwargs)
        self.__x = kwargs.get("x", None)
        self.__y = kwargs.get("y", None)
        self.__z = kwargs.get("z", None)


class Gyroscope(GenericSensor):
    def __init__(self):
        super(Gyroscope, self).__init__()
        self.__x = None
        self.__y = None
        self.__z = None
        self.attr_2_column_mapping["__x"] = ("x", "float")
        self.attr_2_column_mapping["__y"] = ("y", "float")
        self.attr_2_column_mapping["__z"] = ("z", "float")

    def set_sensor(self, **kwargs):
        super(Gyroscope, self).set_sensor(**kwargs)
        self.__x = kwargs.get("x", None)
        self.__y = kwargs.get("y", None)
        self.__z = kwargs.get("z", None)


class Altimeter(GenericSensor):
    def __init__(self):
        super(Altimeter, self).__init__()
        self.__flights_ascended = None
        self.__flights_descended = None
        self.__rate = None
        self.__stepping_gain = None
        self.__stepping_loss = None
        self.__steps_ascended = None
        self.__steps_descended = None
        self.__total_gain = None
        self.__total_loss = None
        self.attr_2_column_mapping["__flights_ascended"] = ("flights_ascended", "int")
        self.attr_2_column_mapping["__flights_descended"] = ("flights_descended", "int")
        self.attr_2_column_mapping["__rate"] = ("rate", "float")
        self.attr_2_column_mapping["__stepping_gain"] = ("stepping_gain", "int")
        self.attr_2_column_mapping["__stepping_loss"] = ("stepping_loss", "int")
        self.attr_2_column_mapping["__steps_ascended"] = ("steps_ascended", "int")
        self.attr_2_column_mapping["__steps_descended"] = ("steps_descended", "int")
        self.attr_2_column_mapping["__total_gain"] = ("total_gain", "int")
        self.attr_2_column_mapping["__total_loss"] = ("total_loss", "int")

    def set_sensor(self, **kwargs):
        super(Altimeter, self).set_sensor(**kwargs)
        self.__flights_ascended = kwargs.get("flightsAscended", None)
        self.__flights_descended = kwargs.get("flightsDescended", None)
        self.__rate = kwargs.get("rate", None)
        self.__stepping_gain = kwargs.get("steppingGain", None)
        self.__stepping_loss = kwargs.get("steppingLoss", None)
        self.__steps_ascended = kwargs.get("stepsAscended", None)
        self.__steps_descended = kwargs.get("stepsDescended", None)
        self.__total_gain = kwargs.get("totalGain", None)
        self.__total_loss = kwargs.get("totalLoss", None)


class AmbientLight(GenericSensor):
    def __init__(self):
        super(AmbientLight, self).__init__()
        self.__brightness = None
        self.attr_2_column_mapping["__brightness"] = ("brightness", "int")

    def set_sensor(self, **kwargs):
        super(AmbientLight, self).set_sensor(**kwargs)
        self.__brightness = kwargs.get("brightness", None)


class Barometer(GenericSensor):
    def __init__(self):
        super(Barometer, self).__init__()
        self.__temperature = None
        self.__air_pressure = None
        self.attr_2_column_mapping["__temperature"] = ("temperature", "float")
        self.attr_2_column_mapping["__air_pressure"] = ("air_pressure", "float")

    def set_sensor(self, **kwargs):
        super(Barometer, self).set_sensor(**kwargs)
        self.__temperature = kwargs.get("temperature", None)
        self.__air_pressure = kwargs.get("airPressure", None)


class Calories(GenericSensor):
    def __init__(self):
        super(Calories, self).__init__()
        self.__calories = None
        self.attr_2_column_mapping["__calories"] = ("calories", "int")

    def set_sensor(self, **kwargs):
        super(Calories, self).set_sensor(**kwargs)
        self.__calories = kwargs.get("calories", None)


class Distance(GenericSensor):
    def __init__(self):
        super(Distance, self).__init__()
        self.__current_motion = None
        self.__pace = None
        self.__speed = None
        self.__total_distance = None
        self.attr_2_column_mapping["__current_motion"] = ("current_motion", "int")
        self.attr_2_column_mapping["__pace"] = ("pace", "float")
        self.attr_2_column_mapping["__speed"] = ("speed", "float")
        self.attr_2_column_mapping["__total_distance"] = ("total_distance", "int")

    def set_sensor(self, **kwargs):
        super(Distance, self).set_sensor(**kwargs)
        self.__current_motion = kwargs.get("currentMotion", None)
        self.__pace = kwargs.get("pace", None)
        self.__speed = kwargs.get("speed", None)
        self.__total_distance = kwargs.get("totalDistance", None)


class UV(GenericSensor):
    def __init__(self):
        super(UV, self).__init__()
        self.__index = None
        self.attr_2_column_mapping["__index"] = ("index_uv", "int")

    def set_sensor(self, **kwargs):
        super(UV, self).set_sensor(**kwargs)
        self.__index = kwargs.get("index", None)


class SkinTemperature(GenericSensor):
    def __init__(self):
        super(SkinTemperature, self).__init__()
        self.__temperature = None
        self.attr_2_column_mapping["__temperature"] = ("temperature", "float")

    def set_sensor(self, **kwargs):
        super(SkinTemperature, self).set_sensor(**kwargs)
        self.__temperature = kwargs.get("temperature", None)


class GSR(GenericSensor):
    def __init__(self):
        super(GSR, self).__init__()
        self.__resistance = None
        self.attr_2_column_mapping["__resistance"] = ("resistance", "int")

    def set_sensor(self, **kwargs):
        super(GSR, self).set_sensor(**kwargs)
        self.__resistance = kwargs.get("resistance", None)


class HeartRate(GenericSensor):
    def __init__(self):
        super(HeartRate, self).__init__()
        self.__rate = None
        self.__quality = None
        self.attr_2_column_mapping["__rate"] = ("rate", "int")
        self.attr_2_column_mapping["__quality"] = ("quality", "int")

    def set_sensor(self, **kwargs):
        super(HeartRate, self).set_sensor(**kwargs)
        self.__rate = kwargs.get("rate", None)
        self.__quality = kwargs.get("quality", None)


class RRInterval(GenericSensor):
    def __init__(self):
        super(RRInterval, self).__init__()
        self.__interval = None
        self.attr_2_column_mapping["__interval"] = ("interval", "float")

    def set_sensor(self, **kwargs):
        super(RRInterval, self).set_sensor(**kwargs)
        self.__interval = kwargs.get("interval", None)


class SensorFactory(object):
    def produce_sensor_object(self, sensor_type_name):
        """Return sensor object based on sensor type
            Args:
                sensor_type_name (str): validate type name of sensors like hdhld, accelerometer
        Returns:
            sensor object
        """
        if sensor_type_name.strip().lower() == "hdhld":
            return Hdhld()
        elif sensor_type_name.strip().lower() == "accelerometer" or sensor_type_name.strip().lower() == "accel":
            return Accelerometer()
        elif sensor_type_name.strip().lower() == "gyroscope":
            return Gyroscope()
        elif sensor_type_name.strip().lower() == "altimeter":
            return Altimeter()
        elif sensor_type_name.strip().lower() == "ambientlight":
            return AmbientLight()
        elif sensor_type_name.strip().lower() == "barometer":
            return Barometer()
        elif sensor_type_name.strip().lower() == "calorie":
            return Calories()
        elif sensor_type_name.strip().lower() == "distance":
            return Distance()
        elif sensor_type_name.strip().lower() == "uv":
            return UV()
        elif sensor_type_name.strip().lower() == "skintemperature":
            return SkinTemperature()
        elif sensor_type_name.strip().lower() == "gsr":
            return GSR()
        elif sensor_type_name.strip().lower() == "heartrate":
            return HeartRate()
        elif sensor_type_name.strip().lower() == "rrinterval":
            return RRInterval()
        else:
            return None


# ==============================================================================
# Function
# ==============================================================================
def process_data(iter):
    """Parse JSON data and write to its specific Cassandra Table and kairos database.
    Args:
        iter (iterator): records in Kafka topics
    """
    global valid_sensor_type_list, DISABLE_SENSOR_SET
    # Create cluster object and start session
    cluster_object = Cluster([cluster])
    session = cluster_object.connect(keyspace)

    # Construct instances of all subclasses of GenericSensor by SensorFactory.
    print "==> Construct instances of all subclasses of GenericSensor for CURRENT partition"
    sensor_object_dict = dict()
    for sensor_type_name in valid_sensor_type_list:
        sensor_object_dict[sensor_type_name.strip().lower()] = \
            SensorFactory().produce_sensor_object(sensor_type_name.strip().lower())

    # Loop records
    total_processed_line_number = dict()
    total_line_number = 0
    for record in iter:
        total_line_number += 1
        # print record
        if record <> '':
            # print record
            json_str = json.loads(record)
            normalized_sensor_type_name = json_str['eventtype'].lower().strip()
            # Specify the correct table for insertion
            if normalized_sensor_type_name not in DISABLE_SENSOR_SET:
                table = config_parser.get(APP_NAME, "cassandra.table." + json_str['eventtype'])
                try:
                    sensor_object_dict[normalized_sensor_type_name].set_sensor(**json_str)
                    sensor_object_dict[normalized_sensor_type_name].issue_insert_query_cassandra(table, session)
                    sensor_object_dict[normalized_sensor_type_name].append_karrios_data_points(table, re.compile)
                    sensor_object_dict[normalized_sensor_type_name].issue_insert_query_karrios(requests, json.dumps,
                                                                                   kairosdb_url, max_post_size)
                    total_processed_line_number.setdefault(normalized_sensor_type_name, 0)
                    total_processed_line_number[normalized_sensor_type_name] += 1
                except KeyError:
                    print "    There is NO sensor object available for this sensor type %s" % normalized_sensor_type_name
            else:
                print "    This sensor type %s is DISABLE, and SKIP .." % normalized_sensor_type_name
            total_line_number += 1
    cluster_object.shutdown()


    # Post the rest of the kairos data that didn't qualify because of the size limit
    for sensor_type_name, sensor_object in sensor_object_dict.items():
        if sensor_object:
            # Make sure sensor object is valid
            sensor_object.issue_insert_query_karrios(requests, json.dumps, kairosdb_url, max_post_size, True)
    print "    Total %d records in this partition, and total %s records are parsed SUCCESSFULLY. " \
          % (total_line_number, json.dumps(total_processed_line_number))

    # release memory for sensor_object_dict
    del sensor_object_dict


def valid_data(rdd):
    """Do transformation and filter out RDDs from DStream before writing data to Cassandra or KariosDB,
    and return transformed and filtered RDD
    Args:
        rdd (rdd):
    Return:
        rdd
    """
    # Create cluster object and start session
    global topics, zk_quorum, logger, process_start_time
    logger.debug("    %s" %(get_elapsed_time(process_start_time, time.time(), "Writing data to Cassandra and Karios")))
    number_of_records_in_rdd = rdd.count()
    if number_of_records_in_rdd == 0:
        logger.debug("    NO data is coming from topics %s in Kafka broker %s", " | ".join(topics.keys()), zk_quorum)
        return
    else:
        logger.debug("    Start proccessing %d reocrds for each partition ...", number_of_records_in_rdd)
        rdd.foreachPartition(process_data)

def get_elapsed_time(in_starttime_in_second, in_end_time_in_second, in_process_step_name):
    """Return elapsed time including hours, minutes and seconds.
    Args:
       in_starttime_in_second (int): elapsed time in seconds since UNIX epoch time
       in_end_time_in_second (int): elasped time in seconds since UNIX epoch time
       in_process_step_name (str): Nmae of process
    Return:
        rdd
    """
    duration_in_seconds = in_end_time_in_second - in_starttime_in_second
    out_second = int(duration_in_seconds) % 60
    minutes_amount = int(duration_in_seconds) // 60
    out_minute = minutes_amount % 60
    hours_amount = minutes_amount // 60
    return "    Total elapsed time of {} : {} Hours {} Minutes {} Seconds.\n".format(in_process_step_name, hours_amount
                                                                                     , out_minute,out_second)


# ==============================================================================
# Main
# ==============================================================================

if __name__ == "__main__":
    process_start_time = time.time()

    # Get all valid sensor type list
    valid_sensor_type_list = rta_constants.SENSORS_ACTIVITY_TYPE
    valid_sensor_type_list.extend(rta_constants.SENSORS_PHYSIO_TYPE)

    try:
        logging.config.fileConfig(rta_constants.PROPERTIES_LOG_FILE)
        logger = logging.getLogger(APP_NAME)
    except Exception as e:
        print "ERROR: CAN NOT instantiate logger with log properties file %s and application name %s" \
              % (rta_constants.PROPERTIES_LOG_FILE, APP_NAME)
        # e.
        sys.exit(-1)

    logger.info("==> Start running raw writer ...")
    logger.debug("   python version: %s" % sys.version_info)

    # Load default args from configuration file
    logger.info("==> Start instantiating config parse in properties file %s", rta_constants.PROPERTIES_FILE)
    config_parser = SafeConfigParser()
    config_parser.read(rta_constants.PROPERTIES_FILE)

    # Check the consistency of the APP_NAME section in rta.properties
    logger.info("==> Start getting variables in properties file %s", rta_constants.PROPERTIES_FILE)
    if ((not config_parser.has_section(APP_NAME)) |
            (not config_parser.has_option(rta_constants.FRAMEWORK_NAME, "zookeeper.host_port")) |
            (not config_parser.has_option(rta_constants.FRAMEWORK_NAME, "kafka.host_port")) |
            (not config_parser.has_option(APP_NAME, "kafka.data.in.topics")) |
            (not config_parser.has_section(rta_constants.FRAMEWORK_NAME)) |
            (not config_parser.has_option(rta_constants.FRAMEWORK_NAME, "cassandra.cluster")) |
            (not config_parser.has_option(rta_constants.FRAMEWORK_NAME, "cassandra.keyspace")) |
            (not config_parser.has_option(rta_constants.FRAMEWORK_NAME, "kafka.control.topic")) |
            (not config_parser.has_option(rta_constants.FRAMEWORK_NAME, "kafka.group")) |
            (not config_parser.has_option(rta_constants.FRAMEWORK_NAME, "spark.nb_threads")) |
            (not config_parser.has_option(rta_constants.FRAMEWORK_NAME, "kairosdb.url")) |
            (not config_parser.has_option(rta_constants.FRAMEWORK_NAME, "kairosdb.post.size")) |
            (not config_parser.has_option(rta_constants.FRAMEWORK_NAME, "spark.batch_duration"))):
        logger.error("properties file %s mal-formated. Missing attribute or section. \
                    Exit" % (rta_constants.PROPERTIES_FILE))
        sys.exit(-1)
    # Retrieve Configuration Parameters
    # logger.info("Initializing kafka stream context for sensor data")
    zk_quorum = config_parser.get(rta_constants.FRAMEWORK_NAME, "zookeeper.host_port")
    kafka_broker_list = config_parser.get(rta_constants.FRAMEWORK_NAME, "kafka.host_port")
    topics = config_parser.get(APP_NAME, "kafka.data.in.topics")
    # Split topics into a dict and remove empty strings e.g. {'topic1': 1, 'topic2': 1}
    # logger.debug("Format topics for RDD")
    topics = [x.strip() for x in topics.split(';')]
    topics = filter(None, topics)
    topics = dict(zip(topics, [1] * len(topics)))
    group = config_parser.get(rta_constants.FRAMEWORK_NAME, "kafka.group")
    num_threads = config_parser.get(rta_constants.FRAMEWORK_NAME, "spark.nb_threads")
    batch_duration = int(config_parser.get(rta_constants.FRAMEWORK_NAME, "spark.batch_duration"))
    kairosdb_url = config_parser.get(rta_constants.FRAMEWORK_NAME, "kairosdb.url")
    max_post_size = int(config_parser.get(rta_constants.FRAMEWORK_NAME, "kairosdb.post.size"))
    logger.info("    zookeeper.host_port: %s" % zk_quorum)
    logger.info("    topics: %s" % " | ".join(topics.keys()))
    logger.info("    kafka.group: %s" % group)
    logger.info("    Spark batch interval (in seconds) : %d" % batch_duration)
    logger.info("    kairos database REST URL: %s" % kairosdb_url)
    logger.info("    max number of data points in ONE post to karios db is %d" % max_post_size)

    # Configure Spark
    logger.info("==> Initializing Spark Context ...")
    conf = SparkConf().setAppName(APP_NAME)
    # conf = conf.setMaster("local[*]")
    sc = SparkContext(conf=conf)
    ssc = StreamingContext(sc, batch_duration)

    # Configure Cassandra
    logger.info("==> Initializing Cassandra variables ...")
    cluster = config_parser.get(rta_constants.FRAMEWORK_NAME, "cassandra.cluster")
    keyspace = config_parser.get(rta_constants.FRAMEWORK_NAME, "cassandra.keyspace")
    logger.info("    cassandra.cluster: %s" % cluster)
    logger.info("    cassandra.keyspace: %s" % keyspace)

    # Connection object is created for each RDD partition
    logger.info("==> Creating Spark DStream ...")
    try:
        # kafka_stream = KafkaUtils.createStream(ssc, zk_quorum, group, topics).map(lambda x: x[1])
        kafka_stream = KafkaUtils.createDirectStream(ssc, topics.keys(), {"metadata.broker.list": kafka_broker_list})
        lines = kafka_stream.map(lambda x: x[1])
        # lines.pprint()
        lines.foreachRDD(lambda rdd: valid_data(rdd))
        # kafka_stream.foreachRDD(lambda rdd: rdd.foreachPartition(process_data))
        logger.debug("Process controller started. Entering kafka ctrl listening loop")
        ssc.start()
        ssc.awaitTermination()
    except KeyboardInterrupt:
        logger.debug("    %s\n    %s" % ("Skip", get_elapsed_time(process_start_time, time.time(), APP_NAME)))
    except Exception as e:
        process_end_time = time.time()
        logger.error("    %s\n    %s" %(e.message, get_elapsed_time(process_start_time, process_end_time, APP_NAME)))
