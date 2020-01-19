#!/bin/bash

ANCILLA_HOME="$HOME" #/.ancilla"

WIFI_CONFIG_FILE=$ANCILLA_HOME/wificfg.json
CONFIG_FILE=$ANCILLA_HOME/config.json
# ANCILLA_HOME=/Users/kmussel/Development/frenzylabs/ancilla/ancilla

# LCONFIGTIME=`stat -c %Z $CONFIG_FILE`
# LWIFITIME=`stat -c %Z $WIFI_CONFIG_FILE`

CONFIG=`jq '.' $CONFIG_FILE`
WIFI_CONFIG=`jq '.' $WIFI_CONFIG_FILE`


# jq '.node |= '$NEWNODE'' $ANCILLA_HOME/config.json > $ANCILLA_HOME/config.json
NODE=$(jq '.node' <<< $CONFIG)
WIFI=$(jq '.wifi' <<< $CONFIG)


load_config_vars() {
  NEW_CONFIG=`jq '.' $CONFIG_FILE`
  NEW_WIFI_CONFIG=`jq '.' $WIFI_CONFIG_FILE`
  NEWNODE=$(jq '.node' <<< $NEW_CONFIG)
  NEWWIFI=$(jq '.wifi' <<< $NEW_CONFIG)
}

load_config_vars

# TESTNODE=`jq '.node.latest_image_digest |= "tadad"' $ANCILLA_HOME/config.json`

# echo "TEST NODE = $TESTNODE"

# `jq '. |= "'$TESTNODE'"' $ANCILLA_HOME/config.json`

# NEWNODE=$(jq '.latest_image_digest |= "tada"' <<< $NODE)
# echo "NEW NODE = $NEWNODE"

# jq --argjson node "$NEWNODE" '.node |= $node' <<< $CONFIG

# jq '.node |= [$NEWNODE]' $ANCILLA_HOME/config.json
# jq --arg node_param $NEWNODE

run_ancilla() {
  NODE_CONTAINER_NAME=ancilla
  if [ "$(docker inspect -f '{{.State.Running}}' $NODE_CONTAINER_NAME 2>/dev/null)" = "true" ];
  then
    return
  fi

  
  AUTO_UPDATE=$(jq '.auto_update' <<< $NEWNODE)

  NODE_CONTAINER_EXIST=$(docker ps -a --filter name=^$NODE_CONTAINER_NAME$ | grep $NODE_CONTAINER_NAME)
  NODE_DOCKER_IMAGE=$(jq -r '.image' <<< $NEWNODE)
  NODE_DOCKER_IMAGE_TAG=$(jq -r '.tag' <<< $NEWNODE)
  echo "NODE IMAGE = $NODE_DOCKER_IMAGE"
  # if [ ! -z "$NODE_CONTAINER_EXIST" ]
  # then
  #   NODE_CURRENT_DIGEST=`docker inspect --format='{{.Image}}' ancilla`
  
  # ANCILLA_IMAGE_DIGEST=`docker images --no-trunc --format "{{.ID}}" $NODE_DOCKER_IMAGE`
  NODE_LATEST_IMAGE_DIGEST=`docker pull $NODE_DOCKER_IMAGE:$NODE_DOCKER_IMAGE_TAG | grep Digest | awk {'print $2'}`
  echo "NODE LatestIMAGEDIGEST = $NODE_LATEST_IMAGE_DIGEST"
  
  NEWNODE=$(jq '.latest_image_digest |= "'$NODE_LATEST_IMAGE_DIGEST'"' <<< $NEWNODE)

  CURRENT_IMAGE_DIGEST=$(jq -r '.current_image_digest' <<< $NEWNODE)
  if [ -z "$CURRENT_IMAGE_DIGEST" ]
  then
    NEWNODE=$(jq '.current_image_digest |= "'$NODE_LATEST_IMAGE_DIGEST'"' <<< $NEWNODE)
    CURRENT_IMAGE_DIGEST=$NODE_LATEST_IMAGE_DIGEST
  fi

  if [ "$AUTO_UPDATE" = "true" ]
  then
    NEWNODE=$(jq -r '.current_image_digest |= "'$NODE_LATEST_IMAGE_DIGEST'"' <<< $NEWNODE)
    if [ ! -z "$NODE_CONTAINER_EXIST" ]
    then
        echo "Removing container first" 
        docker rm $NODE_CONTAINER_NAME
    fi
    docker run --name=$NODE_CONTAINER_NAME -d --restart=on-failure --privileged --net host -v "$HOME/.ancilla":"$HOME/.ancilla" $NODE_DOCKER_IMAGE@$NODE_LATEST_IMAGE_DIGEST
  else
    if [ ! -z "$NODE_CONTAINER_EXIST" ]
    then
      echo "Start docker"
      docker start $NODE_CONTAINER_NAME
    else
      echo "RUN docker"
      docker run --name=$NODE_CONTAINER_NAME -d --restart=on-failure --privileged --net host -v "$HOME/.ancilla":"$HOME/.ancilla" $NODE_DOCKER_IMAGE@$CURRENT_IMAGE_DIGEST
    fi
  fi

  if [ "$NEWNODE" = "$NODE" ]
  then
    echo "NODES ARE THE SAME"
  else
    echo "NODES ARE DIFFERENT"
    echo "NODE = $NEWNODE"
    echo "CONFIG = $CONFIG"
    NODE=$NEWNODE
    jq --argjson node "$NEWNODE" '.node |= $node' <<< $CONFIG > $CONFIG_FILE
  fi
}


update_wifi() {
  WIFI_DOCKER_IMAGE=$(jq -r '.image' <<< $NEWWIFI)
  WIFI_DOCKER_IMAGE_TAG=$(jq -r '.tag' <<< $NEWWIFI)

  WIFI_LATEST_IMAGE_DIGEST=`docker pull $WIFI_DOCKER_IMAGE:$WIFI_DOCKER_IMAGE_TAG | grep Digest | awk {'print $2'}`
  echo "WIFI LatestIMAGEDIGEST = $WIFI_LATEST_IMAGE_DIGEST"
  
  NEWWIFI=$(jq '.latest_image_digest |= "'$WIFI_LATEST_IMAGE_DIGEST'"' <<< $NEWWIFI)

  WIFI_NEW_IMAGE_DIGEST=$(jq -r '.current_image_digest' <<< $NEWWIFI)
  if [ -z "$WIFI_NEW_IMAGE_DIGEST" ]
  then
    NEWWIFI=$(jq '.current_image_digest |= "'$WIFI_LATEST_IMAGE_DIGEST'"' <<< $NEWWIFI)
    WIFI_NEW_IMAGE_DIGEST=$WIFI_LATEST_IMAGE_DIGEST
  fi
}

run_wifi() {
  WIFI_CONTAINER_NAME=wifi
  WIFI_CONTAINER_EXIST=$(docker ps -a --filter name=^$WIFI_CONTAINER_NAME$ | grep $WIFI_CONTAINER_NAME)
  WIFI_DOCKER_IMAGE=$(jq -r '.image' <<< $NEWWIFI)

  WIFI_CURRENT_IMAGE_DIGEST=$(jq -r '.current_image_digest' <<< $WIFI)
  WIFI_NEW_IMAGE_DIGEST=$(jq -r '.current_image_digest' <<< $NEWWIFI)
  WIFI_RECREATE_CONTAINER=false
  if [ ! -z "$WIFI_CONTAINER_EXIST" ] || [ -z "$WIFI_NEW_IMAGE_DIGEST" ]
  then
    echo "Update wifi  container first" 
    update_wifi
  fi
  if [ "$WIFI_CURRENT_IMAGE_DIGEST" != "$WIFI_NEW_IMAGE_DIGEST" ]
  then
    WIFI_RECREATE_CONTAINER=true
  fi

  echo "WIFI IMAGE = $WIFI_DOCKER_IMAGE"

  NETWORKON=$(jq '.on' <<< $NEWWIFI)

  current_ssid=$(jq -r '.host_apd_cfg.ssid' <<< $WIFI_CONFIG)
  ssid=$(jq -r '.host_apd_cfg.ssid' <<< $NEW_WIFI_CONFIG)
  echo "SSID = $ssid"
  
  if [ "$ssid" != "$current_ssid" ] || [ -z "$ssid" ] || [ "$ssid" = "" ];  then
    echo "SSID needs to be added $ssid"
    if [ -z "$ssid" ] || [ "$ssid" = "" ]
    then
      local newssid=$(head -80 /dev/urandom | tr -dc 'a-z' | fold -w 6 | head -n 1)      
      ssid="ancilla-setup-$newssid"
      echo "NEWSSID = $ssid"
      echo "SETTING SSID IN WIFICFG"
      NEW_WIFI_CONFIG=$(jq '.host_apd_cfg.ssid |= "'$ssid'"' <<< $NEW_WIFI_CONFIG)
    fi
  fi


  if [ "$NEW_WIFI_CONFIG" = "$WIFI_CONFIG" ]
  then
    echo "WIFI CONFIG IS THE SAME"
  else
    echo "WIFI CONFIG IS DIFFERENT need to restart"
    echo "wifi = $NEW_WIFI_CONFIG"

    WIFI_RESTART=true

    WIFI_CONFIG=$NEW_WIFI_CONFIG
    echo $NEW_WIFI_CONFIG | jq . > $WIFI_CONFIG_FILE
  fi

  if [ "$NEWWIFI" = "$WIFI" ]
  then
    echo "WIFI IS THE SAME"

  else
    echo "WIFI IS DIFFERENT"
    
    if [ ! -z "$NETWORKON" ] && [ $NETWORKON = "true" ]
    then
      WIFI_RESTART=true
    fi
    echo "wifi = $NEWWIFI"
    WIFI=$NEWWIFI
    jq --argjson wifi "$NEWWIFI" '.wifi |= $wifi' <<< $NEW_CONFIG > $CONFIG_FILE
  fi


  handle_wifi_container
  
      
}


handle_wifi_container() {
  if [ "$WIFI_RESTART" = "true" ] || [ "$WIFI_RECREATE_CONTAINER" = "true" ] && [ ! -z "$WIFI_CONTAINER_EXIST" ]
  then
    
      docker stop $WIFI_CONTAINER_NAME
      if [ "$WIFI_RECREATE_CONTAINER" = "true" ]
      then
        docker rm $WIFI_CONTAINER_NAME
        docker run -d --name=wifi --restart=on-failure --privileged --net host -v $WIFI_CONFIG_FILE:/cfg/wificfg.json $WIFI_DOCKER_IMAGE@$WIFI_NEW_IMAGE_DIGEST
      else
        docker start $WIFI_CONTAINER_NAME
      fi

  else
    if [ "$(docker inspect -f '{{.State.Running}}' $WIFI_CONTAINER_NAME 2>/dev/null)" = "true" ];
    then
      if [ ! -z "$NETWORKON" ] && [ $NETWORKON = "true" ]
      then
        return
      else
        docker stop $WIFI_CONTAINER_NAME
      fi
      
    else
      if [ ! -z "$NETWORKON" ] && [ $NETWORKON = "true" ] 
      then
        if [ -z "$WIFI_CONTAINER_EXIST" ]
        then
          docker run -d --name=wifi --restart=on-failure --privileged --net host -v $WIFI_CONFIG_FILE:/cfg/wificfg.json $WIFI_DOCKER_IMAGE@$WIFI_NEW_IMAGE_DIGEST
        else
          docker start $WIFI_CONTAINER_NAME
        fi
      fi
    fi
  fi
}

run_wifi
run_ancilla

LCONFIGTIME=`stat -c %Z $CONFIG_FILE`
LWIFITIME=`stat -c %Z $WIFI_CONFIG_FILE`

while true    
do
  
  ACONFIGTIME=`stat -c %Z $CONFIG_FILE`
  AWIFITIME=`stat -c %Z $WIFI_CONFIG_FILE`
  
  if [ "$ACONFIGTIME" != "$LCONFIGTIME" ] || [ "$AWIFITIME" != "$LWIFITIME" ]
  then    
    load_config_vars
    if [ "$NEWWIFI" != "$WIFI" ] || [ "$NEW_WIFI_CONFIG" != "$WIFI_CONFIG" ]
    then
      run_wifi
    fi

    if [ "$NEWNODE" != "$NODE" ]
    then
      run_ancilla
    fi
    LCONFIGTIME=`stat -c %Z $CONFIG_FILE`
    LWIFITIME=`stat -c %Z $WIFI_CONFIG_FILE`
  fi
   sleep 5
done


# $ANCILLA_HOME/wificfg-default.json > $ANCILLA_HOME/wificfg.json

# # # run_ancilla() {
# #     CURRENT_DIGEST=`docker inspect --format='{{.Image}}' ancilla`
# #     CURRENT_IMAGE_ID=$(grep -Po "(?<=^AP=).*" $ANCILLA_HOME/discovery.txt)
# #     ANCILLA_IMAGE_ID=`docker images --format "{{.ID}}" layerkeep/ancilla:staging-latest`
# #     docker pull layerkeep/ancilla:staging-latest
# # #   docker run --name=ancilla -d --restart=unless-stopped --privileged --net host -v "$HOME/.ancilla":"$HOME/.ancilla" dfbb6772aa1flayerkeep/ancilla:staging-latest
# # # }

# LNETWORKON=`jq '.AP' $ANCILLA_HOME/config.json`
# LNETWORKON=$(grep -Po "(?<=^AP=).*" $ANCILLA_HOME/discovery.txt)
# LSSID=""


# CONTAINER_NAME=wifi

# # CONTAINER_EXIST=$(docker ps -a --filter name=^$CONTAINER_NAME$ | grep $CONTAINER_NAME)


# # WIFIRUNNING=`docker inspect -f '{{.State.Running}}' wifi`
# toggle_wifi() {
#   local recreate="$1"
#   echo "TW RECREATE=$recreate"
#   if [ "$(docker inspect -f '{{.State.Running}}' $CONTAINER_NAME 2>/dev/null)" = "true" ];
#   then
#     if [ ! -z "$LNETWORKON" ] && [ "$LNETWORKON" = "false" ]
#     then    
#       echo "Wifi Container Stoping"
#       docker stop wifi
#     else
#       echo "Wifi Container Running"
#       if [ ! -z "$recreate" ] && [ "$recreate" = "true" ]
#       then
#         docker stop wifi
#         start_wifi $recreate
#       fi

#     fi
#   else
#     if [ ! -z "$LNETWORKON" ] && [ $LNETWORKON = "true" ]
#     then
#       echo "Wifi Container Starting"
#       start_wifi $recreate
#       # if [ ! -z "$CONTAINER_EXIST" ]; 
#       # then
#       #   echo "Removing container first" 
#       #   docker rm $CONTAINER_NAME
#       # fi
#       # docker run -d --name=wifi --restart=on-failure --privileged --net host -v $HOME/wificfg.json:/cfg/wificfg.json cjimti/iotwifi      
#     else
#       echo "Wifi Container Not Running"
#     fi
#   fi
# }

# start_wifi() {
#   echo "START WIFI"
#   CONTAINER_EXIST=$(docker ps -a --filter name=^$CONTAINER_NAME$ | grep $CONTAINER_NAME)
#   local recreate="$1"
#   local createnew=""
# 	if [ ! -z "$recreate" ] && [ "$recreate" = "true" ] && [ ! -z "$CONTAINER_EXIST" ]
#   then
#    docker rm $CONTAINER_NAME
#    createnew="true"
#   fi
#   if [ -z "$createnew" ] && [ ! -z "$CONTAINER_EXIST" ]; 
#   then
#     docker start wifi
#   else
#     docker run -d --name=wifi --restart=on-failure --privileged --net host -v $ANCILLA_HOME/wificfg.json:/cfg/wificfg.json cjimti/iotwifi
#   fi
# }


# handle_wifi () {
#   # local var1='C'
#   # var2='D'
#   echo "handle wifi"
#   local networkon=$(grep -Po "(?<=^AP=).*" $ANCILLA_HOME/discovery.txt)
#   local ssid=$(grep -Po "(?<=^SSID=).*" $ANCILLA_HOME/discovery.txt)
#   local recreate=""
#   if [ "$ssid" != "$LSSID" ] || [ -z "$ssid" ];  then
#     echo "SSID needs to be added"
#     recreate="true"
#     if [ -z "$ssid" ]
#     then
#       local newssid=$(head -80 /dev/urandom | tr -dc 'a-z' | fold -w 6 | head -n 1)      
#       ssid="ancilla-setup-$newssid"
#       echo "NEWSSID = $ssid"
#       echo "SSID=$ssid" >> $ANCILLA_HOME/discovery.txt
#     fi    
#     LSSID=$ssid
#     echo "SETTING SSID IN WIFICFG"
#     jq '.host_apd_cfg.ssid |= "'$LSSID'"' $ANCILLA_HOME/wificfg-default.json > $ANCILLA_HOME/wificfg.json
#   fi
#   if [ "$networkon" != "$LNETWORKON" ]
#   then
#     LNETWORKON=$networkon
#   fi
#   echo "RECREATE=$recreate"
#   toggle_wifi $recreate
# }


# handle_wifi



# while true    
# do
#    ATIME=`stat -c %Z $ANCILLA_HOME/discovery.txt`

#    if [[ "$ATIME" != "$LTIME" ]]
#    then    
#        echo "RUN COMMAND"       
#        handle_wifi
#        LTIME=`stat -c %Z $ANCILLA_HOME/discovery.txt`
#       #  LTIME=$ATIME
       
#    fi
#    sleep 5
# done




# # if [[NETWORKON = "true"]]
# # then
# #   echo "WIFI SHOULD BE RUNNING"
# #   if [[WIFIRUNNING]]
  
# #   docker run -d --restart=unless-stopped --privileged --net host -v $HOME/wificfg.json:/cfg/wificfg.json cjimti/iotwifi
# # else
# #   echo "WIFI SHOULD BE OFF"
# #   docker ps -f name=wifi | grep -w wifid

# #   docker ps --filter name=^wifi$

  

# # NEWSSID=$(cat /dev/urandom | tr -dc 'a-z' | fold -w 6 | head -n 1)
# # SSID="ancilla-setup-$NEWSSID"

# # `jq '.host_apd_cfg.ssid |= "'$SSID'"' $HOME/wificfg-default.json > $HOME/wificfg.json`

# # `jq 'del(.host_apd_cfg)' $HOME/wificfg.json > wifinohost.cfg`

# # # jq '.host_apd_cfg.ssid |= "'$SSID'"' $HOME/wificfg.json > wificfg.json
# # # {
# # #   "dnsmasq_cfg": {
# # #     "address": "/#/192.168.27.1",
# # #     "dhcp_range": "192.168.27.100,192.168.27.150,1h",
# # #     "vendor_class": "set:device,IoT"
# # #   },
# # #   "host_apd_cfg": {
# # #     "ip": "192.168.27.1",
# # #     "ssid": "ancilla-setud",
# # #     "wpa_passphrase": "ancilla1134",
# # #     "channel": "6"
# # #   },
# # #   "wpa_supplicant_cfg": {
# # #     "cfg_file": "/etc/wpa_supplicant/wpa_supplicant.conf"
# # #   }
# # # }