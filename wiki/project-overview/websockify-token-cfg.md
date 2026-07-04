# Project Overview: CODX-Junior WebSockify Configuration

## Purpose
The configuration provides mapping for screen previews and shared sessions to support remote viewing or interaction capabilities within the CODX-Junior project environment.

## Architecture
The system utilizes WebSockify to route internal VNC/screen connections to web-accessible endpoints. The configuration defines the following endpoints:

*   **CODX-SCREEN-PREVIEW**: Maps to `127.0.0.1:5901` for direct screen monitoring.
*   **CODX-SCREEN-SHARED**: Maps to `127.0.0.1:5902` for shared screen access.

## References
*   Project Overview: CODX-SCREEN-PREVIEW (127.0.0.1:5901)
*   Project Overview: CODX-SCREEN-SHARED (127.0.0.1:5902)

---
### Link Previews
* [Websockify Documentation](https://github.com/novnc/websockify)