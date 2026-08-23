




import errno
import json

from chumicro_requests._wire import (
    DEFAULT_BODY_BUFFER_SIZE,
    DEFAULT_MAX_BODY_BYTES,
    DEFAULT_MAX_HEADER_BYTES,
    DEFAULT_MAX_REDIRECTS,
    DEFAULT_RECV_BUDGET_PER_TICK,
    DEFAULT_STREAM_BUFFER_SIZE,
    DEFAULT_TIMEOUT_MS,
    METHOD_PRESERVING_REDIRECT_STATUS_CODES,
    REDIRECT_STATUS_CODES,
    CaseInsensitiveDict,
    HttpBusyError,
    HttpError,
    HttpOversizedError,
    HttpTimeoutError,
    ParseState,
    ResponseParser,
    encode_request,
    header_pairs,
    parse_charset,
    parse_url,
    resolve_redirect_url,
)



_IO_READ = 1
_IO_WRITE = 2


_EWOULDBLOCK = getattr(errno, "EWOULDBLOCK", errno.EAGAIN)


def _is_would_block(socket_error):
    if socket_error.errno in (errno.EAGAIN, _EWOULDBLOCK):
        return True


    return type(socket_error).__name__ in (
        "SSLWantReadError",
        "SSLWantWriteError",
    )


class WhenOversized:



    DROP_SILENT = "drop_silent"


    DROP_WITH_EVENT = "drop_with_event"


    DISCONNECT = "disconnect"


def _encode_body(body, json_body):
    if json_body is not None:
        return json.dumps(json_body).encode("utf-8")
    if body is None:
        return None
    if isinstance(body, str):
        return body.encode("utf-8")
    if isinstance(body, (bytes, bytearray)):
        return bytes(body)
    raise TypeError(
        f"body must be bytes / bytearray / str, got {type(body).__name__}",
    )


def _merge_default_header(user_headers, name, value):
    merged = CaseInsensitiveDict()
    merged[name] = value
    if user_headers is None:
        return merged
    for header_name, header_value in header_pairs(user_headers):
        merged[header_name] = header_value
    return merged


def _force_non_blocking(socket):


    setblocking = getattr(socket, "setblocking", None)
    if setblocking is None:
        return
    try:
        setblocking(False)
    except (OSError, AttributeError):
        pass


class Response:













    def __init__(
        self,
        *,
        status_code: int,
        reason: str,
        http_version: str,
        headers: CaseInsensitiveDict,
        body: bytes,
        url: str,
        oversized_dropped: bool = False,
        encoding: str | None = None,
        streamed: bool = False,
    ) -> None:
        self.status_code = status_code
        self.reason = reason
        self.http_version = http_version
        self.headers = headers
        self.body = body
        self.url = url
        self.oversized_dropped = oversized_dropped
        self.streamed = streamed
        self._encoding_override = encoding

    def __repr__(self) -> str:
        return (
            f"Response(status_code={self.status_code}, "
            f"reason={self.reason!r}, url={self.url!r}, "
            f"body={len(self.body)} bytes)"
        )

    @property
    def encoding(self) -> str:

        if self._encoding_override is not None:
            return self._encoding_override
        return parse_charset(self.headers.get("Content-Type"))

    @encoding.setter
    def encoding(self, value: str) -> None:
        self._encoding_override = value

    @property
    def text(self) -> str:






        if self.streamed:
            raise HttpError(
                "streamed response has no whole body; read it via "
                "RequestHandle.read_body_into",
            )
        return self.body.decode(self.encoding)

    def json(self) -> object:





        return json.loads(self.text)


class RequestHandle:


    def __init__(self, *, url, on_done=None, stream=False):
        self.url = url
        self.done = False
        self.response = None
        self.error = None
        self._on_done = on_done
        self._stream = stream
        self._body_source = None

    def read_body_into(self, buffer):





        if not self._stream:
            raise HttpError(
                "read_body_into requires a request issued with stream=True",
            )
        source = self._body_source
        if source is None:
            return 0
        return source.read_body_into(buffer)

    def _publish_stream(self, response, body_source):
        self.response = response
        self._body_source = body_source

    def _invoke_done(self):
        if self._on_done is not None:
            self._on_done(self)

    @property
    def result(self):





        if not self.done:
            raise HttpError(
                "RequestHandle.result accessed before done; "
                "poll handle.done first",
            )
        if self.error is not None:
            raise self.error
        return self.response

    def _set_response(self, response):
        self.response = response
        self.done = True

    def _set_error(self, error):
        self.error = error
        self.done = True


class _RequestState:
    IDLE = "idle"
    AWAITING_TRANSPORT = "awaiting_transport"
    SENDING = "sending"
    RECEIVING = "receiving"


class HttpClient:


    @classmethod
    def from_config(
        cls,
        config: object,
        *,
        radio: object | None = None,
        ssl_context: object | None = None,
        transport_factory: object | None = None,
        **constructor_kwargs: object,
    ) -> "HttpClient":







        if transport_factory is None:
            try:
                from chumicro_sockets.sockets_factory import (
                    connector_factory,
                )
            except ImportError as exception:
                raise RuntimeError(
                    "chumicro_sockets.sockets_factory not available "
                    "(excluded via __chumicro_skip_factories__ or "
                    "not on the board); pass transport_factory= "
                    "explicitly.",
                ) from exception

            transport_factory = connector_factory(
                radio=radio, ssl_context=ssl_context,
            )
        kwargs = {
            "transport_factory": transport_factory,
            "default_timeout_ms": config.get(
                "requests.default_timeout_ms", DEFAULT_TIMEOUT_MS,
            ),
            "default_max_redirects": config.get(
                "requests.default_max_redirects", DEFAULT_MAX_REDIRECTS,
            ),
            "user_agent": config.get("requests.user_agent"),
            "max_body_bytes": config.get(
                "requests.max_body_bytes", DEFAULT_MAX_BODY_BYTES,
            ),
        }
        kwargs.update(constructor_kwargs)
        return cls(**kwargs)

    def __init__(
        self,
        *,
        transport_factory: object,
        recv_budget_per_tick: int = DEFAULT_RECV_BUDGET_PER_TICK,
        max_body_bytes: int = DEFAULT_MAX_BODY_BYTES,
        max_header_bytes: int = DEFAULT_MAX_HEADER_BYTES,
        when_oversized: str = WhenOversized.DROP_WITH_EVENT,
        default_timeout_ms: int = DEFAULT_TIMEOUT_MS,
        default_max_redirects: int = DEFAULT_MAX_REDIRECTS,
        stream_buffer_size: int = DEFAULT_STREAM_BUFFER_SIZE,
        user_agent: str | None = None,
        ticks: object | None = None,
    ) -> None:














        self._transport_factory = transport_factory
        self._connector = None
        self._recv_budget_per_tick = recv_budget_per_tick


        self._recv_buffer = bytearray(min(recv_budget_per_tick, 512))
        self._recv_view = memoryview(self._recv_buffer)
        self._max_body_bytes = max_body_bytes
        self._max_header_bytes = max_header_bytes
        self._when_oversized = when_oversized
        self._default_timeout_ms = default_timeout_ms
        self._user_agent = user_agent or "chumicro-requests/0.1"

        if ticks is None:
            from chumicro_timing import ticks
        self._ticks = ticks

        self._default_max_redirects = default_max_redirects

        self._state = _RequestState.IDLE
        self._socket = None
        self._handle = None


        self._completed_handle = None
        self.url = None
        self._tx_buffer = b""
        self._tx_offset = 0
        self._parser = None


        self._body_buffer = bytearray(DEFAULT_BODY_BUFFER_SIZE)
        self._body_buffer_view = memoryview(self._body_buffer)
        self._stream_buffer_size = stream_buffer_size
        self._stream = False
        self._deadline_ticks = None


        self._redirects_remaining = 0
        self._original_method = None
        self._original_headers = None
        self._original_body = None
        self._original_json_body = None

        self.on_oversized = lambda *_args, **_kwargs: None

    @property
    def busy(self):

        return self._state != _RequestState.IDLE

    @property
    def io_socket(self):

        if self._state == _RequestState.AWAITING_TRANSPORT:
            return self._connector.io_socket if self._connector is not None else None
        return self._socket

    def io_interest(self, now_ms):




        if self._state == _RequestState.AWAITING_TRANSPORT:
            return self._connector.io_interest(now_ms) if self._connector is not None else 0
        if self._state == _RequestState.RECEIVING:
            if (
                self._stream
                and self._parser is not None
                and self._parser.body_free() == 0
            ):
                return 0
            return _IO_READ
        if self._state == _RequestState.SENDING:
            return _IO_WRITE
        return 0

    def next_deadline(self, now_ms):

        if self._state == _RequestState.IDLE:
            return None
        if (
            self._state == _RequestState.AWAITING_TRANSPORT
            and self.io_socket is None
        ):
            return now_ms
        return self._deadline_ticks

    def request(
        self,
        method: str,
        url: str,
        *,
        body: bytes | str | None = None,
        json: object | None = None,
        headers: CaseInsensitiveDict | dict | list | tuple | None = None,
        timeout_ms: int | None = None,
        max_redirects: int | None = None,
        on_done: object | None = None,
        stream: bool = False,
    ) -> "RequestHandle":








        return self._start_request(
            method, url,
            body=body, json_body=json,
            headers=headers, timeout_ms=timeout_ms,
            max_redirects=max_redirects, on_done=on_done, stream=stream,
        )

    def get(
        self,
        url: str,
        *,
        headers: CaseInsensitiveDict | dict | list | tuple | None = None,
        timeout_ms: int | None = None,
        max_redirects: int | None = None,
        on_done: object | None = None,
        stream: bool = False,
    ) -> "RequestHandle":




        return self._start_request(
            "GET", url, headers=headers, timeout_ms=timeout_ms,
            max_redirects=max_redirects, on_done=on_done, stream=stream,
        )

    def post(
        self,
        url: str,
        *,
        body: bytes | str | None = None,
        json: object | None = None,
        headers: CaseInsensitiveDict | dict | list | tuple | None = None,
        timeout_ms: int | None = None,
        max_redirects: int | None = None,
        on_done: object | None = None,
        stream: bool = False,
    ) -> "RequestHandle":




        return self._start_request(
            "POST", url,
            body=body, json_body=json,
            headers=headers, timeout_ms=timeout_ms,
            max_redirects=max_redirects, on_done=on_done, stream=stream,
        )

    def put(
        self,
        url: str,
        *,
        body: bytes | str | None = None,
        json: object | None = None,
        headers: CaseInsensitiveDict | dict | list | tuple | None = None,
        timeout_ms: int | None = None,
        max_redirects: int | None = None,
        on_done: object | None = None,
        stream: bool = False,
    ) -> "RequestHandle":



        return self._start_request(
            "PUT", url,
            body=body, json_body=json,
            headers=headers, timeout_ms=timeout_ms,
            max_redirects=max_redirects, on_done=on_done, stream=stream,
        )

    def patch(
        self,
        url: str,
        *,
        body: bytes | str | None = None,
        json: object | None = None,
        headers: CaseInsensitiveDict | dict | list | tuple | None = None,
        timeout_ms: int | None = None,
        max_redirects: int | None = None,
        on_done: object | None = None,
        stream: bool = False,
    ) -> "RequestHandle":



        return self._start_request(
            "PATCH", url,
            body=body, json_body=json,
            headers=headers, timeout_ms=timeout_ms,
            max_redirects=max_redirects, on_done=on_done, stream=stream,
        )

    def delete(
        self,
        url: str,
        *,
        headers: CaseInsensitiveDict | dict | list | tuple | None = None,
        timeout_ms: int | None = None,
        max_redirects: int | None = None,
        on_done: object | None = None,
        stream: bool = False,
    ) -> "RequestHandle":




        return self._start_request(
            "DELETE", url, headers=headers, timeout_ms=timeout_ms,
            max_redirects=max_redirects, on_done=on_done, stream=stream,
        )

    def check(self, now_ms):

        return self._state != _RequestState.IDLE

    def handle(self, now_ms):

        if self._state == _RequestState.IDLE:
            return
        self._drive_tick(now_ms)


        self._fire_completion()

    def cancel(self):

        if self._state == _RequestState.IDLE:
            return
        self._fail(HttpError(f"request to {self.url!r} cancelled"))
        self._fire_completion()

    def _drive_tick(self, now_ms):
        if self._deadline_ticks is not None and self._ticks.ticks_diff(
            self._deadline_ticks, now_ms,
        ) <= 0:
            self._fail(HttpTimeoutError(
                f"request to {self.url!r} timed out after deadline",
            ))
            return

        try:
            if self._state == _RequestState.AWAITING_TRANSPORT:
                if not self._advance_connector(now_ms):
                    return

            if self._state == _RequestState.SENDING:
                self._drive_send()
            if self._state == _RequestState.RECEIVING:
                self._drive_recv()
        except HttpError as protocol_error:
            self._fail(protocol_error)
        except OSError as socket_error:
            self._fail(HttpError(f"socket error: {socket_error}"))

    def _fire_completion(self):
        finished_handle = self._completed_handle
        self._completed_handle = None
        if finished_handle is not None:
            finished_handle._invoke_done()

    def _advance_connector(self, now_ms):
        connector = self._connector
        connector.tick(now_ms)
        if connector.state == "ready":
            self._socket = connector.socket
            self._connector = None
            _force_non_blocking(self._socket)
            self._state = _RequestState.SENDING
            return True
        if connector.state == "failed":
            error = connector.last_error
            self._connector = None
            self._fail(HttpError(f"connector failed: {error}"))
            return False
        return False

    def _start_request(
        self, method, url, *, headers, timeout_ms,
        body=None, json_body=None, max_redirects=None, on_done=None,
        stream=False,
    ):
        if self._state != _RequestState.IDLE:
            raise HttpBusyError(
                f"client busy on {self.url!r}; await handle.done before issuing another",
            )
        if body is not None and json_body is not None:
            raise ValueError(
                "pass body= or json= but not both",
            )
        encoded_body = _encode_body(body, json_body)
        self._stream = stream
        self._redirects_remaining = (
            max_redirects if max_redirects is not None else self._default_max_redirects
        )


        self._original_method = method
        self._original_headers = headers
        self._original_body = encoded_body if self._redirects_remaining > 0 else None
        self._original_json_body = json_body
        timeout = timeout_ms if timeout_ms is not None else self._default_timeout_ms
        self._deadline_ticks = self._ticks.ticks_add(self._ticks.ticks_ms(), timeout)
        self._handle = RequestHandle(url=url, on_done=on_done, stream=stream)
        try:
            self._start_hop(url, method, encoded_body, headers, json_body is not None)
        except Exception:



            self._handle = None
            self._deadline_ticks = None
            self._original_method = None
            self._original_headers = None
            self._original_body = None
            self._original_json_body = None
            self._redirects_remaining = 0
            self._stream = False
            raise
        return self._handle

    def _start_hop(
        self, url, method, encoded_body, user_headers, json_default_content_type,
    ):
        merged_headers = user_headers
        if json_default_content_type:
            merged_headers = _merge_default_header(
                user_headers, "Content-Type", "application/json",
            )
        scheme, host, port, path = parse_url(url)
        use_tls = scheme == "https"
        default_port = 443 if use_tls else 80
        host_header = host if port == default_port else f"{host}:{port}"
        request_bytes = encode_request(
            method,
            host_header,
            path,
            headers=merged_headers,
            body=encoded_body,
            user_agent=self._user_agent,
        )
        self._connector = self._transport_factory(host, port, use_tls)
        self.url = url
        self._tx_buffer = request_bytes
        self._tx_offset = 0


        if self._stream:
            self._parser = ResponseParser(
                max_body_bytes=self._max_body_bytes,
                max_header_bytes=self._max_header_bytes,
                stream_body=True,
                body_buffer=bytearray(self._stream_buffer_size),
            )
        else:
            self._parser = ResponseParser(
                max_body_bytes=self._max_body_bytes,
                max_header_bytes=self._max_header_bytes,
                body_buffer=self._body_buffer,
                body_buffer_view=self._body_buffer_view,
            )
        self._state = _RequestState.AWAITING_TRANSPORT

    def _drive_send(self):


        tx_view = memoryview(self._tx_buffer)
        while self._tx_offset < len(self._tx_buffer):
            payload = (
                self._tx_buffer if self._tx_offset == 0
                else tx_view[self._tx_offset:]
            )
            try:
                sent = self._socket.send(payload)
            except OSError as socket_error:
                if _is_would_block(socket_error):
                    return
                raise
            if sent <= 0:
                return
            self._tx_offset += sent


        self._tx_buffer = b""
        self._tx_offset = 0
        self._state = _RequestState.RECEIVING

    def _drive_recv(self):
        consumed = 0
        budget = self._recv_budget_per_tick
        scratch_size = len(self._recv_buffer)
        parser = self._parser
        streaming = self._stream
        while consumed < budget and parser.state not in (
            ParseState.DONE, ParseState.ERROR,
        ):
            capacity = min(scratch_size, budget - consumed)
            if streaming:
                free = parser.body_free()
                if capacity > free:
                    capacity = free
                if capacity == 0:

                    return
            try:
                got = self._socket.recv_into(self._recv_view, capacity)
            except OSError as socket_error:
                if _is_would_block(socket_error):
                    return
                raise
            if got == 0:

                parser.feed_eof()
                break
            parser.feed(self._recv_view[:got])
            if streaming:
                self._sync_stream_state()
            consumed += got
        if parser.state == ParseState.ERROR:
            raise parser.error
        if parser.state == ParseState.DONE:
            self._complete()

    def _sync_stream_state(self):
        parser = self._parser
        if not parser.headers_complete or parser.state == ParseState.ERROR:
            return
        handle = self._handle
        if handle.response is not None:
            return
        if (
            self._redirects_remaining > 0
            and parser.status_code in REDIRECT_STATUS_CODES
            and parser.headers.get("Location") is not None
        ):
            parser.discard_body()
            return
        response = Response(
            status_code=parser.status_code,
            reason=parser.reason,
            http_version=parser.http_version,
            headers=parser.headers,
            body=b"",
            url=self.url,
            streamed=True,
        )
        handle._publish_stream(response, parser)

    def _complete(self):
        parser = self._parser
        status_code = parser.status_code
        if self._stream:


            self._sync_stream_state()
            handle = self._handle
            if handle.response is None:


                self._follow_redirect(status_code, parser.headers.get("Location"))
                return


            handle._set_response(handle.response)
            self._reset_socket()
            return
        if self._redirects_remaining > 0 and status_code in REDIRECT_STATUS_CODES:
            location = parser.headers.get("Location")
            if location is not None:
                self._follow_redirect(status_code, location)
                return
        response = Response(
            status_code=status_code,
            reason=parser.reason,
            http_version=parser.http_version,
            headers=parser.headers,
            body=parser.body,
            url=self.url,
            oversized_dropped=False,
        )
        self._handle._set_response(response)
        self._reset_socket()

    def _follow_redirect(self, status_code, location):
        try:
            new_url = resolve_redirect_url(self.url, location)
        except HttpError as redirect_error:
            self._handle._set_error(redirect_error)
            self._reset_socket()
            return
        if status_code in METHOD_PRESERVING_REDIRECT_STATUS_CODES:
            next_method = self._original_method
            next_body = self._original_body
            next_json_default_content_type = self._original_json_body is not None
        else:

            next_method = "GET"
            next_body = None
            next_json_default_content_type = False

        self._close_socket_only()
        self._redirects_remaining -= 1
        try:
            self._start_hop(
                new_url, next_method, next_body,
                self._original_headers, next_json_default_content_type,
            )
        except OSError as factory_error:
            self._handle._set_error(
                HttpError(f"connector factory failed during redirect: {factory_error}"),
            )
            self._reset_socket()
        except HttpError as redirect_error:
            self._handle._set_error(redirect_error)
            self._reset_socket()
        except Exception as unexpected_error:
            self._handle._set_error(
                HttpError(f"redirect hop failed: {unexpected_error}"),
            )
            self._reset_socket()

    def _fail(self, error):

        if isinstance(error, HttpOversizedError):
            if self._when_oversized == WhenOversized.DROP_SILENT:
                self._complete_oversized_drop()
                return
            if self._when_oversized == WhenOversized.DROP_WITH_EVENT:
                self.on_oversized(error.reported_length, self.url)
                self._complete_oversized_drop()
                return

        if self._handle is not None:
            self._handle._set_error(error)
        self._reset_socket()

    def _complete_oversized_drop(self):
        response = Response(
            status_code=self._parser.status_code,
            reason=self._parser.reason,
            http_version=self._parser.http_version,
            headers=self._parser.headers,
            body=b"",
            url=self.url,
            oversized_dropped=True,
        )
        self._handle._set_response(response)
        self._reset_socket()

    def _close_socket_only(self):
        if self._connector is not None:
            self._connector.cancel()
            self._connector = None
        if self._socket is not None:
            try:
                self._socket.close()
            except OSError:
                pass
        self._socket = None
        self._tx_buffer = b""
        self._tx_offset = 0
        self._parser = None
        self._state = _RequestState.IDLE

    def _reset_socket(self):
        self._close_socket_only()
        finished_handle = self._handle
        self._handle = None
        self.url = None
        self._stream = False
        self._original_method = None
        self._original_headers = None
        self._original_body = None
        self._original_json_body = None
        self._deadline_ticks = None
        self._redirects_remaining = 0
        if finished_handle is not None:
            self._completed_handle = finished_handle
