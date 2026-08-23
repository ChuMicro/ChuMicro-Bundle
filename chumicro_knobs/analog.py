

import sys



RAW_RANGE = 65536


DEFAULT_STEPS = 100




DEFAULT_DEADBAND = 512


def _select_analog_source(pin):

    runtime_name = sys.implementation.name
    if runtime_name == "circuitpython":
        from chumicro_knobs._adapters.cp import CpAnalogSource
        return CpAnalogSource(pin)
    if runtime_name == "micropython":
        from chumicro_knobs._adapters.mp import MpAnalogSource
        return MpAnalogSource(pin)
    raise RuntimeError(
        "CPython has no converter to sample.  Build the knob with "
        "source=FakeAnalogSource() from chumicro_knobs.testing and set a reading from "
        "your test, or run this on CircuitPython or MicroPython.",
    )


class AnalogKnob:


















    def __init__(
        self,
        pin: object | None = None,
        *,
        source: object | None = None,
        steps: int = DEFAULT_STEPS,
        deadband: int = DEFAULT_DEADBAND,
    ) -> None:
        if source is not None:
            self._source = source
        elif pin is not None:
            self._source = _select_analog_source(pin)
        else:
            raise ValueError("AnalogKnob needs either pin= or source=")

        self._steps = steps
        self._deadband = deadband


        self.value = 0


        self.raw = 0

        self.delta = 0

        self.just_moved = False

        self.on_change = None

    def check(self, now_ms: int) -> bool:








        source = self._source
        source.poll(now_ms)
        raw = source.raw
        if abs(raw - self.raw) <= self._deadband:
            self.delta = 0
            self.just_moved = False
            return False

        self.raw = raw
        value = raw * self._steps // RAW_RANGE
        delta = value - self.value
        self.value = value
        self.delta = delta
        self.just_moved = delta != 0
        return self.just_moved

    def handle(self, now_ms: int) -> None:

        if self.just_moved and self.on_change is not None:
            self.on_change(self.value)

    def deinit(self) -> None:

        self._source.deinit()
