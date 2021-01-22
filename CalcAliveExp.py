from typing import List

import sys
from utils import *

class CalcAliveExp:
    def __init__(self, debug):
        self.dbug = debug

    def debug(self, msg) -> None:
        if self.dbug:
            sys.stderr.write(msg)

    def calc(self, blocks: List[SmallBlock]) -> List[SmallBlock]:
        blocks = self.calculate_alive_blocks(blocks)

        return blocks




