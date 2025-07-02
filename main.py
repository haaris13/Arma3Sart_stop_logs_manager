import tkinter as tk
from tkinter import messagebox, scrolledtext, filedialog
import subprocess
import os
import time
import threading
import psutil
import json

CONFIG_FILE = "config.json"
DEFAULT_CONFIG = {
    "ARMA_DIR": "",
    "STEAMCMD_PATH": "",
    "STEAM_USER": "anonymous",
    "APP_ID": 233780,
    "RESTART_INTERVAL": 21600,
    "LOG_DIR": "logs",
    "DISCORD_WEBHOOK": ""
}

# === CONFIGURATION ===
def load_config():
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w") as f:
            json.dump(DEFAULT_CONFIG, f, indent=4)
        return DEFAULT_CONFIG.copy()
    with open(CONFIG_FILE) as f:
        return json.load(f)

def save_config(conf):
    with open(CONFIG_FILE, "w") as f:
        json.dump(conf, f, indent=4)

config = load_config()
PID_FILE = os.path.join(config["ARMA_DIR"], "server.pid")

# === FONCTIONS SERVEUR ===
def is_server_running():
    if os.path.isfile(PID_FILE):
        with open(PID_FILE) as f:
            pid = int(f.read())
        return psutil.pid_exists(pid)
    return False

def get_last_log():
    try:
        log_dir = config["LOG_DIR"]
        files = sorted([f for f in os.listdir(log_dir) if f.startswith("server_")], reverse=True)
        if files:
            with open(os.path.join(log_dir, files[0]), "r") as f:
                return f.read()[-3000:]
        return "Aucun log trouvé."
    except Exception as e:
        return f"Erreur lecture log : {e}"

def start_server():
    if is_server_running():
        messagebox.showinfo("Info", "Le serveur est déjà lancé.")
        return
    log_dir = config["LOG_DIR"]
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"server_{time.strftime('%Y-%m-%d_%H-%M-%S')}.log")
    with open(log_file, "w") as f:
        proc = subprocess.Popen([
            os.path.join(config["ARMA_DIR"], "arma3server"),
            "-config=server.cfg", "-port=2302", "-name=server", "-mod=@mods"
        ], cwd=config["ARMA_DIR"], stdout=f, stderr=subprocess.STDOUT)
        with open(PID_FILE, "w") as pidf:
            pidf.write(str(proc.pid))
    messagebox.showinfo("Serveur", "Serveur démarré.")

def stop_server():
    if not is_server_running():
        messagebox.showinfo("Info", "Le serveur n'est pas actif.")
        return
    with open(PID_FILE) as f:
        pid = int(f.read())
    try:
        psutil.Process(pid).terminate()
        os.remove(PID_FILE)
        messagebox.showinfo("Serveur", "Serveur arrêté.")
    except Exception as e:
        messagebox.showerror("Erreur", f"Impossible d'arrêter le serveur : {e}")

def restart_server():
    stop_server()
    time.sleep(3)
    start_server()

def update_server():
    stop_server()
    subprocess.run([
        config["STEAMCMD_PATH"],
        "+login", config["STEAM_USER"],
        "+force_install_dir", config["ARMA_DIR"],
        "+app_update", str(config["APP_ID"]), "validate",
        "+quit"
    ])
    messagebox.showinfo("Mise à jour", "Mise à jour terminée.")
    start_server()

def auto_restart_loop():
    while True:
        start_server()
        time.sleep(config["RESTART_INTERVAL"])
        stop_server()

def launch_loop_thread():
    t = threading.Thread(target=auto_restart_loop, daemon=True)
    t.start()
    messagebox.showinfo("Loop", f"Redémarrage automatique lancé ({config['RESTART_INTERVAL']//3600}h).")

# === FENÊTRE DE CONFIGURATION ===
def open_config_window():
    win = tk.Toplevel()
    win.title("Configuration")
    win.geometry("500x400")

    entries = {}
    fields = [
        ("ARMA_DIR", "Dossier Arma 3"),
        ("STEAMCMD_PATH", "Chemin vers steamcmd.sh"),
        ("STEAM_USER", "Utilisateur Steam"),
        ("APP_ID", "ID du serveur Steam"),
        ("RESTART_INTERVAL", "Intervalle redémarrage (s)"),
        ("LOG_DIR", "Dossier de logs"),
        ("DISCORD_WEBHOOK", "Webhook Discord (optionnel)")
    ]

    for i, (key, label) in enumerate(fields):
        tk.Label(win, text=label).grid(row=i, column=0, sticky='w', padx=10, pady=5)
        e = tk.Entry(win, width=50)
        e.grid(row=i, column=1, padx=10)
        e.insert(0, str(config.get(key, "")))
        entries[key] = e

    def save_and_close():
        for k in entries:
            val = entries[k].get().strip()
            config[k] = int(val) if k == "RESTART_INTERVAL" else val
        save_config(config)
        messagebox.showinfo("Config", "Configuration enregistrée.")
        win.destroy()

    tk.Button(win, text="Enregistrer", command=save_and_close).grid(row=len(fields), column=0, columnspan=2, pady=20)

# === INTERFACE PRINCIPALE ===
def create_gui():
    root = tk.Tk()
    root.title("Gestionnaire Arma 3 Server")
    root.geometry("600x500")

    tk.Button(root, text="Démarrer le serveur", width=25, command=start_server).pack(pady=5)
    tk.Button(root, text="Arrêter le serveur", width=25, command=stop_server).pack(pady=5)
    tk.Button(root, text="Redémarrer", width=25, command=restart_server).pack(pady=5)
    tk.Button(root, text="Mettre à jour via SteamCMD", width=25, command=update_server).pack(pady=5)
    tk.Button(root, text="Lancer redémarrage auto", width=25, command=launch_loop_thread).pack(pady=5)
    tk.Button(root, text="Configurer", width=25, command=open_config_window).pack(pady=5)

    tk.Label(root, text="Derniers logs :").pack(pady=10)
    log_text = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=70, height=10)
    log_text.pack()

    def refresh_logs():
        log_text.delete(1.0, tk.END)
        log_text.insert(tk.END, get_last_log())

    tk.Button(root, text="Rafraîchir les logs", command=refresh_logs).pack(pady=5)

    root.mainloop()

# === MAIN ===
if __name__ == "__main__":
    create_gui()
