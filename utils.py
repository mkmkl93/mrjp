from antlr.LatteParser import LatteParser

registers = ['rdi', 'rsi', 'rdx', 'rcx', 'r8', 'r9', 'eax']

class Var:
    def __init__(self, typ=None, value=None, res_type=None, loc=None):
        self.type = typ
        self.value = value
        self.res_type = res_type
        self.loc = loc


def get_default_value(typ):
    if typ == 'int':
        return '0'

    if typ == 'string':
        return ''

    if typ == 'boolean':
        return 'false'

    return None


def get_from_item(item: LatteParser.ItemContext, default_value: str, typ: str):
    value = item.expr()

    return Var(typ, default_value if value is None else value.getText())