

import sys


DEFAULT_DETENT_STEPS = 4


def _select_encoder_source(pin_a, pin_b, *, detent_steps):

    runtime_name = sys.implementation.name
    if runtime_name == "circuitpython":
        from chumicro_knobs._adapters.cp import CpEncoderSource
        return CpEncoderSource(pin_a, pin_b, detent_steps=detent_steps)
    if runtime_name == "micropython":
        from chumicro_knobs._adapters.mp import MpEncoderSource
        return MpEncoderSource(pin_a, pin_b, detent_steps=detent_steps)
    raise RuntimeError(
        "CPython has no pins to watch a shaft with.  Build the encoder with "
        "source=FakeEncoderSource() from chumicro_knobs.testing and turn it from "
        "your test, or run this on CircuitPython or MicroPython.",
    )


class Encoder:





















    def __init__(
        self,
        pin_a: object | None = None,
        pin_b: object | None = None,
        *,
        source: object | None = None,
        detent_steps: int = DEFAULT_DETENT_STEPS,
        bounds: tuple[int, int] | None = None,
        wrap: bool = False,
    ) -> None:
        if detent_steps < 1:


            raise ValueError("detent_steps must be 1 or more")
        if source is not None:
            self._source = source
        elif pin_a is not None and pin_b is not None:
            self._source = _select_encoder_source(
                pin_a, pin_b, detent_steps=detent_steps,
            )
        else:
            raise ValueError("Encoder needs both pin_a= and pin_b=, or source=")

        if bounds is None:
            if wrap:
                raise ValueError("wrap=True needs bounds=(low, high) to wrap around")
            self._bounded = False
            self._low = 0
            self._high = 0
            self._span = 0
        else:
            self._bounded = True
            self._low = bounds[0]
            self._high = bounds[1]
            self._span = self._high - self._low + 1
        self._wrap = wrap

        start_position = 0
        if self._bounded:
            if start_position < self._low:
                start_position = self._low
            elif start_position > self._high:
                start_position = self._high



        self.position = start_position


        self.delta = 0

        self.just_moved = False

        self.on_change = None

        self._last_raw_position = self._source.raw_position

    def check(self, now_ms: int) -> bool:








        source = self._source
        source.poll(now_ms)
        raw_position = source.raw_position
        moved = raw_position - self._last_raw_position
        if moved == 0:
            self.delta = 0
            self.just_moved = False
            return False
        self._last_raw_position = raw_position

        previous_position = self.position
        position = previous_position + moved
        if not self._bounded:
            delta = moved
        elif self._wrap:
            position = self._low + (position - self._low) % self._span
            delta = moved
        else:
            if position < self._low:
                position = self._low
            elif position > self._high:
                position = self._high
            delta = position - previous_position

        self.position = position
        self.delta = delta
        self.just_moved = delta != 0
        return self.just_moved

    def handle(self, now_ms: int) -> None:

        if self.just_moved and self.on_change is not None:
            self.on_change(self.delta)

    def deinit(self) -> None:

        self._source.deinit()
