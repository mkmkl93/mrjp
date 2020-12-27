from typing import List

import re
import sys
from utils import *

class Machine:
    def __init__(self, DEBUG):
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

    def to_mem(self, var: str):
        if var.isnumeric():
            return '${}'.format(int(var))

        m = re.match(r'.*_t(\d*)', var)
        return '-{}(%rbp)'.format(4 * int(m.group(1)))

    def translate(self, blocks: List[Block]) -> None:
        self.add_start()

        for block in blocks:
            self.translate_block(block)

        self.code.append('')

    def add_start(self):
        self.code.append('    .global main')
        self.code.append('    .text')
        self.code.append('')

    def translate_block(self, block: Block):
        self.code.append('{}:'.format(block.name))

        for quad in block.quads:
            self.add_quad(quad)

        self.code.append('')

    def add_epilog(self):
        self.code.append('    mov %rbp, %rsp')
        self.code.append('    pop %rbp')

    # def add_variables(self, code):
    #     offset = 4
    #
    #     for line in code:
    #         m = re.match(r"(.*?) = .*", line)
    #
    #         if m and m.group(1) not in registers:
    #             self.blocks[-1].vars[m.group(1)] = offset
    #             offset += 4
    #
    def add_quad(self, quad):
        if isinstance(quad, QFunBegin):
            self.code.append('    push %rbp')
            self.code.append('    mov %rsp, %rbp')
            self.code.append('    sub ${}, %rsp'.format(4 * (quad.val + 1)))
        elif isinstance(quad, QFunEnd):
            return
        elif isinstance(quad, QEq):
            loc1 = self.to_mem(quad.val1)
            loc2 = self.to_mem(quad.val2)
            self.code.append('    movl {}, %eax'.format(loc2))
            self.code.append('    movl %eax, {}'.format(loc1))
        elif isinstance(quad, QReturn):
            if quad.val is not None:
                loc = self.to_mem(quad.val)

                self.code.append('    movl {}, %eax'.format(loc))

            self.add_epilog()
            self.code.append('    ret')

        # elif line.startswith(('mul', 'div')):
        #     m = re.match(r'(.*) (.*) (.*)', line)
        #     op = m.group(1)
        #     dest = m.group(2)
        #     source = m.group(2)
        #
        #     self.add_mul(op, dest, source)
        # elif line.startswith('call'):
        #     self.code.append('    ' + line)
        # elif line.startswith('push'):
        #     m = re.match(r'push (.*)', line)
        #
        #     self.code.append('    push %' + m.group(1))
        # elif line.startswith('neg'):
        #     m = re.match(r'neg (.*)', line)
        #
        #     self.add_neg(m.group(1))
        elif isinstance(quad, QEmpty):
            return
        else:
            self.debug("Not handled " + quad + '\n')

    # def add_mov(self, dest, source):
    #     if dest not in registers and source not in registers:
    #         source = self.to_reg_or_con(source)
    #     else:
    #         source = self.to_any(source)
    #
    #     dest = self.to_any(dest)
    #
    #     if source.startswith('$') and dest[0] != '%':
    #         op = 'movl'
    #     else:
    #         op = 'mov'
    #
    #     self.code.append('    {} {}, {}'.format(op, source, dest))
    #
    # def add_ret(self, source):
    #     self.code.append('    ret')
    #
    # def add_neg(self, source):
    #     source = self.to_any(source)
    #
    #     if source.startswith('%'):
    #         op = 'neg'
    #     else:
    #         op = 'negl'
    #
    #     self.code.append('    {} {}'.format(op, source))
    #
    # def add_mul(self, op, mul1, mul2):
    #     mul1 = self.to_any(mul1)
    #     mul2 = self.to_reg_or_con(mul2)
    #
    #     self.code.append('    i{} {}, {}'.format(op, mul1, mul2))







