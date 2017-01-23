


# release V1.1

# impacted files (v1.1)
* `src/rta_processor_simple.py`
* `src/har_predict_aggr_ensemble.py`
* `conf/rta.properties`
* `src/rta_constants.py`
## Major update
The main update is the introduction of grainne's contribution on the Platform + removing the process control (not used at all)

* New classifier that are leveraging other python (pandas) libraries and that are not yet supported by spark.
* As a consequence,
  * HDFS has been removed from the platform. All the models are now file system based and still located into the `data-models` directory
  * The `rta_processor_simple_1_1.py`, `har_predict_aggr_ensemble_1_1.py` and `novelty_detect.py` do not contain any capability for process control (as it was originaly imagined). Simplification
  * This means that we use spark mainly for the spark-streaming and the Spark-SQL (analytic) capabilities (for easy feature extraction)
  * The `rta_processor_simple_1_1.py` and `har_predict_aggr_ensemble_1_1.py`can still support in theory the spark capabilities but this branch of code is not maintain in the source.
  * The `novelty_detect_1_1.py` has not been touch except the process control part.

## release logs
  * 16/09: `model_generator.py` updated on github master. Support now sklearn. Generate the models for the simple classifier **and** aggregator using these new data-science libraries
