class Var:
    def __init__(self, type=None, value=None, loc=None):
        self.type = type
        self.value = value
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
        super().__init__()
        self.res_type = res_type
        self.type = type
