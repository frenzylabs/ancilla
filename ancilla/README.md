Ancilla
=======

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


sudo vi /lib/systemd/system/ancilla.service
sudo systemctl enable ancilla
sudo systemctl daemon-reload
<!-- systemctl enable ancilla -->


docker run -d --restart=unless-stopped --privileged --net host -v "$HOME/.ancilla":"$HOME/.ancilla" layerkeep/ancilla:initial
  -v <HOST_PATH>/wpa_supplicant.conf:<CONTAINER_PATH>/wpa_supplicant.conf cjimti/iotwifi

docker run -d --restart=unless-stopped --privileged --net host -v $(pwd)/wificfg.json:/cfg/wificfg.json cjimti/iotwifi
  -v <HOST_PATH>/wpa_supplicant.conf:<CONTAINER_PATH>/wpa_supplicant.conf cjimti/iotwifi