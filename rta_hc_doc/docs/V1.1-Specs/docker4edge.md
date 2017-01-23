
# Objective
* The objective of this work is to develop a docker ready container for a deployment on an [HPE Edge Gateway EL20](https://www.hpe.com/h20195/v2/GetPDF.aspx/c04884769.pdf).

* [The docker framework](https://www.docker.com/) is the leading environment chosen by HPE, for supporting the PaaS _Build,ship,run_ strategy.

Refer to the [edge topology diagram available here](../Install/setup-edge.md) for a description of the setup.

# setup
* The target system (Edge EL20 Gateway) will run CentOS 7.2 with docker ready and installed
* A DEV/ITG environemnt will be used for making all the test prior to deployment on the EL20.
```
Kernel Version 3.10.0-327.36.1.el7.x86_64
IP: 10.3.35.91
User: root
Password: swatch2HPESC
```

# Working model
* A [dockerfile file](https://docs.docker.com/engine/reference/builder/) will be used to define the container.
* We will develop a single container embeding all the components presented in the above architecture diagram.

# phasing

|phase    |                                                             |
|---------|-------------------------------------------------------------|
|0.1      | centOs:latest + Python (anaconda2) + kafka-python           |
|0.2      | + JAVA                                                      |
|0.3      | + Tomcat                                                    |
|0.4      | + Kafka                                                     |
|0.5      | + Spark                                                     |
|0.6      | + rta_processor_simple                                      |

# docker images
* We choose an approach with 2 dockers files
    * `rta_hc` dockerfile containing all the package installation
    * `rta_hc_conf` which will first load the `rta_hc` (FROM rta_hc) and apply the required configuration
* We pass parameters to the `rta_hc_conf` at build time (choose the best one)
    * Approach-1 is to use `-e var=xxx -e var2=rrrr etc ...`
    * Approach-2 is to use the `--build-arg` with the `ARG` command in the docker file.
* Parameters are
    * `cloud_server` = 10.3.35.93
    * `spark_driver_mem` = 512M
    * `spark_executor_mem` = 3g

|component          | Config update                                                                                                 |
|-------------------|---------------------------------------------------------------------------------------------------------------|
|python             | No specific config file to update  <br> ENV set to PATH=/opt/mount1/anaconda2/bin:$PATH                       |
|Java               | ENV set to `JAVA_HOME` & `PATH`
|Tomcat             | `webapps/simpleiothttp2kafka/WEB-INF/web.xml`. <br> `iot.kafka.host` context IP set to `cloud_server`. Port remains unchanged <br> |
|Kafka              | - `config/zookeeper.properties` and `config/server.properties` according to install doc  <br> - Creation of all the topics as described in the install doc [see here](../Install/installation.md#kafka)       |
|Spark              | - update the `spark-env.sh`. IP@ to be set to the `0.0.0.0` value <br> - ENV set to PATH <br> - `spark-defaults.conf` set to `spark_driver_mem` and `spark_executor_mem` <br> - `conf/slaves` localhost |

## Version 0.1
* Pyhton installation doc [is available here](../Install/installation#python-anaconda2)
* The _Core_ chapter can be implemented in the dockerfile
* For _specific package_ chapter is applicable **only** for kafka. We do not need the other python modules


# Materials
* [The specification web site:](http://c4t19765.itcs.hpecorp.net/rta_iot/hc-realtime-analytic-poc/)
* [Getting start with docker](https://docs.docker.com/engine/getstarted/)
* [Excellent docker tutorial](https://prakhar.me/docker-curriculum/#setup)
