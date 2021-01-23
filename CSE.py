from typing import List

import sys
from CalcAliveSet import CalcAliveSet
from utils import *

class CSE:
    def __init__(self, debug):
        self.dbug = debug
        self.repeat = True
        self.tmp_counter = 0

    def get_tmp_number(self) -> int:
        self.tmp_counter += 1
        return self.tmp_counter

    def debug(self, msg) -> None:
        if self.dbug:
            sys.stderr.write(msg)

    def error(self, msg) -> None:
        sys.stderr.write("ERROR\n")
        sys.stderr.write("\033[91mRuntime error\033[0m\n")
        sys.stderr.write(msg + '\n')
        sys.exit(1)

    def optimise(self, blocks: List[SmallBlock]) -> List[SmallBlock]:
        while self.repeat:
            self.repeat = False
            blocks = self.compress_values(blocks)
            blocks = self.lcse(blocks)
            blocks = self.propagate_in_blocks(blocks)
            blocks = self.clear_blocks(blocks)
            blocks = self.gcse(blocks)# clear_blocks should be called before that

        return blocks

    def compress_values(self, blocks: List[SmallBlock]) -> List[SmallBlock]:
        def compress_block(block: SmallBlock) -> SmallBlock:
            def replace_in_block(start: int, replace_from: str, replace_to: str):
                for i in range(start, len(block.quads)):
                    quad = block.quads[i]
                    if isinstance(quad, (QJump, QFunBegin, QFunEnd, QLabel)):
                        pass
                    elif isinstance(quad, QEq):
                        if quad.var == replace_from:
                            block.quads[i].var = replace_to
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
                    elif isinstance(quad, QCmp):
                        if quad.var1 == replace_from:
                            block.quads[i].var1 = replace_to
                        if quad.var2 == replace_from:
                            block.quads[i].var2 = replace_to
                    else:
                        self.debug("Shouldn't be here compress_block replace_in_block")
                        sys.exit(1)

            for i, quad in enumerate(block.quads):
                if isinstance(quad, (QJump, QFunBegin, QFunEnd, QLabel, QReturn, QEq, QFunCall)):
                    pass
                elif isinstance(quad, QBinOp):
                    if is_const(quad.var1) and is_const(quad.var2):
                        if quad.op == '+' and quad.typ == 'string':
                            res_value = str(quad.var1[1:-1]) + str(quad.var2[1:-1])
                        elif quad.op == '+' and quad.typ == 'int':
                            res_value = int(quad.var1) + int(quad.var2)
                        elif quad.op == '-':
                            res_value = int(quad.var1) - int(quad.var2)
                        elif quad.op == '*':
                            res_value = int(quad.var1) * int(quad.var2)
                        elif quad.op == '/':
                            res_value = calculate_div(int(quad.var1), int(quad.var2))
                            if res_value is None:
                                self.error("Divider equals to 0")
                        elif quad.op == '%':
                            res_value = calculate_mod(int(quad.var1), int(quad.var2))
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
                            res_value = - int(quad.var)
                        elif quad.op == '!':
                            res_value = 1 - int(quad.var)
                        elif quad.op == '++':
                            res_value = 1 + int(quad.var)
                        elif quad.op == '--':
                            res_value = 1 - int(quad.var)
                        else:
                            self.debug("Shouldn't be here compress_block QUnOp")
                            sys.exit(1)
                        res_value = str(res_value)

                        replace_in_block(i + 1, quad.res, res_value)
                        block.quads[i] = QEq(quad.res, res_value)
                        self.repeat = True
                elif isinstance(quad, QCmp):
                    if is_const(quad.var1) and is_const(quad.var2):
                        if quad.op == 'jge':
                            res = int(quad.var1) < int(quad.var2)
                        elif quad.op == 'jg':
                            res = int(quad.var1) <= int(quad.var2)
                        elif quad.op == 'jle':
                            res = int(quad.var1) > int(quad.var2)
                        elif quad.op == 'jl':
                            res = int(quad.var1) >= int(quad.var2)
                        elif quad.op == 'jne':
                            res = int(quad.var1) == int(quad.var2)
                        elif quad.op == 'je':
                            res = int(quad.var1) != int(quad.var2)
                        else:
                            self.debug("Shouldn't be here compress_block QCmp")
                            sys.exit(1)

                        if res:
                            block.quads[i] = QEmpty()
                        else:
                            block.quads[i] = QJump(quad.name)
                else:
                    self.debug("Shouldn't be here compress_block")
                    sys.exit(1)

            return block

        placeholder = blocks
        blocks = []
        for block in placeholder:
            blocks.append(compress_block(block))

        return blocks

    def clear_blocks(self, blocks: List[SmallBlock]) -> List[SmallBlock]:
        label_jmp_counter = {}
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
                elif isinstance(quad, QEmpty):
                    if not quad.code:
                        self.repeat = True
                    else:
                        block.quads.append(quad)
                # elif isinstance(quad, QLabel):
                #     if quad.name in label_jmp_counter:
                #         block.quads.append(quad)
                #     else:
                #         self.repeat = True
                else:
                    self.debug("Shouldn't be here clear_blocks clear_block")
                    sys.exit(1)

            return block

        # def count_labels() -> None:
        #     for block in blocks:
        #         for quad in block.quads:
        #             if isinstance(quad, (QFunBegin, QFunCall, QReturn, QFunEnd, QLabel, QEq, QBinOp, QUnOp, QEmpty)):
        #                 pass
        #             elif isinstance(quad, (QJump, QCmp)):
        #                 label_jmp_counter[quad.name] = 1
        #             else:
        #                 self.debug("Shouldn't be here clear_blocks count_labels")
        #                 sys.exit(1)

        alive = CalcAliveSet(self.dbug)
        blocks = alive.calc(blocks)

        # count_labels()

        for i, block in enumerate(blocks):
            blocks[i] = clear_block(block)

        return blocks

    def lcse(self, blocks: List[SmallBlock]) -> List[SmallBlock]:
        def lcse_block(block: SmallBlock) -> SmallBlock:
            def replace_in_block(start: int, replace_from: (str, str, str), replace_to: str) -> bool:
                changed = False
                for i in range(start, len(placeholder)):
                    quad = placeholder[i]
                    if isinstance(quad, (QJump, QFunBegin, QFunEnd, QLabel, QReturn, QUnOp, QCmp)):
                        pass
                    elif isinstance(quad, QBinOp):
                        if (quad.var1, quad.op, quad.var2) == replace_from:
                            placeholder[i] = QEq(quad.res, replace_to)
                            changed = True
                        if quad.res in list(replace_from):
                            return
                    elif isinstance(quad, (QEq, QFunCall, QUnOp)):
                        if quad.res in list(replace_from):
                            return
                    else:
                        self.debug("Shouldn't be here lcse_block replace_in_block")
                        sys.exit(1)
                return changed

            placeholder = block.quads
            block.quads = []
            for i, quad in enumerate(placeholder):
                if isinstance(quad, (QEmpty, QJump, QFunBegin, QFunEnd, QLabel, QUnOp, QReturn, QFunCall, QEq, QCmp)):
                    pass
                elif isinstance(quad, QBinOp):
                    m = re.match(r'(.*)t\d*', quad.res)
                    tmp_name = '{}tmp{}'.format(m.group(1), self.get_tmp_number())
                    if replace_in_block(i + 1, (quad.var1, quad.op, quad.var2), tmp_name):
                        old_res = quad.res
                        quad.res = tmp_name
                        block.quads.append(quad)
                        quad = QEq(old_res, tmp_name)
                else:
                    self.debug("Shouldn't be here lcse lcse_block")
                    sys.exit(1)

                block.quads.append(quad)

            return block

        for i, block in enumerate(blocks):
            blocks[i] = lcse_block(block)

        return blocks

    def propagate_in_blocks(self, blocks: List[SmallBlock]) -> List[SmallBlock]:
        def propagate_in_block(block: SmallBlock) -> SmallBlock:
            def replace_in_block(start: int, replace_from: str, replace_to: str) -> None:
                for i in range(start, len(block.quads)):
                    quad = block.quads[i]
                    if isinstance(quad, (QEmpty, QJump, QFunBegin, QFunEnd, QLabel)):
                        pass
                    elif isinstance(quad, QEq):
                        if quad.var == replace_from:
                            block.quads[i].var = replace_to
                            replace_in_block(i + 1, quad.res, replace_to)
                        if quad.res == replace_from:
                            return
                    elif isinstance(quad, QBinOp):
                        if quad.var1 == replace_from:
                            block.quads[i].var1 = replace_to
                            self.repeat = True
                        if quad.var2 == replace_from:
                            block.quads[i].var2 = replace_to
                            self.repeat = True
                        if quad.res == replace_from:
                            return
                    elif isinstance(quad, QFunCall):
                        for j, arg in enumerate(quad.args):
                            if arg == replace_from:
                                block.quads[i].args[j] = replace_to
                                self.repeat = True
                        if quad.res == replace_from:
                            return
                    elif isinstance(quad, QReturn):
                        if quad.var is not None and quad.var == replace_from:
                            block.quads[i].var = replace_to
                            self.repeat = True
                    elif isinstance(quad, QUnOp):
                        if quad.var == replace_from:
                            block.quads[i].var = replace_to
                        if quad.res == replace_from:
                            return
                    elif isinstance(quad, QCmp):
                        if quad.var1 == replace_from:
                            block.quads[i].var1 = replace_to
                            self.repeat = True
                        if quad.var2 == replace_from:
                            block.quads[i].var2 = replace_to
                            self.repeat = True
                    else:
                        self.debug("Shouldn't be here propagate_in_block replace_in_block")
                        sys.exit(1)

            for i, quad in enumerate(block.quads):
                if isinstance(quad, (QEmpty, QJump, QFunBegin, QFunEnd, QLabel, QUnOp, QReturn, QFunCall, QBinOp, QCmp)):
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

        return blocks

    def gcse(self, blocks: List[SmallBlock]) -> List[SmallBlock]:
        def calculate_alive_exps(blocks: List[SmallBlock]) -> List[SmallBlock]:
            def calculate_alive(block: SmallBlock, alive_set: AliveExpr) -> AliveExpr:
                for quad in block.quads:
                    if isinstance(quad, (QJump, QCmp, QReturn, QFunBegin, QFunEnd, QFunCall)):
                        pass
                    elif isinstance(quad, QEq):
                        alive_set.add((quad.res,), quad.var)
                        alive_set.discard(quad.res)
                    elif isinstance(quad, QBinOp):
                        alive_set.add((quad.var1, quad.op, quad.var2), quad.res)
                        alive_set.discard(quad.res)
                    elif isinstance(quad, QUnOp):
                        alive_set.add((quad.op, quad.var), quad.res)
                        alive_set.discard(quad.res)
                return alive_set

            map_block = {}
            n = len(blocks)

            for i in range(n):
                map_block[blocks[i].name] = i

            for block in blocks:
                block.in_alive_expr = AliveExpr()
                block.out_alive_expr = AliveExpr()

            for i in range(n):
                que = [i]

                while len(que) != 0:
                    x = que.pop()

                    old_state = blocks[x].out_alive_expr.copy()
                    blocks[x].out_alive_expr = calculate_alive(blocks[x], blocks[x].in_alive_expr.copy())
                    new_state = blocks[x].out_alive_expr.copy()

                    if old_state != new_state or len(blocks[x].quads) == 1:
                        for following_name in blocks[x].following_blocks:
                            following_number = map_block[following_name]
                            blocks[following_number].in_alive_expr.intersection(new_state)
                            que.append(following_number)
            return blocks

        def gcse_block(block: SmallBlock) -> SmallBlock:
            alive_exps = block.in_alive_expr.copy()
            for i, quad in enumerate(block.quads):
                if isinstance(quad, (QEmpty, QJump, QFunBegin, QFunEnd, QLabel)):
                    pass
                elif isinstance(quad, QEq):
                    if quad.var in alive_exps:
                        block.quads[i].var = alive_exps[quad.var]
                        self.repeat = True
                    alive_exps.discard(quad.res)
                elif isinstance(quad, QBinOp):
                    tmp = (quad.var1, quad.op, quad.var2)
                    if tmp in alive_exps:
                        block.quads[i] = QEq(quad.res, alive_exps[tmp])
                        self.repeat = True
                    elif (quad.var1,) in alive_exps:
                        block.quads[i].var1 = alive_exps[(quad.var1,)]
                        self.repeat = True
                    elif (quad.var2,) in alive_exps:
                        block.quads[i].var2 = alive_exps[(quad.var2,)]
                        self.repeat = True
                    alive_exps.discard(quad.res)
                elif isinstance(quad, QFunCall):
                    for j, arg in enumerate(quad.args):
                        if arg in alive_exps:
                            block.quads[i].args[j] = alive_exps[arg]
                            self.repeat = True
                    alive_exps.discard(quad.res)
                elif isinstance(quad, QReturn):
                    if quad.var is not None and quad.var in alive_exps:
                        block.quads[i].var = alive_exps[quad.var]
                        self.repeat = True
                elif isinstance(quad, QUnOp):
                    if quad.var in alive_exps:
                        block.quads[i].var = alive_exps[quad.var]
                        self.repeat = True
                    alive_exps.discard(quad.res)
                elif isinstance(quad, QCmp):
                    if quad.var1 in alive_exps:
                        block.quads[i].var1 = alive_exps[quad.var1]
                        self.repeat = True
                    if quad.var2 in alive_exps:
                        block.quads[i].var = alive_exps[quad.var2]
                        self.repeat = True
                else:
                    self.debug("Shouldn't be here gcse_block")
                    sys.exit(1)

            return block

        blocks = calculate_alive_exps(blocks)

        for i, block in enumerate(blocks):
            blocks[i] = gcse_block(block)

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
