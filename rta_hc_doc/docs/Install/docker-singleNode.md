Dockerfile Explanation
======================

* The following chapter explain how to install the complete prototype framework on a single node.
* This include: Python / Java / Spark / Kafka / Cassandra / KairosDb / Grafana
* At the moment this does not include yet the procedure to install the business logic package.
    * processors + management-cli/web

* The following docker has been tested on a CentOS version 7.0.2 with docker 1.12.1

## Structure & Installing materials

(Elvin) I'm an administrator arriving on this CentOs + Docker fresh System. I have in hands a `rta-framework-docker.tar` file
* What do I have to do to install the different materials (dockerfiles + iot_hc_schema.cql + ????)
* Which folder do we have to create on the target system (where docker is installed). The 3 below ?
* We must describe an installation procedure for this docker pacakge
* that some file must be put under some of these one (**iot_hc_schema.cql** for example)

Located under three directories（/opt/mount2 /opt/mount3 /opt/mount4）are three dockerfiles of the same name "dockerfile". ( you can't use other names actually )

The first dockerfile in **/opt/mount2** is used to install.
The second dockerfile in **/opt/mount3** is used to config.
The third dockerfile in **/opt/mount4** is used to start.

In the following chapter we explain the procedure to be followed to sequentially install, config and start the framework using docker.

----------

## Docker execution

### First dockerfile (/opt/mount2)
--------------------

The first dockerfile will install all the necessary components on centos:latest within the docker container.
It will also mount the /opt/mount2 (the directory that has the dockerfile) onto the docker container.

> **Attention:**
> Make sure there is a file called **iot_hc_schema.cql** under the path /opt/mount2.
> The container needs to access the file when build.

Use the command below when you are in the path **/opt/mount2**

    dokcer build -t rta_hc_install .

If the build is successful, the image **rta_hc_install** will be created.
> **Attention:**
> The **-t XXX** (option) means give the dockerfile image a tag called XXX.
>The **.** (dot) at the end means the dockerfile for. build is in the current directory ( /opt/mount2 )


----------


### Second dockerfile (/opt/mount3)
---------------------

The second dockerfile will do all the necessary configurations.
It will expose ports 9797 ( for tomcat and kafka ) and 3000 ( for grafana ).
It will also create a file called docker-start.sh under the directory /opt/mount1 in the docker container. This file is used for starting up purposes.
Use the command below when you are in the path  **/opt/mount3**

    docker build --build-arg cloud_server=10.3.35.93 \
    	--build-arg spark_driver_mem=512M \
    	--build-arg spark_executor_mem=3g \
    	-t rta_hc_conf .

> **Attention:**
>The **\\** ( backslash ) here is used to continue the line, you can type them in one line anyway.
>The **- -build-arg** (option) means give an argument to the command.
>You should give exactly **three** arguments here for build purpose.

If the build is successful, the image **rta_hc_conf** will be created.


----------


### Third dockerfile (/opt/mount4)
--------------------

The third dockerfile will start all the needed components like cassandra, kafka, kairosdb etc.
> **Attention:**
>The third dockerfile has a line called **ENTRYPOINT**, it will run the docker-start.sh in /opt/mount1 as mentioned earlier, so as to start all the neccsary components if the image is run.

Use the command below when you are in the path **/opt/mount4**

    dokcer build -t rta_hc .

If the build is successful, the image **rta_hc** will be created.



----------

# Docker Management
-------------------------

 After you build all three images, to **RUN** the container use the command

    docker run -d -p 9797:9797 -p 3000:3000 rta_hc

> **Attention:**
> The **-d** (option) means run the container in detach mode, which means that the container will persist in the system.
> The **-p XXXX:YYYY** (option) means the exposed port YYYY will be mapped to the system port XXXX.

To check whether a docker is up and running use the command

    docker ps
To go into a docker environment
**First**, make sure there is a container up and running
**Second**, use the command

    docker exec -it $(docker ps -q) /bin/bash

If successful, you are already in the container, do anything you want.
> **Attention:**
> The **-i** (option) above means interactive mode
> The **-t** (option) means allocate a pseudo-tty
>the **-q** (option) here means display only container IDs.
>If there is more than one container up and running, substitute $(docker ps -q) with the exact **container ID**.

To stop a running containers use the command


    docker stop $(docker ps -q)

To delete containers not running use the command

    docker rm $(docker ps -a -q)

> **Attention:**
> The **-a** (option) above means show all current and history containers

To delete unsuccessful images of the name "none"
**First**, delete all history containers not running
**Second**, use the command

    docker images|grep none|awk '{print $3}'|xargs docker rmi


## Miscellaneous
-----------------

For detailed account of what the three dockerfiles are doing, please consult to the **COMMENTS** in the dockerfile.

----------
