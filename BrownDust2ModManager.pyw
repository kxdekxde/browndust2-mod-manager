import os
import sys
import json
import csv
import subprocess
import shutil
import tempfile
import re
import urllib.request
import hashlib
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton,
    QScrollArea, QHBoxLayout, QLabel, QLineEdit,
    QFileDialog, QMessageBox, QProgressDialog, QHeaderView, QTableWidget, QTableWidgetItem
)
from PyQt6.QtGui import QIcon, QColor, QPalette
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer

# GitHub configuration
GITHUB_FILES = {
    "characters.json": "https://raw.githubusercontent.com/kxdekxde/browndust2-mod-manager/refs/heads/main/characters.json"
}

def get_base_path():
    """Get the base path for the application"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(__file__)

def calculate_file_hash(filepath):
    """Calculate SHA256 hash of a file"""
    sha256_hash = hashlib.sha256()
    if os.path.exists(filepath):
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def download_file(url, destination):
    try:
        urllib.request.urlretrieve(url, destination)
        return True
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return False

def check_for_updates():
    """Check if GitHub files are newer than local ones"""
    updates_available = False
    for filename, url in GITHUB_FILES.items():
        local_path = os.path.join(get_base_path(), filename)
        if os.path.exists(local_path):
            local_hash = calculate_file_hash(local_path)
            
            temp_file = os.path.join(tempfile.gettempdir(), f"temp_{filename}")
            if download_file(url, temp_file):
                remote_hash = calculate_file_hash(temp_file)
                os.remove(temp_file)
                
                if local_hash != remote_hash:
                    updates_available = True
                    break
    return updates_available

def update_files_from_github():
    """Download updated files from GitHub"""
    for filename, url in GITHUB_FILES.items():
        local_path = os.path.join(get_base_path(), filename)
        download_file(url, local_path)

class SpineViewerController:
    def __init__(self):
        self.viewer_process = None
        self.viewer_path = os.path.join(get_base_path(), "SpineViewer-anosu", "SpineViewer.exe")
        
    def launch_viewer(self, skel_path=None):
        """Launch the Spine viewer with optional skeleton file"""
        try:
            if os.path.exists(self.viewer_path):
                if skel_path:
                    self.viewer_process = subprocess.Popen([self.viewer_path, skel_path])
                else:
                    self.viewer_process = subprocess.Popen([self.viewer_path])
                return True
            else:
                print(f"Spine viewer not found at: {self.viewer_path}")
                return False
        except Exception as e:
            print(f"Error launching viewer: {e}")
            return False
            
    def close_viewer(self):
        """Close the viewer"""
        if self.viewer_process and self.viewer_process.poll() is None:
            self.viewer_process.terminate()

class SpineViewer(QWidget):
    def __init__(self):
        super().__init__()
        self.settings_file = os.path.join(get_base_path(), "spine_viewer_settings.json")
        self.setWindowTitle("Brown Dust II Mod Manager")
        self.setGeometry(100, 100, 1200, 800)
        self.viewer_controller = SpineViewerController()
        self._character_data_cache = None  # Cache for character data

        # Apply Windows 11 dark theme
        self.set_windows11_dark_theme()

        # Check for updates before loading anything and update without asking
        self.check_and_update_github_files()

        self.character_data = self.load_character_data()
        self.settings = self.load_settings()

        main_layout = QVBoxLayout()

        # Mods folder selection bar
        folder_layout = QHBoxLayout()
        folder_layout.addWidget(QLabel("Mods Folder:"))

        self.folder_edit = QLineEdit()
        self.folder_edit.setPlaceholderText("Path to your mods folder")
        if self.settings.get("mods_folder"):
            self.folder_edit.setText(self.settings["mods_folder"])
        folder_layout.addWidget(self.folder_edit)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_mods_folder)
        folder_layout.addWidget(browse_btn)

        refresh_btn = QPushButton("Refresh Mods List")
        refresh_btn.clicked.connect(self.load_mods)
        folder_layout.addWidget(refresh_btn)

        main_layout.addLayout(folder_layout)

        # Search bar for filtering mods
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search:"))

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Filter mods by author, character or type...")
        self.search_edit.textChanged.connect(self.filter_mods)
        search_layout.addWidget(self.search_edit)

        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear_search)
        search_layout.addWidget(clear_btn)

        main_layout.addLayout(search_layout)

        # Create table widget for mods list
        self.table_widget = QTableWidget()
        self.table_widget.setColumnCount(6)
        
        # Store original labels to manage sort indicators
        self.original_header_labels = ["Author", "Character", "Costume", "Type", "Status", "Actions"]
        self.table_widget.setHorizontalHeaderLabels(self.original_header_labels)
        self.table_widget.setSortingEnabled(True)
        
        # Connect signal to update header with sort arrows
        header = self.table_widget.horizontalHeader()
        header.sortIndicatorChanged.connect(self.update_header_sort_indicator)
        
        # Configure column resize modes
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)  # Author
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)  # Character
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)     # Costume
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)  # Type
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive)  # Status
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # Actions
        
        self.table_widget.verticalHeader().setVisible(False)
        self.table_widget.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_widget.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        main_layout.addWidget(self.table_widget)
        self.setLayout(main_layout)

        self.verify_mods_folder()
        self.folder_edit.textChanged.connect(self.folder_path_changed)

    def update_header_sort_indicator(self, column_index, order):
        """Update header text to show a sort order arrow."""
        # First, reset all headers to their original text
        for i in range(len(self.original_header_labels)):
            header_item = self.table_widget.horizontalHeaderItem(i)
            if header_item:
                header_item.setText(self.original_header_labels[i])
        
        # If sorting is disabled (index is -1), we are done.
        if column_index == -1:
            return

        # Append an arrow to the header of the currently sorted column
        header_item = self.table_widget.horizontalHeaderItem(column_index)
        if header_item:
            original_text = self.original_header_labels[column_index]
            if order == Qt.SortOrder.AscendingOrder:
                header_item.setText(f"{original_text} ▲")
            elif order == Qt.SortOrder.DescendingOrder:
                header_item.setText(f"{original_text} ▼")

    def set_windows11_dark_theme(self):
        """Apply Windows 11 style dark theme to the application"""
        app = QApplication.instance()
        
        # Enable dark title bar on Windows
        if sys.platform == "win32":
            try:
                from ctypes import windll, byref, sizeof, c_int
                hwnd = int(self.winId())
                for attribute in [19, 20]:  # Try both dark mode attributes
                    try:
                        value = c_int(1)
                        windll.dwmapi.DwmSetWindowAttribute(
                            hwnd,
                            attribute,
                            byref(value),
                            sizeof(value)
                        )
                    except Exception as e:
                        print(f"Dark title bar not supported (attribute {attribute}): {e}")
            except Exception as e:
                print(f"Dark title bar initialization failed: {e}")

        # Create dark palette with correct parameter order
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(32, 32, 32))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(240, 240, 240))
        palette.setColor(QPalette.ColorRole.Base, QColor(25, 25, 25))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(240, 240, 240))
        palette.setColor(QPalette.ColorRole.Text, QColor(240, 240, 240))
        palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(240, 240, 240))
        palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
        palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(240, 240, 240))
        palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(120, 120, 120))

        # Disabled colors
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor(127, 127, 127))
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(127, 127, 127))
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(127, 127, 127))

        app.setPalette(palette)

        # Set style sheet for additional styling
        self.setStyleSheet("""
            QWidget {
                background-color: #202020;
                color: #f0f0f0;
                font-family: "Segoe UI", Arial, sans-serif;
                font-size: 9pt;
            }
            QPushButton {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 5px 12px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
                border: 1px solid #4d4d4d;
            }
            QPushButton:pressed {
                background-color: #1d1d1d;
            }
            QScrollArea {
                border: none;
            }
            QLineEdit {
                background-color: #252525;
                color: #f0f0f0;
                padding: 5px;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                selection-background-color: #3a6ea5;
                selection-color: #ffffff;
            }
            QLineEdit:disabled {
                background-color: #1a1a1a;
                color: #7f7f7f;
            }
            QProgressDialog {
                background-color: #202020;
                color: #f0f0f0;
            }
            QProgressBar {
                background-color: #252525;
                color: #f0f0f0;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #3a6ea5;
                border-radius: 3px;
            }
            QLabel {
                color: #f0f0f0;
            }
            QMessageBox {
                background-color: #202020;
            }
            QMessageBox QLabel {
                color: #f0f0f0;
            }
            QScrollBar:vertical {
                border: none;
                background: #252525;
                width: 10px;
                margin: 0px 0px 0px 0px;
            }
            QScrollBar::handle:vertical {
                background: #0077BE;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::add-line:vertical {
                border: none;
                background: none;
                height: 0px;
                subcontrol-position: bottom;
                subcontrol-origin: margin;
            }
            QScrollBar::sub-line:vertical {
                border: none;
                background: none;
                height: 0px;
                subcontrol-position: top;
                subcontrol-origin: margin;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
            QTableWidget {
                background-color: #252525;
                border: 1px solid #3d3d3d;
                gridline-color: #3d3d3d;
            }
            QHeaderView::section {
                background-color: #2d2d2d;
                color: #f0f0f0;
                padding: 5px;
                border: none;
            }
            QTableWidgetItem {
                text-align: center;
            }
        """)

    def check_and_update_github_files(self):
        """Check for updates from GitHub and update without asking"""
        try:
            if check_for_updates():
                update_files_from_github()
        except Exception as e:
            print(f"Error checking for updates: {e}")

    def get_modfile_path(self, folder_path):
        """Find the .modfile or .mod file in the folder or its subfolders"""
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if file.lower().endswith('.modfile') or file.lower().endswith('.mod'):
                    return os.path.join(root, file)
        return None

    def is_mod_active(self, folder_path):
        """Check if mod is active by looking for .modfile extension in subfolders"""
        modfile_path = self.get_modfile_path(folder_path)
        if modfile_path:
            return modfile_path.lower().endswith('.modfile')
        return False

    def has_animation_files(self, folder_path):
        """Check if folder contains .skel or .json animation files"""
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if file.lower().endswith('.skel') or file.lower().endswith('.json'):
                    return True
        return False

    def get_character_id_from_folder(self, folder_path):
        """Improved file ID detection with special case handling"""
        found_ids = set()
        
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                lower_file = file.lower()
                
                # Standard character files (charXXXXXX)
                char_match = re.match(r'^(cutscene_)?(char\d{6})', lower_file)
                if char_match:
                    found_ids.add(char_match.group(2))
                
                # Special illustration/NPC files
                elif any(x in lower_file for x in ['illust_', 'npc', 'special']):
                    base_name = os.path.splitext(lower_file)[0]
                    found_ids.add(base_name)
                
                # Fallback: Any ID-like pattern
                elif '_' in lower_file:
                    possible_id = lower_file.split('_')[0]
                    if len(possible_id) >= 6:  # Minimum length for IDs
                        found_ids.add(possible_id)
        
        return max(found_ids, key=lambda x: len(x)) if found_ids else None

    def load_character_data(self):
        """Load character data from JSON file and organize by file_id"""
        character_data = {}
        try:
            json_path = os.path.join(get_base_path(), "characters.json")
            if not os.path.exists(json_path):
                download_file(GITHUB_FILES["characters.json"], json_path)
                
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for entry in data:
                    file_id = entry.get('file_id', '').lower()
                    if file_id:
                        if file_id not in character_data:
                            character_data[file_id] = []
                        character_data[file_id].append({
                            'character': entry.get('character', ''),
                            'costume': entry.get('costume', ''),
                            'type': entry.get('type', 'idle').lower(),
                            'hashed_name': entry.get('hashed_name', ''),
                            'file_id': file_id
                        })
        except Exception as e:
            print(f"Error loading character data: {e}")
            return {}
        return character_data

    def get_character_display_info(self, folder_path, subfolder_name):
        """Get enhanced character info with special case handling"""
        folder_files = [f.lower() for f in os.listdir(folder_path)]
        
        # First check if this is a non-animation mod (no .skel/.json files)
        if not self.has_animation_files(folder_path):
            # Try to find matching illustration/NPC data first
            char_id = self.get_character_id_from_folder(folder_path)
            if char_id:
                # Check for exact match first
                if char_id.lower() in self.character_data:
                    entries = self.character_data[char_id.lower()]
                    return {
                        'character': entries[0]['character'],
                        'costume': entries[0]['costume'],
                        'type': entries[0]['type'].upper()
                    }
                
                # Check for partial matches (illust_special, specialIllust, etc.)
                for file_id, entries in self.character_data.items():
                    if file_id.lower() == char_id.lower():
                        return {
                            'character': entries[0]['character'],
                            'costume': entries[0]['costume'],
                            'type': entries[0]['type'].upper()
                        }
            
            return {
                'character': 'Illustration',
                'costume': subfolder_name,
                'type': 'IMAGE'
            }
        
        # Handle illust_dating cases (e.g., illust_dating1, illust_dating2, etc.)
        for file in folder_files:
            if 'illust_dating' in file:
                # Extract the full illust_datingX pattern
                match = re.search(r'(illust_dating\d+)', file)
                if match:
                    illust_id = match.group(1)
                    # Find matching entry in character data
                    for file_id, entries in self.character_data.items():
                        if file_id.lower() == illust_id.lower():
                            return {
                                'character': entries[0]['character'],
                                'costume': entries[0]['costume'],
                                'type': 'DATING SIM'
                            }
                    # Fallback if no exact match found
                    return {
                        'character': 'Illustration',
                        'costume': subfolder_name,
                        'type': 'DATING SIM'
                    }

        # Original character ID detection for animation files
        char_id = self.get_character_id_from_folder(folder_path)
        is_cutscene = any('cutscene' in f for f in folder_files)
        
        if not char_id:
            # Handle other special cases (NPC, story illustrations, etc.)
            if any(x in f for f in folder_files for x in ['npc', 'illust_', 'special']):
                # Try to find matching data in character.json
                for file in folder_files:
                    base_name = os.path.splitext(file)[0]
                    for file_id, entries in self.character_data.items():
                        if file_id.lower() == base_name.lower():
                            return {
                                'character': entries[0]['character'],
                                'costume': entries[0]['costume'],
                                'type': entries[0]['type'].upper()
                            }
                
                return {
                    'character': 'Special',
                    'costume': subfolder_name,
                    'type': 'ANIMATION'
                }
            return {
                'character': 'Unknown',
                'costume': '',
                'type': 'CUTSCENE' if is_cutscene else 'IDLE'
            }
        
        # Find all matching entries (case-insensitive)
        matching_entries = []
        for file_id, entries in self.character_data.items():
            if file_id.lower() == char_id.lower():
                matching_entries.extend(entries)
        
        if not matching_entries:
            # Check for special illustration cases
            if 'illust_' in char_id.lower() or 'special' in char_id.lower():
                for file in folder_files:
                    base_name = os.path.splitext(file)[0]
                    for file_id, entries in self.character_data.items():
                        if file_id.lower() == base_name.lower():
                            return {
                                'character': entries[0]['character'],
                                'costume': entries[0]['costume'],
                                'type': entries[0]['type'].upper()
                            }
            
            return {
                'character': 'Unknown',
                'costume': '',
                'type': 'CUTSCENE' if is_cutscene else 'IDLE'
            }
        
        # Find the most appropriate entry
        matched_entry = None
        for entry in matching_entries:
            if is_cutscene and entry.get('type', '').lower() == 'cutscene':
                matched_entry = entry
                break
            elif not is_cutscene and entry.get('type', '').lower() == 'idle':
                matched_entry = entry
                break
        
        if not matched_entry:
            matched_entry = matching_entries[0]
        
        return {
            'character': matched_entry.get('character', 'Unknown'),
            'costume': matched_entry.get('costume', ''),
            'type': matched_entry.get('type', 'CUTSCENE' if is_cutscene else 'IDLE').upper()
        }

    def format_display_name(self, name):
        """Simple formatter that preserves original names"""
        return name

    def browse_mods_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Select Mods Folder", os.path.expanduser("~"),
            QFileDialog.Option.ShowDirsOnly
        )
        if folder:
            self.folder_edit.setText(folder)
            self.settings["mods_folder"] = folder
            self.save_settings()
            self.load_mods()

    def folder_path_changed(self, text):
        self.settings["mods_folder"] = text
        self.save_settings()
        self.load_mods()

    def load_settings(self):
        default_settings = {
            "mods_folder": ""
        }
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading settings: {e}")
        return default_settings

    def save_settings(self):
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(self.settings, f, indent=4)
        except Exception as e:
            print(f"Error saving settings: {e}")

    def verify_mods_folder(self):
        if not self.settings.get("mods_folder") or not os.path.exists(self.settings["mods_folder"]):
            QMessageBox.information(
                self, "Select Mods Folder",
                "Please enter or browse your mods folder path",
                QMessageBox.StandardButton.Ok
            )
        else:
            self.load_mods()

    def load_mods(self):
        # Fix: Reset sorting to default before reloading to prevent refresh issues.
        self.table_widget.sortByColumn(-1, Qt.SortOrder.AscendingOrder)
        
        mods_folder = self.settings.get("mods_folder", "")
        self.table_widget.setRowCount(0)
        
        if mods_folder and os.path.exists(mods_folder):
            # First get all author folders
            author_folders = [f for f in os.listdir(mods_folder) 
                            if os.path.isdir(os.path.join(mods_folder, f)) and not f.startswith('.')]
            
            # Track maximum content widths for fixed columns
            max_author_width = 0
            max_character_width = 0
            max_type_width = 0
            max_status_width = 0
            
            # First pass: Calculate maximum content widths
            temp_font = self.table_widget.font()
            temp_fm = self.table_widget.fontMetrics()
            
            for author in author_folders:
                author_path = os.path.join(mods_folder, author)
                subfolders = [f for f in os.listdir(author_path) 
                             if os.path.isdir(os.path.join(author_path, f)) and not f.startswith('.')]
                
                for subfolder in subfolders:
                    subfolder_path = os.path.join(author_path, subfolder)
                    char_info = self.get_character_display_info(subfolder_path, subfolder)
                    
                    # Calculate required widths
                    author_width = temp_fm.horizontalAdvance(author) + 20  # + padding
                    char_width = temp_fm.horizontalAdvance(char_info['character']) + 20
                    type_width = temp_fm.horizontalAdvance(char_info['type']) + 20
                    status_width = temp_fm.horizontalAdvance("Active") + 20  # "Active" is longer than "Inactive"
                    
                    if author_width > max_author_width:
                        max_author_width = author_width
                    if char_width > max_character_width:
                        max_character_width = char_width
                    if type_width > max_type_width:
                        max_type_width = type_width
                    if status_width > max_status_width:
                        max_status_width = status_width
            
            # Second pass: Add rows with fixed column widths
            for author in sorted(author_folders):
                author_path = os.path.join(mods_folder, author)
                subfolders = [f for f in os.listdir(author_path) 
                             if os.path.isdir(os.path.join(author_path, f)) and not f.startswith('.')]
                
                for subfolder in sorted(subfolders):
                    subfolder_path = os.path.join(author_path, subfolder)
                    self.add_mod_row(author, subfolder, subfolder_path)
            
            # Set fixed column widths
            self.table_widget.setColumnWidth(0, max_author_width)    # Author
            self.table_widget.setColumnWidth(1, max_character_width) # Character
            self.table_widget.setColumnWidth(3, max_type_width)      # Type
            self.table_widget.setColumnWidth(4, max_status_width)    # Status
        
    def add_mod_row(self, author, subfolder, folder_path):
        row = self.table_widget.rowCount()
        self.table_widget.insertRow(row)
        
        char_info = self.get_character_display_info(folder_path, subfolder)
        
        # Author column
        author_item = QTableWidgetItem(self.format_display_name(author))
        author_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Character column
        char_item = QTableWidgetItem(char_info['character'])
        char_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Costume column
        costume_item = QTableWidgetItem(char_info['costume'])
        costume_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Type column
        type_item = QTableWidgetItem(char_info['type'])
        type_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Status column
        status_text = "Active" if self.is_mod_active(folder_path) else "Inactive"
        status_item = QTableWidgetItem(status_text)
        status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        status_item.setForeground(QColor('#4ec9b0') if status_text == "Active" else QColor('#f48771'))
        
        # Set all items
        self.table_widget.setItem(row, 0, author_item)
        self.table_widget.setItem(row, 1, char_item)
        self.table_widget.setItem(row, 2, costume_item)
        self.table_widget.setItem(row, 3, type_item)
        self.table_widget.setItem(row, 4, status_item)
        
        # Actions column
        action_widget = QWidget()
        action_layout = QHBoxLayout(action_widget)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(5)
        
        # Preview button
        preview_btn = QPushButton("Preview")
        preview_btn.setFixedWidth(80)
        preview_btn.clicked.connect(lambda _, p=folder_path: self.preview_folder(p))
        action_layout.addWidget(preview_btn)
        
        # Activate/Deactivate button
        activate_btn = QPushButton("Activate" if not self.is_mod_active(folder_path) else "Deactivate")
        activate_btn.setFixedWidth(80)
        activate_btn.setProperty("folder_path", folder_path)
        activate_btn.clicked.connect(self.toggle_mod_activation)
        action_layout.addWidget(activate_btn)
        
        # Open Folder button
        open_btn = QPushButton("Open Folder")
        open_btn.setFixedWidth(80)
        open_btn.setProperty("folder_path", folder_path)
        open_btn.clicked.connect(self.open_mod_folder)
        action_layout.addWidget(open_btn)
        
        self.table_widget.setCellWidget(row, 5, action_widget)

    def filter_mods(self):
        search_text = self.search_edit.text().lower()

        if not search_text:
            # Show all rows if search is empty
            for row in range(self.table_widget.rowCount()):
                self.table_widget.setRowHidden(row, False)
            return

        for row in range(self.table_widget.rowCount()):
            author_item = self.table_widget.item(row, 0)
            character_item = self.table_widget.item(row, 1)
            costume_item = self.table_widget.item(row, 2)
            type_item = self.table_widget.item(row, 3)
            status_item = self.table_widget.item(row, 4)

            # Ensure all items exist before attempting to read text from them
            if not all([author_item, character_item, costume_item, type_item, status_item]):
                continue

            # Concatenate all searchable text into one string for easy searching
            row_text = (
                author_item.text().lower() +
                character_item.text().lower() +
                costume_item.text().lower() +
                type_item.text().lower() +
                status_item.text().lower()
            )
            
            matches = search_text in row_text
            self.table_widget.setRowHidden(row, not matches)

    def clear_search(self):
        self.search_edit.clear()
        self.filter_mods()

    def toggle_mod_activation(self):
        btn = self.sender()
        if not btn:
            return
            
        folder_path = btn.property("folder_path")
        if not folder_path:
            return
            
        modfile_path = self.get_modfile_path(folder_path)
        if not modfile_path:
            QMessageBox.warning(self, "Error", "No .modfile or .mod file found in this mod folder", QMessageBox.StandardButton.Ok)
            return
            
        try:
            if modfile_path.lower().endswith('.modfile'):
                # Deactivate the mod
                new_path = modfile_path[:-8] + '.mod'
                os.rename(modfile_path, new_path)
                btn.setText("Activate")
            else:
                # Activate the mod
                new_path = modfile_path[:-4] + '.modfile'
                os.rename(modfile_path, new_path)
                btn.setText("Deactivate")
                
            # Update the status in the table
            for row in range(self.table_widget.rowCount()):
                if self.table_widget.cellWidget(row, 5) == btn.parentWidget():
                    status_item = QTableWidgetItem("Active" if btn.text() == "Deactivate" else "Inactive")
                    status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    if btn.text() == "Deactivate":
                        status_item.setForeground(QColor('#4ec9b0'))  # Teal for active
                    else:
                        status_item.setForeground(QColor('#f48771'))  # Salmon for inactive
                    self.table_widget.setItem(row, 4, status_item)
                    break
                        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to toggle mod activation: {str(e)}", QMessageBox.StandardButton.Ok)

    def open_mod_folder(self):
        btn = self.sender()
        if not btn:
            return
            
        folder_path = btn.property("folder_path")
        if not folder_path:
            return
            
        try:
            if sys.platform == 'win32':
                os.startfile(folder_path)
            elif sys.platform == 'darwin':
                subprocess.run(['open', folder_path])
            else:
                subprocess.run(['xdg-open', folder_path])
        except Exception as e:
            QMessageBox.critical(
                self, "Error",
                f"Failed to open folder:\n{str(e)}",
                QMessageBox.StandardButton.Ok
            )

    def preview_folder(self, folder_path):
        skeleton_files = []
        json_files = []
        png_files = []
        
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                lower_file = file.lower()
                file_path = os.path.join(root, file)
                if lower_file.endswith('.skel'):
                    skeleton_files.append(file_path)
                elif lower_file.endswith('.json'):
                    json_files.append(file_path)
                elif lower_file.endswith('.png'):
                    png_files.append(file_path)
        
        for skel_file in skeleton_files:
            self.preview_animation(skel_file)
            return
        
        for json_file in json_files:
            try:
                for encoding in ['utf-8', 'utf-16', 'latin-1', 'cp1252']:
                    try:
                        with open(json_file, 'r', encoding=encoding) as f:
                            data = json.load(f)
                            if 'skeleton' in data or 'bones' in data:
                                self.preview_animation(json_file)
                                return
                    except UnicodeDecodeError:
                        continue
            except Exception as e:
                print(f"Error processing JSON file: {e}")
        
        if png_files:
            self.open_image(png_files[0])
            return
        
        QMessageBox.warning(
            self, "No Animation Files",
            f"No valid .skel, .json, or .png files found in {os.path.basename(folder_path)}",
            QMessageBox.StandardButton.Ok
        )

    def open_image(self, image_path):
        try:
            if sys.platform == 'win32':
                os.startfile(image_path)
            elif sys.platform == 'darwin':
                subprocess.run(['open', image_path])
            else:
                subprocess.run(['xdg-open', image_path])
        except Exception as e:
            QMessageBox.critical(
                self, "Error",
                f"Failed to open image:\n{str(e)}",
                QMessageBox.StandardButton.Ok
            )

    def preview_animation(self, animation_path):
        if not os.path.exists(self.viewer_controller.viewer_path):
            QMessageBox.critical(
                self, "Error",
                "Spine viewer executable not found!\n"
                f"Expected path: {self.viewer_controller.viewer_path}",
                QMessageBox.StandardButton.Ok
            )
            return
        
        if not self.viewer_controller.launch_viewer(animation_path):
            QMessageBox.critical(
                self, "Error",
                "Failed to launch Spine viewer",
                QMessageBox.StandardButton.Ok
            )

    def closeEvent(self, event):
        self.viewer_controller.close_viewer()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    icon_path = os.path.join(get_base_path(), "icon.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    viewer = SpineViewer()
    viewer.show()
    sys.exit(app.exec())