from typing import List

import antlr4
import sys
from antlr.LatteParser import LatteParser
from utils import *


class Code4:
    def __init__(self, DEBUG):
        self.envs = [{}]
        self.DEBUG = DEBUG

    def debug(self, msg) -> None:
        if self.DEBUG:
            sys.stderr.write(msg)

    def error(self, ctx: antlr4.ParserRuleContext, msg) -> None:
        sys.stderr.write("ERROR\n")
        sys.stderr.write("\033[91m" + "Code4 error at " + str(ctx.start.line) + ":" + str(ctx.start.column) + "\033[0m\n")
        sys.stderr.write(msg + '\n')
        sys.exit(1)

    def add_bultin(self) -> None:
        self.envs[0]['printInt'] = VFunction('int', 'void')
        self.envs[0]['readInt'] = VFunction('', 'int')
        self.envs[0]['printString'] = VFunction('string', 'void')
        self.envs[0]['readString'] = VFunction('', 'string')
        self.envs[0]['error'] = VFunction('', 'void')

    def enter_program(self, ctx: LatteParser.ProgramContext) -> List[Block]:
        self.add_bultin()
        res = []

        for topDef in ctx.children:
            if isinstance(topDef, LatteParser.TopDefContext):
                self.add_definition(topDef)

        for topDef in ctx.children:
            if isinstance(topDef, LatteParser.TopDefContext):
                res.append(self.enter_top_def(topDef))

        return res

    def add_definition(self, ctx: LatteParser.TopDefContext) -> None:
        typ = ctx.type_().getText()
        name = ctx.ID().getText()
        arguments: LatteParser.ArgContext = ctx.arg()
        args = []

        if arguments is None:
            self.envs[-1][name] = VFunction('', typ)
            return

        for i in range(len(arguments.type_())):
            arg_typ = arguments.type_(i).getText()
            args.append(arg_typ)

        args_str = ' -> '.join(args)

        self.envs[-1][name] = VFunction(args_str, typ)

    def enter_top_def(self, ctx: LatteParser.TopDefContext) -> Block:
        self.envs.append({})
        name = ctx.ID().getText()
        args = ctx.arg()
        ctx_block = ctx.block()
        block = Block(name)

        block.add_quad(QFunBegin(name))

        if args is not None:
            for i, arg in enumerate(args.type_()):
                arg_typ = arg.getText()
                arg_name = arg.getText()

                if i < 6:
                    loc = registers[i]
                else:
                    loc = '{}(%rbp)'.format(8 + 4 * (i - 6))

                self.envs[-1][arg_name] = Var(arg_typ, loc=loc)

        block = self.enter_block(ctx_block, block)

        block.total_count += block.var_counter
        block.quads[0] = QFunBegin(name, block.total_count)
        block.add_quad(QFunEnd(name))
        self.envs.pop()

        return block

    def enter_block(self, ctx: LatteParser.BlockContext, block) -> Block:
        for stmt in ctx.children:
            if isinstance(stmt, antlr4.TerminalNode):
                continue
            elif isinstance(stmt, LatteParser.StmtContext):
                block = self.enter_stmt(stmt, block)
            else:
                self.error(ctx, "Unresolved instance in enter_block stmt")
        block.add_quad(QEmpty())

        return block

    def enter_ret(self, ctx: LatteParser.RetContext, block) -> Block:
        val, block = self.enter_expr(ctx.expr(), block)

        block.add_quad(QReturn(val.loc))

        return block

    # def enter_vret(self, ctx: LatteParser.VRetContext, name, counter) -> int:
    #     self.code.append('ret')
    #
    #     return counter


    # def enter_decl(self, ctx: LatteParser.DeclContext, name, counter) -> int:
    #     var_type = ctx.type_().getText()
    #     default_value = get_default_value(var_type)
    #
    #     for i in range(len(ctx.item())):
    #         var_item: LatteParser.ItemContext = ctx.item(i)
    #         var_name = var_item.ID().getText()
    #         item_expr = var_item.expr()
    #         var_loc = '{}_{}'.format(name, var_name)
    #
    #         if item_expr is None:
    #             var_value = Var(var_type, default_value, loc=default_value)
    #         else:
    #             var_value, counter = self.enter_expr(item_expr, name, counter)
    #
    #         self.envs[-1][var_name] = Var(var_type, var_value.value, loc=var_loc)
    #         self.code.append('{} = {}'.format(var_loc, var_value.loc))
    #
    #     return counter
    #
    def enter_expr(self, ctx: LatteParser.ExprContext, block) -> (Var, Block):
    #     if isinstance(ctx, LatteParser.EUnOpContext):
    #         exp = ctx.expr()
    #         var_exp, counter_tmp = self.enter_expr(exp, name, counter)
    #         counter = counter_tmp
    #
    #         if ctx.children[0].getText() == '-':
    #             self.code.append('neg ' + var_exp.loc)
    #         else:
    #             self.code.append('xor ' + var_exp.loc)
    #
    #         return var_exp, counter
    #     elif isinstance(ctx, LatteParser.EMulOpContext):
    #         val_exps: List[Var] = []
    #         for x in ctx.expr():
    #             var, counter_tmp = self.enter_expr(x, name, counter)
    #             counter = counter_tmp
    #             val_exps.append(var)
    #
    #         var_name = name + '_t{}'.format(counter)
    #
    #         if ctx.mulOp().getText() == '*':
    #             op = 'mul'
    #         else:
    #             op = 'div'
    #
    #         self.code.append('{} {} {}'.format(op, val_exps[0].loc, val_exps[1].loc))
    #         self.code.append(var_name + ' = eax')
    #         counter += 1
    #
    #         return Var('int', loc=var_name), counter
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
        #             return env[var_name], counter
        if isinstance(ctx, LatteParser.EIntContext):
            var_name = block.give_var_name()
            quad = QEq(var_name, ctx.INT().getText())

            block.add_quad(quad)
            return VInt(ctx.INT().getText(), loc=var_name), block
        # elif isinstance(ctx, LatteParser.ETrueContext):
        #     return Var('boolean', 'true')
        # elif isinstance(ctx, LatteParser.EFalseContext):
        #     return Var('boolean', 'false')
        elif isinstance(ctx, LatteParser.EFunCallContext):
            fun_name = ctx.ID().getText()
            res_name = block.give_var_name()

            var_list = []
            for x in ctx.expr():
                var, counter = self.enter_expr(x, block)
                var_list.append(var)

            var_types = [x.type for x in var_list]
            var_type = ' -> '.join(var_types)
            fun = None

            for env in self.envs[::-1]:
                if fun_name in env:
                    if env[fun_name].type == var_type:
                        fun = env[fun_name]
                        break

            block.add_quad(QFunCall(fun_name, res_name, [x.loc for x in var_list]))

            return Var(fun.res_type, loc=res_name), block
        # elif isinstance(ctx, LatteParser.EStrContext):
        #     return Var('string', ctx.STR().getText())
        # elif isinstance(ctx, LatteParser.EParenContext):
        #     return self.enter_expr(ctx.expr())
        # else:
        #     self.error(ctx, "Unresolved instance in enter_expr")

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
    # def enter_ass(self, ctx: LatteParser.AssContext, name, counter) -> None:
    #     var_name = ctx.ID().getText()
    #     exp = ctx.expr()
    #
    #     val_exp, coutner = self.enter_expr(exp, name, counter)
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
    def enter_stmt(self, ctx: LatteParser.StmtContext, block) -> Block:
        self.debug(ctx.getText() + "\n")
        if isinstance(ctx, LatteParser.BlockStmtContext):
            self.envs.append({})

            name = block.give_block_name()
            block.add_inside(self.enter_block(ctx.block, Block(name)))

            self.envs.pop()
            return block
        # elif isinstance(ctx, LatteParser.DeclContext):
        #     return self.enter_decl(ctx, name, counter), block_counter
        # elif isinstance(ctx, LatteParser.AssContext):
        #     self.enter_ass(ctx, name, counter)
        # elif isinstance(ctx, LatteParser.IncrContext):
        #     self.enter_incr(ctx)
        # elif isinstance(ctx, LatteParser.DecrContext):
        #     self.enter_decr(ctx)
        elif isinstance(ctx, LatteParser.RetContext):
            return self.enter_ret(ctx, block)
        # elif isinstance(ctx, LatteParser.VRetContext):
        #     return self.enter_vret(ctx, name, counter), block_counter
        # elif isinstance(ctx, LatteParser.CondContext):
        #     self.enter_cond(ctx, ret_type)
        # elif isinstance(ctx, LatteParser.CondElseContext):
        #     self.enter_cond_else(ctx, ret_type)
        # elif isinstance(ctx, LatteParser.WhileContext):
        #     self.enter_while(ctx, ret_type)
        elif isinstance(ctx, LatteParser.SExpContext):
            _, block = self.enter_expr(ctx.expr(), block)
            return block
        elif isinstance(ctx, LatteParser.EmptyContext):
            return block
        else:
            self.error(ctx, "Unresolved instance in enter_block StmtContext")

