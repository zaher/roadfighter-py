"""CEnemySlidderCarObject port."""

from __future__ import annotations

from .enemy_car_object import CEnemyCarObject


class CEnemySlidderCarObject(CEnemyCarObject):
    def cycle(self, keyboard, old_keyboard) -> bool:
        retval = super().cycle(keyboard, old_keyboard)
        if self.state == 1 and self.game.min_distance_to_players(self.y) < 192:
            closest_player = self.game.find_closest_player(self.x, self.y)
            if self.x > closest_player.get_x():
                self.distance_to_border += 40 if self.following_right_border else -40
            else:
                self.distance_to_border += -40 if self.following_right_border else 40
            if self.distance_to_border < 0:
                self.distance_to_border += 80
            self.state = 2
        return retval

