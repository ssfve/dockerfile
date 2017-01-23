# -*- coding: utf-8 -*-
"""
Created on Mon May 30 14:07:49 2016

@author: planat
"""

import subprocess
import time;

localtime = time.asctime( time.localtime(time.time()) )
'''
hostname = sys.argv[1]
if (len(hostname == 0)):
    print "usage is python monitor_fielSys.py <hostname>"
    exit(0)
'''

# primary
SEND_MAIL_CMD = "sendmail"
DF_CMD = "df"
MAIL_ADD = "vincent.planat@hpe.com"

p1 = subprocess.Popen(['yum','clean','all'],
                      stdin =subprocess.PIPE,
                      stdout=subprocess.PIPE)
df_output = p1.communicate()[0]
print("yum clean all");

p1 = subprocess.Popen(['find','/var/log','-name','\"*.log.*\"','-delete'],
                      stdin =subprocess.PIPE,
                      stdout=subprocess.PIPE)
df_output = p1.communicate()[0]
print("find . -name \"*.log.*\" -exec rm -fr {} \;");

p1 = subprocess.Popen(['df','-h'],
                      stdin =subprocess.PIPE,
                      stdout=subprocess.PIPE)
df_output = p1.communicate()[0]

p1 = subprocess.Popen(['/bin/hostname'],
                      stdin =subprocess.PIPE,
                      stdout=subprocess.PIPE)
hostname_output = p1.communicate()[0]

df_output =  "----------------------------------" + "\n" + "Server:"+hostname_output  + "---------------------------------------" + "\n" + df_output + "---------------------------------------"
df_output = df_output + "\n \n find . -name \"*.log.*\" -exec rm -fr {} \;"
print df_output

p1 = subprocess.Popen(['/usr/sbin/sendmail',MAIL_ADD],
                      stdin =subprocess.PIPE,
                      stdout=subprocess.PIPE)
p1.communicate(df_output)
print ("%s:  mail sent to:%s for hostname:%s" %(str(localtime), MAIL_ADD,hostname_output))

