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
	&& rm -rf ui/dist \
	&& rm -rf ui/.cache

run: bundle_js
	@python -m ancilla

bundle_js:
	@cd ui \
	&& npm run build


package_python:
	@python setup.py macos -s && \
	mkdir dist && \
	mv macOS dist/

package: clean bundle_js package_python
