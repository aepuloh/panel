# ===================================
# 🌿 GRASSPANEL v5.5 - Stable Release (Pro Edition)
# ===================================
# Dev by GPT-5 | 2025
# Features:
# - BIND9 local DNS auto record (grass.web.id)
# - Nginx auto reload
# - SMTP email notifications
# - Smart File Manager (upload/edit/delete/copy/move/zip)
# - Deploy & Domain auto status
# - Logs, Users, Visitor analytics
# ===================================

# === Flask & Web Core ===
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, jsonify, send_file,
    abort, send_from_directory
)
from werkzeug.utils import secure_filename
from functools import wraps

# === Email Handling ===
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# === System / Utility Libraries ===
import os
import json
import ssl
import time
import psutil
import shutil
import smtplib
import zipfile
import logging
import threading
import subprocess
import requests
from datetime import datetime

# ===================================
# ⚙️ KONFIGURASI DASAR
# ===================================
app = Flask(__name__)
app.secret_key = "grasspanel_secret_2025"

CONFIG_PATH = "/opt/grasspanel/config.json"
DEV_APPS_PATH = "/opt/grasspanel/dev_applications.json"
LOG_FILE = "/opt/grasspanel/grasspanel.log"
DEPLOY_LOG_DIR = "/opt/grasspanel/deploy_logs"
VISITOR_LOG = "/opt/grasspanel/visitors.json"

os.makedirs(DEPLOY_LOG_DIR, exist_ok=True)

SMTP_SERVER = "mail.gazetools.my.id"
SMTP_PORT = 465
SMTP_USER = "cpanelweb@gazetools.my.id"
SMTP_PASS = "7~OC0g#qY$v7HObP"

# ===================================
# 🧾 LOGGING
# ===================================
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
# ===================================
# 🧰 SAFE JSON LOADER (ANTI CRASH)
# ===================================
def safe_load_json(path, default=None):
    """Membaca file JSON dengan aman, mengembalikan default bila rusak"""
    if not os.path.exists(path):
        return default if default is not None else []
    try:
        with open(path) as f:
            return json.load(f)
    except json.JSONDecodeError:
        logging.warning(f"[SAFE_JSON] File {path} rusak — diperbaiki otomatis.")
        # coba auto perbaikan dasar
        try:
            with open(path) as f:
                content = f.read()
                content = content.strip()
                if content.startswith("[" ) and not content.endswith("]"):
                    content += "]"
                elif content.endswith("]") and not content.startswith("["):
                    content = "[" + content
                data = json.loads(content)
                with open(path, "w") as fw:
                    json.dump(data, fw, indent=4)
                return data
        except Exception:
            pass
        return default if default is not None else []
    except Exception as e:
        logging.error(f"[SAFE_JSON] Error: {e}")
        return default if default is not None else []
# ===================================
# 🔧 UTILITAS
# ===================================
def safe_load_json(path, default=None):
    """Membaca file JSON dengan aman"""
    if default is None:
        default = []
    try:
        if not os.path.exists(path):
            return default
        with open(path) as f:
            return json.load(f)
    except Exception as e:
        logging.warning(f"[JSON] Gagal load {path}: {e}")
        return default

def load_config():
    """Load konfigurasi utama"""
    if not os.path.exists(CONFIG_PATH):
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        with open(CONFIG_PATH, "w") as f:
            json.dump({
                "users": [{"username": "admin", "password": "Grass@2025", "role": "admin"}],
                "projects": [],
            }, f)
    return safe_load_json(CONFIG_PATH, {})

def save_config(data):
    """Simpan konfigurasi JSON"""
    with open(CONFIG_PATH, "w") as f:
        json.dump(data, f, indent=4)

# ===================================
# 🔐 AUTHENTIKASI
# ===================================
def require_login(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper

def require_admin(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if session.get("role") != "admin":
            abort(403)
        return f(*args, **kwargs)
    return wrapper

# ===================================
# 👣 VISITOR TRACKING
# ===================================
@app.before_request
def track_visitors():
    """Catat pengunjung publik"""
    try:
        if request.path.startswith(("/static", "/favicon", "/login", "/logout")):
            return

        ip = request.remote_addr or "unknown"
        ua = request.headers.get("User-Agent", "unknown")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        visitors = safe_load_json(VISITOR_LOG, [])
        visitors.append({
            "ip": ip,
            "path": request.path,
            "user_agent": ua[:100],
            "time": timestamp
        })

        visitors = visitors[-1000:]
        with open(VISITOR_LOG, "w") as f:
            json.dump(visitors, f, indent=2)
    except Exception as e:
        logging.warning(f"[Visitors] Gagal mencatat: {e}")

# ===================================
# 🔑 LOGIN / LOGOUT
# ===================================
@app.route("/login", methods=["GET", "POST"])
def login():
    data = load_config()
    users = data.get("users", [])
    error = None

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        user = next((u for u in users if u["username"] == username and u["password"] == password), None)

        if user:
            session["user"] = username
            session["role"] = user["role"]
            logging.info(f"✅ Login berhasil: {username}")
            return redirect(url_for("home"))
        else:
            error = "❌ Username atau password salah"
            logging.warning(f"Login gagal: {username}")

    return render_template("login.html", error=error)

@app.route("/logout")
def logout():
    user = session.get("user", "unknown")
    logging.info(f"🚪 {user} logout.")
    session.clear()
    return redirect(url_for("login"))
    # ===================================
# 🏠 DASHBOARD
# ===================================
@app.route("/")
@app.route("/dashboard")
@require_login
def dashboard():
    data = load_config()
    user, role = session["user"], session["role"]

    projects = (
        data.get("projects", [])
        if role == "admin"
        else [p for p in data.get("projects", []) if p.get("owner") == user]
    )

    pending_count = 0
    if role == "admin" and os.path.exists(DEV_APPS_PATH):
        try:
            dev_apps = safe_load_json(DEV_APPS_PATH, [])
            pending_count = len([a for a in dev_apps if a.get("status") == "pending"])
        except Exception as e:
            logging.warning(f"[Dashboard] Gagal baca DEV_APPS_PATH: {e}")

    return render_template(
        "dashboard.html",
        user=user,
        role=role,
        projects=projects,
        pending_count=pending_count
    )

# ===================================
# 🏡 HOME PAGE
# ===================================
@app.route("/home")
@require_login
def home():
    user = session.get("user")
    role = session.get("role")
    return render_template("home.html", user=user, role=role)

# ===================================
# 🧱 PROJECT CREATION (NEW VERSION)
# ===================================
@app.route("/create_website", methods=["GET", "POST"])
@require_login
def create_website():
    """Membuat website baru dan langsung aktif"""
    if request.method == "GET":
        return render_template("create_website.html", user=session["user"], role=session["role"])

    name = request.form.get("name", "").strip().lower()
    domain = request.form.get("domain", "").strip().lower()

    if not name or not domain:
        session["toast"] = {"message": "❌ Nama dan domain wajib diisi", "level": "error"}
        return redirect(url_for("dashboard"))

    if not domain.endswith(".grass.web.id"):
        domain = f"{domain}.grass.web.id"

    path = f"/var/www/{name}"
    os.makedirs(path, exist_ok=True)

    # === Index file default ===
    index_file = os.path.join(path, "index.html")
    if not os.path.exists(index_file):
        with open(index_file, "w") as f:
            f.write(f"""
            <html><head>
            <title>{name} — GrassPanel Site</title>
            <style>
            body{{background:#0f2027;color:white;text-align:center;font-family:Poppins,sans-serif;padding-top:15%;}}
            h1{{color:#00ffbf;text-shadow:0 0 12px rgba(0,255,180,0.6);}}
            p{{color:#ccc;}}
            </style></head>
            <body>
              <h1>🌿 {name}.grass.web.id</h1>
              <p>Website berhasil dibuat menggunakan GrassPanel v5.5</p>
              <p>Domain: <a href="http://{domain}" style="color:#00ffbf;text-decoration:none;">{domain}</a></p>
            </body></html>
            """)

    # === Simpan ke config ===
    data = load_config()
    data["projects"].append({
        "name": name,
        "domain": domain,
        "path": path,
        "owner": session["user"],
        "status": "created"
    })
    save_config(data)

    # Tambahkan DNS + Nginx
    add_dns_record_local(domain, ip="160.187.141.218")

    nginx_conf = f"""
server {{
    listen 80;
    server_name {domain};
    root {path};
    index index.html index.htm;
    access_log /var/log/nginx/{name}_access.log;
    error_log /var/log/nginx/{name}_error.log;
}}
"""
    conf_path = f"/etc/nginx/sites-available/{domain}.conf"
    enabled_path = f"/etc/nginx/sites-enabled/{domain}.conf"

    with open(conf_path, "w") as f:
        f.write(nginx_conf)
    if os.path.exists(enabled_path):
        os.remove(enabled_path)
    os.symlink(conf_path, enabled_path)

    os.system("nginx -t && systemctl reload nginx")

    session["toast"] = {"message": f"✅ Website {domain} berhasil dibuat!", "level": "success"}
    logging.info(f"[PROJECT] Website {domain} dibuat oleh {session['user']}")

    # Redirect langsung ke File Manager
    return redirect(url_for("file_manager", project_name=name))

# ===================================
# 🗂️ FILE MANAGER SYSTEM
# ===================================
@app.route("/files/<project_name>")
@require_login
def file_manager(project_name):
    """Menampilkan daftar file & folder project"""
    data = load_config()
    project = next((p for p in data.get("projects", []) if p["name"] == project_name), None)
    if not project:
        abort(404, "Project tidak ditemukan")

    base_path = project["path"]
    if not os.path.exists(base_path):
        os.makedirs(base_path, exist_ok=True)

    try:
        items = []
        for name in os.listdir(base_path):
            full_path = os.path.join(base_path, name)
            item_info = {
                "name": name,
                "is_dir": os.path.isdir(full_path),
                "size": os.path.getsize(full_path) if os.path.isfile(full_path) else "-",
                "mtime": datetime.fromtimestamp(os.path.getmtime(full_path)).strftime("%Y-%m-%d %H:%M")
            }
            items.append(item_info)
        items.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))

        return render_template(
            "file_manager.html",
            project=project,
            items=items,
            user=session["user"],
            role=session["role"]
        )
    except Exception as e:
        logging.error(f"[FILES] Gagal membuka File Manager: {e}")
        return f"<h3 style='color:red;'>Terjadi kesalahan: {e}</h3>", 500

# ===================================
# 📤 UPLOAD FILE
# ===================================
@app.route("/files/<project_name>/upload", methods=["POST"])
@require_login
def upload_file(project_name):
    """Upload file ke project"""
    data = load_config()
    project = next((p for p in data["projects"] if p["name"] == project_name), None)
    if not project:
        abort(404)

    base_path = project["path"]
    file = request.files.get("file")
    if not file:
        return "Tidak ada file", 400

    filename = secure_filename(file.filename)
    save_path = os.path.join(base_path, filename)
    file.save(save_path)

    # Ekstrak otomatis jika ZIP
    if filename.lower().endswith(".zip"):
        with zipfile.ZipFile(save_path, "r") as z:
            z.extractall(base_path)
        os.remove(save_path)
        logging.info(f"[UPLOAD] ZIP {filename} diekstrak di {project_name}")

    logging.info(f"[UPLOAD] File {filename} diunggah ke {project_name} oleh {session['user']}")
    session["toast"] = {"message": f"✅ File {filename} diunggah", "level": "success"}
    return redirect(url_for("file_manager", project_name=project_name))

# ===================================
# ✏️ EDIT FILE
# ===================================
@app.route("/files/<project_name>/edit", methods=["GET", "POST"])
@require_login
def edit_file(project_name):
    """Edit file teks"""
    data = load_config()
    project = next((p for p in data["projects"] if p["name"] == project_name), None)
    if not project:
        abort(404)

    base = project["path"]
    rel_path = request.args.get("path")
    full_path = os.path.join(base, rel_path)

    if not os.path.exists(full_path):
        abort(404)

    if request.method == "POST":
        content = request.form.get("content", "")
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        session["toast"] = {"message": f"✅ File {rel_path} disimpan!", "level": "success"}
        logging.info(f"[EDIT] File {rel_path} disimpan di project {project_name} oleh {session['user']}")
        return redirect(url_for("file_manager", project_name=project_name))

    with open(full_path, "r", encoding="utf-8") as f:
        content = f.read()
    return render_template("edit_file.html", project=project, file_path=rel_path, content=content)

# ===================================
# ⚙️ FILE ACTIONS (COPY, MOVE, RENAME, DELETE, NEW)
# ===================================
@app.route("/files/<project_name>/action", methods=["POST"])
@require_login
def file_action(project_name):
    """Aksi file/folder"""
    data = load_config()
    project = next((p for p in data["projects"] if p["name"] == project_name), None)
    if not project:
        abort(404)

    base = project["path"]
    action = request.form.get("action")
    target = request.form.get("target")
    new_name = request.form.get("new_name")
    destination = request.form.get("destination")

    full_path = os.path.join(base, target) if target else None
    try:
        if action == "rename" and full_path and new_name:
            os.rename(full_path, os.path.join(base, new_name))
        elif action == "new_file" and new_name:
            open(os.path.join(base, new_name), "w").close()
        elif action == "new_folder" and new_name:
            os.makedirs(os.path.join(base, new_name), exist_ok=True)
        elif action == "copy" and full_path and destination:
            dst = os.path.join(base, destination, os.path.basename(full_path))
            if os.path.isdir(full_path):
                shutil.copytree(full_path, dst)
            else:
                shutil.copy2(full_path, dst)
        elif action == "move" and full_path and destination:
            shutil.move(full_path, os.path.join(base, destination))
        elif action == "delete" and full_path:
            if os.path.isdir(full_path):
                shutil.rmtree(full_path)
            elif os.path.exists(full_path):
                os.remove(full_path)
        session["toast"] = {"message": f"✅ Aksi {action} berhasil", "level": "success"}
        logging.info(f"[FILES] {action.upper()} dijalankan di {project_name}")
    except Exception as e:
        logging.error(f"[FILES] Error saat {action}: {e}")
        session["toast"] = {"message": f"❌ Gagal {action}: {e}", "level": "error"}

    return redirect(url_for("file_manager", project_name=project_name))
    # ===================================
# 🧩 FILE ACTION ALIASES (KOMPATIBILITAS LAMA)
# ===================================

def _legacy_action(project_name, action):
    """Helper internal untuk menjalankan aksi file lama"""
    request.form = request.form.copy()
    request.form["action"] = action
    return file_action(project_name)

@app.route("/files/<project_name>/delete", methods=["POST"])
@require_login
def delete_file(project_name):
    """Alias lama: delete file"""
    return _legacy_action(project_name, "delete")

@app.route("/files/<project_name>/rename", methods=["POST"])
@require_login
def rename_file(project_name):
    """Alias lama: rename file"""
    return _legacy_action(project_name, "rename")

@app.route("/files/<project_name>/copy", methods=["POST"])
@require_login
def copy_file(project_name):
    """Alias lama: copy file"""
    return _legacy_action(project_name, "copy")

@app.route("/files/<project_name>/move", methods=["POST"])
@require_login
def move_file(project_name):
    """Alias lama: move file"""
    return _legacy_action(project_name, "move")

@app.route("/files/<project_name>/new_file", methods=["POST"])
@require_login
def new_file(project_name):
    """Alias lama: buat file baru"""
    return _legacy_action(project_name, "new_file")

@app.route("/files/<project_name>/new_folder", methods=["POST"])
@require_login
def new_folder(project_name):
    """Alias lama: buat folder baru"""
    return _legacy_action(project_name, "new_folder")

import re

# ===================================
# 🧩 SAFE NAME GENERATOR
# ===================================
def safe_name(name: str) -> str:
    """Pastikan nama aman untuk folder, domain, dan nginx"""
    n = re.sub(r'[^a-zA-Z0-9_-]+', '-', name.strip().lower())
    n = re.sub(r'-+', '-', n)
    return n
# ===================================
# 💾 AUTO DATABASE MANAGEMENT
# ===================================
import string, secrets
import mysql.connector

def mysql_connect():
    """Koneksi root MySQL"""
    try:
        return mysql.connector.connect(
            host="localhost",
            user="root",
            password="YOUR_ROOT_PASSWORD"  # 🔧 ubah sesuai root mysql kamu
        )
    except Exception as e:
        logging.error(f"MySQL Connect Error: {e}")
        return None

def create_database_for_project(name):
    """Buat database, user, dan password otomatis"""
    conn = mysql_connect()
    if not conn:
        return None
    cursor = conn.cursor()
    db_name = f"db_{safe_name(name)}"
    user = f"usr_{safe_name(name)}"
    password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(10))
    try:
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
        cursor.execute(f"CREATE USER IF NOT EXISTS '{user}'@'localhost' IDENTIFIED BY '{password}'")
        cursor.execute(f"GRANT ALL PRIVILEGES ON {db_name}.* TO '{user}'@'localhost'")
        cursor.execute("FLUSH PRIVILEGES")
        conn.commit()
        logging.info(f"[DB] Database {db_name} dan user {user} dibuat")
        return {"db": db_name, "user": user, "password": password}
    except Exception as e:
        logging.error(f"[DB_ERROR] {e}")
        return None
    finally:
        conn.close()

def delete_database_for_project(name):
    """Hapus database dan user otomatis"""
    conn = mysql_connect()
    if not conn:
        return
    cursor = conn.cursor()
    db_name = f"db_{safe_name(name)}"
    user = f"usr_{safe_name(name)}"
    try:
        cursor.execute(f"DROP DATABASE IF EXISTS {db_name}")
        cursor.execute(f"DROP USER IF EXISTS '{user}'@'localhost'")
        conn.commit()
        logging.info(f"[DB_DELETE] {db_name} & user {user} dihapus")
    except Exception as e:
        logging.error(f"[DB_DELETE_FAIL] {e}")
    finally:
        conn.close()


# ===================================
# 🚀 DEPLOY SYSTEM (STABLE & FIXED)
# ===================================
def background_deploy(project, idx):
    """Deploy otomatis aman (tanpa 404, auto index, & sinkron status/log)"""
    name_raw = project["name"]
    name = safe_name(name_raw)
    domain = f"{name}.grass.web.id"
    path = f"/var/www/{name}"
    log_path = f"{DEPLOY_LOG_DIR}/{name}.log"

    os.makedirs(path, exist_ok=True)
    os.makedirs("/var/log/nginx", exist_ok=True)

    def log(msg):
        ts = datetime.now().strftime("[%H:%M:%S]")
        line = f"{ts} {msg}"
        with open(log_path, "a") as f:
            f.write(line + "\n")
        logging.info(line)

    # === Mulai Deploy
    log(f"🚀 [START] Deploy dimulai untuk '{name_raw}' ({domain})")

    try:
        # === Update status config
        data = load_config()
        data["projects"][idx]["status"] = "deploying"
        data["projects"][idx]["domain"] = domain
        data["projects"][idx]["path"] = path
        save_config(data)

        # === Buat database otomatis
        db_info = create_database_for_project(name_raw)
        if db_info:
            db_json = os.path.join(path, "db.json")
            with open(db_json, "w") as f:
                json.dump(db_info, f, indent=2)
            log(f"💾 Database otomatis dibuat: {db_info['db']} (user: {db_info['user']})")
        else:
            log("⚠️ Database gagal dibuat (cek MySQL root config)")

        # === Buat index.html default jika belum ada
        index_file = os.path.join(path, "index.html")
        if not os.path.exists(index_file):
            with open(index_file, "w") as f:
                f.write(f"""
                <html><head><title>{domain}</title></head>
                <body style='background:#0f2027;color:white;text-align:center;padding-top:10%;font-family:Poppins'>
                    <h1 style='color:#00ffbf;'>🌿 {domain}</h1>
                    <p>Website berhasil di-deploy otomatis via GrassPanel 🚀</p>
                </body></html>
                """)
            log("📄 File index.html default dibuat")

        os.system(f"chown -R www-data:www-data {path}")
        log("🔑 Permission diset untuk www-data")

        # === DNS record lokal
        add_dns_record_local(domain, ip="160.187.141.218")
        os.system("systemctl reload bind9")
        log("✅ DNS record ditambahkan & Bind9 direload")

        # === Konfigurasi Nginx
        nginx_conf = f"""
server {{
    listen 80;
    server_name {domain};
    root {path};
    index index.html index.htm;
    access_log /var/log/nginx/{name}_access.log;
    error_log /var/log/nginx/{name}_error.log;

    location / {{
        try_files $uri $uri/ =404;
    }}
}}
"""
        conf_path = f"/etc/nginx/sites-available/{domain}.conf"
        enabled_path = f"/etc/nginx/sites-enabled/{domain}.conf"

        with open(conf_path, "w") as f:
            f.write(nginx_conf.strip())

        if os.path.exists(enabled_path):
            os.remove(enabled_path)
        os.symlink(conf_path, enabled_path)
        log("🌐 Nginx config dibuat & disimpan")

        # 🧹 Pastikan hanya hapus symlink rusak (bukan semua)
        try:
            subprocess.run(["find", "-L", "/etc/nginx/sites-enabled/", "-type", "l", "-delete"], check=True)
            log("🧹 Symlink rusak dibersihkan sebelum reload Nginx")
        except Exception as e:
            log(f"⚠️ Gagal hapus symlink rusak: {e}")

        # 🔍 Tes konfigurasi nginx sebelum reload
        test = subprocess.run(["nginx", "-t"], capture_output=True, text=True)
        if test.returncode != 0:
            log(f"❌ [NGINX_FAIL] {test.stderr.strip()}")
            data["projects"][idx]["status"] = "offline"
            save_config(data)
            return

        subprocess.run(["systemctl", "reload", "nginx"], check=True)
        log("✅ Nginx berhasil direload")

        # === Cek domain online maksimal 120 detik
        log("🕒 Mengecek status domain publik...")
        for _ in range(24):
            try:
                r = requests.get(f"http://{domain}", timeout=5)
                if r.status_code in [200, 301, 302]:
                    data["projects"][idx]["status"] = "online"
                    save_config(data)
                    log(f"✅ Website aktif: http://{domain}")
                    log(f"🔗 [DOMAIN_READY] http://{domain}")
                    return
            except Exception as e:
                log(f"🔄 Menunggu domain aktif... ({e})")
            time.sleep(5)

        # === Jika gagal setelah 120 detik
        data["projects"][idx]["status"] = "offline"
        save_config(data)
        log("⚠️ Domain belum aktif setelah 120 detik.")
        log(f"🔗 [DOMAIN_FAIL] http://{domain}")

    except Exception as e:
        log(f"❌ Deploy gagal: {str(e)}")
        data = load_config()
        data["projects"][idx]["status"] = "offline"
        save_config(data)


# ===================================
# ⚙️ PROJECT ACTIONS (DEPLOY / DELETE)
# ===================================
@app.route("/action/<int:idx>/<string:cmd>")
@require_login
def project_action(idx, cmd):
    """Deploy & Delete project"""
    data = load_config()
    projects = data.get("projects", [])
    if idx < 0 or idx >= len(projects):
        abort(404)

    project = projects[idx]
    name = project["name"]
    safe = safe_name(name)
    domain = project.get("domain", f"{safe}.grass.web.id")
    path = project.get("path", f"/var/www/{safe}")
    log_file = f"{DEPLOY_LOG_DIR}/{safe}.log"

    # 🚀 DEPLOY ===========================================================
    if cmd == "deploy":
        # Reset log setiap redeploy
        with open(log_file, "w") as f:
            f.write(f"[{datetime.now().strftime('%H:%M:%S')}] 🚀 Redeploy dimulai...\n")

        # Update status di config
        data["projects"][idx]["status"] = "deploying"
        save_config(data)

        # Jalankan background deploy thread
        threading.Thread(target=background_deploy, args=(project, idx), daemon=True).start()

        session["toast"] = {
            "message": f"🚀 Deploy ulang dimulai untuk {name}",
            "level": "success"
        }
        logging.info(f"[DEPLOY] {name} dijalankan ulang oleh {session['user']}")
        return redirect(url_for("dashboard"))

    # 🗑️ DELETE ===========================================================
    elif cmd == "delete":
        try:
            # 🔹 Hapus database otomatis
            delete_database_for_project(name)
            logging.info(f"[DB_DELETE] Database {name} dihapus otomatis")

            # 🔹 Hapus log deploy
            if os.path.exists(log_file):
                os.remove(log_file)
                logging.info(f"[DELETE] Log file {log_file} dihapus")

            # 🔹 Hapus folder website
            if os.path.isdir(path):
                shutil.rmtree(path)
                logging.info(f"[DELETE] Folder {path} dihapus")

            # 🔹 Hapus konfigurasi Nginx
            conf = f"/etc/nginx/sites-available/{domain}.conf"
            enabled = f"/etc/nginx/sites-enabled/{domain}.conf"
            for f in [conf, enabled]:
                if os.path.exists(f):
                    os.remove(f)
                    logging.info(f"[DELETE] {f} dihapus")

            # 🔹 Hapus DNS record dari Bind9
            zone_file = "/etc/bind/zones/db.grass.web.id"
            if os.path.exists(zone_file):
                sub = domain.replace(".grass.web.id", "")
                with open(zone_file, "r") as f:
                    lines = f.readlines()
                with open(zone_file, "w") as f:
                    for line in lines:
                        if sub not in line:
                            f.write(line)
                os.system("systemctl reload bind9")
                logging.info(f"[DNS] Record {domain} dihapus dari zone")

            # 🔹 Reload Nginx untuk bersihkan konfigurasi
            os.system("nginx -t && systemctl reload nginx")

            # 🔹 Hapus dari config.json
            projects.pop(idx)
            save_config(data)

            session["toast"] = {
                "message": f"🧹 {domain} & semua datanya dihapus otomatis",
                "level": "success"
            }
        except Exception as e:
            session["toast"] = {
                "message": f"❌ Gagal hapus {domain}: {e}",
                "level": "error"
            }
            logging.error(f"[DELETE_FAIL] {domain}: {e}")

    return redirect(url_for("dashboard"))


# ===================================
# 📄 DEPLOY LOG VIEWER (REAL-TIME + ANIMASI)
# ===================================
@app.route("/deploy_logs/<project>")
@require_login
def deploy_logs(project):
    """Tampilkan log deploy secara real-time + domain aktif"""
    log_path = f"{DEPLOY_LOG_DIR}/{project}.log"

    # Mode RAW (AJAX refresh)
    if request.args.get("raw"):
        if os.path.exists(log_path):
            with open(log_path, "r") as f:
                return f.read()
        return "Belum ada log."

    if not os.path.exists(log_path):
        return f"<pre style='color:white;background:#0f2027;padding:20px;'>❌ Belum ada log untuk {project}</pre>"

    with open(log_path, "r") as f:
        content = f.read()

    # Cari domain terakhir (READY / FAIL)
    domain_ready = ""
    for line in reversed(content.splitlines()):
        if "[DOMAIN_READY]" in line:
            domain_ready = line.split("[DOMAIN_READY]")[-1].strip()
            break
        if "[DOMAIN_FAIL]" in line:
            domain_ready = line.split("[DOMAIN_FAIL]")[-1].strip()
            break

    domain_link = ""
    if domain_ready:
        domain_link = f"""
        <div style='margin:15px 0;text-align:center;'>
          <a href='{domain_ready}' target='_blank' style='
            color:#00ffa2;
            text-decoration:none;
            font-weight:bold;
            font-size:1rem;
            background:rgba(0,255,162,0.1);
            padding:10px 18px;
            border-radius:8px;
            display:inline-block;
            box-shadow:0 0 10px rgba(0,255,162,0.4);
            transition:0.3s;
          ' onmouseover="this.style.background='rgba(0,255,162,0.3)'" 
             onmouseout="this.style.background='rgba(0,255,162,0.1)'">
             🌐 Buka Website: {domain_ready}
          </a>
        </div>"""

    return f"""
    <html>
    <head>
      <meta charset='utf-8'>
      <title>📜 Deploy Log — {project}</title>
      <meta http-equiv='refresh' content='3'>
      <style>
        body {{background:#0f2027;color:#00eaff;font-family:monospace;padding:20px;white-space:pre-wrap;}}
        h2 {{text-align:center;color:#00ffa2;font-family:Poppins,sans-serif;}}
        .container {{
          background:rgba(255,255,255,0.06);
          padding:15px;
          border-radius:8px;
          max-height:80vh;
          overflow-y:auto;
          box-shadow:0 0 12px rgba(0,255,180,0.2);
        }}
        .blink {{
          animation: blink 1.2s infinite alternate;
          color:#ffd447;
        }}
        @keyframes blink {{ 0%{{opacity:1}} 100%{{opacity:0.3}} }}
      </style>
      <script>
        async function refresh() {{
          const res = await fetch(window.location.href + '?raw=1&_=' + Date.now());
          const txt = await res.text();
          document.querySelector('.container').textContent = txt;
          window.scrollTo(0, document.body.scrollHeight);
        }}
        setInterval(refresh, 2500);
        window.onload = refresh;
      </script>
    </head>
    <body>
      <h2>🚀 Deploy Log: {project}</h2>
      {domain_link or "<p class='blink' style='text-align:center;'>⏳ Sedang deploy...</p>"}
      <div class='container'>{content}</div>
    </body>
    </html>
    """

# ===================================
# 🌐 BIND9 LOCAL DNS AUTO RECORD
# ===================================
def add_dns_record_local(domain, ip="160.187.141.218"):
    """Tambahkan A record otomatis ke zone grass.web.id"""
    zone_file = "/etc/bind/zones/db.grass.web.id"
    reload_cmd = "systemctl reload bind9"
    try:
        if not domain.endswith(".grass.web.id"):
            logging.warning(f"[DNS] ❌ {domain} bukan subdomain grass.web.id")
            return False
        sub = domain.replace(".grass.web.id", "")
        record = f"{sub}\tIN\tA\t{ip}\n"
        with open(zone_file, "r") as f:
            lines = f.readlines()
        if any(sub in line for line in lines):
            logging.info(f"[DNS] ℹ️ {domain} sudah ada di zone.")
            return True
        with open(zone_file, "a") as f:
            f.write(record)
        update_zone_serial(zone_file)
        os.system(reload_cmd)
        logging.info(f"[DNS] ✅ Record {domain} ditambahkan ({ip})")
        return True
    except Exception as e:
        logging.error(f"[DNS] ❌ Gagal menambahkan record {domain}: {e}")
        return False

def update_zone_serial(zone_file):
    """Update serial file BIND9"""
    try:
        with open(zone_file, "r") as f:
            lines = f.readlines()
        for i, line in enumerate(lines):
            if ";" in line and "Serial" in line:
                num = int(line.strip().split(";")[0])
                new = str(num + 1)
                lines[i] = line.replace(str(num), new)
                break
        with open(zone_file, "w") as f:
            f.writelines(lines)
        logging.info("[DNS] Serial zone diperbarui.")
    except Exception as e:
        logging.warning(f"[DNS] Gagal update serial: {e}")

# ===================================
# 📧 EMAIL SYSTEM
# ===================================
def send_email(recipient, subject, html_content):
    """Kirim email HTML via SMTP"""
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = SMTP_USER
        msg["To"] = recipient
        msg.attach(MIMEText(html_content, "html"))

        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context) as s:
            s.login(SMTP_USER, SMTP_PASS)
            s.sendmail(SMTP_USER, recipient, msg.as_string())

        logging.info(f"[MAIL] ✅ Email terkirim ke {recipient}")
        return True
    except Exception as e:
        logging.error(f"[MAIL] ❌ {e}")
        return False

# ===================================
# 👥 USER MANAGEMENT (ADMIN ONLY)
# ===================================
@app.route("/users", methods=["GET", "POST"])
@require_admin
def users():
    """Kelola user panel"""
    data = load_config()
    users = data.get("users", [])
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()
        role = request.form["role"]

        if any(u["username"] == username for u in users):
            return render_template("users.html", users=users, error="❌ Username sudah ada")

        users.append({"username": username, "password": password, "role": role})
        save_config(data)
        session["toast"] = {"message": f"✅ User {username} ditambahkan", "level": "success"}
        logging.info(f"[USER] ✅ User {username} ditambahkan oleh {session['user']}")
        return redirect(url_for("users"))

    return render_template("users.html", users=users, user=session["user"], role=session["role"])

@app.route("/delete_user/<username>")
@require_admin
def delete_user(username):
    """Hapus user, tapi akun admin utama dikunci permanen"""
    data = load_config()

    # Lindungi akun admin utama
    if username.lower() == "admin":
        session["toast"] = {
            "message": "🔒 Akun admin utama tidak dapat dihapus!",
            "level": "error"
        }
        logging.warning(f"[SECURITY] ⚠️ {session['user']} mencoba menghapus akun admin utama.")
        return redirect(url_for("users"))

    # Filter & hapus user selain admin utama
    users = [u for u in data.get("users", []) if u["username"] != username]
    data["users"] = users
    save_config(data)

    session["toast"] = {"message": f"🗑️ User {username} dihapus", "level": "success"}
    logging.info(f"[USER] 🗑️ User {username} dihapus oleh {session['user']}")
    return redirect(url_for("users"))

# ===================================
# 🧩 DEVELOPER APPLICATIONS (Admin Only)
# ===================================
@app.route("/dev_applications")
@require_admin
def dev_applications():
    """Menampilkan daftar pengajuan developer (dengan history)"""
    apps = safe_load_json(DEV_APPS_PATH, [])

    # Normalisasi status ke lowercase
    for a in apps:
        a["status"] = str(a.get("status", "pending")).strip().lower()

    # Urutkan dari terbaru
    apps = sorted(apps, key=lambda x: x.get("waktu", ""), reverse=True)

    pending_count = sum(1 for a in apps if a["status"] == "pending")

    return render_template(
        "dev_applications.html",
        apps=apps,  # <== kirim semua data (bukan filtered)
        user=session["user"],
        role=session["role"],
        pending_count=pending_count
    )

@app.route("/approve_dev", methods=["POST"])
@require_admin
def approve_dev():
    """Setujui pengajuan developer"""
    email = request.form.get("email")
    username = request.form.get("username")
    password = request.form.get("password")

    apps = safe_load_json(DEV_APPS_PATH, [])
    for a in apps:
        if a["email"] == email:
            a["status"] = "approved"
            a["approved_by"] = session["user"]
            a["approved_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            break

    with open(DEV_APPS_PATH, "w") as f:
        json.dump(apps, f, indent=4)
    os.sync()

    # tambahkan user dev
    data = load_config()
    if not any(u["username"] == username for u in data.get("users", [])):
        data["users"].append({"username": username, "password": password, "role": "dev"})
        save_config(data)

    # kirim email
    html_message = f"""
    <html><body style="font-family:Poppins,sans-serif;background:#0f2027;color:#fff;padding:25px;">
      <h2 style="color:#00ffa2;">🎉 Selamat {username}!</h2>
      <p>Pengajuanmu sebagai Developer GrassPanel telah disetujui ✅</p>
      <ul>
        <li>👤 Username: {username}</li>
        <li>🔑 Password: {password}</li>
      </ul>
      <p>Login: <a href="http://panel.grass.web.id" style="color:#00ffa2;">panel.grass.web.id</a></p>
    </body></html>
    """
    send_email(email, "🎉 Akun Developer GrassPanel", html_message)
    logging.info(f"[DEV] ✅ {email} disetujui oleh {session['user']}")

    session["toast"] = {"message": f"✅ {email} disetujui", "level": "success"}
    return redirect(url_for("dev_applications"))

@app.route("/reject_dev", methods=["POST"])
@require_admin
def reject_dev():
    """Tolak pengajuan developer"""
    email = request.form.get("email")

    apps = safe_load_json(DEV_APPS_PATH, [])
    for a in apps:
        if a["email"] == email:
            a["status"] = "rejected"
            a["rejected_by"] = session["user"]
            a["rejected_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            break

    with open(DEV_APPS_PATH, "w") as f:
        json.dump(apps, f, indent=4)
    os.sync()

    html_message = f"""
    <html><body style="font-family:Poppins,sans-serif;background:#0f2027;color:white;padding:25px;">
      <h2 style="color:#ff6363;">🙏 Mohon Maaf</h2>
      <p>Terima kasih atas pengajuanmu sebagai Developer GrassPanel.</p>
      <p>Saat ini belum dapat kami setujui. Kamu dapat mengajukan kembali di waktu mendatang.</p>
      <p>Semangat terus berkarya 🌿</p>
    </body></html>
    """
    send_email(email, "🙏 Pengajuan Developer GrassPanel", html_message)
    logging.info(f"[DEV] ❌ {email} ditolak oleh {session['user']}")

    session["toast"] = {"message": f"❌ {email} ditolak", "level": "error"}
    return redirect(url_for("dev_applications"))
    # ===================================
# 📊 VISITOR ANALYTICS (Admin Only)
# ===================================
@app.route("/visitors")
@require_admin
def visitors():
    """Statistik pengunjung"""
    visitors = safe_load_json(VISITOR_LOG, [])
    total_visits = len(visitors)
    unique_ips = len(set(v["ip"] for v in visitors))
    today = datetime.now().strftime("%Y-%m-%d")
    today_visits = [v for v in visitors if today in v["time"]]

    return render_template(
        "visitors.html",
        user=session["user"],
        role=session["role"],
        visitors=visitors[::-1],
        total_visits=total_visits,
        unique_ips=unique_ips,
        today_visits=len(today_visits)
    )

# ===================================
# 🔧 INTEGRATIONS SYSTEM
# ===================================
@app.route("/integrations", methods=["GET", "POST"])
@require_admin
def integrations():
    """Kelola integrasi API eksternal"""
    data = load_config()
    integrations_data = data.get("integrations", {})

    if request.method == "POST":
        form_data = request.form.to_dict()
        integrations_data.update(form_data)
        data["integrations"] = integrations_data
        save_config(data)

        logging.info(f"[Integrations] Diperbarui oleh {session['user']}: {list(form_data.keys())}")
        message = "Integrasi berhasil disimpan ✅"
        try:
            if "host" in form_data and "token" in form_data:
                res = requests.get(
                    f"https://{form_data['host']}:2083/execute/Version/get_version",
                    headers={"Authorization": f"cpanel {form_data['user']}:{form_data['token']}"},
                    timeout=5,
                    verify=False
                )
                if res.status_code == 200:
                    message = "✅ cPanel API terhubung!"
        except Exception as e:
            logging.warning(f"[Integrations] Gagal test koneksi: {e}")
            message = "⚠️ Integrasi disimpan, tapi koneksi gagal."

        session["toast"] = {"message": message, "level": "success"}
        return redirect(url_for("integrations"))

    return render_template(
        "integrations.html",
        user=session["user"],
        role=session["role"],
        integrations=integrations_data
    )

# ===================================
# 💾 BACKUP SYSTEM
# ===================================
@app.route("/backup")
@require_admin
def backup_system():
    """Backup penuh config dan proyek"""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = "/opt/grasspanel/backups"
    os.makedirs(backup_dir, exist_ok=True)
    zip_path = f"{backup_dir}/backup_{ts}.zip"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(CONFIG_PATH, arcname="config.json")
        if os.path.exists("/var/www"):
            for root, _, files in os.walk("/var/www"):
                for f in files:
                    full = os.path.join(root, f)
                    z.write(full, arcname=os.path.relpath(full, "/var/www"))

    logging.info(f"[BACKUP] ✅ Backup dibuat: {zip_path}")
    return send_file(zip_path, as_attachment=True)

# ===================================
# 📈 SYSTEM STATUS (CPU, RAM, DISK)
# ===================================
@app.route("/system_status")
def system_status():
    """Statistik real-time server"""
    return jsonify({
        "cpu": psutil.cpu_percent(interval=0.5),
        "ram": psutil.virtual_memory().percent,
        "disk": psutil.disk_usage('/').percent,
        "uptime": int(time.time() - psutil.boot_time())
    })

# ===================================
# 🔔 TOAST MESSAGE (UI Notifications)
# ===================================
@app.route("/get_toast")
def get_toast():
    """Ambil pesan toast dari session"""
    toast = session.pop("toast", None)
    return jsonify(toast or {})

# ===================================
# 🌐 CEK STATUS DOMAIN PROYEK (API)
# ===================================
@app.route("/check_domain_status/<project>")
@require_login
def check_domain_status(project):
    """Mengembalikan status domain proyek (online/offline/deploying)"""
    data = load_config()
    for p in data.get("projects", []):
        if p["name"] == project:
            status = p.get("status", "unknown")
            domain = p.get("domain")

            # Kalau masih deploying, langsung return
            if status == "deploying":
                return jsonify({"status": "deploying"})

            # Coba koneksi ke domain kalau ada
            if domain:
                try:
                    r = requests.get(f"http://{domain}", timeout=4)
                    if r.status_code in [200, 301, 302]:
                        # Update status jadi online
                        p["status"] = "online"
                        save_config(data)
                        return jsonify({"status": "online"})
                    else:
                        p["status"] = "offline"
                        save_config(data)
                        return jsonify({"status": "offline"})
                except Exception:
                    p["status"] = "offline"
                    save_config(data)
                    return jsonify({"status": "offline"})
            else:
                return jsonify({"status": "offline"})
    return jsonify({"status": "unknown"})

# ===================================
# 🧠 DEVELOPER APPLY (Public)
# ===================================
@app.route("/apply_dev", methods=["POST"])
def apply_dev():
    """Form publik untuk developer baru"""
    nama = request.form.get("nama")
    email = request.form.get("email").strip().lower()
    alasan = request.form.get("alasan")

    data = {
        "nama": nama,
        "email": email,
        "alasan": alasan,
        "waktu": str(datetime.now()),
        "status": "pending"
    }

    apps = safe_load_json(DEV_APPS_PATH, [])

    # Hapus pengajuan lama dengan email sama
    apps = [a for a in apps if a.get("email", "").strip().lower() != email]

    # Tambahkan pengajuan baru
    apps.append(data)

    with open(DEV_APPS_PATH, "w") as f:
        json.dump(apps, f, indent=4)
    os.sync()

    # Kirim email konfirmasi
    html_message = f"""
    <html><body style='font-family:Poppins,sans-serif;background:#0f2027;color:white;padding:20px;'>
      <h2 style='color:#00d9ff;'>Halo {nama} 👋</h2>
      <p>Terima kasih telah mengajukan diri sebagai Developer di <b>GrassPanel</b>.</p>
      <p>Admin akan meninjau aplikasi kamu secepatnya.</p>
      <p><b>Waktu pengajuan:</b> {data['waktu']}</p>
      <hr><p>Salam,<br><b>GrassPanel System</b></p>
    </body></html>
    """
    send_email(email, "📩 Pengajuan Developer GrassPanel", html_message)
    logging.info(f"[APPLY_DEV] Developer apply dari {nama} <{email}>")
    return redirect(url_for("login"))

# ===================================
# 🚀 RUN GRASSPANEL
# ===================================
if __name__ == "__main__":
    logging.info("🚀 GrassPanel v5.5 started on port 80")
    app.run(host="0.0.0.0", port=80, debug=False)