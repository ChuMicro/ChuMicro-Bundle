

try:
    from micropython import const
except ImportError:
    def const(value):
        return value


class HttpError(Exception):
    pass


class HttpProtocolError(HttpError):
    pass


class HttpTimeoutError(HttpError):
    pass


class HttpBusyError(HttpError):
    pass


class HttpURLError(HttpError):
    pass


class HttpOversizedError(HttpError):


    def __init__(self, message: str, *, reported_length: int) -> None:
        super().__init__(message)
        self.reported_length = reported_length



DEFAULT_MAX_BODY_BYTES = const(65536)


DEFAULT_MAX_HEADER_BYTES = const(16384)


DEFAULT_RECV_BUDGET_PER_TICK = const(1024)


DEFAULT_BODY_BUFFER_SIZE = const(1024)


DEFAULT_STREAM_BUFFER_SIZE = const(1024)


DEFAULT_TIMEOUT_MS = const(10000)


DEFAULT_MAX_REDIRECTS = const(5)


REDIRECT_STATUS_CODES = frozenset({301, 302, 303, 307, 308})



METHOD_PRESERVING_REDIRECT_STATUS_CODES = frozenset({307, 308})


CRLF = b"\r\n"


_NON_ASCII_LINE = object()


def header_pairs(headers):


    return headers.items() if hasattr(headers, "items") else headers



CRLF_CRLF = b"\r\n\r\n"


NO_BODY_STATUS_CODES = frozenset({204, 304})


def parse_charset(content_type: str | None) -> str:








    if not content_type:
        return "utf-8"
    parts = content_type.split(";")
    for part in parts[1:]:
        token = part.strip()
        if token[:8].lower() != "charset=":
            continue
        value = token[8:].strip()
        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
        return value or "utf-8"
    return "utf-8"


def parse_url(url: str) -> tuple[str, str, int, str]:











    if not isinstance(url, str):
        raise HttpURLError(f"url must be str, got {type(url).__name__}")
    if url.startswith("http://"):
        scheme = "http"
        rest = url[7:]
        default_port = 80
    elif url.startswith("https://"):
        scheme = "https"
        rest = url[8:]
        default_port = 443
    else:
        raise HttpURLError(
            f"url must start with http:// or https://, got {url!r}",
        )
    if not rest:
        raise HttpURLError(f"url is missing host: {url!r}")


    authority_end = len(rest)
    for delimiter in ("/", "?", "#"):
        index = rest.find(delimiter)
        if index != -1 and index < authority_end:
            authority_end = index
    host_and_port = rest[:authority_end]
    remainder = rest[authority_end:]
    if not remainder:
        path = "/"
    elif remainder[0] == "/":
        path = remainder
    else:

        path = "/" + remainder

    if not host_and_port:
        raise HttpURLError(f"url is missing host: {url!r}")

    colon_index = host_and_port.find(":")
    if colon_index == -1:
        host = host_and_port
        port = default_port
    else:
        host = host_and_port[:colon_index]
        port_str = host_and_port[colon_index + 1:]
        if not host:
            raise HttpURLError(f"url is missing host: {url!r}")
        try:
            port = int(port_str)
        except ValueError as parse_error:
            raise HttpURLError(
                f"url has non-integer port {port_str!r}: {url!r}",
            ) from parse_error
        if port <= 0 or port > 65535:
            raise HttpURLError(
                f"url port {port} out of range 1-65535: {url!r}",
            )
    return scheme, host, port, path


def resolve_redirect_url(current_url: str, location: str) -> str:












    if not location:
        raise HttpURLError("redirect Location header is empty")
    if location.startswith("http://") or location.startswith("https://"):
        return location

    first_slash = location.find("/")
    scheme_zone = location if first_slash == -1 else location[:first_slash]
    if ":" in scheme_zone:
        raise HttpURLError(
            f"redirect Location has unsupported scheme: {location!r}",
        )
    scheme, host, port, current_path = parse_url(current_url)
    default_port = 443 if scheme == "https" else 80
    host_part = host if port == default_port else f"{host}:{port}"
    if location.startswith("/"):
        return f"{scheme}://{host_part}{location}"
    query_index = current_path.find("?")
    base_path = current_path[:query_index] if query_index != -1 else current_path
    last_slash = base_path.rfind("/")
    if last_slash == -1:
        base_path = "/"
    else:
        base_path = base_path[:last_slash + 1]
    return f"{scheme}://{host_part}{base_path}{location}"


class CaseInsensitiveDict:


    def __init__(self):


        self._entries = {}
        self._order = []

    def __setitem__(self, name, value):
        lower = name.lower()
        if lower not in self._entries:
            self._order.append(lower)
        self._entries[lower] = (name, value)

    def __getitem__(self, name):
        return self._entries[name.lower()][1]

    def __contains__(self, name):
        return name.lower() in self._entries

    def __iter__(self):
        for lower in self._order:
            yield self._entries[lower][0]

    def __len__(self):
        return len(self._entries)

    def __eq__(self, other):
        if not isinstance(other, CaseInsensitiveDict):
            return NotImplemented
        if len(self._entries) != len(other._entries):
            return False
        for lower, (_name, value) in self._entries.items():
            if lower not in other._entries:
                return False
            if other._entries[lower][1] != value:
                return False
        return True

    def __repr__(self):
        pairs = ", ".join(
            f"{name!r}: {value!r}"
            for name, value in self.items()
        )
        return f"CaseInsensitiveDict({{{pairs}}})"

    def get(self, name, default=None):

        entry = self._entries.get(name.lower())
        if entry is None:
            return default
        return entry[1]

    def items(self):

        for lower in self._order:
            yield self._entries[lower]

    def add(self, name, value):

        lower = name.lower()
        existing = self._entries.get(lower)
        if existing is None:
            self._order.append(lower)
            self._entries[lower] = (name, value)
            return
        original_name, current_value = existing
        joined = f"{current_value}, {value}"
        self._entries[lower] = (original_name, joined)


def _reject_unsafe_chars(label: str, value: str) -> None:


    for character in value:
        if character in ("\r", "\n", "\x00") or ord(character) > 0x7E:
            raise HttpURLError(
                f"{label} contains a non-ASCII or control character",
            )


def encode_request(
    method: str,
    host: str,
    path: str,
    *,
    headers: CaseInsensitiveDict | dict | list | tuple | None = None,
    body: bytes | None = None,
    user_agent: str | None = None,
) -> bytes:
















    merged = CaseInsensitiveDict()
    merged["Host"] = host
    merged["User-Agent"] = user_agent or "chumicro-requests/0.1"
    merged["Accept"] = "*/*"

    merged["Accept-Encoding"] = "identity"


    merged["Connection"] = "close"
    if body is not None:
        merged["Content-Length"] = str(len(body))

    if headers is not None:
        for name, value in header_pairs(headers):
            merged[name] = value

    _reject_unsafe_chars("method", method)
    _reject_unsafe_chars("path", path)
    parts = [f"{method} {path} HTTP/1.1\r\n".encode("ascii")]
    for name, value in merged.items():
        _reject_unsafe_chars("header name", str(name))
        _reject_unsafe_chars("header value", str(value))
        parts.append(f"{name}: {value}\r\n".encode("ascii"))
    parts.append(CRLF)
    if body is not None:
        parts.append(body)
    return b"".join(parts)


class ParseState:


    STATUS = "status"
    HEADERS = "headers"
    BODY = "body"
    CHUNK_SIZE = "chunk_size"
    CHUNK_DATA = "chunk_data"
    CHUNK_TRAILER = "chunk_trailer"
    DONE = "done"
    ERROR = "error"


class ResponseParser:


    def __init__(
        self,
        *,
        max_body_bytes: int = DEFAULT_MAX_BODY_BYTES,
        max_header_bytes: int = DEFAULT_MAX_HEADER_BYTES,
        body_buffer: bytearray | None = None,
        body_buffer_view: memoryview | None = None,
        stream_body: bool = False,
    ) -> None:











        self._max_body_bytes = max_body_bytes
        self._max_header_bytes = max_header_bytes
        self._stream_body = stream_body
        if stream_body and body_buffer is None:
            body_buffer = bytearray(DEFAULT_STREAM_BUFFER_SIZE)
        self._buffer = bytearray()
        self._read_offset = 0
        self.state = ParseState.STATUS
        self.status_code = None
        self.reason = ""
        self.http_version = ""
        self.headers = CaseInsensitiveDict()
        if body_buffer is not None:
            if body_buffer_view is None:
                body_buffer_view = memoryview(body_buffer)
            self._body = body_buffer
            self._body_view = body_buffer_view
            self._body_capacity = len(body_buffer)
        else:
            self._body = bytearray()
            self._body_view = memoryview(self._body)
            self._body_capacity = 0
        self._body_write_offset = 0
        self._body_read_offset = 0

        self.headers_complete = False

        self._body_remaining = -1
        self._chunk_remaining = 0
        self.error = None

    def _live_len(self):
        return len(self._buffer) - self._read_offset

    def _live_find(self, target):
        position = self._buffer.find(target, self._read_offset)
        if position == -1:
            return -1
        return position - self._read_offset

    def _live_slice(self, start, end=None):
        absolute_start = self._read_offset + start
        if end is None:
            return self._buffer[absolute_start:]
        return self._buffer[absolute_start:absolute_start + end]

    def _consume(self, count):
        self._read_offset += count
        if self._read_offset > 0 and self._read_offset * 2 >= len(self._buffer):


            self._buffer[:self._read_offset] = b""
            self._read_offset = 0

    def _reset_buffer(self):
        self._buffer = bytearray()
        self._read_offset = 0

    @property
    def body(self):

        return bytes(self._body_view[self._body_read_offset:self._body_write_offset])

    def body_free(self):

        return self._body_capacity - self._body_write_offset

    def read_body_into(self, buffer):

        available = self._body_write_offset - self._body_read_offset
        if available <= 0:
            return 0
        count = len(buffer)
        if count > available:
            count = available
        start = self._body_read_offset
        end = start + count
        buffer[:count] = self._body_view[start:end]
        if end == self._body_write_offset:
            self._body_read_offset = 0
            self._body_write_offset = 0
        else:
            self._body_read_offset = end
        return count

    def discard_body(self):

        self._body_read_offset = 0
        self._body_write_offset = 0

    def feed(self, chunk):

        if self.state in (ParseState.DONE, ParseState.ERROR):
            return
        if chunk:
            if self.state == ParseState.BODY:
                self._absorb_body_bytes(chunk)
            else:


                live = len(self._buffer) - self._read_offset
                if live + len(chunk) > self._max_header_bytes:
                    self._fail(HttpProtocolError(
                        "unparsed response bytes exceeded "
                        f"{self._max_header_bytes} (state={self.state})",
                    ))
                    return
                self._buffer.extend(chunk)
        self._advance()

    def feed_eof(self):

        if self.state == ParseState.DONE:
            return
        if self.state == ParseState.ERROR:
            return
        if self.state == ParseState.BODY and self._body_remaining < 0:

            self.state = ParseState.DONE
            return
        if self.state == ParseState.BODY and self._body_remaining > 0:
            self._fail(HttpProtocolError(
                f"peer closed mid-body; {self._body_remaining} bytes "
                "still expected per Content-Length",
            ))
            return
        if self.state in (
            ParseState.CHUNK_SIZE, ParseState.CHUNK_DATA, ParseState.CHUNK_TRAILER,
        ):
            self._fail(HttpProtocolError(
                f"peer closed mid-chunked-body (state={self.state})",
            ))
            return
        self._fail(HttpProtocolError(
            f"peer closed before response completed (state={self.state})",
        ))

    def _advance(self):



        while True:
            step = _ADVANCE_STEPS.get(self.state)
            if step is None or not step(self):
                return

    def _take_ascii_line(self, label):



        crlf_index = self._live_find(CRLF)
        if crlf_index == -1:
            return None
        line = self._live_slice(0, crlf_index)
        self._consume(crlf_index + 2)
        try:
            return str(line, "ascii")
        except UnicodeError:
            self._fail(HttpProtocolError(
                f"non-ASCII {label}: {bytes(line)!r}",
            ))
            return _NON_ASCII_LINE

    def _try_parse_status_line(self):

        text = self._take_ascii_line("status line")
        if text is None:
            return False
        if text is _NON_ASCII_LINE:
            return True
        parts = text.split(" ", 2)
        if len(parts) < 2:
            self._fail(HttpProtocolError(f"malformed status line: {text!r}"))
            return True
        version_str, code_str = parts[0], parts[1]
        if not version_str.startswith("HTTP/"):
            self._fail(HttpProtocolError(
                f"status line missing HTTP version: {text!r}",
            ))
            return True
        try:
            self.status_code = int(code_str)
        except ValueError:
            self._fail(HttpProtocolError(
                f"non-integer status code: {code_str!r}",
            ))
            return True
        self.http_version = version_str
        self.reason = parts[2] if len(parts) == 3 else ""
        self.state = ParseState.HEADERS
        return True

    def _try_parse_headers(self):
        text = self._take_ascii_line("header line")
        if text is None:
            return False
        if text is _NON_ASCII_LINE:
            return True
        if text == "":

            self._enter_body_state()
            return True
        colon_index = text.find(":")
        if colon_index <= 0:
            self._fail(HttpProtocolError(
                f"header line missing ':' or empty name: {text!r}",
            ))
            return True
        name = text[:colon_index]
        value = text[colon_index + 1:].strip()
        self.headers.add(name, value)
        return True

    def _enter_body_state(self):


        if 100 <= self.status_code < 200 and self.status_code != 101:
            self.status_code = None
            self.reason = ""
            self.http_version = ""
            self.headers = CaseInsensitiveDict()
            self.state = ParseState.STATUS
            return
        self.headers_complete = True
        if self.status_code in NO_BODY_STATUS_CODES:
            self.state = ParseState.DONE
            return


        transfer_encoding = self.headers.get("Transfer-Encoding")
        if transfer_encoding is not None:
            normalized = transfer_encoding.replace(" ", "").lower()
            if normalized != "chunked":
                self._fail(HttpProtocolError(
                    f"unsupported Transfer-Encoding: {transfer_encoding!r} "
                    "(only 'chunked' is supported in v1)",
                ))
                return
            self.state = ParseState.CHUNK_SIZE
            return
        content_length_str = self.headers.get("Content-Length")
        if content_length_str is not None:
            try:
                content_length = int(content_length_str)
            except ValueError:
                self._fail(HttpProtocolError(
                    f"non-integer Content-Length: {content_length_str!r}",
                ))
                return
            if content_length < 0:
                self._fail(HttpProtocolError(
                    f"negative Content-Length: {content_length}",
                ))
                return
            if content_length > self._max_body_bytes and not self._stream_body:
                self._fail(HttpOversizedError(
                    f"Content-Length {content_length} exceeds cap "
                    f"{self._max_body_bytes}",
                    reported_length=content_length,
                ))
                return
            self._body_remaining = content_length
            if content_length == 0:
                self.state = ParseState.DONE
                return
            self.state = ParseState.BODY
            self._body_write_offset = 0


            if content_length > self._body_capacity and not self._stream_body:
                self._body = bytearray(content_length)
                self._body_view = memoryview(self._body)
                self._body_capacity = content_length
            self._absorb_trailing_bytes()
            return
        self._body_remaining = -1
        self.state = ParseState.BODY
        self._absorb_trailing_bytes()

    def _absorb_trailing_bytes(self):


        if self._live_len() == 0:
            return
        tail_bytes = self._live_slice(0)
        self._reset_buffer()
        self._absorb_body_bytes(tail_bytes)

    def _try_parse_chunk_size(self):
        text = self._take_ascii_line("chunk-size line")
        if text is None:
            return False
        if text is _NON_ASCII_LINE:
            return True

        semicolon_index = text.find(";")
        size_text = text[:semicolon_index] if semicolon_index != -1 else text
        size_text = size_text.strip()
        if not size_text:
            self._fail(HttpProtocolError(
                f"empty chunk-size line: {text!r}",
            ))
            return True
        try:
            chunk_size = int(size_text, 16)
        except ValueError:
            self._fail(HttpProtocolError(
                f"non-hex chunk-size: {size_text!r}",
            ))
            return True
        if chunk_size < 0:
            self._fail(HttpProtocolError(
                f"negative chunk-size: {chunk_size}",
            ))
            return True


        if not self._stream_body and self._body_write_offset + chunk_size > self._max_body_bytes:
            self._fail(HttpOversizedError(
                f"chunked body would exceed cap {self._max_body_bytes}",
                reported_length=self._body_write_offset + chunk_size,
            ))
            return True
        if chunk_size == 0:
            self.state = ParseState.CHUNK_TRAILER
            return True
        self._chunk_remaining = chunk_size
        self.state = ParseState.CHUNK_DATA
        return True

    def _try_consume_chunk_data(self):
        if self._chunk_remaining > 0:
            available = min(self._chunk_remaining, self._live_len())
            if available == 0:
                return False
            source = memoryview(self._buffer)[
                self._read_offset:self._read_offset + available
            ]
            self._absorb_body_chunk(source)


            source = None
            self._consume(available)
            self._chunk_remaining -= available
            if self._chunk_remaining > 0:
                return False

        if self._live_len() < 2:
            return False
        tail = self._live_slice(0, 2)
        if tail != CRLF:
            self._fail(HttpProtocolError(
                f"missing CRLF after chunk data: {bytes(tail)!r}",
            ))
            return True
        self._consume(2)
        self.state = ParseState.CHUNK_SIZE
        return True

    def _try_parse_chunk_trailer(self):
        crlf_index = self._live_find(CRLF)
        if crlf_index == -1:
            return False
        if crlf_index == 0:

            self._consume(2)
            self.state = ParseState.DONE
            return True

        self._consume(crlf_index + 2)
        return True

    def _absorb_body_bytes(self, chunk):
        if self._body_remaining == 0:
            return
        if self._body_remaining > 0:
            take = min(self._body_remaining, len(chunk))
            self._absorb_body_chunk(chunk[:take] if take < len(chunk) else chunk)
            self._body_remaining -= take
            if self._body_remaining == 0:
                self.state = ParseState.DONE
            return

        chunk_len = len(chunk)
        if not self._stream_body and self._body_write_offset + chunk_len > self._max_body_bytes:
            self._fail(HttpOversizedError(
                f"response body exceeded cap {self._max_body_bytes}",
                reported_length=self._body_write_offset + chunk_len,
            ))
            return
        self._absorb_body_chunk(chunk)

    def _absorb_body_chunk(self, chunk):
        chunk_len = len(chunk)
        write_offset = self._body_write_offset
        end_offset = write_offset + chunk_len
        if end_offset <= len(self._body_view):
            self._body[write_offset:end_offset] = chunk
        elif self._stream_body:


            self._fail(HttpError(
                "streamed-body staging overflow: drain read_body_into "
                "and bound each feed by body_free()",
            ))
            return
        else:


            new_capacity = len(self._body_view) * 2
            if new_capacity < end_offset:
                new_capacity = end_offset
            if new_capacity > self._max_body_bytes:


                new_capacity = self._max_body_bytes
            new_body = bytearray(new_capacity)
            new_body[:write_offset] = self._body_view[:write_offset]
            new_body[write_offset:end_offset] = chunk
            self._body = new_body
            self._body_view = memoryview(new_body)
            self._body_capacity = new_capacity
        self._body_write_offset = end_offset

    def _fail(self, error):
        self.error = error
        self.state = ParseState.ERROR





_ADVANCE_STEPS = {
    ParseState.STATUS: ResponseParser._try_parse_status_line,
    ParseState.HEADERS: ResponseParser._try_parse_headers,
    ParseState.CHUNK_SIZE: ResponseParser._try_parse_chunk_size,
    ParseState.CHUNK_DATA: ResponseParser._try_consume_chunk_data,
    ParseState.CHUNK_TRAILER: ResponseParser._try_parse_chunk_trailer,
}
