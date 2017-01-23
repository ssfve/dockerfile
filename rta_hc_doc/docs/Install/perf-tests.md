# Performance tests
```
[root@c2t08978 src]# python traffic_generate.py
usage: traffic_generate.py [-h] -u NB_USERS -p TRAFFIC_REF_PATH
                           [-d TEST_DURATION] [-l LAMBD_INV]
                           [-s SERVLET_POST_URL]
traffic_generate.py: error: argument -u/--nb_users is required
[root@c2t08978 src]# pwd
/opt/mount1/rta-hc/integration/rta-hc-framework-master/src

python traffic_generate.py -u "vincent.planat@hpe.com" -p "/opt/mount1/temp/1_msbandraw_062016.txt" -s "http://c2t08978.itcs.hpecorp.net:9797/simpleiothttp2kafka/raw_msband_v2" -d 620000 -l 20
```
