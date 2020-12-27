class Block:
    quads = []

    def __init__(self, name):
        self.name = name
        self.var_counter = 0
        self.block_counter = 0
        self.next = None
        self.total_count = 0

    def give_var_name(self):
        self.var_counter += 1
        return '{}_t{}'.format(self.name, self.var_counter)

    def give_block_name(self):
        self.block_counter += 1
        return '{}_b{}'.format(self.name, self.block_counter)

    def add_quad(self, quad):
        self.quads.append(quad)

    def __str__(self):
        return self.name + ':\n' + '\n'.join([str(x) for x in self.quads])


class Quad:
    def __init__(self):
        pass


class QReturn(Quad):
    def __init__(self, val=None):
        super().__init__()
        self.val = val

    def __str__(self):
        if self.val is None:
            return 'return'
        else:
            return 'return {}'.format(self.val)


class QEq(Quad):
    def __init__(self, val1, val2):
        super().__init__()
        self.val1 = val1
        self.val2 = val2

    def __str__(self):
        return '{} = {}'.format(self.val1, self.val2)


class QFunBegin(Quad):
    def __init__(self, name, val=0):
        super().__init__()
        self.name = name
        self.val = val

    def __str__(self):
        return '{}__begin {}'.format(self.name, self.val)


class QFunEnd(Quad):
    def __init__(self, name):
        super().__init__()
        self.name = name

    def __str__(self):
        return '{}__end'.format(self.name)


class QEmpty(Quad):
    def __init__(self):
        super().__init__()

    def __str__(self):
        return ''


class QFunCall(Quad):
    def __init__(self, name, val, args):
        super().__init__()
        self.val = val
        self.name = name
        self.args = args

    def __str__(self):
        if self.val is None:
            return 'call {} {}'.format(self.name, ' '.join(self.args))
        else:
            return '{} = call {} {}'.format(self.val, self.name, ' '.join(self.args))


class QBinOp(Quad):
    def __init__(self, res, val1, op, val2):
        super().__init__()
        self.res = res
        self.val1 = val1
        self.op = op
        self.val2 = val2

    def __str__(self):
        return '{} = {} {} {}'.format(self.res, self.val1, self.op, self.val2)


class QUnOp(Quad):
    def __init__(self, res, op, val):
        super().__init__()
        self.res = res
        self.op = op
        self.val = val

    def __str__(self):
        return '{} = {} {}'.format(self.res, self.op, self.val)
