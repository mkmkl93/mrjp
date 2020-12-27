class Var:
    def __init__(self, type=None, value=None, res_type=None, loc=None):
        self.type = type
        self.value = value
        self.res_type = res_type
        self.loc = loc


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
        super().__init__(type=type, res_type=res_type)
        self.type = '(' + type + ')'