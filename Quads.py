class AliveSet:
    def __init__(self, s=set()):
        self.alive_set = s

    def __str__(self):
        return str(self.alive_set)

    def __contains__(self, item):
        return item in self.alive_set

    def __eq__(self, other):
        return self.alive_set == other.alive_set

    def union(self, other):
        self.alive_set |= other.alive_set

    def add(self, value):
        print(value, value.isnumeric())
        if value is None or value.isnumeric() or value == '' or value[0] == '"':
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
    def __init__(self, val1, val2):
        super().__init__()
        self.val1 = val1
        self.val2 = val2

    def __str__(self):
        return 'cmp {}, {}'.format(self.val1, self.val2).ljust(40) + super().__str__()


class QReturn(Quad):
    def __init__(self, val=None):
        super().__init__()
        self.val = val

    def __str__(self):
        if self.val is None:
            return 'return {}'.format(super().__str__())
        else:
            return 'return {}'.format(self.val).ljust(40) + super().__str__()


class QEq(Quad):
    def __init__(self, val1, val2):
        super().__init__()
        self.val1 = val1
        self.val2 = val2

    def __str__(self):
        return '{} = {}'.format(self.val1, self.val2).ljust(40) + super().__str__()


class QFunBegin(Quad):
    def __init__(self, name, val=None):
        super().__init__()
        self.name = name
        self.val = val

    def __str__(self):
        if self.val is None:
            return '{}'.format(self.name)
        else:
            return '{}__begin {}'.format(self.name, self.val).ljust(40) + super().__str__()


class QFunEnd(Quad):
    def __init__(self, name):
        super().__init__()
        self.name = name

    def __str__(self):
        return '{}__end'.format(self.name).ljust(40) + super().__str__()


class QFunCall(Quad):
    def __init__(self, name, val, args):
        super().__init__()
        self.val = val
        self.name = name
        self.args = args

    def __str__(self):
        if self.val is None:
            return 'call {} {}'.format(self.name, ' '.join(self.args)).ljust(40) + super().__str__()
        else:
            return '{} = call {} {}'.format(self.val, self.name, ' '.join(self.args)).ljust(40) + super().__str__()


class QBinOp(Quad):
    def __init__(self, res, val1, op, val2, typ='int'):
        super().__init__()
        self.res = res
        self.val1 = val1
        self.op = op
        self.val2 = val2
        self.typ = typ

    def __str__(self):
        return '{} = {} {} {} ({})'.format(self.res, self.val1, self.op, self.val2, self.typ).ljust(40) + super().__str__()


class QUnOp(Quad):
    def __init__(self, res, op, val):
        super().__init__()
        self.res = res
        self.op = op
        self.val = val

    def __str__(self):
        return '{} = {} {}'.format(self.res, self.op, self.val).ljust(40) + super().__str__()
