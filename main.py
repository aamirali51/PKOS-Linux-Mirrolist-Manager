#!/usr/bin/env python3
"""
PKOS Linux Mirrorlist Manager
A modern GUI application for managing Arch Linux mirror lists

Developer: Aamir Abdullah
Email: aamirabdullah33@gmail.com
License: Open Source
Version: 2.0
"""
import sys
from PyQt6.QtWidgets import QApplication
from src.ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("PKOS Linux Mirrorlist Manager")
    app.setApplicationVersion("2.0")
    app.setOrganizationName("PKOS Linux")
    app.setOrganizationDomain("pkos-linux.org")
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
