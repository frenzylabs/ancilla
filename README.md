Ancilla
=======

An application to be able to manage all your 3D printers, cameras and files from one place.   

# 

## Installation
Using Prebuilt Raspberry PI Image

  1. Download Image
  2. Mount SD card on your computer and flash the Image to it (using something like etcher)
      A. If you want to connect to you wifi network immediately and not have to join the access point to put in your credentials
         
  3. Then plug the SD card into your raspberry pi and start it up.  It will take a few minutes.  
  4.  If you didnt manually add the wifi credentials then you'll need to connect to the Raspberry Pi access point.  
      



  On first boot it will expand your partition to take up all available space on your SD card.
  This can be prevented by opening up the file `cmdline.txt` and removing the text `quiet init=/usr/lib/raspi-config/init_resize.sh`

  
## Connect To Your Wifi Network
  ### Access Point:
  1. Look for a wifi network called ancilla-setup-{....}  and Join the network with password `ancilla1134`
  2. In your browser you should be able to go to `http://ancilla.local:5000` 
        If for some reason that doesn't work you can go to the IP address `http://192.168.27.1:5000`
  3.  Bottom left of the webpage you should see a gear.  Click that and modal will appear where you can add your wifi credentials. 
        ** There is an issue where as soon as it connects it changes networks so the call to connect never returns.  If it fails try 
        refreshing the page and if you can't access ancilla.local then try going to the IP address. 
  4. Once connected you can switch back to your network.  


  ### Manually
  Before First Boot 
  Mount SD Card on your computer and add a file named `wpa_supplicant.conf` in the root directory with the following content.
  Be sure to replace the network ssid and psk with your wifi network. 
  ```
  country=us
  ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
  update_config=1

  network={
    scan_ssid=1
    ssid="MyNetworkSSID"
    psk="Pa55w0rd1234"
  }
  ```


# Development

## Setup: (Mac, linux unsure)

```
$ git clone https://github.com/yyuu/pyenv.git ~/.pyenv
$ git clone https://github.com/yyuu/pyenv-virtualenv.git ~/.pyenv/plugins/pyenv-virtualenv
```


## Add the following to your .zshrc/.bash_profile:

```
## Pyenv
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"

if command -v pyenv 1>/dev/null 2>&1; then

  eval "$(pyenv init -)"
  eval "$(pyenv virtualenv-init -)"
fi
```

## Then:

```
$ env PYTHON_CONFIGURE_OPTS="--enable-shared" pyenv install 3.7.4
```

## After install, cd in to directory and do the following:

```
$ virtualenv .venv --no-site-packages
$ source .venv/bin/activate
$ pip install -r requirements.txt
```

## For the UI setup:

You can work on the UI separately by cloning the UI repo:
`git clone git@github.com:frenzylabs/ancilla-ui.git`

Or you can pull the submodule down by running:
`make update-ui`

Then run it with:

```
$ cd ancilla/ui
$ yarn install --check-files
$ yarn start
```

## Running Dev

```
$ make run
```

## Packaging

Updates the UI module, cleans it and packages it

```
$ make build-ui
```



# docker cleanup
docker rm $(docker ps -a -q)
docker rmi $(docker images | grep "<none>" | awk '{print $3}')
docker rmi $(docker images | awk '{print $3}')

sudo mv ancilla.service /lib/systemd/system/ancilla.service

sudo vi /lib/systemd/system/ancilla.service
sudo systemctl enable ancilla
sudo systemctl daemon-reload
<!-- systemctl enable ancilla -->


sudo iptables -t nat -I PREROUTING -p tcp --dport 80 -j REDIRECT --to-port 5000
sudo iptables -I INPUT -p tcp --dport 5000 -j ACCEPT

docker run --name=ancilla -d --restart=unless-stopped --privileged --net host -v "$HOME/.ancilla":"$HOME/.ancilla" layerkeep/ancilla:staging-972ea36

docker run --name=ancilla -d --restart=unless-stopped --privileged --net host -v "$HOME/.ancilla":"/root/.ancilla" layerkeep/ancilla:staging-972ea36

  -v <HOST_PATH>/wpa_supplicant.conf:<CONTAINER_PATH>/wpa_supplicant.conf cjimti/iotwifi

docker run -d --restart=unless-stopped --privileged --net host -v $HOME/wificfg.json:/cfg/wificfg.json cjimti/iotwifi
  -v <HOST_PATH>/wpa_supplicant.conf:<CONTAINER_PATH>/wpa_supplicant.conf cjimti/iotwifi


docker run -d --restart=unless-stopped --privileged --net host -v $HOME/wifinohost.json:/cfg/wificfg.json cjimti/iotwifi  


Expand sd card
`sudo raspi-config --expand-rootfs`

Camera:

v4l2-ctl -d /dev/video0 --list-formats
