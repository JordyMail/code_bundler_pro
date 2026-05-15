#!/usr/bin/env python3
"""
Code Bundler Pro - GUI Application
Fitur lengkap: drag & drop folder, exclude otomatis, token counter, save preference
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import List, Set, Dict
import threading

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QListWidget, QListWidgetItem, QLabel, QFileDialog,
    QMessageBox, QProgressBar, QCheckBox, QGroupBox, QTextEdit,
    QSplitter, QLineEdit, QComboBox, QSpinBox
)
from PyQt5.QtCore import Qt, QMimeData, QThread, pyqtSignal, QSettings
from PyQt5.QtGui import QDragEnterEvent, QDropEvent, QFont, QColor, QIcon

try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False
    print("Warning: tiktoken tidak terinstall. Token count akan menggunakan estimasi kasar.")

# ============== KONFIGURASI ==============
CONFIG_FILE = ".codebundle.json"
DEFAULT_EXCLUDE_DIRS = {
    'node_modules', '.git', '__pycache__', 'venv', 'env', 
    'dist', 'build', '.vscode', '.idea', 'logs', 'tmp',
    'temp', 'cache', '.next', 'out', '.nuxt'
}

# Ekstensi file yang didukung (bisa diedit user nanti)
DEFAULT_EXTENSIONS = {
    '.py', '.js', '.ts', '.jsx', '.tsx', '.html', '.htm', '.css', '.scss', '.sass',
    '.json', '.xml', '.yaml', '.yml', '.md', '.txt', '.sql', '.sh', '.bat', '.ps1',
    '.java', '.cpp', '.c', '.h', '.cs', '.go', '.rs', '.php', '.rb', '.pl', '.lua',
    '.env', '.gitignore', '.dockerignore', '.ini', '.cfg', '.conf', '.toml',
    '.vue', '.svelte', '.astro', '.sqlite', '.graphql', '.proto', '.kt', '.kts',
    '.swift', '.m', '.mm', '.scala', '.clj', '.cljs', '.r', '.R', '.lua'
}

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

# ============== UTILITY FUNCTIONS ==============
def estimate_token_count(text: str) -> int:
    """Estimasi jumlah token (priority: tiktoken -> fallback kasar)"""
    if TIKTOKEN_AVAILABLE:
        try:
            enc = tiktoken.get_encoding("cl100k_base")  # sama dengan ChatGPT/GPT-4
            return len(enc.encode(text))
        except:
            pass
    # Fallback: perkiraan kasar (1 token ≈ 4 karakter)
    return len(text) // 4

class FileScanner(QThread):
    """Thread untuk scanning file tanpa freeze GUI"""
    progress = pyqtSignal(int, int)  # current, total
    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    
    def __init__(self, root_dir: str, exclude_dirs: Set[str], extensions: Set[str]):
        super().__init__()
        self.root_dir = Path(root_dir)
        self.exclude_dirs = exclude_dirs
        self.extensions = extensions
        
    def should_exclude(self, path: Path) -> bool:
        """Cek apakah path harus di-exclude"""
        parts = path.parts
        for exclude in self.exclude_dirs:
            if exclude in parts:
                return True
        return False
    
    def run(self):
        try:
            files = []
            all_files = list(self.root_dir.rglob("*"))
            total = len(all_files)
            
            for idx, filepath in enumerate(all_files):
                if idx % 10 == 0:
                    self.progress.emit(idx, total)
                
                if not filepath.is_file():
                    continue
                
                # Exclude folder otomatis
                if self.should_exclude(filepath):
                    continue
                
                # Cek ekstensi
                if filepath.suffix.lower() in self.extensions:
                    # Cek ukuran
                    size = filepath.stat().st_size
                    if size <= MAX_FILE_SIZE:
                        files.append(filepath)
            
            self.progress.emit(total, total)
            self.finished.emit(files)
        except Exception as e:
            self.error.emit(str(e))

# ============== MAIN GUI WINDOW ==============
class CodeBundlerGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_dir = Path.cwd()
        self.all_files: List[Path] = []
        self.selected_files: Set[Path] = set()
        self.exclude_dirs = set(DEFAULT_EXCLUDE_DIRS)
        self.extensions = set(DEFAULT_EXTENSIONS)
        self.scanner_thread = None
        
        self.init_ui()
        self.load_preferences()
        
    def init_ui(self):
        self.setWindowTitle("Code Bundler Pro - Copy All Files to One TXT")
        self.setGeometry(100, 100, 1200, 800)
        self.setAcceptDrops(True)
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        
        # ===== DRAG & DROP AREA =====
        drag_group = QGroupBox("📂 1. Drag & Drop Folder Project atau Klik 'Browse'")
        drag_layout = QVBoxLayout(drag_group)
        
        self.drop_label = QLabel("📁 Drag & Drop folder project ke sini\n\nAtau klik tombol Browse")
        self.drop_label.setAlignment(Qt.AlignCenter)
        self.drop_label.setStyleSheet("""
            QLabel {
                border: 2px dashed #aaa;
                border-radius: 10px;
                padding: 20px;
                background-color: #f8f9fa;
                font-size: 14px;
            }
            QLabel:hover {
                border-color: #4CAF50;
                background-color: #f0f8f0;
            }
        """)
        self.drop_label.setMinimumHeight(100)
        
        browse_btn = QPushButton("📁 Browse Folder")
        browse_btn.clicked.connect(self.browse_folder)
        
        drag_layout.addWidget(self.drop_label)
        drag_layout.addWidget(browse_btn, 0, Qt.AlignCenter)
        
        # ===== FILTER OPTIONS =====
        filter_group = QGroupBox("⚙️ 2. Filter Options")
        filter_layout = QVBoxLayout(filter_group)
        
        # Exclude folders
        exclude_layout = QHBoxLayout()
        exclude_layout.addWidget(QLabel("Exclude Folders:"))
        self.exclude_input = QLineEdit(",".join(sorted(self.exclude_dirs)))
        self.exclude_input.textChanged.connect(self.update_exclude_dirs)
        exclude_layout.addWidget(self.exclude_input)
        filter_layout.addLayout(exclude_layout)
        
        # File extensions
        ext_layout = QHBoxLayout()
        ext_layout.addWidget(QLabel("File Extensions:"))
        self.ext_input = QLineEdit(",".join(sorted(self.extensions)))
        self.ext_input.textChanged.connect(self.update_extensions)
        ext_layout.addWidget(self.ext_input)
        filter_layout.addLayout(ext_layout)
        
        # Size limit
        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel("Max File Size (MB):"))
        self.size_spin = QSpinBox()
        self.size_spin.setRange(0, 100)
        self.size_spin.setValue(5)
        self.size_spin.valueChanged.connect(self.update_size_limit)
        size_layout.addWidget(self.size_spin)
        size_layout.addStretch()
        filter_layout.addLayout(size_layout)
        
        # ===== FILE LIST =====
        files_group = QGroupBox("📄 3. Pilih File yang Akan Dibundle")
        files_layout = QVBoxLayout(files_group)
        
        # Buttons untuk seleksi
        select_btns_layout = QHBoxLayout()
        select_all_btn = QPushButton("✅ Select All")
        select_all_btn.clicked.connect(self.select_all_files)
        deselect_all_btn = QPushButton("❌ Deselect All")
        deselect_all_btn.clicked.connect(self.deselect_all_files)
        refresh_btn = QPushButton("🔄 Refresh Files")
        refresh_btn.clicked.connect(self.refresh_files)
        
        select_btns_layout.addWidget(select_all_btn)
        select_btns_layout.addWidget(deselect_all_btn)
        select_btns_layout.addWidget(refresh_btn)
        select_btns_layout.addStretch()
        files_layout.addLayout(select_btns_layout)
        
        self.file_list = QListWidget()
        self.file_list.setSelectionMode(QListWidget.MultiSelection)
        self.file_list.itemChanged.connect(self.on_item_changed)
        files_layout.addWidget(self.file_list)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.hide()
        files_layout.addWidget(self.progress_bar)
        
        # ===== OUTPUT & TOKEN =====
        output_group = QGroupBox("📝 4. Output & Token Info")
        output_layout = QVBoxLayout(output_group)
        
        # Token info
        token_info_layout = QHBoxLayout()
        self.token_label = QLabel("📊 Token estimasi: 0 tokens (0 files selected)")
        self.token_label.setFont(QFont("Monospace", 10))
        token_info_layout.addWidget(self.token_label)
        token_info_layout.addStretch()
        output_layout.addLayout(token_info_layout)
        
        # Output file name
        output_name_layout = QHBoxLayout()
        output_name_layout.addWidget(QLabel("Output File:"))
        self.output_name = QLineEdit("bundle_for_ai.txt")
        output_name_layout.addWidget(self.output_name)
        output_layout.addLayout(output_name_layout)
        
        # Bundle button
        self.bundle_btn = QPushButton("🚀 BUNDLE SELECTED FILES")
        self.bundle_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.bundle_btn.clicked.connect(self.bundle_files)
        output_layout.addWidget(self.bundle_btn)
        
        # ===== STATUS BAR =====
        self.statusBar().showMessage("Ready. Drag & drop folder untuk memulai.")
        
        # Layout utama
        main_layout.addWidget(drag_group)
        main_layout.addWidget(filter_group)
        
        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(files_group)
        splitter.addWidget(output_group)
        splitter.setSizes([500, 200])
        main_layout.addWidget(splitter)
        
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            
    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            folder_path = urls[0].toLocalFile()
            if os.path.isdir(folder_path):
                self.load_folder(folder_path)
            else:
                QMessageBox.warning(self, "Error", "Harap drop FOLDER, bukan file.")
    
    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Pilih Folder Project")
        if folder:
            self.load_folder(folder)
    
    def load_folder(self, folder_path: str):
        self.current_dir = Path(folder_path)
        self.statusBar().showMessage(f"Loading folder: {folder_path}")
        self.drop_label.setText(f"📁 {folder_path}\n\nMemproses...")
        
        # Start scanner thread
        self.scanner_thread = FileScanner(
            folder_path, 
            self.exclude_dirs, 
            self.extensions
        )
        self.scanner_thread.progress.connect(self.update_progress)
        self.scanner_thread.finished.connect(self.on_files_scanned)
        self.scanner_thread.error.connect(self.on_scan_error)
        
        self.progress_bar.show()
        self.progress_bar.setValue(0)
        self.scanner_thread.start()
    
    def update_progress(self, current, total):
        if total > 0:
            self.progress_bar.setValue(int((current / total) * 100))
    
    def on_files_scanned(self, files: List[Path]):
        self.all_files = files
        self.selected_files.clear()
        
        # Update file list widget
        self.file_list.clear()
        for filepath in files:
            rel_path = filepath.relative_to(self.current_dir)
            size_mb = filepath.stat().st_size / (1024*1024)
            item = QListWidgetItem(f"📄 {rel_path} ({size_mb:.2f} MB)")
            item.setData(Qt.UserRole, str(filepath))
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)  # Default all selected
            self.file_list.addItem(item)
            self.selected_files.add(filepath)
        
        self.progress_bar.hide()
        self.statusBar().showMessage(f"✅ Found {len(files)} text files")
        self.drop_label.setText(f"📁 {self.current_dir}\n\n{len(files)} files ditemukan")
        self.update_token_count()
    
    def on_scan_error(self, error_msg: str):
        self.progress_bar.hide()
        QMessageBox.critical(self, "Error", f"Gagal scan folder:\n{error_msg}")
        self.statusBar().showMessage("Error scanning folder")
    
    def update_exclude_dirs(self):
        text = self.exclude_input.text()
        self.exclude_dirs = set([d.strip() for d in text.split(",") if d.strip()])
        self.save_preferences()
        if self.current_dir != Path.cwd():
            self.refresh_files()
    
    def update_extensions(self):
        text = self.ext_input.text()
        self.extensions = set([ext.strip() for ext in text.split(",") if ext.strip()])
        self.save_preferences()
        if self.current_dir != Path.cwd():
            self.refresh_files()
    
    def update_size_limit(self):
        global MAX_FILE_SIZE
        MAX_FILE_SIZE = self.size_spin.value() * 1024 * 1024
        self.save_preferences()
        if self.current_dir != Path.cwd():
            self.refresh_files()
    
    def refresh_files(self):
        if self.current_dir and self.current_dir.exists():
            self.load_folder(str(self.current_dir))
    
    def on_item_changed(self, item: QListWidgetItem):
        filepath = Path(item.data(Qt.UserRole))
        if item.checkState() == Qt.Checked:
            self.selected_files.add(filepath)
        else:
            self.selected_files.discard(filepath)
        self.update_token_count()
    
    def select_all_files(self):
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            item.setCheckState(Qt.Checked)
            filepath = Path(item.data(Qt.UserRole))
            self.selected_files.add(filepath)
        self.update_token_count()
    
    def deselect_all_files(self):
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            item.setCheckState(Qt.Unchecked)
            filepath = Path(item.data(Qt.UserRole))
            self.selected_files.discard(filepath)
        self.update_token_count()
    
    def update_token_count(self):
        """Update estimasi token"""
        if not self.selected_files:
            self.token_label.setText("📊 Token estimasi: 0 tokens (0 files selected)")
            return
        
        total_chars = 0
        for filepath in self.selected_files:
            try:
                total_chars += filepath.stat().st_size
            except:
                pass
        
        estimated_tokens = estimate_token_count(" " * total_chars)
        self.token_label.setText(
            f"📊 Token estimasi: {estimated_tokens:,} tokens "
            f"({len(self.selected_files)} files, ~{total_chars:,} chars)"
        )
        
        # Warning jika terlalu besar (> 200K tokens)
        if estimated_tokens > 200000:
            self.token_label.setStyleSheet("color: red; font-weight: bold;")
            self.token_label.setText(
                self.token_label.text() + "\n⚠️ PERINGATAN: Token >200k, mungkin melebihi konteks AI!"
            )
        else:
            self.token_label.setStyleSheet("")
    
    def bundle_files(self):
        """Gabungkan file yang dipilih"""
        if not self.selected_files:
            QMessageBox.warning(self, "Peringatan", "Tidak ada file yang dipilih.")
            return
        
        output_path = self.current_dir / self.output_name.text()
        
        try:
            with open(output_path, 'w', encoding='utf-8') as out:
                # Header
                out.write("# " + "="*70 + "\n")
                out.write("# CODE BUNDLE\n")
                out.write(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                out.write(f"# Project: {self.current_dir.name}\n")
                out.write(f"# Total files: {len(self.selected_files)}\n")
                out.write("# " + "="*70 + "\n\n")
                
                # Proses setiap file
                for idx, filepath in enumerate(sorted(self.selected_files)):
                    rel_path = filepath.relative_to(self.current_dir)
                    
                    # Separator
                    out.write(f"===== FILE {idx+1}/{len(self.selected_files)}: {rel_path} =====\n")
                    
                    # Baca isi file
                    try:
                        content = self.read_file_safe(filepath)
                        out.write(content)
                        if not content.endswith('\n'):
                            out.write('\n')
                        out.write("\n\n")
                    except Exception as e:
                        out.write(f"[ERROR] Gagal membaca file: {e}\n\n")
            
            # Simpan preferensi pilihan file
            self.save_selected_files_preference()
            
            QMessageBox.information(
                self, 
                "Sukses", 
                f"✅ Berhasil!\n\n"
                f"Output: {output_path}\n"
                f"Total file: {len(self.selected_files)}\n"
                f"File siap di-copy ke AI Chat!"
            )
            self.statusBar().showMessage(f"Bundle saved: {output_path}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Gagal membuat bundle:\n{str(e)}")
    
    def read_file_safe(self, filepath: Path) -> str:
        """Baca file dengan berbagai encoding"""
        encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
        for enc in encodings:
            try:
                return filepath.read_text(encoding=enc)
            except (UnicodeDecodeError, PermissionError):
                continue
        return f"[Cannot read file: binary or unsupported encoding]"
    
    def save_preferences(self):
        """Simpan preferensi ke .codebundle.json"""
        prefs = {
            'exclude_dirs': list(self.exclude_dirs),
            'extensions': list(self.extensions),
            'max_file_size_mb': self.size_spin.value(),
            'output_name': self.output_name.text()
        }
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(prefs, f, indent=2)
        except:
            pass  # Silent fail untuk preference
    
    def load_preferences(self):
        """Load preferensi dari .codebundle.json"""
        try:
            if Path(CONFIG_FILE).exists():
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    prefs = json.load(f)
                
                if 'exclude_dirs' in prefs:
                    self.exclude_dirs = set(prefs['exclude_dirs'])
                    self.exclude_input.setText(",".join(sorted(self.exclude_dirs)))
                
                if 'extensions' in prefs:
                    self.extensions = set(prefs['extensions'])
                    self.ext_input.setText(",".join(sorted(self.extensions)))
                
                if 'max_file_size_mb' in prefs:
                    self.size_spin.setValue(prefs['max_file_size_mb'])
                
                if 'output_name' in prefs:
                    self.output_name.setText(prefs['output_name'])
        except:
            pass  # Silent fail jika file corrupt
    
    def save_selected_files_preference(self):
        """Simpan daftar file yang dipilih untuk project ini"""
        pref_file = self.current_dir / CONFIG_FILE
        try:
            # Load existing
            prefs = {}
            if pref_file.exists():
                with open(pref_file, 'r', encoding='utf-8') as f:
                    prefs = json.load(f)
            
            # Save selected files (relative paths)
            selected_paths = [
                str(f.relative_to(self.current_dir)) 
                for f in self.selected_files
            ]
            prefs['last_selected_files'] = selected_paths
            prefs['last_bundle_time'] = datetime.now().isoformat()
            
            with open(pref_file, 'w', encoding='utf-8') as f:
                json.dump(prefs, f, indent=2)
        except:
            pass

# ============== MAIN ==============
def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Modern style
    
    # Set application icon (optional)
    app.setApplicationName("Code Bundler Pro")
    
    window = CodeBundlerGUI()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()