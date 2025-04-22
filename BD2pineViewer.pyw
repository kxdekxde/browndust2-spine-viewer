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
    QFileDialog, QMessageBox, QProgressDialog
)
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer

# GitHub configuration
GITHUB_FILES = {
    "BD2 Characters - Characters.csv": "https://raw.githubusercontent.com/kxdekxde/browndust2-repacker/main/AddressablesJSON/BD2%20Characters%20-%20Characters.csv"
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
        self.setWindowTitle("Brown Dust II Spine Viewer")
        self.setGeometry(100, 100, 1000, 600)
        self.viewer_controller = SpineViewerController()

        # Check for updates before loading anything
        self.check_github_updates()

        self.character_map = self.load_character_map()
        self.settings = self.load_settings()

        self.setStyleSheet("""
            QWidget { background-color: #252525; color: white; }
            QPushButton { background-color: #444; border: 1px solid #555; padding: 5px; min-width: 80px; }
            QPushButton:hover { background-color: #555; }
            QScrollArea { border: none; }
            QLineEdit { background-color: #333; color: white; padding: 5px; border: 1px solid #555; }
            QProgressDialog { background-color: #252525; color: white; }
            QProgressBar { background-color: #333; color: white; border: 1px solid #555; text-align: center; }
        """)

        main_layout = QVBoxLayout()

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

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)

        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.scroll_area.setWidget(self.scroll_content)
        main_layout.addWidget(self.scroll_area)

        self.setLayout(main_layout)

        self.verify_mods_folder()
        self.folder_edit.textChanged.connect(self.folder_path_changed)

    def get_character_id_from_folder(self, folder_path):
        """Scan folder recursively for .skel/.json files and extract character ID (case-insensitive)"""
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if file.lower().endswith('.skel') or file.lower().endswith('.json'):
                    filename = os.path.splitext(file)[0]
                    if filename.lower().startswith('cutscene_'):
                        return filename[9:].lower()
                    return filename.lower()
        return None

    def check_github_updates(self):
        """Check for updates from GitHub and prompt user"""
        try:
            if check_for_updates():
                reply = QMessageBox.question(
                    self, 'Update Available',
                    'New updates are available on GitHub. Would you like to download them now?',
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    update_files_from_github()
                    QMessageBox.information(
                        self, 'Update Complete',
                        'Files have been updated successfully.',
                        QMessageBox.StandardButton.Ok
                    )
        except Exception as e:
            print(f"Error checking for updates: {e}")

    def load_character_map(self):
        character_map = {}
        try:
            csv_path = os.path.join(get_base_path(), "BD2 Characters - Characters.csv")
            if not os.path.exists(csv_path):
                download_file(GITHUB_FILES["BD2 Characters - Characters.csv"], csv_path)
                
            with open(csv_path, newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                current_character = ""
                for row in reader:
                    if row['CHARACTER']:
                        current_character = row['CHARACTER']
                    
                    if row['ID']:
                        display_name = current_character
                        if row['COSTUME']:
                            display_name += f" ({row['COSTUME']})"
                        
                        character_map[row['ID'].lower()] = display_name
                        
                        if row['CUTSCENE']:
                            cutscene_id = f"cutscene_{row['ID']}".lower()
                            character_map[cutscene_id] = f"{display_name} (Cutscene)"
        except Exception as e:
            print(f"Error loading character map: {e}")
        return character_map

    def format_display_name(self, name):
        return name.replace('_', ' ')

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
                "Please enter or browse to your mods folder path",
                QMessageBox.StandardButton.Ok
            )
        else:
            self.load_mods()

    def load_mods(self):
        mods_folder = self.settings.get("mods_folder", "")
        while self.scroll_layout.count():
            item = self.scroll_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if mods_folder and os.path.exists(mods_folder):
            for item in sorted(os.listdir(mods_folder)):
                item_path = os.path.join(mods_folder, item)
                if not os.path.isdir(item_path) or item.startswith('.'):
                    continue
                self.add_mod_item(item, item_path)

    def add_mod_item(self, folder_name, folder_path):
        item_widget = QWidget()
        item_layout = QHBoxLayout(item_widget)

        preview_btn = QPushButton("Preview")
        preview_btn.setFixedWidth(100)
        preview_btn.clicked.connect(lambda _, p=folder_path: self.preview_folder(p))
        item_layout.addWidget(preview_btn)

        self.name_edit = QLineEdit(self.format_display_name(folder_name))
        self.name_edit.setStyleSheet("color: white;")
        self.name_edit.setMinimumWidth(300)
        self.name_edit.setProperty("original_path", folder_path)
        item_layout.addWidget(self.name_edit)

        character_id = self.get_character_id_from_folder(folder_path)
        character_name = self.character_map.get(character_id, "Unknown")
        
        character_label = QLabel(character_name)
        character_label.setStyleSheet("color: #999;")
        character_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        character_label.setMinimumWidth(150)
        item_layout.addWidget(character_label)

        rename_btn = QPushButton("Rename")
        rename_btn.setFixedWidth(100)
        rename_btn.clicked.connect(self.rename_folder)
        item_layout.addWidget(rename_btn)

        self.scroll_layout.addWidget(item_widget)

    def rename_folder(self):
        btn = self.sender()
        if not btn:
            return
            
        item_widget = btn.parentWidget()
        if not item_widget:
            return
            
        name_edit = None
        original_path = None
        for child in item_widget.children():
            if isinstance(child, QLineEdit):
                name_edit = child
                original_path = child.property("original_path")
                break
                
        if not name_edit or not original_path:
            return
            
        new_name = name_edit.text().strip()
        if not new_name:
            QMessageBox.warning(self, "Error", "Name cannot be empty", QMessageBox.StandardButton.Ok)
            return
            
        new_folder_name = new_name  
        parent_dir = os.path.dirname(original_path)
        new_path = os.path.join(parent_dir, new_folder_name)
        
        try:
            os.rename(original_path, new_path)
            name_edit.setProperty("original_path", new_path)
            
            character_id = self.get_character_id_from_folder(new_path)
            character_name = self.character_map.get(character_id, "Unknown")
            
            for child in item_widget.children():
                if isinstance(child, QLabel) and child.text() not in ["Preview", "Rename"]:
                    child.setText(character_name)
                    break
                    
            QMessageBox.information(self, "Success", "Folder renamed successfully", QMessageBox.StandardButton.Ok)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to rename folder: {str(e)}", QMessageBox.StandardButton.Ok)

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
        if not self.viewer_controller.launch_viewer(animation_path):
            QMessageBox.critical(
                self, "Error",
                "Failed to launch Spine viewer",
                QMessageBox.StandardButton.Ok
            )
        else:
            QTimer.singleShot(500, self.bring_to_front)

    def bring_to_front(self):
        self.raise_()
        self.activateWindow()
        self.showNormal()

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