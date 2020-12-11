latte:
	java -jar lib/antlr-4.9-complete.jar -Dlanguage=Python3 -o antlr Latte.g4

test:
	python3 test.py