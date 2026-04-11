from __future__ import annotations

from enum import Enum
from pathlib import Path

from .constants import PROJECT_ROOT, USERDATA_DIR


class FileType(str, Enum):
    GAMEDATA = "gamedata"
    USERDATA = "userdata"


def mkdirp(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def resolve_path(name: str | Path, file_type: FileType) -> Path:
    relative = Path(name)
    if file_type == FileType.GAMEDATA:
        return PROJECT_ROOT / relative
    target = USERDATA_DIR / relative
    mkdirp(target.parent)
    return target


def f1open(name: str | Path, mode: str, file_type: FileType):
    return resolve_path(name, file_type).open(mode)
