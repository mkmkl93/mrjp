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
                arg_name = args.ID(i).getText()

                if i < 6:
                    reg = registers[i]
                    arg_loc = block.give_var_name()
                    block.add_quad(QEq(arg_loc, reg))
                else:
                    arg_loc = '{}(%rbp)'.format(16 + 4 * (i - 6))

                self.envs[-1][arg_name] = Var(arg_typ, loc=arg_loc)

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
        elif isinstance(ctx, LatteParser.ETrueContext):
            var_name = block.give_var_name()

            block.add_quad(QEq(var_name, '1'))
            return VBool('true', var_name), block
        elif isinstance(ctx, LatteParser.EFalseContext):
            var_name = block.give_var_name()

            block.add_quad(QEq(var_name, '0'))
            return VBool('false', var_name), block
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
        elif isinstance(ctx, LatteParser.EParenContext):
            return self.enter_expr(ctx.expr(), block)
        elif isinstance(ctx, (LatteParser.EAndContext, LatteParser.EOrContext, LatteParser.EOrContext, LatteParser.ERelOpContext)):
            label1 = block.give_label()
            label2 = block.give_label()
            label3 = block.give_label()
            var_name = block.give_var_name()

            block = self.enter_lazy_expr(ctx, block, label1, label2)

            block.add_quad(QLabel(label1))
            block.add_quad(QEq(var_name, '1'))
            block.add_quad(QJump('jmp', label3))
            block.add_quad(QLabel(label2))
            block.add_quad(QEq(var_name, '0'))
            block.add_quad(QLabel(label3))

            return VBool(None, var_name), block
        else:
            self.error(ctx, "Unresolved instance in enter_expr")

    def enter_while(self, ctx: LatteParser.WhileContext, block: Block) -> Block:
        condition = ctx.expr()

        while_number = block.give_while_number()
        while_name = '{}_while{}'.format(block.name, while_number)
        while_start = '{}_start'.format(while_name)
        while_end = '{}_end'.format(while_name)

        block.add_quad(QLabel(while_name))
        block = self.enter_lazy_expr(condition, block, while_start, while_end)

        self.envs.append({})
        block.add_quad(QLabel(while_start))
        block = self.enter_stmt(ctx.stmt(), block)
        self.envs.pop()

        block.add_quad(QJump('jmp', while_name))
        block.add_quad(QLabel(while_end))

        return block

    def enter_lazy_expr(self, ctx: LatteParser.ExprContext, block, pos_label, neg_label) -> Block:
        if isinstance(ctx, LatteParser.ETrueContext):
            block.add_quad(QJump('jmp', pos_label))
        elif isinstance(ctx, LatteParser.EFalseContext):
            block.add_quad(QJump('jmp', neg_label))
        elif isinstance(ctx, LatteParser.EAndContext):
            exp1 = ctx.expr(0)
            exp2 = ctx.expr(1)

            label = block.give_label()

            block = self.enter_lazy_expr(exp1, block, label, neg_label)
            block.add_quad(QLabel(label))
            block = self.enter_lazy_expr(exp2, block, pos_label, neg_label)
        elif isinstance(ctx, LatteParser.EOrContext):
            exp1 = ctx.expr(0)
            exp2 = ctx.expr(1)

            label = block.give_label()

            block = self.enter_lazy_expr(exp1, block, pos_label, label)
            block.add_quad(QJump('jmp', pos_label))
            block.add_quad(QLabel(label))
            block = self.enter_lazy_expr(exp2, block, pos_label, neg_label)
        elif isinstance(ctx, LatteParser.ERelOpContext):
            exp1 = ctx.expr(0)
            exp2 = ctx.expr(1)

            val1, block = self.enter_expr(exp1, block)
            val2, block = self.enter_expr(exp2, block)

            rel_op = ctx.relOp().getText()

            if rel_op == '<':
                op = 'jge'
            elif rel_op == '<=':
                op = 'jg'
            elif rel_op == '>':
                op = 'jle'
            elif rel_op == '>=':
                op = 'jl'
            elif rel_op == '==':
                op = 'jne'
            elif rel_op == '!=':
                op = 'je'

            block.add_quad(QCmp(val1.loc, val2.loc))
            block.add_quad(QJump(op, neg_label))
        elif isinstance(ctx, LatteParser.EParenContext):
            block = self.enter_lazy_expr(ctx.expr(), block, pos_label, neg_label)
        else:
            var, block = self.enter_expr(ctx, block)

            block.add_quad(QCmp(var.loc, '1'))
            block.add_quad(QJump('jne', neg_label))
            block.add_quad(QJump('jmp', pos_label))
        return block

    def enter_ass(self, ctx: LatteParser.AssContext, block) -> Block:
        var_name = ctx.ID().getText()
        exp = ctx.expr()

        val_exp, block = self.enter_expr(exp, block)

        for env in self.envs[::-1]:
            if var_name in env:
                block.add_quad(QEq(env[var_name].loc, val_exp.loc))
                break

        return block

    def enter_incr(self, ctx: LatteParser.IncrContext, block) -> Block:
        var_name = ctx.ID().getText()

        for env in self.envs[::-1]:
            if var_name in env:
                name = block.give_var_name()
                block.add_quad(QUnOp(env[var_name].loc, '++', env[var_name].loc))
                return block

    def enter_decr(self, ctx: LatteParser.DecrContext, block) -> Block:
        var_name = ctx.ID().getText()

        for env in self.envs[::-1]:
            if var_name in env:
                name = block.give_var_name()
                block.add_quad(QUnOp(env[var_name].loc, '--', env[var_name].loc))
                return block

    def enter_cond(self, ctx: LatteParser.CondContext, block: Block) -> Block:
        condition = ctx.expr()
        if_number = block.give_if_number()
        if_name = '{}_if{}'.format(block.name, if_number)
        if_start = '{}_start'.format(if_name)
        if_end = '{}_end'.format(if_name)

        block = self.enter_lazy_expr(condition, block, if_start, if_end)

        self.envs.append({})
        block.add_quad(QLabel(if_start))
        block = self.enter_stmt(ctx.stmt(), block)
        block.add_quad(QLabel(if_end))
        self.envs.pop()

        return block

    def enter_cond_else(self, ctx: LatteParser.CondElseContext, block) -> Block:
        condition = ctx.expr()
        if_number = block.give_if_number()
        if_name = '{}_if{}'.format(block.name, if_number)
        if_true = '{}_start'.format(if_name)
        if_else = '{}_else'.format(if_name)
        if_end = '{}_end'.format(if_name)

        block = self.enter_lazy_expr(condition, block, if_true, if_else)

        self.envs.append({})
        block.add_quad(QLabel(if_true))
        block = self.enter_stmt(ctx.stmt(0), block)
        block.add_quad(QJump('jmp', if_end))
        self.envs.pop()

        self.envs.append({})
        block.add_quad(QLabel(if_else))
        block = self.enter_stmt(ctx.stmt(1), block)
        self.envs.pop()

        block.add_quad(QLabel(if_end))
        return block

    def enter_stmt(self, ctx: LatteParser.StmtContext, block) -> Block:
        self.debug(ctx.getText() + "\n")
        if isinstance(ctx, LatteParser.BlockStmtContext):
            self.envs.append({})

            name = block.give_block_name()
            rec_block = self.enter_block(ctx, SmallBlock(name, block))
            block = block.add_block(rec_block)

            self.envs.pop()
            return block
        elif isinstance(ctx, LatteParser.DeclContext):
            return self.enter_decl(ctx, block)
        elif isinstance(ctx, LatteParser.AssContext):
            return self.enter_ass(ctx, block)
        elif isinstance(ctx, LatteParser.IncrContext):
            return self.enter_incr(ctx, block)
        elif isinstance(ctx, LatteParser.DecrContext):
            return self.enter_decr(ctx, block)
        elif isinstance(ctx, LatteParser.RetContext):
            return self.enter_ret(ctx, block)
        elif isinstance(ctx, LatteParser.VRetContext):
            return self.enter_vret(ctx, block)
        elif isinstance(ctx, LatteParser.CondContext):
            return self.enter_cond(ctx, block)
        elif isinstance(ctx, LatteParser.CondElseContext):
            return self.enter_cond_else(ctx, block)
        elif isinstance(ctx, LatteParser.WhileContext):
            return self.enter_while(ctx, block)
        elif isinstance(ctx, LatteParser.SExpContext):
            _, block = self.enter_expr(ctx.expr(), block)
            return block
        elif isinstance(ctx, LatteParser.EmptyContext):
            return block
        else:
            self.error(ctx, "Unresolved instance in enter_block StmtContext")

