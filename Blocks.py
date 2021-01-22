from Quads import *
import re
import sys

arg_registers = ['%rdi', '%rsi', '%rdx', '%rcx', '%r8', '%r9']

callee_saved = ['%rbx', '%r12', '%r13', '%r14', '%r15']
caller_saved = ['%r10', '%r11']

free_registers = callee_saved + caller_saved


def is_register(var) -> bool:
    return var in free_registers + arg_registers


def is_mem_loc(var) -> bool:
    return re.match(r'-?\d*\(%rbp\)', var)

class Table:
    def __init__(self):
        self.table = {}

    def __getitem__(self, item) -> set:
        if item not in self.table:
            self.table[item] = set()
        return self.table[item]

    def __setitem__(self, key, value) -> None:
        self.table[key] = value


class AliveExpr:
    def __init__(self, d=dict()):
        self.alive_expr = d.copy()
        self.was_intersected = False

    def __str__(self):
        return str(self.alive_expr)

    def __contains__(self, item):
        return item in self.alive_expr

    def __eq__(self, other):
        return self.alive_expr == other.alive_expr

    def __getitem__(self, item) -> set:
        return self.alive_expr[item]

    def intersection(self, other):
        if not self.was_intersected:
            self.alive_expr = other.alive_expr.copy()
            self.was_intersected = True
        else:
            self.alive_expr = {x:self.alive_expr[x] for x in other.alive_expr if x in self.alive_expr}

    def add(self, key, value):
        self.alive_expr[key] = value

    def discard(self, delete):
        placeholder = self.alive_expr
        self.alive_expr = {}
        for key, value in placeholder.items():
            if len(list(key)) == 1:
                if delete not in [key, value]:
                    self.alive_expr[key] = value
            elif len(list(key)) == 2:
                _, var = key
                if delete not in [value, var]:
                    self.alive_expr[key] = value
            elif len(list(key)) == 3:
                var1, _, var2 = key
                if delete not in [value, var1, var2]:
                    self.alive_expr[key] = value
            else:
                print("Shouldn't be here AliveExpr")
                sys.exit(1)

    def copy(self):
        return AliveExpr(self.alive_expr)


class Block:
    def __init__(self, name):
        self.name = name
        self.var_counter = 0
        self.block_counter = 0
        self.while_counter = 0
        self.if_counter = 0
        self.label_counter = 0
        self.following_blocks = []
        self.previous_blocks = []

    def give_var_name(self):
        pass

    def give_block_name(self):
        pass

    def give_while_number(self):
        pass

    def give_if_number(self):
        pass

    def give_label(self):
        pass

    def add_quad(self, quad):
        pass

    def add_block(self, block):
        pass

    def limit_locals(self, limit):
        pass

class BigBlock(Block):
    def __init__(self, block):
        super().__init__(block.name)
        self.blocks = [block]
        self.var_counter = block.var_counter
        self.block_counter = block.block_counter
        self.if_counter = block.if_counter
        self.while_counter = block.while_counter
        self.label_counter = block.label_counter

    def add_quad(self, quad):
        self.blocks[-1].add_quad(quad)

    def add_block(self, block):
        self.blocks.append(block)
        self.blocks.append(SmallBlock(self.give_block_name()))
        return self

    def give_var_name(self):
        self.var_counter += 1
        return '{}_t{}'.format(self.name, self.var_counter)

    def give_block_name(self):
        self.block_counter += 1
        return '{}_b{}'.format(self.name, self.block_counter)

    def give_label(self):
        self.label_counter += 1
        return '{}_l{}'.format(self.name, self.label_counter)

    def give_while_number(self):
        self.while_counter += 1
        return self.while_counter

    def give_if_number(self):
        self.if_counter += 1
        return self.if_counter

    def limit_locals(self, limit):
        self.blocks[0].limit_locals(limit)

    def __str__(self):
        return 'Block ' + self.name + '\n'.join(str(x) for x in self.blocks)


class SmallBlock(Block):
    def __init__(self, name, block=None):
        super().__init__(name)
        self.quads = []
        self.big_brother = block
        self.table = Table()
        self.in_alive_expr = AliveExpr()
        self.out_alive_expr = AliveExpr()

        for free_reg in free_registers:
            self.table[free_reg] = set()

    def add_quad(self, quad):
        self.quads.append(quad)

    def add_block(self, block):
        big_block = BigBlock(self)
        big_block.add_block(block)
        return big_block

    def give_var_name(self):
        if self.big_brother is not None:
            return self.big_brother.give_var_name()
        else:
            self.var_counter += 1
            return '{}_t{}'.format(self.name, self.var_counter)

    def give_block_name(self):
        if self.big_brother is not None:
            return self.big_brother.give_block_name()
        else:
            self.block_counter += 1
            return '{}_b{}'.format(self.name, self.block_counter)

    def give_label(self):
        if self.big_brother is not None:
            return self.big_brother.give_var_name()
        else:
            self.label_counter += 1
            return '{}_l{}'.format(self.name, self.label_counter)

    def give_while_number(self):
        if self.big_brother is not None:
            return self.big_brother.give_var_name()
        else:
            self.while_counter += 1
            return self.while_counter

    def give_if_number(self):
        if self.big_brother is not None:
            return self.big_brother.give_var_name()
        else:
            self.if_counter += 1
            return self.if_counter

    def limit_locals(self, limit):
        self.quads[0] = QFunBegin(str(self.quads[0]), limit)

    def add_following(self, block_label):
        self.following_blocks.append(block_label)

    def add_previous(self, block_label):
        self.previous_blocks.append(block_label)

    def __str__(self):
        if not self.quads:
            return ''
        else:
            return ('Block ' + self.name + ':').ljust(40) + str(self.in_alive_expr) + str(self.out_alive_expr) + '\n' + '\n'.join([str(x) for x in self.quads])




