











SMOOTHING_SHIFT = 4

def middle_of_three(first: int, second: int, third: int) -> int:











    if first > second:
        first, second = second, first
    if second > third:
        second = third
    if first > second:
        second = first
    return second


class EncoderSource:










    raw_position = 0

    def poll(self, now_ms: int) -> None:

        raise NotImplementedError

    def deinit(self) -> None:

        raise NotImplementedError


class AnalogSource:








    raw = 0

    def poll(self, now_ms: int) -> None:

        raise NotImplementedError

    def deinit(self) -> None:

        raise NotImplementedError
