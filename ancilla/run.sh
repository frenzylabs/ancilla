#!/bin/bash

ANCILLA_HOME="$HOME/.ancilla"

LTIME=`stat -c %Z $ANCILLA_HOME/discovery.txt`

LNETWORKON=$(grep -Po "(?<=^AP=).*" $ANCILLA_HOME/discovery.txt)
LSSID=""


CONTAINER_NAME=wifi

CONTAINER_EXIST=$(docker ps -a --filter name=^$CONTAINER_NAME$ | grep $CONTAINER_NAME)

if [ -z "$CONTAINER_EXIST" ]
then
  echo "NO WIFI CONTAINER"
else
  echo "WIFI CONTAINER"
fi

# WIFIRUNNING=`docker inspect -f '{{.State.Running}}' wifi`
toggle_wifi() {
  local recreate="$1"
  echo "TW RECREATE=$recreate"
  if [ "$(docker inspect -f '{{.State.Running}}' $CONTAINER_NAME 2>/dev/null)" = "true" ];
  then
    if [ ! -z "$LNETWORKON" ] && [ "$LNETWORKON" = "false" ]
    then    
      echo "Wifi Container Stoping"
      docker stop wifi
    else
      echo "Wifi Container Running"
      if [ ! -z "$recreate" ] && [ "$recreate" = "true" ]
      then
        docker stop wifi
        start_wifi $recreate
      fi

    fi
  else
    if [ ! -z "$LNETWORKON" ] && [ $LNETWORKON = "true" ]
    then
      echo "Wifi Container Starting"
      start_wifi $recreate
      # if [ ! -z "$CONTAINER_EXIST" ]; 
      # then
      #   echo "Removing container first" 
      #   docker rm $CONTAINER_NAME
      # fi
      # docker run -d --name=wifi --restart=on-failure --privileged --net host -v $HOME/wificfg.json:/cfg/wificfg.json cjimti/iotwifi      
    else
      echo "Wifi Container Not Running"
    fi
  fi
}

start_wifi() {
  echo "START WIFI"
  CONTAINER_EXIST=$(docker ps -a --filter name=^$CONTAINER_NAME$ | grep $CONTAINER_NAME)
  local recreate="$1"
  local createnew=""
	if [ ! -z "$recreate" ] && [ "$recreate" = "true" ] && [ ! -z "$CONTAINER_EXIST" ]
  then
   docker rm $CONTAINER_NAME
   createnew="true"
  fi
  if [ -z "$createnew" ] && [ ! -z "$CONTAINER_EXIST" ]; 
  then
    docker start wifi
  else
    docker run -d --name=wifi --restart=on-failure --privileged --net host -v $ANCILLA_HOME/wificfg.json:/cfg/wificfg.json cjimti/iotwifi
  fi
}


handle_wifi () {
  # local var1='C'
  # var2='D'
  echo "handle wifi"
  local networkon=$(grep -Po "(?<=^AP=).*" $ANCILLA_HOME/discovery.txt)
  local ssid=$(grep -Po "(?<=^SSID=).*" $ANCILLA_HOME/discovery.txt)
  local recreate=""
  if [ "$ssid" != "$LSSID" ] || [ -z "$ssid" ];  then
    echo "SSID needs to be added"
    recreate="true"
    if [ -z "$ssid" ]
    then
      local newssid=$(head -80 /dev/urandom | tr -dc 'a-z' | fold -w 6 | head -n 1)      
      ssid="ancilla-setup-$newssid"
      echo "NEWSSID = $ssid"
      echo "SSID=$ssid" >> $ANCILLA_HOME/discovery.txt
    fi    
    LSSID=$ssid
    echo "SETTING SSID IN WIFICFG"
    jq '.host_apd_cfg.ssid |= "'$LSSID'"' $ANCILLA_HOME/wificfg-default.json > $ANCILLA_HOME/wificfg.json
  fi
  if [ "$networkon" != "$LNETWORKON" ]
  then
    LNETWORKON=$networkon
  fi
  echo "RECREATE=$recreate"
  toggle_wifi $recreate
}


handle_wifi



while true    
do
   ATIME=`stat -c %Z $ANCILLA_HOME/discovery.txt`

   if [[ "$ATIME" != "$LTIME" ]]
   then    
       echo "RUN COMMAND"       
       handle_wifi
       LTIME=`stat -c %Z $ANCILLA_HOME/discovery.txt`
      #  LTIME=$ATIME
       
   fi
   sleep 5
done




# if [[NETWORKON = "true"]]
# then
#   echo "WIFI SHOULD BE RUNNING"
#   if [[WIFIRUNNING]]
  
#   docker run -d --restart=unless-stopped --privileged --net host -v $HOME/wificfg.json:/cfg/wificfg.json cjimti/iotwifi
# else
#   echo "WIFI SHOULD BE OFF"
#   docker ps -f name=wifi | grep -w wifid

#   docker ps --filter name=^wifi$

  

# NEWSSID=$(cat /dev/urandom | tr -dc 'a-z' | fold -w 6 | head -n 1)
# SSID="ancilla-setup-$NEWSSID"

# `jq '.host_apd_cfg.ssid |= "'$SSID'"' $HOME/wificfg-default.json > $HOME/wificfg.json`

# `jq 'del(.host_apd_cfg)' $HOME/wificfg.json > wifinohost.cfg`

# # jq '.host_apd_cfg.ssid |= "'$SSID'"' $HOME/wificfg.json > wificfg.json
# # {
# #   "dnsmasq_cfg": {
# #     "address": "/#/192.168.27.1",
# #     "dhcp_range": "192.168.27.100,192.168.27.150,1h",
# #     "vendor_class": "set:device,IoT"
# #   },
# #   "host_apd_cfg": {
# #     "ip": "192.168.27.1",
# #     "ssid": "ancilla-setud",
# #     "wpa_passphrase": "ancilla1134",
# #     "channel": "6"
# #   },
# #   "wpa_supplicant_cfg": {
# #     "cfg_file": "/etc/wpa_supplicant/wpa_supplicant.conf"
# #   }
# # }