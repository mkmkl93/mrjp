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
        self.add_at_the_end = 0

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

    def divide_into_blocks(self, quads: List[Quad], res) -> List[SmallBlock]:
        block = SmallBlock(str(self.block_counter))
        block.add_quad(quads[0])
        self.block_counter += 1

        for i, quad in enumerate(quads[1:]):
            if isinstance(quad, (QLabel, QFunBegin)):
                res.append(block)
                return self.divide_into_blocks(quads[i + 1:], res)
            elif isinstance(quad, QJump):
                block.add_quad(quad)
                res.append(block)
                return self.divide_into_blocks(quads[i + 2:], res)
            else:
                block.add_quad(quad)

        res.append(block)
        return res

    def optimise(self, blocks: List[Block]) -> List[Block]:
        quads = []
        for block in blocks:
            quads = self.get_quads(block, quads)

        blocks = self.divide_into_blocks(quads, [])

        blocks = self.calculate_alive_all(blocks)

        for block in blocks:
            block_label = block.quads[0].name
            self.debug('{{ {} }} -> {} -> {{ {} }}\n'.format(', '.join(block.previous_blocks), block_label, ', '.join(block.following_blocks)))

        for block in blocks:
            self.calculate_code(block)

        prolog_block = SmallBlock(str(0))
        prolog_block.quads.append(self.add_strings())
        prolog_block.quads.append(self.add_start())
        blocks.insert(0, prolog_block)

        return blocks

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

    def get_epilog(self):
        quad = QEmpty()

        for reg in reversed(callee_saved):
            quad.code.append('    pop {}'.format(reg))
        quad.code.append('    mov %rbp, %rsp')
        quad.code.append('    pop %rbp')

        return quad

    def store_caller(self, block, quad):
        for reg in caller_saved:
            if block.table[reg] != set():
                quad.code.append('    push {}'.format(reg))

        return quad

    def restore_caller(self, block, quad):
        for reg in reversed(caller_saved):
            if block.table[reg] != set():
                quad.code.append('    pop {}'.format(reg))
        return quad

    def get_prolog(self, quad):
        quad.code.append('    push %rbp')
        quad.code.append('    mov %rsp, %rbp')

        for reg in callee_saved:
            quad.code.append('    push {}'.format(reg))

        return quad

    def calculate_alive_all(self, blocks: List[SmallBlock]) -> List[SmallBlock]:
        map_label = {}
        n = len(blocks)

        for i in range(n):
            block_label = blocks[i].quads[0].name
            map_label[block_label] = i

        for i in range(n):
            prev_quad = blocks[i - 1].quads[-1]
            if i > 0 and not isinstance(prev_quad, QFunEnd) and (not isinstance(prev_quad, QJump) or prev_quad.op != 'jmp'):
                blocks[i].add_previous(blocks[i - 1].quads[0].name)
                blocks[i - 1].add_following(blocks[i].quads[0].name)

            act_quad = blocks[i].quads[-1]
            if isinstance(act_quad, QJump):
                blocks[i].add_following(act_quad.name)
                jmp_indx = map_label[act_quad.name]
                blocks[jmp_indx].add_previous(blocks[i].quads[0].name)

        for i in range(n):
            que = [(i, False)]

            while len(que) != 0:
                x, flag = que.pop()

                old_state = blocks[x].quads[0].alive.copy()
                blocks[x] = self.calculate_alive(blocks[x])
                new_state = blocks[x].quads[0].alive.copy()

                if old_state != new_state or flag:
                    for prev_name in blocks[x].previous_blocks:
                        prev_number = map_label[prev_name]
                        if prev_number != x:
                            blocks[prev_number].quads[-1].alive.union(new_state)
                            que.append((prev_number, True))

        return blocks

    def calculate_alive(self, block: SmallBlock):
        alive_set = block.quads[-1].alive.copy()
        ln = len(block.quads)
        for i, quad in enumerate(block.quads[-1::-1]):
            block.quads[ln - i - 1].alive = alive_set.copy()

            if isinstance(quad, QJump):
                pass
            elif isinstance(quad, QCmp):
                alive_set.add(quad.val1)
                alive_set.add(quad.val2)
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
                alive_set.discard(quad.val)
                for arg in quad.args:
                    alive_set.add(arg)
            elif isinstance(quad, QBinOp):
                alive_set.discard(quad.res)
                alive_set.add(quad.val1)
                alive_set.add(quad.val2)
            elif isinstance(quad, QUnOp):
                alive_set.discard(quad.res)
                alive_set.add(quad.val)

        return block

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
                quad.code.append('    {} {}'.format(quad.op, quad.name))
                block.quads.append(quad)
            elif isinstance(quad, QCmp):
                # Both don't have registers and the the first one will be alive while the second won't be
                if not self.has_register(block, quad.val1) and not self.has_register(block, quad.val2) \
                   and quad.val1 in quad.alive and quad.val2 not in quad.alive:
                    block, quad, var1_loc = self.get_register(block, quad, quad.val1)
                    var2_loc = self.get_anything(block, quad.val2)
                else:
                    var1_loc = self.get_anything(block, quad.val1)
                    block, quad, var2_loc = self.get_register(block, quad, quad.val2)

                quad.code.append('    cmp {}, {}'.format(var2_loc, var1_loc))

                block.quads.append(quad)
            elif isinstance(quad, QReturn):
                if quad.val is not None:
                    block, quad, reg = self.get_register(block, quad, quad.val)
                    quad.code.append('    movq {}, %rax'.format(reg))

                quad.code.append('    add ${}, %rsp'.format(8 * self.add_at_the_end))
                quad_empty = self.get_epilog()
                quad_empty.code.append('    ret')
                quad_empty.alive = quad.alive

                block.quads.append(quad)
                block.quads.append(quad_empty)
            elif isinstance(quad, QEq):
                # Second argument is a number
                if quad.val2.isnumeric():
                    block, quad, var_reg = self.get_free_register(block, quad)
                    quad.code.append('    movq ${}, {}'.format(int(quad.val2), var_reg))
                # Second argument is a string
                elif quad.val2 == '' or quad.val2[0] == '"':
                    self.strings.append((quad.val1 + '__str', quad.val2))
                    block, quad, var_reg = self.get_free_register(block, quad)

                    quad.code.append('    movq ${}, {}'.format(quad.val1 + '__str', var_reg))
                elif quad.val2 in arg_registers:
                    block, quad, var_reg = self.get_free_register(block, quad)

                    quad.code.append('    mov {}, {}'.format(quad.val2, var_reg))
                else:
                    block, quad, var_reg = self.get_register(block, quad, quad.val2)
                    if quad.val2 not in quad.alive:
                        block.table[quad.val2] = set()
                        block.table[var_reg].discard(quad.val2)

                if quad.val1 in quad.alive:
                    block = self.clear_var(block, quad.val1)
                    block.table[var_reg].add(quad.val1)
                    block.table[quad.val1].add(var_reg)

                block.quads.append(quad)
            elif isinstance(quad, QFunBegin):
                quad_empty = QEmpty()
                quad_empty.code.append('{}:'.format(quad.name))
                quad_empty = self.get_prolog(quad_empty)
                quad_empty.alive = quad.alive
                block.quads.append(quad_empty)
                local_vars_size = quad.val

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
                    arg_loc = self.get_anything(block, arg)

                    op = 'mov' if arg_loc in free_registers else 'movq'
                    quad.code.append('    {} {}, {}'.format(op, arg_loc, reg))

                quad.code.append('    call {}'.format(quad.name))

                if len(quad.args) > 6:
                    quad.code.append('    add ${}, %rsp'.format(8 * (len(quad.args) - 6)))

                if quad.val in quad.alive:
                    block, quad, free_reg = self.get_free_register(block, quad)
                    quad.code.append('    movq %rax, {}'.format(free_reg))
                    block.table[free_reg].add(quad.val)
                    block.table[quad.val].add(free_reg)

                quad_store = self.store_caller(block, QEmpty())
                quad_restore = self.restore_caller(block, QEmpty())
                quad_restore.alive = quad.alive
                quad_store.alive = place_holder[i - 1].alive
                block.quads.append(quad_store)
                block.quads.append(quad)
                block.quads.append(quad_restore)
            elif isinstance(quad, QBinOp):
                # Only Concat
                if quad.typ == 'string':
                    val1_loc = self.get_anything(block, quad.val1)
                    val2_loc = self.get_anything(block, quad.val2)

                    op1 = 'mov' if val1_loc in free_registers else 'movl'
                    op2 = 'mov' if val2_loc in free_registers else 'movl'

                    quad.code.append('    {} {}, %rdi'.format(op1, val1_loc))
                    quad.code.append('    {} {}, %rsi'.format(op2, val2_loc))

                    quad.code.append('    call concat')

                    if quad.val1 not in quad.alive:
                        block = self.clear_var(block, quad.val1)
                    if quad.val2 not in quad.alive:
                        block = self.clear_var(block, quad.val2)

                    block, quad, free_reg = self.get_free_register(block, quad)
                    quad.code.append('    mov %rax, {}'.format(free_reg))

                    block.table[free_reg].add(quad.res)
                    block.table[quad.res].add(free_reg)
                # Only idiv
                elif quad.op in ['%', '/']:
                    block, quad, val1_loc = self.get_register(block, quad, quad.val1)
                    val2_loc = self.get_anything(block, quad.val2)

                    if quad.op == '/':
                        res_loc = '%rax'
                    else:
                        res_loc = '%rdx'

                    op = 'idiv' if val2_loc in free_registers else 'idivq'

                    quad.code.append('    movq {}, %rax'.format(val1_loc))
                    quad.code.append('    cqto')
                    quad.code.append('    {} {}'.format(op, val2_loc))

                    if quad.val1 not in quad.alive:
                        block = self.clear_var(block, quad.val1)
                    if quad.val2 not in quad.alive:
                        block = self.clear_var(block, quad.val2)

                    block, quad, free_reg = self.get_free_register(block, quad)
                    quad.code.append('    mov {}, {}'.format(res_loc, free_reg))
                    block.table[free_reg].add(quad.res)
                    block.table[quad.res].add(free_reg)
                else:
                    # res_loc = self.to_mem(quad.res)
                    block, quad, val1_loc = self.get_register(block, quad, quad.val1)
                    val2_loc = self.get_anything(block, quad.val2)
                    bloc, quad, res_loc = self.get_free_register(block, quad)

                    quad.code.append('    mov {}, {}'.format(val1_loc, res_loc))

                    if quad.op == '*':
                        op = 'imul'
                    elif quad.op == '+':
                        op = 'add'
                    elif quad.op == '-':
                        op = 'sub'
                    else:
                        sys.exit('No operator in Optimiser calculate code QBinOP')

                    if not is_register(val2_loc):
                        op += 'q'

                    quad.code.append('    {} {}, {}'.format(op, val2_loc, res_loc))

                    if quad.val1 not in quad.alive:
                        block = self.clear_var(block, quad.val1)
                    if quad.val2 not in quad.alive:
                        block = self.clear_var(block, quad.val2)

                    block.table[res_loc].add(quad.res)
                    block.table[quad.res].add(res_loc)

                block.quads.append(quad)
            elif isinstance(quad, QUnOp):
                # res_loc = self.get_register(block, quad, quad.res)
                block, quad, res_loc = self.get_register(block, quad, quad.res)
                var_loc = self.get_anything(block, quad.val)

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

                if quad.val not in quad.alive:
                    block = self.clear_var(block, quad.val)

                block.quads.append(quad)

        quad_clear_block = QEmpty()
        quad_clear_block.alive = block.quads[-1].alive.copy()
        block, quad_clear_block = self.clear_block(block, quad_clear_block)

        # If last quad is jump
        if isinstance(block.quads[-1], QJump):
            block.quads.insert(len(block.quads) - 1, quad_clear_block)
        else:
            block.quads.append(quad_clear_block)

        return block

    def get_anything(self, block: SmallBlock, var: str) -> str:
        if is_const(var):
            return '$' + var

        # Prefer register
        for place in block.table[var]:
            if place in free_registers:
                return place

        # But pointer is still ok
        return self.get_mem_loc(var)

    def get_register(self, block: SmallBlock, quad: Quad, var: str) -> (Block, Quad, str):
        if is_const(var):
            return block, quad, '$' + var

        if var in arg_registers or is_const(var):
            return block, quad, var

        for place in block.table[var]:
            if place in free_registers + arg_registers:
                return block, quad, place

        block, quad, free_reg = self.get_free_register(block, quad)
        var_loc = self.get_mem_loc(var)
        quad.code.append('    movq {}, {}'.format(var_loc, free_reg))

        block.table[free_reg].add(var)
        block.table[var].add(free_reg)

        return block, quad, free_reg

    def get_free_register(self, block: SmallBlock, quad: Quad) -> (Block, Quad, str):
        for free_reg in free_registers:
            if block.table[free_reg] == set():
                return block, quad, free_reg

        #TODO freee reg here
        sys.exit(1)
        return None

    def get_mem_loc(self, var: str) -> str:
        m = re.match(r'.*_t(\d*)', var)
        var_loc = '-{}(%rbp)'.format(8 * int(m.group(1)))

        return var_loc

    def has_register(self, block: SmallBlock, var: str):
        if is_const(var):
            return True

        for place in block.table[var]:
            if place in free_registers:
                return True
        return False

    def clear_block(self, block: SmallBlock, quad: Quad) -> (SmallBlock, Quad):
        for reg in free_registers:
            if block.table[reg] is not None:
                for var in block.table[reg]:
                    var_loc = self.get_mem_loc(var)
                    if var_loc not in block.table[var] and var in quad.alive:
                        quad.code.append('    movq {}, {}'.format(reg, var_loc))
                block.table[reg] = set()
        return block, quad

    def clear_reg(self, block: SmallBlock, quad: Quad, reg: str) -> (SmallBlock, Quad):
        placeholder = block.table[reg].copy()

        for var in placeholder:
            block.table[reg].discard(var)
            block.table[var].discard(reg)

            if block.table[var] == set() and var in quad.alive:
                var_loc = self.get_mem_loc(var)
                quad.code.append('    movq {}, {}'.format(reg, var_loc))

        return block, quad

    def clear_var(self, block: SmallBlock, var: str) -> SmallBlock:
        placeholder = block.table[var].copy()
        for reg in placeholder:
            if reg in free_registers:
                block.table[reg].discard(var)

        block.table[var] = set()

        return block