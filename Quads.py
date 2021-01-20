class AliveSet:
    def __init__(self, s=set()):
        self.alive_set = s.copy()

    def __str__(self):
        return str(self.alive_set)

    def __contains__(self, item):
        return item in self.alive_set

    def __eq__(self, other):
        return self.alive_set == other.alive_set

    def union(self, other):
        self.alive_set |= other.alive_set

    def add(self, value):
        if value is None or value.isnumeric() or value == '' or value[0] == '"' or (value[0] == '-' and value[1:].isnumeric()):
            pass
        else:
            self.alive_set.add(value)

    def discard(self, value):
        self.alive_set.discard(value)

    def copy(self):
        return AliveSet(self.alive_set.copy())


class Quad:
    def __init__(self):
        self.alive = AliveSet()
        self.code = []
        self.line = 0

    def __str__(self):
        delimeter = '\n' + (' ' * 60)

        return '{}'.format(str(self.alive)) + delimeter.join([''] + self.code)


class QEmpty(Quad):
    def __init__(self):
        super().__init__()

    def __str__(self):
        return 'QEmpty'.ljust(40) + super().__str__()


class QLabel(Quad):
    def __init__(self, name):
        super().__init__()
        self.name = name

    def __str__(self):
        return '{}:'.format(self.name).ljust(40) + super().__str__()


class QJump(Quad):
    def __init__(self, op, name):
        super().__init__()
        self.op = op
        self.name = name

    def __str__(self):
        return '{} {}'.format(self.op, self.name).ljust(40) + super().__str__()


class QCmp(Quad):
    def __init__(self, var1, var2):
        super().__init__()
        self.var1 = var1
        self.var2 = var2

    def __str__(self):
        return 'cmp {}, {}'.format(self.var1, self.var2).ljust(40) + super().__str__()


class QReturn(Quad):
    def __init__(self, var=None):
        super().__init__()
        self.var = var

    def __str__(self):
        if self.var is None:
            return 'return {}'.format(super().__str__())
        else:
            return 'return {}'.format(self.var).ljust(40) + super().__str__()


class QEq(Quad):
    def __init__(self, var1, var2):
        super().__init__()
        self.var1 = var1
        self.var2 = var2

    def __str__(self):
        return '{} = {}'.format(self.var1, self.var2).ljust(40) + super().__str__()


class QFunBegin(Quad):
    def __init__(self, name, var=None):
        super().__init__()
        self.name = name
        self.var = var

    def __str__(self):
        if self.var is None:
            return '{}'.format(self.name)
        else:
            return '{}__begin {}'.format(self.name, self.var).ljust(40) + super().__str__()


class QFunEnd(Quad):
    def __init__(self, name):
        super().__init__()
        self.name = name

    def __str__(self):
        return '{}__end'.format(self.name).ljust(40) + super().__str__()


class QFunCall(Quad):
    def __init__(self, name, var, args):
        super().__init__()
        self.var = var
        self.name = name
        self.args = args

    def __str__(self):
        if self.var is None:
            return 'call {} {}'.format(self.name, ' '.join(self.args)).ljust(40) + super().__str__()
        else:
            return '{} = call {} {}'.format(self.var, self.name, ' '.join(self.args)).ljust(40) + super().__str__()


class QBinOp(Quad):
    def __init__(self, res, var1, op, var2, typ='int'):
        super().__init__()
        self.res = res
        self.var1 = var1
        self.op = op
        self.var2 = var2
        self.typ = typ

    def __str__(self):
        return '{} = {} {} {} ({})'.format(self.res, self.var1, self.op, self.var2, self.typ).ljust(40) + super().__str__()


class QUnOp(Quad):
    def __init__(self, res, op, var):
        super().__init__()
        self.res = res
        self.op = op
        self.var = var

    def __str__(self):
        return '{} = {} {}'.format(self.res, self.op, self.var).ljust(40) + super().__str__()
