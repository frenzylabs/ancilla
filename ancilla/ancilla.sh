#!/bin/bash

# ANCILLA_HOME="$HOME/.ancilla"
HOME=/home/pi
ANCILLA_HOME="$HOME/.ancilla"

WIFI_CONFIG_FILE=$ANCILLA_HOME/wificfg.json
CONFIG_FILE=$ANCILLA_HOME/config.json

# docker run -it --name=ancilla2 --privileged --net host -v "$HOME/.ancilla":"$HOME/.ancilla" layerkeep/ancilla:staging-latest /bin/bash

CONFIG=`jq '.' $CONFIG_FILE`
WIFI_CONFIG=`jq '.' $WIFI_CONFIG_FILE`

echo "WifiConfig = $WIFI_CONFIG"

SYSTEM=$(jq '.system' <<< $CONFIG)
NODE=$(jq '.node' <<< $CONFIG)
WIFI=$(jq '.wifi' <<< $CONFIG)


load_config_vars() {
  NEW_CONFIG=`jq '.' $CONFIG_FILE`
  NEW_WIFI_CONFIG=`jq '.' $WIFI_CONFIG_FILE`
  NEWNODE=$(jq '.node' <<< $NEW_CONFIG)
  NEWWIFI=$(jq '.wifi' <<< $NEW_CONFIG)
  NEWSYSTEM=$(jq '.system' <<< $NEW_CONFIG)
}

load_config_vars

if ping -q -c 1 -W 1 8.8.8.8 >/dev/null; then
  echo "IPv4 is up"
  NETWORK_CONNECTED=true
else
  echo "IPv4 is down"
  NETWORK_CONNECTED=false
fi

update_node() {
  NODE_DOCKER_IMAGE=$(jq -r '.image' <<< $NEWNODE)
  NODE_DOCKER_IMAGE_TAG=$(jq -r '.tag' <<< $NEWNODE)
  NODE_AUTO_UPDATE=$(jq '.auto_update' <<< $NEWNODE)

  if [ "$NETWORK_CONNECTED" = "true" ]
  then
    NODE_LATEST_IMAGE_DIGEST=`docker pull $NODE_DOCKER_IMAGE:$NODE_DOCKER_IMAGE_TAG | grep Digest | awk {'print $2'}`
    echo "NODE LatestIMAGEDIGEST = $NODE_LATEST_IMAGE_DIGEST"
  fi
  
  if [ ! -z "$NODE_LATEST_IMAGE_DIGEST" ]
  then
    NEWNODE=$(jq '.latest_image_digest |= "'$NODE_LATEST_IMAGE_DIGEST'"' <<< $NEWNODE)
  else
    NODE_LATEST_IMAGE_DIGEST=$(jq -r '.current_image_digest' <<< $NODE)
  fi

  NODE_NEW_IMAGE_DIGEST=$(jq -r '.current_image_digest' <<< $NEWNODE)
  if [ -z "$NODE_NEW_IMAGE_DIGEST" ]
  then
    NEWNODE=$(jq '.current_image_digest |= "'$WIFI_LATEST_IMAGE_DIGEST'"' <<< $NEWNODE)
    NODE_NEW_IMAGE_DIGEST=$NODE_LATEST_IMAGE_DIGEST
  fi

  if [ "$NODE_AUTO_UPDATE" = "true" ]
  then
    NEWNODE=$(jq -r '.current_image_digest |= "'$NODE_LATEST_IMAGE_DIGEST'"' <<< $NEWNODE)
    NODE_NEW_IMAGE_DIGEST=$NODE_LATEST_IMAGE_DIGEST
  fi

}


run_ancilla() {
  NODE_CONTAINER_NAME=ancilla
  if [ "$(docker inspect -f '{{.State.Running}}' $NODE_CONTAINER_NAME 2>/dev/null)" = "true" ];
  then
    return
  fi
  NODE_CURRENT_IMAGE_DIGEST=$(jq -r '.current_image_digest' <<< $NODE)
  
  AUTO_UPDATE=$(jq '.auto_update' <<< $NEWNODE)

  NODE_CONTAINER_EXIST=$(docker ps -a --filter name=^$NODE_CONTAINER_NAME$ | grep $NODE_CONTAINER_NAME)
  NODE_DOCKER_IMAGE=$(jq -r '.image' <<< $NEWNODE)
  # NODE_DOCKER_IMAGE_TAG=$(jq -r '.tag' <<< $NEWNODE)
  echo "NODE IMAGE = $NODE_DOCKER_IMAGE"
  update_node
  

  if [ "$NEWNODE" = "$NODE" ]
  then
    echo "NODES ARE THE SAME"
  else
    echo "NODE = $NEWNODE"
    NODE=$NEWNODE    
    jq --argjson node "$NEWNODE" '.node |= $node' <<< $NEW_CONFIG > $CONFIG_FILE
  fi

  if [ "$NODE_NEW_IMAGE_DIGEST" != "$NODE_CURRENT_IMAGE_DIGEST" ]
  then
    if [ ! -z "$NODE_CONTAINER_EXIST" ]
    then
        echo "Removing container first" 
        docker rm $NODE_CONTAINER_NAME
    fi
    docker run --name=$NODE_CONTAINER_NAME -d --restart=on-failure --privileged --net host -v "$HOME/.ancilla":"$HOME/.ancilla" $NODE_DOCKER_IMAGE@$NODE_NEW_IMAGE_DIGEST
  else
    if [ ! -z "$NODE_CONTAINER_EXIST" ]
    then
        echo "Start container" 
        docker start $NODE_CONTAINER_NAME
    else
      docker run --name=$NODE_CONTAINER_NAME -d --restart=on-failure --privileged --net host -v "$HOME/.ancilla":"$HOME/.ancilla" $NODE_DOCKER_IMAGE@$NODE_NEW_IMAGE_DIGEST
    fi
  fi
}


update_wifi() {
  WIFI_DOCKER_IMAGE=$(jq -r '.image' <<< $NEWWIFI)
  WIFI_DOCKER_IMAGE_TAG=$(jq -r '.tag' <<< $NEWWIFI)

  if [ "$NETWORK_CONNECTED" = "true" ]
  then
    WIFI_LATEST_IMAGE_DIGEST=`docker pull $WIFI_DOCKER_IMAGE:$WIFI_DOCKER_IMAGE_TAG | grep Digest | awk {'print $2'}`
    echo "WIFI Latest IMAGEDIGEST = $WIFI_LATEST_IMAGE_DIGEST"
  fi
  
  if [ ! -z "$WIFI_LATEST_IMAGE_DIGEST" ]
  then
    NEWWIFI=$(jq '.latest_image_digest |= "'$WIFI_LATEST_IMAGE_DIGEST'"' <<< $NEWWIFI)
  else
    WIFI_LATEST_IMAGE_DIGEST=$(jq -r '.current_image_digest' <<< $WIFI)
  fi

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


run_system() {
  REBOOT_TIME=$(jq '.reboot' <<< $SYSTEM)
  NEW_REBOOT_TIME=$(jq '.reboot' <<< $NEWSYSTEM)
  if [ "$REBOOT_TIME" != "$NEW_REBOOT_TIME" ]
  then
    echo "rebooting system"
    sudo reboot
  fi

  RESTART_TIME=$(jq '.restart_ancilla' <<< $SYSTEM)
  NEW_RESTART_TIME=$(jq '.restart_ancilla' <<< $NEWSYSTEM)
  if [ "$RESTART_TIME" != "$NEW_RESTART_TIME" ]
  then
    echo "restart ancilla"
    SYSTEM=$NEWSYSTEM
    docker restart ancilla
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
    if [ "$NEWSYSTEM" != "$SYSTEM" ]
    then
      run_system
    fi

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

