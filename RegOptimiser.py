from typing import List

import sys
import bisect
from utils import *


def get_mem_loc(var: str) -> str:
    m = re.match(r'.*_t(\d*)', var)
    if m:
        var_loc = '-{}(%rbp)'.format(8 * (5 + int(m.group(1))))
    else:
        var_loc = var

    return var_loc


def has_register(block: SmallBlock, var: str) -> bool:
    if is_const(var):
        return True

    for place in block.table[var]:
        if place in free_registers:
            return True
    return False


def clear_block(block: SmallBlock, quad: Quad) -> (SmallBlock, Quad):
    for reg in free_registers:
        if block.table[reg] is not None:
            for var in block.table[reg]:
                var_loc = get_mem_loc(var)
                if var_loc not in block.table[var] and var in quad.alive:
                    quad.code.append('    movq {}, {}'.format(reg, var_loc))
                block.table[var].discard(reg)
        block.table[reg] = set()
    return block, quad


def clear_reg(block: SmallBlock, quad: Quad, reg: str, force_save=False) -> (SmallBlock, Quad):
    placeholder = block.table[reg].copy()

    for var in placeholder:
        block.table[reg].discard(var)
        block.table[var].discard(reg)

        if block.table[var] == set() and var in quad.alive or force_save:
            var_loc = get_mem_loc(var)
            quad.code.append('    movq {}, {}'.format(reg, var_loc))

    return block, quad


def clear_var(block: SmallBlock, var: str) -> SmallBlock:
    placeholder = block.table[var].copy()
    for reg in placeholder:
        if reg in free_registers:
            block.table[reg].discard(var)

    block.table[var] = set()

    return block


def get_anything(block: SmallBlock, var: str) -> str:
    if is_const(var):
        return '$' + var

    # Prefer register
    for place in block.table[var]:
        if place in free_registers:
            return place

    # But pointer is still ok
    return get_mem_loc(var)


def get_prolog(quad):
    quad.code.append('    push %rbp')
    quad.code.append('    mov %rsp, %rbp')

    for reg in callee_saved:
        quad.code.append('    push {}'.format(reg))

    return quad


class RegOptimiser:
    def __init__(self, debug):
        self.dbug = debug
        self.code = []
        self.block_counter = 1
        self.add_at_the_end = 0
        self.appearances = {}
        self.line = 0
        self.strings = {}
        self.string_counter = 1

    def debug(self, msg) -> None:
        if self.dbug:
            sys.stderr.write(msg)

    def optimise(self, blocks: List[SmallBlock]) -> List[SmallBlock]:
        for block in blocks:
            self.add_appearances(block)

        for block in blocks:
            self.calculate_code(block)

        prolog_block = SmallBlock(str(0))
        prolog_block.quads.append(self.add_strings())
        prolog_block.quads.append(add_start())
        blocks.insert(0, prolog_block)

        return blocks

    def add_appearances(self, block: SmallBlock):
        for _, quad in enumerate(block.quads):
            self.line += 1
            quad.line = self.line

            if isinstance(quad, (QJump, QFunBegin, QFunCall)):
                pass
            elif isinstance(quad, QCmp):
                self.add_appearance(quad.var1)
                self.add_appearance(quad.var2)
            elif isinstance(quad, QReturn):
                self.add_appearance(quad.var)
            elif isinstance(quad, QEq):
                self.add_appearance(quad.res)
                self.add_appearance(quad.var)
            elif isinstance(quad, QFunCall):
                for arg in quad.args:
                    self.add_appearance(arg)
            elif isinstance(quad, QBinOp):
                self.add_appearance(quad.var1)
                self.add_appearance(quad.var2)
            elif isinstance(quad, QUnOp):
                self.add_appearance(quad.var)
        return block

    def add_appearance(self, var):
        if var not in self.appearances:
            self.appearances[var] = []
        self.appearances[var].append(self.line)

    def add_string(self, key):
        if key not in self.strings:
            self.strings[key] = '_string_{}'.format(self.string_counter)
            self.string_counter += 1

    def add_strings(self):
        quad = QEmpty()
        if not self.strings:
            return quad

        quad.code.append('.data')
        for val, label in self.strings.items():
            if val == '':
                val = '""'
            quad.code.append('    {}: .string {}'.format(label, val))

        return quad

    def calculate_code(self, block: SmallBlock) -> SmallBlock:
        place_holder = block.quads
        block.quads = []

        for i, quad in enumerate(place_holder):
            if isinstance(quad, QEmpty):
                block.quads.append(quad)
            elif isinstance(quad, QLabel):
                quad.code.append(quad.name + ':')
                block.quads.append(quad)
            elif isinstance(quad, QJump):
                quad.code.append('    jmp {}'.format(quad.name))
                block.quads.append(quad)
            elif isinstance(quad, QCmp):
                # Both don't have registers and the the first one will be alive while the second won't be
                if not has_register(block, quad.var1) and not has_register(block, quad.var2) \
                   and quad.var1 in quad.alive and quad.var2 not in quad.alive:
                    block, quad, var1_loc = self.get_register(block, quad, quad.var1)
                    var2_loc = get_anything(block, quad.var2)
                else:
                    var1_loc = get_anything(block, quad.var1)
                    block, quad, var2_loc = self.get_register(block, quad, quad.var2)

                op = "cmp" if is_register(var1_loc) or is_register(var2_loc) else "cmpq"

                quad.code.append('    {} {}, {}'.format(op, var2_loc, var1_loc))
                quad.code.append('    {} {}'.format(quad.op, quad.name))

                block.quads.append(quad)
            elif isinstance(quad, QReturn):
                if quad.var is not None:
                    block, quad, reg = self.get_register(block, quad, quad.var)
                    quad.code.append('    movq {}, %rax'.format(reg))

                quad.code.append('    add ${}, %rsp'.format(8 * self.add_at_the_end))
                quad_empty = get_epilog()
                quad_empty.code.append('    ret')
                quad_empty.alive = quad.alive

                block.quads.append(quad)
                block.quads.append(quad_empty)
            elif isinstance(quad, QEq):
                # Second argument is a number
                if quad.var.isnumeric() or quad.var.startswith("-") and quad.var[1:].isnumeric():
                    block, quad, var_reg = self.get_free_register(block, quad)
                    quad.code.append('    movq ${}, {}'.format(int(quad.var), var_reg))
                # Second argument is a string
                elif quad.var == '' or quad.var[0] == '"':
                    self.add_string(quad.var)
                    block, quad, var_reg = self.get_free_register(block, quad)

                    quad.code.append('    movq ${}, {}'.format(self.strings[quad.var], var_reg))
                elif quad.var in arg_registers:
                    block, quad, var_reg = self.get_free_register(block, quad)

                    quad.code.append('    mov {}, {}'.format(quad.var, var_reg))
                else:
                    block, quad, var_reg = self.get_register(block, quad, quad.var)
                    if quad.var not in quad.alive:
                        block.table[quad.var] = set()
                        block.table[var_reg].discard(quad.var)

                if quad.res in quad.alive:
                    block = clear_var(block, quad.res)
                    block.table[var_reg].add(quad.res)
                    block.table[quad.res].add(var_reg)

                block.quads.append(quad)
            elif isinstance(quad, QFunBegin):
                quad_empty = QEmpty()
                quad_empty.code.append('{}:'.format(quad.name))
                quad_empty = get_prolog(quad_empty)
                quad_empty.alive = quad.alive
                block.quads.append(quad_empty)
                local_vars_size = quad.var

                # we want to have (8 * local_vars_size + <number of pushed registers> * 8) % 16 == 0
                # to make space for local variables and callee saved regs and allign %rsp to 16
                while (8 * local_vars_size + 6 * 8) % 16 != 8:
                    local_vars_size += 1

                # At the end of function restore stack size
                self.add_at_the_end = local_vars_size
                quad.code.append('    sub ${}, %rsp'.format(8 * local_vars_size))
                block.quads.append(quad)
            elif isinstance(quad, QFunEnd):
                block.quads.append(quad)
            elif isinstance(quad, QFunCall):
                for arg in quad.args[:5:-1]:
                    block, quad, arg_loc = self.get_register(block, quad, arg)
                    quad.code.append('    push {}'.format(arg_loc))

                for arg, reg in zip(quad.args[:6], arg_registers):
                    arg_loc = get_anything(block, arg)

                    op = 'mov' if arg_loc in free_registers else 'movq'
                    quad.code.append('    {} {}, {}'.format(op, arg_loc, reg))

                quad.code.append('    call {}'.format(quad.name))

                if len(quad.args) > 6:
                    quad.code.append('    add ${}, %rsp'.format(8 * (len(quad.args) - 6)))

                if quad.res in quad.alive:
                    block, quad, free_reg = self.get_free_register(block, quad)
                    quad.code.append('    movq %rax, {}'.format(free_reg))
                    quad_store = store_caller(block, QEmpty())
                    quad_restore = restore_caller(block, QEmpty())
                    block.table[free_reg].add(quad.res)
                    block.table[quad.res].add(free_reg)
                else:
                    quad_store = store_caller(block, QEmpty())
                    quad_restore = restore_caller(block, QEmpty())

                for arg in quad.args:
                    if arg not in quad.alive:
                        clear_var(block, arg)
                        
                quad_restore.alive = quad.alive
                quad_store.alive = place_holder[i - 1].alive
                block.quads.append(quad_store)
                block.quads.append(quad)
                block.quads.append(quad_restore)
            elif isinstance(quad, QBinOp):
                # Only Concat
                if quad.typ == 'string':
                    var1_loc = get_anything(block, quad.var1)
                    var2_loc = get_anything(block, quad.var2)

                    op1 = 'mov' if var1_loc in free_registers else 'movq'
                    op2 = 'mov' if var2_loc in free_registers else 'movq'

                    quad.code.append('    {} {}, %rdi'.format(op1, var1_loc))
                    quad.code.append('    {} {}, %rsi'.format(op2, var2_loc))

                    quad.code.append('    call concat')

                    if quad.var1 not in quad.alive:
                        block = clear_var(block, quad.var1)
                    if quad.var2 not in quad.alive:
                        block = clear_var(block, quad.var2)

                    block, quad, free_reg = self.get_free_register(block, quad)
                    quad.code.append('    mov %rax, {}'.format(free_reg))

                    block.table[free_reg].add(quad.res)
                    block.table[quad.res].add(free_reg)
                # Only idiv
                elif quad.op in ['%', '/']:
                    block, quad, var1_loc = self.get_register(block, quad, quad.var1)
                    var2_loc = get_anything(block, quad.var2)

                    if quad.op == '/':
                        res_loc = '%rax'
                    else:
                        res_loc = '%rdx'

                    op = 'idiv' if var2_loc in free_registers else 'idivq'

                    quad.code.append('    movq {}, %rax'.format(var1_loc))
                    quad.code.append('    cqto')
                    quad.code.append('    {} {}'.format(op, var2_loc))

                    if quad.var1 not in quad.alive:
                        block = clear_var(block, quad.var1)
                    if quad.var2 not in quad.alive:
                        block = clear_var(block, quad.var2)

                    block, quad, free_reg = self.get_free_register(block, quad)
                    quad.code.append('    mov {}, {}'.format(res_loc, free_reg))
                    block.table[free_reg].add(quad.res)
                    block.table[quad.res].add(free_reg)
                else:
                    # res_loc = self.to_mem(quad.res)
                    block, quad, var1_loc = self.get_register(block, quad, quad.var1)
                    bloc, quad, res_loc = self.get_free_register(block, quad)
                    var2_loc = get_anything(block, quad.var2)

                    quad.code.append('    mov {}, {}'.format(var1_loc, res_loc))

                    if quad.op == '*':
                        op = 'imul'
                    elif quad.op == '+':
                        op = 'add'
                    elif quad.op == '-':
                        op = 'sub'
                    else:
                        sys.exit('No operator in Optimiser calculate code QBinOP')

                    if not is_register(var2_loc):
                        op += 'q'

                    quad.code.append('    {} {}, {}'.format(op, var2_loc, res_loc))

                    if quad.var1 not in quad.alive:
                        block = clear_var(block, quad.var1)
                    if quad.var2 not in quad.alive:
                        block = clear_var(block, quad.var2)

                    block.table[res_loc].add(quad.res)
                    block.table[quad.res].add(res_loc)

                block.quads.append(quad)
            elif isinstance(quad, QUnOp):
                # res_loc = self.get_register(block, quad, quad.res)
                block, quad, res_loc = self.get_register(block, quad, quad.res)
                var_loc = get_anything(block, quad.var)

                op = 'mov' if var_loc in free_registers + arg_registers else 'movq'
                quad.code.append('    {} {}, {}'.format(op, var_loc, res_loc))

                if quad.op == '-':
                    op = 'neg'
                elif quad.op == '!':
                    op = 'xor'
                elif quad.op == '--':
                    op = 'dec'
                else:
                    op = 'inc'

                if op == 'xor':
                    quad.code.append('    xorq $1, {}'.format(res_loc))
                else:
                    quad.code.append('    {} {}'.format(op, res_loc))

                block.table[res_loc].add(quad.res)
                block.table[quad.res].add(res_loc)

                if quad.var not in quad.alive:
                    block = clear_var(block, quad.var)

                block.quads.append(quad)

        quad_clear_block = QEmpty()
        quad_clear_block.alive = block.quads[-1].alive.copy()
        block, quad_clear_block = clear_block(block, quad_clear_block)

        # If last quad is jump
        if isinstance(block.quads[-1], (QJump, QCmp)):
            for code in quad_clear_block.code:
                block.quads[-1].code.insert(len(block.quads[-1].code) - 1, code)
        else:
            block.quads.append(quad_clear_block)

        return block

    def get_register(self, block: SmallBlock, quad: Quad, var: str) -> (Block, Quad, str):
        if is_const(var):
            return block, quad, '$' + var

        if var in arg_registers or is_const(var):
            return block, quad, var

        for place in block.table[var]:
            if place in free_registers + arg_registers:
                return block, quad, place

        block, quad, free_reg = self.get_free_register(block, quad)
        var_loc = get_mem_loc(var)
        quad.code.append('    movq {}, {}'.format(var_loc, free_reg))

        block.table[free_reg].add(var)
        block.table[var].add(free_reg)

        return block, quad, free_reg

    def get_free_register(self, block: SmallBlock, quad: Quad) -> (Block, Quad, str):
        for free_reg in free_registers:
            if block.table[free_reg] == set():
                return block, quad, free_reg

        block, quad = self.free_register(block, quad)
        return self.get_free_register(block, quad)

    def free_register(self, block: SmallBlock, quad: Quad) -> (Block, Quad):
        # Forget clean values and check for empty register
        for free_reg in free_registers:
            placeholder_free_reg = block.table[free_reg]

            for var in placeholder_free_reg:
                placeholder_var = block.table[var]
                for var_place in placeholder_var:
                    if is_mem_loc(var_place):
                        block.table[var].discard(free_reg)
                        block.table[free_reg].discard(var)

            if block.table[free_reg] == set():
                return block, quad

        # All left values in registers are dirty so find register that appears the farthest and clean it
        latest_appearance = -1
        reg_to_free = None
        for free_reg in free_registers:
            latest_tmp = 1000000

            for var in block.table[free_reg]:
                bisect_tmp = bisect.bisect(self.appearances[var], quad.line)
                if bisect_tmp != len(self.appearances[var]):
                    var_next_appearance = self.appearances[var][bisect_tmp]
                    latest_tmp = min(latest_tmp, var_next_appearance)

            if latest_tmp > latest_appearance:
                latest_appearance = latest_tmp
                reg_to_free = free_reg

        # for var in block.table[reg_to_free]:
        #     mem_loc = self.get_mem_loc(var)
        #     quad.code.append('    movq {}, {}'.format(reg_to_free, mem_loc))

        return clear_reg(block, quad, reg_to_free, True)


def add_start() -> QEmpty:
    quad = QEmpty()
    quad.code.append('.text')
    quad.code.append('    .global main')
    quad.code.append('    .text')
    quad.code.append('')

    return quad


def get_epilog() -> QEmpty:
    quad = QEmpty()

    for reg in reversed(callee_saved):
        quad.code.append('    pop {}'.format(reg))
    quad.code.append('    mov %rbp, %rsp')
    quad.code.append('    pop %rbp')

    return quad


def store_caller(block: SmallBlock, quad: Quad) -> Quad:
    for reg in caller_saved:
        if block.table[reg] != set():
            quad.code.append('    push {}'.format(reg))

    return quad


def restore_caller(block: SmallBlock, quad: Quad) -> Quad:
    for reg in reversed(caller_saved):
        if block.table[reg] != set():
            quad.code.append('    pop {}'.format(reg))
    return quad
