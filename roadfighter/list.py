from __future__ import annotations

import random
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Generic, Optional, TypeVar


T = TypeVar("T")


@dataclass
class LLink(Generic[T]):
    obj: T
    next: Optional["LLink[T]"] = None

    def Getnext(self) -> Optional["LLink[T]"]:
        return self.next

    def Setnext(self, nxt: Optional["LLink[T]"]) -> None:
        self.next = nxt

    def GetObj(self) -> T:
        return self.obj

    def SetObj(self, obj: T) -> None:
        self.obj = obj

    def Anade(self, obj: T) -> None:
        if self.next is None:
            self.next = LLink(obj)
        else:
            self.next.Anade(obj)


class List(Generic[T]):
    def __init__(self, other: Optional["List[T]"] = None) -> None:
        self.original = True
        self.list: Optional[LLink[T]] = None
        self.top: Optional[LLink[T]] = None
        self.act: Optional[LLink[T]] = None
        if other is not None:
            self.Instance(other)

    def Delete(self) -> None:
        self.list = None
        self.top = None
        self.act = None

    def Instance(self, other: "List[T]") -> None:
        self.list = other.list
        self.top = other.top
        self.act = other.list
        self.original = False

    def Rewind(self) -> None:
        self.act = self.list

    def Forward(self) -> None:
        self.act = self.top

    def Next(self) -> None:
        if self.act is not None:
            self.act = self.act.Getnext()

    def Prev(self) -> None:
        if self.act is None or self.act == self.list:
            return
        tmp = self.list
        while tmp is not None and tmp.Getnext() is not self.act:
            tmp = tmp.Getnext()
        self.act = tmp

    def GetObj(self) -> T:
        if self.act is None:
            raise IndexError("List cursor is at end")
        return self.act.GetObj()

    def SetObj(self, obj: T) -> None:
        if self.act is None:
            raise IndexError("List cursor is at end")
        self.act.SetObj(obj)

    def GetPos(self) -> Optional[LLink[T]]:
        return self.act

    def EmptyP(self) -> bool:
        return self.list is None

    def EndP(self) -> bool:
        return self.act is None

    def LastP(self) -> bool:
        return self.act is self.top

    def BeginP(self) -> bool:
        return self.act is self.list

    def Insert(self, obj: T) -> None:
        if self.list is None:
            self.list = LLink(obj)
            self.top = self.list
        else:
            self.list = LLink(obj, self.list)
        if self.act is None:
            self.act = self.list

    def Add(self, obj: T) -> None:
        if self.list is None:
            self.list = LLink(obj)
            self.top = self.list
            self.act = self.list
        else:
            assert self.top is not None
            self.top.Anade(obj)
            self.top = self.top.Getnext()

    def AddAfter(self, pos: Optional[LLink[T]], obj: T) -> None:
        if pos is None:
            self.Insert(obj)
            return
        new_link = LLink(obj, pos.Getnext())
        pos.Setnext(new_link)
        if new_link.Getnext() is None:
            self.top = new_link

    def AddBefore(self, pos: Optional[LLink[T]], obj: T) -> None:
        if pos is self.list:
            self.Insert(obj)
            return
        prev = self.list
        while prev is not None and prev.Getnext() is not pos:
            prev = prev.Getnext()
        new_link = LLink(obj, pos)
        if prev is None:
            self.list = new_link
        else:
            prev.Setnext(new_link)
        if pos is None:
            self.top = new_link

    def Iterate(self) -> Optional[T]:
        if self.act is None:
            return None
        obj = self.act.GetObj()
        self.act = self.act.Getnext()
        return obj

    def ExtractIni(self) -> Optional[T]:
        if self.list is None:
            return None
        obj = self.list.GetObj()
        tmp = self.list
        self.list = tmp.Getnext()
        if self.act is tmp:
            self.act = self.list
        if self.top is tmp:
            self.top = self.list
        return obj

    def Extract(self) -> Optional[T]:
        if self.list is None:
            return None
        prev = None
        cur = self.list
        while cur.Getnext() is not None:
            prev = cur
            cur = cur.Getnext()
        obj = cur.GetObj()
        if prev is None:
            self.list = None
            self.top = None
            self.act = None
        else:
            prev.Setnext(None)
            self.top = prev
            if self.act is cur:
                self.act = self.top
        return obj

    def MemberP(self, obj: T) -> bool:
        cur = self.list
        while cur is not None:
            if cur.GetObj() == obj:
                return True
            cur = cur.Getnext()
        return False

    def MemberGet(self, obj: T) -> Optional[T]:
        cur = self.list
        while cur is not None:
            if cur.GetObj() == obj:
                return cur.GetObj()
            cur = cur.Getnext()
        return None

    def MemberRefP(self, obj: T) -> bool:
        cur = self.list
        while cur is not None:
            if cur.GetObj() is obj:
                return True
            cur = cur.Getnext()
        return False

    def Length(self) -> int:
        count = 0
        cur = self.list
        while cur is not None:
            cur = cur.Getnext()
            count += 1
        return count

    def Copy(self, other: "List[T]") -> None:
        self.Delete()
        self.original = True
        cur = other.list
        while cur is not None:
            obj = cur.GetObj()
            clone = obj.copy() if hasattr(obj, "copy") else obj
            self.Add(clone)
            cur = cur.Getnext()
        self.Synchronize(other)

    def Synchronize(self, other: "List[T]") -> None:
        self.act = self.list
        cur = other.list
        while cur is not None and cur is not other.act:
            cur = cur.Getnext()
            if self.act is not None:
                self.act = self.act.Getnext()

    def Append(self, other: "List[T]") -> None:
        cur = other.list
        while cur is not None:
            obj = cur.GetObj()
            clone = obj.copy() if hasattr(obj, "copy") else obj
            self.Add(clone)
            cur = cur.Getnext()

    def DeleteElement(self, obj: T) -> bool:
        prev = None
        cur = self.list
        while cur is not None and cur.GetObj() is not obj:
            prev = cur
            cur = cur.Getnext()
        if cur is None:
            return False
        if prev is None:
            self.list = cur.Getnext()
            if self.act is cur:
                self.act = self.list
            if self.top is cur:
                self.top = self.list
        else:
            prev.Setnext(cur.Getnext())
            if self.act is cur:
                self.act = cur.Getnext()
            if self.top is cur:
                self.top = prev
        return True

    def GetRandom(self) -> T:
        length = self.Length()
        if length == 0:
            raise IndexError("Cannot pick from empty List")
        return self[random.randrange(length)]

    def SearchObjRef(self, obj: T) -> int:
        pos = 0
        cur = self.list
        while cur is not None:
            if cur.GetObj() is obj:
                return pos
            cur = cur.Getnext()
            pos += 1
        return -1

    def SearchObj(self, obj: T) -> int:
        pos = 0
        cur = self.list
        while cur is not None:
            if cur.GetObj() == obj:
                return pos
            cur = cur.Getnext()
            pos += 1
        return -1

    def Sort(self, predicate: Callable[[T, T], bool]) -> None:
        prev = None
        cur = self.list
        while cur is not None:
            if prev is not None and not predicate(prev.GetObj(), cur.GetObj()):
                prev.obj, cur.obj = cur.obj, prev.obj
            prev = cur
            cur = cur.Getnext()

    def SetNoOriginal(self) -> None:
        self.original = False

    def SetOriginal(self) -> None:
        self.original = True

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, List):
            return False
        left = self.list
        right = other.list
        while left is not None and right is not None:
            if left.GetObj() != right.GetObj():
                return False
            left = left.Getnext()
            right = right.Getnext()
        return left is None and right is None

    def __getitem__(self, index: int) -> T:
        cur = self.list
        while cur is not None and index > 0:
            cur = cur.Getnext()
            index -= 1
        if cur is None:
            raise IndexError(index)
        return cur.GetObj()

    def __iter__(self) -> Iterator[T]:
        cur = self.list
        while cur is not None:
            yield cur.GetObj()
            cur = cur.Getnext()
