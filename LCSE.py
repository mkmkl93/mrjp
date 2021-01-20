from typing import List

import sys
from Alive import Alive
from utils import *

class LCSE:
    def __init__(self, debug):
        self.dbug = debug
        self.appear_counter = {}
        self.known_value = {}

    def debug(self, msg) -> None:
        if self.dbug:
            sys.stderr.write(msg)

    def error(self, msg) -> None:
        sys.stderr.write("ERROR\n")
        sys.stderr.write("\033[91mRuntime error\033[0m\n")
        sys.stderr.write(msg + '\n')
        sys.exit(1)

    def optimise(self, blocks: List[SmallBlock]) -> List[SmallBlock]:
        blocks = self.compress_values(blocks)

        return blocks

    def compress_values(self, blocks: List[SmallBlock]) -> List[SmallBlock]:
        for block in blocks:
            self.count_left_appearances(block)

        placeholder = blocks
        blocks = []
        for block in placeholder:
            blocks.append(self.compress_block(block))

        blocks = self.clear_blocks(blocks)

        return blocks

    def clear_blocks(self, blocks: List[SmallBlock]) -> List[SmallBlock]:
        alive = Alive(self.dbug)
        blocks = alive.optimise(blocks)

        placeholder = blocks
        blocks = []
        for block in placeholder:
            blocks.append(self.clear_block(block))

        return blocks

    def clear_block(self, block: SmallBlock) -> SmallBlock:
        placeholder = block.quads
        block.quads = []
        for quad in placeholder:
            if isinstance(quad, (QJump, QFunBegin, QFunCall, QCmp, QReturn, QFunEnd, QLabel)):
                block.quads.append(quad)
            elif isinstance(quad, QEq):
                if quad.var1 in quad.alive:
                    block.quads.append(quad)
            elif isinstance(quad, (QBinOp, QUnOp)):
                if quad.res in quad.alive:
                    block.quads.append(quad)
            else:
                self.debug("Shouldn't be here clear_block")
                sys.exit(1)

        return block

    def count_left_appearances(self, block: SmallBlock) -> None:
        for quad in block.quads:
            if isinstance(quad, (QJump, QFunBegin, QFunCall, QCmp, QReturn, QFunEnd, QLabel)):
                pass
            elif isinstance(quad, QEq):
                self.add_appearance(quad.var1)
            elif isinstance(quad, QFunCall):
                self.add_appearance(quad.var)
            elif isinstance(quad, QBinOp):
                self.add_appearance(quad.res)
            elif isinstance(quad, QUnOp):
                self.add_appearance(quad.res)
            else:
                self.debug("Shouldn't be here count_left_appearances")
                sys.exit(1)

    def add_appearance(self, var):
        if var not in self.appear_counter:
            self.appear_counter[var] = 0
        self.appear_counter[var] += 1

    def is_forbidden(self, var: str) -> bool:
        return var in self.appear_counter and self.appear_counter[var] > 1

    def is_to_compress(self, var: str) -> bool:
        if is_const(var):
            self.known_value[var] = var

        return var in self.known_value and not self.is_forbidden(var)

    def compress_block(self, block: SmallBlock) -> SmallBlock:
        placeholder = block.quads
        block.quads = []
        for quad in placeholder:
            if isinstance(quad, (QJump, QFunBegin, QLabel)):
                pass
            elif isinstance(quad, QReturn):
                if quad.var is not None and quad.var.isnumeric():
                    quad = QReturn(self.known_value[quad.var])
            elif isinstance(quad, QEq):
                if self.is_to_compress(quad.var2):

                    quad = QEq(quad.var1, self.known_value[quad.var2])

                    self.known_value[quad.var1] = quad.var2
            elif isinstance(quad, QFunCall):
                if quad.name in self.known_value:
                    quad = QEq(quad.var, self.known_value[quad.name])
            elif isinstance(quad, QBinOp):
                if self.is_to_compress(quad.var1) and self.is_to_compress(quad.var2):
                    if quad.op == '+' and quad.typ == 'string':
                        res_value = str(self.known_value[quad.var1][1:-1]) + str(self.known_value[quad.var2][1:-1])
                    elif quad.op == '+' and quad.typ == 'int':
                        res_value = int(self.known_value[quad.var1]) + int(self.known_value[quad.var2])
                    elif quad.op == '-':
                        res_value = int(self.known_value[quad.var1]) - int(self.known_value[quad.var2])
                    elif quad.op == '*':
                        res_value = int(self.known_value[quad.var1]) * int(self.known_value[quad.var2])
                    elif quad.op == '/':
                        res_value = calculate_div(int(self.known_value[quad.var1]), int(self.known_value[quad.var2]))
                        if res_value is None:
                            self.error("Divider equals to 0")
                    elif quad.op == '%':
                        res_value = calculate_mod(int(self.known_value[quad.var1]), int(self.known_value[quad.var2]))
                        if res_value is None:
                            self.error("Remainder equals to 0")
                    else:
                        self.debug("Shouldn't be here compress_block QBinOp")
                        sys.exit(1)

                    res_value = str(res_value)
                    if quad.typ == 'string':
                        res_value = '"' + res_value + '"'

                    self.known_value[quad.res] = res_value
                    quad = QEq(quad.res, res_value)

            elif isinstance(quad, QUnOp):
                if self.is_to_compress(quad.var):
                    if quad.op == '-':
                        res_value = - int(self.known_value[quad.var])
                    elif quad.op == '!':
                        res_value = 1 - int(self.known_value[quad.var])
                    else:
                        self.debug("Shouldn't be here compress_block QUnOp")
                        sys.exit(1)
                    res_value = str(res_value)

                    self.known_value[quad.res] = res_value
                    quad = QEq(quad.res, res_value)

            block.quads.append(quad)

        return block


def calculate_mod(a: int, b: int) -> int:
    if b == 0:
        return None

    if a < 0:
        if b < 0:
            return a % b
        else:
            return 0 if a % b == 0 else a % b - b
    else:
        if b < 0:
            return 0 if a % b == 0 else a % b - b
        else:
            return a % b

def calculate_div(a: int, b: int) -> int :
    if b == 0:
        return None

    if a < 0:
        if b < 0:
            return a // b
        else:
            return a // b if a % b == 0 else a // b + 1
    else:
        if b < 0:
            return a // b if a % b == 0 else a // b + 1
        else:
            return a // b
