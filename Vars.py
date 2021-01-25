class Var:
    def __init__(self, type=None, value=None, loc=None):
        self.type = type
        self.value = value
        self.loc = loc


class VBool(Var):
    def __init__(self, value, loc):
        super().__init__(value=value, loc=loc)
        self.type = 'boolean'


class VInt(Var):
    def __init__(self, value, loc):
        super().__init__(value=value, loc=loc)
        self.type = 'int'


class VString(Var):
    def __init__(self, value, loc):
        super().__init__(value=value, loc=loc)
        self.type = 'string'


class VFunction(Var):
    def __init__(self, type, res_type):
        super().__init__()
        self.res_type = res_type
        self.type = type

    def __eq__(self, other):
        return other.res_type == self.res_type and other.type == self.type


class VArray(Var):
    def __init__(self, type, loc):
        super().__init__(loc=loc)
        self.type = type + '[]'

    def __eq__(self, other):
        return other.type == self.type