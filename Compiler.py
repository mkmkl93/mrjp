import antlr4
import sys
from antlr.LatteLexer import LatteLexer
from antlr.LatteParser import LatteParser

def error(ctx, msg):
    sys.stderr.write("ERROR\n")
    sys.exit(1)

class Value:
    def __init__(self, type, name, value):
        self.type = type
        self.name = name
        self.value = value


class Compiler:
    def __init__(self):
        self.var_type = {}
        self.var_val = {}

    def enterProgram(self, ctx: LatteParser.ProgramContext):
        for topDef in ctx.children:
            if isinstance(topDef, LatteParser.TopDefContext):
                self.enterTopDef(topDef)

    def enterTopDef(self, ctx: LatteParser.TopDefContext):
        type = ctx.type_().getText()
        name = ctx.ID().getText()
        args = ctx.arg()
        block = ctx.block()

        print(type, name, args, block)
        self.enterBlock(block, type)

    def enterBlock(self, ctx:LatteParser.BlockContext, retType):
        for stmt in ctx.children:
            if isinstance(stmt, LatteParser.StmtContext):
                if isinstance(stmt, LatteParser.RetContext):
                    self.enterRet(stmt, retType)

    def enterRet(self, ctx:LatteParser.RetContext, retType):
        val = self.enterExpr(ctx.expr())
        if val.type != retType:
            error(ctx, "Returning wront type")

    def enterExpr(self, ctx:LatteParser.ExprContext):
        if isinstance(ctx, LatteParser.EIntContext):
            return Value('int', '', int(ctx.INT().__str__()))




