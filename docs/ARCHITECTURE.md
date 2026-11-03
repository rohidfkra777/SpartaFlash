# SpartaFlash - Technical Architecture & HAL Specification

## 1. Hardware Abstraction Layer (HAL)
The application decouples user interface workflows from time-critical serial bus communication using a Hardware Abstraction Layer.

* **High-Speed Deterministic Driver**: Time-sensitive hardware handshakes and flashing protocols run via native runtime drivers (`.pyd` / compiled libraries) to ensure sub-millisecond synchronization.
* **Worker Thread Isolation**: All serial communication and firmware flashing occur on dedicated background QThread workers, maintaining UI responsiveness at 60 FPS.

## 2. Security & RBAC Model
* **Credential Protection**: Account credentials are verified against salted cryptographic hashes .
* **Role Hierarchy**:
  * `ADMIN`: Full administrative control over station settings, user provisioning, and diagnostic testing.
  * `OPERATOR`: Production-line role restricted to flashing, viewing read-only telemetry, and exporting shift history.

## 3. Telemetry Integration
Workstation telemetry communicates with standard MQTT v3.1.1/v5 broker endpoints using topic partitioning:
* `alfa/device/{mac}/telemetry`
* `alfa/device/{mac}/command`
* `alfa/station/{station_id}/status`
