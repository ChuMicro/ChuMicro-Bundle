

import gc

from chumicro_mqtt._wire import (
    MQTTBackpressureError,
    MQTTConnectError,
    MQTTError,
    MQTTProtocolError,
    UnsupportedQoSError,
    topic_matches,
)

gc.collect()


def __getattr__(name):
    if name in (
        "InboundPublish",
        "MQTTClient",
        "ProtocolState",
        "WhenOversized",
        "default_client_id",
    ):


        gc.collect()
        import chumicro_mqtt.client as _client

        return getattr(_client, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [



    "InboundPublish",
    "MQTTClient",
    "MQTTBackpressureError",
    "MQTTConnectError",
    "MQTTError",
    "MQTTProtocolError",
    "ProtocolState",
    "UnsupportedQoSError",
    "WhenOversized",
    "default_client_id",
    "topic_matches",
]

gc.collect()
