#!/usr/bin/env python3

import os
import sys

import antlr4
from antlr.LatteLexer import LatteLexer
from antlr.LatteParser import LatteParser
from antlr4.error.ErrorListener import ErrorListener
from Compiler import Compiler

class MyErrorListener(ErrorListener):
    def __init__(self):
        super(MyErrorListener, self).__init__()

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        raise Exception("Oh no!")

    def reportAmbiguity(self, recognizer, dfa, startIndex, stopIndex, exact, ambigAlts, configs):
        raise Exception("Oh no!!")

    # def reportAttemptingFullContext(self, recognizer, dfa, startIndex, stopIndex, conflictingAlts, configs):
    #     print(startIndex, stopIndex, conflictingAlts);
    #     raise Exception("Oh no!!!")

    # def reportContextSensitivity(self, recognizer, dfa, startIndex, stopIndex, prediction, configs):
    #     print(startIndex, stopIndex, prediction)
    #     raise Exception("Oh no!!!!")


def main(argv):
    if len(argv) != 2:
        print ("Invalid number of arguments. Expected \"python3 Latte.py foo/bar/baz.lat\"")
        sys.exit(1)

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
    compiler = Compiler()

    compiler.enterProgram(prog_tree)


if __name__ == '__main__':
    main(sys.argv)