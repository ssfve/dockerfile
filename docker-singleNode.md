Dockerfile Explanation
======================

* The following chapter explain how to install the complete prototype framework on a single node.
* This include: Python / Java / Spark / Kafka / Cassandra / KairosDb / Grafana
* At the moment this does not include yet the procedure to install the business logic package.
    * processors + management-cli/web

* The following docker has been tested on a CentOS version 7.0.2 with docker 1.12.1

## Installation

**First**, Put rta-framework-docker.tar under system path /opt

    cp rta-framework-docker.tar /opt

**Second**, Decompress rta-framework-docker.tar file to current directory

    tar -xvf rta-framework-docker.tar
	
> **Attention:**
> When preparing the tar file
> 1 Create three folders (**/mount2** **/mount3** **/mount4**)
> 2 Put the **first dockerfile**, **iot_hc_schema.cql**, **start-docker.sh** and all other required installation packages in /mount2
> 3 Put the **second dockerfile** in /mount3
> 4 Put the **third dockerfile** in /mount4
> 5 Put all three folders into the **rta-framework-docker.tar** file

##Docker Structure

Located under three directories（/opt/mount2 /opt/mount3 /opt/mount4）are three dockerfiles of the same name "dockerfile". ( you can't use other names actually )


The first dockerfile in **/opt/mount2** is used to install.
The second dockerfile in **/opt/mount3** is used to config.
The third dockerfile in **/opt/mount4** is used to start.

In the following chapter we explain the procedure to be followed to sequentially install, config and start the framework using docker.

----------

## Docker Execution
--------------------

### Build First Dockerfile (/opt/mount2)
--------------------

The first dockerfile will install all the necessary components on centos:latest within the docker container.
It will also mount /opt/mount2 onto the docker container, thus the two files under this directory ( **iot_hc_schema.cql** and **start-docker.sh** ) and all other neccessary installation packages are passed into the docker container 

> **Attention:**
> Make sure there is a file called **iot_hc_schema.cql** under /opt/mount2
> Make sure there is also a file called **start-docker.sh** under /opt/mount2
> All installation packages shall be put under /opt/mount2 because they are mounted onto the docker container **(local software repository)**, they are not downloaded from web **(online software repository)**
> The container needs to access all files mentioned above when build

Use the command below to **BUILD** image **rta_hc_inst**

		cd /opt/mount2
        dokcer build -t rta_hc_inst .

If the build is successful, the image **rta_hc_inst** will be created.
> **Attention:**
> The **-t XXX** (option) means give the dockerfile image a tag called XXX.
>The **.** (dot) at the end means the dockerfile for. build is in the current directory ( /opt/mount2 )


----------


### Build Second Dockerfile (/opt/mount3)
---------------------

The second dockerfile will do all the necessary configurations.
It will also expose ports for tomcat, ssh, kafka, grafana etc.
Use the command below to **BUILD** image **rta_hc_conf**

    cd /opt/mount3
    docker build --build-arg cloud_server=0.0.0.0 \
    	--build-arg spark_driver_mem=512M \
    	--build-arg spark_executor_mem=3g \
    	-t rta_hc_conf .

> **Attention:**
>The **\\** ( backslash ) here is used to continue the line, you can type them in one line anyway.
>The **- -build-arg** (option) means give an argument to the command.
>You should give exactly **three** arguments here for build purpose.

If the build is successful, the image **rta_hc_conf** will be created.


----------


### Build Third Dockerfile (/opt/mount4)
--------------------

The third dockerfile will start all the needed components like cassandra, kafka, kairosdb etc.
> **Attention:**
>The third dockerfile has a line called **ENTRYPOINT**, it will run start-docker.sh as mentioned earlier, so as to start all the neccsary components if the image will be run.

Use the command below to **BUILD** image **rta_hc** 

    cd /opt/mount4
    dokcer build -t rta_hc .

If the build is successful, the image **rta_hc** will be created.

--------------------

### Run Docker Container (anywhere)
--------------------
After you build all three images **SUCCESSFULLY**, to **RUN** the container use the command

    docker run -d -p 9797:9797 -p 3000:3000 -p 1111:1111 rta_hc

> **Attention:**
> Just run **rta_hc**, you don't need to run the other two images, rta_hc is based on rta_hc_inst and rta_hc_conf
> The **-d** (option) means run the container in detach mode, which means that the container will persist in the system.
> The **-p XXXX:YYYY** (option) means the exposed port YYYY will be mapped to the system port XXXX.


----------

## Docker Management
-------------------------


### Check Docker Status (anywhere)
--------------------

To check whether a docker is up and running use the command

    docker ps

### Enter Docker Container (anywhere)
--------------------
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

### Stop Docker Container (anywhere)
--------------------
To stop a running containers use the command


    docker stop $(docker ps -q)
> **Attention:**
>If there is more than one container up and running, substitute $(docker ps -q) with the exact **container ID**.

### Delete Docker Container (anywhere)
--------------------
To delete containers not running use the command

    docker rm $(docker ps -a -q)

> **Attention:**
> The **-a** (option) above means show all current and history containers

### Delete Docker Image (anywhere)
--------------------
To delete unsuccessful images of the name "none"
**First**, delete all history containers not running
**Second**, use the command

    docker images|grep none|awk '{print $3}'|xargs docker rmi


## Miscellaneous
-----------------

For detailed account of what the three dockerfiles are doing, please consult to the **COMMENTS** in the dockerfile.

----------