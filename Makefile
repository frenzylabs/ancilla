.PHONY: test

ROOT_DIR 	   := $(abspath $(lastword $(MAKEFILE_LIST)))
PROJECT_DIR	 := $(notdir $(patsubst %/,%,$(dir $(ROOT_DIR))))
PROJECT 		 := $(lastword $(PROJECT_DIR))
VERSION_FILE 	= VERSION
VERSION			 	= `cat $(VERSION_FILE)`

all: run

clean:
	@rm -rf dist \
	&& rm -rf __pycache__ \
	&& rm -rf ancilla-ui/dist \
	&& rm -rf macOS \
	&& rm -rf ancilla-ui/.cache \
	&& rm -rf ~/.ancilla

run:
	@RUN_ENV=DEV python -m ancilla

bundle_js:
	@cd ancilla-ui \
	&& yarn install --check-files \
	&& ./node_modules/.bin/parcel build src/index.html --public-url '/static' --out-dir ../ancilla/ui/dist
	# && npm run build


package_python:
	@RUN_ENV=PROD python setup.py macos -s && \
	mkdir dist && \
	mv macOS dist/

package: bundle_js package_python
# package: clean bundle_js package_python
