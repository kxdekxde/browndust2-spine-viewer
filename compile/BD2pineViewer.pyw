import os
import sys
import json
import csv
import subprocess
import shutil
import tempfile
import UnityPy
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
    """Get the base path for the application, handling both running as script and compiled exe"""
    if getattr(sys, 'frozen', False):
        # Running as compiled exe
        return os.path.dirname(sys.executable)
    else:
        # Running as script
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
            # Get local file hash
            local_hash = calculate_file_hash(local_path)
            
            # Get remote file hash (download to temp file)
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

def ensure_viewer_files(app):
    # Create the Skeleton Viewer directory in the same folder as the executable or script
    viewer_dir = os.path.join(get_base_path(), "Skeleton Viewer")
    os.makedirs(viewer_dir, exist_ok=True)
    
    required_files = {
        "skeletonViewer-4.2.40.jar": "https://en.esotericsoftware.com/files/skeletonViewer-4.2.40.jar",
        "skeletonViewer-4.1.24.jar": "https://en.esotericsoftware.com/files/skeletonViewer-4.1.24.jar"
    }
    
    missing_files = []
    for filename, url in required_files.items():
        filepath = os.path.join(viewer_dir, filename)
        if not os.path.exists(filepath):
            missing_files.append((filename, url, filepath))
    
    if missing_files:
        msg = QMessageBox()
        msg.setWindowTitle("Downloading Required Files")
        msg.setText("Downloading necessary Spine viewer files...")
        msg.setStandardButtons(QMessageBox.StandardButton.NoButton)
        msg.show()
        
        app.processEvents()
        
        for filename, url, filepath in missing_files:
            msg.setInformativeText(f"Downloading {filename}...")
            app.processEvents()
            
            if not download_file(url, filepath):
                msg.hide()
                QMessageBox.critical(
                    None, 
                    "Download Error",
                    f"Failed to download required file: {filename}\nPlease check your internet connection.",
                    QMessageBox.StandardButton.Ok
                )
                return False
        
        msg.hide()
    
    return True

class AssetExtractor(QThread):
    progress_signal = pyqtSignal(int, str)
    finished_signal = pyqtSignal(str, str, str)

    def __init__(self, bundle_path, spine_assets_dir):
        super().__init__()
        self.bundle_path = bundle_path
        self.spine_assets_dir = spine_assets_dir
        self.cancelled = False

    def run(self):
        try:
            bundle_name = os.path.splitext(os.path.basename(self.bundle_path))[0]
            output_dir = os.path.join(self.spine_assets_dir, bundle_name)

            if os.path.exists(output_dir):
                shutil.rmtree(output_dir)
            os.makedirs(output_dir, exist_ok=True)

            self.progress_signal.emit(10, "Loading bundle...")
            env = UnityPy.load(self.bundle_path)
            self.progress_signal.emit(20, "Scanning assets...")

            spine_assets = {'skel': None, 'atlas': None, 'textures': []}
            objects = list(env.objects)
            for i, obj in enumerate(objects):
                if self.cancelled:
                    break
                progress = 20 + int((i / len(objects)) * 70)
                self.progress_signal.emit(progress, f"Processing {obj.type.name}...")

                try:
                    data = obj.read()

                    if obj.type.name == "Texture2D":
                        texture_name = f"{data.m_Name}.png"
                        texture_path = os.path.join(output_dir, texture_name)
                        data.image.save(texture_path)
                        spine_assets['textures'].append(texture_path)

                    elif obj.type.name == "TextAsset":
                        asset_name = data.m_Name
                        asset_path = os.path.join(output_dir, asset_name)

                        if asset_name.endswith('.skel') or '.skel.' in asset_name:
                            spine_assets['skel'] = asset_path
                        elif asset_name.endswith('.atlas') or '.atlas.' in asset_name:
                            spine_assets['atlas'] = asset_path

                        with open(asset_path, "wb") as f:
                            f.write(data.m_Script.encode("utf-8", "surrogateescape"))

                except Exception as e:
                    print(f"Error processing asset: {e}")

            if self.cancelled:
                shutil.rmtree(output_dir)
                self.finished_signal.emit(None, None, "Extraction cancelled")
            else:
                self.progress_signal.emit(95, "Finalizing...")
                if spine_assets['skel']:
                    self.finished_signal.emit(
                        output_dir,
                        spine_assets['skel'],
                        "Extraction complete"
                    )
                else:
                    self.finished_signal.emit(
                        output_dir,
                        None,
                        "No Spine skeleton file found"
                    )
                self.progress_signal.emit(100, "Done")

        except Exception as e:
            self.finished_signal.emit(None, None, f"Extraction failed: {str(e)}")

    def cancel(self):
        self.cancelled = True

class SpineViewer(QWidget):
    def __init__(self):
        super().__init__()
        self.settings_file = os.path.join(get_base_path(), "spine_viewer_settings.json")
        self.setWindowTitle("Brown Dust II Spine Viewer")
        self.setGeometry(100, 100, 1000, 600)
        self.viewer_processes = []

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

        self.current_extraction = None
        self.progress_dialog = None

        self.verify_mods_folder()
        self.folder_edit.textChanged.connect(self.folder_path_changed)

    def get_character_id_from_folder(self, folder_path):
        """Scan folder recursively for .skel/.json files and extract character ID (case-insensitive)"""
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if file.lower().endswith('.skel') or file.lower().endswith('.json'):
                    filename = os.path.splitext(file)[0]
                    # Handle cutscene files (case-insensitive)
                    if filename.lower().startswith('cutscene_'):
                        return filename[9:].lower()  # Remove 'cutscene_' prefix and convert to lowercase
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
                # Try to download if missing
                download_file(GITHUB_FILES["BD2 Characters - Characters.csv"], csv_path)
                
            with open(csv_path, newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                current_character = ""
                for row in reader:
                    if row['CHARACTER']:
                        current_character = row['CHARACTER']
                    
                    if row['ID']:  # Only process rows with ID
                        # Create display name with character and costume
                        display_name = current_character
                        if row['COSTUME']:
                            display_name += f" ({row['COSTUME']})"
                        
                        # Map the ID (case-insensitive)
                        character_map[row['ID'].lower()] = display_name
                        
                        # Also map cutscene version if exists (case-insensitive)
                        if row['CUTSCENE']:
                            cutscene_id = f"cutscene_{row['ID']}".lower()
                            character_map[cutscene_id] = f"{display_name} (Cutscene)"
        except Exception as e:
            print(f"Error loading character map: {e}")
        return character_map

    def format_display_name(self, name):
        return name.replace('_', ' ')

    def get_spine_assets_dir(self):
        spine_dir = os.path.join(tempfile.gettempdir(), "SpineAssets")
        os.makedirs(spine_dir, exist_ok=True)
        return spine_dir

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
            "mods_folder": "",
            "zulu_path": r"C:\\Program Files\\Zulu\\zulu-21\\bin\\javaw.exe"
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

    def detect_spine_version(self, skel_path):
        try:
            with open(skel_path, 'rb') as f:
                header = f.read(100).decode('ascii', errors='ignore')
                version_match = re.search(r'(\d+\.\d+)\.\d+', header)
                if version_match:
                    return version_match.group(1)
        except Exception as e:
            print(f"Error detecting Spine version: {e}")
        return None

    def detect_spine_version_from_json(self, json_path):
        try:
            # Try multiple encodings to read the JSON file
            for encoding in ['utf-8', 'utf-16', 'latin-1', 'cp1252']:
                try:
                    with open(json_path, 'r', encoding=encoding) as f:
                        data = json.load(f)
                        if 'skeleton' in data and 'spine' in data['skeleton']:
                            version_str = data['skeleton']['spine']
                            version_match = re.search(r'(\d+\.\d+)\.\d+', version_str)
                            if version_match:
                                return version_match.group(1)
                    break  # Successfully read the file
                except UnicodeDecodeError:
                    continue  # Try next encoding
        except Exception as e:
            print(f"Error detecting Spine version from JSON: {e}")
        return None

    def get_viewer_for_version(self, spine_version):
        viewer_dir = os.path.join(get_base_path(), "Skeleton Viewer")
        if not os.path.exists(viewer_dir):
            os.makedirs(viewer_dir, exist_ok=True)
            
        available_versions = []
        for file in sorted(os.listdir(viewer_dir)):
            if file.startswith("skeletonViewer-") and file.endswith(".jar"):
                version_num = file[14:-4]
                available_versions.append((version_num, os.path.join(viewer_dir, file)))
        
        if not available_versions:
            return None
            
        if not spine_version:
            return available_versions[-1][1]
        
        for ver_num, path in available_versions:
            if ver_num.startswith(spine_version):
                return path
        
        try:
            target_major, target_minor = map(int, spine_version.split('.'))
            best_match = None
            best_diff = float('inf')
            
            for ver_num, path in available_versions:
                try:
                    parts = ver_num.split('.')
                    if len(parts) >= 2:
                        major = int(parts[0])
                        minor = int(parts[1])
                        diff = abs(major - target_major) * 10 + abs(minor - target_minor)
                        
                        if diff < best_diff:
                            best_diff = diff
                            best_match = path
                except:
                    continue
            
            return best_match if best_match else available_versions[-1][1]
        except:
            return available_versions[-1][1]

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

        # Get character ID from skeleton files in folder (case-insensitive)
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
            
        # Keep spaces in folder names
        new_folder_name = new_name  
        parent_dir = os.path.dirname(original_path)
        new_path = os.path.join(parent_dir, new_folder_name)
        
        try:
            os.rename(original_path, new_path)
            name_edit.setProperty("original_path", new_path)
            
            # Update character name display after rename (case-insensitive)
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
        
        # Search recursively for files
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
        
        # Try .skel files first
        for skel_file in skeleton_files:
            self.preview_animation(skel_file)
            return
        
        # Then try .json files
        for json_file in json_files:
            try:
                # Try multiple encodings to read the JSON file
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
        
        # If we have PNG files but no skeleton files, open the first PNG
        if png_files:
            self.open_image(png_files[0])
            return
        
        # If we get here, no valid files were found
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
            else:  # Linux and other Unix-like systems
                subprocess.run(['xdg-open', image_path])
        except Exception as e:
            QMessageBox.critical(
                self, "Error",
                f"Failed to open image:\n{str(e)}",
                QMessageBox.StandardButton.Ok
            )

    def preview_animation(self, animation_path):
        # Determine file type and detect version accordingly
        if animation_path.lower().endswith('.json'):
            spine_version = self.detect_spine_version_from_json(animation_path)
        else:
            spine_version = self.detect_spine_version(animation_path)
        
        viewer_path = self.get_viewer_for_version(spine_version)

        if not viewer_path:
            QMessageBox.critical(
                self, "Error",
                "No skeleton viewer found in 'Skeleton Viewer' folder",
                QMessageBox.StandardButton.Ok
            )
            return

        zulu_javaw = self.settings.get("zulu_path", "javaw")

        try:
            if sys.platform == 'win32':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                subprocess.Popen(
                    [zulu_javaw, "-jar", viewer_path, animation_path],
                    creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
                    startupinfo=startupinfo
                )
            else:
                subprocess.Popen(
                    [zulu_javaw, "-jar", viewer_path, animation_path],
                    start_new_session=True
                )
            
            QTimer.singleShot(500, self.bring_to_front)
            
        except Exception as e:
            QMessageBox.critical(
                self, "Error",
                f"Failed to launch viewer:\n{str(e)}",
                QMessageBox.StandardButton.Ok
            )

    def extract_and_preview(self, bundle_path):
        spine_assets_dir = self.get_spine_assets_dir()
        self.progress_dialog = QProgressDialog(
            f"Extracting assets from {os.path.basename(bundle_path)}...",
            "Cancel", 0, 100, self)
        self.progress_dialog.setWindowTitle("Extracting Assets")
        self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress_dialog.setAutoReset(False)
        self.progress_dialog.canceled.connect(self.cancel_extraction)

        self.current_extraction = AssetExtractor(bundle_path, spine_assets_dir)
        self.current_extraction.progress_signal.connect(self.update_progress)
        self.current_extraction.finished_signal.connect(self.extraction_complete)
        self.current_extraction.start()

        self.progress_dialog.show()

    def update_progress(self, value, message):
        if self.progress_dialog:
            self.progress_dialog.setValue(value)
            self.progress_dialog.setLabelText(message)

    def cancel_extraction(self):
        if self.current_extraction and self.current_extraction.isRunning():
            self.current_extraction.cancel()
        if self.progress_dialog:
            self.progress_dialog.close()
        self.progress_dialog = None

    def extraction_complete(self, output_dir, skel_path, message):
        if self.progress_dialog:
            self.progress_dialog.close()
        if skel_path:
            self.preview_animation(skel_path)
        else:
            if output_dir:
                QMessageBox.warning(
                    self, "Extraction Complete",
                    f"{message}\n\nExtracted assets to:\n{output_dir}",
                    QMessageBox.StandardButton.Ok
                )
            else:
                QMessageBox.critical(
                    self, "Extraction Failed",
                    message,
                    QMessageBox.StandardButton.Ok
                )

    def bring_to_front(self):
        self.raise_()
        self.activateWindow()
        self.showNormal()

    def closeEvent(self, event):
        shutil.rmtree(self.get_spine_assets_dir(), ignore_errors=True)
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    icon_path = os.path.join(get_base_path(), "icon.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    if not ensure_viewer_files(app):
        sys.exit(1)
    
    viewer = SpineViewer()
    viewer.show()
    sys.exit(app.exec())