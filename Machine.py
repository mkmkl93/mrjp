from typing import List

import re
import sys
from utils import Var, get_default_value, get_from_item, registers


class Line:
    def __init__(self):
        self.alive = {}


class Block:
    def __init__(self):
        self.vars = {}
        self.lines: List[Line] = []
        self.following: List[Block] = []
        self.previous: List[Block] = []

    def append(self, line):
        self.lines.append(line)

class Machine:
    def __init__(self, DEBUG):
        self.blocks: List[Block] = []
        self.DEBUG = DEBUG.value
        self.code = []

    def debug(self, msg) -> None:
        if self.DEBUG:
            sys.stderr.write(msg)

    def to_reg_or_con(self, var: str) -> str:
        if var in registers:
            return '%' + var
        elif var.isnumeric():
            return '$' + var
        else:
            var = self.to_any(var)
            self.code.append('    mov {}, %eax'.format(var))
            return '%eax'

    def to_any(self, var: str) -> str:
        if var not in registers and not var.isnumeric():
            return '-' + str(self.blocks[-1].vars[var]) + '(%rbp)'
        elif var in registers:
            return '%' + var
        elif var.isnumeric():
            return '$' + var
        else:
            self.debug("Not handled to_any " + var + '\n')

    def translate(self, code) -> None:
        self.add_start()

        stops = []
        for i, line in enumerate(code):
            if line.endswith('::'):
                stops.append(i)

        stops.append(len(code))
        for i in range(len(stops) - 1):
            start = stops[i]
            end = stops[i + 1]
            self.translate_block(code[start: end])

        self.code.append('')

    def add_start(self):
        self.code.append('    .global main')
        self.code.append('    .text')
        self.code.append('')

    def translate_block(self, code):
        if code[0][-2] == ':':
            self.code.append(code[0][:-1])
        else:
            self.code.append(code[0])

        self.code.append('    push %rbp')
        self.code.append('    mov %rsp, %rbp')

        self.blocks.append(Block())
        self.add_variables(code)

        for line in code[1:]:
            self.add_line(line)

        self.code.append('')

    def add_epilog(self):
        self.code.append('    mov %rbp, %rsp')
        self.code.append('    pop %rbp')
        self.code.append('    ret')

    def add_variables(self, code):
        offset = 4

        for line in code:
            m = re.match(r"(.*?) = .*", line)

            if m and m.group(1) not in registers:
                self.blocks[-1].vars[m.group(1)] = offset
                offset += 4

    def add_line(self, line):
        if line.endswith(':'):
            self.code.append('')
            self.code.append(line)
        elif re.match(r'(.*) = (.*)', line):
            m = re.match(r'(.*) = (.*)', line)
            dest = m.group(1)
            source = m.group(2)

            self.add_mov(dest, source)
        elif line.startswith(('mul', 'div')):
            m = re.match(r'(.*) (.*) (.*)', line)
            op = m.group(1)
            dest = m.group(2)
            source = m.group(2)

            self.add_mul(op, dest, source)
        elif line.startswith('call'):
            self.code.append('    ' + line)
        elif line.startswith('ret'):
            self.add_epilog()
        elif line.startswith('push'):
            m = re.match(r'push (.*)', line)

            self.code.append('    push %' + m.group(1))
        elif line.startswith('neg'):
            m = re.match(r'neg (.*)', line)

            self.add_neg(m.group(1))
        elif line == '':
            return
        else:
            self.debug("Not handled " + line + '\n')

    def add_mov(self, dest, source):
        if dest not in registers and source not in registers:
            source = self.to_reg_or_con(source)
        else:
            source = self.to_any(source)

        dest = self.to_any(dest)

        if source.startswith('$') and dest[0] != '%':
            op = 'movl'
        else:
            op = 'mov'

        self.code.append('    {} {}, {}'.format(op, source, dest))

    def add_ret(self, source):
        self.code.append('    ret')

    def add_neg(self, source):
        source = self.to_any(source)

        if source.startswith('%'):
            op = 'neg'
        else:
            op = 'negl'

        self.code.append('    {} {}'.format(op, source))

    def add_mul(self, op, mul1, mul2):
        mul1 = self.to_any(mul1)
        mul2 = self.to_reg_or_con(mul2)

        self.code.append('    i{} {}, {}'.format(op, mul1, mul2))







