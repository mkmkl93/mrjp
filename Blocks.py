from Quads import *

arg_registers = ['edi', 'esi', 'edx', 'ecx', 'r8d', 'r9d']
free_registers = ['r10d', 'r11d', 'r12d', 'r13d', 'r14d', 'r15d']
callee_saved = ['rbx', 'r12', 'r13', 'r14', 'r15']


class Table:
    def __init__(self):
        self.table = {}

    def __getitem__(self, item) -> set:
        if item not in self.table:
            self.table[item] = set()
        return self.table[item]

    def __setitem__(self, key, value) -> None:
        self.table[key] = value


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

    def add_following_block(self, block):
        self.following_blocks.append(block)

    def add_previous_block(self, block):
        self.previous_blocks.append(block)

    def __str__(self):
        return 'Block ' + self.name + '\n'.join(str(x) for x in self.blocks)


class SmallBlock(Block):
    def __init__(self, name, block=None):
        super().__init__(name)
        self.quads = []
        self.big_brother = block
        self.table = Table()

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

    def __str__(self):
        if not self.quads:
            return ''
        else:
            return 'Block ' + self.name + ':\n' + '\n'.join([str(x) for x in self.quads])




