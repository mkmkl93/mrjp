from typing import List

import re
import sys
from utils import *

class Machine:
    def __init__(self, DEBUG):
        self.DEBUG = DEBUG
        self.code = []
        self.strings = []

    def debug(self, msg) -> None:
        if self.DEBUG:
            sys.stderr.write(msg)

    def to_mem(self, var: str):
        if var.isnumeric():
            return '${}'.format(int(var))

        m = re.match(r'.*_t(\d*)', var)
        return '-{}(%rbp)'.format(4 * int(m.group(1)))

    def translate(self, blocks: List[Block]) -> None:
        self.add_start()

        for block in blocks:
            self.code.append('{}:'.format(block.name))
            self.translate_block(block)

        self.code.append('')
        self.add_strings()

    def add_start(self):
        self.code.append('.text')
        self.code.append('    .global main')
        self.code.append('    .text')
        self.code.append('')

    def add_strings(self):
        code_tmp = self.code
        self.code = []

        self.code.append('.data')
        for label, val in self.strings:
            self.code.append('    {}: .string {}'.format(label, val))

        self.code.extend(code_tmp)

    def translate_block(self, block: Block):
        if isinstance(block, BigBlock):
            for small_block in block.blocks:
                self.translate_block(small_block)
        else:
            for quad in block.quads:
                self.add_quad(quad)

        self.code.append('')

    def add_epilog(self):
        self.code.append('    mov %rbp, %rsp')
        self.code.append('    pop %rbp')

    def add_quad(self, quad):
        if isinstance(quad, QFunBegin):
            self.code.append('    push %rbp')
            self.code.append('    mov %rsp, %rbp')
            self.code.append('    sub ${}, %rsp'.format(4 * (quad.val + 1)))
        elif isinstance(quad, QFunEnd):
            return
        elif isinstance(quad, QEq):
            if quad.val2[0] == '"':
                self.strings.append((quad.val1 + '__str', quad.val2))
                loc1 = self.to_mem(quad.val1)

                self.code.append('    movl ${}, {}'.format(quad.val1 + '__str', loc1))
                return
            else:
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
        elif isinstance(quad, QFunCall):
            for arg in quad.args[:6:-1]:
                arg_loc = self.to_mem(arg)
                self.code.append('    push {}'.format(arg_loc))

            for arg, reg in zip(quad.args[:6], registers):
                arg_loc = self.to_mem(arg)
                self.code.append('    movl {}, %{}'.format(arg_loc, reg))

            self.code.append('    push %rbp')
            self.code.append('    call {}'.format(quad.name))

            self.code.append('    add ${}, %rsp'.format(4 * max(len(quad.args) - 6, 0)))
        elif isinstance(quad, QUnOp):
            res_loc = self.to_mem(quad.res)
            val_loc = self.to_mem(quad.val)

            if quad.op == '-':
                op = 'neg'
            else:
                pass

            self.code.append('    movl {}, %eax'.format(val_loc))
            self.code.append('    {} %eax'.format(op))
            self.code.append('    movl %eax, {}'.format(res_loc))
        elif isinstance(quad, QBinOp):
            res_loc = self.to_mem(quad.res)
            val1_loc = self.to_mem(quad.val1)
            val2_loc = self.to_mem(quad.val2)
            result = '%eax'

            if quad.op == '*':
                op = 'imul'
            elif quad.op == '/':
                op = 'idiv'
            elif quad.op == '+' and quad.typ == 'int':
                op = 'add'
            elif quad.op == '+' and quad.typ == 'string':
                op = 'concat'
            elif quad.op == '-':
                op = 'sub'
            elif quad.op == '%':
                op = 'idiv'
                result = '%edx'

            self.code.append('    movl {}, %eax'.format(val1_loc))
            self.code.append('    movl {}, %edx'.format(val2_loc))

            if op != 'concat':
                self.code.append('    {} %edx, %eax'.format(op))
            else:
                self.code.append('    mov %eax, %edi')
                self.code.append('    mov %edx, %esi')
                self.code.append('    call concat')

            self.code.append('    movl {}, {}'.format(result, res_loc))
        elif isinstance(quad, QLabel):
            self.code.append(str(quad))
        elif isinstance(quad, QJump):
            self.code.append('    jmp {}'.format(quad.name))
        elif isinstance(quad, QEmpty):
            return
        else:
            self.debug("Not handled " + quad + '\n')








