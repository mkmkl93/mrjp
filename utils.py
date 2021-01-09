from antlr.LatteParser import LatteParser
from Vars import *
from Quads import *
from Blocks import *

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


def is_const(var: str) -> bool:
    return var.isnumeric() or var == '' or var[0] == '"'
