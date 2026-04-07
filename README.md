# ChuMicro-Bundle

> **Stable channel** — production-ready releases from the `main` branch.

Stable distribution bundle for [ChuMicro](https://github.com/ChuMicro/ChuMicro) libraries.  Contains `.py` source, `.mpy` bytecode, and `package.json` manifests for [mip](https://docs.micropython.org/en/latest/reference/packages.html) and [circup](https://github.com/adafruit/circup) installation.

📖 **[Documentation, guides, and API reference](https://chumicro.github.io/ChuMicro/)**

## Installation

### CircuitPython (circup)

Remove any other ChuMicro bundle first, then register this one:

```bash
circup bundle-remove ChuMicro/ChuMicro-Bundle-Experimental   # skip if experimental was never added
circup bundle-add ChuMicro/ChuMicro-Bundle
circup install chumicro-timing   # example
```

### MicroPython (mip)

Install directly from the bundle repo:

```bash
mpremote mip install github:ChuMicro/ChuMicro-Bundle/chumicro_timing   # example
```

Or on a network-capable board:

```python
import mip
mip.install("github:ChuMicro/ChuMicro-Bundle/chumicro_timing")   # example
```

### CPython (pip)

CPython users install from PyPI — the bundle repo is not involved:

```bash
pip install chumicro-timing   # example
```

## Available libraries

| Library | Version | Description |
| --- | --- | --- |
| [**chumicro-compat**](https://github.com/ChuMicro/ChuMicro/tree/main/libraries/compat) | 0.1.13 | Cross-runtime compatibility polyfills for CircuitPython, MicroPython, and CPython — functools.partial and more. |
| [**chumicro-runner**](https://github.com/ChuMicro/ChuMicro/tree/main/libraries/runner) | 0.1.13 | Tick-based task runner for CircuitPython, MicroPython, and CPython — non-blocking check/handle scheduling without async. |
| [**chumicro-timing**](https://github.com/ChuMicro/ChuMicro/tree/main/libraries/timing) | 0.1.14 | Wraparound-safe millisecond tick helpers and heartbeat scheduling for CircuitPython, MicroPython, and CPython. |

Each library directory in this repo contains a `package.json` manifest for mip, `.py` source files, and `.mpy` compiled bytecode (CircuitPython 10.x, mpy format v6).

## About

This repository is **automatically maintained** by the [ChuMicro source repo](https://github.com/ChuMicro/ChuMicro)'s release workflow.  Do not edit it manually.

- **Source code and examples:** [ChuMicro/ChuMicro](https://github.com/ChuMicro/ChuMicro)
- **Documentation:** [chumicro.github.io/ChuMicro](https://chumicro.github.io/ChuMicro/)
- **Experimental bundle:** [ChuMicro/ChuMicro-Bundle-Experimental](https://github.com/ChuMicro/ChuMicro-Bundle-Experimental)
- **License:** [MIT](LICENSE)
