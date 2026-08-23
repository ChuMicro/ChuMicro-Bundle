

__chumicro_runtimes__ = ("micropython",)

import array

import machine

from chumicro_knobs._adapters.base import SMOOTHING_SHIFT, middle_of_three

try:
    from micropython import const
except ImportError:
    def const(value):
        return value






_QUADRATURE_STEPS = (
    b"\x01\x00\x02\x01\x02\x01\x01\x00"
    b"\x00\x01\x01\x02\x01\x02\x00\x01"
)



_POSITION = const(0)
_SUB_COUNT = const(1)
_PREVIOUS_STATE = const(2)


class MpEncoderSource:








    def __init__(self, pin_a, pin_b, *, detent_steps: int) -> None:
        self._pin_a = machine.Pin(pin_a, machine.Pin.IN, machine.Pin.PULL_UP)
        self._pin_b = machine.Pin(pin_b, machine.Pin.IN, machine.Pin.PULL_UP)
        self._detent_steps = detent_steps


        self._counters = array.array("l", (0, 0, 0))
        self._counters[_PREVIOUS_STATE] = (self._pin_a.value() << 1) | self._pin_b.value()


        self._edge_handler = self._on_edge
        edges = machine.Pin.IRQ_RISING | machine.Pin.IRQ_FALLING
        self._pin_a.irq(handler=self._edge_handler, trigger=edges)
        self._pin_b.irq(handler=self._edge_handler, trigger=edges)

        self.raw_position = 0

    def _on_edge(self, pin) -> None:








        counters = self._counters
        detent_steps = self._detent_steps
        state = (self._pin_a.value() << 1) | self._pin_b.value()
        step = _QUADRATURE_STEPS[(counters[_PREVIOUS_STATE] << 2) | state] - 1
        counters[_PREVIOUS_STATE] = state
        sub_count = counters[_SUB_COUNT] + step
        if sub_count >= detent_steps:
            counters[_POSITION] += 1
            sub_count = 0
        elif sub_count <= -detent_steps:
            counters[_POSITION] -= 1
            sub_count = 0
        counters[_SUB_COUNT] = sub_count

    def poll(self, now_ms: int) -> None:

        self.raw_position = self._counters[_POSITION]

    def deinit(self) -> None:

        self._pin_a.irq(handler=None)
        self._pin_b.irq(handler=None)


class MpAnalogSource:







    def __init__(self, pin) -> None:
        self._converter = machine.ADC(pin)
        reading = self._converter.read_u16()

        self._recent = [reading, reading, reading]
        self._slot = 0

        self._smoothed = reading << SMOOTHING_SHIFT
        self.raw = reading

    def poll(self, now_ms: int) -> None:

        recent = self._recent
        recent[self._slot] = self._converter.read_u16()
        slot = self._slot + 1
        self._slot = 0 if slot >= 3 else slot
        middle = middle_of_three(recent[0], recent[1], recent[2])
        self._smoothed += middle - (self._smoothed >> SMOOTHING_SHIFT)
        self.raw = self._smoothed >> SMOOTHING_SHIFT

    def deinit(self) -> None:
        pass



