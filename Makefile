.PHONY: test

ROOT_DIR 	   := $(abspath $(lastword $(MAKEFILE_LIST)))
PROJECT_DIR	 := $(notdir $(patsubst %/,%,$(dir $(ROOT_DIR))))
PROJECT 		 := $(lastword $(PROJECT_DIR))
VERSION_FILE 	= VERSION
VERSION			 	= `cat $(VERSION_FILE)`

all: run

clean:
	@rm -rf dist

run: 
	@python -m ancilla

package: clean
	@python setup.py macos -s && \
	mkdir dist && \
	mv macOS dist/
