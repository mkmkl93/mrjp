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
            self.translate_block(code[start : end])

    def add_start(self):
        self.code.append('    .global main')
        self.code.append('    .text')
        self.code.append('')

    def translate_block(self, code):
        if code[0][-2] == ':':
            self.code.append(code[0][:-1])
        else:
            self.code.append(code[0])

        self.code.append('    push rbp')
        self.code.append('    mv rbp rsp')

        self.blocks.append(Block())
        self.add_variables(code)

        for line in code[1:]:
            self.add_line(line)

        self.code.append('')

    def add_variables(self, code):
        offset = 4

        for line in code:
            m = re.match(r"(.*?) = .*", line)

            if m and m.group(1) not in registers:
                self.blocks[-1].vars[m.group(1)] = offset
                offset += 4

    def add_line(self, line):
        if re.match(r'(.*) = (.*)', line):
            m = re.match(r'(.*) = (.*)', line)
            dest = m.group(1)
            source = m.group(2)

            self.add_mov(dest, source)
        elif line.startswith(('push', 'call', 'ret')):
            self.code.append('    ' + line)
        elif line == '':
            return
        else:
            self.debug("Not handled " + line + '\n')

    def add_mov(self, dest, source):
        if dest not in registers:
            dest = '[rbp - ' + str(self.blocks[-1].vars[dest]) + ']'
        if source not in registers and not source.isnumeric():
            source = '[rbp - ' + str(self.blocks[-1].vars[source]) + ']'

        if dest not in registers and source not in registers:
            self.code.append('    mv rax, ' + source)
            source = 'rax'

        self.code.append('    mov ' + dest + ', ' + source)

    def add_ret(self, source):
        if source not in registers and not source.isnumeric():
            source = '[rbp - ' + str(self.blocks[-1].vars[source]) + ']'








