from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QMessageBox, QProgressDialog,
                             QTextEdit, QDialogButtonBox, QCheckBox, QSpinBox,
                             QGroupBox, QFormLayout, QScrollArea, QWidget, QFrame)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QPixmap, QIcon, QColor
import subprocess
import threading


class PasswordDialog(QDialog):
    def __init__(self, title="Authentication Required", message="Enter your password:"):
        super().__init__()
        self.setWindowTitle(title)
        self.setModal(True)
        self.setFixedSize(400, 200)
        
        layout = QVBoxLayout()
        
        # Icon and message
        msg_layout = QHBoxLayout()
        
        # Add lock icon (if available)
        icon_label = QLabel("🔒")
        icon_label.setFont(QFont("Arial", 24))
        msg_layout.addWidget(icon_label)
        
        message_label = QLabel(message)
        message_label.setWordWrap(True)
        msg_layout.addWidget(message_label)
        
        layout.addLayout(msg_layout)
        
        # Password input
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Password")
        self.password_input.returnPressed.connect(self.accept)
        layout.addWidget(self.password_input)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        self.ok_button.setDefault(True)
        button_layout.addWidget(self.ok_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
        # Focus on password input
        self.password_input.setFocus()
    
    def get_password(self):
        return self.password_input.text()


class BackupConfirmDialog(QDialog):
    def __init__(self, existing_backups=None):
        super().__init__()
        self.setWindowTitle("Backup Confirmation")
        self.setModal(True)
        self.setFixedSize(500, 400)
        
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("⚠️ Safety Check - Backup Confirmation")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # Warning message
        warning = QLabel(
            "You are about to modify the system mirrorlist file.\n"
            "This operation requires root privileges and will affect your package manager."
        )
        warning.setWordWrap(True)
        warning.setStyleSheet("color: #d32f2f; font-weight: bold;")
        layout.addWidget(warning)
        
        # Backup options
        backup_group = QGroupBox("Backup Options")
        backup_layout = QVBoxLayout()
        
        self.create_backup_cb = QCheckBox("Create backup before applying changes")
        self.create_backup_cb.setChecked(True)
        backup_layout.addWidget(self.create_backup_cb)
        
        self.verify_backup_cb = QCheckBox("Verify backup was created successfully")
        self.verify_backup_cb.setChecked(True)
        backup_layout.addWidget(self.verify_backup_cb)
        
        backup_group.setLayout(backup_layout)
        layout.addWidget(backup_group)
        
        # Existing backups
        if existing_backups:
            backups_group = QGroupBox("Existing Backups Found")
            backups_layout = QVBoxLayout()
            
            backups_text = QTextEdit()
            backups_text.setMaximumHeight(100)
            backups_text.setPlainText("\n".join(existing_backups))
            backups_text.setReadOnly(True)
            backups_layout.addWidget(backups_text)
            
            backups_group.setLayout(backups_layout)
            layout.addWidget(backups_group)
        
        # Mirror count info
        self.mirror_count_label = QLabel()
        layout.addWidget(self.mirror_count_label)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        # Style the OK button
        ok_button = button_box.button(QDialogButtonBox.StandardButton.Ok)
        ok_button.setText("Proceed with Backup & Apply")
        ok_button.setStyleSheet("QPushButton { background-color: #4caf50; color: white; font-weight: bold; }")
        
        layout.addWidget(button_box)
        self.setLayout(layout)
    
    def set_mirror_count(self, count):
        self.mirror_count_label.setText(f"📊 Selected mirrors: {count}")
    
    def should_create_backup(self):
        return self.create_backup_cb.isChecked()
    
    def should_verify_backup(self):
        return self.verify_backup_cb.isChecked()


class SpeedTestProgressDialog(QDialog):
    cancel_requested = pyqtSignal()  # Signal to request cancellation
    
    def __init__(self, total_mirrors):
        super().__init__()
        self.setWindowTitle("Testing Mirror Speeds")
        self.setModal(True)
        self.setFixedSize(600, 400)
        
        self.total_mirrors = total_mirrors
        self.current_mirror = 0
        self.is_cancelled = False
        
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("⚡ Speed Testing in Progress")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # Info note
        info_note = QLabel("Note: Some mirrors may fail due to geographic restrictions, rate limiting, or temporary issues. This is normal and expected.")
        info_note.setWordWrap(True)
        info_note.setStyleSheet("color: #666; font-size: 11px; margin: 5px 0;")
        layout.addWidget(info_note)
        
        # Overall progress
        self.overall_label = QLabel(f"Testing mirror 0 of {total_mirrors}")
        layout.addWidget(self.overall_label)
        
        from PyQt6.QtWidgets import QProgressBar
        self.overall_progress = QProgressBar()
        self.overall_progress.setMaximum(total_mirrors)
        self.overall_progress.setValue(0)
        layout.addWidget(self.overall_progress)
        
        # Current mirror info
        self.current_mirror_label = QLabel("Preparing...")
        self.current_mirror_label.setWordWrap(True)
        layout.addWidget(self.current_mirror_label)
        
        # Results area
        results_group = QGroupBox("Test Results")
        results_layout = QVBoxLayout()
        
        self.results_text = QTextEdit()
        self.results_text.setMaximumHeight(150)
        self.results_text.setReadOnly(True)
        results_layout.addWidget(self.results_text)
        
        results_group.setLayout(results_layout)
        layout.addWidget(results_group)
        
        # Cancel button
        self.cancel_button = QPushButton("Cancel Testing")
        self.cancel_button.clicked.connect(self.cancel_testing)
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                font-weight: bold;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        layout.addWidget(self.cancel_button)
        
        self.setLayout(layout)
        
        # Track results
        self.results = []
    
    def cancel_testing(self):
        """Handle cancel button click"""
        if not self.is_cancelled:
            self.is_cancelled = True
            self.cancel_button.setText("Cancelling...")
            self.cancel_button.setEnabled(False)
            self.current_mirror_label.setText("Cancelling speed test...")
            self.cancel_requested.emit()
            
            # Update the title to show cancellation
            title_widgets = self.findChildren(QLabel)
            for widget in title_widgets:
                if "Speed Testing" in widget.text():
                    widget.setText("⚠️ Cancelling Speed Test...")
                    widget.setStyleSheet("color: #f44336; font-weight: bold;")
                    break
    
    def update_progress(self, mirror_index, mirror_url, result=None):
        self.current_mirror = mirror_index + 1
        self.overall_progress.setValue(self.current_mirror)
        self.overall_label.setText(f"Testing mirror {self.current_mirror} of {self.total_mirrors}")
        
        # Update current mirror (clean up URL for display)
        display_url = mirror_url.replace('$repo', 'core').replace('$arch', 'x86_64')
        if not display_url.endswith('core.db'):
            display_url = display_url.rstrip('/') + '/core.db'
        self.current_mirror_label.setText(f"Testing: {display_url}")
        
        # Add result if provided
        if result is not None:
            # Clean up the URL for display (remove template variables)
            display_url = mirror_url.replace('$repo', 'core').replace('$arch', 'x86_64')
            if not display_url.endswith('core.db'):
                display_url = display_url.rstrip('/') + '/core.db'
            
            if isinstance(result, (int, float)) and result > 0:
                # Format speed nicely
                if result > 1000000:  # > 1MB/s
                    speed_text = f"{result/1000000:.1f} MB/s"
                elif result > 1000:   # > 1KB/s
                    speed_text = f"{result/1000:.1f} KB/s"
                else:
                    speed_text = f"{result:.0f} B/s"
                
                result_text = f"✅ {speed_text} - {display_url}"
                self.results.append((mirror_index, result))
            else:
                result_text = f"❌ Failed - {display_url}"
                self.results.append((mirror_index, 0))
            
            self.results_text.append(result_text)
            
            # Auto-scroll to bottom
            scrollbar = self.results_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
    
    def is_completed(self):
        return self.current_mirror >= self.total_mirrors


class MirrorSelectionDialog(QDialog):
    def __init__(self, sorted_results):
        super().__init__()
        self.setWindowTitle("Select Fast Mirrors")
        self.setModal(True)
        self.setFixedSize(700, 500)
        
        self.sorted_results = sorted_results
        
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("🏆 Speed Test Results - Select Your Mirrors")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # Quick selection
        quick_select_group = QGroupBox("Quick Selection")
        quick_layout = QHBoxLayout()
        
        self.top_5_btn = QPushButton("Select Top 5")
        self.top_5_btn.clicked.connect(lambda: self.select_top_n(5))
        quick_layout.addWidget(self.top_5_btn)
        
        self.top_10_btn = QPushButton("Select Top 10")
        self.top_10_btn.clicked.connect(lambda: self.select_top_n(10))
        quick_layout.addWidget(self.top_10_btn)
        
        self.select_all_btn = QPushButton("Select All")
        self.select_all_btn.clicked.connect(self.select_all)
        quick_layout.addWidget(self.select_all_btn)
        
        self.select_none_btn = QPushButton("Select None")
        self.select_none_btn.clicked.connect(self.select_none)
        quick_layout.addWidget(self.select_none_btn)
        
        quick_select_group.setLayout(quick_layout)
        layout.addWidget(quick_select_group)
        
        # Results table
        from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView
        self.table = QTableWidget()
        self.table.setStyleSheet("""
           QTableWidget {
    background-color: #ffffff;
    color: #333333;
    border: 1px solid #cccccc;
    gridline-color: #dddddd;
    selection-background-color: #e3f2fd;
}
QTableWidget::item {
    padding: 8px;
    background-color: #ffffff;
    color: #333333;
    border: none;
}
QTableWidget::item:selected {
    background-color: #cce5ff;
    color: #333333;
}
QHeaderView::section {
    background-color: #f5f5f5;
    color: #333333;
    padding: 8px;
    border: 1px solid #cccccc;
    font-weight: bold;
}

            }
        """)
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Select", "Rank", "Speed", "Country", "URL"])
        
        # Configure table
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Select
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Rank
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Speed
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Country
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)           # URL
        
        self.populate_table()
        layout.addWidget(self.table)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def populate_table(self):
        self.table.setRowCount(len(self.sorted_results))
        
        for row, (mirror_data, speed) in enumerate(self.sorted_results):
            # Checkbox
            checkbox_widget = QWidget()
            checkbox_widget.setStyleSheet("background-color: transparent;")
            checkbox_layout = QHBoxLayout(checkbox_widget)
            checkbox = QCheckBox()
            checkbox_layout.addWidget(checkbox)
            checkbox_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            checkbox_layout.setContentsMargins(0, 0, 0, 0)
            self.table.setCellWidget(row, 0, checkbox_widget)
            
            # Rank
            rank_item = QTableWidgetItem(f"#{row + 1}")
            rank_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 1, rank_item)
            
            # Speed
            if speed > 0:
                speed_text = f"{speed:.2f} B/s"
                if speed > 1000000:  # > 1MB/s
                    speed_text = f"{speed/1000000:.2f} MB/s"
                elif speed > 1000:   # > 1KB/s
                    speed_text = f"{speed/1000:.2f} KB/s"
            else:
                speed_text = "Failed"
            
            speed_item = QTableWidgetItem(speed_text)
            speed_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 2, speed_item)
            
            # Country
            country_item = QTableWidgetItem(mirror_data.get('country', 'Unknown'))
            self.table.setItem(row, 3, country_item)
            
            # URL
            url_item = QTableWidgetItem(mirror_data.get('url', ''))
            self.table.setItem(row, 4, url_item)
            
            # Color coding for speed
            if speed > 1000000:  # Fast (green)
                for col in range(1, 5):
                    item = self.table.item(row, col)
                    if item:
                        item.setBackground(QColor("#d4edda"))
            elif speed > 100000:  # Medium (yellow)
                for col in range(1, 5):
                    item = self.table.item(row, col)
                    if item:
                        item.setBackground(QColor("#fff3cd"))
            else:  # Failed (red)
                for col in range(1, 5):
                    item = self.table.item(row, col)
                    if item:
                        item.setBackground(QColor("#f8d7da"))
    
    def select_top_n(self, n):
        for row in range(self.table.rowCount()):
            checkbox_widget = self.table.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox:
                    checkbox.setChecked(row < n)
    
    def select_all(self):
        for row in range(self.table.rowCount()):
            checkbox_widget = self.table.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox:
                    checkbox.setChecked(True)
    
    def select_none(self):
        for row in range(self.table.rowCount()):
            checkbox_widget = self.table.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox:
                    checkbox.setChecked(False)
    
    def get_selected_mirrors(self):
        selected = []
        for row in range(self.table.rowCount()):
            checkbox_widget = self.table.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox and checkbox.isChecked():
                    mirror_data, speed = self.sorted_results[row]
                    selected.append(mirror_data)
        return selected


class AboutDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("About PKOS Linux Mirrorlist Manager")
        self.setModal(True)
        self.setFixedSize(500, 400)
        
        layout = QVBoxLayout()
        
        # App icon and title
        title_layout = QHBoxLayout()
        
        # App icon (using emoji)
        icon_label = QLabel("🏛️")
        icon_label.setFont(QFont("Arial", 48))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_layout.addWidget(icon_label)
        
        # Title and version
        title_info = QVBoxLayout()
        app_title = QLabel("PKOS Linux Mirrorlist Manager")
        app_title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        app_title.setStyleSheet("color: #2196F3;")
        title_info.addWidget(app_title)
        
        version_label = QLabel("Version 2.0")
        version_label.setFont(QFont("Arial", 12))
        version_label.setStyleSheet("color: #666;")
        title_info.addWidget(version_label)
        
        title_layout.addLayout(title_info)
        title_layout.addStretch()
        
        layout.addLayout(title_layout)
        
        # Description
        description = QLabel(
            "A modern GUI application for managing Arch Linux mirror lists.\n"
            "Built specifically for PKOS Linux distribution."
        )
        description.setWordWrap(True)
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        description.setStyleSheet("margin: 20px 0; font-size: 14px;")
        layout.addWidget(description)
        
        # Developer info
        dev_group = QGroupBox("Developer Information")
        dev_layout = QFormLayout()
        
        dev_name = QLabel("Aamir Abdullah")
        dev_name.setStyleSheet("font-weight: bold; color: #2196F3;")
        dev_layout.addRow("Developer:", dev_name)
        
        dev_email = QLabel("aamirabdullah33@gmail.com")
        dev_email.setStyleSheet("font-family: monospace;")
        dev_layout.addRow("Email:", dev_email)
        
        license_label = QLabel("Open Source (MIT License)")
        license_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        dev_layout.addRow("License:", license_label)
        
        dev_group.setLayout(dev_layout)
        layout.addWidget(dev_group)
        
        # PKOS Linux info
        pkos_group = QGroupBox("About PKOS Linux")
        pkos_layout = QVBoxLayout()
        
        pkos_desc = QLabel(
            "PKOS Linux is a modern Arch-based Linux distribution focused on "
            "providing a user-friendly experience while maintaining the power "
            "and flexibility of Arch Linux."
        )
        pkos_desc.setWordWrap(True)
        pkos_desc.setStyleSheet("font-size: 13px; color: #555;")
        pkos_layout.addWidget(pkos_desc)
        
        pkos_group.setLayout(pkos_layout)
        layout.addWidget(pkos_group)
        
        # Features
        features_group = QGroupBox("Key Features")
        features_layout = QVBoxLayout()
        
        features_text = QLabel(
            "• Fetch and filter Arch Linux mirrors\n"
            "• Speed test mirrors for optimal performance\n"
            "• Secure backup and restore functionality\n"
            "• Modern PyQt6 interface with multiple views\n"
            "• Automatic fastest mirror detection"
        )
        features_text.setStyleSheet("font-size: 12px; color: #333;")
        features_layout.addWidget(features_text)
        
        features_group.setLayout(features_layout)
        layout.addWidget(features_group)
        
        # Close button
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)
        
        self.setLayout(layout)