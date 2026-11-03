"""
SpartaFlash - Desktop Application Entry Point.
Developer: Rohidfkra777
GitHub: https://github.com/rohidfkra777
"""

import sys
import os
from pathlib import Path

# Add project root to sys.path so modules resolve cleanly when running directly or packaged
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt

from src.config.constants import APP_NAME, APP_VERSION, APP_ICON_PATH
from src.utils.logger import setup_logger

from src.database.db_manager import db_manager
from src.ui.main_window import MainWindow

def main():
    
    # Station entry point

    # If invoked for esptool CLI delegation (e.g. from flasher subprocess in frozen mode)
    if len(sys.argv) > 2 and sys.argv[1] == "-m" and sys.argv[2] == "esptool":
        import esptool
        try:
            esptool.main(sys.argv[3:])
            sys.exit(0)
        except SystemExit as e:
            sys.exit(e.code)
        except Exception as e:
            sys.stderr.write(f"esptool error: {e}\n")
            sys.exit(1)

    # Setup logger
    logger = setup_logger()
    logger.info(f"Starting {APP_NAME} v{APP_VERSION}...")

    # Initialize Database
    try:
        db_manager.init_database()
        logger.info("Production database initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")

    # Initialize Qt Application
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("Rohidfkra777")
    app.setOrganizationDomain("github.com/rohidfkra777")
    app.setWindowIcon(QIcon(str(APP_ICON_PATH)))

    # Station Security Login Gate
    from src.ui.components.login_dialog import LoginDialog
    login_dialog = LoginDialog()
    if login_dialog.exec() != LoginDialog.Accepted:
        logger.info("Station login cancelled or rejected. Exiting application.")
        sys.exit(0)

    window = MainWindow()
    window.show()

    logger.info("GUI window displayed. Entering Qt event loop.")
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
