import antlr4
import sys
from antlr.LatteParser import LatteParser

class Simplifier:
    def __init__(self, DEBUG):
        self.DEBUG = DEBUG

    def error(self, ctx: antlr4.ParserRuleContext, msg) -> None:
        sys.stderr.write("ERROR\n")
        sys.stderr.write("\033[91m" + "Simplify error at " + str(ctx.start.line) + ":" + str(ctx.start.column) + "\033[0m\n")
        sys.stderr.write(msg + '\n')
        sys.exit(1)

    def debug(self, msg) -> None:
        if self.DEBUG == True:
            sys.stderr.write(msg)

    def simplify(self, ctx: LatteParser.ProgramContext) -> LatteParser.ProgramContext:

        for topDef in ctx.children:
            if isinstance(topDef, LatteParser.TopDefContext):
                self.enter_top_def(topDef)

        return ctx

    def check_for_vreturn_unknown(self, ctx) -> bool:
        if isinstance(ctx, LatteParser.BlockStmtContext):
            return self.check_for_vreturn_block(ctx.block())
        if isinstance(ctx, LatteParser.StmtContext):
            return self.check_for_vreturn_stmt(ctx)

    def check_for_vreturn_stmt(self, ctx: LatteParser.StmtContext) -> bool:
        if isinstance(ctx, (LatteParser.VRetContext, LatteParser.RetContext)):
            return True
        elif isinstance(ctx, LatteParser.CondElseContext):
            stmt1 = ctx.stmt(0)
            stmt2 = ctx.stmt(1)

            return self.check_for_vreturn_unknown(stmt1) and self.check_for_vreturn_unknown(stmt2)
        elif isinstance(ctx, LatteParser.WhileContext):
            return self.check_for_vreturn_unknown(ctx.stmt())
        return False

    def check_for_vreturn_block(self, ctx: LatteParser.BlockContext) -> bool:
        for stmt in reversed(ctx.children):
            if isinstance(stmt, antlr4.TerminalNode):
                continue
            elif isinstance(stmt, LatteParser.StmtContext):
                return self.check_for_vreturn_stmt(stmt)

    def add_ret_to_block(self, ctx: LatteParser.BlockStmtContext):
        if isinstance(ctx.children[-1], LatteParser.BlockStmtContext):
            self.add_ret_to_block(ctx.children[-1])
        else:
            tmp = ctx.children[-1]
            ctx.children[-1] = LatteParser.VRetContext(ctx.parser, ctx)
            ctx.children.append(tmp)

    def enter_top_def(self, ctx: LatteParser.TopDefContext) -> None:
        typ = ctx.type_().getText()
        block = ctx.block()

        self.enter_block(block, typ)

        if typ == 'void' and not self.check_for_vreturn_block(block):
            self.add_ret_to_block(ctx.block())

    def enter_block(self, ctx: LatteParser.BlockContext, ret_type) -> None:
        for i, stmt in enumerate(ctx.children):
            if isinstance(stmt, antlr4.TerminalNode):
                continue
            elif isinstance(stmt, LatteParser.CondContext):
                if stmt.expr().getText() == 'true':
                    ctx.children[i] = stmt.stmt()
                    self.enter_stmt(stmt.stmt(), ret_type)
                elif stmt.expr().getText() == 'false':
                    ctx.children[i] = LatteParser.EmptyContext()
            elif isinstance(stmt, LatteParser.StmtContext):
                self.enter_stmt(stmt, ret_type)
            else:
                self.error(ctx, "Unresolved instance in enter_block stmt")

    def enter_while(self, ctx: LatteParser.WhileContext, ret_type) -> None:
        self.enter_stmt(ctx.stmt(), ret_type)

    def enter_cond(self, ctx: LatteParser.CondContext, ret_type) -> None:
        self.enter_stmt(ctx.stmt(), ret_type)

    def enter_cond_else(self, ctx: LatteParser.CondElseContext, ret_type) -> None:
        for i in range(2):
            self.enter_stmt(ctx.stmt(i), ret_type)

    def enter_stmt(self, ctx: LatteParser.StmtContext, ret_type):
        if isinstance(ctx, LatteParser.BlockStmtContext):
            self.enter_block(ctx.block(), ret_type)
        elif isinstance(ctx, LatteParser.CondContext):
            self.enter_cond(ctx, ret_type)
        elif isinstance(ctx, LatteParser.CondElseContext):
            self.enter_cond_else(ctx, ret_type)
        elif isinstance(ctx, LatteParser.WhileContext):
            self.enter_while(ctx, ret_type)
        else:
            return

