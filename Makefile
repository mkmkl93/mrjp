#!/usr/bin/bash
all: latte

create_env:
	python3 -m venv my_env;
	./my_env/bin/pip3 install absl-py
	./my_env/bin/pip3 install antlr4-python3-runtime

latte: create_env
	java -jar lib/antlr-4.9-complete.jar -Dlanguage=Python3 -o antlr Latte.g4

zip:
	tar -czf mk394332.tar.gz Compiler.py Latte.g4 Latte.py latc_ARCH Makefile test.py lib/ lattests/

ifeq (test,$(firstword $(MAKECMDGOALS)))
  RUN_ARGS := $(wordlist 2,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS))
  $(eval $(RUN_ARGS):;@:)
endif
test:
	python3 test.py $(RUN_ARGS)
