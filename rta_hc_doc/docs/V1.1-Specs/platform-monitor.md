# Followup
* Auto completion of process_name in cmd ?
* Review code and introduce config file (`rta.properties`) ?
* Stability of Web server
* Crontab

# Specification
* Objective is to have a monitor web service (crontab monitored) that will return the status of the different required process of the platform node

* Startup command: `python platform_status_mon.py <hostname>`

## component mapping table
* Depending on the hostname the list of process won't be the same. The following table provides a summary
* At the begining of the script we must list the different servers supported hostname

|process                  | ITG(c9t17308) | ITG(C2t08977) | DEV(C9t21193) | DEV(C2t08978) |
|-------------------------|---------------|---------------|---------------|---------------|
|kafka zookeeper server   | X             |               | X             |               |
|kafka server             | X             |               | X             |               |
|spark master             | X             | X             | X             | X             |
|spark worker             | X             | X             | X             | X             |
|processor accelerometer  | X             |               | X             |               |
|processor gyroscope      | X             |               | X             |               |
|processor barometer      | X             |               | X             |               |
|processor aggregator     | X             |               | X             |               |
|cassandra                |               | X             |               | X             |
|kairosDb server          |               | X             |               | X             |
|grafana server           |               | X             |               | X             |
|tomcat server            |               | X             |               | X             |
|novelty detector         |               | X             |               | X             |
|raw writter              |               | X             |               | X             |

## component dependencies

|process                  | Depends on running component (same system)                                         |
|-------------------------|------------------------------------------------------------------------------------|
|kafka zookeeper server   | No component                                                                       |
|kafka server             | No component                                                                       |
|spark master/worker      | No component                                                                       |
|processor (x,y,z)        | Spark  & kafka-server                                                              |
|cassandra                | No component                                                                       |
|kairosDb server          | cassandra                                                                          |
|grafana server           | kairosDb server                                                                    |
|tomcat server            | No component                                                                       |
|novelty detector         | Spark  & kafka-server (but cannot be easily checked as running on main-analytic)   |
|raw writer               | Spark  & kafka-server (but cannot be easilychecked as running on main-analytic)    |

* **phase-1:**
    * the monitor scan all the system running process and check the status of a predefined list.
    * The montior return a table (text formated) giving the status of each process
    * The monitor must manage the different system environment (ITG and DEV). The idea is that we can easily, in the future add a new set of servers.
        * This will be the case with the solution center project where we are currently deploying the new environment.
* **phase-2:**
    * a small python [Flask](https://www.tutorialspoint.com/flask/flask_quick_guide.htm) web-server is encapsulating this logic and return a HTML formatted table
    * Only a `Refresh` button which will trigger the background script (phase-1) to perform a full check on all the processes and return a result.
    * The web server is monitored by cron
* **phase-3:**
    * Start/Stop/Status command line script. such as the user can, from a command line start, stop and get status of all the process.
    * For that we will use `import cmd` pyhton library.
        * status
        * start <process_name>
        * stop <process_name>

# Phase-1
## skeleton
* A first skeleton code is available
* main logic
  * The code is based on the `psutil` lib which can return, for each linux process, a list of cmd line parameters that have been used to start the process.
  * For example the `run_proc.cmdline()` return the following list
```
 ['java', '-Xmx512M', '-Xms512M', '-server', '-XX:+UseG1GC', '-XX:MaxGCPauseMillis=20',
'-XX:InitiatingHeapOccupancyPercent=35', '-XX:+DisableExplicitGC', '-Djava.awt.headless=true',
'-Xloggc:/opt/mount1/kafka_2.10-0.9.0.0/bin/../logs/zookeeper-gc.log', '-verbose:gc',
'-XX:+PrintGCDetails', '-XX:+PrintGCDateStamps', '-XX:+PrintGCTimeStamps', '-Dcom.sun.management.jmxremote',
'-Dcom.sun.management.jmxremote.authenticate=false', '-Dcom.sun.management.jmxremote.ssl=false',
'-Dkafka.logs.dir=/opt/mount1/kafka_2.10-0.9.0.0/bin/../logs',
'-Dlog4j.configuration=file:bin/../config/log4j.properties', '-cp', ':/opt/mount1/kafka_2.10-0.9.0.0/bin/../libs/*',
'org.apache.zookeeper.server.quorum.QuorumPeerMain', 'config/zookeeper.properties']
```
  * For each process that we want to monitor we identify searching criteria in this list which are taking the form of:
    * `index`: the index of the criteria in the list of cmdLine parmaeter. from 0 to the `len(run_proc.cmdline())`
    * `regex`: a regex used to check the validity of the criteria
  * For example the above process will be defined by 2 criteria
    * `index:0  regex:'java'`
    * `index:22  regex:'config/zookeeper.properties'`
  * `ProcesInfo`
    * The class is used to store the process definition we want to check on the system.
    * An instance is created as follow
    ```
    kafka_server = ProcessInfo("Kafka zookeeper server")
    kafka_server.addSearchCriteria(0,"java")
    kafka_server.addSearchCriteria(22,'config/zookeeper.properties')
    process_list.append(kafka_server)
    ```
  * the process check algorithm is simple
    ```
      scan all the system process. For each of them
        scan all the process to monitor. For each of them
          check the validity of criteria
        if I have the same number of success  as the number of criteria then the process is identified
    ```

  * **Note**
    * Rexex
        * The current skeleton is based on a string equality check only ` (proc_cmdline[criteria_val["index"]] == criteria_val["regex"])):`
        * We need to implement a regex search. For example find `java` in `/opt/java/jdk1.8.0_72/bin/java` to avoid hard coding too much into the script
    * Some process like the simple-processor are associated to 3 linux processes (python launcher, java spark, spark workder). For the moment we will only follow the below table and do not consider this case.

## Process list
* **Main Analytic system (c9txxx)**

| Name                      | sucess criteria list                                        |
|---------------------------|-------------------------------------------------------------|
| kafka zookeeper server    | {index:0, regex:'java'} <br> {index:22, regex:'config/zookeeper.properties'}  <br> {index:21, regex:'org.apache.zookeeper.server`  |
| kafka server              | {index:0, regex:'java'} <br> {index:22, regex:'config/server.properties'}  <br> {index:21, regex:'kafka.Kafka'          |
| spark master              | {index:0, regex:'java'} <br> {index:5, regex:'org.apache.spark.deploy.master.Master'} <br>  {index:7, regex:<server IP@>} |
| spark worker              | {index:0, regex:'java'} <br> {index:5, regex:'org.apache.spark.deploy.worker.Worker'} <br>  {index:8, regex:'spark://<IP@>:7077']} |
| processor accelerometer   | {index:0, regex:'java'} <br> {index:18, regex:'sklearn'} <br>  {index:17, regex:'accelerometer']} <br>  {index:16, regex:'rta_processor_simple.py']} |
| processor gyroscope       | {index:0, regex:'java'} <br> {index:18, regex:'sklearn'} <br>  {index:17, regex:'gyroscope']} <br>  {index:16, regex:'rta_processor_simple.py']} |
| processor barometer       | {index:0, regex:'java'} <br> {index:18, regex:'sklearn'} <br>  {index:17, regex:'barometer']} <br>  {index:16, regex:'rta_processor_simple.py']} |
| processor aggregator      | {index:0, regex:'java'} <br> {index:17, regex:'naivebayes'} <br>  {index:16, regex:'har_predict_aggr_ensemble.py']} |

* **Main Storage (c2txxx)**

| Name                      | sucess criteria list                                        |
|---------------------------|-------------------------------------------------------------|
| cassandra                 | {index:0, regex:'java'} <br> {index:47, regex:'org.apache.cassandra.service.CassandraDaemon'}   |
| kairosDb server           | {index:0, regex:'java'} <br> {index:5, regex:'conf/kairosdb.properties'}  <br> {index:5, regex:'org.kairosdb.core.Main'}  |
| grafana server            | {index:0, regex:'grafana-server'} |
| tomcat server             | {index:0, regex:'java'} <br> {index:9, regex:'org.apache.catalina.startup.Bootstrap'}   |
| novelty detector          | {index:0, regex:'java'} <br> {index:16, regex:'novelty_detect.py'}    |
| raw writter               | {index:0, regex:'java'} <br> {index:16, regex:'raw_writer.py'} |
| spark master              | {index:0, regex:'java'} <br> {index:5, regex:'org.apache.spark.deploy.master.Master'} <br>  {index:7, regex:<server IP@>} |
| spark worker              | {index:0, regex:'java'} <br> {index:5, regex:'org.apache.spark.deploy.worker.Worker'} <br>  {index:8, regex:'spark://<IP@>:7077']} |


# phase-3
Add a command line interface for managing the different process (start/stop/status)

* name of the tool: `platform_mngt_cli.py`
* Once the `platform_mngt_cli.py` is started a line-oriented command processor is proposed to the user
    * The prompt for the command processor will be `rta>>``
    * The line oriented command processor will be developed using the python cmd module. See https://pymotw.com/2/cmd/  and [here for the reference documentation)](https://docs.python.org/2/library/cmd.html).

* The available commands are

|Command	                |Purpose                                                                                                    |
|-------------------------|-----------------------------------------------------------------------------------------------------------|
|list	                    | Display the status of each rta components in a tabular format. Process_name, Status                       |
|start <process Name>	    | This start the <process Name>                                                                             |
|stop <process Name>	    | This stop  the <process Name>                                                                             |
|exit	                    | Exit from the `platform_mngt_cli.py`                                                                      |
