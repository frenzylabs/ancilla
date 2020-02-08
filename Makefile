.PHONY: test

ROOT_DIR 	   := $(abspath $(lastword $(MAKEFILE_LIST)))
PROJECT_DIR	 := $(notdir $(patsubst %/,%,$(dir $(ROOT_DIR))))
PROJECT 		 := $(lastword $(PROJECT_DIR))
VERSION_FILE 	= VERSION
VERSION			 	= `cat $(VERSION_FILE)`


package_ui: clean-ui bundle_js

update-ui:
	git submodule update --remote -- ancilla-ui

build-ui: update-ui package_ui


build-web:
	$(eval LK_COMMIT=$(shell git --git-dir=./.git rev-parse --short HEAD))
	ANCILLA_COMMIT=${LK_COMMIT} docker-compose build ancilla

push_staging:
	$(eval LK_COMMIT=$(shell git --git-dir=./.git rev-parse --short HEAD))
	docker tag localhost/ancilla:${LK_COMMIT} layerkeep/ancilla:staging-${LK_COMMIT}
	docker tag localhost/ancilla:${LK_COMMIT} layerkeep/ancilla:staging-latest
	docker push layerkeep/ancilla:staging-${LK_COMMIT}
	docker push layerkeep/ancilla:staging-latest
	

all: run



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

bundle_js:
	@cd ancilla-ui \
	&& yarn install --check-files \
	&& ./node_modules/.bin/parcel build src/index.html --public-url '/static' --out-dir ../ancilla/ancilla/ui/dist
	# && npm run build


package_python:
	@RUN_ENV=PROD python setup.py macos -s && \
	mkdir dist && \
	mv macOS dist/

package: bundle_js package_python
# package: clean bundle_js package_python
