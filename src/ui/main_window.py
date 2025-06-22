from PyQt6.QtWidgets import (QMainWindow, QTableWidget, QVBoxLayout, QHBoxLayout, 
                             QWidget, QTableWidgetItem, QPushButton, QLabel, 
                             QProgressBar, QGroupBox, QCheckBox, QComboBox,
                             QMessageBox, QHeaderView, QStatusBar, QSplitter)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor
import time
from src.core.mirror_manager import MirrorManager
from src.core.speed_test import test_mirror_speed
from src.core.secure_operations import SecureFileOperations
from src.ui.dialogs import (PasswordDialog, BackupConfirmDialog,
                           SpeedTestProgressDialog, AboutDialog)


class FetchMirrorsThread(QThread):
    mirrors_fetched = pyqtSignal(list)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, mirror_manager, country=None, protocol=None):
        super().__init__()
        self.mirror_manager = mirror_manager
        self.country = country
        self.protocol = protocol
    
    def run(self):
        try:
            mirrors = self.mirror_manager.fetch_mirrors(
                country=self.country, 
                protocol=self.protocol
            )
            self.mirrors_fetched.emit(mirrors)
        except Exception as e:
            self.error_occurred.emit(str(e))


class RankMirrorsThread(QThread):
    mirror_ranked = pyqtSignal(int, float, str)  # row, speed, url
    ranking_finished = pyqtSignal(list)  # sorted results
    progress_updated = pyqtSignal(int, str, str)  # current, url, status
    cancelled = pyqtSignal()  # emitted when cancelled
    
    def __init__(self, mirrors, timeout=15):
        super().__init__()
        self.mirrors = mirrors
        self.results = []
        self._is_cancelled = False
        self.timeout = timeout
    
    def cancel(self):
        """Cancel the speed testing"""
        self._is_cancelled = True
        self.cancelled.emit()
    
    def run(self):
        for row, mirror in enumerate(self.mirrors):
            # Check if cancelled before each test
            if self._is_cancelled:
                self.progress_updated.emit(row, "Cancelled", "❌ Cancelled by user")
                break
                
            url = mirror['url']
            self.progress_updated.emit(row, url, "Testing...")
            
            try:
                # Add a small delay between tests to be respectful to mirror servers
                if row > 0:  # Don't delay the first test
                    time.sleep(0.5)  # 500ms delay between tests
                
                speed = test_mirror_speed(url, self.timeout)
                
                # Check if cancelled after speed test
                if self._is_cancelled:
                    self.progress_updated.emit(row, url, "❌ Cancelled")
                    break
                
                if speed is not None and speed > 0:
                    # Format speed nicely
                    if speed > 1000000:  # > 1MB/s
                        speed_text = f"{speed/1000000:.1f} MB/s"
                    elif speed > 1000:   # > 1KB/s
                        speed_text = f"{speed/1000:.1f} KB/s"
                    else:
                        speed_text = f"{speed:.0f} B/s"
                    
                    self.results.append((mirror, speed))
                    self.progress_updated.emit(row, url, f"✅ {speed_text}")
                else:
                    speed_text = "Failed"
                    self.results.append((mirror, 0))
                    self.progress_updated.emit(row, url, "❌ Failed")
                
                self.mirror_ranked.emit(row, speed if speed else 0, speed_text)
                
            except Exception as e:
                if not self._is_cancelled:
                    self.results.append((mirror, 0))
                    self.mirror_ranked.emit(row, 0, "Error")
                    self.progress_updated.emit(row, url, f"❌ Error: {str(e)[:50]}")
        
        # Only emit results if not cancelled
        if not self._is_cancelled:
            # Sort results by speed (highest first)
            sorted_results = sorted(self.results, key=lambda x: x[1], reverse=True)
            self.ranking_finished.emit(sorted_results)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🏛️ PKOS Linux Mirrorlist Manager")
        self.setGeometry(100, 100, 1400, 900)
        
        # Data storage
        self.mirrors = []
        self.mirror_manager = MirrorManager()
        self.secure_ops = SecureFileOperations()
        self.sorted_results = []
        
        # Threads
        self.fetch_thread = None
        self.rank_thread = None
        
        # Mode tracking
        self.fastest_finder_mode = False
        
        # Setup UI
        self.setup_menu_bar()
        self.setup_ui()
        self.setup_status_bar()
        
    def setup_ui(self):
        # Main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout = QHBoxLayout()
        main_layout.addWidget(splitter)
        main_widget.setLayout(main_layout)
        
        # Left panel for controls
        left_panel = self.create_control_panel()
        splitter.addWidget(left_panel)
        
        # Right panel for table
        right_panel = self.create_table_panel()
        splitter.addWidget(right_panel)
        
        # Set splitter proportions
        splitter.setSizes([350, 1050])
        
    def create_control_panel(self):
        panel = QWidget()
        layout = QVBoxLayout()
        panel.setLayout(layout)
        
        # Title
        title = QLabel("🔧 Mirror Controls")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #2196F3; margin: 10px 0;")
        layout.addWidget(title)
        
        # Fetch options group
        fetch_group = QGroupBox("🌍 Fetch Options")
        fetch_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        fetch_layout = QVBoxLayout()
        
        # Country selection
        country_label = QLabel("Country (optional):")
        self.country_combo = QComboBox()
        self.country_combo.addItems([
            "All Countries", "US", "DE", "GB", "FR", "CA", "AU", "JP", "CN", "IN", 
            "BR", "RU", "KR", "NL", "SE", "NO", "DK", "FI", "IT", "ES", "PT", "PL"
        ])
        self.country_combo.setStyleSheet("QComboBox { padding: 5px; }")
        fetch_layout.addWidget(country_label)
        fetch_layout.addWidget(self.country_combo)
        
        # Protocol selection
        protocol_label = QLabel("Protocol:")
        self.protocol_combo = QComboBox()
        self.protocol_combo.addItems(["All", "https", "http", "rsync"])
        self.protocol_combo.setStyleSheet("QComboBox { padding: 5px; }")
        fetch_layout.addWidget(protocol_label)
        fetch_layout.addWidget(self.protocol_combo)
        
        # Active only checkbox
        self.active_only_cb = QCheckBox("Active mirrors only")
        self.active_only_cb.setChecked(True)
        self.active_only_cb.setStyleSheet("QCheckBox { font-weight: bold; }")
        fetch_layout.addWidget(self.active_only_cb)
        
        fetch_group.setLayout(fetch_layout)
        layout.addWidget(fetch_group)
        
        # Action buttons
        buttons_group = QGroupBox("⚡ Actions")
        buttons_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        buttons_layout = QVBoxLayout()
        
        self.fetch_button = QPushButton("🔄 Fetch Mirrors")
        self.fetch_button.clicked.connect(self.fetch_mirrors)
        self.fetch_button.setMinimumHeight(45)
        self.fetch_button.setStyleSheet("""
            QPushButton { 
                background-color: #4CAF50; 
                color: white; 
                font-weight: bold; 
                border-radius: 5px; 
                padding: 10px;
            }
            QPushButton:hover { background-color: #45a049; }
            QPushButton:disabled { background-color: #cccccc; }
        """)
        buttons_layout.addWidget(self.fetch_button)
        
        self.rank_button = QPushButton("⚡ Rank by Speed")
        self.rank_button.clicked.connect(self.rank_mirrors)
        self.rank_button.setEnabled(False)
        self.rank_button.setMinimumHeight(45)
        self.rank_button.setStyleSheet("""
            QPushButton { 
                background-color: #FF9800; 
                color: white; 
                font-weight: bold; 
                border-radius: 5px; 
                padding: 10px;
            }
            QPushButton:hover { background-color: #e68900; }
            QPushButton:disabled { background-color: #cccccc; }
        """)
        buttons_layout.addWidget(self.rank_button)
        
        self.apply_button = QPushButton("💾 Apply to System")
        self.apply_button.clicked.connect(self.apply_mirrorlist)
        self.apply_button.setEnabled(False)
        self.apply_button.setMinimumHeight(45)
        self.apply_button.setStyleSheet("""
            QPushButton { 
                background-color: #2196F3; 
                color: white; 
                font-weight: bold; 
                border-radius: 5px; 
                padding: 10px;
            }
            QPushButton:hover { background-color: #1976D2; }
            QPushButton:disabled { background-color: #cccccc; }
        """)
        buttons_layout.addWidget(self.apply_button)
        
        self.find_fastest_button = QPushButton("🚀 Find Fastest Mirrors")
        self.find_fastest_button.clicked.connect(self.find_fastest_mirrors)
        self.find_fastest_button.setMinimumHeight(45)
        self.find_fastest_button.setStyleSheet("""
            QPushButton { 
                background-color: #E91E63; 
                color: white; 
                font-weight: bold; 
                border-radius: 5px; 
                padding: 10px;
            }
            QPushButton:hover { background-color: #C2185B; }
            QPushButton:disabled { background-color: #cccccc; }
        """)
        buttons_layout.addWidget(self.find_fastest_button)
        
        self.backup_button = QPushButton("📋 Backup Current")
        self.backup_button.clicked.connect(self.backup_mirrorlist)
        self.backup_button.setMinimumHeight(45)
        self.backup_button.setStyleSheet("""
            QPushButton { 
                background-color: #9C27B0; 
                color: white; 
                font-weight: bold; 
                border-radius: 5px; 
                padding: 10px;
            }
            QPushButton:hover { background-color: #7B1FA2; }
        """)
        buttons_layout.addWidget(self.backup_button)
        
        buttons_group.setLayout(buttons_layout)
        layout.addWidget(buttons_group)
        
        # Progress section
        progress_group = QGroupBox("📊 Progress")
        progress_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        progress_layout = QVBoxLayout()
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid grey;
                border-radius: 5px;
                text-align: center;
                color: #000000;
                background-color: #ffffff;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                width: 20px;
            }
        """)
        progress_layout.addWidget(self.progress_bar)
        
        self.info_label = QLabel("Ready to fetch mirrors")
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("QLabel { padding: 10px; background-color: #f0f0f0; border-radius: 5px; color: #000000; }")
        progress_layout.addWidget(self.info_label)
        
        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)
        
        layout.addStretch()
        return panel
        
    def create_table_panel(self):
        panel = QWidget()
        layout = QVBoxLayout()
        panel.setLayout(layout)
        
        # Table title
        title_layout = QHBoxLayout()
        title = QLabel("📋 Mirror List")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #2196F3; margin: 10px 0;")
        title_layout.addWidget(title)
        
        # Mirror count label
        self.mirror_count_label = QLabel("")
        self.mirror_count_label.setStyleSheet("color: #666; font-weight: bold;")
        title_layout.addWidget(self.mirror_count_label)
        title_layout.addStretch()
        
        layout.addLayout(title_layout)
        
        # Enhanced Rich Table widget
        self.table_widget = QTableWidget()
        self.table_widget.setColumnCount(7)
        self.table_widget.setHorizontalHeaderLabels([
            "✓", "Rank", "🌍 Country", "🔒 Protocol", "🌐 Mirror URL", "📊 Status", "⚡ Speed"
        ])
        
        # Configure table with rich styling
        header = self.table_widget.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)             # Select
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)             # Rank
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Country
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Protocol
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)           # URL
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # Status
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)  # Speed
        
        # Set fixed widths for specific columns
        self.table_widget.setColumnWidth(0, 50)   # Select checkbox
        self.table_widget.setColumnWidth(1, 80)   # Rank
        
        # Enhanced table styling
        self.table_widget.setAlternatingRowColors(True)
        self.table_widget.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_widget.setRowHeight(0, 60)  # Set default row height
        self.table_widget.verticalHeader().setDefaultSectionSize(60)
        
        self.table_widget.setStyleSheet("""
            QTableWidget {
                gridline-color: #e0e0e0;
                background-color: #ffffff;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                font-size: 14px;
                selection-background-color: #e8f5e8;
                color: #000000;
            }
            QTableWidget::item {
                padding: 12px 8px;
                border: none;
                color: #000000;
                background-color: #ffffff;
            }
            QTableWidget::item:selected {
                background-color: #e8f5e8;
                color: #000000;
            }
            QTableWidget::item:hover {
                background-color: #f0f8f0;
                color: #000000;
            }
            QHeaderView::section {
                background-color: #f5f5f5;
                color: #000000;
                padding: 12px 8px;
                border: 1px solid #e0e0e0;
                font-weight: bold;
                font-size: 14px;
            }
            QHeaderView::section:hover {
                background-color: #e8f5e8;
                color: #000000;
            }
            QTableWidget::alternateBase {
                background-color: #fafafa;
            }
        """)
        
        layout.addWidget(self.table_widget)
        
        # Selection controls
        selection_layout = QHBoxLayout()
        
        self.select_all_button = QPushButton("Select All")
        self.select_all_button.clicked.connect(self.select_all_mirrors)
        self.select_all_button.setStyleSheet("QPushButton { padding: 8px; }")
        selection_layout.addWidget(self.select_all_button)
        
        self.select_none_button = QPushButton("Select None")
        self.select_none_button.clicked.connect(self.select_no_mirrors)
        self.select_none_button.setStyleSheet("QPushButton { padding: 8px; }")
        selection_layout.addWidget(self.select_none_button)
        
        self.select_top_button = QPushButton("Select Top 5")
        self.select_top_button.clicked.connect(self.select_top_mirrors)
        self.select_top_button.setStyleSheet("QPushButton { padding: 8px; }")
        selection_layout.addWidget(self.select_top_button)
        
        self.select_fast_button = QPushButton("🏆 Select Fastest")
        self.select_fast_button.clicked.connect(self.select_fastest_mirrors)
        self.select_fast_button.setEnabled(False)
        self.select_fast_button.setStyleSheet("""
            QPushButton { 
                background-color: #FF5722; 
                color: white; 
                font-weight: bold; 
                padding: 8px; 
                border-radius: 3px;
            }
            QPushButton:hover { background-color: #E64A19; }
            QPushButton:disabled { background-color: #cccccc; }
        """)
        selection_layout.addWidget(self.select_fast_button)
        
        selection_layout.addStretch()
        layout.addLayout(selection_layout)
        
        return panel
        
    def setup_status_bar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
        self.status_bar.setStyleSheet("QStatusBar { background-color: #f0f0f0; }")
    
    def setup_menu_bar(self):
        """Setup the menu bar with Help menu"""
        menubar = self.menuBar()
        
        # Help menu
        help_menu = menubar.addMenu('Help')
        
        # About action
        about_action = help_menu.addAction('About')
        about_action.triggered.connect(self.show_about_dialog)
        
        # Separator
        help_menu.addSeparator()
        
        # Documentation action (placeholder)
        docs_action = help_menu.addAction('Documentation')
        docs_action.triggered.connect(self.show_documentation)
    
    def show_about_dialog(self):
        """Show the About dialog"""
        about_dialog = AboutDialog()
        about_dialog.exec()
    
    def show_documentation(self):
        """Show documentation (placeholder)"""
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(
            self,
            "Documentation",
            "📚 PKOS Linux Mirrorlist Manager Documentation\n\n"
            "For detailed documentation and usage instructions, please visit:\n"
            "• GitHub Repository: https://github.com/pkos-linux/mirrorlist-manager\n"
            "• PKOS Linux Wiki: https://wiki.pkos-linux.org\n\n"
            "Quick Start:\n"
            "1. Click 'Fetch Mirrors' to get the latest mirror list\n"
            "2. Use 'Rank by Speed' to test mirror performance\n"
            "3. Select your preferred mirrors\n"
            "4. Click 'Apply to System' to update your mirrorlist\n\n"
            "Developer: Aamir Abdullah (aamirabdullah33@gmail.com)"
        )
        
    def fetch_mirrors(self):
        if self.fetch_thread and self.fetch_thread.isRunning():
            return
            
        # Get selected options
        country = None
        if self.country_combo.currentText() != "All Countries":
            country = self.country_combo.currentText()
            
        protocol = None
        if self.protocol_combo.currentText() != "All":
            protocol = self.protocol_combo.currentText()
        
        # Update UI
        self.fetch_button.setEnabled(False)
        self.rank_button.setEnabled(False)
        self.apply_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.info_label.setText("🔄 Fetching mirrors from archlinux.org...")
        self.status_bar.showMessage("Fetching mirrors...")
        
        # Start fetch thread
        self.fetch_thread = FetchMirrorsThread(self.mirror_manager, country, protocol)
        self.fetch_thread.mirrors_fetched.connect(self.on_mirrors_fetched)
        self.fetch_thread.error_occurred.connect(self.on_fetch_error)
        self.fetch_thread.start()
        
    def on_mirrors_fetched(self, mirrors):
        self.mirrors = mirrors
        self.display_mirrors(mirrors)
        
        # Update UI
        self.fetch_button.setEnabled(True)
        self.rank_button.setEnabled(True)
        self.apply_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.info_label.setText(f"✅ Fetched {len(mirrors)} mirrors successfully")
        self.status_bar.showMessage(f"Loaded {len(mirrors)} mirrors")
        self.mirror_count_label.setText(f"({len(mirrors)} mirrors)")
        
    def on_fetch_error(self, error_msg):
        # Update UI
        self.fetch_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.info_label.setText(f"❌ Error: {error_msg}")
        self.status_bar.showMessage("Fetch failed")
        
        # Show error dialog
        QMessageBox.critical(self, "Fetch Error", f"Failed to fetch mirrors:\n{error_msg}")
        
    def display_mirrors(self, mirrors):
        self.table_widget.setRowCount(len(mirrors))
        
        for row, mirror in enumerate(mirrors):
            # Checkbox for selection with centered alignment
            checkbox_widget = QWidget()
            checkbox_widget.setStyleSheet("background-color: #ffffff; color: #000000;")
            checkbox_layout = QHBoxLayout(checkbox_widget)
            checkbox = QCheckBox()
            checkbox.setStyleSheet("""
                QCheckBox {
                    background-color: #ffffff;
                    color: #000000;
                }
                QCheckBox::indicator {
                    width: 20px;
                    height: 20px;
                }
                QCheckBox::indicator:unchecked {
                    border: 2px solid #cccccc;
                    border-radius: 4px;
                    background-color: #ffffff;
                }
                QCheckBox::indicator:checked {
                    border: 2px solid #4CAF50;
                    border-radius: 4px;
                    background-color: #4CAF50;
                }
            """)
            checkbox_layout.addWidget(checkbox)
            checkbox_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            checkbox_layout.setContentsMargins(0, 0, 0, 0)
            self.table_widget.setCellWidget(row, 0, checkbox_widget)
            
            # Rank badge
            rank_widget = QWidget()
            rank_widget.setStyleSheet("background-color: #ffffff; color: #000000;")
            rank_layout = QHBoxLayout(rank_widget)
            rank_label = QLabel(f"#{row + 1}")
            rank_label.setStyleSheet("""
                QLabel {
                    background-color: #2196F3;
                    color: white;
                    border-radius: 12px;
                    padding: 4px 8px;
                    font-weight: bold;
                    font-size: 12px;
                }
            """)
            rank_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            rank_layout.addWidget(rank_label)
            rank_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            rank_layout.setContentsMargins(0, 0, 0, 0)
            self.table_widget.setCellWidget(row, 1, rank_widget)
            
            # Country with flag
            country_item = QTableWidgetItem(f"🌍 {mirror['country']}")
            country_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            country_item.setFont(QFont("Arial", 13, QFont.Weight.Bold))
            country_item.setBackground(QColor("#ffffff"))
            country_item.setForeground(QColor("#000000"))
            self.table_widget.setItem(row, 2, country_item)
            
            # Protocol with styling
            protocol = mirror['protocol'].upper()
            protocol_item = QTableWidgetItem(protocol)
            protocol_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            protocol_item.setFont(QFont("Arial", 12, QFont.Weight.Bold))
            protocol_item.setBackground(QColor("#ffffff"))
            
            # Color code protocols
            if protocol == "HTTPS":
                protocol_item.setForeground(QColor("#4CAF50"))  # Green
            elif protocol == "HTTP":
                protocol_item.setForeground(QColor("#FF9800"))  # Orange
            else:
                protocol_item.setForeground(QColor("#9E9E9E"))  # Gray
                
            self.table_widget.setItem(row, 3, protocol_item)
            
            # URL with monospace font
            url_item = QTableWidgetItem(mirror['url'])
            url_item.setFont(QFont("Courier New", 11))
            url_item.setToolTip(mirror['url'])  # Full URL on hover
            url_item.setBackground(QColor("#ffffff"))
            url_item.setForeground(QColor("#000000"))
            self.table_widget.setItem(row, 4, url_item)
            
            # Status with icon
            status_item = QTableWidgetItem("🟢 Active")
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            status_item.setFont(QFont("Arial", 12, QFont.Weight.Bold))
            status_item.setBackground(QColor("#ffffff"))
            status_item.setForeground(QColor("#4CAF50"))
            self.table_widget.setItem(row, 5, status_item)
            
            # Speed placeholder
            speed_item = QTableWidgetItem("⏳ Not tested")
            speed_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            speed_item.setFont(QFont("Arial", 12))
            speed_item.setBackground(QColor("#ffffff"))
            speed_item.setForeground(QColor("#9E9E9E"))
            self.table_widget.setItem(row, 6, speed_item)
            
    def rank_mirrors(self):
        if not self.mirrors or (self.rank_thread and self.rank_thread.isRunning()):
            return
        
        # Show progress dialog
        self.progress_dialog = SpeedTestProgressDialog(len(self.mirrors))
        self.progress_dialog.show()
        
        # Update UI
        self.rank_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, len(self.mirrors))
        self.progress_bar.setValue(0)
        self.info_label.setText(f"⚡ Testing {len(self.mirrors)} mirror speeds... (this may take a few minutes)")
        self.status_bar.showMessage("Ranking mirrors by speed...")
        
        # Start ranking thread
        self.rank_thread = RankMirrorsThread(self.mirrors, timeout=15)
        self.rank_thread.mirror_ranked.connect(self.on_mirror_ranked)
        self.rank_thread.ranking_finished.connect(self.on_ranking_finished)
        self.rank_thread.progress_updated.connect(self.on_progress_updated)
        self.rank_thread.cancelled.connect(self.on_speed_test_cancelled)
        
        # Connect progress dialog cancellation to thread cancellation
        self.progress_dialog.cancel_requested.connect(self.rank_thread.cancel)
        
        self.rank_thread.start()
        
    def on_progress_updated(self, current, url, status):
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.update_progress(current, url, status)
        
    def on_mirror_ranked(self, row, speed, speed_text):
        if row < self.table_widget.rowCount():
            # Create rich speed display
            if speed > 0:
                if speed > 1000000:  # > 1MB/s
                    icon = "🚀"
                    color = "#4CAF50"
                    formatted_speed = f"{speed/1000000:.1f} MB/s"
                elif speed > 100000:   # > 100KB/s
                    icon = "⚡"
                    color = "#8BC34A"
                    formatted_speed = f"{speed/1000:.0f} KB/s"
                else:
                    icon = "🐌"
                    color = "#FF9800"
                    formatted_speed = f"{speed:.0f} B/s"
                speed_display = f"{icon} {formatted_speed}"
            else:
                icon = "❌"
                color = "#F44336"
                speed_display = f"{icon} Failed"
            
            speed_item = QTableWidgetItem(speed_display)
            speed_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            speed_item.setFont(QFont("Arial", 12, QFont.Weight.Bold))
            speed_item.setBackground(QColor("#ffffff"))
            speed_item.setForeground(QColor(color))
            self.table_widget.setItem(row, 6, speed_item)
            self.progress_bar.setValue(row + 1)
            
    def on_ranking_finished(self, sorted_results):
        self.sorted_results = sorted_results
        
        # Close progress dialog
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.close()
        
        # Sort table by speed
        self.sort_table_by_speed(sorted_results)
        
        # Update UI
        self.rank_button.setEnabled(True)
        self.select_fast_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.info_label.setText("🏆 Mirror ranking completed! Table sorted by speed.")
        self.status_bar.showMessage("Ranking completed - fastest mirrors at top")
        
        # Show selection dialog
        if sorted_results:
            self.show_mirror_selection_dialog(sorted_results)
    
    def on_speed_test_cancelled(self):
        """Handle speed test cancellation"""
        # Close progress dialog
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.close()
        
        # Reset UI state
        self.rank_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.info_label.setText("❌ Speed test cancelled by user")
        self.status_bar.showMessage("Speed test cancelled")
        
        # Clean up thread
        if hasattr(self, 'rank_thread') and self.rank_thread:
            self.rank_thread.wait(1000)  # Wait up to 1 second for thread to finish
    
    def sort_table_by_speed(self, sorted_results):
        """Sort the table to show fastest mirrors first."""
        # Create a mapping of URLs to their new positions
        url_to_position = {}
        for i, (mirror_data, speed) in enumerate(sorted_results):
            url_to_position[mirror_data['url']] = i
        
        # Reorder table rows
        new_mirrors = []
        for mirror_data, speed in sorted_results:
            new_mirrors.append(mirror_data)
        
        self.mirrors = new_mirrors
        self.display_mirrors(new_mirrors)
        
        # Update speed column with sorted results
        for row, (mirror_data, speed) in enumerate(sorted_results):
            # Create rich speed display
            if speed > 0:
                if speed > 1000000:  # > 1MB/s
                    icon = "🚀"
                    color = "#4CAF50"
                    formatted_speed = f"{speed/1000000:.1f} MB/s"
                elif speed > 100000:   # > 100KB/s
                    icon = "⚡"
                    color = "#8BC34A"
                    formatted_speed = f"{speed/1000:.0f} KB/s"
                else:
                    icon = "🐌"
                    color = "#FF9800"
                    formatted_speed = f"{speed:.0f} B/s"
                speed_display = f"{icon} {formatted_speed}"
            else:
                icon = "❌"
                color = "#F44336"
                speed_display = f"{icon} Failed"
            
            speed_item = QTableWidgetItem(speed_display)
            speed_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            speed_item.setFont(QFont("Arial", 12, QFont.Weight.Bold))
            speed_item.setBackground(QColor("#ffffff"))
            speed_item.setForeground(QColor(color))
            self.table_widget.setItem(row, 6, speed_item)
    
    def show_mirror_selection_dialog(self, sorted_results):
        """Automatically select top performing mirrors."""
        # Auto-select top 10 fastest mirrors
        fast_mirrors = [result[0] for result in sorted_results[:10] if result[1] > 0]
        
        if fast_mirrors:
            # Clear all selections first
            self.select_no_mirrors()
            
            # Select the fastest mirrors
            for mirror in fast_mirrors:
                for row in range(self.table_widget.rowCount()):
                    url_item = self.table_widget.item(row, 4)  # URL is now column 4
                    if url_item and url_item.text() == mirror['url']:
                        checkbox_widget = self.table_widget.cellWidget(row, 0)
                        if checkbox_widget:
                            checkbox = checkbox_widget.findChild(QCheckBox)
                            if checkbox:
                                checkbox.setChecked(True)
                        break
            
            self.info_label.setText(f"✅ Auto-selected {len(fast_mirrors)} fastest mirrors")
        else:
            self.info_label.setText("⚠️ No fast mirrors found")
    
    def select_fastest_mirrors(self):
        """Select the fastest mirrors automatically."""
        if not self.sorted_results:
            return
        
        # Select top 10 fastest mirrors
        self.select_no_mirrors()
        fast_mirrors = [result[0] for result in self.sorted_results[:10] if result[1] > 0]
        
        for mirror in fast_mirrors:
            for row in range(self.table_widget.rowCount()):
                url_item = self.table_widget.item(row, 4)  # URL is now column 4
                if url_item and url_item.text() == mirror['url']:
                    checkbox_widget = self.table_widget.cellWidget(row, 0)
                    if checkbox_widget:
                        checkbox = checkbox_widget.findChild(QCheckBox)
                        if checkbox:
                            checkbox.setChecked(True)
                    break
        
        self.info_label.setText(f"🏆 Auto-selected {len(fast_mirrors)} fastest mirrors")
        
    def select_all_mirrors(self):
        for row in range(self.table_widget.rowCount()):
            checkbox_widget = self.table_widget.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox:
                    checkbox.setChecked(True)
                
    def select_no_mirrors(self):
        for row in range(self.table_widget.rowCount()):
            checkbox_widget = self.table_widget.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox:
                    checkbox.setChecked(False)
                
    def select_top_mirrors(self):
        self.select_no_mirrors()
        for row in range(min(5, self.table_widget.rowCount())):
            checkbox_widget = self.table_widget.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox:
                    checkbox.setChecked(True)
                
    def apply_mirrorlist(self):
        selected_mirrors = []
        
        for row in range(self.table_widget.rowCount()):
            checkbox_widget = self.table_widget.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox and checkbox.isChecked():
                    country_item = self.table_widget.item(row, 2)  # Country is now column 2
                    protocol_item = self.table_widget.item(row, 3)  # Protocol is now column 3
                    url_item = self.table_widget.item(row, 4)       # URL is now column 4
                    
                    if country_item and protocol_item and url_item:
                        # Clean up the country text (remove flag emoji)
                        country_text = country_item.text().replace("🌍 ", "")
                        mirror = {
                            'country': country_text,
                            'protocol': protocol_item.text().lower(),
                            'url': url_item.text()
                        }
                        selected_mirrors.append(mirror)
        
        if not selected_mirrors:
            QMessageBox.warning(self, "No Selection", "Please select at least one mirror.")
            return
        
        # Show backup confirmation dialog
        existing_backups = self.secure_ops.get_existing_backups()
        backup_dialog = BackupConfirmDialog(existing_backups)
        backup_dialog.set_mirror_count(len(selected_mirrors))
        
        if backup_dialog.exec() == backup_dialog.DialogCode.Accepted:
            try:
                # Get password once for all operations
                password = self.secure_ops.authenticate_user("applying mirrorlist changes")
                if not password:
                    return  # User cancelled password dialog
                
                backup_path = None
                
                # Create backup first if requested
                if backup_dialog.should_create_backup():
                    backup_path = self.secure_ops.create_backup(password)
                    if not backup_path:
                        return  # Backup failed
                    
                    if backup_dialog.should_verify_backup():
                        # Verify backup was created using the same password
                        if not self.secure_ops.verify_backup(backup_path, password):
                            QMessageBox.critical(self, "Backup Verification Failed", 
                                               "Could not verify backup was created successfully.")
                            return
                
                # Apply the mirrorlist using the same password
                if self.secure_ops.write_mirrorlist(selected_mirrors, password):
                    # Clear the cached password after successful operation
                    self.secure_ops.clear_cached_password()
                    
                    QMessageBox.information(
                        self, 
                        "Success", 
                        f"✅ Mirrorlist applied successfully!\n\n"
                        f"Applied {len(selected_mirrors)} mirrors to /etc/pacman.d/mirrorlist\n"
                        f"Backup created: {backup_path if backup_path else 'None'}\n\n"
                        f"Run 'sudo pacman -Syy' to refresh package databases."
                    )
                    self.status_bar.showMessage("Mirrorlist applied successfully")
                    self.info_label.setText("✅ Mirrorlist applied! Run 'sudo pacman -Syy'")
                else:
                    # Clear password on failure too
                    self.secure_ops.clear_cached_password()
                    
            except Exception as e:
                # Clear password on error
                self.secure_ops.clear_cached_password()
                QMessageBox.critical(self, "Error", f"Failed to apply mirrorlist:\n{str(e)}")
                self.status_bar.showMessage("Apply failed")
                self.info_label.setText(f"❌ Apply error: {str(e)}")
                
    def backup_mirrorlist(self):
        """Create a backup of the current mirrorlist using in-app password dialog."""
        try:
            # Show existing backups
            existing_backups = self.secure_ops.get_existing_backups()
            
            # Update info
            self.info_label.setText("🔐 Creating backup... (password required)")
            self.status_bar.showMessage("Creating backup...")
            
            # Get password for backup operation
            password = self.secure_ops.authenticate_user("creating backup")
            if not password:
                self.info_label.setText("❌ Backup cancelled by user")
                self.status_bar.showMessage("Backup cancelled")
                return
            
            # Create backup with the authenticated password
            backup_path = self.secure_ops.create_backup(password)
            
            if backup_path:
                # Clear the cached password after successful operation
                self.secure_ops.clear_cached_password()
                
                QMessageBox.information(
                    self, 
                    "Backup Created Successfully", 
                    f"✅ Mirrorlist has been backed up to:\n{backup_path}\n\n"
                    f"📊 Total backups found: {len(existing_backups) + 1}\n\n"
                    f"💡 Tip: Backups are automatically created before applying changes."
                )
                self.status_bar.showMessage(f"Backup created: {backup_path}")
                self.info_label.setText("✅ Backup created successfully")
            else:
                # Clear password on failure
                self.secure_ops.clear_cached_password()
                self.info_label.setText("❌ Backup creation failed")
                self.status_bar.showMessage("Backup failed")
                
        except Exception as e:
            # Clear password on error
            self.secure_ops.clear_cached_password()
            error_msg = str(e)
            QMessageBox.critical(
                self, 
                "Backup Failed", 
                f"❌ Failed to create backup:\n{error_msg}\n\n"
                f"💡 Make sure you have the correct password and sufficient permissions."
            )
            self.status_bar.showMessage("Backup failed")
            self.info_label.setText(f"❌ Backup error: {error_msg}")
    
    def find_fastest_mirrors(self):
        """Automatically find the fastest mirrors with optional country filtering."""
        # Get selected options
        country = None
        if self.country_combo.currentText() != "All Countries":
            country = self.country_combo.currentText()
            
        protocol = None
        if self.protocol_combo.currentText() != "All":
            protocol = self.protocol_combo.currentText()
        
        # Update UI
        self.find_fastest_button.setEnabled(False)
        self.fetch_button.setEnabled(False)
        self.rank_button.setEnabled(False)
        self.apply_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        
        if country:
            self.info_label.setText(f"🚀 Finding fastest mirrors in {country}...")
            self.status_bar.showMessage(f"Finding fastest mirrors in {country}...")
        else:
            self.info_label.setText("🚀 Finding fastest mirrors globally...")
            self.status_bar.showMessage("Finding fastest mirrors globally...")
        
        # Start the process by fetching mirrors first
        self.fastest_finder_mode = True
        self.fetch_thread = FetchMirrorsThread(self.mirror_manager, country, protocol)
        self.fetch_thread.mirrors_fetched.connect(self.on_fastest_mirrors_fetched)
        self.fetch_thread.error_occurred.connect(self.on_fastest_fetch_error)
        self.fetch_thread.start()
    
    def on_fastest_mirrors_fetched(self, mirrors):
        """Handle mirrors fetched for fastest mirror finding."""
        self.mirrors = mirrors
        
        # Limit to a reasonable number for speed testing (40 mirrors max for better reliability)
        test_mirrors = mirrors[:40] if len(mirrors) > 40 else mirrors
        
        self.info_label.setText(f"🔍 Testing {len(test_mirrors)} mirrors for speed...")
        self.status_bar.showMessage(f"Speed testing {len(test_mirrors)} mirrors...")
        
        # Show progress dialog
        self.progress_dialog = SpeedTestProgressDialog(len(test_mirrors))
        self.progress_dialog.show()
        
        # Start ranking the limited set with longer timeout for Find Fastest Mirrors
        self.rank_thread = RankMirrorsThread(test_mirrors, timeout=20)
        self.rank_thread.mirror_ranked.connect(self.on_fastest_mirror_ranked)
        self.rank_thread.ranking_finished.connect(self.on_fastest_ranking_finished)
        self.rank_thread.progress_updated.connect(self.on_progress_updated)
        self.rank_thread.cancelled.connect(self.on_fastest_speed_test_cancelled)
        
        # Connect progress dialog cancellation to thread cancellation
        self.progress_dialog.cancel_requested.connect(self.rank_thread.cancel)
        
        self.rank_thread.start()
    
    def on_fastest_fetch_error(self, error_msg):
        """Handle fetch error for fastest mirror finding."""
        self.find_fastest_button.setEnabled(True)
        self.fetch_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.info_label.setText(f"❌ Error finding fastest mirrors: {error_msg}")
        self.status_bar.showMessage("Fastest mirror search failed")
        QMessageBox.critical(self, "Fastest Mirror Search Error", f"Failed to find fastest mirrors:\n{error_msg}")
    
    def on_fastest_mirror_ranked(self, row, speed, speed_text):
        """Handle individual mirror ranking for fastest finder."""
        # We don't update the main table during fastest finder mode
        pass
    
    def on_fastest_ranking_finished(self, sorted_results):
        """Handle completion of fastest mirror finding."""
        self.fastest_finder_mode = False
        
        # Close progress dialog
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.close()
        
        # Filter out failed mirrors and get top 10
        successful_mirrors = [(mirror, speed) for mirror, speed in sorted_results if speed > 0]
        top_mirrors = successful_mirrors[:10]
        
        if top_mirrors:
            # Display the fastest mirrors in the table
            self.display_fastest_results(top_mirrors)
            
            # Auto-select all the fastest mirrors
            self.select_all_mirrors()
            
            # Update UI
            fastest_speed = top_mirrors[0][1]
            if fastest_speed > 1000000:
                speed_text = f"{fastest_speed/1000000:.1f} MB/s"
            else:
                speed_text = f"{fastest_speed/1000:.0f} KB/s"
            
            self.info_label.setText(f"🏆 Found {len(top_mirrors)} fastest mirrors! Top speed: {speed_text}")
            self.status_bar.showMessage(f"Fastest mirrors found - Top speed: {speed_text}")
        else:
            self.info_label.setText("❌ No working mirrors found")
            self.status_bar.showMessage("No working mirrors found")
        
        # Re-enable buttons
        self.find_fastest_button.setEnabled(True)
        self.fetch_button.setEnabled(True)
        self.rank_button.setEnabled(True)
        self.apply_button.setEnabled(True)
        self.progress_bar.setVisible(False)
    
    def on_fastest_speed_test_cancelled(self):
        """Handle speed test cancellation during fastest mirror finding"""
        self.fastest_finder_mode = False
        
        # Close progress dialog
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.close()
        
        # Reset UI state
        self.find_fastest_button.setEnabled(True)
        self.fetch_button.setEnabled(True)
        self.rank_button.setEnabled(True)
        self.apply_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.info_label.setText("❌ Fastest mirror search cancelled by user")
        self.status_bar.showMessage("Fastest mirror search cancelled")
        
        # Clean up thread
        if hasattr(self, 'rank_thread') and self.rank_thread:
            self.rank_thread.wait(1000)  # Wait up to 1 second for thread to finish
    
    def display_fastest_results(self, fastest_mirrors):
        """Display the fastest mirrors in the table."""
        self.table_widget.setRowCount(len(fastest_mirrors))
        
        for row, (mirror, speed) in enumerate(fastest_mirrors):
            # Checkbox for selection with centered alignment
            checkbox_widget = QWidget()
            checkbox_widget.setStyleSheet("background-color: #ffffff; color: #000000;")
            checkbox_layout = QHBoxLayout(checkbox_widget)
            checkbox = QCheckBox()
            checkbox.setStyleSheet("""
                QCheckBox {
                    background-color: #ffffff;
                    color: #000000;
                }
                QCheckBox::indicator {
                    width: 20px;
                    height: 20px;
                }
                QCheckBox::indicator:unchecked {
                    border: 2px solid #cccccc;
                    border-radius: 4px;
                    background-color: #ffffff;
                }
                QCheckBox::indicator:checked {
                    border: 2px solid #4CAF50;
                    border-radius: 4px;
                    background-color: #4CAF50;
                }
            """)
            checkbox_layout.addWidget(checkbox)
            checkbox_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            checkbox_layout.setContentsMargins(0, 0, 0, 0)
            self.table_widget.setCellWidget(row, 0, checkbox_widget)
            
            # Rank badge
            rank_widget = QWidget()
            rank_widget.setStyleSheet("background-color: #ffffff; color: #000000;")
            rank_layout = QHBoxLayout(rank_widget)
            rank_label = QLabel(f"#{row + 1}")
            rank_label.setStyleSheet("""
                QLabel {
                    background-color: #4CAF50;
                    color: white;
                    border-radius: 12px;
                    padding: 4px 8px;
                    font-weight: bold;
                    font-size: 12px;
                }
            """)
            rank_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            rank_layout.addWidget(rank_label)
            rank_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            rank_layout.setContentsMargins(0, 0, 0, 0)
            self.table_widget.setCellWidget(row, 1, rank_widget)
            
            # Country with flag
            country_item = QTableWidgetItem(f"��� {mirror['country']}")
            country_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            country_item.setFont(QFont("Arial", 13, QFont.Weight.Bold))
            country_item.setBackground(QColor("#ffffff"))
            country_item.setForeground(QColor("#000000"))
            self.table_widget.setItem(row, 2, country_item)
            
            # Protocol with styling
            protocol = mirror['protocol'].upper()
            protocol_item = QTableWidgetItem(protocol)
            protocol_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            protocol_item.setFont(QFont("Arial", 12, QFont.Weight.Bold))
            protocol_item.setBackground(QColor("#ffffff"))
            
            # Color code protocols
            if protocol == "HTTPS":
                protocol_item.setForeground(QColor("#4CAF50"))  # Green
            elif protocol == "HTTP":
                protocol_item.setForeground(QColor("#FF9800"))  # Orange
            else:
                protocol_item.setForeground(QColor("#9E9E9E"))  # Gray
                
            self.table_widget.setItem(row, 3, protocol_item)
            
            # URL with monospace font
            url_item = QTableWidgetItem(mirror['url'])
            url_item.setFont(QFont("Courier New", 11))
            url_item.setToolTip(mirror['url'])  # Full URL on hover
            url_item.setBackground(QColor("#ffffff"))
            url_item.setForeground(QColor("#000000"))
            self.table_widget.setItem(row, 4, url_item)
            
            # Status with icon
            status_item = QTableWidgetItem("🟢 Fastest")
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            status_item.setFont(QFont("Arial", 12, QFont.Weight.Bold))
            status_item.setBackground(QColor("#ffffff"))
            status_item.setForeground(QColor("#4CAF50"))
            self.table_widget.setItem(row, 5, status_item)
            
            # Speed display
            if speed > 1000000:  # > 1MB/s
                icon = "🚀"
                color = "#4CAF50"
                formatted_speed = f"{speed/1000000:.1f} MB/s"
            elif speed > 100000:   # > 100KB/s
                icon = "⚡"
                color = "#8BC34A"
                formatted_speed = f"{speed/1000:.0f} KB/s"
            else:
                icon = "🐌"
                color = "#FF9800"
                formatted_speed = f"{speed:.0f} B/s"
            
            speed_display = f"{icon} {formatted_speed}"
            speed_item = QTableWidgetItem(speed_display)
            speed_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            speed_item.setFont(QFont("Arial", 12, QFont.Weight.Bold))
            speed_item.setBackground(QColor("#ffffff"))
            speed_item.setForeground(QColor(color))
            self.table_widget.setItem(row, 6, speed_item)
        
        # Update mirror count
        self.mirror_count_label.setText(f"({len(fastest_mirrors)} fastest mirrors)")