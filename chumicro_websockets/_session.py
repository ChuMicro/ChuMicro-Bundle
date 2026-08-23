import errno
from collections import deque

try:
    from micropython import const
except ImportError:
    def const(value):
        return value

from chumicro_websockets._wire import (
    CLOSE_BAD_DATA,
    CLOSE_INTERNAL_ERROR,
    CLOSE_NORMAL,
    CLOSE_PROTOCOL_ERROR,
    CLOSE_TOO_BIG,
    DEFAULT_MAX_INBOUND_QUEUE_SIZE,
    OPCODE_BINARY,
    OPCODE_CLOSE,
    OPCODE_CONTINUATION,
    OPCODE_PING,
    OPCODE_PONG,
    OPCODE_TEXT,
    FrameParser,
    FrameParseState,
    WebSocketBackpressureError,
    WebSocketHandshakeError,
    WebSocketProtocolError,
    WebSocketState,
    WebSocketStateError,
    WebSocketTimeoutError,
    encode_close_payload,
    encode_frame,
    parse_close_payload,
    validate_text_payload,
)


_MAX_EMPTY_FRAGMENT_RUN = const(64)





_IO_READ = 1
_IO_WRITE = 2


_TX_QUEUE_HEADROOM = const(8)


class WhenOversized:



    DROP_SILENT = "drop_silent"


    DROP_WITH_EVENT = "drop_with_event"


    DISCONNECT = "disconnect"


def _no_callback(*_args, **_kwargs):
    return None


def _new_tx_queue(maxlen):

    try:
        return deque((), maxlen, 1)
    except TypeError:
        return deque((), maxlen)


def _force_non_blocking(socket):

    setblocking = getattr(socket, "setblocking", None)
    if setblocking is None:
        return
    try:
        setblocking(False)
    except OSError:
        pass


class InboundMessage:


    def __init__(self, *, is_text: bool, text: str | None = None, data: bytes | None = None):
        self.is_text = is_text
        self.text = text
        self.data = data

    def __repr__(self):
        if self.is_text:
            return f"InboundMessage(text={self.text!r})"
        return f"InboundMessage(data={len(self.data)} bytes)"


class _InboundWait:


    io_socket = None


_INBOUND_WAIT = _InboundWait()


class _BaseSession:
    _peer_label: str = ""
    _inbound_mask_required: bool = False

    def _init_session_state(
        self,
        socket,
        *,
        max_message_bytes: int,
        recv_budget_per_tick: int,
        send_budget_per_tick: int,
        max_tx_queue_size: int,
        when_oversized: str,
        pong_timeout_ms: int,
        handshake_timeout_ms: int,
        close_timeout_ms: int,
        ticks,
        max_inbound_queue_size: int = DEFAULT_MAX_INBOUND_QUEUE_SIZE,
    ) -> None:
        self._socket = socket
        self._max_message_bytes = max_message_bytes
        self._recv_budget_per_tick = recv_budget_per_tick
        self._send_budget_per_tick = send_budget_per_tick
        self._max_tx_queue_size = max_tx_queue_size
        self._when_oversized = when_oversized
        self._pong_timeout_ms = pong_timeout_ms
        self._handshake_timeout_ms = handshake_timeout_ms
        self._close_timeout_ms = close_timeout_ms
        self._max_inbound_queue_size = max_inbound_queue_size

        self._ticks = ticks


        recv_scratch_size = min(recv_budget_per_tick, 512)
        self._recv_buffer = bytearray(recv_scratch_size)
        self._recv_view = memoryview(self._recv_buffer)

        self.state = WebSocketState.CONNECTING
        self._frame_parser = FrameParser(max_payload_bytes=max_message_bytes)
        self._post_handshake_carry = b""

        self._tx_queue = _new_tx_queue(max_tx_queue_size + _TX_QUEUE_HEADROOM)

        self._tx_queue_hard_cap = max_tx_queue_size + _TX_QUEUE_HEADROOM

        self._tx_partial_buffer = None
        self._tx_partial_offset = 0

        self._inbound_message_buffer = bytearray()
        self._inbound_message_opcode = None
        self._inbound_oversized = False
        self._inbound_queue = None
        self._inbound_to_queue = False

        self._inbound_reported_length = 0
        self._inbound_empty_fragment_run = 0

        self._handshake_send_buffer = None

        self._handshake_send_view = None
        self._handshake_send_offset = 0

        self._handshake_deadline_ticks = None
        self._close_deadline_ticks = None
        self._pending_ping_deadline_ticks = None
        self._next_auto_ping_ticks = None

        self.last_close_code = None
        self.last_close_reason = ""
        self.last_error = None


        self.on_text = _no_callback
        self.on_binary = _no_callback
        self.on_ping = _no_callback
        self.on_pong = _no_callback
        self.on_close = _no_callback
        self.on_oversized = _no_callback

    @property
    def io_socket(self):

        if self._socket is None:
            return None
        if self.state == WebSocketState.CLOSED:
            return None
        return self._socket

    def io_interest(self, now_ms):

        if self.state in (WebSocketState.OPEN, WebSocketState.CLOSING):
            interest = _IO_READ
            if bool(self._tx_queue) or self._tx_partial_buffer is not None:
                interest |= _IO_WRITE
            return interest
        if self.state == WebSocketState.CONNECTING:
            interest = 0
            if self._connecting_wants_read(now_ms):
                interest |= _IO_READ
            if self._connecting_wants_write(now_ms):
                interest |= _IO_WRITE
            return interest
        return 0

    def _connecting_wants_read(self, now_ms) -> bool:
        return False

    def _connecting_wants_write(self, now_ms) -> bool:
        return False

    def next_deadline(self, now_ms):



        ticks_diff = self._ticks.ticks_diff
        nearest = self._handshake_deadline_ticks
        candidate = self._close_deadline_ticks
        if candidate is not None and (nearest is None or ticks_diff(candidate, nearest) < 0):
            nearest = candidate
        candidate = self._pending_ping_deadline_ticks
        if candidate is not None and (nearest is None or ticks_diff(candidate, nearest) < 0):
            nearest = candidate
        candidate = self._next_auto_ping_ticks
        if candidate is not None and (nearest is None or ticks_diff(candidate, nearest) < 0):
            nearest = candidate
        return nearest

    def send_text(self, text: str) -> None:






        if self.state != WebSocketState.OPEN:
            raise WebSocketStateError(
                f"send_text() requires OPEN state, was {self.state}",
            )
        self._enqueue_user_frame(OPCODE_TEXT, text.encode("utf-8"))

    def send_binary(self, data) -> None:






        if self.state != WebSocketState.OPEN:
            raise WebSocketStateError(
                f"send_binary() requires OPEN state, was {self.state}",
            )



        if not isinstance(data, (bytes, bytearray, memoryview)):
            raise TypeError(
                f"send_binary() requires bytes, bytearray, or memoryview; "
                f"got {type(data).__name__}",
            )

        self._enqueue_user_frame(OPCODE_BINARY, data)

    def send_ping(self, payload: bytes = b"") -> None:

        if self.state != WebSocketState.OPEN:
            raise WebSocketStateError(
                f"send_ping() requires OPEN state, was {self.state}",
            )
        self._enqueue_user_frame(OPCODE_PING, bytes(payload))
        self._arm_pong_deadline()

    def close(self, code: int = CLOSE_NORMAL, reason: str = "") -> None:





        if self.state in (WebSocketState.CLOSING, WebSocketState.CLOSED):
            raise WebSocketStateError(
                f"close() not allowed in state {self.state}",
            )
        self._send_close(code, reason, None)

    def next_message(self):





        if self._inbound_queue is None:

            self._inbound_queue = deque((), self._max_inbound_queue_size)
            self._inbound_to_queue = True
        while True:
            if self._inbound_queue:
                return self._inbound_queue.popleft()
            if self.state == WebSocketState.CLOSED:
                return None
            yield _INBOUND_WAIT

    def _outbound_mask(self):
        raise NotImplementedError

    def _send_handshake_chunk(self, now_ms: int) -> None:
        remaining = self._handshake_send_view[self._handshake_send_offset:]
        if not remaining:
            self._on_handshake_send_complete(now_ms)
            return
        chunk = remaining[: self._send_budget_per_tick]
        try:
            sent = self._socket.send(chunk)
        except OSError as send_error:
            if send_error.errno == errno.EAGAIN:
                return
            self._fail_with_error(
                WebSocketHandshakeError(
                    f"socket error during handshake send: {send_error!r}",
                ),
            )
            return
        if sent is None or sent == 0:
            return
        self._handshake_send_offset += sent
        if self._handshake_send_offset >= len(self._handshake_send_buffer):
            self._on_handshake_send_complete(now_ms)

    def _on_handshake_send_complete(self, now_ms: int) -> None:
        raise NotImplementedError

    def _enqueue_user_frame(self, opcode: int, payload: bytes) -> None:
        if len(self._tx_queue) >= self._max_tx_queue_size:
            raise WebSocketBackpressureError(
                f"TX queue is full ({self._max_tx_queue_size} messages); "
                f"call handle() to drain before sending more",
            )
        encoded = encode_frame(opcode, payload, fin=True, mask=self._outbound_mask())
        self._tx_queue.append(encoded)

    def _enqueue_internal_frame(self, opcode: int, payload: bytes) -> None:

        limit = self._tx_queue_hard_cap
        if opcode != OPCODE_CLOSE:
            limit -= 1
        if len(self._tx_queue) >= limit:
            return
        encoded = encode_frame(opcode, payload, fin=True, mask=self._outbound_mask())
        self._tx_queue.append(encoded)

    def _drain_inbound(self, now_ms: int) -> None:
        remaining = self._recv_budget_per_tick
        while remaining > 0:
            chunk = self._recv_chunk(remaining)
            if chunk is None:
                return
            if not chunk:
                self._fail_with_error(
                    WebSocketProtocolError(
                        "peer closed TCP without sending a CLOSE frame",
                    ),
                )
                return
            self._feed_frame_bytes(chunk, now_ms)
            if self.state == WebSocketState.CLOSED:
                return
            remaining -= len(chunk)

    def _feed_frame_bytes(self, chunk: bytes, now_ms: int) -> None:
        frame_parser = self._frame_parser

        if frame_parser.state == FrameParseState.ERROR:
            return
        offset = 0
        chunk_length = len(chunk)
        while offset < chunk_length:
            try:
                consumed = frame_parser.feed(chunk, offset)
            except WebSocketProtocolError as protocol_error:
                self._send_close(CLOSE_PROTOCOL_ERROR, str(protocol_error), now_ms)
                self.last_error = protocol_error
                return
            if consumed == 0:

                return
            offset += consumed
            if frame_parser.state == FrameParseState.FRAME_READY:
                try:
                    self._dispatch_frame(now_ms)
                finally:

                    if self.state != WebSocketState.CLOSED:
                        frame_parser.reset()
                if self.state == WebSocketState.CLOSED:
                    return

    def _dispatch_frame(self, now_ms: int) -> None:
        opcode = self._frame_parser.opcode
        fin = self._frame_parser.fin
        had_mask = self._frame_parser.had_mask
        payload = self._frame_parser.payload

        if had_mask != self._inbound_mask_required:
            if self._inbound_mask_required:
                message = f"{self._peer_label} frame must be masked"
            else:
                message = f"{self._peer_label} frame must not be masked"
            self._send_close(CLOSE_PROTOCOL_ERROR, message, now_ms)
            return

        if opcode == OPCODE_CLOSE:
            self._handle_close_frame(payload, now_ms)
            return
        if opcode == OPCODE_PING:
            self._handle_ping_frame(payload)
            return
        if opcode == OPCODE_PONG:
            self._handle_pong_frame(payload)
            return

        self._handle_data_frame(opcode, fin, payload, now_ms)

    def _handle_data_frame(self, opcode: int, fin: bool, payload: bytes, now_ms: int) -> None:
        frame_parser = self._frame_parser
        if opcode == OPCODE_CONTINUATION:
            if self._inbound_message_opcode is None:
                self._send_close(
                    CLOSE_PROTOCOL_ERROR,
                    "CONTINUATION frame with no in-progress message",
                    now_ms,
                )
                return
        else:

            if self._inbound_message_opcode is not None:
                self._send_close(
                    CLOSE_PROTOCOL_ERROR,
                    f"new {opcode:#x} frame in the middle of a fragmented message",
                    now_ms,
                )
                return
            self._inbound_message_opcode = opcode
        self._inbound_reported_length += frame_parser.reported_length
        if frame_parser.reported_length > 0:
            self._inbound_empty_fragment_run = 0
        elif not fin:
            self._inbound_empty_fragment_run += 1
            if self._inbound_empty_fragment_run > _MAX_EMPTY_FRAGMENT_RUN:
                self._send_close(
                    CLOSE_PROTOCOL_ERROR,
                    "too many zero-length continuation frames",
                    now_ms,
                )
                return
        if frame_parser.oversized:

            self._inbound_oversized = True
        elif fin and not self._inbound_message_buffer:



            if len(payload) > self._max_message_bytes:
                self._inbound_oversized = True
            else:
                message_opcode = self._inbound_message_opcode
                self._reset_inbound_state()
                self._deliver_message(message_opcode, payload, now_ms)
                return
        else:
            self._extend_inbound_buffer(payload)

        if not fin:
            return

        if self._inbound_oversized:
            self._finish_oversized_message(now_ms)
            return

        message_opcode = self._inbound_message_opcode
        message_payload = bytes(self._inbound_message_buffer)
        self._reset_inbound_state()
        self._deliver_message(message_opcode, message_payload, now_ms)

    def _deliver_message(self, message_opcode: int, message_payload: bytes, now_ms: int) -> None:
        if message_opcode == OPCODE_TEXT:
            try:
                text = validate_text_payload(message_payload)
            except WebSocketProtocolError as utf8_error:
                self._send_close(CLOSE_BAD_DATA, str(utf8_error), now_ms)
                self.last_error = utf8_error
                return
            if self._inbound_to_queue:
                self._inbound_queue.append(InboundMessage(is_text=True, text=text))
            else:
                self.on_text(text)
        elif self._inbound_to_queue:
            self._inbound_queue.append(InboundMessage(is_text=False, data=message_payload))
        else:
            self.on_binary(message_payload)

    def _extend_inbound_buffer(self, payload: bytes) -> None:
        if self._inbound_oversized:
            return
        projected = len(self._inbound_message_buffer) + len(payload)
        if projected > self._max_message_bytes:
            self._inbound_oversized = True
            return
        self._inbound_message_buffer.extend(payload)

    def _finish_oversized_message(self, now_ms: int) -> None:
        reported_length = self._inbound_reported_length
        self._reset_inbound_state()
        policy = self._when_oversized
        if policy == WhenOversized.DROP_SILENT:
            return
        if policy == WhenOversized.DROP_WITH_EVENT:
            self.on_oversized(reported_length)
            return
        if policy == WhenOversized.DISCONNECT:
            self._send_close(
                CLOSE_TOO_BIG,
                f"message exceeded max_message_bytes={self._max_message_bytes}",
                now_ms,
            )

    def _reset_inbound_state(self) -> None:
        self._inbound_message_buffer = bytearray()
        self._inbound_message_opcode = None
        self._inbound_oversized = False
        self._inbound_reported_length = 0
        self._inbound_empty_fragment_run = 0

    def _handle_close_frame(self, payload: bytes, now_ms: int) -> None:
        try:
            code, reason = parse_close_payload(payload)
        except WebSocketProtocolError as parse_error:
            self._send_close(CLOSE_PROTOCOL_ERROR, str(parse_error), now_ms)
            self.last_error = parse_error
            return

        if self.state == WebSocketState.CLOSING:
            if self.last_close_code is None:
                self.last_close_code = code
                self.last_close_reason = reason
            self._finalize_closed()
            return


        self.last_close_code = code
        self.last_close_reason = reason
        self._send_close(code if code is not None else CLOSE_NORMAL, "", now_ms)
        self._finalize_closed()

    def _handle_ping_frame(self, payload: bytes) -> None:
        self._enqueue_internal_frame(OPCODE_PONG, payload)
        self.on_ping(payload)

    def _handle_pong_frame(self, payload: bytes) -> None:
        self._pending_ping_deadline_ticks = None
        self.on_pong(payload)

    def _drain_outbound(self) -> None:
        budget = self._send_budget_per_tick
        while budget > 0:
            if self._tx_partial_buffer is None:
                if not self._tx_queue:
                    return

                self._tx_partial_buffer = memoryview(self._tx_queue.popleft())
                self._tx_partial_offset = 0
            buffer = self._tx_partial_buffer
            offset = self._tx_partial_offset
            chunk = buffer[offset : offset + budget]
            try:
                sent = self._socket.send(chunk)
            except OSError as send_error:
                if send_error.errno == errno.EAGAIN:
                    return
                self._fail_with_error(
                    WebSocketProtocolError(
                        f"socket error during send: {send_error!r}",
                    ),
                )
                return
            if sent is None or sent == 0:
                return
            offset += sent
            if offset >= len(buffer):
                self._tx_partial_buffer = None
                self._tx_partial_offset = 0
            else:
                self._tx_partial_offset = offset
            budget -= sent

    def _recv_chunk(self, max_bytes: int):
        cap = min(max_bytes, len(self._recv_buffer))
        try:
            received = self._socket.recv_into(self._recv_view, cap)
        except OSError as recv_error:
            if recv_error.errno == errno.EAGAIN:
                return None
            self._fail_with_error(
                WebSocketProtocolError(
                    f"socket error during recv: {recv_error!r}",
                ),
            )
            return None
        if received is None:
            return None
        if received == 0:
            return b""
        return self._recv_view[:received]

    def _send_close(self, code: int, reason: str, now_ms: int | None) -> None:
        if self.state in (WebSocketState.CLOSING, WebSocketState.CLOSED):
            return
        try:
            payload = encode_close_payload(code, reason)
        except WebSocketProtocolError:

            payload = b""
        self._enqueue_internal_frame(OPCODE_CLOSE, payload)

        if self.last_close_code is None:
            self.last_close_code = code
            self.last_close_reason = reason
        self.state = WebSocketState.CLOSING
        if now_ms is None:

            now_ms = self._ticks.ticks_ms()
        self._close_deadline_ticks = self._ticks.ticks_add(
            now_ms,
            self._close_timeout_ms,
        )

    def _drop_transport(self) -> None:


        try:
            if self._socket is not None:
                self._socket.close()
        except Exception:
            pass
        self.state = WebSocketState.CLOSED
        self._handshake_deadline_ticks = None
        self._close_deadline_ticks = None
        self._pending_ping_deadline_ticks = None

    def _finalize_closed(self) -> None:

        if self._tx_queue or self._tx_partial_buffer is not None:
            self._drain_outbound()
        self._drop_transport()
        self._on_finalized()
        code = self.last_close_code if self.last_close_code is not None else CLOSE_NORMAL
        self.on_close(code, self.last_close_reason)

    def _fail_with_error(self, error) -> None:
        if self.last_error is None:
            self.last_error = error
        if self.last_close_code is None:
            self.last_close_code = CLOSE_INTERNAL_ERROR
            self.last_close_reason = str(error)
        self._drop_transport()
        self._on_finalized()
        self.on_close(self.last_close_code, self.last_close_reason)

    def _on_finalized(self) -> None:
        pass

    def _check_timeouts(self, now_ms: int) -> bool:
        ticks_diff = self._ticks.ticks_diff
        if (
            self._handshake_deadline_ticks is not None
            and ticks_diff(self._handshake_deadline_ticks, now_ms) <= 0
        ):
            self._fail_with_error(
                WebSocketTimeoutError(
                    f"handshake exceeded {self._handshake_timeout_ms} ms",
                ),
            )
            return True
        if (
            self._close_deadline_ticks is not None
            and ticks_diff(self._close_deadline_ticks, now_ms) <= 0
        ):
            self.last_error = WebSocketTimeoutError(
                f"peer did not send CLOSE within {self._close_timeout_ms} ms",
            )
            self._finalize_closed()
            return True
        if (
            self._pending_ping_deadline_ticks is not None
            and ticks_diff(self._pending_ping_deadline_ticks, now_ms) <= 0
        ):
            self._fail_with_error(
                WebSocketTimeoutError(
                    f"no PONG within {self._pong_timeout_ms} ms of last PING",
                ),
            )
            return True
        return False

    def _arm_pong_deadline(self, now_ms: int | None = None) -> None:
        if self._pong_timeout_ms is None:
            return
        if self._pending_ping_deadline_ticks is not None:
            return
        if now_ms is None:

            now_ms = self._ticks.ticks_ms()
        self._pending_ping_deadline_ticks = self._ticks.ticks_add(
            now_ms,
            self._pong_timeout_ms,
        )
