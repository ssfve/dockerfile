'''
Created on Feb 13, 2016

@author: planat
'''

############################## ActivityDataset class #########################################

class ActivityDataset:
    'Activity Data set'
    
    
    def __init__(self):
        self.SENSORS_TYPE = ["accelerometer","gyroscope","altimeter","ambientLight","barometer","calorie","distance","uv","contact","pedometer"]
    
    #####################################################################################
    # Array Part
    def add_accl_Arr(self,arr_accl):
        '''
        format of arr_accl
        -----------------
        # eventId, deviceType, deviceid, timestamp, userid, trainingMode, x, y, z
        # [["5321bc0a-d35a-4fde-a2fa-e7a766c459cc",""msbad2","b81e905908354542",1455267743619,"vincent.planat@hpe.com","NONE",-0.982422,0.055908,-0.183105],
        # ["5321bc0a-d35a-4fde-a2fa-e7a766c459cc",""msbad2","b81e905908354542",1455267743620,"vincent.planat@hpe.com","NONE",-0.983422,0.145908,-0.343105]]
        '''        
        self.arr_accl       = arr_accl

    def add_gyro_arr(self,arr_gyro):
        '''
        format of arr_gyro
        -----------------
        # eventId, deviceType, deviceid, timestamp, userid, trainingMode, x, y, z
        #[["5321bc0a-d35a-4fde-a2fa-e7a766c459cc",""msbad2","b81e905908354542",1455267743619,"vincent.planat@hpe.com","NONE",-0.982422,0.055908,-0.183105],
        # ["5321bc0a-d35a-4fde-a2fa-e7a766c459cc",""msbad2","b81e905908354542",1455267743620,"vincent.planat@hpe.com","NONE",-0.983422,0.145908,-0.343105]]
        '''        
        self.arr_gyro       = arr_gyro

    def add_altm_arr(self,arr_altm):
        '''
        format of arr_altm
        -----------------
        # eventId, deviceType, deviceid, timestamp, userid, trainingMode, flightsAscended, flightsDescended, rate, steppingGain, steppingLoss, stepsAscended, stepsDescended, totalGain, totalLoss
        #[["5321bc0a-d35a-4fde-a2fa-e7a766c459cc",""msbad2","b81e905908354542",1455267743619,"vincent.planat@hpe.com","NONE",4, 3, -1, 1062, 904, 102, 242, 4706, 3048]
        # ["5321bc0a-d35a-4fde-a2fa-e7a766c459cc",""msbad2","b81e905908354542",1455267743619,"vincent.planat@hpe.com","NONE",2, 4, -1, 1072, 910, 105, 242, 4710, 3050]]
        '''        
        self.arr_altm       = arr_altm

    def add_ablightl_arr(self,arr_ablight):
        '''
        format of arr_ablight
        -----------------
        # eventId, deviceType, deviceid, timestamp, userid, trainingMode, brightness
        #[["5321bc0a-d35a-4fde-a2fa-e7a766c459cc",""msbad2","b81e905908354542",1455267743619,"vincent.planat@hpe.com","NONE",73],
        # ["5321bc0a-d35a-4fde-a2fa-e7a766c459cc",""msbad2","b81e905908354542",1455267743620,"vincent.planat@hpe.com","NONE",77]]
        '''        
        self.arr_ablight       = arr_ablight

    def add_brm_arr(self,arr_barm):
        '''
        format of arr_barm
        -----------------
        # eventId, deviceType, deviceid, timestamp, userid, trainingMode, airPressure, temperature
        #[["5321bc0a-d35a-4fde-a2fa-e7a766c459cc",""msbad2","b81e905908354542",1455267743619,"vincent.planat@hpe.com","NONE",987.90625, 29.045833],
        # ["5321bc0a-d35a-4fde-a2fa-e7a766c459cc",""msbad2","b81e905908354542",1455267743620,"vincent.planat@hpe.com","NONE",987.90625, 30.045833]]
        '''        
        self.arr_barm       = arr_barm

    def add_cal_arr(self,arr_cal):
        '''
        format of arr_cal
        -----------------
        # eventId, deviceType, deviceid, timestamp, userid, trainingMode, calories
        #[["5321bc0a-d35a-4fde-a2fa-e7a766c459cc",""msbad2","b81e905908354542",1455267743619,"vincent.planat@hpe.com","NONE",17064],
        # ["5321bc0a-d35a-4fde-a2fa-e7a766c459cc",""msbad2","b81e905908354542",1455267743620,"vincent.planat@hpe.com","NONE",18564]]
        '''        
        self.arr_cal       = arr_cal

    def add_dst_arr(self,arr_dst):
        '''
        format of arr_dst
        -----------------
        # eventId, deviceType, deviceid, timestamp, userid, trainingMode, currentMotion, pace, speed, totalDistance
        #[["5321bc0a-d35a-4fde-a2fa-e7a766c459cc",""msbad2","b81e905908354542",1455267743619,"vincent.planat@hpe.com","NONE",1, 0.0, 0.0, 2654148],
        # ["5321bc0a-d35a-4fde-a2fa-e7a766c459cc",""msbad2","b81e905908354542",1455267743620,"vincent.planat@hpe.com","NONE",1, 0.0, 0.0, 2654154]]
        '''        
        self.arr_dst       = arr_dst

    def add_uv_arr(self,arr_uv):
        '''
        format of arr_dst
        -----------------
        # eventId, deviceType, deviceid, timestamp, userid, trainingMode, index
        #[["5321bc0a-d35a-4fde-a2fa-e7a766c459cc",""msbad2","b81e905908354542",1455267743619,"vincent.planat@hpe.com","NONE",0],
        # ["5321bc0a-d35a-4fde-a2fa-e7a766c459cc",""msbad2","b81e905908354542",1455267743620,"vincent.planat@hpe.com","NONE",0]]
        '''        
        self.arr_uv       = arr_uv


    #####################################################################################
    # RDD part
    def add_accl_rdd(self,rdd_accl):
        self.rdd_accl       = rdd_accl    
    def add_altm_rdd(self,rdd_altm):        
        self.rdd_altm       = rdd_altm
    def add_ablightl_rdd(self,rdd_amblight):
        self.rdd_amblight   = rdd_amblight
    def add_barm_rdd(self,rdd_barm):
        self.rdd_barm       = rdd_barm
    def add_cal_rdd(self,rdd_cal):
        self.rdd_cal        = rdd_cal
    def add_contact_rdd(self,rdd_contact):
        self.rdd_contact    = rdd_contact
    def add_dist_rdd(self,rdd_dist):
        self.rdd_dist       = rdd_dist
    def add_gyro_rdd(self,rdd_gyro):
        self.rdd_gyro       = rdd_gyro
    def add_pedom_rdd(self,rdd_pedom):
        self.rdd_pedom      = rdd_pedom
    def add_uv_rdd(self,rdd_uv):
        self.rdd_uv         = rdd_uv

    #####################################################################################
    # Statistics
    def get_arr_stats(self):
        stat_report = "ActivityDataset statistics (Arr)\n"
        line = "   arr_accl    size:"+str(len(self.arr_accl))
        stat_report = stat_report + line + "\n"
        line = "   arr_gyro    size:"+str(len(self.arr_gyro))
        stat_report = stat_report + line + "\n"
        line = "   arr_altm    size:"+str(len(self.arr_altm))
        stat_report = stat_report + line + "\n"
        line = "   arr_ablight    size:"+str(len(self.arr_ablight))
        stat_report = stat_report + line + "\n"
        line = "   arr_barm    size:"+str(len(self.arr_barm))
        stat_report = stat_report + line + "\n"
        line = "   arr_dst    size:"+str(len(self.arr_dst))
        stat_report = stat_report + line + "\n"
        line = "   arr_uv    size:"+str(len(self.arr_uv))
        stat_report = stat_report + line + "\n"
        return stat_report

    def get_rdd_stats(self):
        stat_report = "ActivityDataset statistics (Rdd)\n"
        line = "   arr_accl    size:"+str(self.rdd_accl.count())
        stat_report = stat_report + line + "\n"
        line = "   arr_gyro    size:"+str(self.rdd_gyro.count())
        stat_report = stat_report + line + "\n"
        line = "   arr_altm    size:"+str(self.rdd_altm.count())
        stat_report = stat_report + line + "\n"
        line = "   arr_ablight    size:"+str(self.rdd_amblight.count())
        stat_report = stat_report + line + "\n"
        line = "   arr_barm    size:"+str(self.rdd_barm.count())
        stat_report = stat_report + line + "\n"
        line = "   arr_dst    size:"+str(self.rdd_dist.count())
        stat_report = stat_report + line + "\n"
        line = "   arr_uv    size:"+str(self.rdd_uv.count())
        stat_report = stat_report + line + "\n"
        return stat_report


############################################################################################
############################## PhysioDataset class #########################################

class PhysioDataset:
    'Physio Data set'
    SENSORS_TYPE = []
    
    #def __init__(self,rdd_gsr,rdd_heartr,rdd_rri,rdd_skint):
    def __init__(self):
        self.SENSORS_TYPE = ["skinTemperature","heartRate","gsr","rrinterval"]
    '''
        self.rdd_gsr        = rdd_gsr
        self.rdd_heartr     = rdd_heartr
        self.rdd_rri        = rdd_rri
        self.rdd_skint      = rdd_skint
    '''
  
      #####################################################################################
    # Array Part
    def add_skin_templ_arr(self,arr_skint):
        '''
        format of arr_skint
        -----------------
        # eventId, deviceType, deviceid, timestamp, userid, trainingMode, temperature
        #[["5321bc0a-d35a-4fde-a2fa-e7a766c459cc",""msbad2","b81e905908354542",1455267743619,"vincent.planat@hpe.com","NONE",30.41],
        # ["5321bc0a-d35a-4fde-a2fa-e7a766c459cc",""msbad2","b81e905908354542",1455267743620,"vincent.planat@hpe.com","NONE",30.45]]

        '''        
        self.arr_skint       = arr_skint

    def add_heart_rate_arr(self,arr_heartr):
        '''
        format of arr_heartr
        -----------------
        # eventId, deviceType, deviceid, timestamp, userid, trainingMode, rate, quality
        #[["5321bc0a-d35a-4fde-a2fa-e7a766c459cc",""msbad2","b81e905908354542",1455267743619,"vincent.planat@hpe.com","NONE",85, 0],
        # ["5321bc0a-d35a-4fde-a2fa-e7a766c459cc",""msbad2","b81e905908354542",1455267743620,"vincent.planat@hpe.com","NONE",82, 0]]
        '''        
        self.arr_heartr       = arr_heartr

    def add_gsrl_arr(self,arr_gsr):
        '''
        format of arr_gsr
        -----------------
        # eventId, deviceType, deviceid, timestamp, userid, trainingMode, resistance
        #[["5321bc0a-d35a-4fde-a2fa-e7a766c459cc",""msbad2","b81e905908354542",1455267743619,"vincent.planat@hpe.com","NONE",340330],
        # ["5321bc0a-d35a-4fde-a2fa-e7a766c459cc",""msbad2","b81e905908354542",1455267743620,"vincent.planat@hpe.com","NONE",340333]]

        '''        
        self.arr_gsr       = arr_gsr

    def add_rri_arr(self,arr_rri):
        '''
        format of arr_rri
        -----------------
        # eventId, deviceType, deviceid, timestamp, userid, trainingMode, interval
        #[["5321bc0a-d35a-4fde-a2fa-e7a766c459cc",""msbad2","b81e905908354542",1455267743619,"vincent.planat@hpe.com","NONE",0.630496],
        # ["5321bc0a-d35a-4fde-a2fa-e7a766c459cc",""msbad2","b81e905908354542",1455267743620,"vincent.planat@hpe.com","NONE",0.630434]]

        '''        
        self.arr_rri       = arr_rri

    #####################################################################################
    # RDD part
    def add_skin_templ_rdd(self,rdd_skint):
        self.rdd_skint       = rdd_skint    
    def add_heart_rate_rdd(self,rdd_heartr):        
        self.rdd_heartr       = rdd_heartr
    def add_Gsrl_rdd(self,rdd_gsr):
        self.rdd_gsr   = rdd_gsr
    def add_rri_rdd(self,rdd_rri):
        self.rdd_rri       = rdd_rri

    
    #####################################################################################
    # Statistics part
    def get_arr_stats(self):
        stat_report = "PhysioDataset statistics (Arr) \n"
        line = "   arr_skint    size:"+str(len(self.arr_skint))
        stat_report = stat_report + line + "\n"
        line = "   arr_heartr    size:"+str(len(self.arr_heartr))
        stat_report = stat_report + line + "\n"
        line = "   arr_gsr    size:"+str(len(self.arr_gsr))
        stat_report = stat_report + line + "\n"
        line = "   arr_rri    size:"+str(len(self.arr_rri))
        stat_report = stat_report + line + "\n"
        return stat_report

    def get_rdd_stats(self):
        stat_report = "PhysioDataset statistics (Rdd)\n"
        line = "   arr_skint    size:"+str(self.rdd_skint.count())
        stat_report = stat_report + line + "\n"
        line = "   arr_heartr    size:"+str(self.rdd_heartr.count())
        stat_report = stat_report + line + "\n"
        line = "   arr_gsr    size:"+str(self.rdd_gsr.count())
        stat_report = stat_report + line + "\n"
        line = "   arr_rri    size:"+str(self.rdd_rri.count())
        stat_report = stat_report + line + "\n"
        return stat_report


    def getTestVal(self):
        stat_report = "Test retrieve Data\n"
        line = str(self.rdd_gsr.take(3))
        stat_report = stat_report + line + "\n"
        return stat_report

############################################################################################
############################## SensorDataset class #########################################
class SensorsDataset:
    'Aggregation of dataSets'
    
    def __init__(self,sessionId):
        self.sessionId = sessionId
        self.ActivityDS = ActivityDataset()
        self.PhysioDS = PhysioDataset()
     
    def get_session_id(self):
        return self.sessionId
