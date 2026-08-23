




import gc

from chumicro_http_server._wire import (
    DEFAULT_MAX_CONNECTIONS,
    DEFAULT_MAX_HEADERS_BYTES,
    DEFAULT_MAX_REQUEST_BODY_BYTES,
    DEFAULT_MAX_REQUEST_LINE_BYTES,
    DEFAULT_RECV_BUDGET_PER_TICK,
    DEFAULT_REQUEST_TIMEOUT_MS,
    DEFAULT_SEND_BUDGET_PER_TICK,
    DEFAULT_STREAM_BUFFER_SIZE,
    SOURCE_EOF,
    CaseInsensitiveDict,
    RequestParser,
    RequestParseState,
    ServerError,
    ServerHeadersTooLargeError,
    ServerLimitError,
    ServerOversizedError,
    ServerProtocolError,
    ServerRequestLineTooLargeError,
    parse_charset,
    parse_query,
    split_target,
)


def __getattr__(name):

    if name in ("HttpServer", "Request", "Response", "build_response", "encode_response"):

        gc.collect()
        import chumicro_http_server.server as _server

        return getattr(_server, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [



    "DEFAULT_MAX_CONNECTIONS",
    "DEFAULT_MAX_HEADERS_BYTES",
    "DEFAULT_MAX_REQUEST_BODY_BYTES",
    "DEFAULT_MAX_REQUEST_LINE_BYTES",
    "DEFAULT_RECV_BUDGET_PER_TICK",
    "DEFAULT_REQUEST_TIMEOUT_MS",
    "DEFAULT_SEND_BUDGET_PER_TICK",
    "DEFAULT_STREAM_BUFFER_SIZE",
    "SOURCE_EOF",
    "CaseInsensitiveDict",
    "HttpServer",
    "Request",
    "RequestParseState",
    "RequestParser",
    "Response",
    "ServerError",
    "ServerHeadersTooLargeError",
    "ServerLimitError",
    "ServerOversizedError",
    "ServerProtocolError",
    "ServerRequestLineTooLargeError",
    "build_response",
    "encode_response",
    "parse_charset",
    "parse_query",
    "split_target",
]

gc.collect()
