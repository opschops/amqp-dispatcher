import asyncio


class WaitGroup(object):
    event: asyncio.Event
    _count: int

    def __init__(self) -> None:
        self.event = asyncio.Event()
        self.event.set()
        self._count = 0

    def add(self) -> None:
        self._count += 1
        self.event.clear()

    def done(self) -> None:
        self._count -= 1
        if self._count == 0:
            self.event.set()
