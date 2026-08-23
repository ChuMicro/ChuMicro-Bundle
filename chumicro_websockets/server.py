




import errno

try:
    from micropython import const
except ImportError:
    def const(value):
        return value

from chumicro_websockets._session import (
    _IO_READ,
    WhenOversized,
    _BaseSession,
    _force_non_blocking,
)
from chumicro_websockets._wire import (
    CLOSE_NORMAL,
    DEFAULT_CLOSE_TIMEOUT_MS,
    DEFAULT_HANDSHAKE_TIMEOUT_MS,
    DEFAULT_MAX_INBOUND_QUEUE_SIZE,
    DEFAULT_MAX_MESSAGE_BYTES,
    DEFAULT_MAX_TX_QUEUE_SIZE,
    DEFAULT_PONG_TIMEOUT_MS,
    DEFAULT_RECV_BUDGET_PER_TICK,
    DEFAULT_SEND_BUDGET_PER_TICK,
    HandshakeParseState,
    HandshakeRequestParser,
    WebSocketError,
    WebSocketHandshakeError,
    WebSocketState,
    WebSocketStateError,
    encode_server_handshake_response,
    encode_server_rejection,
)



_CONNECTION_PROGRESS_INTERVAL_MS = const(20)


class ServerHandshakePhase:


    READING_REQUEST = "reading_request"
    SENDING_RESPONSE = "sending_response"


class Connection(_BaseSession):


    _peer_label = "client"
    _inbound_mask_required = True

    def __init__(
        self,
        socket,
        now_ms: int,
        *,
        accept_path: str | None,
        max_message_bytes: int,
        recv_budget_per_tick: int,
        send_budget_per_tick: int,
        max_tx_queue_size: int,
        when_oversized: str,
        pong_timeout_ms: int,
        handshake_timeout_ms: int,
        close_timeout_ms: int,
        ticks,
        on_connection_callback,
        max_inbound_queue_size: int = DEFAULT_MAX_INBOUND_QUEUE_SIZE,
    ) -> None:
        _force_non_blocking(socket)
        self._init_session_state(
            socket=socket,
            max_message_bytes=max_message_bytes,
            recv_budget_per_tick=recv_budget_per_tick,
            send_budget_per_tick=send_budget_per_tick,
            max_tx_queue_size=max_tx_queue_size,
            when_oversized=when_oversized,
            pong_timeout_ms=pong_timeout_ms,
            handshake_timeout_ms=handshake_timeout_ms,
            close_timeout_ms=close_timeout_ms,
            max_inbound_queue_size=max_inbound_queue_size,
            ticks=ticks,
        )

        self._accept_path = accept_path
        self._on_connection_callback = on_connection_callback

        self._handshake_phase = ServerHandshakePhase.READING_REQUEST
        self._handshake_request_parser = HandshakeRequestParser()
        self._handshake_deadline_ticks = self._ticks.ticks_add(
            now_ms,
            handshake_timeout_ms,
        )

        self.request_path = ""
        self.request_headers = None

    def check(self, now_ms: int) -> bool:

        return self.state != WebSocketState.CLOSED

    def _connecting_wants_read(self, now_ms) -> bool:
        return self._handshake_phase == ServerHandshakePhase.READING_REQUEST

    def _connecting_wants_write(self, now_ms) -> bool:
        return self._handshake_phase == ServerHandshakePhase.SENDING_RESPONSE

    def handle(self, now_ms: int) -> None:

        if self.state == WebSocketState.CLOSED:
            return

        if self._check_timeouts(now_ms):
            return

        if self.state == WebSocketState.CONNECTING:
            if self._handshake_phase == ServerHandshakePhase.READING_REQUEST:
                self._receive_handshake_chunk()
            elif self._handshake_phase == ServerHandshakePhase.SENDING_RESPONSE:
                self._send_handshake_chunk(now_ms)
            return


        self._drain_inbound(now_ms)
        self._drain_outbound()

    def _outbound_mask(self):

        return None

    def _on_finalized(self) -> None:
        self._handshake_deadline_ticks = None

    def _receive_handshake_chunk(self) -> None:
        chunk = self._recv_chunk(self._recv_budget_per_tick)
        if chunk is None:
            return
        if not chunk:
            self._fail_with_error(
                WebSocketHandshakeError(
                    "client closed connection mid-handshake",
                ),
            )
            return
        try:
            self._handshake_request_parser.feed(chunk)
        except WebSocketHandshakeError as handshake_error:
            self._reject(400, "Bad Request", str(handshake_error))
            return
        if self._handshake_request_parser.state != HandshakeParseState.DONE:
            return
        if (
            self._accept_path is not None
            and self._handshake_request_parser.path != self._accept_path
        ):
            self._reject(
                404,
                "Not Found",
                f"path {self._handshake_request_parser.path!r} not handled",
            )
            return
        self._handshake_send_buffer = encode_server_handshake_response(
            self._handshake_request_parser.client_key,
        )
        self._handshake_send_view = memoryview(self._handshake_send_buffer)
        self._handshake_send_offset = 0
        self.request_path = self._handshake_request_parser.path
        self.request_headers = self._handshake_request_parser.headers
        self._post_handshake_carry = self._handshake_request_parser.leftover
        self._handshake_phase = ServerHandshakePhase.SENDING_RESPONSE

    def _on_handshake_send_complete(self, now_ms: int) -> None:
        self._enter_open(now_ms)

    def _enter_open(self, now_ms: int) -> None:
        self._handshake_request_parser = None
        self._handshake_send_view = None
        self._handshake_send_buffer = None
        self._handshake_phase = None
        self._handshake_deadline_ticks = None
        self.state = WebSocketState.OPEN

        try:
            self._on_connection_callback(self)
        except Exception as callback_error:
            self._fail_with_error(
                WebSocketError(
                    f"on_connection callback raised: {callback_error!r}",
                ),
            )
            return

        if self._post_handshake_carry:
            self._feed_frame_bytes(self._post_handshake_carry, now_ms)
            self._post_handshake_carry = b""

    def _reject(self, status_code: int, reason_phrase: str, message: str) -> None:
        self._send_rejection_response(
            status_code, reason_phrase, message.encode("utf-8"),
        )
        self.last_error = WebSocketHandshakeError(message)

    def _send_rejection_response(
        self,
        status_code: int,
        reason_phrase: str,
        body: bytes,
    ) -> None:
        response = encode_server_rejection(status_code, reason_phrase, body=body)
        try:
            self._socket.send(response)
        except Exception:
            pass
        self._drop_transport()





class WebSocketServer:


    @classmethod
    def from_config(
        cls,
        config: object,
        on_connection: object,
        *,
        radio: object | None = None,
        listener: object | None = None,
        listener_factory: object | None = None,
        accept_path: str | None = None,
        max_connections: int = 2,
        ticks: object | None = None,
        **constructor_kwargs: object,
    ) -> "WebSocketServer":










        if listener is None and listener_factory is None:

            try:
                from chumicro_sockets.sockets_factory import (
                    listener_factory as sockets_listener_factory,
                )
            except ImportError as exception:
                raise RuntimeError(
                    "chumicro_sockets.sockets_factory not available "
                    "(excluded via __chumicro_skip_factories__ or "
                    "not on the board); pass listener= or "
                    "listener_factory= explicitly.",
                ) from exception
            listener_factory = sockets_listener_factory(
                config.get("websockets.server.host", "0.0.0.0"),
                config.get("websockets.server.port", 8765),
                radio=radio,
            )
        kwargs = {
            "listener": listener,
            "listener_factory": listener_factory,
            "on_connection": on_connection,
            "max_connections": max_connections,
            "accept_path": accept_path,
            "max_message_bytes": config.get(
                "websockets.server.max_message_bytes",
                DEFAULT_MAX_MESSAGE_BYTES,
            ),
            "ticks": ticks,
        }
        kwargs.update(constructor_kwargs)
        return cls(**kwargs)

    def __init__(
        self,
        listener: object | None = None,
        on_connection: object | None = None,
        *,
        listener_factory: object | None = None,
        max_connections: int = 2,
        accept_path: str | None = None,
        max_message_bytes: int = DEFAULT_MAX_MESSAGE_BYTES,
        recv_budget_per_tick: int = DEFAULT_RECV_BUDGET_PER_TICK,
        send_budget_per_tick: int = DEFAULT_SEND_BUDGET_PER_TICK,
        max_tx_queue_size: int = DEFAULT_MAX_TX_QUEUE_SIZE,
        when_oversized: str = WhenOversized.DROP_WITH_EVENT,
        pong_timeout_ms: int = DEFAULT_PONG_TIMEOUT_MS,
        handshake_timeout_ms: int = DEFAULT_HANDSHAKE_TIMEOUT_MS,
        close_timeout_ms: int = DEFAULT_CLOSE_TIMEOUT_MS,
        max_inbound_queue_size: int = DEFAULT_MAX_INBOUND_QUEUE_SIZE,
        ticks: object | None = None,
    ) -> None:

























        if (listener is None) == (listener_factory is None):
            raise ValueError(
                "provide exactly one of listener= or listener_factory= "
                "(the factory defers the bind to the first handle() tick)"
            )
        if on_connection is None:
            raise ValueError("on_connection is required")
        self.io_socket = listener
        self._listener_factory = listener_factory
        self._on_connection = on_connection
        self._max_connections = max_connections
        self._accept_path = accept_path
        self._max_message_bytes = max_message_bytes
        self._recv_budget_per_tick = recv_budget_per_tick
        self._send_budget_per_tick = send_budget_per_tick
        self._max_tx_queue_size = max_tx_queue_size
        self._when_oversized = when_oversized
        self._pong_timeout_ms = pong_timeout_ms
        self._handshake_timeout_ms = handshake_timeout_ms
        self._close_timeout_ms = close_timeout_ms
        self._max_inbound_queue_size = max_inbound_queue_size

        if ticks is None:
            from chumicro_timing import ticks
        self._ticks = ticks

        self._connections: list[Connection] = []
        self.closed = False

        self.last_error: BaseException | None = None

    @property
    def connections(self) -> tuple:

        return tuple(self._connections)

    @property
    def connection_count(self) -> int:

        return len(self._connections)

    def io_interest(self, now_ms: int) -> int:



        if self.closed or self.io_socket is None:
            return 0
        return _IO_READ if len(self._connections) < self._max_connections else 0

    def next_deadline(self, now_ms: int) -> int | None:






        if self.closed or not self._connections:
            return None
        ticks_diff = self._ticks.ticks_diff
        nearest = self._ticks.ticks_add(now_ms, _CONNECTION_PROGRESS_INTERVAL_MS)
        for connection in self._connections:
            candidate = connection.next_deadline(now_ms)
            if candidate is not None and ticks_diff(candidate, nearest) < 0:
                nearest = candidate
        return nearest

    def close(self) -> None:

        if self.closed:
            return
        if self.io_socket is not None:
            try:
                self.io_socket.close()
            except Exception:
                pass
            self.io_socket = None
        for connection in list(self._connections):
            if connection.state == WebSocketState.CONNECTING:


                connection._finalize_closed()
                continue
            if connection.state != WebSocketState.CLOSED:
                try:
                    connection.close(CLOSE_NORMAL, "server shutting down")
                except WebSocketStateError:
                    pass

                connection._finalize_closed()
        self._connections.clear()
        self.closed = True

    def check(self, now_ms: int) -> bool:

        return not self.closed

    def handle(self, now_ms: int) -> None:

        if self.closed:
            return
        if self.io_socket is None:
            self.io_socket = self._listener_factory()
            _force_non_blocking(self.io_socket)
        self._accept_pending(now_ms)


        connections = self._connections
        for connection_index in range(len(connections) - 1, -1, -1):
            connection = connections[connection_index]
            if connection.state == WebSocketState.CLOSED:
                connections.pop(connection_index)
                continue
            connection.handle(now_ms)

            if self.closed:
                return
            if connection.state == WebSocketState.CLOSED:
                connections.pop(connection_index)

    def _accept_pending(self, now_ms: int) -> None:
        while True:
            if len(self._connections) >= self._max_connections:
                return
            try:
                accepted = self.io_socket.accept()
            except OSError as accept_error:
                if accept_error.errno == errno.EAGAIN:
                    return
                self.last_error = accept_error
                return
            if accepted is None:
                return
            client_socket, _address = accepted
            connection = Connection(
                client_socket,
                now_ms,
                accept_path=self._accept_path,
                max_message_bytes=self._max_message_bytes,
                recv_budget_per_tick=self._recv_budget_per_tick,
                send_budget_per_tick=self._send_budget_per_tick,
                max_tx_queue_size=self._max_tx_queue_size,
                when_oversized=self._when_oversized,
                pong_timeout_ms=self._pong_timeout_ms,
                handshake_timeout_ms=self._handshake_timeout_ms,
                close_timeout_ms=self._close_timeout_ms,
                max_inbound_queue_size=self._max_inbound_queue_size,
                ticks=self._ticks,
                on_connection_callback=self._on_connection,
            )
            self._connections.append(connection)
