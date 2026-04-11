"""CSemaphoreObject port."""

from __future__ import annotations

from ..constants import CONSTITUTION_NONE, SEMAPHORE_TIME
from ..object import CObject
from ..sound import Sound_play


class CSemaphoreObject(CObject):
    def __init__(self, x: int, y: int, t1, t2, t3, t4, t5, game):
        super().__init__(x, y, None, CONSTITUTION_NONE, game)
        self.tiles = [t1, t2, t3, t4, t5]
        self.ntiles = len(self.tiles)
        self.tile = 0
        self.timmer = 0

    def cycle(self, keyboard, old_keyboard) -> bool:
        self.timmer += 1
        if self.timmer >= SEMAPHORE_TIME * 1:
            self.tile = 1
        if self.timmer >= SEMAPHORE_TIME * 2:
            self.tile = 0
        if self.timmer >= SEMAPHORE_TIME * 3:
            self.tile = 2
        if self.timmer >= SEMAPHORE_TIME * 4:
            self.tile = 0
        if self.timmer >= SEMAPHORE_TIME * 5:
            self.tile = 3
        if self.timmer >= SEMAPHORE_TIME * 6:
            self.tile = 0
        if self.timmer >= SEMAPHORE_TIME * 7:
            self.tile = 4

        if self.timmer in (SEMAPHORE_TIME * 1, SEMAPHORE_TIME * 3, SEMAPHORE_TIME * 5):
            if self.game.S_redlight:
                Sound_play(self.game.S_redlight)
        return True

