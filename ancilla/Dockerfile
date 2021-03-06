FROM balenalib/raspberry-pi-debian-python:3.7-buster-build

RUN mkdir -p /home/pi/ancilla 
WORKDIR /home/pi/
# RUN wget https://bootstrap.pypa.io/get-pip.py
# python3-dev \
    # python3-pip \
RUN apt-get update && apt-get dist-upgrade -y && apt-get install -y \
    libatlas-base-dev \
    libjasper1 \
    libqt4-test \
    libgtk-3-0 \
    ffmpeg

# something with the baleana python doesnt have the pip indices and this adds them
RUN apt-get install -y python3-pip && apt remove python3-pip

# RUN python3.7 get-pip.py
RUN pip install --no-cache-dir --upgrade pip
WORKDIR /home/pi/ancilla

COPY requirements.txt .
RUN pip install -r requirements.txt


RUN mkdir -p /home/pi/ancilla/ancilla
COPY ancilla /home/pi/ancilla/ancilla/

COPY VERSION .
COPY README.md .
COPY setup.py .

RUN mkdir -p /home/pi/.ancilla
COPY config.json /home/pi/.ancilla
COPY wificfg.json /home/pi/.ancilla


# RUN python setup.py bdist
# VOLUME [ "" ]
ENV HOME=/home/pi
CMD ["python", "-m", "ancilla"]

# docker run -d --restart=always --privileged --net host -it -v "~/.ancilla":"$HOME/" layerkeep/ancilla:initial


# # FROM balenalib/raspberry-pi-debian:buster-build

# # # remove several traces of debian python
# # RUN apt-get purge -y python.*

# # # http://bugs.python.org/issue19846
# # # > At the moment, setting "LANG=C" on a Linux system *fundamentally breaks Python 3*, and that's not OK.
# # ENV LANG C.UTF-8

# # # key 63C7CC90: public key "Simon McVittie <smcv@pseudorandom.co.uk>" imported
# # # key 3372DCFA: public key "Donald Stufft (dstufft) <donald@stufft.io>" imported
# # RUN gpg --batch --keyserver keyring.debian.org --recv-keys 4DE8FF2A63C7CC90 \
# # 	&& gpg --batch --keyserver keyserver.ubuntu.com --recv-key 6E3CBCE93372DCFA \
# # 	&& gpg --batch --keyserver keyserver.ubuntu.com --recv-keys 0x52a43a1e4b77b059

# # ENV PYTHON_VERSION 3.7.5

# # # if this is called "PIP_VERSION", pip explodes with "ValueError: invalid truth value '<VERSION>'"
# # ENV PYTHON_PIP_VERSION 19.3.1

# # ENV SETUPTOOLS_VERSION 41.6.0

# # RUN set -x \
# # 	&& curl -SLO "http://resin-packages.s3.amazonaws.com/python/v$PYTHON_VERSION/Python-$PYTHON_VERSION.linux-armv6hf-openssl1.1.tar.gz" \
# # 	&& echo "1e8a493b110a024aab889812e6fabe821cfdff77f3faf4cdb2a71c887ca5a4ab  Python-$PYTHON_VERSION.linux-armv6hf-openssl1.1.tar.gz" | sha256sum -c - \
# # 	&& tar -xzf "Python-$PYTHON_VERSION.linux-armv6hf-openssl1.1.tar.gz" --strip-components=1 \
# # 	&& rm -rf "Python-$PYTHON_VERSION.linux-armv6hf-openssl1.1.tar.gz" \
# # 	&& ldconfig \
# # 	&& if [ ! -e /usr/local/bin/pip3 ]; then : \
# # 		&& curl -SLO "https://raw.githubusercontent.com/pypa/get-pip/430ba37776ae2ad89f794c7a43b90dc23bac334c/get-pip.py" \
# # 		&& echo "19dae841a150c86e2a09d475b5eb0602861f2a5b7761ec268049a662dbd2bd0c  get-pip.py" | sha256sum -c - \
# # 		&& python3 get-pip.py \
# # 		&& rm get-pip.py \
# # 	; fi \
# # 	&& pip3 install --no-cache-dir --upgrade --force-reinstall pip=="$PYTHON_PIP_VERSION" setuptools=="$SETUPTOOLS_VERSION" \
# # 	&& find /usr/local \
# # 		\( -type d -a -name test -o -name tests \) \
# # 		-o \( -type f -a -name '*.pyc' -o -name '*.pyo' \) \
# # 		-exec rm -rf '{}' + \
# # 	&& cd / \
# # 	&& rm -rf /usr/src/python ~/.cache

# # # install "virtualenv", since the vast majority of users of this image will want it
# # RUN pip3 install --no-cache-dir virtualenv

# # ENV PYTHON_DBUS_VERSION 1.2.8

# # # install dbus-python dependencies 
# # RUN apt-get update && apt-get install -y --no-install-recommends \
# # 		libdbus-1-dev \
# # 		libdbus-glib-1-dev \
# # 	&& rm -rf /var/lib/apt/lists/* \
# # 	&& apt-get -y autoremove

# # # install dbus-python
# # RUN set -x \
# # 	&& mkdir -p /usr/src/dbus-python \
# # 	&& curl -SL "http://dbus.freedesktop.org/releases/dbus-python/dbus-python-$PYTHON_DBUS_VERSION.tar.gz" -o dbus-python.tar.gz \
# # 	&& curl -SL "http://dbus.freedesktop.org/releases/dbus-python/dbus-python-$PYTHON_DBUS_VERSION.tar.gz.asc" -o dbus-python.tar.gz.asc \
# # 	&& gpg --verify dbus-python.tar.gz.asc \
# # 	&& tar -xzC /usr/src/dbus-python --strip-components=1 -f dbus-python.tar.gz \
# # 	&& rm dbus-python.tar.gz* \
# # 	&& cd /usr/src/dbus-python \
# # 	&& PYTHON_VERSION=$(expr match "$PYTHON_VERSION" '\([0-9]*\.[0-9]*\)') ./configure \
# # 	&& make -j$(nproc) \
# # 	&& make install -j$(nproc) \
# # 	&& cd / \
# # 	&& rm -rf /usr/src/dbus-python

# # # make some useful symlinks that are expected to exist
# # RUN cd /usr/local/bin \
# # 	&& ln -sf pip3 pip \
# # 	&& { [ -e easy_install ] || ln -s easy_install-* easy_install; } \
# # 	&& ln -sf idle3 idle \
# # 	&& ln -sf pydoc3 pydoc \
# # 	&& ln -sf python3 python \
# # 	&& ln -sf python3-config python-config

# # # set PYTHONPATH to point to dist-packages
# # ENV PYTHONPATH /usr/lib/python3/dist-packages:$PYTHONPATH

# # # CMD ["echo","'No CMD command was set in Dockerfile! Details about CMD command could be found in Dockerfile Guide section in our Docs. Here's the link: https://balena.io/docs"]

# # RUN curl -SLO "https://raw.githubusercontent.com/balena-io-library/base-images/8accad6af708fca7271c5c65f18a86782e19f877/scripts/assets/tests/test-stack@python.sh" \
# # && echo "Running test-stack@python" \
# # && chmod +x test-stack@python.sh \
# # && bash test-stack@python.sh \
# # && rm -rf test-stack@python.sh


