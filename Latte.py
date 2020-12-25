#!/usr/bin/env python3

import sys
import antlr4
import os
import subprocess
from absl import app, flags
from FrontEnd import FrontEnd
from Code4 import Code4
from Machine import Machine
from antlr.LatteLexer import LatteLexer
from antlr.LatteParser import LatteParser
from antlr4.error.ErrorListener import ErrorListener

FLAGS = flags.FLAGS
flags.DEFINE_boolean('debug', False, 'Turn on debug comments')


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
    compiler = FrontEnd(input_file, FLAGS['debug'])
    code4 = Code4(FLAGS['debug'])
    machine = Machine(FLAGS['debug'])

    compiler.enter_program(prog_tree)

    code4.enter_program(prog_tree)
    for i in code4.code:
        print(i)
    print()

    machine.translate(code4.code)
    for i in machine.code:
        print(i)

    output_file_base = os.path.splitext(input_file)[0]
    output_file = output_file_base + '.s'
    with open(output_file, 'w') as output:
        for line in machine.code:
            output.write(line + '\n')

    # #'clang -g lib/runtime.s lattests/good/core052.s -o lattests/good/core052 && ./lattests/good/core052'
    process = subprocess.run(['clang', '-g', 'lib/runtime.c', output_file,
                             '-o' + output_file_base], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False)

    # process = subprocess.run(['gcc', '-g', '-static', '-nostdlib', '-no-pie', '-emain', 'lib/runtime.s', output_file,
    #                           '-o' + output_file_base], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False)

    print(process.stdout.decode("utf-8"))
    print(process.stderr.decode("utf-8"))

    sys.stderr.write('OK\n')
    sys.exit(0)


if __name__ == '__main__':
    app.run(main)
