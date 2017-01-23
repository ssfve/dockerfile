
Access to B10: https://213.30.160.100

# Server 10.3.35.93
* installation under `/opt/rta_hc`: followed the process [documented on the cloud installation page](installation.md)
* (done) python + modules for cassandra + kafka + baysian
* (done) Java
* (done) Kafka
* (done) Spark
* (done) Cassandra (without keyspace creation with tables)
* (done) kairosDb
* (done) Grafana

# Server 10.3.35.93
* installation under `/opt/rta_hc`: followed the process [documented on the cloud installation page](installation.md)
* (done) python + modules for kafka


# EL20

* Installed the Wifi card into the Gateway and connected the antena
* Download Iso image: `CentOS-7-x86_64-Everything-1511.iso`
* Use [Rufus tool](http://rufus.akeo.ie/) to create an bootable USB key image
* Install CentOS-7
* Configure Hotspot Wifi in Bridge mode
    * http://www.cyberciti.biz/faq/debian-ubuntu-linux-setting-wireless-access-point/
    * https://nims11.wordpress.com/2012/04/27/hostapd-the-linux-way-to-create-virtual-wifi-access-point/
    * http://lea-linux.org/documentations/Point_d'acc%C3%A8s_s%C3%A9curis%C3%A9_par_hostAPd


```
yum install epel-release
yum install hostapd

[root@chenu20 hostapd]# lspci | grep Wireless
03:00.0 Network controller: Qualcomm Atheros AR9580 Wireless Network Adapter (rev 01)


Starting the NetworkManager service

First we are going to configure your CentOS system to automatically start the NetworkManager on startup. You can do this by running:
chkconfig NetworkManager on

Then we are going to start it so we can use it right away without needing to reboot:

service NetworkManager start
If you have done that in your graphical environment (Gnome), your Notification Area (usually in the Gnome panel on the top-right) will show a new icon. If you left-click on this icon, you will see a list of possible Wireless networks to connect to.

You may also want to disable the network and wpa_supplicant services at boot time, as NetworkManager will now handle these. For this, simply do:


chkconfig network off
chkconfig wpa_supplicant off

```
