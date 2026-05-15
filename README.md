# Code Bundler Pro

**Satu klik untuk menggabungkan semua kode project Anda ke dalam 1 file, siap copy-paste ke ChatGPT, Claude, atau AI apapun!**

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://python.org)
[![PyQt5](https://img.shields.io/badge/PyQt5-5.15-green.svg)](https://riverbankcomputing.com/software/pyqt/)
[![License](https://img.shields.io/badge/license-MIT-red.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)]()

![Main Window](docs/screenshots/main_window.png)

## **Permasalahan yang Diselesaikan**

> *"Saya selalu kesulitan copy-paste file project satu per satu ke chat bot AI. Jika file terlalu banyak, itu akan memakan waktu berjam-jam!"*

**Solusi:** AI Code Bundler Pro membaca SEMUA file kode Anda (Python, JavaScript, HTML, CSS, JSON, dll), lalu menggabungkannya ke **1 file .txt** yang rapi dan siap pakai.

---

## **Fitur Unggulan**

| Fitur | Status | Deskripsi |
|-------|--------|------------|
| **Drag & Drop** | ✅ | Cukup drag folder project ke aplikasi |
| **GUI Modern** | ✅ | Antarmuka grafis yang mudah digunakan |
| **Token Counter** | ✅ | Estimasi token untuk GPT-4/ChatGPT (akurat!) |
| **Auto Exclude** | ✅ | Otomatis abaikan `node_modules`, `.git`, `__pycache__`, dll |
| **Save Preferences** | ✅ | Pengaturan tersimpan otomatis |
| **Multi-threading** | ✅ | Scan file tanpa freeze aplikasi |
| **Pilih File Manual** | ✅ | Centang file mana saja yang ingin dibundle |
| **Size Limit** | ✅ | Abaikan file > 5MB (bisa diatur) |
| **Custom Extensions** | ✅ | Tambah ekstensi file apapun |
| **Cross-platform** | ✅ | Windows, macOS, Linux |

---

## **Quick Start**

### **Instalasi (3 Langkah)**

```bash
# 1. Clone repository
git clone https://github.com/JordyMail/ACode-Bundler-Pro.git
cd Code-Bundler-Pro

# 2. Install dependensi
pip install -r requirements.txt

# 3. Jalankan aplikasi
python src/code_bundler_pro.py