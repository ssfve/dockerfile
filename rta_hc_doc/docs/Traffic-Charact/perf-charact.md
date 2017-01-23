## Objective
The objective of this performance characterization exercise is to arrive at the end with a tool which will allows us to size a setup based on spark.
The tool will be a simple excel sheet.
So we need to characterize each components of the setup, such as we can incorporate them into the final model

Monit has been installed so far to collect characterization parameters.
I don't know yet if we will have the facilities to collect the data the way we need using monit.
The following specs should help us identifying if monit is the right choice or not.

Another simple option could be also to use sar (http://www.golinuxhub.com/2014/02/tutorial-for-monitoring-tools-sar-and.html) and reformat the output into excel.
This would be a lest complex approach with good granularity.

## List of components
The final model should take into account all the most significant components (in term of resource consuption) of the solution.
Below is the list of these components.

* _Main-analytic node_
  * processor accelerometer (spark-job)
  * processor gyroscope (spark-job)
  * processor distance (spark-job)
  * har aggregator (spark-job)
  * kafka
  * HDFS
  * tomcat (acquisition servlet)
  * Others
* _Main-storage node_
  * Cassandra
  * KairosDB
  * Grafana
  * raw_writer (spark-job)
  * novelty_detector (spark-job)
  * Others


## list of expected characterization parameters
We need to collect th below parameter for each component that we analyse.
* CPU utilization
* Load Average
* Memory
* Network Interfaces
* Disk I/O
* File System spaces utilization

## Individual component characterization

**Input traffic for spark-job**
* Ideally we should quantify the input traffic of each component we want to characterize.
* I propose first to  focus on spark-job (rta_processor, har_predict, raw_writer, novelty_detect)
* We need to mesure the **Kafka traffic-rate per topic (nb-msg/s)** for a single user traffic
  * Inject POST to the System
  * Mesure the **per topic** kafka traffic (nb of message per second) during _processing phase_ (POST duration)


**Per component**
* inject a single user traffic (1 POST every ~1mn) during 10mn
* Retrieve the _characterization parameters_ for each component
* Present results as a graph.
  * Export results as CSV
  * Excel sheet

## Characterization with multiple users
* Impact of the number of users
  * `<nb_users>`: increase the number of users (from 1 to x for example)
  * `<lambd_inv>`: 20s
  * `<duration_test>`(ms): ( `<lambd_inv>` x `<nb_users>` + 10 x 60 ) * 1000
* The idea here is to identify the maximum number of users the platform can support
* During the 15mn stable phase, we must capture the characterization parameters for each components
* Present results as a graph
