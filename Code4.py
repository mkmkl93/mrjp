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
        self.envs[0]['printInt'] = VFunction(['int'], 'void')
        self.envs[0]['readInt'] = VFunction([], 'int')
        self.envs[0]['printString'] = VFunction(['string'], 'void')
        self.envs[0]['readString'] = VFunction([], 'string')
        self.envs[0]['error'] = VFunction([], 'void')

    def enter_program(self, ctx: LatteParser.ProgramContext) -> List[Block]:
        self.add_bultin()
        res: List[Block] = []

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
            self.envs[-1][name] = VFunction([], typ)
            return

        for i in range(len(arguments.type_())):
            arg_typ = arguments.type_(i).getText()
            args.append(arg_typ)

        self.envs[-1][name] = VFunction(args, typ)

    def enter_top_def(self, ctx: LatteParser.TopDefContext) -> Block:
        self.envs.append({})
        name = ctx.ID().getText()
        args = ctx.arg()
        ctx_block = ctx.block()
        block = SmallBlock(name)

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

        block.limit_locals(block.var_counter)
        block.add_quad(QFunEnd(name))
        self.envs.pop()

        return block

    def enter_block(self, ctx: LatteParser.BlockContext, block) -> Block:
        for stmt in ctx.children:
            if isinstance(stmt, antlr4.TerminalNode):
                continue
            elif isinstance(stmt, LatteParser.StmtContext):
                block = self.enter_stmt(stmt, block)
            elif isinstance(stmt, LatteParser.BlockContext):
                block = self.enter_block(stmt, block)
            else:
                self.error(ctx, "Unresolved instance in enter_block stmt")

        if isinstance(block, SmallBlock) and block.quads != [] and not isinstance(block.quads[-1], QEmpty):
            block.add_quad(QEmpty())

        return block

    def enter_ret(self, ctx: LatteParser.RetContext, block) -> Block:
        val, block = self.enter_expr(ctx.expr(), block)

        block.add_quad(QReturn(val.loc))

        return block

    def enter_vret(self, ctx: LatteParser.VRetContext, block) -> Block:
        block.add_quad(QReturn())

        return block

    def enter_decl(self, ctx: LatteParser.DeclContext, block) -> Block:
        var_type = ctx.type_().getText()
        default_value = get_default_value(var_type)

        for i in range(len(ctx.item())):
            var_item: LatteParser.ItemContext = ctx.item(i)
            var_name = var_item.ID().getText()
            item_expr = var_item.expr()
            var_loc = block.give_var_name()

            if item_expr is None:
                var_value = Var(var_type, default_value, loc=default_value)
            else:
                var_value, counter = self.enter_expr(item_expr, block)

            self.envs[-1][var_name] = Var(var_type, var_value.value, loc=var_loc)
            block.add_quad(QEq(var_loc, var_value.loc))

        return block

    def enter_expr(self, ctx: LatteParser.ExprContext, block) -> (Var, Block):
        if isinstance(ctx, LatteParser.EUnOpContext):
            exp = ctx.expr()
            var_exp, block = self.enter_expr(exp, block)
            var_loc = block.give_var_name()
            op = ctx.children[0].getText()

            block.add_quad(QUnOp(var_loc, op, var_exp.loc))

            return Var(var_exp.type, loc=var_loc), block
        elif isinstance(ctx, (LatteParser.EAddOpContext, LatteParser.EMulOpContext)):
            val_exps: List[Var] = []
            for x in ctx.expr():
                var, block = self.enter_expr(x, block)
                val_exps.append(var)

            typ = None

            for exp in val_exps:
                if typ is None and exp.type in ["int", "string"]:
                    typ = exp.type

            var_name = block.give_var_name()

            if isinstance(ctx, LatteParser.EMulOpContext):
                op = ctx.mulOp().getText()
            else:
                op = ctx.addOp().getText()

            block.add_quad(QBinOp(var_name, val_exps[0].loc, op, val_exps[1].loc, typ))
            return Var(typ, None, loc=var_name), block
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
        elif isinstance(ctx, LatteParser.EIdContext):
            var_name = ctx.getText()
            for env in self.envs[::-1]:
                if var_name in env:
                    return env[var_name], block
        elif isinstance(ctx, LatteParser.EIntContext):
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

            fun_type = [x.type for x in var_list]
            fun = None

            for env in self.envs[::-1]:
                if fun_name in env:
                    if env[fun_name].type == fun_type:
                        fun = env[fun_name]
                        break

            block.add_quad(QFunCall(fun_name, res_name, [x.loc for x in var_list]))

            return Var(fun.res_type, loc=res_name), block
        elif isinstance(ctx, LatteParser.EStrContext):
            var_name = block.give_var_name()
            quad = QEq(var_name, ctx.STR().getText())

            block.add_quad(quad)
            return VString(ctx.STR().getText(), loc=var_name), block
        # elif isinstance(ctx, LatteParser.EParenContext):
        #     return self.enter_expr(ctx.expr())
        else:
            self.error(ctx, "Unresolved instance in enter_expr")

    def enter_while(self, ctx: LatteParser.WhileContext, block: Block) -> Block:
        condition = ctx.expr()

        while_number = block.give_while_number()
        while_name = '{}_w{}'.format(block.name, while_number)
        while_start = '{}S'.format(while_name)
        while_end = '{}E'.format(while_name)

        block.add_quad(QLabel(while_name))
        block = self.enter_lazy_expr(condition, block, while_start, while_end)

        self.envs.append({})
        block.add_quad(QLabel(while_start))
        block = self.enter_stmt(ctx.stmt(), block)
        self.envs.pop()

        block.add_quad(QJump(while_name))
        block.add_quad(QLabel(while_end))

        return block

    def enter_lazy_expr(self, ctx: LatteParser.ExprContext, block, pos_label, neg_label) -> Block:
        if isinstance(ctx, LatteParser.ETrueContext):
            block.add_quad(QJump(pos_label))
        elif isinstance(ctx, LatteParser.EAndContext):
            exp1 = ctx.expr(0)
            exp2 = ctx.expr(1)

            label = block.give_label()

            block = self.enter_lazy_expr(exp1, block, label, neg_label)
            block.add_quad(QLabel(label))
            block = self.enter_lazy_expr(exp2, block, pos_label, neg_label)
        return block

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
            rec_block = self.enter_block(ctx, SmallBlock(name))
            block = block.add_block(rec_block)

            self.envs.pop()
            return block
        elif isinstance(ctx, LatteParser.DeclContext):
            return self.enter_decl(ctx, block)
        # elif isinstance(ctx, LatteParser.AssContext):
        #     self.enter_ass(ctx, name, counter)
        # elif isinstance(ctx, LatteParser.IncrContext):
        #     self.enter_incr(ctx)
        # elif isinstance(ctx, LatteParser.DecrContext):
        #     self.enter_decr(ctx)
        elif isinstance(ctx, LatteParser.RetContext):
            return self.enter_ret(ctx, block)
        elif isinstance(ctx, LatteParser.VRetContext):
            return self.enter_vret(ctx, block)
        # elif isinstance(ctx, LatteParser.CondContext):
        #     self.enter_cond(ctx, ret_type)
        # elif isinstance(ctx, LatteParser.CondElseContext):
        #     self.enter_cond_else(ctx, ret_type)
        elif isinstance(ctx, LatteParser.WhileContext):
            return self.enter_while(ctx, block)
        elif isinstance(ctx, LatteParser.SExpContext):
            _, block = self.enter_expr(ctx.expr(), block)
            return block
        elif isinstance(ctx, LatteParser.EmptyContext):
            return block
        else:
            self.error(ctx, "Unresolved instance in enter_block StmtContext")

