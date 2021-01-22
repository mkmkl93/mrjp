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
    return is_number(var) or is_string(var)


def is_number(var: str) -> bool:
    return (var is not None and var.isnumeric()) or (len(var) >= 2 and var[1:].isnumeric())


def is_string(var: str) -> bool:
    return var == '' or var[0] == '"'
