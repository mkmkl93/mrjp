from typing import List

import re
import sys
from utils import *

class Optimiser:
    def __init__(self, DEBUG):
        self.DEBUG = DEBUG
        self.code = []
        self.strings = []
        self.block_counter = 1

    def debug(self, msg) -> None:
        if self.DEBUG:
            sys.stderr.write(msg)

    def get_quads(self, block, res) -> List[Quad]:
        if isinstance(block, BigBlock):
            for b in block.blocks:
                res = self.get_quads(b, res)
        else:
            for quad in block.quads:
                res.append(quad)
        return res

    def divide_into_blocks(self, quads: List[Quad], res) -> List[Block]:
        block = SmallBlock(str(self.block_counter))
        block.add_quad(quads[0])
        self.block_counter += 1

        for i, quad in enumerate(quads[1:]):
            if isinstance(quad, (QLabel, QFunBegin)):
                res.append(block)
                return self.divide_into_blocks(quads[i:], res)
            else:
                block.add_quad(quad)

        res.append(block)
        return res

    def add_start(self) -> QEmpty:
        quad = QEmpty()
        quad.code.append('.text')
        quad.code.append('    .global main')
        quad.code.append('    .text')
        quad.code.append('')

        return quad

    def add_strings(self):
        quad = QEmpty()
        if not self.strings:
            return quad

        quad.code.append('.data')
        for label, val in self.strings:
            if val == '':
                val = '""'
            quad.code.append('    {}: .string {}'.format(label, val))

        return quad

    def optimise(self, blocks: List[Block]) -> List[Block]:
        quads = []
        for block in blocks:
            quads = self.get_quads(block, quads)

        blocks = self.divide_into_blocks(quads, [])
        for block in blocks:
            self.calculate_alive(block)

        for block in blocks:
            self.calculate_code(block)

        prolog_block = SmallBlock(str(0))
        prolog_block.quads.append(self.add_strings())
        prolog_block.quads.append(self.add_start())
        blocks.insert(0, prolog_block)

        return blocks

    def calculate_alive(self, block: SmallBlock):
        alive_set = AliveSet()
        block.quads[-1].alive = alive_set
        ln = len(block.quads)
        for i, quad in enumerate(block.quads[-1::-1]):
            block.quads[ln - i - 1].alive = alive_set.copy()

            if isinstance(quad, QJump):
                pass
            elif isinstance(quad, QCmp):
                pass
            elif isinstance(quad, QReturn):
                alive_set.add(quad.val)
            elif isinstance(quad, QEq):
                alive_set.discard(quad.val1)
                alive_set.add(quad.val2)
            elif isinstance(quad, QFunBegin):
                pass
            elif isinstance(quad, QFunEnd):
                pass
            elif isinstance(quad, QFunCall):
                pass
            elif isinstance(quad, QBinOp):
                pass
            elif isinstance(quad, QUnOp):
                pass

        return block

    def calculate_code(self, block: SmallBlock) -> SmallBlock:
        omit = False
        for i, quad in enumerate(block.quads):
            if omit:
                omit = False
                continue

            if isinstance(quad, QEmpty):
                pass
            if isinstance(quad, QJump):
                pass
            elif isinstance(quad, QCmp):
                pass
            elif isinstance(quad, QReturn):
                if quad.val is not None:
                    block, quad, reg = self.get_register(block, quad, quad.val)
                    quad.code.append('    mov %{}, %eax'.format(reg))
                quad_empty = self.get_epilog()
                quad_empty.code.append('    ret')
                block.quads.insert(i + 1, quad_empty)

                block.quads[i] = quad
            elif isinstance(quad, QEq):
                if quad.val2.isnumeric():
                    block, quad, reg = self.get_free_register(block, quad)
                    quad.code.append('    movl ${}, %{}'.format(int(quad.val2), reg))
                    block.table[reg].add(quad.val1)
                    block.table[quad.val1].add(reg)
                else:
                    block, quad, reg = self.get_register(block, quad, quad.val2)
                    block.table[quad.val1].add(reg)
                    block.table[reg].add(quad.val1)

                    if quad.val2 not in quad.alive:
                        block.table[quad.val2] = set()
                        block.table[quad.val2].discard(reg)
                        block.table[reg].discard(quad.val2)

            elif isinstance(quad, QFunBegin):
                quad_empty = QEmpty()
                quad_empty.code.append('{}:'.format(quad.name))
                quad_empty = self.get_prolog(quad_empty)
                block.quads.insert(i, quad_empty)
                omit = True
                local_vars_size = quad.val
                # we want to have (4 * local_vars_size + <number of pushed registers> * 8) % 16 == 0
                # to make space for local variables and callee saved regs and allign %rsp to 16
                while (4 * local_vars_size + 6 * 4) % 16 != 0:
                    local_vars_size += 1
                quad.code.append('    sub ${}, %rsp'.format(4 * local_vars_size))
            elif isinstance(quad, QFunEnd):
                pass
            elif isinstance(quad, QFunCall):
                pass
            elif isinstance(quad, QBinOp):
                pass
            elif isinstance(quad, QUnOp):
                pass
        return block

    def get_register(self, block: SmallBlock, quad: Quad, var):
        for place in block.table[var]:
            if place in free_registers:
                return block, quad, place

        return self.get_free_register(block, quad)

    def get_free_register(self, block: SmallBlock, quad: Quad):
        for free_reg in free_registers:
            if block.table[free_reg] == set():
                return block, quad, free_reg

        #TODO freee reg here
        return None

    def clear_block(self, block, quad):
        for reg in free_registers:
            if block.table[reg] is not None:
                for var in block.table[reg]:
                    m = re.match(r'.*_t(\d*)', var)
                    var_loc = '-{}(%rbp)'.format(4 * int(m.group(1)))
                    if var_loc not in block.table[var]:
                        quad.code.append('    movl {}, {}'.format(reg, var_loc))
                block.table[reg] = set()
        return block, quad

    def get_epilog(self):
        quad = QEmpty()

        for reg in reversed(callee_saved):
            quad.code.append('    pop %{}'.format(reg))
        quad.code.append('    mov %rbp, %rsp')
        quad.code.append('    pop %rbp')

        return quad

    def get_prolog(self, quad):
        quad.code.append('    push %rbp')
        quad.code.append('    mov %rsp, %rbp')

        for reg in callee_saved:
            quad.code.append('    push %{}'.format(reg))

        return quad
