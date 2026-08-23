

import sys





DEFAULT_SETTLE_MS = 10


DEFAULT_LONG_PRESS_MS = 500


DEFAULT_REPEAT_DELAY_MS = 500


def _select_source(pins, *, active_low, settle_ms, ticks):





    runtime_name = sys.implementation.name
    if runtime_name == "circuitpython":
        from chumicro_buttons._adapters.cp import CpButtonSource
        return CpButtonSource(pins, active_low=active_low, settle_ms=settle_ms)
    if runtime_name == "micropython":
        from chumicro_buttons._adapters.mp import MpButtonSource
        return MpButtonSource(pins, active_low=active_low, settle_ms=settle_ms, ticks=ticks)
    raise RuntimeError(
        "CPython has no GPIO to read.  Build the button with "
        "source=FakeButtonSource(...) from chumicro_buttons.testing and drive it "
        "from your test, or run this on CircuitPython or MicroPython.",
    )


class Button:




























    def __init__(
        self,
        pin: object | None = None,
        *,
        ticks: object,
        source: object | None = None,
        active_low: bool = True,
        settle_ms: int = DEFAULT_SETTLE_MS,
        long_press_ms: int = DEFAULT_LONG_PRESS_MS,
        repeat_ms: int = 0,
        repeat_delay_ms: int = DEFAULT_REPEAT_DELAY_MS,
        click_ms: int = 0,
    ) -> None:
        self._ticks = ticks

        if source is not None:
            self._source = source
        elif pin is not None:
            self._source = _select_source(
                (pin,), active_low=active_low, settle_ms=settle_ms, ticks=ticks,
            )
        else:
            self._source = None

        self._long_press_ms = long_press_ms
        self._repeat_ms = repeat_ms
        self._repeat_delay_ms = repeat_delay_ms
        self._click_ms = click_ms


        self.pressed = False

        self.just_pressed = False

        self.just_released = False

        self.just_long_pressed = False

        self.just_repeated = False

        self.just_clicked = False


        self.held_ms = 0

        self.click_count = 0


        self.overflowed = False


        self.on_press = None

        self.on_release = None

        self.on_long_press = None

        self.on_repeat = None

        self.on_click = None

        self._press_ms = 0
        self._long_fired = False
        self._repeat_next_ms = 0
        self._pending_clicks = 0
        self._click_deadline_ms = 0
        self._click_pending = False
        self._press_is_click = False

    def check(self, now_ms: int) -> bool:








        source = self._source
        if source is None:
            raise RuntimeError(
                "this Button belongs to a Buttons and is driven by it; "
                "tick the Buttons instead of the key.",
            )
        source.poll(now_ms)
        self._begin_tick()
        while source.next_event():


            if source.event_key == 0:
                self._apply_edge(source.event_pressed, source.event_ms)
        self.overflowed = source.overflowed
        source.overflowed = False
        return self._advance(now_ms)

    def handle(self, now_ms: int) -> None:

        if self.just_pressed and self.on_press is not None:
            self.on_press()
        if self.just_released and self.on_release is not None:
            self.on_release()
        if self.just_long_pressed and self.on_long_press is not None:
            self.on_long_press()
        if self.just_repeated and self.on_repeat is not None:
            self.on_repeat()
        if self.just_clicked and self.on_click is not None:
            self.on_click(self.click_count)

    def next_deadline(self, now_ms: int) -> int | None:







        ticks = self._ticks
        nearest = None
        if self.pressed:
            if self._long_press_ms > 0 and not self._long_fired:
                nearest = ticks.ticks_add(self._press_ms, self._long_press_ms)
            if self._repeat_ms > 0:
                candidate = self._repeat_next_ms
                if nearest is None or ticks.ticks_diff(candidate, nearest) < 0:
                    nearest = candidate
            if self._click_ms > 0 and self._press_is_click:
                candidate = ticks.ticks_add(self._press_ms, self._click_ms)
                if nearest is None or ticks.ticks_diff(candidate, nearest) < 0:
                    nearest = candidate
        if self._click_pending:
            candidate = self._click_deadline_ms
            if nearest is None or ticks.ticks_diff(candidate, nearest) < 0:
                nearest = candidate
        return nearest

    def deinit(self) -> None:

        if self._source is not None:
            self._source.deinit()

    def _begin_tick(self) -> None:

        self.just_pressed = False
        self.just_released = False
        self.just_long_pressed = False
        self.just_repeated = False
        self.just_clicked = False

    def _apply_edge(self, pressed: bool, event_ms: int) -> None:






        if pressed == self.pressed:
            return
        self.pressed = pressed
        if pressed:
            self._press_ms = event_ms
            self._long_fired = False
            self._repeat_next_ms = self._ticks.ticks_add(event_ms, self._repeat_delay_ms)
            self._click_pending = False
            self._press_is_click = True
            self.just_pressed = True
        else:
            held_ms = self._ticks.ticks_diff(event_ms, self._press_ms)
            self.held_ms = held_ms if held_ms > 0 else 0
            self.just_released = True
            if self._click_ms > 0 and self._press_is_click:
                self._pending_clicks += 1
                self._click_deadline_ms = self._ticks.ticks_add(event_ms, self._click_ms)
                self._click_pending = True

    def _advance(self, now_ms: int) -> bool:





        fired = self.just_pressed or self.just_released
        ticks = self._ticks
        if self.pressed:
            held_ms = ticks.ticks_diff(now_ms, self._press_ms)
            self.held_ms = held_ms if held_ms > 0 else 0
            if (
                self._long_press_ms > 0
                and not self._long_fired
                and self.held_ms >= self._long_press_ms
            ):
                self._long_fired = True
                self.just_long_pressed = True
                fired = True
            if self._repeat_ms > 0:
                behind_ms = ticks.ticks_diff(now_ms, self._repeat_next_ms)
                if behind_ms >= 0:




                    periods_missed = behind_ms // self._repeat_ms + 1
                    self._repeat_next_ms = ticks.ticks_add(
                        self._repeat_next_ms, periods_missed * self._repeat_ms,
                    )
                    self.just_repeated = True
                    fired = True
            if (
                self._click_ms > 0
                and self._press_is_click
                and self.held_ms >= self._click_ms
            ):



                self._press_is_click = False
                if self._pending_clicks > 0:
                    self.click_count = self._pending_clicks
                    self._pending_clicks = 0
                    self.just_clicked = True
                    fired = True
        if self._click_pending and ticks.ticks_diff(now_ms, self._click_deadline_ms) >= 0:
            self._click_pending = False
            self.click_count = self._pending_clicks
            self._pending_clicks = 0
            self.just_clicked = True
            fired = True
        return fired


class Buttons:





















    def __init__(
        self,
        pins: object | None = None,
        *,
        ticks: object,
        source: object | None = None,
        active_low: bool = True,
        settle_ms: int = DEFAULT_SETTLE_MS,
        long_press_ms: int = DEFAULT_LONG_PRESS_MS,
        repeat_ms: int = 0,
        repeat_delay_ms: int = DEFAULT_REPEAT_DELAY_MS,
        click_ms: int = 0,
    ) -> None:
        self._ticks = ticks
        if source is not None:
            self._source = source
        elif pins is not None:
            if len(pins) == 0:



                raise ValueError("Buttons was given an empty pins sequence")
            self._source = _select_source(
                pins, active_low=active_low, settle_ms=settle_ms, ticks=ticks,
            )
        else:
            raise ValueError("Buttons needs either pins= or source=")


        self.keys = []
        key_index = 0
        while key_index < self._source.key_count:
            self.keys.append(
                Button(
                    long_press_ms=long_press_ms,
                    repeat_ms=repeat_ms,
                    repeat_delay_ms=repeat_delay_ms,
                    click_ms=click_ms,
                    ticks=ticks,
                ),
            )
            key_index += 1


        self.overflowed = False

        self.on_press = None

        self.on_release = None

    def check(self, now_ms: int) -> bool:








        source = self._source
        source.poll(now_ms)
        keys = self.keys
        key_count = len(keys)
        index = 0
        while index < key_count:
            keys[index]._begin_tick()
            index += 1
        while source.next_event():
            keys[source.event_key]._apply_edge(source.event_pressed, source.event_ms)
        self.overflowed = source.overflowed
        source.overflowed = False
        fired = False
        index = 0
        while index < key_count:
            if keys[index]._advance(now_ms):
                fired = True
            index += 1
        return fired

    def handle(self, now_ms: int) -> None:

        keys = self.keys
        key_count = len(keys)
        index = 0
        while index < key_count:
            key = keys[index]
            key.handle(now_ms)
            if key.just_pressed and self.on_press is not None:
                self.on_press(index)
            if key.just_released and self.on_release is not None:
                self.on_release(index)
            index += 1

    def next_deadline(self, now_ms: int) -> int | None:

        ticks = self._ticks
        keys = self.keys
        key_count = len(keys)
        nearest = None
        index = 0
        while index < key_count:
            candidate = keys[index].next_deadline(now_ms)
            if candidate is not None and (
                nearest is None or ticks.ticks_diff(candidate, nearest) < 0
            ):
                nearest = candidate
            index += 1
        return nearest

    def deinit(self) -> None:

        self._source.deinit()

    def __len__(self) -> int:

        return len(self.keys)

    def __getitem__(self, key_index: int) -> Button:

        return self.keys[key_index]
