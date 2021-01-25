from typing import List, Set, Dict, Tuple

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
            blocks = self.loop_optimisation(blocks)
            blocks = self.compress_values(blocks)
            blocks = self.lcse(blocks)
            blocks = self.propagate_in_blocks(blocks)
            blocks = self.clear_blocks(blocks)
            blocks = self.gcse(blocks)# clear_blocks should be called before that
            # self.repeat = False

        return blocks

    def compress_values(self, blocks: List[SmallBlock]) -> List[SmallBlock]:
        def compress_block(block: SmallBlock) -> SmallBlock:
            def replace_in_block(start: int, replace_from: str, replace_to: str):
                for i in range(start, len(block.quads)):
                    quad = block.quads[i]
                    if isinstance(quad, (QEmpty, QJump, QFunBegin, QFunEnd, QLabel)):
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
                if isinstance(quad, (QEmpty, QJump, QFunBegin, QFunEnd, QLabel, QReturn, QEq, QFunCall)):
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
                if isinstance(quad, (QEmpty, QJump, QFunBegin, QFunCall, QCmp, QReturn, QFunEnd, QLabel)):
                    block.quads.append(quad)
                elif isinstance(quad, QEq):
                    if quad.res in quad.alive or quad.res.startswith('(') or quad.var.startswith('('):
                        block.quads.append(quad)
                    else:
                        self.repeat = True
                elif isinstance(quad, (QBinOp, QUnOp)):
                    if quad.res in quad.alive or quad.res.startswith('('):
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
                    if isinstance(quad, (QEmpty, QJump, QFunBegin, QFunEnd, QLabel, QReturn, QUnOp, QCmp)):
                        pass
                    elif isinstance(quad, QBinOp):
                        if (quad.var1, quad.op, quad.var2) == replace_from and not quad.var1.startswith('(') and not quad.var2.startswith('('):
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
                    tmp_name = '{}_t{}'.format(m.group(1), self.get_tmp_number())
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

        fun_begin_pos = None
        for i, block in enumerate(blocks):
            if isinstance(block.quads[0], QFunBegin):
                fun_begin_pos = i
                self.tmp_counter = block.quads[0].var
            if isinstance(block.quads[-1], QFunEnd):
                blocks[fun_begin_pos].quads[0].var = self.tmp_counter
                self.tmp_counter = -100
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
                    if not is_register(quad.var) and '(' not in quad.var and '(' not in quad.res:
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
                    if isinstance(quad, (QEmpty, QJump, QCmp, QReturn, QFunBegin, QFunEnd, QFunCall, QLabel)):
                        pass
                    elif isinstance(quad, QEq): # INNA KOLEJNOSC !!!
                        alive_set.discard(quad.res)
                        alive_set.add((quad.res,), quad.var)
                    elif isinstance(quad, QBinOp):
                        alive_set.add((quad.var1, quad.op, quad.var2), quad.res)
                        alive_set.discard(quad.res)
                    elif isinstance(quad, QUnOp):
                        alive_set.add((quad.op, quad.var), quad.res)
                        alive_set.discard(quad.res)
                    else:
                        self.debug("Shouldn't be here gcse calculate_alive")
                        sys.exit(1)

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

                    blocks[x].out_alive_expr = calculate_alive(blocks[x], blocks[x].in_alive_expr.copy())

                    for following_name in blocks[x].following_blocks:
                        following_number = map_block[following_name]
                        old_state = blocks[following_number].in_alive_expr.copy()
                        was_first = blocks[following_number].in_alive_expr.was_intersected
                        blocks[following_number].in_alive_expr.intersection(blocks[x].out_alive_expr)
                        new_state = blocks[following_number].in_alive_expr.copy()
                        if old_state != new_state or not was_first:
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
                        if (arg,) in alive_exps:
                            block.quads[i].args[j] = alive_exps[(arg,)]
                            self.repeat = True
                    alive_exps.discard(quad.res)
                elif isinstance(quad, QReturn):
                    if quad.var is not None and (quad.var,) in alive_exps:
                        block.quads[i].var = alive_exps[(quad.var,)]
                        self.repeat = True
                elif isinstance(quad, QUnOp):
                    if (quad.var,) in alive_exps:
                        block.quads[i].var = alive_exps[(quad.var,)]
                        self.repeat = True
                    alive_exps.discard(quad.res)
                elif isinstance(quad, QCmp):
                    if (quad.var1,) in alive_exps:
                        block.quads[i].var1 = alive_exps[(quad.var1,)]
                        self.repeat = True
                    if (quad.var2,) in alive_exps:
                        block.quads[i].var2 = alive_exps[(quad.var2,)]
                        self.repeat = True
                else:
                    self.debug("Shouldn't be here gcse_block")
                    sys.exit(1)

            return block

        blocks = calculate_alive_exps(blocks)

        for i, block in enumerate(blocks):
            blocks[i] = gcse_block(block)

        return blocks

    def loop_optimisation(self, blocks: List[SmallBlock]) -> List[SmallBlock]:
        def solve_while(blocks: List[SmallBlock]) -> List[SmallBlock]:
            def calc_single_definition(blocks: List[SmallBlock]) -> Set[str]:
                def calc_single_definition_block(block: SmallBlock, counter: Dict[str, int]) -> Dict[str, int]:
                    def add(var: str) -> None:
                        if var not in counter:
                            counter[var] = 0
                        counter[var] += 1

                    for quad in block.quads:
                        if isinstance(quad, (QEmpty, QLabel, QJump, QCmp, QReturn, QFunBegin, QFunEnd)):
                            pass
                        elif isinstance(quad, (QBinOp, QUnOp, QEq, QFunCall)):
                            add(quad.res)
                        else:
                            self.debug("Shouldn't be here loop_optimisation calc_single_definition_block")
                            sys.exit(1)

                    return counter

                counter = {}
                for block in blocks:
                    counter = calc_single_definition_block(block, counter)

                res = set(x for x in counter if counter[x] == 1)

                return res

            def calc_loop_variant_vars(blocks: List[SmallBlock]) -> Set[str]:
                def calc(block: SmallBlock) -> Set[str]:
                    variant_vars = set()
                    for quad in block.quads:
                        if isinstance(quad, (QEmpty, QLabel, QJump, QCmp, QReturn, QFunBegin, QFunEnd)):
                            pass
                        elif isinstance(quad, (QEq, QBinOp, QUnOp, QFunCall)):
                            variant_vars.add(quad.res)
                        else:
                            self.debug("Shouldn't be here loop_optimisation solve_while")
                            sys.exit(1)

                    return variant_vars

                variant_vars = set()
                for block in blocks:
                    variant_vars |= calc(block)

                return variant_vars

            def calc_basic_induction_vars(blocks: List[SmallBlock]) -> Set[Tuple[str, str, str]]:

                def calc_basic_induction_vars_block(block: SmallBlock, variants: Set[str]) -> Set[Tuple[str, str, str]]:
                    basic_induction_vars = set()
                    for quad in block.quads:
                        if isinstance(quad, (QEmpty, QLabel, QJump, QCmp, QReturn, QFunBegin, QFunEnd, QFunCall, QEq)):
                            pass
                        elif isinstance(quad, QBinOp):
                            if quad.res in [quad.var1, quad.var2] and not quad.var1.startswith('(') and not quad.var2.startswith('('):
                                var1, var2 = quad.var1, quad.var2
                                if quad.res == var2:
                                    var1, var2 = var2, var1 #tylko var2 moze byc const lub niezmiennikiem
                                if (is_const(var2) or var2 not in variants) and quad.op in ['+', '-']:
                                    basic_induction_vars.add((quad.res, quad.op, var2))
                        elif isinstance(quad, QUnOp) and not quad.var.startswith('('):
                            if quad.res == quad.var and quad.op in ['++', '--']:
                                if quad.op == '++':
                                    basic_induction_vars.add((quad.res, '+', '1'))
                                else:
                                    basic_induction_vars.add((quad.res, '-', '1'))
                        else:
                            self.debug("Shouldn't be here loop_optimisation calc_basic_induction_vars_block")
                            sys.exit(1)

                    return basic_induction_vars

                single_definitions = calc_single_definition(blocks)
                variants = calc_loop_variant_vars(blocks)

                basic_induction_vars = set()
                for block in blocks:
                    basic_induction_vars |= calc_basic_induction_vars_block(block, variants)

                basic_induction_vars = set((x, v1, v2) for (x, v1, v2) in basic_induction_vars if x in single_definitions)
                return basic_induction_vars

            def calc_basic_derived_vars(blocks: List[SmallBlock], basics: Set[str]) -> Set[Tuple[str, str, str, str]]:
                def calc_basic_derived_vars_block(block: SmallBlock, basics: Set[str], single_defs: Set[str], variants: Set[str]) -> Set[Tuple[str, str, str, str]]:
                    res = set()
                    for quad in block.quads:
                        if isinstance(quad, (QEmpty, QLabel, QJump, QCmp, QReturn, QFunBegin, QFunEnd, QFunCall, QUnOp)):
                            pass
                        elif isinstance(quad, QEq):
                            if quad.res not in single_defs or quad.var not in basics or is_const(quad.var) or quad.res.startswith('(') or quad.var.startswith('('):
                                pass
                            else:
                                res.add((quad.res, quad.var, '+', '0'))
                        elif isinstance(quad, QBinOp):
                            if quad.res not in single_defs or quad.res in basics or quad.op not in ['+', '-', '*'] or quad.var1.startswith('(') or quad.var2.startswith('('):
                                pass
                            elif quad.var1 in basics and quad.var2 not in variants:
                                res.add((quad.res, quad.var1, quad.op, quad.var2))
                            elif quad.var2 in basics and quad.var1 not in variants:
                                res.add((quad.res, quad.var2, quad.op, quad.var1))
                        else:
                            self.debug("Shouldn't be here loop_optimisation calc_basic_induction_vars_block")
                            sys.exit(1)

                    return res

                single_defs = calc_single_definition(blocks)
                variants = calc_loop_variant_vars(blocks)

                basic_derived = set()
                for block in blocks:
                    basic_derived |= calc_basic_derived_vars_block(block, basics, single_defs, variants)

                return basic_derived

            def replace_basic_derived_vars(blocks: List[SmallBlock], basic_derived_vars: Set[Tuple[str, str, str, str]], change_to: Dict[str, str]) -> List[SmallBlock]:
                def replace_basic_derived_vars_block(block: SmallBlock) -> SmallBlock:
                    placeholder = block.quads
                    block.quads = []

                    for i, quad in enumerate(placeholder):
                        erase_last = False
                        if isinstance(quad, (QEmpty, QLabel, QJump, QCmp, QReturn, QFunBegin, QFunEnd)):
                            pass
                        elif isinstance(quad, QBinOp):
                            if quad.var1.startswith('(') or quad.var2.startswith('('):
                                pass
                            elif (quad.res, quad.var1, quad.op, quad.var2) in basic_derived_vars or (quad.res, quad.var2, quad.op, quad.var1) in basic_derived_vars:
                                erase_last = True
                            elif quad.var1 in change_to:
                                quad.var1 = change_to[quad.var1]
                            elif quad.var2 in change_to:
                                quad.var2 = change_to[quad.var2]
                        elif isinstance(quad, QFunCall):
                            for j, arg in enumerate(quad.args):
                                if arg in change_to:
                                    quad.args[j] = change_to[arg]
                        elif isinstance(quad, QEq):
                            if quad.var.startswith('(') or quad.res.startswith('('):
                                pass
                            elif (quad.res, quad.var, '+', '0') in basic_derived_vars:
                                erase_last = True
                            elif quad.var in change_to:
                                quad.var = change_to[quad.var]
                        elif isinstance(quad, QUnOp):
                            if quad.var.startswith('(') or quad.res.startswith('('):
                                pass
                            elif quad.var in change_to:
                                quad.var = change_to[quad.var]
                        else:
                            self.debug("Shouldn't be here loop_optimisation replace_basic_derived_vars_block")
                            sys.exit(1)

                        block.quads.append(quad)
                        if erase_last:
                            block.quads.pop()

                    return block

                for i, block in enumerate(blocks):
                    blocks[i] = replace_basic_derived_vars_block(block)

                return blocks

            def actualize_derived_vars(blocks: List[SmallBlock], basic_derived_vars: Set[Tuple[str, str, str, str]], basic_vars: Set[Tuple[str, str, str]]) -> List[SmallBlock]:
                def actualize_derived_vars_block(block: SmallBlock) -> SmallBlock:
                    placeholder = block.quads
                    block.quads = []

                    for quad in placeholder:
                        if isinstance(quad, (QEmpty, QLabel, QJump, QCmp, QReturn, QFunBegin, QFunEnd, QFunCall, QEq)):
                            pass
                        elif isinstance(quad, QBinOp):
                            if quad.res in [quad.var1, quad.var2] and (quad.res, quad.op, quad.var1) in basic_vars or (quad.res, quad.op, quad.var2) in basic_vars:
                                var1, var2 = quad.var1, quad.var2
                                if (var2, quad.op, var1) in basic_vars:
                                    var1, var2 = var2, var1

                                for derived_var in basic_derived_vars:
                                    (res, iv, op, const) = derived_var
                                    if iv == var1:
                                        if op == '*':
                                            modify_derived = QBinOp(res, res, quad.op, str(int(const) * int(var2)))
                                        else:
                                            modify_derived = QBinOp(res, res, op, var2)
                                        block.quads.append(modify_derived)
                        elif isinstance(quad, QUnOp):
                            if quad.res == quad.var and quad.op in ['++', '--']:
                                if (quad.res, '+', '1') in basic_vars or (quad.res, '-', '1') in basic_vars:
                                    for derived_var in basic_derived_vars:
                                        (res, iv, op, const) = derived_var
                                        if iv == quad.var:
                                            if op == '*':
                                                modify_derived = QBinOp(res, res, '+', const)
                                            else:
                                                modify_derived = QUnOp(res, quad.op, res)
                                            block.quads.append(modify_derived)
                        else:
                            self.debug("Shouldn't be here loop_optimisation calc_basic_induction_vars_block")
                            sys.exit(1)

                        block.quads.append(quad)
                    return block

                for i, block in enumerate(blocks):
                    blocks[i] = actualize_derived_vars_block(block)

                return blocks

            blocks = self.propagate_in_blocks(blocks) #TODO przesunac wyzej
            blocks = self.compress_values(blocks)
            basic_vars = calc_basic_induction_vars(blocks)
            basic_vars_names = set(x for x, _, _ in basic_vars)
            basic_derived_vars = calc_basic_derived_vars(blocks, basic_vars_names)

            while_name = blocks[0].quads[0].name
            pre_while = SmallBlock(while_name + "_pre_block")
            change: Dict[str, str] = {}

            for derived_var in basic_derived_vars:
                (res, var1, op, var2) = derived_var
                name = '{}_t{}'.format(while_name, self.get_tmp_number())
                if op == '+' and var2 == '0':
                    add_quad = QEq(name, var1)
                else:
                    add_quad = QBinOp(name, var1, op, var2)
                pre_while.quads.append(add_quad)
                change[res] = name

            blocks = replace_basic_derived_vars(blocks, basic_derived_vars, change)
            basic_derived_vars = set((change[res], iv, op, const) for (res, iv, op, const) in basic_derived_vars)
            blocks = actualize_derived_vars(blocks, basic_derived_vars, basic_vars)

            blocks = [pre_while] + blocks
            return blocks

        while_blocks = [[]]
        placeholder = blocks
        fun_begin_pos = (-1, -1)
        for block in placeholder:
            if isinstance(block.quads[0], QLabel) and re.fullmatch(r'.*while_\d*', block.quads[0].name):
                while_blocks.append([block])
            elif isinstance(block.quads[0], QLabel) and re.fullmatch(r'.*while_\d*_end', block.quads[0].name):
                tmp = while_blocks.pop()
                while_blocks[-1].extend(solve_while(tmp))
                while_blocks[-1].append(block)

                if isinstance(block.quads[-1], QFunEnd):
                    i, j = fun_begin_pos
                    while_blocks[i][j].quads[0].var = self.tmp_counter
                    self.tmp_counter = -100
            else:
                if isinstance(block.quads[0], QFunBegin):
                    self.tmp_counter = block.quads[0].var
                    fun_begin_pos = (len(while_blocks) - 1, len(while_blocks[-1]))

                while_blocks[-1].append(block)

                if isinstance(block.quads[-1], QFunEnd):
                    i, j = fun_begin_pos
                    while_blocks[i][j].quads[0].var = self.tmp_counter
                    self.tmp_counter = -100


        alive = CalcAliveSet(self.dbug)
        blocks = alive.calc(while_blocks[0])
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
