import antlr4
import sys
from antlr.LatteLexer import LatteLexer
from antlr.LatteParser import LatteParser
from enum import Enum

def error(ctx, msg) -> None:
    sys.stderr.write("ERROR\n")
    sys.stderr.write(msg + "\n")
    sys.exit(1)


class Var:
    def __init__(self, typ=None, value=None, res_type=None):
        self.type = typ
        self.value = value
        self.res_type = res_type

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


class Compiler:
    def __init__(self):
        self.envs = [{}]

    def add_bultin(self) -> None:
        self.envs[0]['printInt'] = Var('[int]', None, 'void')
        self.envs[0]['readInt'] = Var('[]', None, 'int')
        self.envs[0]['printString'] = Var('[string]', None, 'void')
        self.envs[0]['readString'] = Var('[]', None, 'string')

    def enter_program(self, ctx: LatteParser.ProgramContext) -> None:
        self.add_bultin()

        for topDef in ctx.children:
            if isinstance(topDef, LatteParser.TopDefContext):
                self.add_definition(topDef)

        for topDef in ctx.children:
            if isinstance(topDef, LatteParser.TopDefContext):
                self.enter_top_def(topDef)

    def add_definition(self, ctx: LatteParser.TopDefContext) -> None:
        typ = ctx.type_().getText()
        name = ctx.ID().getText()
        arguments: LatteParser.DeclContext = ctx.arg()
        args = []

        if arguments is None:
            self.envs[-1][name] = Var('[]', None, typ)
            return

        for i in range(len(arguments.type_())):
            arg_typ = arguments.type_(i).getText()
            args.append(arg_typ)

        args_str = '[' + ', '.join(args) + ']'
        self.envs[-1][name] = Var(args_str, None, typ)

    def enter_top_def(self, ctx: LatteParser.TopDefContext) -> None:
        self.envs.append({})
        typ = ctx.type_().getText()
        name = ctx.ID().getText()
        args = ctx.arg()
        block = ctx.block()

        print(typ, name, args, block)
        if args is not None:
            for i in range(len(args.type_())):
                arg_typ = args.type_(i).getText()
                arg_name = args.ID(i).getText()
                arg_val = get_default_value(arg_typ)

                self.envs[-1][arg_name] = Var(arg_typ, arg_val)
        self.enter_block(block, typ)
        self.envs.pop()

    def enter_block(self, ctx: LatteParser.BlockContext, ret_type) -> None:
        for stmt in ctx.children:
            if isinstance(stmt, antlr4.TerminalNode):
                continue
            elif isinstance(stmt, LatteParser.StmtContext):
                self.enter_stmt(stmt, ret_type)
            else:
                error(ctx, "Unresolved instance in enter_block stmt")

    def enter_ret(self, ctx: LatteParser.RetContext, ret_type) -> None:
        val = self.enter_expr(ctx.expr())
        if val.type != ret_type:
            error(ctx, "Returning wrong type")

    def enter_vret(self, ctx: LatteParser.VRetContext, ret_type) -> None:
        if ret_type != "void":
            error(ctx, "Returning wrong type")

    def enter_decl(self, ctx: LatteParser.DeclContext):
        var_type = ctx.type_().getText()
        default_value = get_default_value(var_type)

        for i in range(len(ctx.item())):
            var_item: LatteParser.ItemContext = ctx.item(i)
            var_name = var_item.ID().getText()
            item_expr = var_item.expr()

            if item_expr is None:
                self.envs[-1][var_name] = Var(var_type, default_value)
            else:
                item_expr_var = self.enter_expr(item_expr)

                if item_expr_var.type != var_type:
                    error(ctx, "Mismatch in types")

                var_value = default_value if item_expr is None else item_expr.getText()

                self.envs[-1][var_name] = Var(var_type, var_value)

    def enter_expr(self, ctx: LatteParser.ExprContext) -> Var:
        if isinstance(ctx, LatteParser.EUnOpContext):
            exp = ctx.expr()
            var_exp = self.enter_expr(exp)

            if var_exp.type not in ["boolean", "int"]:
                error(ctx, "Mismatch in types in unary operator")

            return Var(var_exp.type)
        elif isinstance(ctx, LatteParser.EMulOpContext):
            val_exps = [self.enter_expr(exp) for exp in ctx.expr()]

            for exp in val_exps:
                if exp.type != "int":
                    error(ctx, "Multiplied elements aren't all integers")

            return Var('int')
        elif isinstance(ctx, LatteParser.EAddOpContext):
            val_exps = [self.enter_expr(x) for x in ctx.expr()]
            typ = None

            for exp in val_exps:
                if typ is None and exp.type in ["int", "string"]:
                    typ = exp.type
                elif exp.type != typ:
                    error(ctx, "Not all elements are of the same type")

            return Var(typ)
        elif isinstance(ctx, LatteParser.ERelOpContext):
            left, right = ctx.expr()

            var_left = self.enter_expr(left)
            var_right = self.enter_expr(right)

            if var_left.type != var_right.type or var_left.type not in ["int", "boolean"]:
                error(ctx, "Mismatch in types in comparison")

            return Var('boolean')
        elif isinstance(ctx, LatteParser.EAndContext):
            left, right = ctx.expr()

            var_left = self.enter_expr(left)
            var_right = self.enter_expr(right)

            if var_left.type != var_right.type and var_left.type != 'boolean':
                error(ctx, "Mismatch in types in comparison")

            return Var('boolean')
        elif isinstance(ctx, LatteParser.EOrContext):
            left, right = ctx.expr()

            var_left = self.enter_expr(left)
            var_right = self.enter_expr(right)

            if var_left.type != var_right.type and var_left.type != 'boolean':
                error(ctx, "Mismatch in types in comparison")

            return Var('boolean')
        elif isinstance(ctx, LatteParser.EIdContext):
            var_name = ctx.getText()
            for env in self.envs[::-1]:
                if var_name in env:
                    return env[var_name]
            error(ctx, "Element doesn't exist")
        elif isinstance(ctx, LatteParser.EIntContext):
            return Var('int', ctx.INT().getText())
        elif isinstance(ctx, LatteParser.ETrueContext):
            return Var('boolean', 'True')
        elif isinstance(ctx, LatteParser.EFalseContext):
            return Var('boolean', 'False')
        elif isinstance(ctx, LatteParser.EFunCallContext):
            fun_name = ctx.ID().getText()
            var_list = [self.enter_expr(x) for x in ctx.expr()]
            var_types = [x.type for x in var_list]
            var_type = '[' + ', '.join(var_types) + ']'
            fun = None

            for env in self.envs[::-1]:
                if fun_name in env:
                    if env[fun_name].type == var_type:
                        fun = env[fun_name]
                        break

            if fun is None:
                error(ctx, "Not found function with given types of attributes")
            else:
                return Var(fun.res_type)
        elif isinstance(ctx, LatteParser.EStrContext):
            return Var('string', ctx.STR().getText())
        elif isinstance(ctx, LatteParser.EParenContext):
            return self.enter_expr(ctx.expr())
        else:
            error(ctx, "Unresolved instance in enter_expr")

    def enter_while(self, ctx: LatteParser.WhileContext, ret_type) -> None:
        condition = ctx.expr()
        condition_var = self.enter_expr(condition)

        if condition_var.type != 'boolean':
            error(ctx, "Condition doesn't have type boolean")

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
                    error(ctx, "Incorrect type of assignment")
                else:
                    return

        error(ctx, "Variable doesn't exist")

    def enter_incr(self, ctx: LatteParser.IncrContext) -> None:
        var_name = ctx.ID().getText()

        for env in self.envs[::-1]:
            if var_name in env:
                if env[var_name].type != 'int':
                    error(ctx, "Incorrect type")
                else:
                    return

    def enter_decr(self, ctx: LatteParser.DecrContext) -> None:
        var_name = ctx.ID().getText()

        for env in self.envs[::-1]:
            if var_name in env:
                if env[var_name].type != 'int':
                    error(ctx, "Incorrect type")
                else:
                    return

    def enter_cond(self, ctx: LatteParser.CondContext, ret_type) -> None:
        exp = ctx.expr()
        exp_val = self.enter_expr(exp)

        if exp_val.type != "boolean":
            error(ctx, "Expression isn't of type boolean")

        self.envs.append({})
        self.enter_stmt(ctx.stmt(), ret_type)
        self.envs.pop()

    def enter_cond_else(self, ctx: LatteParser.CondElseContext, ret_type) -> None:
        exp = ctx.expr();
        exp_val = self.enter_expr(exp)

        if exp_val.type != "boolean":
            error(ctx, "Expression isn't of type boolean")

        for i in range(2):
            self.envs.append({})
            self.enter_stmt(ctx.stmt(i), ret_type)
            self.envs.pop()

    def enter_stmt(self, ctx: LatteParser.StmtContext, ret_type):
        sys.stderr.write(ctx.getText() + "\n")
        if isinstance(ctx, LatteParser.BlockStmtContext):
            self.enter_block(ctx.block(), ret_type)
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
        else:
            error(ctx, "Unresolved instance in enter_block StmtContext")






