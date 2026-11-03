"""
SpartaFlash - SQLite Database Manager.
Developer: Rohidfkra777
"""

import sqlite3
import threading
import shutil
import logging
from contextlib import contextmanager
from pathlib import Path
from typing import List, Dict, Any, Optional
from src.config.constants import DATABASE_PATH, PORTABLE_DATABASE_PATH
from src.database.models import ProductionRecord, RegisteredDevice

class DatabaseManager:
    """Thread-safe SQLite database manager for production records and registered devices."""
    
    def __init__(self, db_path: Path = DATABASE_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        if self.db_path.resolve() == DATABASE_PATH.resolve():
            self._migrate_legacy_db_if_needed()
        self.init_database()

    def _migrate_legacy_db_if_needed(self) -> None:
        """
        Migrates legacy portable database to the persistent AppData location.
        Ensures existing production records are never lost when upgrading or moving application folders.
        """
        try:
            if not PORTABLE_DATABASE_PATH.exists():
                return
            if PORTABLE_DATABASE_PATH.resolve() == self.db_path.resolve():
                return

            # If persistent DB doesn't exist yet, copy the portable DB directly
            if not self.db_path.exists():
                shutil.copy2(PORTABLE_DATABASE_PATH, self.db_path)
                return

            # Check counts from portable DB
            with sqlite3.connect(str(PORTABLE_DATABASE_PATH), timeout=10.0) as conn_src:
                cur_src = conn_src.cursor()
                cur_src.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='production_records';")
                if not cur_src.fetchone():
                    return
                cur_src.execute("SELECT COUNT(*) FROM production_records;")
                src_count = cur_src.fetchone()[0]
                if src_count == 0:
                    return

            # Check counts from destination DB
            with sqlite3.connect(str(self.db_path), timeout=10.0) as conn_dst:
                cur_dst = conn_dst.cursor()
                cur_dst.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='production_records';")
                dst_tbl = cur_dst.fetchone()
                dst_count = 0
                if dst_tbl:
                    cur_dst.execute("SELECT COUNT(*) FROM production_records;")
                    dst_count = cur_dst.fetchone()[0]

            # If destination is empty but legacy has records, copy file over
            if dst_count == 0 and src_count > 0:
                shutil.copy2(PORTABLE_DATABASE_PATH, self.db_path)
                return

            # If legacy has more records than destination, merge them safely
            if src_count > dst_count:
                with sqlite3.connect(str(self.db_path), timeout=15.0) as conn_dst:
                    cur_dst = conn_dst.cursor()
                    cur_dst.execute("ATTACH DATABASE ? AS legacy_db;", (str(PORTABLE_DATABASE_PATH),))
                    cur_dst.execute("""
                        INSERT OR IGNORE INTO production_records (
                            transaction_id, start_time, end_time, product_category, firmware_name,
                            firmware_version, firmware_hash, target_chip, serial_port, baudrate,
                            mac_address, batch_name, equipment_id, result, verification_status,
                            duration_seconds, error_message, app_version, operator_notes, created_at
                        )
                        SELECT 
                            transaction_id, start_time, end_time, product_category, firmware_name,
                            firmware_version, firmware_hash, target_chip, serial_port, baudrate,
                            mac_address, batch_name, equipment_id, result, verification_status,
                            duration_seconds, error_message, app_version, operator_notes, created_at
                        FROM legacy_db.production_records;
                    """)
                    cur_dst.execute("SELECT name FROM legacy_db.sqlite_master WHERE type='table' AND name='registered_devices';")
                    if cur_dst.fetchone():
                        cur_dst.execute("""
                            INSERT OR IGNORE INTO registered_devices (
                                mac_address, device_name, product_category, flashed_at,
                                last_seen_at, ip_address, status, power_state, voltage,
                                current, power, energy, wifi_rssi, wifi_ssid, batch_name, notes
                            )
                            SELECT 
                                mac_address, device_name, product_category, flashed_at,
                                last_seen_at, ip_address, status, power_state, voltage,
                                current, power, energy, wifi_rssi, wifi_ssid, batch_name, notes
                            FROM legacy_db.registered_devices;
                        """)
                    conn_dst.commit()
                    cur_dst.execute("DETACH DATABASE legacy_db;")
        except Exception as e:
            logging.getLogger("AlfaEnergyFlasher").warning(f"Database auto-migration note: {e}")

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def init_database(self) -> None:
        with self._lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS production_records (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        transaction_id TEXT UNIQUE NOT NULL,
                        start_time TEXT NOT NULL,
                        end_time TEXT,
                        product_category TEXT NOT NULL,
                        firmware_name TEXT NOT NULL,
                        firmware_version TEXT,
                        firmware_hash TEXT NOT NULL,
                        target_chip TEXT NOT NULL,
                        serial_port TEXT NOT NULL,
                        baudrate INTEGER NOT NULL,
                        mac_address TEXT,
                        batch_name TEXT,
                        equipment_id TEXT,
                        result TEXT NOT NULL,
                        verification_status TEXT DEFAULT 'UNVERIFIED',
                        duration_seconds REAL DEFAULT 0.0,
                        error_message TEXT,
                        app_version TEXT NOT NULL,
                        operator_notes TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_prod_result ON production_records (result);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_prod_product ON production_records (product_category);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_prod_created ON production_records (created_at);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_prod_mac ON production_records (mac_address);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_prod_batch ON production_records (batch_name);")

                # Registered Devices Fleet Roster for Live Monitoring & MQTT Control
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS registered_devices (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        mac_address TEXT UNIQUE NOT NULL,
                        device_name TEXT NOT NULL,
                        product_category TEXT NOT NULL,
                        flashed_at TEXT NOT NULL,
                        last_seen_at TEXT,
                        ip_address TEXT,
                        status TEXT DEFAULT 'OFFLINE',
                        power_state TEXT DEFAULT 'UNKNOWN',
                        voltage REAL DEFAULT 0.0,
                        current REAL DEFAULT 0.0,
                        power REAL DEFAULT 0.0,
                        energy REAL DEFAULT 0.0,
                        wifi_rssi INTEGER,
                        wifi_ssid TEXT,
                        batch_name TEXT,
                        notes TEXT
                    );
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_dev_mac ON registered_devices (mac_address);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_dev_status ON registered_devices (status);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_dev_category ON registered_devices (product_category);")

                # Offline Telemetry Buffer & Historical Replay Ingestion Table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS device_telemetry_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        mac_address TEXT NOT NULL,
                        recorded_at TEXT NOT NULL,
                        voltage REAL,
                        current REAL,
                        power REAL,
                        power_factor REAL,
                        energy_total REAL,
                        is_offline_buffer INTEGER DEFAULT 1,
                        seq_num INTEGER,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(mac_address, recorded_at)
                    );
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_hist_mac ON device_telemetry_history (mac_address);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_hist_time ON device_telemetry_history (recorded_at);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_hist_buffer ON device_telemetry_history (is_offline_buffer);")

                # System Event & Incident Notification Audit Logs
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS system_event_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        mac_address TEXT NOT NULL,
                        device_name TEXT NOT NULL,
                        location_desc TEXT,
                        event_type TEXT NOT NULL,
                        downtime_sec INTEGER DEFAULT 0,
                        records_count INTEGER DEFAULT 0,
                        message TEXT NOT NULL
                    );
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_evt_time ON system_event_logs (timestamp);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_evt_mac ON system_event_logs (mac_address);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_evt_type ON system_event_logs (event_type);")
                conn.commit()

                # Approach A: Auto-deduplicate registered devices by 6-digit MAC suffix on startup
                self._deduplicate_registered_devices_internal(conn)

    def insert_record(self, record: ProductionRecord) -> int:
        with self._lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO production_records (
                        transaction_id, start_time, end_time, product_category,
                        firmware_name, firmware_version, firmware_hash, target_chip,
                        serial_port, baudrate, mac_address, batch_name,
                        equipment_id, result, verification_status, duration_seconds,
                        error_message, app_version, operator_notes, created_at
                    ) VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                    )
                """, (
                    record.transaction_id,
                    record.start_time,
                    record.end_time,
                    record.product_category,
                    record.firmware_name,
                    record.firmware_version,
                    record.firmware_hash,
                    record.target_chip,
                    record.serial_port,
                    record.baudrate,
                    record.mac_address,
                    record.batch_name,
                    record.equipment_id,
                    record.result,
                    record.verification_status,
                    record.duration_seconds,
                    record.error_message,
                    record.app_version,
                    record.operator_notes,
                    record.created_at
                ))
                conn.commit()
                record.id = cursor.lastrowid
                return record.id

    def update_record(self, record: ProductionRecord) -> bool:
        with self._lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE production_records SET
                        end_time = ?,
                        result = ?,
                        mac_address = ?,
                        verification_status = ?,
                        duration_seconds = ?,
                        error_message = ?,
                        operator_notes = ?
                    WHERE transaction_id = ?
                """, (
                    record.end_time,
                    record.result,
                    record.mac_address,
                    record.verification_status,
                    record.duration_seconds,
                    record.error_message,
                    record.operator_notes,
                    record.transaction_id
                ))
                conn.commit()
                return cursor.rowcount > 0

    def get_records(
        self,
        product: Optional[str] = None,
        result: Optional[str] = None,
        search_query: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 500,
        offset: int = 0
    ) -> List[ProductionRecord]:
        query = "SELECT * FROM production_records WHERE 1=1"
        params: List[Any] = []

        if product and product != "ALL":
            query += " AND product_category = ?"
            params.append(product)

        if result and result != "ALL":
            query += " AND result = ?"
            params.append(result)

        if search_query:
            q = f"%{search_query.strip()}%"
            query += " AND (transaction_id LIKE ? OR mac_address LIKE ? OR serial_port LIKE ? OR batch_name LIKE ? OR target_chip LIKE ?)"
            params.extend([q, q, q, q, q])

        if start_date:
            query += " AND created_at >= ?"
            params.append(f"{start_date} 00:00:00")

        if end_date:
            query += " AND created_at <= ?"
            params.append(f"{end_date} 23:59:59")

        query += " ORDER BY id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            if not rows:
                return []
            col_names = [col[0] for col in cursor.description]
            return [ProductionRecord.from_row(tuple(r), col_names) for r in rows]

    def get_statistics(self, batch_name: Optional[str] = None) -> Dict[str, Any]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT COUNT(*) as total, " \
                    "SUM(CASE WHEN result = 'PASS' THEN 1 ELSE 0 END) as passed, " \
                    "SUM(CASE WHEN result = 'FAIL' THEN 1 ELSE 0 END) as failed, " \
                    "SUM(CASE WHEN result = 'CANCELLED' THEN 1 ELSE 0 END) as cancelled, " \
                    "AVG(CASE WHEN result = 'PASS' THEN duration_seconds ELSE NULL END) as avg_duration " \
                    "FROM production_records"
            params: List[Any] = []
            if batch_name:
                query += " WHERE batch_name = ?"
                params.append(batch_name)
            cursor.execute(query, params)
            row = cursor.fetchone()
            total = row["total"] or 0
            passed = row["passed"] or 0
            failed = row["failed"] or 0
            cancelled = row["cancelled"] or 0
            avg_duration = round(row["avg_duration"] or 0.0, 1)
            pass_rate = round((passed / total * 100), 1) if total > 0 else 0.0

            return {
                "total": total,
                "passed": passed,
                "failed": failed,
                "cancelled": cancelled,
                "pass_rate": pass_rate,
                "avg_duration": avg_duration
            }

    def get_total_passed_count(self) -> int:
        """Returns total historical successful (PASS) flashing records."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM production_records WHERE result = 'PASS'")
            row = cursor.fetchone()
            return row[0] if row else 0

    def get_today_passed_count(self) -> int:
        """Returns total successful (PASS) flashing records created today (local date)."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM production_records WHERE result = 'PASS' AND date(created_at) = date('now', 'localtime')")
            row = cursor.fetchone()
            return row[0] if row else 0

    def get_model_passed_counts(self) -> Dict[str, int]:
        """Returns counts of passed records grouped by product category."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT product_category, COUNT(*)
                FROM production_records
                WHERE result = 'PASS'
                GROUP BY product_category
                ORDER BY COUNT(*) DESC
            """)
            rows = cursor.fetchall()
            return {r[0]: r[1] for r in rows} if rows else {}

    def get_recent_passed_records(self, limit: int = 10) -> List[ProductionRecord]:
        """Returns the most recent passed production records."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM production_records
                WHERE result = 'PASS' AND mac_address IS NOT NULL
                ORDER BY id DESC
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            if not rows:
                return []
            cols = [desc[0] for desc in cursor.description]
            return [ProductionRecord.from_row(tuple(r), cols) for r in rows]

    def get_batches(self) -> List[str]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT batch_name FROM production_records WHERE batch_name IS NOT NULL AND batch_name != '' ORDER BY batch_name DESC")
            rows = cursor.fetchall()
            return [r[0] for r in rows]

    # =========================================================================
    # Registered Devices Fleet Management & Live MQTT Roster
    # =========================================================================

    def _deduplicate_registered_devices_internal(self, conn: sqlite3.Connection) -> int:
        """
        Internal engine to merge duplicate rows sharing the same 6-digit MAC suffix.
        Preserves canonical flashed MAC, active IP, custom notes, and latest telemetry,
        purging redundant duplicate rows so only 1 row exists per physical device.
        """
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM registered_devices")
        rows = cursor.fetchall()
        if not rows:
            return 0

        cols = [desc[0] for desc in cursor.description]
        devices = [RegisteredDevice.from_row(tuple(r), cols) for r in rows]

        from collections import defaultdict
        grouped = defaultdict(list)
        for d in devices:
            clean_mac = d.mac_address.replace(":", "").replace("-", "").upper()
            suffix = clean_mac[-6:] if len(clean_mac) >= 6 else clean_mac
            grouped[suffix].append(d)

        purged = 0
        cursor.execute("SELECT DISTINCT mac_address FROM production_records WHERE mac_address IS NOT NULL")
        flashed_macs = set(r[0].upper().strip() for r in cursor.fetchall())

        for suffix, group in grouped.items():
            if len(group) <= 1:
                continue

            # Prioritize canonical record:
            # 1. Physically flashed hardware MAC recorded in production_records
            # 2. Full 12-hex MAC over temporary NET: prefix
            # 3. Flashed timestamp populated
            # 4. Valid IP address detected
            def sort_priority(dev: RegisteredDevice):
                is_flashed = 1 if dev.mac_address.upper() in flashed_macs else 0
                is_not_net = 0 if dev.mac_address.upper().startswith("NET:") else 1
                has_flashed_at = 1 if dev.flashed_at else 0
                has_ip = 1 if dev.ip_address else 0
                return (is_flashed, is_not_net, has_flashed_at, has_ip)

            group.sort(key=sort_priority, reverse=True)
            canonical = group[0]
            duplicates = group[1:]

            best_ip = canonical.ip_address
            best_notes = canonical.notes
            best_batch = canonical.batch_name
            best_power = canonical.power
            best_voltage = canonical.voltage
            best_current = canonical.current
            best_energy = canonical.energy
            best_status = canonical.status
            best_last_seen = canonical.last_seen_at
            best_pstate = canonical.power_state

            for dup in duplicates:
                if not best_ip and dup.ip_address:
                    best_ip = dup.ip_address
                if (not best_notes or best_notes.startswith("Active AlfaEnergy") or best_notes.startswith("Flashed by")) and dup.notes and not dup.notes.startswith("Active") and not dup.notes.startswith("Flashed"):
                    best_notes = dup.notes
                if not best_batch and dup.batch_name:
                    best_batch = dup.batch_name
                if (best_power == 0.0 or best_power is None) and dup.power and dup.power > 0:
                    best_power = dup.power
                if (best_voltage == 0.0 or best_voltage is None) and dup.voltage and dup.voltage > 0:
                    best_voltage = dup.voltage
                if (best_current == 0.0 or best_current is None) and dup.current and dup.current > 0:
                    best_current = dup.current
                if (best_energy == 0.0 or best_energy is None) and dup.energy and dup.energy > 0:
                    best_energy = dup.energy
                if best_status != "ONLINE" and dup.status == "ONLINE":
                    best_status = "ONLINE"
                if not best_last_seen or (dup.last_seen_at and dup.last_seen_at > best_last_seen):
                    best_last_seen = dup.last_seen_at
                if (best_pstate in ("UNKNOWN", None, "")) and dup.power_state and dup.power_state != "UNKNOWN":
                    best_pstate = dup.power_state

                # Repoint telemetry history to canonical MAC
                cursor.execute("""
                    UPDATE OR IGNORE device_telemetry_history
                    SET mac_address = ?
                    WHERE mac_address = ?
                """, (canonical.mac_address, dup.mac_address))

                cursor.execute("DELETE FROM registered_devices WHERE id = ?", (dup.id,))
                purged += 1

            cursor.execute("""
                UPDATE registered_devices
                SET ip_address = ?,
                    notes = ?,
                    batch_name = ?,
                    power = ?,
                    voltage = ?,
                    current = ?,
                    energy = ?,
                    status = ?,
                    last_seen_at = ?,
                    power_state = ?
                WHERE id = ?
            """, (
                best_ip, best_notes, best_batch, best_power,
                best_voltage, best_current, best_energy, best_status,
                best_last_seen, best_pstate, canonical.id
            ))

        conn.commit()
        return purged

    def deduplicate_registered_devices(self) -> int:
        """Thread-safe entry point to merge duplicate device rows by suffix."""
        with self._lock:
            with self.get_connection() as conn:
                return self._deduplicate_registered_devices_internal(conn)

    def register_device(self, device: RegisteredDevice) -> int:
        """
        Registers or smart-merges a device into the live fleet roster.
        Guarantees only ONE row per physical 6-digit MAC suffix (Approach A).
        """
        clean_mac = device.mac_address.upper().strip()
        clean_suffix = clean_mac.replace(":", "").replace("-", "")[-6:]

        with self._lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Approach A: Find any existing record with identical 6-digit suffix
                cursor.execute("""
                    SELECT id, mac_address, ip_address, notes, batch_name, status,
                           voltage, current, power, energy, power_state, last_seen_at, flashed_at
                    FROM registered_devices
                    WHERE mac_address = ?
                       OR REPLACE(REPLACE(mac_address, ':', ''), '-', '') LIKE '%' || ?
                       OR device_name LIKE '%' || ?
                    ORDER BY CASE WHEN mac_address = ? THEN 0 ELSE 1 END, id ASC
                """, (clean_mac, clean_suffix, clean_suffix, clean_mac))
                existing = cursor.fetchall()

                if existing:
                    target_row = existing[0]
                    target_id = target_row["id"]

                    # Keep canonical hardware MAC if new device has real MAC (not temporary NET:)
                    target_mac = clean_mac if not clean_mac.startswith("NET:") else target_row["mac_address"]
                    final_ip = device.ip_address or target_row["ip_address"]

                    old_notes = target_row["notes"]
                    is_new_generic = (not device.notes or device.notes.startswith("Active AlfaEnergy") or device.notes.startswith("Flashed by"))
                    has_custom_old = (old_notes and not old_notes.startswith("Active") and not old_notes.startswith("Flashed"))
                    final_notes = old_notes if (is_new_generic and has_custom_old) else (device.notes or old_notes)

                    final_batch = device.batch_name or target_row["batch_name"]
                    final_status = device.status if device.status == "ONLINE" else (target_row["status"] or device.status)
                    final_flashed_at = device.flashed_at or target_row["flashed_at"]

                    cursor.execute("""
                        UPDATE registered_devices
                        SET mac_address = ?,
                            device_name = ?,
                            product_category = ?,
                            flashed_at = COALESCE(NULLIF(?, ''), flashed_at),
                            last_seen_at = COALESCE(?, last_seen_at),
                            ip_address = ?,
                            status = ?,
                            batch_name = ?,
                            notes = ?
                        WHERE id = ?
                    """, (
                        target_mac,
                        device.device_name,
                        device.product_category,
                        final_flashed_at,
                        device.last_seen_at,
                        final_ip,
                        final_status,
                        final_batch,
                        final_notes,
                        target_id
                    ))

                    # Purge any extra duplicate records sharing this 6-digit suffix
                    if len(existing) > 1:
                        for extra in existing[1:]:
                            cursor.execute("""
                                UPDATE OR IGNORE device_telemetry_history
                                SET mac_address = ?
                                WHERE mac_address = ?
                            """, (target_mac, extra["mac_address"]))
                            cursor.execute("DELETE FROM registered_devices WHERE id = ?", (extra["id"],))

                    conn.commit()
                    return target_id
                else:
                    cursor.execute("""
                        INSERT INTO registered_devices (
                            mac_address, device_name, product_category, flashed_at,
                            last_seen_at, ip_address, status, power_state,
                            voltage, current, power, energy, wifi_rssi, wifi_ssid,
                            batch_name, notes
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        clean_mac,
                        device.device_name,
                        device.product_category,
                        device.flashed_at,
                        device.last_seen_at,
                        device.ip_address,
                        device.status,
                        device.power_state,
                        device.voltage,
                        device.current,
                        device.power,
                        device.energy,
                        device.wifi_rssi,
                        device.wifi_ssid,
                        device.batch_name,
                        device.notes
                    ))
                    conn.commit()
                    return cursor.lastrowid or 0

    def get_registered_device(self, mac_address: str) -> Optional[RegisteredDevice]:
        """Retrieves a single registered device by full MAC address or 6-char suffix."""
        clean_mac = mac_address.upper().strip()
        clean_suffix = clean_mac.replace(":", "").replace("-", "")[-6:]
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM registered_devices
                WHERE mac_address = ?
                   OR REPLACE(REPLACE(mac_address, ':', ''), '-', '') LIKE '%' || ?
                   OR device_name LIKE '%' || ?
                ORDER BY CASE WHEN mac_address = ? THEN 0 ELSE 1 END, id DESC
                LIMIT 1
            """, (clean_mac, clean_suffix, clean_suffix, clean_mac))
            row = cursor.fetchone()
            if row:
                cols = [desc[0] for desc in cursor.description]
                return RegisteredDevice.from_row(tuple(row), cols)
        return None

    def get_all_registered_devices(
        self,
        filter_status: Optional[str] = None,
        filter_category: Optional[str] = None,
        search: Optional[str] = None
    ) -> List[RegisteredDevice]:
        """Retrieves all registered devices, guaranteed distinct by 6-character suffix."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM registered_devices WHERE 1=1"
            params: List[Any] = []

            if filter_status and filter_status != "ALL":
                query += " AND status = ?"
                params.append(filter_status)

            if filter_category and filter_category != "ALL":
                query += " AND product_category = ?"
                params.append(filter_category)

            if search:
                query += " AND (device_name LIKE ? OR mac_address LIKE ? OR ip_address LIKE ? OR notes LIKE ?)"
                term = f"%{search}%"
                params.extend([term, term, term, term])

            query += " ORDER BY CASE WHEN status = 'ONLINE' THEN 0 ELSE 1 END, id DESC"
            cursor.execute(query, params)
            rows = cursor.fetchall()
            if not rows:
                return []
            cols = [desc[0] for desc in cursor.description]

            # Approach A: Deduplicate by 6-digit suffix when returning
            seen_suffixes = set()
            deduped = []
            for r in rows:
                dev = RegisteredDevice.from_row(tuple(r), cols)
                clean_mac = dev.mac_address.replace(":", "").replace("-", "").upper()
                suffix = clean_mac[-6:] if len(clean_mac) >= 6 else clean_mac
                if suffix not in seen_suffixes:
                    seen_suffixes.add(suffix)
                    deduped.append(dev)
            return deduped

    def update_device_telemetry(
        self,
        mac_address: str,
        ip: Optional[str] = None,
        voltage: Optional[float] = None,
        current: Optional[float] = None,
        power: Optional[float] = None,
        energy: Optional[float] = None,
        wifi_rssi: Optional[int] = None,
        wifi_ssid: Optional[str] = None,
        power_state: Optional[str] = None,
        status: str = "ONLINE"
    ) -> bool:
        """Atomically updates live telemetry and status from MQTT message payload."""
        from datetime import datetime
        clean_mac = mac_address.upper().strip()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        clean_ip = str(ip).strip() if (ip and str(ip).strip() and str(ip).strip() not in ("-", "None", "")) else None

        with self._lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE registered_devices
                    SET last_seen_at = ?,
                        status = ?,
                        ip_address = COALESCE(?, ip_address),
                        voltage = COALESCE(?, voltage),
                        current = COALESCE(?, current),
                        power = COALESCE(?, power),
                        energy = COALESCE(?, energy),
                        wifi_rssi = COALESCE(?, wifi_rssi),
                        wifi_ssid = COALESCE(?, wifi_ssid),
                        power_state = COALESCE(?, power_state)
                    WHERE mac_address = ?
                """, (
                    now_str,
                    status,
                    clean_ip,
                    voltage,
                    current,
                    power,
                    energy,
                    wifi_rssi,
                    wifi_ssid,
                    power_state,
                    clean_mac
                ))
                conn.commit()
                return cursor.rowcount > 0

    def update_device_status(self, mac_address: str, status: str) -> bool:
        """Updates device online/offline status (e.g. from MQTT LWT topic)."""
        from datetime import datetime
        clean_mac = mac_address.upper().strip()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with self._lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE registered_devices
                    SET status = ?, last_seen_at = ?
                    WHERE mac_address = ?
                """, (status, now_str, clean_mac))
                conn.commit()
                return cursor.rowcount > 0

    def update_device_notes(self, mac_address: str, notes: Optional[str]) -> bool:
        """Updates user custom notes / location alias for a device."""
        clean_mac = mac_address.upper().strip()
        with self._lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE registered_devices
                    SET notes = ?
                    WHERE mac_address = ?
                """, (notes, clean_mac))
                conn.commit()
                return cursor.rowcount > 0

    def delete_registered_device(self, mac_address: str) -> bool:
        """Removes a device from the fleet monitoring roster."""
        clean_mac = mac_address.upper().strip()
        with self._lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM registered_devices WHERE mac_address = ?", (clean_mac,))
                conn.commit()
                return cursor.rowcount > 0

    def insert_telemetry_history(
        self,
        mac_address: str,
        recorded_at: str,
        voltage: Optional[float] = None,
        current: Optional[float] = None,
        power: Optional[float] = None,
        power_factor: Optional[float] = None,
        energy_total: Optional[float] = None,
        is_offline_buffer: int = 1,
        seq_num: Optional[int] = None
    ) -> bool:
        """
        Inserts offline buffered telemetry or historical telemetry points replayed from firmware.
        Uses INSERT OR REPLACE on UNIQUE(mac_address, recorded_at) to ensure idempotent ingestion.
        """
        clean_mac = mac_address.upper().strip()
        with self._lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO device_telemetry_history (
                        mac_address, recorded_at, voltage, current, power,
                        power_factor, energy_total, is_offline_buffer, seq_num
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    clean_mac,
                    recorded_at,
                    voltage,
                    current,
                    power,
                    power_factor,
                    energy_total,
                    is_offline_buffer,
                    seq_num
                ))
                conn.commit()
                return cursor.rowcount > 0

    def get_telemetry_history(
        self,
        mac_address: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Retrieves historical telemetry entries for a given MAC address ordered by timestamp descending."""
        clean_mac = mac_address.upper().strip()
        with self._lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, mac_address, recorded_at, voltage, current, power,
                           power_factor, energy_total, is_offline_buffer, seq_num, created_at
                    FROM device_telemetry_history
                    WHERE mac_address = ?
                    ORDER BY recorded_at DESC
                    LIMIT ?
                """, (clean_mac, limit))
                rows = cursor.fetchall()
                return [dict(row) for row in rows]

    def get_telemetry_history_count(self, mac_address: Optional[str] = None) -> int:
        """Returns the total number of replayed/historical telemetry records."""
        with self._lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                if mac_address:
                    cursor.execute("SELECT COUNT(*) FROM device_telemetry_history WHERE mac_address = ?", (mac_address.upper().strip(),))
                else:
                    cursor.execute("SELECT COUNT(*) FROM device_telemetry_history")
                row = cursor.fetchone()
                return row[0] if row else 0

    # =========================================================================
    # System Event & Incident Notification Audit Logs
    # =========================================================================

    def insert_system_event(
        self,
        mac_address: str,
        device_name: str,
        location_desc: Optional[str],
        event_type: str,
        downtime_sec: int = 0,
        records_count: int = 0,
        message: str = ""
    ) -> int:
        """Records a connection, restore, or sync incident notification into the database."""
        from datetime import datetime
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        clean_mac = mac_address.upper().strip()

        with self._lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO system_event_logs (
                        timestamp, mac_address, device_name, location_desc,
                        event_type, downtime_sec, records_count, message
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    now_str,
                    clean_mac,
                    device_name,
                    location_desc or "",
                    event_type,
                    downtime_sec,
                    records_count,
                    message
                ))
                conn.commit()
                return cursor.lastrowid or 0

    def get_system_events(
        self,
        limit: int = 200,
        event_type: Optional[str] = None,
        search: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retrieves system event audit logs ordered by timestamp descending."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM system_event_logs WHERE 1=1"
            params: List[Any] = []

            if event_type and event_type != "ALL":
                query += " AND event_type = ?"
                params.append(event_type)

            if search:
                query += " AND (device_name LIKE ? OR location_desc LIKE ? OR message LIKE ? OR mac_address LIKE ?)"
                term = f"%{search}%"
                params.extend([term, term, term, term])

            query += " ORDER BY id DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def clear_system_events(self) -> bool:
        """Clears all system event history logs."""
        with self._lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM system_event_logs")
                conn.commit()
                return True

    def get_system_events_count(self) -> int:
        """Returns total count of logged system events."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM system_event_logs")
            row = cursor.fetchone()
            return row[0] if row else 0

# Global database manager singleton
db_manager = DatabaseManager()


