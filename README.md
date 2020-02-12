Ancilla
=======

An application to be able to manage all your 3D printers, cameras and files from one place.   

# Dev

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

```
$ cd ancilla/ui
$ yarn install --check-files
$ npm start
```

## Running Dev

```
$ make
```

## Packaging

```
$ make package
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


