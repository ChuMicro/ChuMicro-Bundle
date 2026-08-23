

__chumicro_runtimes__ = ("micropython",)

import array

from chumicro_buttons._adapters.base import ButtonSource

try:
    from micropython import const
except ImportError:
    def const(value):
        return value




DEFAULT_RING_DEPTH = const(32)


class _KeyEdgeCapture:






    def __init__(self, source: object, key_index: int) -> None:
        self._source = source
        self._key_index = key_index

    def record(self, pin: object) -> None:

        self._source._capture_edge(self._key_index, pin.value())


class MpButtonSource(ButtonSource):
















    def __init__(
        self,
        pins: object,
        *,
        active_low: bool,
        settle_ms: int,
        ticks: object,
        ring_depth: int = DEFAULT_RING_DEPTH,
    ) -> None:
        from machine import Pin

        self._ticks = ticks


        self._ticks_ms = ticks.ticks_ms
        self._settle_ms = settle_ms
        self._pressed_level = 0 if active_low else 1

        pull = Pin.PULL_UP if active_low else Pin.PULL_DOWN
        for pin in pins:
            pin.init(Pin.IN, pull)
        self._pins = tuple(pins)
        self.key_count = len(self._pins)

        self._ring_depth = ring_depth
        self._edge_codes = array.array("H", [0] * ring_depth)
        self._edge_times = array.array("i", [0] * ring_depth)
        self._write_index = 0
        self._read_index = 0


        self.overflowed = False


        self._dropped_edges = False





        self._believed = array.array("b", [0] * self.key_count)
        self._pending = array.array("b", [0] * self.key_count)
        self._change_ms = array.array("i", [0] * self.key_count)
        self._sweep_key = 0



        started_ms = self._ticks_ms()
        self._now_ms = started_ms
        key_index = 0
        while key_index < self.key_count:
            if self._pins[key_index].value() == self._pressed_level:
                self._pending[key_index] = 1
            self._change_ms[key_index] = started_ms
            key_index += 1

        self._captures = []
        trigger = Pin.IRQ_RISING | Pin.IRQ_FALLING
        key_index = 0
        while key_index < self.key_count:
            capture = _KeyEdgeCapture(self, key_index)
            self._captures.append(capture)
            self._pins[key_index].irq(handler=capture.record, trigger=trigger)
            key_index += 1

    def poll(self, now_ms: int) -> None:





        self._now_ms = now_ms
        return None

    def next_event(self) -> bool:











        codes = self._edge_codes
        times = self._edge_times
        believed = self._believed
        pending = self._pending
        change_ms = self._change_ms
        ticks_diff = self._ticks.ticks_diff
        settle_ms = self._settle_ms
        pressed_level = self._pressed_level
        ring_depth = self._ring_depth
        read_index = self._read_index

        while read_index != self._write_index:
            code = codes[read_index]
            at_ms = times[read_index]
            read_index += 1
            if read_index >= ring_depth:
                read_index = 0
            self._read_index = read_index
            key_index = code >> 1
            sample = 1 if (code & 1) == pressed_level else 0
            if sample == pending[key_index]:
                continue
            departed = pending[key_index]
            departed_ms = change_ms[key_index]
            confirmed = (
                departed != believed[key_index]
                and ticks_diff(at_ms, departed_ms) >= settle_ms
            )
            pending[key_index] = sample
            if not confirmed:



                if sample != believed[key_index]:
                    change_ms[key_index] = at_ms
                continue


            believed[key_index] = departed
            change_ms[key_index] = at_ms
            self.event_key = key_index
            self.event_pressed = departed == 1
            self.event_ms = departed_ms
            return True

        key_count = self.key_count
        now_ms = self._now_ms
        if self._dropped_edges:



            self._dropped_edges = False
            pins = self._pins
            key_index = 0
            while key_index < key_count:
                sample = 1 if pins[key_index].value() == pressed_level else 0
                if sample != pending[key_index]:
                    pending[key_index] = sample
                    if sample != believed[key_index]:
                        change_ms[key_index] = now_ms
                key_index += 1

        key_index = self._sweep_key
        while key_index < key_count:
            if (
                pending[key_index] != believed[key_index]
                and ticks_diff(now_ms, change_ms[key_index]) >= settle_ms
            ):
                believed[key_index] = pending[key_index]
                self.event_key = key_index
                self.event_pressed = pending[key_index] == 1
                self.event_ms = change_ms[key_index]
                self._sweep_key = key_index + 1
                return True
            key_index += 1
        self._sweep_key = 0
        return False

    def deinit(self) -> None:

        pins = self._pins
        key_index = 0
        while key_index < len(pins):
            pins[key_index].irq(handler=None)
            key_index += 1
        self._pins = ()
        self._captures = []
        self._dropped_edges = False

    def _capture_edge(self, key_index: int, level: int) -> None:







        write_index = self._write_index
        next_write = write_index + 1
        if next_write >= self._ring_depth:
            next_write = 0
        if next_write == self._read_index:
            self.overflowed = True
            self._dropped_edges = True
            return
        self._edge_codes[write_index] = (key_index << 1) | level




        self._edge_times[write_index] = self._ticks_ms()
        self._write_index = next_write


class MpKeyMatrixSource(ButtonSource):
















    def __init__(
        self,
        row_pins: object,
        column_pins: object,
        *,
        columns_to_anodes: bool = True,
        settle_ms: int,
        ticks: object,
    ) -> None:
        from machine import Pin

        self._ticks = ticks
        self._pin_type = Pin
        self._settle_ms = settle_ms


        self._drive_level = 0 if columns_to_anodes else 1
        self._rest_pull = Pin.PULL_UP if columns_to_anodes else Pin.PULL_DOWN

        for pin in row_pins:
            pin.init(Pin.IN, self._rest_pull)
        self._rows = tuple(row_pins)
        for pin in column_pins:
            pin.init(Pin.IN, self._rest_pull)
        self._columns = tuple(column_pins)

        self.key_count = len(self._rows) * len(self._columns)
        self._believed = array.array("b", [0] * self.key_count)
        self._pending = array.array("b", [0] * self.key_count)
        self._change_ms = array.array("i", [0] * self.key_count)
        self._sweep_key = 0


        self._sample_ms = 0

    def poll(self, now_ms: int) -> None:

        rows = self._rows
        columns = self._columns
        pin_type = self._pin_type
        believed = self._believed
        pending = self._pending
        change_ms = self._change_ms
        drive_level = self._drive_level
        rest_level = 1 - drive_level
        rest_pull = self._rest_pull
        row_count = len(rows)
        column_count = len(columns)
        row_index = 0
        while row_index < row_count:
            row = rows[row_index]
            row.init(pin_type.OUT, value=drive_level)
            key_index = row_index * column_count
            column_index = 0
            while column_index < column_count:
                sample = 1 if columns[column_index].value() == drive_level else 0
                if sample != pending[key_index]:
                    pending[key_index] = sample
                    if sample != believed[key_index]:
                        change_ms[key_index] = now_ms
                column_index += 1
                key_index += 1



            row.init(pin_type.OUT, value=rest_level)
            row.init(pin_type.IN, rest_pull)
            row_index += 1
        self._sample_ms = now_ms
        return None

    def next_event(self) -> bool:






        believed = self._believed
        pending = self._pending
        change_ms = self._change_ms
        ticks_diff = self._ticks.ticks_diff
        settle_ms = self._settle_ms
        sample_ms = self._sample_ms
        key_index = self._sweep_key
        key_count = self.key_count
        while key_index < key_count:
            if (
                pending[key_index] != believed[key_index]
                and ticks_diff(sample_ms, change_ms[key_index]) >= settle_ms
            ):
                believed[key_index] = pending[key_index]
                self.event_key = key_index
                self.event_pressed = pending[key_index] == 1
                self.event_ms = change_ms[key_index]
                self._sweep_key = key_index + 1
                return True
            key_index += 1
        self._sweep_key = 0
        return False

    def deinit(self) -> None:

        pin_type = self._pin_type
        rest_pull = self._rest_pull
        rows = self._rows
        row_index = 0
        while row_index < len(rows):
            rows[row_index].init(pin_type.IN, rest_pull)
            row_index += 1
        self._rows = ()
        self._columns = ()
