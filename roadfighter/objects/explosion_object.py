"""CExplosionObject port."""

from __future__ import annotations

from ..constants import CONSTITUTION_NONE
from ..object import CObject


class CExplosionObject(CObject):
    def __init__(self, x: int, y: int, tiles, first_tile: int, last_tile: int, game):
        super().__init__(x, y, None, CONSTITUTION_NONE, game)
        self.tiles = [tiles[index] for index in range(first_tile, last_tile + 1)]
        self.ntiles = len(self.tiles)
        self.tile = 0
        self.timmer = 0

    def cycle(self, keyboard, old_keyboard) -> bool:
        self.timmer += 1
        self.tile = self.timmer // 2
        return self.tile < self.ntiles

