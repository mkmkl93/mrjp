from typing import List

import sys
from utils import *

class CalcAliveSet:
    def __init__(self, debug):
        self.dbug = debug
        self.code = []
        self.strings = []
        self.block_counter = 1
        self.add_at_the_end = 0
        self.appearances = {}
        self.line = 0

    def debug(self, msg) -> None:
        if self.dbug:
            sys.stderr.write(msg)

    def calc(self, blocks: List[Block]) -> List[SmallBlock]:
        quads = []
        for block in blocks:
            quads = self.get_quads(block, quads)

        blocks = self.divide_into_blocks(quads, [])

        blocks = self.calculate_alive_all(blocks)

        for block in blocks:
            block_label = block.quads[0].name
            self.debug('{{ {} }} -> {} -> {{ {} }}\n'.format(
                ', '.join(block.previous_blocks), block_label, ', '.join(block.following_blocks)))

        return blocks

    def get_quads(self, block, res) -> List[Quad]:
        if isinstance(block, BigBlock):
            for b in block.blocks:
                res = self.get_quads(b, res)
        else:
            for quad in block.quads:
                res.append(quad)
        return res

    def divide_into_blocks(self, quads: List[Quad], res) -> List[SmallBlock]:
        block = SmallBlock(str(self.block_counter))
        if not quads:
            return block
        self.block_counter += 1

        for i, quad in enumerate(quads):
            if isinstance(quad, (QLabel, QFunBegin)) and i > 0:
                res.append(block)
                return self.divide_into_blocks(quads[i:], res)
            elif isinstance(quad, (QCmp, QJump)):
                block.add_quad(quad)
                res.append(block)
                return self.divide_into_blocks(quads[i + 1:], res)
            else:
                block.add_quad(quad)

        res.append(block)
        return res

    def calculate_alive_all(self, blocks: List[SmallBlock]) -> List[SmallBlock]:
        map_label = {}
        map_block = {}
        n = len(blocks)

        for block in blocks:
            for quad in block.quads:
                quad.alive = AliveSet()

        for i in range(n):
            block_label = blocks[i].quads[0].name
            map_label[block_label] = blocks[i].name
            map_block[blocks[i].name] = i

        for i in range(n):
            prev_quad = blocks[i - 1].quads[-1]
            if i > 0 and not isinstance(prev_quad, QFunEnd) and not isinstance(prev_quad, QJump):
                blocks[i].add_previous(blocks[i - 1].name)
                blocks[i - 1].add_following(blocks[i].name)

            act_quad = blocks[i].quads[-1]
            if isinstance(act_quad, (QCmp, QJump)):
                jmp_indx = map_block [map_label[act_quad.name]]

                blocks[i].add_following(map_label[act_quad.name])
                blocks[jmp_indx].add_previous(blocks[i].name)

        for i in range(n):
            que = [i]

            while len(que) != 0:
                x = que.pop()

                old_state = blocks[x].quads[0].alive.copy()
                blocks[x] = self.calculate_alive(blocks[x])
                new_state = blocks[x].quads[0].alive.copy()

                if old_state != new_state or len(blocks[x].quads) == 1:
                    for prev_name in blocks[x].previous_blocks:
                        prev_number = map_block[prev_name]
                        if prev_number != x:
                            blocks[prev_number].quads[-1].alive.union(new_state)
                            que.append(prev_number)

        # placeholder = blocks
        # blocks = []
        # for block in placeholder:
        #     if not block.previous_blocks and not isinstance(block.quads[0], QFunBegin) and not isinstance(block.quads[-1], QFunEnd):
        #         pass
        #     else:
        #         blocks.append(block)

        return blocks

    def calculate_alive(self, block: SmallBlock):
        alive_set = block.quads[-1].alive.copy()
        ln = len(block.quads)
        for i, quad in enumerate(block.quads[-1::-1]):
            block.quads[ln - i - 1].alive = alive_set.copy()
            self.line += 1
            quad.line = self.line

            if isinstance(quad, QJump):
                pass
            elif isinstance(quad, QCmp):
                alive_set.add(quad.var1)
                alive_set.add(quad.var2)
            elif isinstance(quad, QReturn):
                alive_set.add(quad.var)
            elif isinstance(quad, QEq):
                alive_set.discard(quad.res)
                alive_set.add(quad.var)
            elif isinstance(quad, QFunBegin):
                pass
            elif isinstance(quad, QFunEnd):
                pass
            elif isinstance(quad, QFunCall):
                alive_set.discard(quad.res)
                for arg in quad.args:
                    alive_set.add(arg)
            elif isinstance(quad, QBinOp):
                alive_set.discard(quad.res)
                alive_set.add(quad.var1)
                alive_set.add(quad.var2)
            elif isinstance(quad, QUnOp):
                alive_set.discard(quad.res)
                alive_set.add(quad.var)
        return block
