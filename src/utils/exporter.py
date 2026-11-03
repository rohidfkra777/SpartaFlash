"""
SpartaFlash - Export Utility (CSV and Production Reports).
Developer: Rohidfkra777
"""

import csv
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from src.config.constants import APP_NAME, APP_VERSION, DEVELOPER_NAME, DEVELOPER_GITHUB, REPORTS_DIR
from src.database.models import ProductionRecord

def export_records_to_csv(records: List[ProductionRecord], output_path: Optional[Path] = None) -> Path:
    """Exports a list of production records to a professional CSV report."""
    if output_path is None:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = REPORTS_DIR / f"Production_Report_{timestamp}.csv"

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        
        # Metadata Header
        writer.writerow([f"# {APP_NAME} Production Log Report"])
        writer.writerow([f"# Generated At: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"])
        writer.writerow([f"# Application Version: {APP_VERSION}"])
        writer.writerow([f"# Developed by: {DEVELOPER_NAME} ({DEVELOPER_GITHUB})"])
        writer.writerow([f"# Total Records: {len(records)}"])
        writer.writerow([])  # Blank row

        # Data Columns
        headers = [
            "Transaction ID",
            "Start Time",
            "End Time",
            "Product",
            "Firmware Name",
            "Firmware Version",
            "SHA-256 Hash",
            "Target Chip",
            "Serial Port",
            "Baudrate",
            "MAC Address",
            "Batch Name",
            "Result",
            "Verification",
            "Duration (s)",
            "App Version",
            "Error Message",
            "Operator Notes"
        ]
        writer.writerow(headers)

        for r in records:
            writer.writerow([
                r.transaction_id,
                r.start_time,
                r.end_time or "",
                r.product_category,
                r.firmware_name,
                r.firmware_version or "-",
                r.firmware_hash,
                r.target_chip,
                r.serial_port,
                r.baudrate,
                r.mac_address or "N/A",
                r.batch_name or "-",
                r.result,
                r.verification_status,
                f"{r.duration_seconds:.2f}",
                r.app_version,
                r.error_message or "",
                r.operator_notes or ""
            ])

    return output_path

def generate_batch_summary_text(stats: Dict[str, Any], batch_name: Optional[str] = None) -> str:
    """Generates a text summary of production stats."""
    batch_display = batch_name if batch_name else "All Batches"
    lines = [
        f"==================================================",
        f"        {APP_NAME} - BATCH SUMMARY REPORT         ",
        f"==================================================",
        f"Batch Identifier : {batch_display}",
        f"Generated At     : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Software Version : {APP_VERSION}",
        f"Developer        : {DEVELOPER_NAME} ({DEVELOPER_GITHUB})",
        f"--------------------------------------------------",
        f"Total Units Flashed : {stats.get('total', 0)}",
        f"PASS (Success)      : {stats.get('passed', 0)}",
        f"FAIL (Failed)       : {stats.get('failed', 0)}",
        f"CANCELLED           : {stats.get('cancelled', 0)}",
        f"Pass Rate           : {stats.get('pass_rate', 0.0)}%",
        f"Average Duration    : {stats.get('avg_duration', 0.0)}s",
        f"==================================================",
    ]
    return "\n".join(lines)
