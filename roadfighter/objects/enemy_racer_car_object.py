"""CEnemyRacerCarObject port."""

from __future__ import annotations

from ..sound import Sound_play
from .enemy_car_object import CEnemyCarObject


class CEnemyRacerCarObject(CEnemyCarObject):
    def __init__(self, x: int, y: int, tile, start_delay: int, game):
        super().__init__(x, y, tile, start_delay, game)
        self.advanced = False

    def cycle(self, keyboard, old_keyboard) -> bool:
        retval = super().cycle(keyboard, old_keyboard)
        if not self.advanced and self.game.min_distance_to_players(self.y) < 48 and self.y_speed != 0:
            self.advanced = True
            if self.game.S_caradvance:
                Sound_play(self.game.S_caradvance)
        return retval

