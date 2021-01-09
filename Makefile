#!/usr/bin/bash
all: latte

create_env:
	python3 -m venv my_env;
	./my_env/bin/pip3 install absl-py
	./my_env/bin/pip3 install antlr4-python3-runtime

latte: create_env
	java -jar lib/antlr-4.9-complete.jar -Dlanguage=Python3 -o antlr Latte.g4

zip:
	tar -czf mk394332.tar.gz FrontEnd.py Latte.g4 Latte.py latc_x86_64 Makefile test.py utils.py Simplifier.py Code4.py RegOptimiser.py lib/ lattests/ Vars.py Quads.py Blocks.py

ifeq (test,$(firstword $(MAKECMDGOALS)))
  RUN_ARGS := $(wordlist 2,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS))
  $(eval $(RUN_ARGS):;@:)
endif

lib:
	clang -S lib/runtime.c -o lib/runtime.s

test:
	python3 test.py $(RUN_ARGS)
