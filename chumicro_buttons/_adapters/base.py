


class ButtonSource:










    key_count = 0


    overflowed = False


    event_key = 0


    event_pressed = False


    event_ms = 0

    def poll(self, now_ms: int) -> None:






        raise NotImplementedError

    def next_event(self) -> bool:






        raise NotImplementedError

    def deinit(self) -> None:

        raise NotImplementedError
