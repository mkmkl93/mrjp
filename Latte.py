#!/usr/bin/env python3

import sys
import antlr4
from absl import flags
from Compiler import Compiler
from antlr.LatteLexer import LatteLexer
from antlr.LatteParser import LatteParser
from antlr4.error.ErrorListener import ErrorListener

flags.DEFINE_boolean('debug', False, 'Turn on debug comments')
FLAGS = flags.FLAGS


class MyErrorListener(ErrorListener):
    def __init__(self):
        super(MyErrorListener, self).__init__()

    def syntaxError(self, recognizer, offending_symbol, line, column, msg, e):
        sys.stderr.write("ERROR\n")
        sys.stderr.write("\033[91m" + "Syntax error at " + str(line) + ":" + str(column) + "\033[0m\n")
        sys.stderr.write(offending_symbol.text + '\n')
        sys.stderr.write(msg + '\n')
        sys.exit(1)


def main(argv):
    input_file = argv[1]

    input_file_stream = antlr4.FileStream(input_file)
    my_error_listener = MyErrorListener()

    lexer = LatteLexer(input_file_stream)
    lexer.removeErrorListeners()
    lexer.addErrorListener(my_error_listener)

    stream = antlr4.CommonTokenStream(lexer)

    parser = LatteParser(stream)
    parser.removeErrorListeners()
    parser.addErrorListener(my_error_listener)
    prog_tree = parser.program()
    compiler = Compiler(input_file, FLAGS['debug'])

    compiler.enter_program(prog_tree)

    sys.stderr.write('OK\n')
    sys.exit(0)

if __name__ == '__main__':
    main(sys.argv)
