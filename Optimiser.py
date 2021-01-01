from typing import List

import re
import sys
from utils import *


class Optimiser:
    def __init__(self, DEBUG):
        self.DEBUG = DEBUG
        self.code = []
        self.strings = []
        self.block_counter = 0

    def debug(self, msg) -> None:
        if self.DEBUG:
            sys.stderr.write(msg)

    def get_quads(self, block, res) -> List[Quad]:
        if isinstance(block, BigBlock):
            for b in block.blocks:
                res = self.get_quads(b, res)
        else:
            for quad in block.quads:
                res.append(quad)
        return res

    def divide_into_blocks(self, quads: List[Quad], res) -> List[Block]:
        block = SmallBlock(self.block_counter)
        block.add_quad(quads[0])
        self.block_counter += 1

        for i, quad in enumerate(quads[1:]):
            if isinstance(quad, QEmpty):
                continue
            elif isinstance(quad, (QLabel, QFunBegin)):
                res.append(block)
                return self.divide_into_blocks(quads[i:], res)
            else:
                block.add_quad(quad)

        res.append(block)
        return res

    def optimise(self, blocks: List[Block]) -> List[Block]:
        quads = []
        for block in blocks:
            quads = self.get_quads(block, quads)

        blocks = self.divide_into_blocks(quads, [])

        return blocks









