# demo Script

Source Sharepoint>Documents>Decks: https://ent302.sharepoint.hpe.com/teams/rtahc/Shared%20Documents/Decks/RPM%20-%20WW-HealthCare.pptx

## slide 2: Agenda
During the last 8 months an HP-IT team developed a big-data for healthcare opportunity.
The objective of the current session is to present

* The problem this solution is tackling
* What is the user story behind this solution and which actors are involved in
* Which software stack has been built up and integrated for this purpose
* Which advanced analytic data flow is underlying the end 2 end execution of this platform
* Finally a demo will be executed to illustrate the concepts developed with this prototype


## slide-3: Remote Patient Monitoring (RPM)
All Healthcare agency are facing, nowadays, a high budget pressures. In particular the hospitals who have to face different challenges.
To name just a few of the most important ones:

* The coming growth of people above 60 which should reach 20% of the population around the 2050
* The importance of chronical disease like diabetic, Chronical Obstructive Disease, or Heart disease in our Industrial society

Healthcare agency, who are highly contributing to the funding of most of these institutions are starting to establish programs for a more strict budget control.
Chronical disease is one of the import cost centers of hospital. In the US, in 2012 (the model is starting to be applied in Europe) the US affordable Card defined the readmission rate as a KPI subject to penalties.
In fact, most hospitals face a high readmission rate within the 30 days after a first visit for a chronical disease (around 20/25%)
A growing number of chronical disease are beeing included in the penalty list

One of the solutions, proposed by the industry, to help hospitals in this context, is to deploy remote patient monitoring solution.
This approach has multiple advantage

* Offer the opportunity to the patient to stay at home avoiding un-necessary periodic visits to the hospitals. Less stress less visit costs.
* Offer the opportunity to the hospital to continue monitoring the evolution of the disease and be ready to ask for a visit when needed.

## slide-4: Story Board
The Story board developed for this opportunity is the following

* phase-1
    * Patient is equipped with various sensors that are collecting both physiological and activity data from the patient.
    * Periodically the patient is "labelling" these data. For example, it informs the system about its current activity (walking, sitting etc ...) or provide some feedback about its current health status.
    * This produces a "labelled" traffic that is used to train different patient models.
    * In the current proposal, model are individuals. Each patient has its own one characterizing its pathology, behavior and chronical disease(s)
    * This phase make take several days

At the end of phase-1 the system trained a set of models for each patient, that will be used during the real-time data processing.

* phase-2
    * The Analytic platform interfaces with the Patient
        * It collects periodically the activity and physiological data. This time no labelling is required. Realtime analytic is performed by the platform to detect
            * The patient current physical activity (Walking, Sitting etc ...)
            * If something new (novelty detection) is currently happening
        * It sends some patient coaching information like, Daily energy expenditure, Activity recommendation etc ...
        * As a Result
            * The patient has a better control of his disease, stress may be decreased resulting into a better disease self management

    * The Analytic platform interfaces with the Clinician
        * If novelty is detected by the system an alert is sent to the doctor.
        * A complete dashboard of the patient profile along with an history of his activity and health sensors.
        * As a result he
            * Anticipates Sever degradation
            * Can alert the patient and ask for a visit

## slide-5: Realtime Analytic stack
A full open-source stack has been setup to address the above functionalities

* At the edge a Microsoft Band-2 is connected vi bluetooth with a Mobile Apps.
    * The Microsoft Band-2 is equipped with 7 activity sensors (gyroscope x,y,z - accelerometer, distance, barometer, altimeter etc ...) and 3 physiological ones (respiration rate, Skin temperature and Heart-Rate)
    * The mobile apps is in charge of buffering the traffic received from the Band-2 and sending it to the HP Cloud every minute (around 200Kb)
* A Data normalization layer, running Nifi, is in charge of extracting the traffic and posting it to the Kafka messaging bus
* The Spark micro batch Analytic framework is then used to process these data in 3 static-pages
    * HAR
    * Data fusion
    * Novelty detection
* A Cassandra Realtime database is used to store data
* R is used to train Bayesian Model (for novelty detection)
* Hadoop is used to store Randomforest models for HAR

## slide-6: Analytic data follow
In this slide we present the analytic data flow taking place in this prototype

* On the top left, off-line data training is presented. Based on labelled data, individual RandomForest (classifier) and Bayesian model are trained **for each patient**
* The real-time traffic generated by the Microsoft Band-2 is split in 2 parts
    * Activity data (accel, gyroscope etc ...) is sent to independant RandomForest classifier.
        * each classifier works on different data and produce an Activity prediction (Sitting, Walking etc ...)
    * A fusion analytic is then performed based output of each independant classifier.
        * This stage applies a Majority voting decision to produce a final Patient Activity
    * Physiological data (HR, RR, SkT) are sent to the baysian model along with the infered activity.
        * The system query the model 4 times based on this 4 inputs mixing each time differently the parameter
            * What is the % of chance to have this activity given the current HR, RR, SkT
            * What is the % of chance to have this HR given the current Activity, RR, SkT
            * etc ...
        * If we have more than 50% of the answer which are below 10% (which is our novelty detection threshold) we consider we have a Novel time framework
        * Then we accumulate these time frame over a period of 10mn and compute a resulting novelty rate.

# Demo script
* The current dashboard is divided in 2 parts
    * Upper part is representing real time physiological data (HR, RR, SkT)
    * Lower left part is representing the HAR as a result of the fusion Analytic
    * Lower right part is displaying the novelty rate as computed in realtime by the system

* Exercise -1
    * detecting HAR
        * Start walking during 2 mn

* Exercice -2
    * detecting novelty
        * It is quite difficult to generate  "naturally" novelty. I've tried to hold my breath during 1mn but the sensor is not very sensible.
        * The option chosen here is to influence the real-time traffic received by the system
        * For that a front end servlet is used to decrease or increase by a certain percentage the physiological data values.
