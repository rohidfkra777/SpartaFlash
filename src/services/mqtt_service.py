"""
SpartaFlash - Real-time MQTT Fleet Monitoring & Control Service.
Developer: Rohidfkra777

Connects directly to the official IoT Broker (MQTT_BROKER:1883)
using locked production credentials (sparta-ganteng).
Subscribes to AlfaEnergy/#, tele/#, stat/# to monitor real-time telemetry (V, A, W, kWh)
and sends commands (Power, Status, TelePeriod, Restart, Upgrade) per MQTT_LOCAL_GUIDE.md.
"""

import json
import logging
import time
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List

from PySide6.QtCore import QObject, Signal

try:
    import paho.mqtt.client as mqtt
    PAHO_AVAILABLE = True
except ImportError:
    PAHO_AVAILABLE = False
    mqtt = None

from src.config.constants import (
    DEFAULT_MQTT_BROKER,
    DEFAULT_MQTT_PORT,
    DEFAULT_MQTT_USER,
    DEFAULT_MQTT_PASSWORD,
    DEFAULT_MQTT_KEEPALIVE,
    DEFAULT_MQTT_TOPIC_PREFIX,
    PRODUCT_PLUG,
    PRODUCT_CT,
)
from src.database.db_manager import db_manager
from src.database.models import RegisteredDevice

logger = logging.getLogger("AlfaEnergyFlasher")


class MqttService(QObject):
    """
    Background MQTT Service bridging Paho MQTT network thread with Qt GUI signals.
    Thread-safe, locked to the official IoT broker with auto-reconnect.
    """

    # Signals
    sig_connection_changed = Signal(bool, str)        # (is_connected, status_text)
    sig_message_received = Signal(str, str, str)       # (topic, payload, timestamp_str)
    sig_device_updated = Signal(str)                  # (mac_address)
    sig_device_registered = Signal(str)               # (mac_address)
    sig_log_event = Signal(str, str)                  # (level, message)
    sig_device_event = Signal(str, str, dict)         # (mac_address, event_name, payload_dict)
    sig_buffer_progress = Signal(str, int, int)       # (mac_address, seq, total_records)

    _instance: Optional["MqttService"] = None

    @classmethod
    def get_instance(cls) -> "MqttService":
        if cls._instance is None:
            cls._instance = MqttService()
        return cls._instance

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        # Broker configuration is locked strictly to official IoT broker
        self.broker = DEFAULT_MQTT_BROKER
        self.port = DEFAULT_MQTT_PORT
        self.keepalive = DEFAULT_MQTT_KEEPALIVE
        self.username: str = DEFAULT_MQTT_USER
        self.password: str = DEFAULT_MQTT_PASSWORD

        self._client: Optional[mqtt.Client] = None
        self._is_connected = False
        self._client_id = f"AlfaEnergyFlasher_{uuid.uuid4().hex[:6]}"
        self._subscribed_topics: List[str] = [
            f"{DEFAULT_MQTT_TOPIC_PREFIX}/Plug/#",
            f"{DEFAULT_MQTT_TOPIC_PREFIX}/CT/#",
            f"{DEFAULT_MQTT_TOPIC_PREFIX}/meta/#"
        ]
        self._ip_query_tracker: Dict[str, float] = {}
        self._buffer_sync_trackers: Dict[str, Dict[str, Any]] = {}

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    def start(self, *args, **kwargs) -> bool:
        """
        Initializes and connects to the official IoT broker in a background thread.
        Broker host, port, and credentials cannot be overridden (locked default).
        """
        if not PAHO_AVAILABLE:
            self.sig_log_event.emit("ERROR", "paho-mqtt library is not installed.")
            return False

        self.broker = DEFAULT_MQTT_BROKER
        self.port = DEFAULT_MQTT_PORT
        self.username = DEFAULT_MQTT_USER
        self.password = DEFAULT_MQTT_PASSWORD

        self.stop()

        try:
            # Paho MQTT 2.x CallbackAPIVersion support with MQTT 3.1.1 standard
            if hasattr(mqtt, "CallbackAPIVersion"):
                self._client = mqtt.Client(
                    mqtt.CallbackAPIVersion.VERSION2,
                    client_id=self._client_id,
                    protocol=mqtt.MQTTv311,
                    clean_session=True
                )
            else:
                self._client = mqtt.Client(
                    client_id=self._client_id,
                    protocol=mqtt.MQTTv311,
                    clean_session=True
                )

            if self.username and self.password:
                self._client.username_pw_set(self.username, self.password)

            self._client.on_connect = self._on_connect
            self._client.on_disconnect = self._on_disconnect
            self._client.on_message = self._on_message

            logger.info(f"Connecting to Official AlfaEnergy Broker: {self.broker}:{self.port} as {self._client_id}...")
            self._client.connect_async(self.broker, self.port, self.keepalive)
            self._client.loop_start()
            return True

        except Exception as e:
            logger.error(f"Failed to start MQTT service: {e}", exc_info=True)
            self.sig_connection_changed.emit(False, f"Connection error: {str(e)}")
            return False

    def stop(self) -> None:
        """Disconnects client and stops network background loop."""
        if self._client:
            try:
                self._client.loop_stop()
                self._client.disconnect()
            except Exception as e:
                logger.warning(f"Error stopping MQTT client: {e}")
            finally:
                self._client = None
                self._is_connected = False
                self.sig_connection_changed.emit(False, "Disconnected")

    def _on_connect(self, client, userdata, flags, reason_code, properties=None):
        rc = getattr(reason_code, "value", reason_code)
        if rc == 0:
            self._is_connected = True
            logger.info(f"MQTT Connected successfully to {self.broker}:{self.port}")
            self.sig_connection_changed.emit(True, "Connected")

            # Subscribe to fleet telemetry & status topics
            for topic in self._subscribed_topics:
                client.subscribe(topic, qos=0)
                logger.debug(f"Subscribed to MQTT topic: {topic}")

            # Subscribe only to explicit topics of registered devices (never AlfaEnergy/EM-XXXX/#)
            self.subscribe_registered_devices()
        else:
            self._is_connected = False
            msg = f"Connection failed (code: {rc})"
            logger.warning(f"MQTT {msg}")
            self.sig_connection_changed.emit(False, msg)

    def _on_disconnect(self, client, userdata, disconnect_flags_or_rc, reason_code=None, properties=None):
        self._is_connected = False
        logger.warning(f"MQTT Disconnected from {self.broker}:{self.port}")
        self.sig_connection_changed.emit(False, "Disconnected")

    def _on_message(self, client, userdata, msg):
        """Processes incoming MQTT messages and parses official AlfaEnergy Plug & CT telemetry."""
        try:
            topic = msg.topic
            # Strict topic filter: ONLY process AlfaEnergy/Plug/#, AlfaEnergy/CT/#, and AlfaEnergy/meta/#
            # All other legacy, flat, or general broker topics (e.g. EM, MC, tele/#, stat/#) are strictly ignored.
            if not (topic.startswith(f"{DEFAULT_MQTT_TOPIC_PREFIX}/Plug/") or 
                    topic.startswith(f"{DEFAULT_MQTT_TOPIC_PREFIX}/CT/") or 
                    topic.startswith(f"{DEFAULT_MQTT_TOPIC_PREFIX}/meta/")):
                return

            payload_str = msg.payload.decode("utf-8", errors="replace")
            timestamp_str = datetime.now().strftime("%H:%M:%S.%f")[:-3]

            # Emit filtered message for Live Console
            try:
                self.sig_message_received.emit(topic, payload_str, timestamp_str)
                # Analyze topic and correlate with registered device
                self._process_device_message(topic, payload_str)
            except RuntimeError:
                pass

        except Exception as e:
            logger.error(f"Error handling MQTT message on {msg.topic}: {e}", exc_info=True)

    def _process_device_message(self, topic: str, payload_str: str) -> None:
        """
        Parses official AlfaEnergy topic hierarchy (per MQTT_LOCAL_GUIDE.md):
        - AlfaEnergy/Plug/<MAC>/tele/LWT, SENSOR, STATE, etc.
        - AlfaEnergy/CT/<MAC>/tele/LWT, SENSOR, STATE, etc.
        - AlfaEnergy/meta/<KEY>/notes -> Retained notes sync
        """
        parts = topic.split("/")
        if len(parts) < 3 or parts[0] != DEFAULT_MQTT_TOPIC_PREFIX:
            return

        # Solution 2: Cross-computer retained metadata synchronization (AlfaEnergy/meta/<KEY>/notes)
        if parts[1].upper() == "META":
            if len(parts) >= 4 and parts[3].lower() == "notes":
                device_key = parts[2]
                matched = self._find_or_create_device(device_key)
                if matched:
                    new_note = payload_str.strip() or None
                    if matched.notes != new_note:
                        matched.notes = new_note
                        db_manager.update_device_notes(matched.mac_address, new_note)
                        try:
                            self.sig_device_updated.emit(matched.mac_address)
                        except RuntimeError:
                            pass
            return

        # Strictly allow only Plug and CT categories (latest official firmware)
        if parts[1].upper() not in ("PLUG", "CT"):
            return

        category_hint = PRODUCT_PLUG if parts[1].upper() == "PLUG" else PRODUCT_CT
        device_key = parts[2]
        prefix = parts[3] if len(parts) >= 4 else ""
        subtopic = parts[4] if len(parts) >= 5 else (parts[3] if len(parts) >= 4 else "")

        # Ignore legacy store meters (EM), controllers (MC), broadcast groups, or subtopics
        up_key = device_key.upper().strip()
        if "EM" in up_key or "MC" in up_key or up_key in (
            "ALFAENERGY_ALL", "ALFAENERGY_PLUG_ALL", "ALFAENERGY_CT_ALL",
            "TELE", "STAT", "CMND", "STATUS", "PLUG", "CT"
        ):
            return

        matched_device = self._find_or_create_device(device_key, category_hint)
        if not matched_device:
            return

        mac = matched_device.mac_address
        updated = False

        # Universal IP Detection: Extract valid IP from any Tasmota payload format
        detected_ip = self._extract_ip_address(payload_str)
        if detected_ip:
            db_manager.update_device_telemetry(mac_address=mac, ip=detected_ip, status="ONLINE")
            matched_device.ip_address = detected_ip
            updated = True
        elif not matched_device.ip_address:
            # Proactively query network status (Status 5) if device is online but has no IP
            self._proactive_query_ip(matched_device)

        # Solution 1: Device hardware flash DeviceName / FriendlyName extraction
        if "{" in payload_str and ("DeviceName" in payload_str or "FriendlyName" in payload_str or "FriendlyName1" in payload_str):
            try:
                j_obj = json.loads(payload_str)
                d_name = None
                if isinstance(j_obj, dict):
                    d_name = j_obj.get("DeviceName")
                    if not d_name and "Status" in j_obj and isinstance(j_obj["Status"], dict):
                        d_name = j_obj["Status"].get("DeviceName")
                    if not d_name and "StatusPRM" in j_obj and isinstance(j_obj["StatusPRM"], dict):
                        d_name = j_obj["StatusPRM"].get("DeviceName")
                    if not d_name and "FriendlyName1" in j_obj:
                        fn1 = j_obj["FriendlyName1"]
                        d_name = fn1[0] if isinstance(fn1, list) and fn1 else (fn1 if isinstance(fn1, str) else None)
                    if not d_name and "FriendlyName" in j_obj:
                        fn = j_obj["FriendlyName"]
                        d_name = fn[0] if isinstance(fn, list) and fn else (fn if isinstance(fn, str) else None)
                if d_name and isinstance(d_name, str):
                    clean_dname = d_name.strip()
                    if clean_dname and not clean_dname.startswith("AlfaEnergy") and not clean_dname.startswith("Tasmota"):
                        if matched_device.notes != clean_dname:
                            matched_device.notes = clean_dname
                            db_manager.update_device_notes(mac, clean_dname)
                            updated = True
            except Exception:
                pass

        # 0A. Offline Data Buffering Replay (tele/HISTORY)
        if subtopic in ("HISTORY", "history"):
            try:
                data = json.loads(payload_str)
                rec_time = data.get("Time")
                seq = data.get("Seq", 0)
                energy_data = data.get("ENERGY", {})

                v = energy_data.get("Voltage")
                c = energy_data.get("Current")
                p = energy_data.get("Power")
                pf = energy_data.get("Factor", energy_data.get("PowerFactor"))
                tot = energy_data.get("Total")

                if rec_time:
                    db_manager.insert_telemetry_history(
                        mac_address=mac,
                        recorded_at=rec_time,
                        voltage=float(v) if v is not None else None,
                        current=float(c) if c is not None else None,
                        power=float(p) if p is not None else None,
                        power_factor=float(pf) if pf is not None else None,
                        energy_total=float(tot) if tot is not None else None,
                        is_offline_buffer=1,
                        seq_num=int(seq) if seq is not None else None
                    )

                # Update in-memory sync progress tracker
                if mac in self._buffer_sync_trackers:
                    self._buffer_sync_trackers[mac]["seq"] = int(seq)
                    total = self._buffer_sync_trackers[mac].get("total", 0)
                    try:
                        self.sig_buffer_progress.emit(mac, int(seq), total)
                    except RuntimeError:
                        pass
            except Exception as err:
                logger.debug(f"Could not parse HISTORY payload: {err}")
            return  # Isolated from live telemetry; never overwrite live metrics

        # 0B. Offline Data Buffer Events (tele/EVENT)
        elif subtopic in ("EVENT", "event"):
            try:
                data = json.loads(payload_str)
                event_name = data.get("Event", "")
                if event_name == "InternetRestored":
                    buffered = int(data.get("BufferedRecords", 0))
                    downtime = int(data.get("DowntimeSec", 0))
                    self._buffer_sync_trackers[mac] = {
                        "total": buffered,
                        "seq": 0,
                        "downtime": downtime,
                        "start_time": time.time()
                    }
                    db_manager.update_device_status(mac, "ONLINE")
                    try:
                        self.sig_device_event.emit(mac, "InternetRestored", data)
                        self.sig_device_updated.emit(mac)
                    except RuntimeError:
                        pass
                elif event_name == "SyncComplete":
                    replayed = int(data.get("ReplayedRecords", 0))
                    if mac in self._buffer_sync_trackers:
                        del self._buffer_sync_trackers[mac]
                    db_manager.update_device_status(mac, "ONLINE")
                    try:
                        self.sig_device_event.emit(mac, "SyncComplete", data)
                        self.sig_device_updated.emit(mac)
                    except RuntimeError:
                        pass
                else:
                    try:
                        self.sig_device_event.emit(mac, event_name, data)
                    except RuntimeError:
                        pass
            except Exception as err:
                logger.debug(f"Could not parse EVENT payload: {err}")
            return

        # 0C. Firmware Buffer Status Diagnostic (stat/BUFFER or stat/RESULT)
        elif subtopic in ("BUFFER", "buffer") or ("{" in payload_str and '"Buffer"' in payload_str):
            try:
                data = json.loads(payload_str)
                buf_info = data.get("Buffer", data)
                if isinstance(buf_info, dict) and ("UsedRecords" in buf_info or "Records" in buf_info or "State" in buf_info):
                    try:
                        self.sig_device_event.emit(mac, "BufferStatus", buf_info)
                    except RuntimeError:
                        pass
            except Exception as err:
                logger.debug(f"Could not parse BUFFER status payload: {err}")

        # 1. LWT / Online State
        if subtopic in ("LWT", "online") or (prefix == "status" and subtopic == "online"):
            is_on = payload_str.strip().lower() in ("online", "true", "1")
            status = "ONLINE" if is_on else "OFFLINE"
            db_manager.update_device_status(mac, status)
            if is_on and not matched_device.ip_address:
                self._proactive_query_ip(matched_device)
            updated = True

        elif subtopic in ("SENSOR", "STATUS8", "R", "S", "T") or (prefix == "3P") or ("{" in payload_str and ("V" in payload_str or "ENERGY" in payload_str)):
            try:
                data = json.loads(payload_str)
                energy = data.get("ENERGY", data.get("StatusSNS", {}).get("ENERGY", data))

                v = None
                c = None
                p = None
                e = None

                if isinstance(energy, dict):
                    v = energy.get("Voltage", energy.get("V"))
                    c = energy.get("Current", energy.get("A"))
                    p = energy.get("Power", energy.get("W"))
                    e = energy.get("Total", energy.get("kWh", energy.get("Today")))

                    # Support 3-phase CT nested dictionary (e.g., {"3P/R": {"Voltage": 220.5, ...}})
                    phase_sub = energy.get("3P/R", energy.get("3P", energy.get("Phase_1", energy.get("Phase1"))))
                    if isinstance(phase_sub, dict):
                        if v is None:
                            v = phase_sub.get("Voltage", phase_sub.get("V"))
                        if c is None:
                            c = phase_sub.get("Current", phase_sub.get("A"))
                        if p is None:
                            p = phase_sub.get("Power", phase_sub.get("W"))
                        if e is None:
                            e = phase_sub.get("Total", phase_sub.get("kWh"))

                # Guard against multi-phase array/list values (e.g. [220.1, 219.5, 221.0])
                if isinstance(v, list) and v:
                    v = v[0]
                if isinstance(c, list) and c:
                    c = sum(float(x) for x in c if x is not None)
                if isinstance(p, list) and p:
                    p = sum(float(x) for x in p if x is not None)
                if isinstance(e, list) and e:
                    e = sum(float(x) for x in e if x is not None)

                if v is not None or c is not None or p is not None or e is not None:
                    db_manager.update_device_telemetry(
                        mac_address=mac,
                        voltage=float(v) if v is not None else None,
                        current=float(c) if c is not None else None,
                        power=float(p) if p is not None else None,
                        energy=float(e) if e is not None else None,
                        status="ONLINE"
                    )
                    updated = True
            except Exception as err:
                logger.debug(f"Could not parse telemetry payload: {err}")

        # 4. STATE (Uptime, Power State, Wi-Fi RSSI)
        elif subtopic == "STATE":
            try:
                data = json.loads(payload_str)
                p_state = data.get("POWER")
                wifi = data.get("Wifi", {})
                rssi = wifi.get("RSSI")
                ssid = wifi.get("SSId")

                db_manager.update_device_telemetry(
                    mac_address=mac,
                    power_state=p_state,
                    wifi_rssi=int(rssi) if rssi is not None else None,
                    wifi_ssid=ssid,
                    status="ONLINE"
                )
                updated = True
            except Exception as err:
                logger.debug(f"Could not parse STATE payload: {err}")

        # 5. POWER direct confirmation
        elif subtopic in ("POWER", "RESULT"):
            p_state = None
            if "{" in payload_str:
                try:
                    p_state = json.loads(payload_str).get("POWER")
                except Exception:
                    pass
            else:
                s = payload_str.strip().upper()
                if s in ("ON", "OFF"):
                    p_state = s

            if p_state:
                db_manager.update_device_telemetry(
                    mac_address=mac,
                    power_state=p_state,
                    status="ONLINE"
                )
                updated = True

        if updated:
            try:
                self.sig_device_updated.emit(mac)
            except RuntimeError:
                pass

    @staticmethod
    def _extract_ip_address(payload_str: str) -> Optional[str]:
        """
        Extracts valid IPv4 address from any standard or nested Tasmota payload format
        (Info2, StatusNET, Wifi, Status 0, or direct raw IP string).
        """
        if not payload_str:
            return None
        clean_text = payload_str.strip()
        # Direct raw IP string
        if clean_text.count(".") == 3 and not clean_text.startswith("{"):
            parts = clean_text.split(".")
            if all(p.isdigit() and 0 <= int(p) <= 255 for p in parts):
                return clean_text

        if "{" in payload_str:
            try:
                data = json.loads(payload_str)
                if isinstance(data, dict):
                    # Check direct keys
                    for k in ("IPAddress", "IP", "ip"):
                        val = data.get(k)
                        if val and isinstance(val, str) and "." in val and val != "0.0.0.0":
                            return val.strip()

                    # Check nested containers (Info2, StatusNET, Wifi, Status, Network)
                    for container_key in ("Info2", "StatusNET", "Wifi", "Status", "Network"):
                        sub = data.get(container_key)
                        if isinstance(sub, dict):
                            for k in ("IPAddress", "IP", "ip"):
                                val = sub.get(k)
                                if val and isinstance(val, str) and "." in val and val != "0.0.0.0":
                                    return val.strip()
            except Exception:
                pass
        return None

    def _proactive_query_ip(self, device: RegisteredDevice):
        """
        Proactively requests network status (Status 5) if an online device's IP is not yet recorded.
        Protected by a 60-second cooldown per device to avoid query flooding.
        """
        import time
        now = time.time()
        clean_mac = device.mac_address.upper().strip()
        last_query = self._ip_query_tracker.get(clean_mac, 0.0)
        if now - last_query < 60.0:
            return

        self._ip_query_tracker[clean_mac] = now
        mac_key = self.get_device_topic_key(clean_mac)
        cat = "Plug" if device.product_category == PRODUCT_PLUG else "CT"
        query_topic = f"AlfaEnergy/{cat}/{mac_key}/cmnd/Status"
        self.publish_raw(query_topic, "5")
        logger.info(f"Proactively queried network IP (Status 5) for {device.device_name} ({clean_mac})")

    def _find_or_create_device(self, device_key: str, category_hint: Optional[str] = None) -> Optional[RegisteredDevice]:
        """
        Finds a registered device by device_name, full MAC, or 6-char MAC suffix.
        Auto-registers if it is recognized as an active AlfaEnergy unit with valid MAC hex.
        Explicitly excludes legacy store meters (EM) and microcontrollers (MC).
        """
        up_key = device_key.upper().strip()
        if "EM" in up_key or "MC" in up_key or up_key in (
            "ALFAENERGY_ALL", "ALFAENERGY_PLUG_ALL", "ALFAENERGY_CT_ALL",
            "TELE", "STAT", "CMND", "STATUS", "PLUG", "CT"
        ):
            return None

        all_devices = db_manager.get_all_registered_devices()

        # Match exact device_name
        for d in all_devices:
            if d.device_name.lower() == device_key.lower():
                return d

        # Match clean MAC suffix (e.g. key is 'E62A34' and mac is 'AC:15:18:E6:2A:34')
        clean_key = device_key.replace(":", "").replace("-", "").upper()
        if clean_key.startswith("NET"):
            clean_key = clean_key[3:]
        clean_suffix = clean_key[-6:] if len(clean_key) >= 6 else clean_key

        # Approach A: Find existing device by canonical suffix
        found = db_manager.get_registered_device(clean_suffix)
        if not found:
            found = db_manager.get_registered_device(device_key)

        if found:
            # Update category and device name prefix if mismatched (e.g. from Plug to CT)
            if category_hint and found.product_category != category_hint:
                found.product_category = category_hint
                prefix = "AlfaEnergy_CT" if category_hint == PRODUCT_CT else "AlfaEnergy_Plug"
                found.device_name = f"{prefix}-{clean_suffix}"
                db_manager.register_device(found)
            return found

        # Only auto-register if clean_suffix is a valid 6-char hexadecimal MAC suffix
        is_hex = all(c in "0123456789ABCDEF" for c in clean_suffix)
        if not is_hex or len(clean_suffix) != 6:
            return None

        # Check if full MAC is in production audit history (flashed devices)
        category = category_hint or (PRODUCT_CT if "_CT" in device_key else PRODUCT_PLUG)
        prefix = "AlfaEnergy_CT" if category == PRODUCT_CT else "AlfaEnergy_Plug"
        device_name = f"{prefix}-{clean_suffix}"
        real_mac = None

        recent_records = db_manager.get_records(limit=300)
        for r in recent_records:
            if r.mac_address:
                r_clean = r.mac_address.replace(":", "").replace("-", "").upper()
                if r_clean.endswith(clean_suffix):
                    real_mac = r.mac_address
                    break

        final_mac = real_mac if real_mac else f"NET:{clean_suffix}"
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        dev = RegisteredDevice(
            mac_address=final_mac,
            device_name=device_name,
            product_category=category,
            flashed_at=now_str,
            status="ONLINE",
            notes="Active AlfaEnergy unit"
        )
        db_manager.register_device(dev)
        self.sig_device_registered.emit(dev.mac_address)
        logger.info(f"Auto-registered active device from AlfaEnergy broker: {device_name} ({final_mac}) [{category}]")
        return dev

    def auto_register_flashed_device(self, mac_address: str, category: str, batch_name: Optional[str] = None) -> RegisteredDevice:
        """
        Called immediately upon successful flashing completion to insert the device into the fleet roster.
        """
        clean_mac = mac_address.upper().strip()
        mac_suffix = clean_mac.replace(":", "")[-6:]
        prefix = "AlfaEnergy_Plug" if category == PRODUCT_PLUG else "AlfaEnergy_CT"
        device_name = f"{prefix}-{mac_suffix}"

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        device = RegisteredDevice(
            mac_address=clean_mac,
            device_name=device_name,
            product_category=category,
            flashed_at=now_str,
            status="OFFLINE",
            batch_name=batch_name,
            notes="Flashed by SpartaFlash"
        )
        db_manager.register_device(device)
        self.sig_device_registered.emit(clean_mac)
        logger.info(f"Device successfully registered into fleet roster: {device_name} ({clean_mac})")

        # Explicitly subscribe to this device's topic (never wildcard AlfaEnergy/#)
        self.subscribe_device(clean_mac)
        return device

    def get_device_category(self, device_name_or_mac: str) -> str:
        """Returns 'Plug' or 'CT' based on device information."""
        dev = self._resolve_device(device_name_or_mac)
        if dev and dev.product_category == PRODUCT_CT:
            return "CT"
        clean = device_name_or_mac.upper()
        if "_CT" in clean or "-CT" in clean or clean.endswith("CT"):
            return "CT"
        return "Plug"

    def subscribe_device(self, mac_or_name: str, category: Optional[str] = None) -> None:
        """Subscribes strictly to an individual device topic on AlfaEnergy/<Category>/<KEY>/#."""
        mac_key = self.get_device_topic_key(mac_or_name)
        up = mac_key.upper()
        if "EM" in up or "MC" in up:
            return
        cat = category or self.get_device_category(mac_or_name)
        if self._client and self._is_connected:
            topic = f"{DEFAULT_MQTT_TOPIC_PREFIX}/{cat}/{mac_key}/#"
            self._client.subscribe(topic, qos=0)
            logger.info(f"Subscribed strictly to device topic: {topic}")

    def unsubscribe_device(self, mac_or_name: str, category: Optional[str] = None) -> None:
        """Unsubscribes from an individual device topic."""
        mac_key = self.get_device_topic_key(mac_or_name)
        cat = category or self.get_device_category(mac_or_name)
        if self._client and self._is_connected:
            topic = f"{DEFAULT_MQTT_TOPIC_PREFIX}/{cat}/{mac_key}/#"
            self._client.unsubscribe(topic)
            logger.info(f"Unsubscribed from device topic: {topic}")

    def subscribe_registered_devices(self) -> None:
        """Subscribes strictly to all registered devices in local database, ignoring EM-XXXX."""
        if not self._client or not self._is_connected:
            return
        for dev in db_manager.get_all_registered_devices():
            cat = "Plug" if dev.product_category == PRODUCT_PLUG else "CT"
            self.subscribe_device(dev.mac_address, category=cat)

    def get_device_topic_key(self, device_name_or_mac: str) -> str:
        """Derives 6-char MAC hex or deviceId for AlfaEnergy/<Category>/<KEY>/... format."""
        dev = self._resolve_device(device_name_or_mac)
        if dev:
            if ":" in dev.mac_address:
                return dev.mac_address.replace(":", "")[-6:].upper()
            if "-" in dev.device_name:
                return dev.device_name.split("-")[-1].upper()
            return dev.mac_address
        clean = device_name_or_mac.strip().replace(":", "")
        return clean[-6:].upper() if len(clean) >= 6 else clean

    def publish_power(self, device_name_or_mac: str, state: str = "TOGGLE") -> bool:
        """Publishes Power command to AlfaEnergy/Plug/<MAC>/cmnd/Power."""
        mac_key = self.get_device_topic_key(device_name_or_mac)
        topic = f"{DEFAULT_MQTT_TOPIC_PREFIX}/Plug/{mac_key}/cmnd/Power"
        return self.publish_raw(topic, state)

    def publish_restart(self, device_name_or_mac: str) -> bool:
        """Publishes restart command to AlfaEnergy/<Category>/<MAC>/cmnd/Restart 1."""
        mac_key = self.get_device_topic_key(device_name_or_mac)
        cat = self.get_device_category(device_name_or_mac)
        topic = f"{DEFAULT_MQTT_TOPIC_PREFIX}/{cat}/{mac_key}/cmnd/Restart"
        return self.publish_raw(topic, "1")

    def publish_query_status(self, device_name_or_mac: str, status_code: str = "8") -> bool:
        """Queries status and telemetry AlfaEnergy/<Category>/<MAC>/cmnd/Status."""
        mac_key = self.get_device_topic_key(device_name_or_mac)
        cat = self.get_device_category(device_name_or_mac)
        topic = f"{DEFAULT_MQTT_TOPIC_PREFIX}/{cat}/{mac_key}/cmnd/Status"
        return self.publish_raw(topic, status_code)

    def publish_raw(self, topic: str, payload: str, qos: int = 0, retain: bool = False) -> bool:
        """Publishes raw MQTT message (MQTTX style)."""
        if not self._client or not self._is_connected:
            logger.warning(f"Cannot publish to {topic}: MQTT not connected.")
            return False

        try:
            self._client.publish(topic, payload, qos=qos, retain=retain)
            logger.info(f"Published MQTT (retain={retain}): [{topic}] -> {payload}")
            return True
        except Exception as e:
            logger.error(f"Failed to publish to {topic}: {e}")
            return False

    def sync_device_notes(self, mac_address: str, notes: Optional[str], category: Optional[str] = None) -> bool:
        """
        Synchronizes device custom notes / location across all computers and device hardware (Option A):
        1. Local SQLite database persistence.
        2. Shared MQTT Broker Retained message (AlfaEnergy/meta/<KEY>/notes, retain=True).
        3. Device internal NVS flash parameters via Tasmota commands:
           - cmnd/DeviceName <notes> (Web UI Header & Network Hostname)
           - cmnd/FriendlyName1 <notes> (Web UI Relay Switch / Toggle Label)
        """
        clean_mac = mac_address.upper().strip()
        clean_notes = notes.strip() if notes else None

        # 1. Update local database
        db_manager.update_device_notes(clean_mac, clean_notes)

        mac_key = self.get_device_topic_key(clean_mac)
        cat = category or self.get_device_category(clean_mac)
        payload = clean_notes or ""
        hw_payload = payload if payload else "0"

        # 2. Solution 2: Publish retained metadata to shared broker (retained indefinitely across PCs)
        meta_topic = f"{DEFAULT_MQTT_TOPIC_PREFIX}/meta/{mac_key}/notes"
        self.publish_raw(meta_topic, payload, qos=1, retain=True)

        # 3. Solution 1 (Option A): Synchronize both DeviceName (Header) and FriendlyName1 (Relay button)
        # DeviceName command (Header Web UI & Hostname)
        cmnd_devname = f"{DEFAULT_MQTT_TOPIC_PREFIX}/{cat}/{mac_key}/cmnd/DeviceName"
        self.publish_raw(cmnd_devname, hw_payload, qos=0)
        flat_devname = f"{DEFAULT_MQTT_TOPIC_PREFIX}/{mac_key}/cmnd/DeviceName"
        self.publish_raw(flat_devname, hw_payload, qos=0)

        # FriendlyName1 command (Web UI Relay Toggle button label)
        cmnd_friendly = f"{DEFAULT_MQTT_TOPIC_PREFIX}/{cat}/{mac_key}/cmnd/FriendlyName1"
        self.publish_raw(cmnd_friendly, hw_payload, qos=0)
        flat_friendly = f"{DEFAULT_MQTT_TOPIC_PREFIX}/{mac_key}/cmnd/FriendlyName1"
        self.publish_raw(flat_friendly, hw_payload, qos=0)

        try:
            self.sig_device_updated.emit(clean_mac)
        except RuntimeError:
            pass
        return True

    def _resolve_device(self, key: str) -> Optional[RegisteredDevice]:
        clean_key = key.strip()
        dev = db_manager.get_registered_device(clean_key)
        if dev:
            return dev
        for d in db_manager.get_all_registered_devices():
            if d.device_name.lower() == clean_key.lower():
                return d
        return None


# Global singleton instance
mqtt_service = MqttService.get_instance()
