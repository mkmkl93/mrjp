from typing import List

import sys
from Alive import Alive
from utils import *

class LCSE:
    def __init__(self, debug):
        self.dbug = debug
        self.known_value = {}
        self.repeat = True

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
        # while self.repeat:
        #     self.repeat = False
        #     blocks = self.lcse(blocks)
        #     blocks = self.propagate_in_blocks(blocks)
            # self.repeat = False

        return blocks

    def compress_values(self, blocks: List[SmallBlock]) -> List[SmallBlock]:
        placeholder = blocks
        blocks = []
        for block in placeholder:
            blocks.append(self.compress_block(block))

        blocks = self.clear_blocks(blocks)

        return blocks

    def clear_blocks(self, blocks: List[SmallBlock]) -> List[SmallBlock]:
        def clear_block(block: SmallBlock) -> SmallBlock:
            placeholder = block.quads
            block.quads = []
            for quad in placeholder:
                if isinstance(quad, (QJump, QFunBegin, QFunCall, QCmp, QReturn, QFunEnd, QLabel)):
                    block.quads.append(quad)
                elif isinstance(quad, QEq):
                    if quad.res in quad.alive:
                        block.quads.append(quad)
                    else:
                        self.repeat = True
                elif isinstance(quad, (QBinOp, QUnOp)):
                    if quad.res in quad.alive:
                        block.quads.append(quad)
                    else:
                        self.repeat = True
                else:
                    self.debug("Shouldn't be here clear_block")
                    sys.exit(1)

            return block
        alive = Alive(self.dbug)
        blocks = alive.optimise(blocks)

        for i, block in enumerate(blocks):
            blocks[i] = clear_block(block)

        return blocks

    def compress_block(self, block: SmallBlock) -> SmallBlock:
        def replace_in_block(start: int, replace_from: str, replace_to: str):
            for i in range(start, len(block.quads)):
                quad = block.quads[i]
                if isinstance(quad, (QJump, QFunBegin, QLabel)):
                    pass
                elif isinstance(quad, QEq):
                    if quad.var == replace_from:
                        block.quads[i].res = replace_to
                    if quad.res == replace_from:
                        return
                elif isinstance(quad, QBinOp):
                    if quad.var1 == replace_from:
                        block.quads[i].var1 = replace_to
                    if quad.var2 == replace_from:
                        block.quads[i].var2 = replace_to
                    if quad.res == replace_from:
                        return
                elif isinstance(quad, QFunCall):
                    for j, arg in quad.args:
                        if arg == replace_from:
                            block.quads[i].args[j] = replace_to
                    if quad.res == replace_from:
                        return
                elif isinstance(quad, QReturn):
                    if quad.var is not None and quad.var == replace_from:
                        block.quads[i].res = replace_to
                elif isinstance(quad, QUnOp):
                    if quad.res == replace_from:
                        return
                else:
                    self.debug("Shouldn't be here compress_block replace_in_block")
                    sys.exit(1)

        for i, quad in enumerate(block.quads):
            if isinstance(quad, (QJump, QFunBegin, QLabel, QReturn, QEq, QFunCall)):
                pass
            elif isinstance(quad, QBinOp):
                if is_const(quad.var1) and is_const(quad.var2):
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

                    replace_in_block(i + 1, quad.res, res_value)
                    block.quads[i] = QEq(quad.res, res_value)
                    self.repeat = True
            elif isinstance(quad, QUnOp):
                if is_const(quad.var):
                    if quad.op == '-':
                        res_value = - int(self.known_value[quad.var])
                    elif quad.op == '!':
                        res_value = 1 - int(self.known_value[quad.var])
                    else:
                        self.debug("Shouldn't be here compress_block QUnOp")
                        sys.exit(1)
                    res_value = str(res_value)

                    replace_in_block(i + 1, quad.res, res_value)
                    block.quads[i] = QEq(quad.res, res_value)
                    self.repeat = True

        return block

    def lcse(self, blocks: List[SmallBlock]) -> List[SmallBlock]:
        def lcse_block(block: SmallBlock) -> SmallBlock:
            def replace_in_block(start: int, replace_from: (str, str, str), replace_to: str) -> None:
                for i in range(start, len(block.quads)):
                    quad = block.quads[i]
                    if isinstance(quad, (QJump, QFunBegin, QLabel, QReturn, QUnOp)):
                        pass
                    elif isinstance(quad, QBinOp):
                        if (quad.var1, quad.op, quad.var2) == replace_from:
                            block.quads[i] = QEq(quad.res, replace_to)
                        if quad.res in list(replace_from):
                            return
                    elif isinstance(quad, (QEq, QFunCall, QUnOp)):
                        if quad.res in list(replace_from):
                            return
                    else:
                        self.debug("Shouldn't be here lcse_block replace_in_block")
                        sys.exit(1)

            placeholder = block.quads
            block.quads = []
            for i, quad in enumerate(placeholder):
                if isinstance(quad, (QJump, QFunBegin, QFunEnd, QLabel, QUnOp, QReturn, QFunCall, QEq)):
                    pass
                elif isinstance(quad, QBinOp):
                    replace_in_block(i + 1, quad.res, quad.res)
                else:
                    self.debug("Shouldn't be here clear_block")
                    sys.exit(1)

                block.quads.append(quad)

            return block

        for i, block in enumerate(blocks):
            blocks[i] = lcse_block(block)

        blocks = self.clear_blocks(blocks)

        return blocks

    def propagate_in_blocks(self, blocks: List[SmallBlock]) -> List[SmallBlock]:
        def propagate_in_block(block: SmallBlock) -> SmallBlock:
            def replace_in_block(start: int, replace_from: str, replace_to: str) -> None:
                for i in range(start, len(block.quads)):
                    quad = block.quads[i]
                    if isinstance(quad, (QJump, QFunBegin, QFunEnd, QLabel)):
                        pass
                    elif isinstance(quad, QEq):
                        if quad.var == replace_from:
                            replace_in_block(i + 1, quad.res, replace_to)
                        if quad.res == replace_from:
                            return
                    elif isinstance(quad, QBinOp):
                        if quad.var1 == replace_from:
                            block.quads[i].var1 = replace_to
                        if quad.var2 == replace_from:
                            block.quads[i].var2 = replace_to
                        if quad.res == replace_from:
                            return
                    elif isinstance(quad, QFunCall):
                        for j, arg in enumerate(quad.args):
                            if arg == replace_from:
                                block.quads[i].args[j] = replace_to
                        if quad.res == replace_from:
                            return
                    elif isinstance(quad, QReturn):
                        if quad.var is not None and quad.var == replace_from:
                            block.quads[i].res = replace_to
                    elif isinstance(quad, QUnOp):
                        if quad.res == replace_from:
                            return
                    else:
                        self.debug("Shouldn't be here propagate_in_block replace_in_block")
                        sys.exit(1)

            for i, quad in enumerate(block.quads):
                if isinstance(quad, (QJump, QFunBegin, QFunEnd, QLabel, QUnOp, QReturn, QFunCall, QBinOp)):
                    pass
                elif isinstance(quad, QEq):
                    if not is_register(quad.var):
                        replace_in_block(i + 1, quad.res, quad.var)
                else:
                    self.debug("Shouldn't be here clear_block")
                    sys.exit(1)

            return block

        for i, block in enumerate(blocks):
            blocks[i] = propagate_in_block(block)

        blocks = self.clear_blocks(blocks)

        return blocks







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
