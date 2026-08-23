

__chumicro_runtimes__ = ("circuitpython",)

import analogio
import rotaryio

from chumicro_knobs._adapters.base import SMOOTHING_SHIFT, middle_of_three


class CpEncoderSource:








    def __init__(self, pin_a, pin_b, *, detent_steps: int) -> None:
        self._encoder = rotaryio.IncrementalEncoder(pin_a, pin_b, divisor=detent_steps)
        self.raw_position = self._encoder.position

    def poll(self, now_ms: int) -> None:

        self.raw_position = self._encoder.position

    def deinit(self) -> None:

        self._encoder.deinit()


class CpAnalogSource:






    def __init__(self, pin) -> None:
        self._converter = analogio.AnalogIn(pin)
        reading = self._converter.value

        self._recent = [reading, reading, reading]
        self._slot = 0

        self._smoothed = reading << SMOOTHING_SHIFT
        self.raw = reading

    def poll(self, now_ms: int) -> None:

        recent = self._recent
        recent[self._slot] = self._converter.value
        slot = self._slot + 1
        self._slot = 0 if slot >= 3 else slot
        middle = middle_of_three(recent[0], recent[1], recent[2])
        self._smoothed += middle - (self._smoothed >> SMOOTHING_SHIFT)
        self.raw = self._smoothed >> SMOOTHING_SHIFT

    def deinit(self) -> None:

        self._converter.deinit()
