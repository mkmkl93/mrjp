from typing import List

import antlr4
import sys
from antlr.LatteParser import LatteParser
from utils import Var, get_default_value, registers


class Code4:
    def __init__(self, DEBUG):
        self.envs = [{}]
        self.DEBUG = DEBUG
        self.code = []

    def debug(self, msg) -> None:
        if self.DEBUG == True:
            sys.stderr.write(msg)

    def add_bultin(self) -> None:
        self.envs[0]['printInt'] = Var('int', None, 'void')
        self.envs[0]['readInt'] = Var('', None, 'int')
        self.envs[0]['printString'] = Var('string', None, 'void')
        self.envs[0]['readString'] = Var('', None, 'string')
        self.envs[0]['error'] = Var('', None, 'void')

    def enter_program(self, ctx: LatteParser.ProgramContext) -> None:
        self.add_bultin()

        for topDef in ctx.children:
            if isinstance(topDef, LatteParser.TopDefContext):
                self.enter_top_def(topDef)

    def enter_top_def(self, ctx: LatteParser.TopDefContext) -> None:
        self.envs.append({})
        name = ctx.ID().getText()
        args = ctx.arg()
        block = ctx.block()

        if args is not None:
            for i in range(len(args.type_())):
                arg_typ = args.type_(i).getText()
                arg_name = args.ID(i).getText()
                arg_val = get_default_value(arg_typ)

                self.envs[-1][arg_name] = Var(arg_typ, arg_val)

        self.enter_block(block, name, 0)
        self.envs.pop()

    def enter_block(self, ctx: LatteParser.BlockContext, name, counter) -> None:
        self.code.append(name + '::')
        for stmt in ctx.children:
            if isinstance(stmt, antlr4.TerminalNode):
                continue
            elif isinstance(stmt, LatteParser.StmtContext):
                counter += self.enter_stmt(stmt, name, counter)
            else:
                self.error(ctx, "Unresolved instance in enter_block stmt")
        self.code.append('')

    def enter_ret(self, ctx: LatteParser.RetContext, name, counter) -> int:
        val, tmp = self.enter_expr(ctx.expr(), name, counter)
        counter = tmp

        self.code.append('eax = ' + val.loc)
        self.code.append('ret')

        return counter

    # def enter_vret(self, ctx: LatteParser.VRetContext, ret_type) -> None:
    #     if ret_type != "void":
    #         self.error(ctx, "Returning wrong type\nExpected " + ret_type + " got void")
    #
    # def enter_decl(self, ctx: LatteParser.DeclContext):
    #     var_type = ctx.type_().getText()
    #     default_value = get_default_value(var_type)
    #
    #     if var_type == 'void':
    #         self.error(ctx, 'Void cannot be type of an argument')
    #
    #     for i in range(len(ctx.item())):
    #         var_item: LatteParser.ItemContext = ctx.item(i)
    #         var_name = var_item.ID().getText()
    #         item_expr = var_item.expr()
    #
    #         if var_name in self.envs[-1]:
    #             self.error(ctx, "Variable already declared: " + var_name)
    #
    #         if item_expr is None:
    #             self.envs[-1][var_name] = Var(var_type, default_value)
    #         else:
    #             item_expr_var = self.enter_expr(item_expr)
    #
    #             if item_expr_var.type == 'int' and item_expr_var.value is not None and \
    #                     (not -2147483648 <= int(item_expr_var.value) <= 2147483647):
    #                 self.error(ctx, 'Number too large')
    #
    #             if var_type != item_expr_var.type:
    #                 self.error(ctx, "Mismatch in types\nExpected " + var_type + " got " + item_expr_var.type)
    #
    #             var_value = default_value if item_expr is None else item_expr.getText()
    #
    #             self.envs[-1][var_name] = Var(var_type, var_value)

    def enter_expr(self, ctx: LatteParser.ExprContext, name, counter) -> (Var, int):
        if isinstance(ctx, LatteParser.EUnOpContext):
            exp = ctx.expr()
            var_exp, counter_tmp = self.enter_expr(exp, name, counter)
            counter = counter_tmp

            if ctx.children[0].getText() == '-':
                self.code.append('neg ' + var_exp.loc)
            else:
                self.code.append('xor ' + var_exp.loc)

            return var_exp, counter
        elif isinstance(ctx, LatteParser.EMulOpContext):
            val_exps: List[Var] = []
            for x in ctx.expr():
                var, counter_tmp = self.enter_expr(x, name, counter)
                counter = counter_tmp
                val_exps.append(var)

            var_name = name + '_t{}'.format(counter)
            self.code.append('mul ' + val_exps[0].loc + ' ' + val_exps[1].loc)
            self.code.append(var_name + ' = eax')
            counter += 1

            return Var('int', loc=var_name), counter
        # elif isinstance(ctx, LatteParser.EAddOpContext):
        #     val_exps = [self.enter_expr(x) for x in ctx.expr()]
        #     typ = None
        #
        #     for exp in val_exps:
        #         if typ is None and exp.type in ["int", "string"]:
        #             typ = exp.type
        #         elif exp.type != typ:
        #             self.error(ctx, "Not all elements are of the same type")
        #
        #     if ctx.addOp().getText() == '-' and typ == 'string':
        #         self.error(ctx, 'Cannot subtract strings')
        #
        #     return Var(typ)
        # elif isinstance(ctx, LatteParser.ERelOpContext):
        #     left, right = ctx.expr()
        #
        #     var_left = self.enter_expr(left)
        #     var_right = self.enter_expr(right)
        #
        #     if var_left.type != var_right.type or var_left.type not in ["int", "boolean"]:
        #         self.error(ctx, "Mismatch in types of comparison")
        #
        #     return Var('boolean')
        # elif isinstance(ctx, LatteParser.EAndContext):
        #     left, right = ctx.expr()
        #
        #     var_left = self.enter_expr(left)
        #     var_right = self.enter_expr(right)
        #
        #     if var_left.type != var_right.type and var_left.type != 'boolean':
        #         self.error(ctx, "Mismatch in types of comparison")
        #
        #     return Var('boolean')
        # elif isinstance(ctx, LatteParser.EOrContext):
        #     left, right = ctx.expr()
        #
        #     var_left = self.enter_expr(left)
        #     var_right = self.enter_expr(right)
        #
        #     if var_left.type != var_right.type and var_left.type != 'boolean':
        #         self.error(ctx, "Mismatch in types of comparison")
        #
        #     return Var('boolean')
        # elif isinstance(ctx, LatteParser.EIdContext):
        #     var_name = ctx.getText()
        #     for env in self.envs[::-1]:
        #         if var_name in env:
        #             return env[var_name]
        #     self.error(ctx, "Element doesn't exist")
        elif isinstance(ctx, LatteParser.EIntContext):
            var_name = name + '_t{}'.format(counter)
            self.code.append(var_name + ' = ' + ctx.INT().getText())
            counter += 1
            return Var('int', ctx.INT().getText(), loc=var_name), counter
        # elif isinstance(ctx, LatteParser.ETrueContext):
        #     return Var('boolean', 'true')
        # elif isinstance(ctx, LatteParser.EFalseContext):
        #     return Var('boolean', 'false')
        elif isinstance(ctx, LatteParser.EFunCallContext):
            fun_name = ctx.ID().getText()

            var_list = []
            for x in ctx.expr():
                var, counter_tmp = self.enter_expr(x, name, counter)
                counter = counter_tmp
                var_list.append(var)

            var_types = [x.type for x in var_list]
            var_type = ' -> '.join(var_types)
            fun = None

            for env in self.envs[::-1]:
                if fun_name in env:
                    if env[fun_name].type == var_type:
                        fun = env[fun_name]
                        break

            for var in var_list[:6:-1]:
                self.code.append('push ' + var.loc)

            for var, reg in zip(var_list[:5:], registers):
                self.code.append('{} = {}'.format(reg, var.loc))

            self.code.append('push rbp')
            self.code.append('call ' + fun_name)
            var_name = name + '_t{}'.format(counter)

            if fun.res_type != 'void':
                self.code.append(var_name + ' = eax')
            counter += 1

            return Var(fun.res_type), counter
        # elif isinstance(ctx, LatteParser.EStrContext):
        #     return Var('string', ctx.STR().getText())
        # elif isinstance(ctx, LatteParser.EParenContext):
        #     return self.enter_expr(ctx.expr())
        else:
            self.error(ctx, "Unresolved instance in enter_expr")

    # def enter_while(self, ctx: LatteParser.WhileContext, ret_type) -> None:
    #     condition = ctx.expr()
    #     condition_var = self.enter_expr(condition)
    #
    #     if condition_var.type != 'boolean':
    #         self.error(ctx, "Condition doesn't have type boolean")
    #
    #     if condition_var.value == 'true' and isinstance(ctx.stmt(), LatteParser.DeclContext):
    #         self.error(ctx, 'Cannot declare variable here')
    #
    #     self.envs.append({})
    #     self.enter_stmt(ctx.stmt(), ret_type)
    #     self.envs.pop()
    #
    # def enter_ass(self, ctx: LatteParser.AssContext) -> None:
    #     var_name = ctx.ID().getText()
    #     exp = ctx.expr()
    #
    #     val_exp = self.enter_expr(exp)
    #
    #     for env in self.envs[::-1]:
    #         if var_name in env:
    #             if env[var_name].type != val_exp.type:
    #                 self.error(ctx,
    #                            "Incorrect type of assignment\nExpected " + env[var_name].type + " got " + val_exp.type)
    #             else:
    #                 return
    #
    #     self.error(ctx, "Variable not declared: " + var_name)
    #
    # def enter_incr(self, ctx: LatteParser.IncrContext) -> None:
    #     var_name = ctx.ID().getText()
    #
    #     for env in self.envs[::-1]:
    #         if var_name in env:
    #             if env[var_name].type != 'int':
    #                 self.error(ctx, "Incorrect type\nExpected " + env[var_name].type + " got int")
    #             else:
    #                 return
    #
    # def enter_decr(self, ctx: LatteParser.DecrContext) -> None:
    #     var_name = ctx.ID().getText()
    #
    #     for env in self.envs[::-1]:
    #         if var_name in env:
    #             if env[var_name].type != 'int':
    #                 self.error(ctx, "Incorrect type\nExpected " + env[var_name].type + " got int")
    #             else:
    #                 return
    #
    # def enter_cond(self, ctx: LatteParser.CondContext, ret_type) -> None:
    #     exp = ctx.expr()
    #     exp_val = self.enter_expr(exp)
    #
    #     if exp_val.type != "boolean":
    #         self.error(ctx, "Expression isn't of type boolean")
    #
    #     if exp_val.value == 'false':
    #         return
    #
    #     if exp_val.value == 'true' and isinstance(ctx.stmt(), LatteParser.DeclContext):
    #         self.error(ctx, 'Cannot declare variable here')
    #
    #     self.envs.append({})
    #     self.enter_stmt(ctx.stmt(), ret_type)
    #     self.envs.pop()
    #
    # def enter_cond_else(self, ctx: LatteParser.CondElseContext, ret_type) -> None:
    #     exp = ctx.expr()
    #     exp_val = self.enter_expr(exp)
    #
    #     if exp_val.type != "boolean":
    #         self.error(ctx, "Expression isn't of type boolean")
    #
    #     if exp_val.value == 'true' and isinstance(ctx.stmt(0), LatteParser.DeclContext):
    #         self.error(ctx, 'Cannot declare variable here')
    #
    #     if exp_val.value == 'false' and isinstance(ctx.stmt(1), LatteParser.DeclContext):
    #         self.error(ctx, 'Cannot declare variable here')
    #
    #     for i in range(2):
    #         self.envs.append({})
    #         self.enter_stmt(ctx.stmt(i), ret_type)
    #         self.envs.pop()
    #
    def enter_stmt(self, ctx: LatteParser.StmtContext, name, counter) -> int:
        self.debug(ctx.getText() + "\n")
        # if isinstance(ctx, LatteParser.BlockStmtContext):
        #     self.envs.append({})
        #     ret = self.enter_block(ctx.block(), name, counter)
        #     self.envs.pop()
        #     return ret
        # elif isinstance(ctx, LatteParser.DeclContext):
        #     self.enter_decl(ctx)
        # elif isinstance(ctx, LatteParser.AssContext):
        #     self.enter_ass(ctx)
        # elif isinstance(ctx, LatteParser.IncrContext):
        #     self.enter_incr(ctx)
        # elif isinstance(ctx, LatteParser.DecrContext):
        #     self.enter_decr(ctx)
        if isinstance(ctx, LatteParser.RetContext):
            return self.enter_ret(ctx, name, counter)
        # elif isinstance(ctx, LatteParser.VRetContext):
        #     self.enter_vret(ctx, ret_type)
        # elif isinstance(ctx, LatteParser.CondContext):
        #     self.enter_cond(ctx, ret_type)
        # elif isinstance(ctx, LatteParser.CondElseContext):
        #     self.enter_cond_else(ctx, ret_type)
        # elif isinstance(ctx, LatteParser.WhileContext):
        #     self.enter_while(ctx, ret_type)
        elif isinstance(ctx, LatteParser.SExpContext):
            _, ret = self.enter_expr(ctx.expr(), name, counter)
            return ret
        elif isinstance(ctx, LatteParser.EmptyContext):
            return
        else:
            self.error(ctx, "Unresolved instance in enter_block StmtContext")

