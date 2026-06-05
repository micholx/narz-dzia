import requests
import socket
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from tkinter.scrolledtext import ScrolledText
from datetime import datetime
import argparse
import time
import sys

MIN_DELAY_MS = 1
TIMEOUT_SECONDS = 5
MIN_SLEEP = 0.001


def current_time() -> str:
    return datetime.now().strftime("%H:%M:%S")


def resolve_host_port(target: str, protocol: str, port_arg: int | None) -> tuple[str, int]:
    if ":" in target and protocol in {"TCP", "UDP"}:
        host, port_text = target.rsplit(":", 1)
        if port_text.isdigit():
            return host, int(port_text)
    if port_arg is not None:
        return target, int(port_arg)
    # sensible defaults
    return target, (443 if protocol == "HTTPS" else 80)


def check_http(target: str) -> str:
    if not target.startswith(("http://", "https://")):
        target = f"http://{target}"
    response = requests.get(target, timeout=TIMEOUT_SECONDS)
    return f"HTTP {response.status_code}"


def check_https(target: str) -> str:
    if not target.startswith("https://"):
        target = f"https://{target.lstrip('http://').lstrip('https://')}"
    response = requests.get(target, timeout=TIMEOUT_SECONDS)
    return f"HTTPS {response.status_code}"


def check_tcp(target: str, port_arg: int | None) -> str:
    host, port = resolve_host_port(target, "TCP", port_arg)
    with socket.create_connection((host, port), timeout=TIMEOUT_SECONDS):
        pass
    return f"TCP OK {host}:{port}"


def check_udp(target: str, port_arg: int | None) -> str:
    host, port = resolve_host_port(target, "UDP", port_arg)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(TIMEOUT_SECONDS)
        sock.sendto(b"ping", (host, port))
    return f"UDP wysłano do {host}:{port}"


def perform_check(target: str, protocol: str, port_arg: int | None = None) -> str:
    if protocol == "HTTP":
        return check_http(target)
    if protocol == "HTTPS":
        return check_https(target)
    if protocol == "TCP":
        return check_tcp(target, port_arg)
    if protocol == "UDP":
        return check_udp(target, port_arg)
    raise ValueError("Nieznany protokół")

class RouterTesterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("")
        self.root.geometry("560x520")
        self.root.resizable(False, False)

        self.target_var = tk.StringVar()
        self.protocol_var = tk.StringVar(value="HTTP")
        self.port_var = tk.StringVar(value="80")
        self.rate_var = tk.StringVar(value="1")
        self.packet_rate = 1
        self.stop_event = threading.Event()
        self.request_count = 0

        self.setup_style()
        self.create_widgets()
        self.on_protocol_change()

    def setup_style(self):
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TButton", padding=8)
        style.configure("TLabel", padding=4)
        style.configure("TEntry", padding=4)
        style.configure("Status.TLabel", font=(None, 10, "bold"))

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding=14)
        main_frame.pack(fill=tk.BOTH, expand=True)

        input_frame = ttk.Frame(main_frame)
        input_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(input_frame, text="Adres routera lub URL:").grid(row=0, column=0, sticky=tk.W)
        self.target_entry = ttk.Entry(input_frame, textvariable=self.target_var, width=60)
        self.target_entry.grid(row=1, column=0, sticky=tk.EW, pady=(5, 8), columnspan=4)
        self.target_entry.focus()

        ttk.Label(input_frame, text="Protokół:").grid(row=2, column=0, sticky=tk.W)
        self.protocol_combo = ttk.Combobox(input_frame, textvariable=self.protocol_var, values=["HTTP", "HTTPS", "TCP", "UDP"], state="readonly", width=12)
        self.protocol_combo.grid(row=3, column=0, sticky=tk.W, pady=(4, 8))
        self.protocol_combo.bind("<<ComboboxSelected>>", self.on_protocol_change)

        ttk.Label(input_frame, text="Port (TCP/UDP):").grid(row=2, column=1, sticky=tk.W, padx=(12, 0))
        self.port_entry = ttk.Entry(input_frame, textvariable=self.port_var, width=12)
        self.port_entry.grid(row=3, column=1, sticky=tk.W, padx=(12, 0), pady=(4, 8))

        ttk.Label(input_frame, text="Pakiety/s (0 = bez przerwy):").grid(row=2, column=2, sticky=tk.W, padx=(12, 0))
        self.rate_entry = ttk.Entry(input_frame, textvariable=self.rate_var, width=12)
        self.rate_entry.grid(row=3, column=2, sticky=tk.W, padx=(12, 0), pady=(4, 8))

        ttk.Label(input_frame, text="Opis:").grid(row=2, column=3, sticky=tk.W, padx=(12, 0))
        self.help_label = ttk.Label(input_frame, text="HTTP: pełny URL | TCP/UDP: host i port", foreground="#555555")
        self.help_label.grid(row=3, column=3, sticky=tk.W, padx=(12, 0), pady=(4, 8))

        input_frame.columnconfigure(0, weight=1)
        input_frame.columnconfigure(1, weight=0)
        input_frame.columnconfigure(2, weight=0)
        input_frame.columnconfigure(3, weight=1)

        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=(0, 12))

        self.start_button = ttk.Button(control_frame, text="Start", command=self.start_test)
        self.start_button.pack(side=tk.LEFT)

        self.stop_button = ttk.Button(control_frame, text="Stop", command=self.stop_test, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=8)

        self.clear_button = ttk.Button(control_frame, text="Wyczyść historię", command=self.clear_history)
        self.clear_button.pack(side=tk.LEFT)

        status_frame = ttk.LabelFrame(main_frame, text="Status", padding=10)
        status_frame.pack(fill=tk.X, pady=(0, 12))

        self.status_label = ttk.Label(status_frame, text="Gotowy", style="Status.TLabel")
        self.status_label.pack(anchor=tk.W)

        self.info_label = ttk.Label(status_frame, text="Wysłane pakiety: 0 | Ostatni wynik: —")
        self.info_label.pack(anchor=tk.W, pady=(6, 0))

        log_frame = ttk.LabelFrame(main_frame, text="Historia wyników", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.history_box = ScrolledText(log_frame, wrap=tk.WORD, height=20, state=tk.DISABLED)
        self.history_box.pack(fill=tk.BOTH, expand=True)

    def on_protocol_change(self, event=None):
        protocol = self.protocol_var.get()
        self.port_entry.configure(state=tk.NORMAL)
        if protocol == "HTTP":
            self.port_var.set("80")
            self.port_entry.configure(state=tk.DISABLED)
            self.help_label.configure(text="HTTP: wpisz pełny URL, np. http://example.com")
        elif protocol == "HTTPS":
            self.port_var.set("443")
            self.port_entry.configure(state=tk.DISABLED)
            self.help_label.configure(text="HTTPS: wpisz pełny URL, np. https://example.com")
        else:
            self.port_entry.configure(state=tk.NORMAL)
            self.help_label.configure(text="TCP/UDP: wpisz host, np. 192.168.1.1")

    def append_history(self, text: str) -> None:
        self.history_box.configure(state=tk.NORMAL)
        self.history_box.insert(tk.END, text + "\n")
        self.history_box.configure(state=tk.DISABLED)
        self.history_box.see(tk.END)

    def start_test(self) -> None:
        target = self.target_var.get().strip()
        protocol = self.protocol_var.get()
        if not target:
            messagebox.showwarning("Brak adresu", "Podaj adres routera lub URL do przetestowania.")
            return

        if protocol in {"TCP", "UDP"} and not self.port_var.get().strip().isdigit():
            messagebox.showwarning("Błędny port", "Podaj poprawny numer portu dla TCP/UDP.")
            return

        if not self.rate_var.get().strip().isdigit() or int(self.rate_var.get().strip()) < 0:
            messagebox.showwarning("Błędna wartość pakietów", "Podaj liczbę pakietów na sekundę (0 = bez przerwy).")
            return

        self.packet_rate = int(self.rate_var.get().strip())
        self.request_count = 0
        self.clear_history()
        self.stop_event.clear()
        self.start_button.configure(state=tk.DISABLED)
        self.stop_button.configure(state=tk.NORMAL)
        self.status_label.configure(text="Test uruchomiony")
        self.info_label.configure(text=f"Wysłane pakiety: {self.request_count} | Ostatni wynik: —")
        self.append_history(f"[{self.current_time()}] Rozpoczęto test dla: {target} ({protocol})")
        self.schedule_next_check()

    def stop_test(self) -> None:
        self.stop_event.set()
        self.start_button.configure(state=tk.NORMAL)
        self.stop_button.configure(state=tk.DISABLED)
        self.status_label.configure(text="Test zatrzymany")
        self.append_history(f"[{self.current_time()}] Test zatrzymany.")

    def schedule_next_check(self) -> None:
        if self.stop_event.is_set():
            return
        thread = threading.Thread(target=self.check_router, daemon=True)
        thread.start()

    def check_router(self) -> None:
        target = self.target_var.get().strip()
        protocol = self.protocol_var.get()
        try:
            status_text = self.perform_check(target, protocol)
            result_text = f"[{self.current_time()}] {protocol} -> {status_text}"
        except Exception as exc:
            status_text = f"Błąd: {exc}"
            result_text = f"[{self.current_time()}] {protocol} -> {status_text}"

        self.request_count += 1
        self.root.after(0, lambda: self.update_results(result_text, status_text))
        if not self.stop_event.is_set():
            if self.packet_rate == 0:
                self.root.after(MIN_DELAY_MS, self.schedule_next_check)
            else:
                delay_ms = max(1, int(1000 / self.packet_rate))
                self.root.after(delay_ms, self.schedule_next_check)

    def perform_check(self, target: str, protocol: str) -> str:
        if protocol == "HTTP":
            return self.check_http(target)
        if protocol == "HTTPS":
            return self.check_https(target)
        if protocol == "TCP":
            return self.check_tcp(target)
        if protocol == "UDP":
            return self.check_udp(target)
        raise ValueError("Nieznany protokół")

    def check_http(self, target: str) -> str:
        if not target.startswith(("http://", "https://")):
            target = f"http://{target}"
        response = requests.get(target, timeout=TIMEOUT_SECONDS)
        return f"HTTP {response.status_code}"

    def check_https(self, target: str) -> str:
        if not target.startswith("https://"):
            target = f"https://{target.lstrip('http://').lstrip('https://')}"
        response = requests.get(target, timeout=TIMEOUT_SECONDS)
        return f"HTTPS {response.status_code}"

    def check_tcp(self, target: str) -> str:
        host, port = self.resolve_host_port(target)
        with socket.create_connection((host, port), timeout=TIMEOUT_SECONDS):
            pass
        return f"TCP OK {host}:{port}"

    def check_udp(self, target: str) -> str:
        host, port = self.resolve_host_port(target)
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(TIMEOUT_SECONDS)
            sock.sendto(b"ping", (host, port))
        return f"UDP wysłano do {host}:{port}"

    def resolve_host_port(self, target: str) -> tuple[str, int]:
        if ":" in target and self.protocol_var.get() in {"TCP", "UDP"}:
            host, port_text = target.rsplit(":", 1)
            if port_text.isdigit():
                return host, int(port_text)
        port = int(self.port_var.get().strip())
        return target, port

    def update_results(self, result_text: str, status_text: str) -> None:
        self.append_history(result_text)
        self.info_label.configure(text=f"Wysłane pakiety: {self.request_count} | Ostatni wynik: {status_text}")

    def clear_history(self) -> None:
        self.history_box.configure(state=tk.NORMAL)
        self.history_box.delete("1.0", tk.END)
        self.history_box.configure(state=tk.DISABLED)

    @staticmethod
    def current_time() -> str:
        return datetime.now().strftime("%H:%M:%S")


def main() -> None:
    root = tk.Tk()
    RouterTesterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
