

__chumicro_runtimes__ = ("circuitpython",)

from chumicro_buttons._adapters.base import ButtonSource

try:
    from micropython import const
except ImportError:
    def const(value):
        return value




SCANS_PER_SETTLE_WINDOW = const(4)



MINIMUM_SCAN_INTERVAL_SECONDS = 0.001


def keypad_scan_timing(settle_ms: int) -> tuple[float, int]:







    if settle_ms <= 0:
        return MINIMUM_SCAN_INTERVAL_SECONDS, 1
    if settle_ms < SCANS_PER_SETTLE_WINDOW:
        scans = int(settle_ms)
        return MINIMUM_SCAN_INTERVAL_SECONDS, scans if scans >= 1 else 1
    return settle_ms / SCANS_PER_SETTLE_WINDOW / 1000, SCANS_PER_SETTLE_WINDOW


def keypad_module() -> object:





    try:
        import keypad
    except ImportError:


        raise RuntimeError(
            "this CircuitPython build has no keypad module, which is what scans the "
            "keys.  Flash a full build of CircuitPython for this board, or build the "
            "keys with source=FakeButtonSource(...) from chumicro_buttons.testing and "
            "drive them yourself.",
        ) from None
    return keypad


class _KeypadScanSource(ButtonSource):






    def _adopt_scanner(self, scanner: object, event: object) -> None:




        self._scanner = scanner
        self._events = scanner.events
        self._event = event
        self.key_count = scanner.key_count


        scanner.reset()

    def poll(self, now_ms: int) -> None:



        return None

    def next_event(self) -> bool:






        events = self._events
        event = self._event
        if events.get_into(event):
            self.event_key = event.key_number
            self.event_pressed = event.pressed


            self.event_ms = event.timestamp
            return True
        if events.overflowed:
            self.overflowed = True


            events.clear()
        return False

    def deinit(self) -> None:

        self._scanner.deinit()


class CpButtonSource(_KeypadScanSource):







    def __init__(self, pins: object, *, active_low: bool, settle_ms: int) -> None:
        keypad = keypad_module()

        interval_seconds, debounce_threshold = keypad_scan_timing(settle_ms)
        self._adopt_scanner(
            keypad.Keys(
                pins,
                value_when_pressed=not active_low,
                interval=interval_seconds,
                debounce_threshold=debounce_threshold,
            ),
            keypad.Event(),
        )


class CpKeyMatrixSource(_KeypadScanSource):







    def __init__(
        self,
        row_pins: object,
        column_pins: object,
        *,
        columns_to_anodes: bool = True,
        settle_ms: int,
    ) -> None:
        keypad = keypad_module()

        interval_seconds, debounce_threshold = keypad_scan_timing(settle_ms)
        self._adopt_scanner(
            keypad.KeyMatrix(
                row_pins,
                column_pins,
                columns_to_anodes=columns_to_anodes,
                interval=interval_seconds,
                debounce_threshold=debounce_threshold,
            ),
            keypad.Event(),
        )
