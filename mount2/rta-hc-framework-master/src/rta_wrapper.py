#!/opt/mount1/anaconda2/bin/python
# -*- coding: utf-8 -*-
"""
Created on May 31, 2016
Purpose: Spark job wrapper to be scheduled by Supervisord
@author: Chen-Gang He
        2016-05-31
        1> initially created
        2016-06-16
        Support wrapper can check if process is already running. If so, exit abnormally. If not, it will be started
        normally.
@author: Chen-Gang He
        2016-08-31
	1> fix regular expression bug in get_pid_file_name
"""
import argparse
import subprocess
import psutil
import re
import time
import socket
import sys
import signal
import ctypes
import os

libc = ctypes.CDLL("libc.so.6")


# ==============================================================================
# Function
# ==============================================================================
def set_pdeathsig(sig=signal.SIGTERM):
    def callable():
        return libc.prctl(1, sig)

    return callable


def get_process_id(process_name_pattern_regexp, re_compile, running_time_in_seconds):
    """Return process ID based on process_name_pattern_regexp or None if there is no such process running
        Args:
            process_name_pattern_regexp (unicode): pattern string of process name
            re_compile (ref): variable reference to re.compile
            running_time_in_seconds (int): duration to wait to check running process
    Returns:
        int
    """
    # Wait running_time_in_seconds to check if the process is still running
    time.sleep(running_time_in_seconds)
    process_name_pattern_obj = re_compile(process_name_pattern_regexp)
    for proc in psutil.process_iter():
        try:
            pinfo = proc.as_dict(attrs=['pid', 'name', 'cmdline', 'cpu_times'])
        except psutil.NoSuchProcess:
            pass
        process_name_search_result = process_name_pattern_obj.search(' '.join(pinfo["cmdline"]))
        process_running_time_name_tuple = pinfo["cpu_times"]
        process_running_time = process_running_time_name_tuple.user
        if pinfo["name"] == "python" and process_name_search_result:
            print "    process_name_pattern_regexp is running with pid %d and command line %s for %.2f minutes" \
                  % (pinfo["pid"], ' '.join(pinfo["cmdline"]), process_running_time)
            return pinfo["pid"]
    return None


def handle_commandline():
    """Do with script's arguments, and return dictionary of arguments
    Returns:
        dict
    """
    host_ip_address = socket.gethostbyname(socket.gethostname())
    default_master_ip_port = "spark://" + host_ip_address + ":7077"
    parser = argparse.ArgumentParser()
    parser.add_argument("-sh", "--script_home", type=str, help="Script home direcotory absolute path", required=True)
    parser.add_argument("-m", "--spark_master", type=str,
                        help="Spark master URL. By default: " + default_master_ip_port, default=default_master_ip_port)
    parser.add_argument("-e", "--executor_memory", type=str, help="Spark executor_memory", default="2G")
    parser.add_argument("-d", "--driver_memory", type=str, help="Spark driver_memory", default="512M")
    parser.add_argument("-c", "--executor_core_num", type=int, help="Spark total number of cores for executors",
                        default=1)
    parser.add_argument("-sn", "--script_name", type=str, help="Script name and its arguements if required",
                        required=True)
    parser.add_argument("-w", "--dependent_script_mode", action="store_true",
                        help="Wait dependent script to run or not")
    parser.add_argument("-p", "--dependent_process_name", type=str, help="Dependent process name to be waited")
    parser.add_argument("-n", "--number_of_second_to_wait", type=int,
                        help="the number of seconds to wait dependent process name", default=10)
    args = parser.parse_args()
    args_dict = vars(args)
    if not args_dict["dependent_process_name"] and args_dict["dependent_script_mode"]:
        args.error("-p DEPENDENT_PROCESS_NAME MUST be specified if -w is set !!")
    return args_dict


def get_pid_file_name(*args):
    """Get the name of pid file invoked by this script.
        Args:
            *args (str): process name and its arguments
    Returns:
        str
    """
    # Replace script extension with "_", and enclose script name and its arguements by "_".
    pid_file_name = [re.sub(r'''\.[\w]{1,2} ''', "_", str(a).strip()).replace(' ', '_') for a in args]
    return "_".join(pid_file_name) + ".pid"


def generate_pid_file(pidfile_path, pidfile_name, pid_number):
    """Get the name of pid file invoked by this script.
        Args:
            pidfile_path (str): path of pid file
            pidfile_name (str): name of pid file
            pid_number (int): number of process id
    Returns:
        str
    """
    if not os.path.exists(pidfile_path):
        os.makedirs(pidfile_path)
    pidfile = os.path.join(pidfile_path, pidfile_name)
    with open(pidfile, 'w') as f:
        f.write(str(pid_number))
        f.close()
    return None


def has_running_pid(pidfile_path, pidfile_name):
    """ Check pid file and read pid number, and validate if pid is running. If so, return (True, pid)
    otherwise, (False, None)
        Args:
            pidfile_path (str): path of pid file
            pidfile_name (str): name of pid file
    Returns:
        tuple(bool, number)
    """
    pidfile = os.path.join(pidfile_path, pidfile_name)
    if os.path.exists(pidfile_path) and os.path.exists(pidfile):
        with open(pidfile, 'r') as f:
            pid = f.read()
            for p in pid.split():
                if psutil.pid_exists(int(p)):
                    return (True, int(p))
            return(False, None)
    else:
        return(False, None)


def main():
    # Handle command line
    args_dict = handle_commandline()
    proc_pid_path = os.path.join(args_dict["script_home"], "run")
    proc_pid_name = get_pid_file_name(args_dict["script_name"])

    # Check if waiting dependent job is set
    print "==> Check if this process is running or not ..."
    running_pid_tuple = has_running_pid(proc_pid_path, proc_pid_name)
    if running_pid_tuple[0]:
        print "    this process %s with pid %d is ALREADY running, and exit !!!" %(args_dict["script_name"], running_pid_tuple[1])
        sys.exit(-1)

    print "==> Start rta_wrapper ..."
    if args_dict["dependent_script_mode"]:
        print "==> Wait dependent script for %d seconds to start ..." % (args_dict["number_of_second_to_wait"])
        dependent_process_name_pattern_regexp = ur'''.*''' + args_dict['dependent_process_name'] + ur''''''
        if not get_process_id(dependent_process_name_pattern_regexp, re.compile, args_dict["number_of_second_to_wait"]):
            print "    There is NO dependent process %s running !" % (args_dict['dependent_process_name'])
            sys.exit(-1)

    print "==> Generate process ID file %s in path %s ..." %(proc_pid_name, proc_pid_path)
    generate_pid_file(proc_pid_path, proc_pid_name, os.getpid())
    print "==> Start running the process ..."
    script_command = "/opt/rta_hc/spark-1.6.1-bin-hadoop2.6/bin/spark-submit --master " + args_dict[
        "spark_master"] + " --executor-memory " \
                     + args_dict["executor_memory"] + " --driver-memory " + args_dict["driver_memory"] \
                     + " --total-executor-cores " + str(args_dict["executor_core_num"]) \
                     + " --jars " + args_dict[
                         "script_home"] + "/libs/spark-streaming-kafka-assembly_2.10-1.6.0.jar " \
                     + args_dict["script_home"] + "/src/" + args_dict["script_name"]
    main_proc = subprocess.Popen(script_command, shell=True, preexec_fn=set_pdeathsig(signal.SIGTERM))
    a, b = main_proc.communicate()

# ==============================================================================
# Main
# ==============================================================================
if __name__ == "__main__":
    main()
