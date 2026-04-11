"""Base object classes ported from CObject.cpp/h and CCarObject.cpp."""

from __future__ import annotations

from .constants import CONSTITUTION_CAR, CONSTITUTION_NONE


def _mask_collision(tile1, x1: int, y1: int, tile2, x2: int, y2: int) -> bool:
    if tile1.collision_data is None or tile2.collision_data is None:
        return False
    return tile1.collision_data.collides_with(tile2.collision_data, x2 - x1, y2 - y1)


class CObject:
    def __init__(self, x: int = 0, y: int = 0, tile=None, constitution: int = CONSTITUTION_NONE, game=None):
        self.state = 0
        self.constitution = constitution
        self.game = game
        self.tiles = []
        self.ntiles = 0
        self.tile = 0
        self.x = x
        self.y = y
        self.draw_x = x
        self.draw_y = y

        if tile is not None:
            self.tiles = [tile]
            self.ntiles = 1

    def cycle(self, keyboard, old_keyboard) -> bool:
        return True

    def draw(self, sx: int, sy: int, screen) -> None:
        self.draw_x = self.x
        self.draw_y = self.y
        if 0 <= self.tile < self.ntiles:
            self.tiles[self.tile].draw(self.x - sx, self.y - sy, screen)

    def collision(self, offsx: int, offsy: int, other: "CObject") -> bool:
        t1 = self.tiles[self.tile] if 0 <= self.tile < self.ntiles else None
        t2 = other.tiles[other.tile] if 0 <= other.tile < other.ntiles else None
        if t1 is None or t2 is None:
            return False
        if t1.collision_data is None or t2.collision_data is None:
            return False
        return _mask_collision(t1, self.draw_x, self.draw_y, t2, other.draw_x + offsx, other.draw_y + offsy)

    def get_x(self) -> int:
        return self.x

    def get_y(self) -> int:
        return self.y

    def get_dx(self) -> int:
        if 0 <= self.tile < self.ntiles:
            return self.tiles[self.tile].get_dx()
        return 0

    def get_dy(self) -> int:
        if 0 <= self.tile < self.ntiles:
            return self.tiles[self.tile].get_dy()
        return 0

    def set_state(self, state: int) -> None:
        self.state = state

    def get_state(self) -> int:
        return self.state

    def constitution_test(self, constitution: int) -> bool:
        return (self.constitution & constitution) != 0


class CCarObject(CObject):
    def __init__(self, x: int = 0, y: int = 0, tile=None, game=None):
        super().__init__(x, y, tile, CONSTITUTION_CAR, game)
        self.y_precision = 0
        self.x_precision = 0
        self.y_speed = 0
        self.x_speed = 0
        self.last_collision = None

    def cycle(self, keyboard, old_keyboard) -> bool:
        self.y_precision += self.y_speed
        while self.y_precision > (1 << 8):
            self.y += 1
            self.y_precision -= 1 << 8
        while self.y_precision < ((-1) << 8):
            self.y -= 1
            self.y_precision += 1 << 8

        self.x_precision += self.x_speed
        while self.x_precision > (1 << 8):
            self.x += 1
            self.x_precision -= 1 << 8
        while self.x_precision < ((-1) << 8):
            self.x -= 1
            self.x_precision += 1 << 8
        return True

    def get_y_speed(self) -> int:
        return self.y_speed

    def car_collision(self, car: "CCarObject") -> None:
        self.last_collision = car

    def compute_next_x(self) -> int:
        tmp = self.x_precision + self.x_speed
        new_x = self.x
        while tmp > (1 << 8):
            new_x += 1
            tmp -= 1 << 8
        while tmp < ((-1) << 8):
            new_x -= 1
            tmp += 1 << 8
        return new_x

    def compute_next_y(self) -> int:
        tmp = self.y_precision + self.y_speed
        new_y = self.y
        while tmp > (1 << 8):
            new_y += 1
            tmp -= 1 << 8
        while tmp < ((-1) << 8):
            new_y -= 1
            tmp += 1 << 8
        return new_y
