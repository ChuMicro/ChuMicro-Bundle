<p align="center">
  <a href="https://github.com/ChuMicro/ChuMicro"><img src="https://raw.githubusercontent.com/ChuMicro/ChuMicro/main/support/docs/chumicro.png" width="420" alt="ChuMicro" /></a>
</p>
<h1 align="center">ChuMicro-Bundle</h1>

<p align="center">
  <strong>Stable bundle for <a href="https://github.com/ChuMicro/ChuMicro">ChuMicro</a> &mdash; install any library on CircuitPython, MicroPython, or CPython.</strong>
</p>

<p align="center">
  <a href="https://chumicro.github.io/ChuMicro/">Docs</a> &bull;
  <a href="https://github.com/ChuMicro/ChuMicro">Source</a> &bull;
  <a href="https://github.com/ChuMicro/ChuMicro-Bundle-Experimental">Experimental Bundle</a>
</p>


## Get started

Swap `chumicro-timing` for whichever library you need.

**CircuitPython ([circup](https://github.com/adafruit/circup)):**

circup is CircuitPython's package manager — it uses [bundles](https://learn.adafruit.com/keep-your-circuitpython-libraries-on-devices-up-to-date-with-circup/bundle-commands) to find third-party packages. Register the ChuMicro bundle once, then install any library by name:

```bash
circup bundle-add ChuMicro/ChuMicro-Bundle
circup install chumicro_timing
```

> If you previously registered the experimental bundle, remove it first — circup may pick either version when both are active:
> ```
> circup bundle-remove ChuMicro/ChuMicro-Bundle-Experimental
> ```

**MicroPython ([mip](https://docs.micropython.org/en/latest/reference/packages.html)):**

```bash
mpremote mip install github:ChuMicro/ChuMicro-Bundle/chumicro_timing
```

Or from the REPL on a network-capable board:

```python
import mip
mip.install("github:ChuMicro/ChuMicro-Bundle/chumicro_timing")
```

> **Want pre-compiled `.mpy` bytecode?** Add `mpy6/` before the package name for faster startup and lower RAM usage on boards with mpy format v6 (MicroPython 1.24+):
> ```
> mpremote mip install github:ChuMicro/ChuMicro-Bundle/mpy6/chumicro_timing
> ```

**CPython (pip):**

On your laptop, install from PyPI — no bundle needed:

```bash
pip install chumicro-timing
```

## What's in the bundle?

| Library | Version | Description |
| --- | --- | --- |
| [**chumicro-compat**](https://github.com/ChuMicro/ChuMicro/tree/main/libraries/compat) | 0.3.1 | Cross-runtime compatibility polyfills for CircuitPython, MicroPython, and CPython — functools.partial and more. |
| [**chumicro-config**](https://github.com/ChuMicro/ChuMicro/tree/main/libraries/config) | 0.7.3 | Standardized runtime-config helpers for ChuMicro libraries — section loader + on-device runtime-config reader. |
| [**chumicro-http_server**](https://github.com/ChuMicro/ChuMicro/tree/main/libraries/http_server) | 0.19.0 | Non-blocking HTTP/1.1 server for CircuitPython, MicroPython, and CPython. |
| [**chumicro-kvstore**](https://github.com/ChuMicro/ChuMicro/tree/main/libraries/kvstore) | 0.3.1 | Tiny mutable key-value store for persisted runtime state — counters, timestamps, tokens — across CircuitPython, MicroPython, and CPython. |
| [**chumicro-mqtt**](https://github.com/ChuMicro/ChuMicro/tree/main/libraries/mqtt) | 0.28.0 | Non-blocking MQTT 3.1.1 client (QoS 0+1) for CircuitPython, MicroPython, and CPython. |
| [**chumicro-msgpack**](https://github.com/ChuMicro/ChuMicro/tree/main/libraries/msgpack) | 0.2.2 | Compact MessagePack serialization for CircuitPython, MicroPython, and CPython — delegates to the native C module when available. |
| [**chumicro-ntp**](https://github.com/ChuMicro/ChuMicro/tree/main/libraries/ntp) | 0.13.0 | Runner-shaped SNTP client over an injected UDP socket — pure-Python, cross-runtime. |
| [**chumicro-requests**](https://github.com/ChuMicro/ChuMicro/tree/main/libraries/requests) | 0.19.0 | Non-blocking HTTP/1.1 client for CircuitPython, MicroPython, and CPython. |
| [**chumicro-runner**](https://github.com/ChuMicro/ChuMicro/tree/main/libraries/runner) | 0.19.0 | Tick-based task runner for CircuitPython, MicroPython, and CPython — non-blocking check/handle scheduling without async. |
| [**chumicro-sockets**](https://github.com/ChuMicro/ChuMicro/tree/main/libraries/sockets) | 0.20.0 | Cross-runtime TCP + TLS sockets for CircuitPython, MicroPython, and CPython. |
| [**chumicro-timing**](https://github.com/ChuMicro/ChuMicro/tree/main/libraries/timing) | 0.8.1 | Wraparound-safe millisecond tick helpers plus wait value objects (deadlines, rates, signals) for CircuitPython, MicroPython, and CPython. |
| [**chumicro-websockets**](https://github.com/ChuMicro/ChuMicro/tree/main/libraries/websockets) | 0.25.0 | Non-blocking WebSocket (RFC 6455) client + server for CircuitPython, MicroPython, and CPython |
| [**chumicro-wifi**](https://github.com/ChuMicro/ChuMicro/tree/main/libraries/wifi) | 0.8.1 | Unified wifi supervisor across CircuitPython, MicroPython, and CPython — sole-supervisor model with reconnect, state machine, and per-runtime adapters. |

Each root directory contains `.py` source and a `package.json` manifest for mip.  Pre-compiled `.mpy` bytecode is stored in two runtime-specific directories:

- **`circuitpython-10.x-mpy/`** — compiled with CircuitPython's mpy-cross, used by circup zip bundles.
- **`mpy6/`** — compiled with MicroPython's mpy-cross, installable via `mip`.

CircuitPython and MicroPython `.mpy` files are not interchangeable — each runtime's mpy-cross embeds a different magic byte in the header.

## About

This repo is generated automatically by the [ChuMicro release workflow](https://github.com/ChuMicro/ChuMicro/blob/main/.github/workflows/release.yml). Don't edit it by hand — changes will be overwritten on the next release.

- **Source code and examples:** [ChuMicro/ChuMicro](https://github.com/ChuMicro/ChuMicro)
- **Documentation:** [chumicro.github.io/ChuMicro](https://chumicro.github.io/ChuMicro/)
- **Experimental bundle:** [ChuMicro/ChuMicro-Bundle-Experimental](https://github.com/ChuMicro/ChuMicro-Bundle-Experimental)
- **License:** [MIT](LICENSE)
