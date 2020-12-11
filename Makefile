latte:
	java -jar lib/antlr-4.9-complete.jar -Dlanguage=Python3 -o antlr Latte.g4


ifeq (test,$(firstword $(MAKECMDGOALS)))
  RUN_ARGS := $(wordlist 2,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS))
  $(eval $(RUN_ARGS):;@:)
endif
test:
	python3 test.py $(RUN_ARGS)