# Scan Watcher Deployment Log Documentation

## Overview
This document describes the network monitoring scan initiated on August 9, 2026 at 2:17:49 PM CEST using the scan watcher utility.

## Configuration Details

### Network Interface Setup
- **Interface**: any (monitoring all interfaces)
- **Direction**: outbound traffic
- **Local IPs Monitored**: 135.181.0.35, 172.22.0.1, 172.21.0.1, 172.20.0.1, 172.19.0.1, 172.26.0.1, 172.23.0.1, 172.27.0.1, 172.18.0.1, 172.28.0.1, 172.24.0.1, 172.25.0.1, 10.200.0.1

### Monitored Ports
The scan watches for activity on the following ports:
- **Database Services**: 27017 (MongoDB), 3306 (MySQL), 5432 (PostgreSQL), 5984 (CouchDB)
- **Cache Services**: 6379, 6380 (Redis)
- **Blockchain/Web3**: 8545, 8546, 8547 (Ethereum RPC)
- **Search/Indexing**: 9200, 9300 (Elasticsearch)
- **Container/API Services**: 2375, 2376 (Docker), 8091 (Couchbase), 2379 (etcd)
- **Remote Access**: 23 (Telnet), 2323, 445 (SMB), 3389 (RDP), 5900 (VNC)
- **Chat/IRC**: 6667, 6697 (IRC)
- **Web Services**: 4444, 4445, 8081, 8888

### Operational Mode
- **Mode**: list
- **Packet Capture**: Full packet capture enabled at `./scanwatch_20260809_141749/capture_20260809_141749.pcap`
- **Event Log**: `./scanwatch_20260809_141749/scan_events_20260809_141749.log`

## Runtime Information
- **Process ID**: 2558699
- **Status**: Watcher running
- **Control**: Press Ctrl+C to stop the monitoring process