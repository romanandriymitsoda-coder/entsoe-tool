import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import os
import requests
from urllib.parse import urljoin
from datetime import datetime
from export_combined_excel import export_combined_excel

SETTINGS_FILE = "settings.json"
FMS_BASE_URL_DEFAULT = "https://fms.tp.entsoe.eu/"
KEYCLOAK_TOKEN_URL = "https://keycloak.tp.entsoe.eu/realms/tp/protocol/openid-connect/token"
USERNAME = "test"
PASSWORD = "test"

def load_settings():
    default_download = os.path.join(os.path.expanduser("~"), "Downloads")
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r") as f:
            return json.load(f)
    return {
        "host": FMS_BASE_URL_DEFAULT,
        "username": USERNAME,
        "password": PASSWORD,
        "download_path": default_download,
    }

def save_settings(data):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(data, f)

def generate_month_keys(start_year, start_month, end_year, end_month):
    try:
        start = datetime(int(start_year), int(start_month), 1)
        end = datetime(int(end_year), int(end_month), 1)
    except ValueError:
        return []
    
    keys = []
    while start <= end:
        keys.append(start.strftime("%Y_%m"))
        if start.month == 12:
            start = datetime(start.year + 1, 1, 1)
        else:
            start = datetime(start.year, start.month + 1, 1)
    return keys

def _get_bearer_token(username: str, password: str, timeout: int = 30) -> str:
    data = {
        "client_id": "tp-fms-public",
        "grant_type": "password",
        "username": username,
        "password": password,
    }
    resp = requests.post(KEYCLOAK_TOKEN_URL, data=data, timeout=timeout)
    resp.raise_for_status()
    payload = resp.json()
    return payload.get("access_token", "")


def _list_folder(fms_base_url: str, token: str, path: str, page_size: int = 5000, timeout: int = 60):
    url = urljoin(fms_base_url, "listFolder")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    if not path.endswith("/"):
        path = path + "/"
    body = {
        "path": path,
        "sorterList": [
            {"key": "periodCovered.from", "ascending": True}
        ],
        "pageInfo": {"pageIndex": 0, "pageSize": page_size},
    }
    resp = requests.post(url, headers=headers, json=body, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def _download_file_by_id(fms_base_url: str, token: str, file_id: str, local_path: str, timeout: int = 300):
    url = urljoin(fms_base_url, "downloadFileContent")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    body = {
        "fileIdList": [file_id],
        "topLevelFolder": "TP_export",
        "downloadAsZip": False,
    }
    with requests.post(url, headers=headers, json=body, stream=True, timeout=timeout) as r:
        r.raise_for_status()
        with open(local_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)


def download_files_by_month(settings, remote_folder, pattern_keyword, month_keys):
    try:
        username = settings.get("username", USERNAME)
        password = settings.get("password", PASSWORD)
        fms_base = settings.get("host", FMS_BASE_URL_DEFAULT)

        if not username or not password:
            return False, "Chybí uživatelské jméno nebo heslo. Doplňte chybějící údaj v Nastavení."

        token = _get_bearer_token(username, password)
        if not token:
            return False, "Nepodařilo se získat autorizační token."

        folder_path = remote_folder if remote_folder.startswith("/TP_export/") else f"/TP_export/{remote_folder}"
        folder_json = _list_folder(fms_base, token, folder_path)
        items = folder_json.get("contentItemList", [])

        to_download = []
        for item in items:
            name = item.get("name", "")
            if not name:
                continue
            if pattern_keyword in name and any(key in name for key in month_keys):
                file_id = item.get("fileId")
                if file_id:
                    to_download.append((file_id, name))

        if not to_download:
            return False, "Nebyly nalezeny žádné soubory pro zvolené období."

        os.makedirs(settings['download_path'], exist_ok=True)
        for file_id, name in to_download:
            local_path = os.path.join(settings['download_path'], name)
            _download_file_by_id(fms_base, token, file_id, local_path)

        return True, None

    except requests.exceptions.SSLError as e:
        return False, (
            "Chyba ověření TLS certifikátu (SSL). "
            "Zkuste nastavit cestu k firemnímu CA (PEM) do Nastavení nebo dočasně vypnout ověřování."
        )
    except requests.HTTPError as e:
        try:
            detail = e.response.text
        except Exception:
            detail = str(e)
        return False, f"Chyba při stahování (HTTP): {detail}"
    except Exception as e:
        return False, f"Chyba při stahování: {str(e)}"


class FileLibraryDownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ENTSO-E File Library Downloader")

        self.settings = load_settings()

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(expand=1, fill="both")

        self.create_download_tab()
        self.create_settings_tab()
        self.create_description_tab()

    def create_download_tab(self):
        self.download_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.download_tab, text="Stažení dat")

        ttk.Label(self.download_tab, text="Vyberte typ dat:").grid(row=0, column=0, sticky="w", padx=10, pady=(10, 0))
        self.include_reserves = tk.BooleanVar()
        self.include_energy = tk.BooleanVar()
        ttk.Checkbutton(self.download_tab, text="Regulační zálohy", variable=self.include_reserves).grid(row=1, column=0, sticky="w", padx=20)
        ttk.Checkbutton(self.download_tab, text="Regulační energie", variable=self.include_energy).grid(row=2, column=0, sticky="w", padx=20)

        ttk.Label(self.download_tab, text="Období (měsíc a rok):").grid(row=3, column=0, sticky="w", padx=10, pady=(10, 0))
        self.start_month = tk.StringVar()
        self.start_year = tk.StringVar()
        self.end_month = tk.StringVar()
        self.end_year = tk.StringVar()

        months = ["Leden", "Únor", "Březen", "Duben", "Květen", "Červen", "Červenec", "Srpen", "Září", "Říjen", "Listopad", "Prosinec"]
        self.months_map = {m: f"{i+1:02d}" for i, m in enumerate(months)}
        current_year = datetime.now().year
        years = [str(y) for y in range(2022, current_year + 1)]

        ttk.Label(self.download_tab, text="Od:").grid(row=4, column=0, sticky="w", padx=20)
        self.start_month_cb = ttk.Combobox(self.download_tab, values=months, textvariable=self.start_month, width=12, state="readonly")
        self.start_year_cb = ttk.Combobox(self.download_tab, values=years, textvariable=self.start_year, width=6, state="readonly")
        self.start_month_cb.grid(row=5, column=0, sticky="w", padx=20)
        self.start_year_cb.grid(row=5, column=0, sticky="e", padx=20)

        ttk.Label(self.download_tab, text="Do:").grid(row=6, column=0, sticky="w", padx=20)
        self.end_month_cb = ttk.Combobox(self.download_tab, values=months, textvariable=self.end_month, width=12, state="readonly")
        self.end_year_cb = ttk.Combobox(self.download_tab, values=years, textvariable=self.end_year, width=6, state="readonly")
        self.end_month_cb.grid(row=7, column=0, sticky="w", padx=20)
        self.end_year_cb.grid(row=7, column=0, sticky="e", padx=20)

        ttk.Button(self.download_tab, text="Zpracovat data", command=self.download_data).grid(row=8, column=0, pady=20)

    def create_settings_tab(self):
        self.settings_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.settings_tab, text="Nastavení")

        ttk.Label(self.settings_tab, text="Cílová složka:").grid(row=0, column=0, sticky="w")
        self.path_var = tk.StringVar(value=self.settings.get("download_path", ""))
        self.entry_path = ttk.Entry(self.settings_tab, textvariable=self.path_var, width=40)
        self.entry_path.grid(row=0, column=1)
        ttk.Button(self.settings_tab, text="Procházet", command=self.browse_folder).grid(row=0, column=2)

        ttk.Label(self.settings_tab, text="FMS host (API):").grid(row=1, column=0, sticky="w")
        self.host_var = tk.StringVar(value=self.settings.get("host", ""))
        ttk.Entry(self.settings_tab, textvariable=self.host_var, width=40).grid(row=1, column=1, sticky="w")

        ttk.Label(self.settings_tab, text="Uživatelské jméno:").grid(row=2, column=0, sticky="w")
        self.user_var = tk.StringVar(value=self.settings.get("username", ""))
        ttk.Entry(self.settings_tab, textvariable=self.user_var, width=40).grid(row=2, column=1, sticky="w")

        ttk.Label(self.settings_tab, text="Heslo:").grid(row=3, column=0, sticky="w")
        self.pass_var = tk.StringVar(value=self.settings.get("password", ""))
        ttk.Entry(self.settings_tab, textvariable=self.pass_var, show="*", width=40).grid(row=3, column=1, sticky="w")

        ttk.Button(self.settings_tab, text="Uložit nastavení", command=lambda: self.save(show_message=True)).grid(row=4, column=1, pady=10, sticky="w")

    def create_description_tab(self):
        self.description_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.description_tab, text="Popis dat")

        text = (
            "Data v hodinových intervalech jsou vypočítána jako aritmetické průměry.\n"
            "Zdrojem dat je Transparency Platform ENTSO-E.\n\n"
            "Zdrojová data pro regulační zálohy:\n" 
            "AmountAndPricesPaidOfBalancingReservesUnderContract.\n\n"
            "Zdrojová data pro regulační energii:\n"
            "PricesOfActivatedBalancingEnergy.\n\n\n"
            "Autor programu: Roman Andriy Mitsoda\n\n"
            "@EY ~~Všechna práva vyhrazena."
        )

        label = ttk.Label(self.description_tab, text=text, justify="left", wraplength=500)
        label.pack(padx=20, pady=20, anchor="w")

    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.path_var.set(folder)

    def save(self, show_message=True):
        data = {
            "download_path": self.path_var.get(),
            "host": self.host_var.get(),
            "username": self.user_var.get(),
            "password": self.pass_var.get()
        }
        save_settings(data)
        self.settings = data
        if show_message:
            messagebox.showinfo("Uloženo", "Nastavení byla uložena.")

    def download_data(self):
        self.save(show_message=False)

        sm = self.months_map.get(self.start_month.get())
        em = self.months_map.get(self.end_month.get())
        sy = self.start_year.get()
        ey = self.end_year.get()

        if not all([sm, em, sy, ey]):
            messagebox.showerror("Chyba", "Zadejte prosím celé období (měsíc a rok).")
            return

        try:
            start_date = datetime(int(sy), int(sm), 1)
            end_date = datetime(int(ey), int(em), 1)
            if start_date > end_date:
                messagebox.showerror("Chyba", "Počáteční měsíc musí předcházet koncovému.")
                return
        except ValueError:
            messagebox.showerror("Chyba", "Neplatné datum.")
            return

        if not self.include_reserves.get() and not self.include_energy.get():
            messagebox.showinfo("Hotovo", "Nebyla vybrána žádná datová sada.")
            return

        messagebox.showinfo("Zpracování", "Skoč si na kafe, data se zpracovávají...")

        keys = generate_month_keys(sy, sm, ey, em)
        reserves_success = False
        energy_success = False

        if self.include_reserves.get():
            success, msgError = download_files_by_month(
                self.settings,
                "/TP_export/AmountAndPricesPaidOfBalancingReservesUnderContract_17.1.B_C_r3",
                "AmountAndPricesPaidOfBalancingReservesUnderContract",
                keys
            )
            if success:
                reserves_success = True
            else:
                messagebox.showerror("Chyba", msgError)

        if self.include_energy.get():
            success, msgError = download_files_by_month(
                self.settings,
                "/TP_export/PricesOfActivatedBalancingEnergy_17.1.F_r3",
                "PricesOfActivatedBalancingEnergy",
                keys
            )
            if success:
                energy_success = True
            else:
                messagebox.showerror("Chyba", msgError)
                    

        if (self.include_reserves.get() and reserves_success) or (self.include_energy.get() and energy_success):
            excel_path = export_combined_excel(self.settings["download_path"], start_date, end_date)
            if excel_path:
                messagebox.showinfo("Hotovo", f"Výstupní Excel byl uložen zde: {excel_path}")
            else:
                messagebox.showinfo("Hotovo", "Filtrace: Nebyla nalezena žádná použitelná data.")
        else:
            messagebox.showinfo("Hotovo", "Nebyla nalezena žádná použitelná data.")

if __name__ == "__main__":
    root = tk.Tk()
    app = FileLibraryDownloaderApp(root)
    root.mainloop()
