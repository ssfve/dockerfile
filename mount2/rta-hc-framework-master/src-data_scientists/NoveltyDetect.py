# -*- coding: utf-8 -*-
"""
Created on Tue Apr 12 17:12:29 2016

@author: planat
"""
import bif_parser

'''
__import__ is a Python function that will import a package using a string as 
the name of the package. It returns a new object that represents the imported 
package. 

So foo = __import__('bar') will import a package named bar and store 
a reference to its objects in a local object variable foo.
'''

# .bif file should be in the same folder with python code
name = "bnhcband"
module_name = bif_parser.parse(name) #parse .bif file into python module
module = __import__(module_name) #import the module
bg = module.create_bbn() #create bayesian network
from collections import OrderedDict
# define NoveltyDetect Class
class NoveltyDetect:
    def __init__(self, novel_threshold, novel_window_size_limit, novel_rate_theshold):
        
        '''
            parameters initiatilation      
        '''
        self.novel_threshold = novel_threshold
        self.novel_window_size_limit = novel_window_size_limit
        self.novel_rate_theshold =novel_rate_theshold
        # store novel points (temperature, heartrate and etc. whose probability is less than threshold) in each novel timestamp
        self.novel_points = []
        # store novel_points with format 1, 0
        self.novel_timeframes = []
        
    # parse the intervals in .bif file to extract the specific values    
    def parse_values(self, filename):
        GSR_RESISTANCE = []
        SKTMP_TEMPERATURE = []
        HR_RATE = []
        RRI_INTERVAL = []
        infile = open(filename+'.bif')
        while True:
            line = infile.readline()
            # parse the GSR_RESISTANCE: { [390_1.4e+03], _1.4e+03_4.27e+03], _4.27e+03_9.16e+03], _9.16e+03_3.4e+05] };
            if line.startswith('variable GSR_RESISTANCE'):
                line = infile.readline()
                left1 = line.find('[')
                left1 = line.find('[',left1+1)
                right1 = line.find('_')
                GSR_RESISTANCE_num1 = line[left1+1:right1]
                GSR_RESISTANCE.append(GSR_RESISTANCE_num1)
                left1 = line.find('_',left1+1)
                right1 = line.find(']',right1+1)
                GSR_RESISTANCE_num2 = line[left1+1:right1]   
                GSR_RESISTANCE.append(GSR_RESISTANCE_num2)
                left1 = line.find('_',left1+1)
                right1 = line.find('_',left1+1)
                GSR_RESISTANCE_num3 = line[left1+1:right1]
                
                left1 = line.find('_',left1+1)
                right1 = line.find(']',left1+1)
                GSR_RESISTANCE_num4 = line[left1+1:right1]
                GSR_RESISTANCE.append(GSR_RESISTANCE_num4)
                left1 = line.find('_',left1+1)
                right1 = line.find('_',left1+1)
                GSR_RESISTANCE_num5 = line[left1+1:right1]
            
                left1 = line.find('_',left1+1)
                right1 = line.find(']',left1+1)
                GSR_RESISTANCE_num6 = line[left1+1:right1]
                GSR_RESISTANCE.append(GSR_RESISTANCE_num6)
                left1 = line.find('_',left1+1)
                right1 = line.find('_',left1+1)
                GSR_RESISTANCE_num7 = line[left1+1:right1]
               
                left1 = line.find('_',left1+1)
                right1 = line.find(']',left1+1)
                GSR_RESISTANCE_num8 = line[left1+1:right1]
                GSR_RESISTANCE.append(GSR_RESISTANCE_num8)
            # parse the SKTMP_TEMPERATURE { [29.1_29.8], _29.8_30.7], _30.7_31.3], _31.3_31.5] };    
            if line.startswith('variable SKTMP_TEMPERATURE'):
                line = infile.readline()
                left1 = line.find('[')
                left1 = line.find('[',left1+1)
                right1 = line.find('_')
                SKTMP_TEMPERATURE_num1 = line[left1+1:right1]
                SKTMP_TEMPERATURE.append(SKTMP_TEMPERATURE_num1)
                left1 = line.find('_',left1+1)
                right1 = line.find(']',right1+1)
                SKTMP_TEMPERATURE_num2 = line[left1+1:right1]   
                SKTMP_TEMPERATURE.append(SKTMP_TEMPERATURE_num2)
                left1 = line.find('_',left1+1)
                right1 = line.find('_',left1+1)
                SKTMP_TEMPERATURE_num3 = line[left1+1:right1]
                
                left1 = line.find('_',left1+1)
                right1 = line.find(']',left1+1)
                SKTMP_TEMPERATURE_num4 = line[left1+1:right1]
                SKTMP_TEMPERATURE.append(SKTMP_TEMPERATURE_num4)
                left1 = line.find('_',left1+1)
                right1 = line.find('_',left1+1)
                SKTMP_TEMPERATURE_num5 = line[left1+1:right1]
            
                left1 = line.find('_',left1+1)
                right1 = line.find(']',left1+1)
                SKTMP_TEMPERATURE_num6 = line[left1+1:right1]
                SKTMP_TEMPERATURE.append(SKTMP_TEMPERATURE_num6)
                left1 = line.find('_',left1+1)
                right1 = line.find('_',left1+1)
                SKTMP_TEMPERATURE_num7 = line[left1+1:right1]
               
                left1 = line.find('_',left1+1)
                right1 = line.find(']',left1+1)
                SKTMP_TEMPERATURE_num8 = line[left1+1:right1]   
                SKTMP_TEMPERATURE.append(SKTMP_TEMPERATURE_num8)
            # parse the  HR_RATE  { [64_72], _72_75], _75_79], _79_108] };  
            if line.startswith('variable HR_RATE'):
                line = infile.readline()
                left1 = line.find('[')
                left1 = line.find('[',left1+1)
                right1 = line.find('_')
                HR_RATE_num1 = line[left1+1:right1]
                HR_RATE.append(HR_RATE_num1)
                left1 = line.find('_',left1+1)
                right1 = line.find(']',right1+1)
                HR_RATE_num2 = line[left1+1:right1]   
                HR_RATE.append(HR_RATE_num2)
                left1 = line.find('_',left1+1)
                right1 = line.find('_',left1+1)
                HR_RATE_num3 = line[left1+1:right1]
                
                left1 = line.find('_',left1+1)
                right1 = line.find(']',left1+1)
                HR_RATE_num4 = line[left1+1:right1]
                HR_RATE.append(HR_RATE_num4)
                left1 = line.find('_',left1+1)
                right1 = line.find('_',left1+1)
                HR_RATE_num5 = line[left1+1:right1]
            
                left1 = line.find('_',left1+1)
                right1 = line.find(']',left1+1)
                HR_RATE_num6 = line[left1+1:right1]
                HR_RATE.append(HR_RATE_num6)
                left1 = line.find('_',left1+1)
                right1 = line.find('_',left1+1)
                HR_RATE_num7 = line[left1+1:right1]
               
                left1 = line.find('_',left1+1)
                right1 = line.find(']',left1+1)
                HR_RATE_num8 = line[left1+1:right1]    
                HR_RATE.append(HR_RATE_num8)
            # parse the RRI_INTERVAL { [0.0332_0.647], _0.647_0.763], _0.763_0.846], _0.846_1.48] };    
            if line.startswith('variable RRI_INTERVAL'):
                line = infile.readline()
                left1 = line.find('[')
                left1 = line.find('[',left1+1)
                right1 = line.find('_')
                RRI_INTERVAL_num1 = line[left1+1:right1]
                RRI_INTERVAL.append(RRI_INTERVAL_num1)
                left1 = line.find('_',left1+1)
                right1 = line.find(']',right1+1)
                RRI_INTERVAL_num2 = line[left1+1:right1]   
                RRI_INTERVAL.append(RRI_INTERVAL_num2)
                left1 = line.find('_',left1+1)
                right1 = line.find('_',left1+1)
                RRI_INTERVAL_num3 = line[left1+1:right1]
                
                left1 = line.find('_',left1+1)
                right1 = line.find(']',left1+1)
                RRI_INTERVAL_num4 = line[left1+1:right1]
                RRI_INTERVAL.append(RRI_INTERVAL_num4)
                left1 = line.find('_',left1+1)
                right1 = line.find('_',left1+1)
                RRI_INTERVAL_num5 = line[left1+1:right1]
            
                left1 = line.find('_',left1+1)
                right1 = line.find(']',left1+1)
                RRI_INTERVAL_num6 = line[left1+1:right1]
                RRI_INTERVAL.append(RRI_INTERVAL_num6)
                left1 = line.find('_',left1+1)
                right1 = line.find('_',left1+1)
                RRI_INTERVAL_num7 = line[left1+1:right1]
               
                left1 = line.find('_',left1+1)
                right1 = line.find(']',left1+1)
                RRI_INTERVAL_num8 = line[left1+1:right1]
                RRI_INTERVAL.append(RRI_INTERVAL_num8)
            # stop parsing    
            if line.startswith('probability'):
                #print [GSR_RESISTANCE, SKTMP_TEMPERATURE, HR_RATE, RRI_INTERVAL]
                return  GSR_RESISTANCE, SKTMP_TEMPERATURE, HR_RATE, RRI_INTERVAL
                break

    def detect_novelty(self, physio_events_list, activity_label):
        
        '''
        
        physio_events_list
            event1: {"eventid":2808d537-c37b-481c-b6e9-b96328e7bcd5, "timestamp":1457003498147, "sensorType":"heartRate", "rate":65}
            event2: {"eventid":2808d537-c37b-481c-b6e9-b96328e7bcd6, "timestamp":1457003498147, "sensorType":"rrinterval", "rate":0.64}
            event3: {"eventid":2808d537-c37b-481c-b6e9-b96328e7bcd7, "timestamp":1457003498147, "sensorType":"gsr", "rate":1.64}
            event4: {"eventid":2808d537-c37b-481c-b6e9-b96328e7bcd8, "timestamp":1457003498147, "sensorType":"skinTemperature", "rate":38.64}
        activity_label    
            event5: {"eventid":2808d537-c37b-481c-b6e9-b96328e7bcd9, "timestamp":1457003498147, "sensorType":"activity", "result":WALKING}
        
        '''
        # obtain the specific values and store them in the corresponding list
        GSR_RESISTANCE, SKTMP_TEMPERATURE, HR_RATE, RRI_INTERVAL = self.parse_values(name)
#        print physio_events_list[0]['temperature']      
        # put the specific value in the corresponding interval
        if (float(physio_events_list[0]['temperature']) >= float(SKTMP_TEMPERATURE[0]) and  float(physio_events_list[0]['temperature']) <= float(SKTMP_TEMPERATURE[1])):
            SKTMP_TEMPERATURE_VALUE = '[' + SKTMP_TEMPERATURE[0] + '_' + SKTMP_TEMPERATURE[1] + ']'
        elif (float(physio_events_list[0]['temperature']) > float(SKTMP_TEMPERATURE[1]) and  float(physio_events_list[0]['temperature']) <= float(SKTMP_TEMPERATURE[2])):
            SKTMP_TEMPERATURE_VALUE = '_' + SKTMP_TEMPERATURE[1] + '_' + SKTMP_TEMPERATURE[2] + ']'
        elif (float(physio_events_list[0]['temperature']) > float(SKTMP_TEMPERATURE[2]) and  float(physio_events_list[0]['temperature']) <= float(SKTMP_TEMPERATURE[3])):
            SKTMP_TEMPERATURE_VALUE = '_' + SKTMP_TEMPERATURE[2] + '_' + SKTMP_TEMPERATURE[3] + ']'
        elif (float(physio_events_list[0]['temperature']) > float(SKTMP_TEMPERATURE[3]) and  float(physio_events_list[0]['temperature']) <= float(SKTMP_TEMPERATURE[4])):
            SKTMP_TEMPERATURE_VALUE = '_' + SKTMP_TEMPERATURE[3] + '_' + SKTMP_TEMPERATURE[4] + ']'
        else:
            SKTMP_TEMPERATURE_VALUE = physio_events_list[0]['temperature']
#        print SKTMP_TEMPERATURE_VALUE
#        print physio_events_list[1]['resistance']        
        if (float(physio_events_list[1]['resistance']) >= float(GSR_RESISTANCE[0]) and  float(physio_events_list[1]['resistance']) <= float(GSR_RESISTANCE[1])):
            GSR_RESISTANCE_VALUE = '[' + GSR_RESISTANCE[0] + '_' + GSR_RESISTANCE[1] + ']'
        elif (float(physio_events_list[1]['resistance']) > float(GSR_RESISTANCE[1]) and  float(physio_events_list[1]['resistance']) <= float(GSR_RESISTANCE[2])):
            GSR_RESISTANCE_VALUE = '_' + GSR_RESISTANCE[1] + '_' + GSR_RESISTANCE[2] + ']'
        elif (float(physio_events_list[1]['resistance']) > float(GSR_RESISTANCE[2]) and  float(physio_events_list[1]['resistance']) <= float(GSR_RESISTANCE[3])):
            GSR_RESISTANCE_VALUE = '_' + GSR_RESISTANCE[2] + '_' + GSR_RESISTANCE[3] + ']'
        elif (float(physio_events_list[1]['resistance']) > float(GSR_RESISTANCE[3]) and  float(physio_events_list[1]['resistance']) <= float(GSR_RESISTANCE[4])):
            GSR_RESISTANCE_VALUE = '_' + GSR_RESISTANCE[3] + '_' + GSR_RESISTANCE[4] + ']'
        else:
            GSR_RESISTANCE_VALUE = physio_events_list[1]['resistance']
#        print GSR_RESISTANCE_VALUE
#        print type(physio_events_list[2]['rate'])        
        if (float(physio_events_list[2]['rate']) >= float(HR_RATE[0]) and  float(physio_events_list[2]['rate']) <= float(HR_RATE[1])):
            HR_RATE_VALUE = '[' + HR_RATE[0] + '_' + HR_RATE[1] + ']'
        elif (float(physio_events_list[2]['rate']) > float(HR_RATE[1]) and  float(physio_events_list[2]['rate']) <= float(HR_RATE[2])):
            HR_RATE_VALUE = '_' + HR_RATE[1] + '_' + HR_RATE[2] + ']'
        elif (float(physio_events_list[2]['rate']) > float(HR_RATE[2]) and  float(physio_events_list[2]['rate']) <= float(HR_RATE[3])):
            HR_RATE_VALUE= '_' + HR_RATE[2] + '_' + HR_RATE[3] + ']'
        elif (float(physio_events_list[2]['rate']) > float(HR_RATE[3]) and  float(physio_events_list[2]['rate']) <= float(HR_RATE[4])):
            HR_RATE_VALUE = '_' + HR_RATE[3] + '_' + HR_RATE[4] + ']'
        else:
            HR_RATE_VALUE = physio_events_list[2]['rate']
#        print HR_RATE_VALUE
#        print physio_events_list[3]['interval']         
        if (float(physio_events_list[3]['interval']) >= float(RRI_INTERVAL[0]) and  float(physio_events_list[3]['interval']) <= float(RRI_INTERVAL[1])):
            RRI_INTERVAL_VALUE = '[' + RRI_INTERVAL[0] + '_' + RRI_INTERVAL[1] + ']'
        elif (float(physio_events_list[3]['interval']) > float(RRI_INTERVAL[1]) and  float(physio_events_list[3]['interval']) <= float(RRI_INTERVAL[2])):
            RRI_INTERVAL_VALUE = '_' + RRI_INTERVAL[1] + '_' + RRI_INTERVAL[2] + ']'
        elif (float(physio_events_list[3]['interval']) > float(RRI_INTERVAL[2]) and  float(physio_events_list[3]['interval']) <= float(RRI_INTERVAL[3])):
            RRI_INTERVAL_VALUE = '_' + RRI_INTERVAL[2] + '_' + RRI_INTERVAL[3] + ']'
        elif (float(physio_events_list[3]['interval']) > float(RRI_INTERVAL[3]) and  float(physio_events_list[3]['interval']) <= float(RRI_INTERVAL[4])):
            RRI_INTERVAL_VALUE = '_' + RRI_INTERVAL[3] + '_' + RRI_INTERVAL[4] + ']'
        else:
            RRI_INTERVAL_VALUE = physio_events_list[3]['interval']
#        print RRI_INTERVAL_VALUE        
#            Activity_VALUE = activity_label[i/4]['result']     
        Activity_VALUE = activity_label['activity']
#        print Activity_VALUE

        # if any ofthe four evidence events is out of the four intervals definted in the bif file, the fifth event probability should be 0        
        if (SKTMP_TEMPERATURE_VALUE == physio_events_list[0]['temperature'] or GSR_RESISTANCE_VALUE == physio_events_list[1]['resistance'] or HR_RATE_VALUE == physio_events_list[2]['rate'] or RRI_INTERVAL_VALUE == physio_events_list[3]['interval']): 
            SKTMP_TEMPERATURE_prob = 0.0    
            GSR_RESISTANCE_prob = 0.0  
            HR_RATE_prob = 0.0    
            RRI_INTERVAL_prob = 0.0    
            Activity_prob = 0.0    
        else:
            # call the BNN query
            SKTMP_TEMPERATURE_prob = bg.query(HR_RATE=HR_RATE_VALUE, Activity=Activity_VALUE, GSR_RESISTANCE=GSR_RESISTANCE_VALUE, RRI_INTERVAL=RRI_INTERVAL_VALUE)[('SKTMP_TEMPERATURE', SKTMP_TEMPERATURE_VALUE)]    
            GSR_RESISTANCE_prob = bg.query(HR_RATE=HR_RATE_VALUE, Activity=Activity_VALUE, SKTMP_TEMPERATURE=SKTMP_TEMPERATURE_VALUE, RRI_INTERVAL=RRI_INTERVAL_VALUE)[('GSR_RESISTANCE', GSR_RESISTANCE_VALUE)]  
            HR_RATE_prob = bg.query(SKTMP_TEMPERATURE=SKTMP_TEMPERATURE_VALUE, Activity=Activity_VALUE, GSR_RESISTANCE=GSR_RESISTANCE_VALUE, RRI_INTERVAL=RRI_INTERVAL_VALUE)[('HR_RATE', HR_RATE_VALUE)]    
            RRI_INTERVAL_prob = bg.query(HR_RATE=HR_RATE_VALUE, Activity=Activity_VALUE, GSR_RESISTANCE=GSR_RESISTANCE_VALUE, SKTMP_TEMPERATURE=SKTMP_TEMPERATURE_VALUE)[('RRI_INTERVAL', RRI_INTERVAL_VALUE)]    
            Activity_prob = bg.query(HR_RATE=HR_RATE_VALUE, SKTMP_TEMPERATURE=SKTMP_TEMPERATURE_VALUE, GSR_RESISTANCE=GSR_RESISTANCE_VALUE, RRI_INTERVAL=RRI_INTERVAL_VALUE)[('Activity', Activity_VALUE)]    
            
#            print SKTMP_TEMPERATURE_prob  
#            print GSR_RESISTANCE_prob  
#            print HR_RATE_prob  
#            print RRI_INTERVAL_prob 
#            print Activity_prob          
#            print self.novel_threshold
#       
        # store the current novel point, if any of the five probability is less than the threshold, it will be added in the novel_point list    
        novel_point = []
        if (SKTMP_TEMPERATURE_prob < self.novel_threshold or HR_RATE_prob < self.novel_threshold or GSR_RESISTANCE_prob < self.novel_threshold or RRI_INTERVAL_prob < self.novel_threshold or Activity_prob < self.novel_threshold):
            if SKTMP_TEMPERATURE_prob < self.novel_threshold:                
                novel_point.append({'in_events' : [{'id':activity_label['eventId']}, {'id':physio_events_list[1]['eventId']}, {'id':physio_events_list[2]['eventId']}, {'id':physio_events_list[3]['eventId']}], 'out_event':physio_events_list[0]['eventId'], 'result-percentage':SKTMP_TEMPERATURE_prob}) 
             
            if GSR_RESISTANCE_prob < self.novel_threshold:
                novel_point.append({'in_events' : [{'id':physio_events_list[0]['eventId']}, {'id':activity_label['eventId']}, {'id':physio_events_list[2]['eventId']}, {'id':physio_events_list[3]['eventId']}], 'out_event':physio_events_list[1]['eventId'], 'result-percentage':GSR_RESISTANCE_prob}) 
             
            if HR_RATE_prob < self.novel_threshold:
                novel_point.append({'in_events' : [{'id':physio_events_list[0]['eventId']}, {'id':physio_events_list[1]['eventId']}, {'id':activity_label['eventId']}, {'id':physio_events_list[3]['eventId']}], 'out_event':physio_events_list[2]['eventId'], 'result-percentage':HR_RATE_prob}) 
             
            if RRI_INTERVAL_prob < self.novel_threshold:
                novel_point.append({'in_events' : [{'id':physio_events_list[0]['eventId']}, {'id':physio_events_list[1]['eventId']}, {'id':physio_events_list[2]['eventId']}, {'id':activity_label['eventId']}], 'out_event':physio_events_list[3]['eventId'], 'result-percentage':RRI_INTERVAL_prob}) 
             
            if Activity_prob < self.novel_threshold:
                novel_point.append({'in_events' : [{'id':physio_events_list[0]['eventId']}, {'id':physio_events_list[1]['eventId']}, {'id':physio_events_list[2]['eventId']}, {'id':physio_events_list[3]['eventId']}], 'out_event':activity_label['eventId'], 'result-percentage':Activity_prob})                    
            # append the novel_point    
            self.novel_points.append(novel_point)
            # append 1 since it is novel point
            self.novel_timeframes.append(1)
        else:
            self.novel_points.append(0)
            self.novel_timeframes.append(0)
        # if the length of novel points is less than window size, set the rate and event is none    
        if len(self.novel_timeframes) < self.novel_window_size_limit:
            novel_rate = None
            novel_event = None
        # if the length reach the limit, calculate the novel_rate 
        elif len(self.novel_timeframes) == self.novel_window_size_limit:
            novel_rate = sum(self.novel_timeframes)/float(self.novel_window_size_limit)
            # if novel_rate is above threshold, then output the novel_event, otherwise output zero
            if novel_rate > self.novel_rate_theshold:
                novel_event = self.novel_points
            else:
                novel_event = None
        else:
            # if the lenght is longer than the window size, need to shift the window to right for one element
            self.novel_timeframes = self.novel_timeframes[1:]
            self.novel_points = self.novel_points[1:]
            novel_rate = sum(self.novel_timeframes)/float(self.novel_window_size_limit)
            #compare with the threshold
            if novel_rate > self.novel_rate_theshold:
                novel_event = self.novel_points
            else:
                novel_event = None
        # return the novel_result
        novel_result = OrderedDict()
        novel_result['novel_rate'] = novel_rate
        novel_result['novel_timeframe'] = novel_event
        return novel_result 


import json
novel_data = []
# read the json file and store in novel_data
for line in open("novelty_traffic1.json", 'r'):
    novel_data.append(json.loads(line))
# create a object with pre-difined arguments
Novelty = NoveltyDetect(0.3, 30, 0.4)
with open('novelty_result.json', 'w') as fp:
    # extract each five lines as a block
    for i in range(0, len(novel_data), 5):
        physio_events_list = []
        physio_events_list.append(novel_data[i+2])
        physio_events_list.append(novel_data[i+1])
        physio_events_list.append(novel_data[i])
        physio_events_list.append(novel_data[i+3])
        activity_label = novel_data[i+4]                    
        # output the result in JSON file
        json.dump(Novelty.detect_novelty(physio_events_list, activity_label), fp)
        fp.write('\n')
       