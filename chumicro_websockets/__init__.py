




import gc

from chumicro_websockets._wire import (
    CLOSE_BAD_DATA,
    CLOSE_GOING_AWAY,
    CLOSE_INTERNAL_ERROR,
    CLOSE_NORMAL,
    CLOSE_PROTOCOL_ERROR,
    CLOSE_TOO_BIG,
    OPCODE_BINARY,
    OPCODE_CLOSE,
    OPCODE_CONTINUATION,
    OPCODE_PING,
    OPCODE_PONG,
    OPCODE_TEXT,
    WebSocketBackpressureError,
    WebSocketError,
    WebSocketHandshakeError,
    WebSocketProtocolError,
    WebSocketState,
    WebSocketStateError,
    WebSocketTimeoutError,
    WebSocketURLError,
    derive_accept_key,
    make_websocket_key,
    parse_ws_url,
)

gc.collect()

from chumicro_websockets._session import InboundMessage, WhenOversized

gc.collect()


def __getattr__(name):

    if name == "WebSocketClient":
        from chumicro_websockets.client import WebSocketClient

        return WebSocketClient
    if name == "Connection":
        from chumicro_websockets.server import Connection

        return Connection
    if name == "WebSocketServer":
        from chumicro_websockets.server import WebSocketServer

        return WebSocketServer
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [



    "CLOSE_BAD_DATA",
    "CLOSE_GOING_AWAY",
    "CLOSE_INTERNAL_ERROR",
    "CLOSE_NORMAL",
    "CLOSE_PROTOCOL_ERROR",
    "CLOSE_TOO_BIG",
    "OPCODE_BINARY",
    "OPCODE_CLOSE",
    "OPCODE_CONTINUATION",
    "OPCODE_PING",
    "OPCODE_PONG",
    "OPCODE_TEXT",
    "Connection",
    "InboundMessage",
    "WebSocketBackpressureError",
    "WebSocketClient",
    "WebSocketError",
    "WebSocketHandshakeError",
    "WebSocketProtocolError",
    "WebSocketServer",
    "WebSocketState",
    "WebSocketStateError",
    "WebSocketTimeoutError",
    "WebSocketURLError",
    "WhenOversized",
    "derive_accept_key",
    "make_websocket_key",
    "parse_ws_url",
]

gc.collect()
