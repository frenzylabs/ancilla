.PHONY: test

ROOT_DIR 	   := $(abspath $(lastword $(MAKEFILE_LIST)))
PROJECT_DIR	 := $(notdir $(patsubst %/,%,$(dir $(ROOT_DIR))))
PROJECT 		 := $(lastword $(PROJECT_DIR))
VERSION_FILE 	= VERSION
VERSION			 	= `cat $(VERSION_FILE)`


package-ui: clean-ui bundle-js

update-ui:
	git submodule update --remote -- ancilla-ui

build-ui: update-ui package-ui


build-rpi:
	$(eval LK_COMMIT=$(shell git --git-dir=./.git rev-parse --short HEAD))
	ANCILLA_COMMIT=${LK_COMMIT} docker-compose build ancilla

push-rpi-production:
	$(eval LK_COMMIT=$(shell git --git-dir=./.git rev-parse --short HEAD))
	docker tag localhost/ancilla:${LK_COMMIT} layerkeep/ancilla:${LK_COMMIT}
	docker tag localhost/ancilla:${LK_COMMIT} layerkeep/ancilla:latest
	docker push layerkeep/ancilla:${LK_COMMIT}
	docker push layerkeep/ancilla:latest

push-rpi-staging:
	$(eval LK_COMMIT=$(shell git --git-dir=./.git rev-parse --short HEAD))
	docker tag localhost/ancilla:${LK_COMMIT} layerkeep/ancilla:staging-${LK_COMMIT}
	docker tag localhost/ancilla:${LK_COMMIT} layerkeep/ancilla:staging-latest
	docker push layerkeep/ancilla:staging-${LK_COMMIT}
	docker push layerkeep/ancilla:staging-latest

build-rpi3:
	$(eval LK_COMMIT=$(shell git --git-dir=./.git rev-parse --short HEAD))
	ANCILLA_COMMIT=${LK_COMMIT} docker-compose build ancilla-rpi3

push-rpi3-staging:
	$(eval LK_COMMIT=$(shell git --git-dir=./.git rev-parse --short HEAD))
	docker tag localhost/ancilla:rpi3-${LK_COMMIT} layerkeep/ancilla:staging-rpi3-${LK_COMMIT}
	docker tag localhost/ancilla:rpi3-${LK_COMMIT} layerkeep/ancilla:staging-rpi3-latest
	docker push layerkeep/ancilla:staging-rpi3-${LK_COMMIT}
	docker push layerkeep/ancilla:staging-rpi3-latest

build-rpi4:
	$(eval LK_COMMIT=$(shell git --git-dir=./.git rev-parse --short HEAD))
	ANCILLA_COMMIT=${LK_COMMIT} docker-compose build ancilla-rpi4	

push_rpi4:
	$(eval LK_COMMIT=$(shell git --git-dir=./.git rev-parse --short HEAD))
	docker tag localhost/ancilla:rpi4-${LK_COMMIT} layerkeep/ancilla:staging-rpi4-${LK_COMMIT}
	docker tag localhost/ancilla:rpi4-${LK_COMMIT} layerkeep/ancilla:staging-rpi4-latest
	docker push layerkeep/ancilla:staging-rpi4-${LK_COMMIT}
	docker push layerkeep/ancilla:staging-rpi4-latest
	

all: run


clean-docker:
	docker rm $(shell docker ps -a -q)
	docker rmi $(shell docker images | grep '<none>' | awk '{print $$3}')

clean-ui:
	@rm -rf ancilla/ui

clean-all:
	@rm -rf *.ipc \
	&& rm -rf dist \
	&& rm -rf __pycache__ \
	&& rm -rf ancilla-ui/dist \
	&& rm -rf macOS \
	&& rm -rf ancilla-ui/.cache \
	&& rm -rf ~/.ancilla

run:
	@RUN_ENV=DEV cd ancilla && python -m ancilla

bundle-js:
	@cd ancilla-ui \
	&& yarn install --check-files \
	&& ./node_modules/.bin/parcel build src/index.html --public-url '/static' --out-dir ../ancilla/ancilla/ui/dist
	# && npm run build


package_python:
	@RUN_ENV=PROD python setup.py macos -s && \
	mkdir dist && \
	mv macOS dist/

package: bundle-js package_python
# package: clean bundle_js package_python
