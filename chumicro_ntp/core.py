

import errno
import struct

try:
    from micropython import const
except ImportError:
    def const(value):
        return value



NTP_TO_UNIX = const(2208988800)

PACKET_SIZE = const(48)


CLIENT_FIRST_BYTE = const(0x23)

SERVER_MODE = const(4)


_DRAIN_LIMIT = const(8)

_CLIENT_REQUEST = bytes([CLIENT_FIRST_BYTE]) + b"\x00" * (PACKET_SIZE - 1)


_WOULD_BLOCK_ERRNOS = (errno.EAGAIN,)
if hasattr(errno, "EWOULDBLOCK"):
    _WOULD_BLOCK_ERRNOS = (errno.EAGAIN, errno.EWOULDBLOCK)


class NTPError(OSError):
    pass


def _parse_response(packet: bytes | memoryview) -> int:
    if len(packet) < PACKET_SIZE:
        raise NTPError(f"short SNTP response ({len(packet)} bytes)")

    mode = packet[0] & 0b111
    if mode != SERVER_MODE:
        raise NTPError(f"unexpected SNTP mode {mode} (want {SERVER_MODE})")
    stratum = packet[1]
    if stratum == 0:

        raise NTPError("SNTP kiss-of-death (stratum=0)")

    seconds_1900 = struct.unpack_from(">I", packet, 40)[0]
    if seconds_1900 == 0:

        raise NTPError("SNTP zero transmit timestamp")

    if seconds_1900 < NTP_TO_UNIX:
        seconds_1900 += 0x100000000
    return seconds_1900 - NTP_TO_UNIX


class NTPResult:






    def __init__(self, ticks_started_ms: int) -> None:
        self._ticks_started_ms = ticks_started_ms
        self.done = False
        self._unix_seconds: int | None = None
        self.error: Exception | None = None

    @property
    def unix_seconds(self) -> int:






        if not self.done:
            raise RuntimeError("NTP request still in flight")
        if self.error is not None:
            raise self.error
        return self._unix_seconds

    def _fail(self, exception: Exception) -> None:
        self.error = exception
        self.done = True


class NTPClient:













    @classmethod
    def from_config(
        cls,
        config: object,
        *,
        radio: object | None = None,
        socket: object | None = None,
        transport_factory: object | None = None,
        ticks: object | None = None,
        **constructor_kwargs: object,
    ) -> "NTPClient":

















        if socket is None and transport_factory is None:
            try:
                from chumicro_sockets.sockets_factory import (
                    udp_socket_factory,
                )
            except ImportError as exception:
                raise RuntimeError(
                    "chumicro_sockets.sockets_factory not available "
                    "(excluded via __chumicro_skip_factories__ or "
                    "not on the board); pass transport_factory= or "
                    "socket= explicitly.",
                ) from exception

            transport_factory = udp_socket_factory(radio=radio)

        kwargs = {
            "socket": socket,
            "transport_factory": transport_factory,
            "server": config.get("ntp.server", "pool.ntp.org"),
            "port": config.get("ntp.port", 123),
            "timeout_ms": config.get("ntp.timeout_ms", 5_000),
            "ticks": ticks,
        }
        kwargs.update(constructor_kwargs)
        return cls(**kwargs)

    def __init__(
        self,
        socket: object | None = None,
        *,
        transport_factory: object | None = None,
        server: str = "pool.ntp.org",
        port: int = 123,
        timeout_ms: int = 5_000,
        ticks: object | None = None,
    ) -> None:
        if timeout_ms <= 0:
            raise ValueError("timeout_ms must be positive")
        if (socket is None) == (transport_factory is None):
            raise ValueError(
                "provide exactly one of socket= or transport_factory= "
                "(the factory defers the UDP open to the first query)"
            )
        self.socket = socket
        self._transport_factory = transport_factory
        self.server = server
        self.port = port
        self.timeout_ms = timeout_ms
        if ticks is None:
            from chumicro_timing import ticks
        self._ticks = ticks
        self._result: NTPResult | None = None
        self._recv_buffer = bytearray(PACKET_SIZE)
        self._recv_view = memoryview(self._recv_buffer)

    @property
    def busy(self) -> bool:

        return self._result is not None and not self._result.done

    def query(self) -> NTPResult:








        if self.busy:
            raise RuntimeError(
                "NTP query already in flight; await result before re-querying",
            )
        if self.socket is None:
            if self._transport_factory is None:
                raise RuntimeError(
                    "socket closed; pass transport_factory= to reopen on demand",
                )
            self.socket = self._transport_factory()

        self._drain_socket()
        now_ms = self._ticks.ticks_ms()
        result = NTPResult(ticks_started_ms=now_ms)
        try:
            self.socket.sendto(_CLIENT_REQUEST, self.server, self.port)
        except OSError as send_error:
            result._fail(send_error)
            self._result = result
            return result
        self._result = result
        return result

    def _drain_socket(self) -> None:
        for _ in range(_DRAIN_LIMIT):
            try:
                received_count, _sender = self.socket.recvfrom_into(
                    self._recv_buffer,
                )
            except OSError:
                return
            if received_count == 0:
                return

    def check(self, now_ms: int) -> bool:





        return self.busy

    def handle(self, now_ms: int) -> None:





        result = self._result
        if result is None or result.done:
            return
        try:
            received_count, _sender = self.socket.recvfrom_into(
                self._recv_buffer,
            )
        except OSError as recv_error:
            if recv_error.errno in _WOULD_BLOCK_ERRNOS:
                self._check_timeout(result, now_ms)
                return
            result._fail(recv_error)
            return
        if received_count == 0:
            self._check_timeout(result, now_ms)
            return
        try:
            unix_seconds = _parse_response(
                self._recv_view[:received_count],
            )
        except NTPError as parse_error:
            result._fail(parse_error)
            return
        result._unix_seconds = unix_seconds
        result.done = True

    def _check_timeout(self, result: "NTPResult", now_ms: int) -> None:
        elapsed_ms = self._ticks.ticks_diff(now_ms, result._ticks_started_ms)
        if elapsed_ms >= self.timeout_ms:
            result._fail(
                NTPError(f"SNTP query timed out after {elapsed_ms} ms"),
            )

    def cancel(self) -> bool:





        if not self.busy:
            return False
        self._result._fail(NTPError("canceled"))
        return True

    def close(self) -> None:






        if self.socket is None:
            return
        try:
            self.socket.close()
        except OSError:
            pass
        self.socket = None
