import antlr4
import sys
from antlr.LatteParser import LatteParser
from utils import *


class FrontEnd:
    def __init__(self, file, DEBUG):
        self.envs = [{}]
        self.file = file
        self.DEBUG = DEBUG

    def error(self, ctx: antlr4.ParserRuleContext, msg) -> None:
        sys.stderr.write("ERROR\n")
        sys.stderr.write("\033[91m" + "Compilation error at " + str(ctx.start.line) + ":" + str(ctx.start.column) + "\033[0m\n")
        sys.stderr.write(msg + '\n')
        with open(self.file) as fp:
            for i, line in enumerate(fp):
                if ctx.start.line <= i + 1 <= ctx.stop.line:
                    sys.stderr.write("\033[94m" + line + "\033[0m")
        sys.exit(1)

    def debug(self, msg) -> None:
        if self.DEBUG:
            sys.stderr.write(msg)

    def add_bultin(self) -> None:
        self.envs[0]['printInt'] = VFunction(['int'], 'void')
        self.envs[0]['readInt'] = VFunction([], 'int')
        self.envs[0]['printString'] = VFunction(['string'], 'void')
        self.envs[0]['readString'] = VFunction([], 'string')
        self.envs[0]['error'] = VFunction([], 'void')

    def enter_program(self, ctx: LatteParser.ProgramContext) -> None:
        self.add_bultin()

        for topDef in ctx.children:
            if isinstance(topDef, LatteParser.TopDefContext):
                self.add_definition(topDef)

        if 'main' not in self.envs[-1] or self.envs[-1]['main'].res_type != 'int':
            self.error(ctx, 'No int main declared')

        for topDef in ctx.children:
            if isinstance(topDef, LatteParser.TopDefContext):
                self.enter_top_def(topDef)

    def add_definition(self, ctx: LatteParser.TopDefContext) -> None:
        typ = ctx.type_().getText()
        name = ctx.ID().getText()
        arguments: LatteParser.ArgContext = ctx.arg()
        args = []

        if arguments is None:
            self.envs[-1][name] = VFunction(args, typ)
            return

        if name == 'main':
            self.error(ctx, 'Main function cannot take arguments')

        for i in range(len(arguments.type_())):
            arg_typ = arguments.type_(i).getText()

            if arg_typ == 'void':
                self.error(ctx, 'Void cannot be type of a variable')

            args.append(arg_typ)

        if name in self.envs[-1]:
            self.error(ctx, "Redefinition of function " + name)
        self.envs[-1][name] = VFunction(args, typ)

    def check_for_return_unknown(self, ctx) -> int:
        if isinstance(ctx, LatteParser.BlockStmtContext):
            return self.check_for_return_block(ctx.block())
        else:
            return self.check_for_return_stmt(ctx)

    # 0 - None, 1 - 1, 2 - both or always
    def check_for_return_stmt(self, ctx: LatteParser.StmtContext) -> int:
        if isinstance(ctx, (LatteParser.VRetContext, LatteParser.RetContext)):
            return 2
        elif isinstance(ctx, LatteParser.CondElseContext):
            stmt1 = ctx.stmt(0)
            stmt2 = ctx.stmt(1)

            if ctx.expr().getText() == 'false':
                return self.check_for_return_unknown(stmt2)

            if ctx.expr().getText() == 'true':
                return self.check_for_return_unknown(stmt1)

            if_val = self.check_for_return_unknown(stmt1)
            else_val = self.check_for_return_unknown(stmt2)

            if_val = max(0, if_val - 1)
            else_val = max(0, else_val - 1)
            ret_val = if_val + else_val

            return ret_val
        elif isinstance(ctx, LatteParser.CondContext) and ctx.expr().getText() == 'true':
            stmt_true = ctx.stmt()

            if self.check_for_return_unknown(stmt_true):
                return 2
        elif isinstance(ctx, LatteParser.WhileContext):
            ret = self.check_for_return_unknown(ctx.stmt())

            if ctx.expr().getText() == 'true' and ret == 1:
                ret = 2

            return ret
        else:
            return 0


    def check_for_return_block(self, ctx: LatteParser.BlockContext) -> int:
        for stmt in reversed(ctx.children):
            if isinstance(stmt, antlr4.TerminalNode):
                continue
            elif isinstance(stmt, LatteParser.StmtContext):
                return self.check_for_return_unknown(stmt)
            else:
                return False

        return False

    def enter_top_def(self, ctx: LatteParser.TopDefContext) -> None:
        self.envs.append({})
        typ = ctx.type_().getText()
        args = ctx.arg()
        block = ctx.block()

        if typ != 'void' and not self.check_for_return_block(block):
            self.error(ctx, "No return statement in every possible branch")

        if args is not None:
            for i in range(len(args.type_())):
                arg_typ = args.type_(i).getText()
                arg_name = args.ID(i).getText()
                arg_val = get_default_value(arg_typ)

                if arg_typ == 'void':
                    self.error(ctx, 'Void cannot be type of an argument')

                if arg_name in self.envs[-1]:
                    self.error(ctx, "Repeated argument name: " + arg_name)

                self.envs[-1][arg_name] = Var(arg_typ, arg_val)

        self.enter_block(block, typ)
        self.envs.pop()

    def enter_block(self, ctx: LatteParser.BlockContext, ret_type) -> None:
        for i, stmt in enumerate(ctx.children):
            if isinstance(stmt, antlr4.TerminalNode):
                continue
            elif isinstance(stmt, LatteParser.StmtContext):
                self.enter_stmt(stmt, ret_type)
            else:
                self.error(ctx, "Unresolved instance in enter_block stmt")

    def enter_ret(self, ctx: LatteParser.RetContext, ret_type) -> None:
        if ret_type == 'void':
            self.error(ctx, "Returning something in void unction")
            
        val = self.enter_expr(ctx.expr())
        if val.type != ret_type:
            self.error(ctx, "Returning wrong type\nExpected " + ret_type + " got " + val.type)

    def enter_vret(self, ctx: LatteParser.VRetContext, ret_type) -> None:
        if ret_type != "void":
            self.error(ctx, "Returning wrong type\nExpected " + ret_type + " got void")

    def enter_decl(self, ctx: LatteParser.DeclContext):
        var_type = ctx.type_().getText()
        default_value = get_default_value(var_type)

        if var_type == 'void':
            self.error(ctx, 'Void cannot be type of an argument')

        for i in range(len(ctx.item())):
            var_item: LatteParser.ItemContext = ctx.item(i)
            var_name = var_item.ID().getText()
            item_expr = var_item.expr()

            if var_name in self.envs[-1]:
                self.error(ctx, "Variable already declared: " + var_name)

            if item_expr is None:
                self.envs[-1][var_name] = Var(var_type, default_value)
            else:
                item_expr_var = self.enter_expr(item_expr)

                if item_expr_var.type == 'int' and item_expr_var.value is not None and\
                        (not -2147483648 <= int(item_expr_var.value) <= 2147483647):
                    self.error(ctx, 'Number too large')

                if var_type != item_expr_var.type:
                    self.error(ctx, "Mismatch in types\nExpected " + var_type + " got " + item_expr_var.type)

                var_value = default_value if item_expr is None else item_expr.getText()

                self.envs[-1][var_name] = Var(var_type, var_value)

    def enter_expr(self, ctx: LatteParser.ExprContext) -> Var:
        if isinstance(ctx, LatteParser.EUnOpContext):
            exp = ctx.expr()
            var_exp = self.enter_expr(exp)

            if ctx.children[0].getText() == '-' and var_exp.type != "int" or \
                    ctx.children[0].getText() == '!' and var_exp.type != "boolean":
                self.error(ctx, "Mismatch in types in unary operator")

            return Var(var_exp.type)
        elif isinstance(ctx, LatteParser.EMulOpContext):
            val_exps = [self.enter_expr(exp) for exp in ctx.expr()]

            for exp in val_exps:
                if exp.type != "int":
                    self.error(ctx, "Multiplied elements aren't all integers")

            return Var('int')
        elif isinstance(ctx, LatteParser.EAddOpContext):
            val_exps = [self.enter_expr(x) for x in ctx.expr()]
            typ = None

            for exp in val_exps:
                if typ is None and exp.type in ["int", "string"]:
                    typ = exp.type
                elif exp.type != typ:
                    self.error(ctx, "Not all elements are of the same type")

            if ctx.addOp().getText() == '-' and typ == 'string':
                self.error(ctx, 'Cannot subtract strings')

            return Var(typ)
        elif isinstance(ctx, LatteParser.ERelOpContext):
            left, right = ctx.expr()

            var_left = self.enter_expr(left)
            var_right = self.enter_expr(right)

            if var_left.type != var_right.type or var_left.type not in ["int", "boolean"]:
                self.error(ctx, "Mismatch in types of comparison")

            return Var('boolean')
        elif isinstance(ctx, LatteParser.EAndContext):
            left, right = ctx.expr()

            var_left = self.enter_expr(left)
            var_right = self.enter_expr(right)

            if var_left.type != var_right.type and var_left.type != 'boolean':
                self.error(ctx, "Mismatch in types of comparison")

            return Var('boolean')
        elif isinstance(ctx, LatteParser.EOrContext):
            left, right = ctx.expr()

            var_left = self.enter_expr(left)
            var_right = self.enter_expr(right)

            if var_left.type != var_right.type and var_left.type != 'boolean':
                self.error(ctx, "Mismatch in types of comparison")

            return Var('boolean')
        elif isinstance(ctx, LatteParser.EIdContext):
            var_name = ctx.getText()
            for env in self.envs[::-1]:
                if var_name in env:
                    return env[var_name]
            self.error(ctx, "Element doesn't exist")
        elif isinstance(ctx, LatteParser.EIntContext):
            return Var('int', ctx.INT().getText())
        elif isinstance(ctx, LatteParser.ETrueContext):
            return Var('boolean', 'true')
        elif isinstance(ctx, LatteParser.EFalseContext):
            return Var('boolean', 'false')
        elif isinstance(ctx, LatteParser.EFunCallContext):
            fun_name = ctx.ID().getText()
            var_list = [self.enter_expr(x) for x in ctx.expr()]
            fun_type = [x.type for x in var_list]
            fun = None

            for env in self.envs[::-1]:
                if fun_name in env:
                    if env[fun_name].type == fun_type:
                        fun = env[fun_name]
                        break

            if fun is None:
                self.error(ctx, "Not found function with given types of attributes")
            else:
                return Var(fun.res_type)
        elif isinstance(ctx, LatteParser.EStrContext):
            return Var('string', ctx.STR().getText())
        elif isinstance(ctx, LatteParser.EParenContext):
            return self.enter_expr(ctx.expr())
        else:
            self.error(ctx, "Unresolved instance in enter_expr")

    def enter_while(self, ctx: LatteParser.WhileContext, ret_type) -> None:
        condition = ctx.expr()
        condition_var = self.enter_expr(condition)

        if condition_var.type != 'boolean':
            self.error(ctx, "Condition doesn't have type boolean")

        if condition_var.value == 'true' and isinstance(ctx.stmt(), LatteParser.DeclContext):
            self.error(ctx, 'Cannot declare variable here')

        self.envs.append({})
        self.enter_stmt(ctx.stmt(), ret_type)
        self.envs.pop()

    def enter_ass(self, ctx: LatteParser.AssContext) -> None:
        var_name = ctx.ID().getText()
        exp = ctx.expr()

        val_exp = self.enter_expr(exp)

        for env in self.envs[::-1]:
            if var_name in env:
                if env[var_name].type != val_exp.type:
                    self.error(ctx, "Incorrect type of assignment\nExpected " + env[var_name].type + " got " + val_exp.type)
                else:
                    return

        self.error(ctx, "Variable not declared: " + var_name)

    def enter_incr(self, ctx: LatteParser.IncrContext) -> None:
        var_name = ctx.ID().getText()

        for env in self.envs[::-1]:
            if var_name in env:
                if env[var_name].type != 'int':
                    self.error(ctx, "Incorrect type\nExpected " + env[var_name].type + " got int")
                else:
                    return

    def enter_decr(self, ctx: LatteParser.DecrContext) -> None:
        var_name = ctx.ID().getText()

        for env in self.envs[::-1]:
            if var_name in env:
                if env[var_name].type != 'int':
                    self.error(ctx, "Incorrect type\nExpected " + env[var_name].type + " got int")
                else:
                    return

    def enter_cond(self, ctx: LatteParser.CondContext, ret_type) -> None:
        exp = ctx.expr()
        exp_val = self.enter_expr(exp)

        if exp_val.type != "boolean":
            self.error(ctx, "Expression isn't of type boolean")

        if exp_val.value == 'false':
            return

        if isinstance(ctx.stmt(), LatteParser.DeclContext):
            self.error(ctx, 'Cannot declare variable here')

        self.envs.append({})
        self.enter_stmt(ctx.stmt(), ret_type)
        self.envs.pop()

    def enter_cond_else(self, ctx: LatteParser.CondElseContext, ret_type) -> None:
        exp = ctx.expr()
        exp_val = self.enter_expr(exp)

        if exp_val.type != "boolean":
            self.error(ctx, "Expression isn't of type boolean")

        if exp_val.value == 'true' and isinstance(ctx.stmt(0), LatteParser.DeclContext):
            self.error(ctx, 'Cannot declare variable here')

        if exp_val.value == 'false' and isinstance(ctx.stmt(1), LatteParser.DeclContext):
            self.error(ctx, 'Cannot declare variable here')

        for i in range(2):
            self.envs.append({})
            self.enter_stmt(ctx.stmt(i), ret_type)
            self.envs.pop()

    def enter_stmt(self, ctx: LatteParser.StmtContext, ret_type):
        if isinstance(ctx, LatteParser.BlockStmtContext):
            self.envs.append({})
            self.enter_block(ctx.block(), ret_type)
            self.envs.pop()
        elif isinstance(ctx, LatteParser.DeclContext):
            self.enter_decl(ctx)
        elif isinstance(ctx, LatteParser.AssContext):
            self.enter_ass(ctx)
        elif isinstance(ctx, LatteParser.IncrContext):
            self.enter_incr(ctx)
        elif isinstance(ctx, LatteParser.DecrContext):
            self.enter_decr(ctx)
        elif isinstance(ctx, LatteParser.RetContext):
            self.enter_ret(ctx, ret_type)
        elif isinstance(ctx, LatteParser.VRetContext):
            self.enter_vret(ctx, ret_type)
        elif isinstance(ctx, LatteParser.CondContext):
            self.enter_cond(ctx, ret_type)
        elif isinstance(ctx, LatteParser.CondElseContext):
            self.enter_cond_else(ctx, ret_type)
        elif isinstance(ctx, LatteParser.WhileContext):
            self.enter_while(ctx, ret_type)
        elif isinstance(ctx, LatteParser.SExpContext):
            self.enter_expr(ctx.expr())
        elif isinstance(ctx, LatteParser.EmptyContext):
            return
        else:
            self.error(ctx, "Unresolved instance in enter_block StmtContext")

