

import sys

from chumicro_buttons.core import (
    DEFAULT_LONG_PRESS_MS,
    DEFAULT_REPEAT_DELAY_MS,
    DEFAULT_SETTLE_MS,
    Buttons,
)


def _select_matrix_source(row_pins, column_pins, *, columns_to_anodes=True, settle_ms, ticks):





    runtime_name = sys.implementation.name
    if runtime_name == "circuitpython":
        from chumicro_buttons._adapters.cp import CpKeyMatrixSource
        return CpKeyMatrixSource(
            row_pins, column_pins, columns_to_anodes=columns_to_anodes, settle_ms=settle_ms,
        )
    if runtime_name == "micropython":
        from chumicro_buttons._adapters.mp import MpKeyMatrixSource
        return MpKeyMatrixSource(
            row_pins,
            column_pins,
            columns_to_anodes=columns_to_anodes,
            settle_ms=settle_ms,
            ticks=ticks,
        )
    raise RuntimeError(
        "CPython has no GPIO to scan.  Build the matrix with "
        "source=FakeButtonSource(...) from chumicro_buttons.testing and drive it "
        "from your test, or run this on CircuitPython or MicroPython.",
    )


class KeyMatrix(Buttons):






























    def __init__(
        self,
        row_pins: object | None = None,
        column_pins: object | None = None,
        *,
        ticks: object,
        source: object | None = None,
        columns_to_anodes: bool = True,
        settle_ms: int = DEFAULT_SETTLE_MS,
        long_press_ms: int = DEFAULT_LONG_PRESS_MS,
        repeat_ms: int = 0,
        repeat_delay_ms: int = DEFAULT_REPEAT_DELAY_MS,
        click_ms: int = 0,
    ) -> None:
        if source is None:
            if row_pins is None or column_pins is None:
                raise ValueError("KeyMatrix needs either row_pins and column_pins, or source=")
            if len(row_pins) == 0 or len(column_pins) == 0:


                raise ValueError("KeyMatrix was given an empty row_pins or column_pins")
            source = _select_matrix_source(
                row_pins,
                column_pins,
                columns_to_anodes=columns_to_anodes,
                settle_ms=settle_ms,
                ticks=ticks,
            )
        super().__init__(
            source=source,
            long_press_ms=long_press_ms,
            repeat_ms=repeat_ms,
            repeat_delay_ms=repeat_delay_ms,
            click_ms=click_ms,
            ticks=ticks,
        )
