### 
Should use a 4GB SD card to minimize the size and time

## Get the Base OS
I used raspbian-buster-lite

Flash the Image to an SD card (using etcher or whatever)
Once flashed remount it and open up the root directory.
Add an empty file named ssh.  This will allow you to ssh into it using:
pi@XXX.XXX.XXX.XXX
password:  raspberry

If you don't have ethernet available then you'll need to setup wpa_supplicant

Inside the same root diretory add a file named "wpa_supplicant.conf"

Add your wifi connection details:
```
country=us
update_config=1

network={
 scan_ssid=1
 ssid="MyNetworkSSID"
 psk="Pa55w0rd1234"
}
```



## INSTALL DOCKER

sudo apt update
sudo apt install -y \
     apt-transport-https \
     ca-certificates \
     curl \
     gnupg2 \
     software-properties-common

# Get the Docker signing key for packages
curl -fsSL https://download.docker.com/linux/$(. /etc/os-release; echo "$ID")/gpg | sudo apt-key add -

# Add the Docker official repos
echo "deb [arch=armhf] https://download.docker.com/linux/$(. /etc/os-release; echo "$ID") \
     $(lsb_release -cs) stable" | \
    sudo tee /etc/apt/sources.list.d/docker.list

# Install Docker
# The aufs package, part of the "recommended" packages, won't install on Buster just yet, because of missing pre-compiled kernel modules.
# We can work around that issue by using "--no-install-recommends"
sudo apt update
sudo apt install -y --no-install-recommends \
    docker-ce \
    cgroupfs-mount


sudo usermod -aG docker pi

reboot (or use sudo to run docker for right now)


apt install netcat 

# For Parsing Config files
apt install jq


mkdir /home/pi/.ancilla


To use the wifi docker image we need to disable the main wpa_supplicant.
`sudo systemctl mask wpa_supplicant.service`
`sudo pkill wpa_supplicant`
# rename wpa_supplicant on the host to ensure that it is not used.
`sudo mv /sbin/wpa_supplicant /sbin/no_wpa_supplicant`


From Local Device: Copy ancilla.service, ancilla.sh, wificfg.json, config.json to image

scp -r /path/to/ancilla/ancilla.service pi@192.XXX.XXX.XXX:/home/pi/ancilla.service
scp -r /path/to/ancilla/ancilla.sh pi@192.XXX.XXX.XXX:/home/pi/ancilla.sh

scp -r /path/to/ancilla/ancilla/wificfg.json pi@192.XXX.XXX.XXX:/home/pi/.ancilla/wificfg.json
scp -r /path/to/ancilla/ancilla/config.json pi@192.XXX.XXX.XXX:/home/pi/.ancilla/config.json

On Remote:

sudo mv ancilla.service /lib/systemd/system/ancilla.service
sudo systemctl enable ancilla
sudo systemctl daemon-reload


Make sure you're connected to network first time and then run:
`sudo systemctl start ancilla`
This will pull down the wifi and ancilla images


validate that both images are running 
`docker ps`

also check to see if ancilla-setup-xxxxx wifi network appeared


## Cleanup before creating image
If you added wpa_supplicant file then you'll want to remove your creds before creating the image:
Edit /etc/wpa_supplicant/wpa_supplicant.conf and delete the network information. 


Then we can stop and remove the containers (not the images)


docker stop wifi
docker rm wifi
docker stop ancilla
docker rm ancilla

## Update Wifi SSID to be empty
sudo systemctl stop ancilla (otherwise when we edit the wificfg.json file it will get regenerated)

Update the ssid field in wificfg.json file to be an empty string.

This will allow the ancilla script to generate a new one. 


# Auto Resize Partition

vi /boot/cmdline.txt 
`console=serial0,115200 console=tty1 root=PARTUUID=6c586e13-02 rootfstype=ext4 elevator=deadline fsck.repair=yes rootwait quiet init=/usr/lib/raspi-config/init_resize.sh`

// Maybe
sudo wget -qO /boot/cmdline.txt https://github.com/RPi-Distro/pi-gen/raw/master/stage1/00-boot-files/files/cmdline.txt
wget -qO - https://github.com/RPi-Distro/pi-gen/raw/master/stage2/01-sys-tweaks/00-patches/07-resize-init.diff | sudo patch -p3 -d /boot


#
sudo wget -qO resize2fs_once https://github.com/RPi-Distro/pi-gen/raw/master/stage2/01-sys-tweaks/files/resize2fs_once
sudo cp resize2fs_once /etc/init.d/resize2fs_once

sudo wget -qO /etc/init.d/resize2fs_once https://github.com/RPi-Distro/pi-gen/raw/master/stage2/01-sys-tweaks/files/resize2fs_once
sudo chmod +x /etc/init.d/resize2fs_once
sudo systemctl enable resize2fs_once


## Create Image

turn off the pi take the sd card and mount it on your computer
On Mac can use disk utility
  Select the external disk you just mounted (select the parent and not the boot partition)
  Right click on it and select "Image from 'device name'"
  Change format to cd/dvr
  and create the image
  
  When finished you can rename it .iso instead of .cdr
  Then you can use etcher to flash it to another memory card







