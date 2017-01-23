# Minutes (28/10/2016)
## docker development
* include the platform monitor installation & config into the dockerfile logic.
  * I've started formating a documentation explaning how to install the platform_mon but it's not finalized.
  * Please look at the [ installation page](../install/installation,md), I have added a section for platform monitor
  * under the `/opt/rta_hc` you will find a tar file containing the src of the platform monitor that must be isntalled into the `src` directory
  * for the config file could you also create a tar file containing all the config file of the `conf` directory and us that.
  * The update of the conf file should be limited to the hostname or IP@...




# Minutes (25/10/2016)
## platform monitor
* Move the platform monitor stuff under `/opt/rta_hc/rta-hc-framework-master/`
    * All the source file (.py + static) should be located under `src`
    * The .properties under the `conf` directory
* Test on `10.3.35.93` the start/stop of kafka / zookeeper / kairosDb / cassandra / tomcat / grafana / spark
    * all the processor and the raw_writer have not been isntalled yet
* Remove start & Stop button from the web-server page
* porotype of `tail -f` from web-page
    * change the start command of accel for example
```
nohup /opt/mount1/spark-1.6.1-bin-hadoop2.6/bin/spark-submit --master spark://16.250.25.6:7077 --executor-memory 2G --driver-memory 512M --total-executor-cores 1 --jars ../libs/spark-streaming-kafka-assembly_2.10-1.6.0.jar rta_processor_simple_1_1.py accelerometer sklearn 1>../log/rta_processor_accel.log 2>&1 &
```
    * `tail -f` should be done on the `../log/rta_processor_accel.log`

# Minutes (20/10/2016)

## platform monitor
* Review the packaging and align with the recommendation below
    * detail the 3 modules briefly (what they are used for) (web, cli, library)
    * how to install (should be placed into the `src` directory, as I understood)
    * which configuration files are they referring and where should this file be located
* Fix Web server module
    * When we shutdown the web-server all the process, started from the web interfaces are stopped !
    * I sent few research result. My feeling is that it's around how the sub-process are started and which level of "connection" they keep with there parent
    * Understand what happens when we stop the flask server
    * Following use-cases must be supported
        1. Start process from cli and check status from web
        2. Stop process from cli  and check status from web
        3. Start process from web and check status from cli
        4. Stop process from web and check status from cli
* Prepare the monitoring tool for running on the `10.3.35.93`
    * On this server both `main-analytic` and `main-storage` profiles should run on the same machine
    * Once this is prepared Vincent will install and test it on the 10.3.35.93

## docker development
* The dockerfile do not need to start all the components of the platform. This task will be done by the platform monitor that Larry is developing
* Nevertheless to configure
    * Tomcat we need to start it, deploy the war and stopped
    * Kafka (creating the topics) we need to start kafka first
* All the other process (spark, cassandra, kairosDb, Grafana etc ..) will be started by the administrator

* Need to extend now the dockerfile (isntall and config) to the following process
    * cassandra
    * kairosDb
    * Grafana
    * platform monitor

# Minutes (17/10/2016)
## platform monitor

* Command line interface
    * spark (worker AND master) are currently started with the command `start spark`
    * I recommend that we display (list layout) the spark status as follow
```
PID     Process         status
        spark
pid1        master      Running
pid2        worker      Running
```

* Web interface
    * replace the `Refresh me` link by a buttons. Locate the button after the table (cetered)
    * Server name as a table title (h1 or h2) centered
    * Problem
        * When we shutdown the web-server all the process, started from the web interfaces are stopped !

* documentation
    * Written in markdown
    * Admin guide
        * Setup
            * detail the 3 modules briefly (what they are used for) (web, cli, library)
            * how to install (should be placed into the `src` directory, as I understood)
            * which configuration files are they referring and where should this file be located
        * Config
                * Explain how to configure the modules. Re-explain the concept we developed with the server profile
                * Give examples
    * Startup
        * cli module
            * start command
        * web module
            * start command


# Minutes (10/10/2016)

* start grafana ERROR
* `start cassandra`
    * I've seen the following message `Cassandra is running, please stop cassandra first` when you try to start cassandra.
    * We should not have such message as cassandra is starting ...
* `start grafana`
    * `None` is displayed. Should be removed
* correct syntax `raw_writer` not `raw_writter` (with double t)
* Develop the web interface
    * We should have 3 python modules
        * A core library used to handle the logic around start/stop/Status
        * A command line module leveraging the library for the command line monitor
        * A web module leveraging the library for the web monitor

* (VPL) Update the specs with rta.properties


# Minutes (10/10/2016)

## platform monitor
* Demo scheduled tuesday the 10/10
* As the `ps ax` approach is not working fine (str truncated) Vincent propose to use the `psutil process Class` and call the `pid()` function
* [The documentation is here](https://pythonhosted.org/psutil/#process-class)
* Larry will provide a status of current development using the following table

|developed module | process                 | function                | comment                                            |
|-----------------|-------------------------|-------------------------|----------------------------------------------------|
|command line     |kafka zookeeper server   |Start() Stop() Status()  |Start & Stop: pid based on psutil. Status: psutil   |
|                 |kafka server             |Start() Stop() Status()  ||
|                 |spark (master/worker)    |Start() Stop() Status()  ||
|                 |procc accelerometer      |Start() Stop() Status()  ||
|                 |procc gyroscope          |Start() Stop() Status()  ||
|                 |procc barometer          |Start() Stop() Status()  ||
|                 |procc aggregator         |Start() Stop() Status()  ||
|                 |procc novelty detector   |Start() Stop() Status()  ||
|                 |procc raw_writer         |Start() Stop() Status()  ||
|                 |cassandra                |Start() Stop() Status()  ||
|                 |kairosDb server          |Start() Stop() Status()  ||
|                 |Grafana server           |Start() Stop() Status()  ||
|                 |tomcat server            |Start() Stop() Status()  ||
|Web monitor      |kafka zookeeper server   |Start() Stop() Status()  |Start & Stop: pid based on psutil. Status: psutil   |
|                 |kafka server             |Start() Stop() Status()  ||
|                 |spark (master/worker)    |Start() Stop() Status()  ||
|                 |procc accelerometer      |Start() Stop() Status()  ||
|                 |procc gyroscope          |Start() Stop() Status()  ||
|                 |procc barometer          |Start() Stop() Status()  ||
|                 |procc aggregator         |Start() Stop() Status()  ||
|                 |procc novelty detector   |Start() Stop() Status()  ||
|                 |procc raw_writer         |Start() Stop() Status()  ||
|                 |cassandra                |Start() Stop() Status()  ||
|                 |kairosDb server          |Start() Stop() Status()  ||
|                 |Grafana server           |Start() Stop() Status()  ||
|                 |tomcat server            |Start() Stop() Status()  ||


## docker development
* Demo scheduled Wednesday the 11/10
* The servlet can be downloaded from the `10.3.35.93` system.
* I've done the test on the `10.3.35.91` and executed successfully
  `wget http://10.3.35.93/rta_hc/simpleiothttp2kafka.war`

-------------------------------------------------------

# Minutes (29/09/2016)
## platform monitor
* kafka and zookeeper stop procedure.
    * An anlternative is to retrieve the result of the `ps ax` and parse it to get the pid. The bellow code illustrate what I mean.
```
import os
import sys
import re

# first retrieve the pid of the Kafka server
#PIDS_CMD = "ps ax | grep -i 'kafka\.Kafka' | grep java | grep -v grep | awk '{print $1}'"

ps_cmd = "ps ax"
regex_search = re.compile(".*kafka\.Kafka config\/server\.properties")

# Retrieve the result of ps ax into a list
procc_list=os.popen(ps_cmd).readlines()
# filter each element of the list and keep only the one matching the regex
procc_line = filter(regex_search.match,procc_list)
# the resulting procc_line is a list of 1 element.
# We scan this elem (for elem in procc_line) and split its content using a space seperator
pid = [elem.split(' ')[0] for elem in procc_line]
# The first ([0]) one is the pid we are looking for
print ("result:%s" % pid[0])
sys.exit(1)
```
* Start/stop for cassandra/kairos etc ...
    * [The procedure is documented here:](../Install/start.md#stop-commands)

* Test all the cases (start/stop) with dependencies

## docker development
* Vincent updated the specification. In particular
    * [New page here for edge topology](../Install/setup-edge.md)
    * [configuration strategy for docker files](../V1.1-Specs/docker4edge.md#docker-images)
* Option of using ENV taken by Elvin. OK
* TAG & REPOSITORY to add like (for tag)
```
  docker build -t vieux/apache:2.0 .
```
  * Objective is for the moment to use the local repository (as you are doing)
* Next steps are
  * Tomcat
    * The installation requires a .war file that must be retrieved from the project github directory here: https://github.hpe.com/vincent-planat/rta-hc-framework/blob/master/bin/simpleiothttp2kafka.war
  * Kafka
  * Spark
* **Container configuration**
  * We propose to back all the solution configuration into a specific docker container.
      * [This is option one of this post](https://dantehranian.wordpress.com/2015/03/25/how-should-i-get-application-configuration-into-my-docker-containers/)
      * Idea is to have 2 containers.
        * The first one developed currently that do not do any configuration update (`first-container`)
        * The second one that perform all the configuration (FROM `first-container`)
  * For the configuration container
      * It is important to avoid any IP@ harcoding into the dockerfile script.
      * We propose to pass the parameters to the container during the build using `-e hello=world`
      * Then using the `ENV` to persist and update the config file.
      * The config files will be updated using `sed command`
  * [I have documented here](../V1.1-Specs/docker4edge.md#docker-images) the different files that are subject to configuration and should be externalized to the second container.

---------------------------------------------------------------------------------------------------------

# Minutes (28/09/2016)
## platform monitor
* interactive command line script
    * The `start` and `stop` command must pass a process name. the `start_spark_master` command for example is not valid. [See the V1.1-Specs](../V1.1-Specs/platform-monitor.md#phase-3) for detail.
    * For spark master/worker we must us the `start-all.sh` and `stop-all.sh` scripts provided by Spark.
    * Implement the dependencies mechanism as presented in the [V1.1-Specs](../V1.1-Specs/platform-monitor.md#component-dependencies)
* Web interface
    * When the script starts it checks if the current hostname is in the pre-configured list.
    * If it's not the case then **the script exits** with a ERROR detail
        * _The platform monitor is not configured to run on the current hostname <hostname>. See `rta.properties`_

* The interactive command line script must be finished first such as the dependencies mechanism is well tested and controller. Then the code will be integrated into the web interface (START and STOP buttons).

## docker development
* Vincent updated a bit the Python `Core` install process.
    * Not `hadoop` user anymore but `root`.
    * Not tar xvf anymore but retrieve the package from Anaconda site (wget etc ). [See the install script for python](../Install/installation.md#core)
