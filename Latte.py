#!/usr/bin/env python3

import sys
import antlr4
import os
import subprocess
from absl import app, flags
from Simplifier import Simplifier
from FrontEnd import FrontEnd
from Code4 import Code4
from CSE import CSE
from CalcAliveSet import CalcAliveSet
from RegOptimiser import RegOptimiser
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


def debug(msg) -> None:
    if FLAGS['debug'].value:
        print(msg)


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

    simplifier = Simplifier(FLAGS['debug'].value)
    front_end = FrontEnd(input_file, FLAGS['debug'].value)
    code4 = Code4(FLAGS['debug'].value)
    alivesets = CalcAliveSet(FLAGS['debug'].value)
    cse = CSE(FLAGS['debug'].value)
    optimiser = RegOptimiser(FLAGS['debug'].value)

    front_end.enter_program(prog_tree)
    prog_tree = simplifier.simplify(prog_tree)

    debug('Kod czwórkowy:')
    blocks = code4.enter_program(prog_tree)
    for block in blocks:
        debug(block)
    debug('')

    debug("Podział na bloki i wylicznaie zbiorów żywych")
    blocks_alive = alivesets.calc(blocks)
    for block in blocks_alive:
        debug(block)
    debug('')

    debug("Optymalizacje CSE")
    blocks_optimised = cse.optimise(blocks_alive)
    for block in blocks_optimised:
        debug(block)
    debug('')

    debug("Zamiana na kod maszynowy")
    blocks_calculated = optimiser.optimise(blocks_optimised)
    for block in blocks_calculated:
        debug(block)
    debug('')

    output_file_base = os.path.splitext(input_file)[0]
    output_file = output_file_base + '.s'
    with open(output_file, 'w') as output:
        for block in blocks_calculated:
            for quad in block.quads:
                if quad.code:
                    for line in quad.code:
                        debug(line)
                        output.write(line + '\n')
    debug('')

    process = subprocess.run(['clang', '-g', 'lib/runtime.c', output_file, '-o' + output_file_base],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False, encoding='utf-8')

    debug(process.stdout)
    debug(process.stderr)

    if process.returncode != 0:
        sys.exit(process.returncode)
    sys.stderr.write('OK\n')
    sys.exit(0)


if __name__ == '__main__':
    app.run(main)
