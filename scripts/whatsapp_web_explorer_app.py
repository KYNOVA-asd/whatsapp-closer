"""Desktop sales panel demo for the whatsapp-web-explorer branch."""

from __future__ import annotations

import csv
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from tkinter import BOTH, END, LEFT, W, X, filedialog, messagebox
import tkinter as tk
from tkinter import ttk


ROOT = Path(__file__).resolve().parent.parent
LOCAL_DIR = ROOT / ".local" / "whatsapp-web-explorer"
EDGE_PROFILE = ROOT / ".local" / "edge-whatsapp-profile"
LEADS_FILE = LOCAL_DIR / "leads.json"
CONFIG_FILE = LOCAL_DIR / "config.json"
BLASTER_FILE = LOCAL_DIR / "blaster.json"
EDGE_SCRIPT = ROOT / "scripts" / "abrir_whatsapp_web_edge.ps1"
BRIDGE_SCRIPT = ROOT / "scripts" / "whatsapp_web_bridge.py"

BG = "#eeeae3"
GREEN = "#355244"
GOLD = "#cfc47c"
PANEL = "#fbf8f0"
INK = "#111111"
MUTED = "#5f615b"
WHITE = "#ffffff"
RED = "#9f2d2d"


@dataclass
class Lead:
    nombre: str
    telefono: str
    etapa: str
    ultimo_mensaje: str
    pendiente: str
    score: int


class ExplorerApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("WhatsApp Web Explorer · sales workspace")
        self.geometry("1320x820")
        self.minsize(1120, 700)
        self.configure(bg=BG)
        self.leads: list[Lead] = []
        self.selected_index: int | None = None
        self.visible_chats: list[dict] = []
        self.extract_candidates_cache: list[dict] = []
        self.extract_participants_cache: list[dict] = []
        self.blast_messages: list[dict] = []
        self.blast_message_source_indices: list[int] = []
        self.view_buttons: dict[str, ttk.Button] = {}

        self._configure_style()
        self._build()
        self._load_leads()
        self.show_view("vendedor")

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(".", font=("Segoe UI", 10), background=BG, foreground=INK)
        style.configure("TFrame", background=BG)
        style.configure("Panel.TFrame", background=PANEL, relief="flat", borderwidth=0)
        style.configure("Band.TFrame", background=GREEN)
        style.configure("Title.TLabel", background=BG, foreground=INK, font=("Segoe UI", 23, "bold"))
        style.configure("Muted.TLabel", background=BG, foreground=MUTED)
        style.configure("PanelTitle.TLabel", background=PANEL, foreground=INK, font=("Segoe UI", 13, "bold"))
        style.configure("PanelMuted.TLabel", background=PANEL, foreground=MUTED, font=("Segoe UI", 9))
        style.configure("Metric.TLabel", background=GREEN, foreground=WHITE, font=("Segoe UI", 14, "bold"))
        style.configure("MetricSmall.TLabel", background=GREEN, foreground="#dce5dd", font=("Segoe UI", 9))
        style.configure("TButton", padding=(12, 8), background=PANEL, foreground=INK)
        style.configure("Accent.TButton", padding=(14, 9), background=GREEN, foreground=WHITE)
        style.map("Accent.TButton", background=[("active", "#263d32")])
        style.configure("Gold.TButton", padding=(14, 9), background=GOLD, foreground=INK)
        style.configure("Danger.TButton", padding=(14, 9), background=RED, foreground=WHITE)
        style.map("Danger.TButton", background=[("active", "#7f2020")])
        style.configure("Nav.TButton", padding=(16, 10), background="#ded8cd", foreground=INK)
        style.configure("NavActive.TButton", padding=(16, 10), background=GREEN, foreground=WHITE)
        style.configure("Treeview", rowheight=36, fieldbackground=PANEL, background=PANEL, foreground=INK, borderwidth=0)
        style.configure("Treeview.Heading", background="#ddd7cb", foreground=INK, font=("Segoe UI", 9, "bold"))

    def _build(self) -> None:
        root = ttk.Frame(self, padding=20)
        root.pack(fill=BOTH, expand=True)

        header = ttk.Frame(root)
        header.pack(fill=X, pady=(0, 14))
        title_area = ttk.Frame(header)
        title_area.pack(side=LEFT, fill=X, expand=True)
        ttk.Label(title_area, text="WhatsApp Web Explorer", style="Title.TLabel").pack(anchor=W)
        ttk.Label(
            title_area,
            text="Sales workspace v2 · vendedor real, blaster consentido, extractor de afiliados y configuracion.",
            style="Muted.TLabel",
        ).pack(anchor=W, pady=(3, 0))
        actions = ttk.Frame(header)
        actions.pack(side=tk.RIGHT)
        ttk.Button(actions, text="Abrir WhatsApp Web", style="Accent.TButton", command=self.open_edge).pack(side=LEFT, padx=(0, 8))
        ttk.Button(actions, text="⟳", width=3, command=self.refresh_from_whatsapp).pack(side=LEFT, padx=(0, 8))
        ttk.Button(actions, text="Guardar", style="Gold.TButton", command=self.save_leads).pack(side=LEFT)

        nav = ttk.Frame(root)
        nav.pack(fill=X, pady=(0, 12))
        for key, text in [("vendedor", "Vendedor"), ("blaster", "Blaster"), ("extractor", "Extractor afiliados"), ("config", "Config")]:
            btn = ttk.Button(nav, text=text, style="Nav.TButton", command=lambda name=key: self.show_view(name))
            btn.pack(side=LEFT, padx=(0, 8))
            self.view_buttons[key] = btn

        self.content = ttk.Frame(root)
        self.content.pack(fill=BOTH, expand=True)
        self.views = {
            "vendedor": self._build_vendedor(self.content),
            "blaster": self._build_blaster(self.content),
            "extractor": self._build_extractor(self.content),
            "config": self._build_config(self.content),
        }

    def _panel(self, parent: ttk.Frame, padding: int = 14) -> ttk.Frame:
        return ttk.Frame(parent, style="Panel.TFrame", padding=padding)

    def _build_vendedor(self, parent: ttk.Frame) -> ttk.Frame:
        view = ttk.Frame(parent)
        view.columnconfigure(0, weight=5)
        view.columnconfigure(1, weight=4)
        view.rowconfigure(1, weight=1)

        metrics = ttk.Frame(view, style="Band.TFrame", padding=14)
        metrics.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        self.status_var = tk.StringVar(value="Edge: pendiente")
        self.lead_count_var = tk.StringVar(value="0")
        self.pending_count_var = tk.StringVar(value="0")
        for label, var in [("Leads", self.lead_count_var), ("Pendientes", self.pending_count_var)]:
            box = ttk.Frame(metrics, style="Band.TFrame")
            box.pack(side=LEFT, padx=(0, 34))
            ttk.Label(box, textvariable=var, style="Metric.TLabel").pack(anchor=W)
            ttk.Label(box, text=label, style="MetricSmall.TLabel").pack(anchor=W)
        ttk.Label(metrics, textvariable=self.status_var, style="MetricSmall.TLabel").pack(side=tk.RIGHT)

        crm = self._panel(view)
        crm.grid(row=1, column=0, sticky="nsew", padx=(0, 12))
        crm.rowconfigure(2, weight=1)
        crm.columnconfigure(0, weight=1)
        top = ttk.Frame(crm, style="Panel.TFrame")
        top.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        ttk.Label(top, text="Bandeja de ventas", style="PanelTitle.TLabel").pack(side=LEFT)
        ttk.Button(top, text="Importar CSV", command=self.import_csv).pack(side=tk.RIGHT, padx=(8, 0))
        ttk.Button(top, text="Leer WhatsApp", command=self.refresh_from_whatsapp).pack(side=tk.RIGHT)
        ttk.Label(crm, text="Selecciona un lead para leer WhatsApp real, generar borrador y cerrar seguimiento.", style="PanelMuted.TLabel").grid(row=1, column=0, sticky="w", pady=(0, 8))

        columns = ("nombre", "telefono", "etapa", "pendiente", "score")
        self.tree = ttk.Treeview(crm, columns=columns, show="headings", selectmode="browse")
        for col, label, width in [
            ("nombre", "Lead / chat", 260),
            ("telefono", "Contacto", 170),
            ("etapa", "Etapa", 120),
            ("pendiente", "Pendiente", 280),
            ("score", "Score", 70),
        ]:
            self.tree.heading(col, text=label)
            self.tree.column(col, width=width, anchor=W)
        self.tree.grid(row=2, column=0, sticky="nsew")
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        work = self._panel(view)
        work.grid(row=1, column=1, sticky="nsew")
        work.columnconfigure(0, weight=1)
        work.rowconfigure(2, weight=2)
        work.rowconfigure(4, weight=1)
        ttk.Label(work, text="Ventas real", style="PanelTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(work, text="Lee el chat seleccionado, extrae quien escribio y envia solo con confirmacion.", style="PanelMuted.TLabel").grid(row=1, column=0, sticky="w", pady=(2, 8))
        self.detail = tk.Text(work, height=12, wrap="word", bd=0, bg="#f4efe6", fg=INK, padx=12, pady=12)
        self.detail.grid(row=2, column=0, sticky="nsew")
        btns = ttk.Frame(work, style="Panel.TFrame")
        btns.grid(row=3, column=0, sticky="ew", pady=10)
        ttk.Button(btns, text="Leer chat seleccionado", style="Accent.TButton", command=self.read_selected_chat).pack(side=LEFT, padx=(0, 8))
        ttk.Button(btns, text="Leer chat activo", command=self.read_active_chat).pack(side=LEFT, padx=(0, 8))
        ttk.Button(btns, text="Borrador IA", style="Gold.TButton", command=self.generate_draft).pack(side=LEFT)
        self.draft = tk.Text(work, height=8, wrap="word", bd=0, bg="#e7eee8", fg=INK, padx=12, pady=12)
        self.draft.grid(row=4, column=0, sticky="nsew")
        send_row = ttk.Frame(work, style="Panel.TFrame")
        send_row.grid(row=5, column=0, sticky="ew", pady=(10, 0))
        ttk.Button(send_row, text="Enviar borrador real", style="Danger.TButton", command=self.send_draft_real).pack(side=LEFT, padx=(0, 8))
        ttk.Button(send_row, text="Marcar revisado", command=self.mark_reviewed).pack(side=LEFT)
        return view

    def _build_blaster(self, parent: ttk.Frame) -> ttk.Frame:
        view = ttk.Frame(parent)
        view.rowconfigure(0, weight=1)
        view.columnconfigure(0, weight=1)

        tabs = ttk.Notebook(view)
        tabs.grid(row=0, column=0, sticky="nsew")

        dashboard = self._panel(tabs)
        dashboard.columnconfigure((0, 1, 2, 3), weight=1)
        ttk.Label(dashboard, text="Dashboard blaster", style="PanelTitle.TLabel").grid(row=0, column=0, columnspan=4, sticky="w")
        ttk.Label(dashboard, text="Flujo: importar numeros, elegir plantilla de campana y preparar cola con revision.", style="PanelMuted.TLabel").grid(row=1, column=0, columnspan=4, sticky="w", pady=(2, 14))
        self.blast_contacts_var = tk.StringVar(value="0")
        self.blast_ready_var = tk.StringVar(value="0")
        self.blast_messages_var = tk.StringVar(value="0")
        self.blast_queue_var = tk.StringVar(value="0")
        for idx, (label, var) in enumerate([
            ("Contactos", self.blast_contacts_var),
            ("Con telefono", self.blast_ready_var),
            ("Plantillas", self.blast_messages_var),
            ("En cola", self.blast_queue_var),
        ]):
            box = ttk.Frame(dashboard, style="Band.TFrame", padding=12)
            box.grid(row=2, column=idx, sticky="ew", padx=(0, 10))
            ttk.Label(box, textvariable=var, style="Metric.TLabel").pack(anchor=W)
            ttk.Label(box, text=label, style="MetricSmall.TLabel").pack(anchor=W)
        steps = tk.Text(dashboard, height=10, wrap="word", bd=0, bg=PANEL, fg=INK, padx=12, pady=12)
        steps.grid(row=3, column=0, columnspan=4, sticky="nsew", pady=(16, 0))
        steps.insert(END, "1. Importa CSV en Preparar numeros.\n2. Crea o selecciona una plantilla tipo Campana.\n3. Prepara cola y revisa antes de enviar.\n4. Mensajes rapidos se guardan para respuestas manuales, no para blast masivo.")
        steps.configure(state="disabled")

        templates = self._panel(tabs)
        templates.columnconfigure(0, weight=1)
        templates.rowconfigure(6, weight=1)
        ttk.Label(templates, text="Plantillas y mensajes rapidos", style="PanelTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(templates, text="Campana arma cola; Mensaje rapido sirve como texto reutilizable.", style="PanelMuted.TLabel").grid(row=1, column=0, sticky="w", pady=(2, 10))

        product_row = ttk.Frame(templates, style="Panel.TFrame")
        product_row.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        product_row.columnconfigure(1, weight=1)
        ttk.Label(product_row, text="Producto", style="PanelMuted.TLabel", width=10).grid(row=0, column=0, sticky="w")
        self.blast_product_var = tk.StringVar(value="tu servicio")
        ttk.Entry(product_row, textvariable=self.blast_product_var).grid(row=0, column=1, sticky="ew")

        filters = ttk.Frame(templates, style="Panel.TFrame")
        filters.grid(row=3, column=0, sticky="ew", pady=(0, 10))
        ttk.Label(filters, text="Ver", style="PanelMuted.TLabel").pack(side=LEFT, padx=(0, 6))
        self.blast_message_filter_var = tk.StringVar(value="Todos")
        filter_box = ttk.Combobox(filters, textvariable=self.blast_message_filter_var, values=["Todos", "Campanas", "Rapidos"], width=12, state="readonly")
        filter_box.pack(side=LEFT, padx=(0, 12))
        filter_box.bind("<<ComboboxSelected>>", lambda _event: self.refresh_blast_message_list())
        ttk.Label(filters, text="Tipo", style="PanelMuted.TLabel").pack(side=LEFT, padx=(0, 6))
        self.blast_message_type_var = tk.StringVar(value="Campana")
        ttk.Combobox(filters, textvariable=self.blast_message_type_var, values=["Campana", "Rapido"], width=12, state="readonly").pack(side=LEFT)

        library = ttk.Frame(templates, style="Panel.TFrame")
        library.grid(row=4, column=0, sticky="ew", pady=(0, 10))
        library.columnconfigure(0, weight=1)
        self.blast_message_list = tk.Listbox(library, height=5, bd=0, bg="#f4efe6", fg=INK, highlightthickness=1, highlightcolor=GOLD)
        self.blast_message_list.grid(row=0, column=0, sticky="ew")
        self.blast_message_list.bind("<<ListboxSelect>>", self.on_blast_message_select)
        library_actions = ttk.Frame(library, style="Panel.TFrame")
        library_actions.grid(row=0, column=1, sticky="ns", padx=(8, 0))
        ttk.Button(library_actions, text="Nuevo", command=self.add_blast_message).pack(fill=X, pady=(0, 6))
        ttk.Button(library_actions, text="Actualizar", command=self.update_blast_message).pack(fill=X, pady=(0, 6))
        ttk.Button(library_actions, text="Borrar", style="Danger.TButton", command=self.delete_blast_message).pack(fill=X)

        name_row = ttk.Frame(templates, style="Panel.TFrame")
        name_row.grid(row=5, column=0, sticky="ew", pady=(0, 8))
        name_row.columnconfigure(1, weight=1)
        ttk.Label(name_row, text="Nombre", style="PanelMuted.TLabel", width=10).grid(row=0, column=0, sticky="w")
        self.blast_message_name_var = tk.StringVar(value="Promo principal")
        ttk.Entry(name_row, textvariable=self.blast_message_name_var).grid(row=0, column=1, sticky="ew")

        self.blast_template = tk.Text(templates, height=12, wrap="word", bd=0, bg="#f4efe6", fg=INK, padx=12, pady=12)
        self.blast_template.grid(row=6, column=0, sticky="nsew")
        self.blast_template.insert(END, "Hola {nombre}, tenemos una promo de {producto}. Si quieres mas info responde SI.")
        self.blast_messages = [
            {
                "name": "Promo principal",
                "type": "campaign",
                "template": self.blast_template.get("1.0", END).strip(),
            }
        ]
        self.refresh_blast_message_list()
        self.blast_message_list.selection_set(0)

        actions = ttk.Frame(templates, style="Panel.TFrame")
        actions.grid(row=7, column=0, sticky="ew", pady=(12, 0))
        ttk.Button(actions, text="Guardar todo", style="Gold.TButton", command=self.save_blaster_state).pack(side=LEFT)

        numbers = self._panel(tabs)
        numbers.columnconfigure(0, weight=1)
        numbers.rowconfigure(2, weight=1)
        ttk.Label(numbers, text="Preparar numeros para mensajes", style="PanelTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(numbers, text="Importa CSV compatible, arma cola y simula ronda antes de enviar.", style="PanelMuted.TLabel").grid(row=1, column=0, sticky="w", pady=(2, 10))
        queue_wrap = ttk.Frame(numbers, style="Panel.TFrame")
        queue_wrap.grid(row=2, column=0, sticky="nsew")
        queue_wrap.columnconfigure(0, weight=1)
        queue_wrap.rowconfigure(0, weight=1)
        self.queue = tk.Listbox(queue_wrap, bd=0, bg=PANEL, fg=INK, highlightthickness=1, highlightcolor=GOLD)
        self.queue.grid(row=0, column=0, sticky="nsew")
        for rule in ["Regla: consentimiento o relacion previa.", "Regla: limite diario y pausas.", "Regla: baja/stop cancela seguimiento."]:
            self.queue.insert(END, rule)
        numbers_actions = ttk.Frame(numbers, style="Panel.TFrame")
        numbers_actions.grid(row=3, column=0, sticky="ew", pady=(12, 0))
        ttk.Button(numbers_actions, text="Importar CSV", command=self.import_blast_csv).pack(side=LEFT, padx=(0, 8))
        ttk.Button(numbers_actions, text="Preparar cola", style="Accent.TButton", command=self.prepare_blast_campaign).pack(side=LEFT, padx=(0, 8))
        ttk.Button(numbers_actions, text="Simular ronda", style="Gold.TButton", command=self.simulate_blast_round).pack(side=LEFT, padx=(0, 8))
        ttk.Button(numbers_actions, text="Guardar todo", style="Gold.TButton", command=self.save_blaster_state).pack(side=LEFT)

        tabs.add(dashboard, text="Dashboard")
        tabs.add(templates, text="Plantillas")
        tabs.add(numbers, text="Preparar numeros")
        self.update_blast_metrics()
        return view

    def _build_extractor(self, parent: ttk.Frame) -> ttk.Frame:
        view = ttk.Frame(parent)
        view.columnconfigure(0, weight=1)
        view.columnconfigure(1, weight=1)
        view.rowconfigure(0, weight=1)
        left = self._panel(view)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        left.rowconfigure(4, weight=1)
        left.columnconfigure(0, weight=1)
        ttk.Label(left, text="Extractor de numeros desde TXT -> Tabla + CSV", style="PanelTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(left, text="Sube tu archivo .txt", style="PanelMuted.TLabel").grid(row=1, column=0, sticky="w", pady=(2, 10))

        controls = ttk.Frame(left, style="Panel.TFrame")
        controls.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        ttk.Button(controls, text="Seleccionar archivo", style="Accent.TButton", command=self.import_whatsapp_txt).pack(side=LEFT, padx=(0, 18))
        ttk.Label(controls, text="Formato de salida", style="PanelMuted.TLabel").pack(side=LEFT, padx=(0, 6))
        self.extract_format_var = tk.StringVar(value="E164")
        format_box = ttk.Combobox(
            controls,
            textvariable=self.extract_format_var,
            values=["E164", "MX10"],
            width=8,
            state="readonly",
        )
        format_box.pack(side=LEFT, padx=(0, 8))
        format_box.bind("<<ComboboxSelected>>", lambda _event: self.rebuild_extractor_numbers())
        ttk.Button(controls, text="Descargar CSV", command=self.export_extractor_csv).pack(side=LEFT, padx=(0, 8))
        ttk.Button(controls, text="Copiar columna", command=self.copy_extractor_column).pack(side=LEFT, padx=(0, 8))
        ttk.Button(controls, text="Limpiar", style="Danger.TButton", command=self.clear_extractor).pack(side=LEFT)

        metrics = ttk.Frame(left, style="Panel.TFrame")
        metrics.grid(row=3, column=0, sticky="ew", pady=(0, 10))
        self.extract_file_var = tk.StringVar(value="-")
        self.extract_candidates_var = tk.StringVar(value="0")
        self.extract_unique_var = tk.StringVar(value="0")
        self.extract_phones_var = tk.StringVar(value="0")
        for label, var in [
            ("Archivo", self.extract_file_var),
            ("Candidatos detectados", self.extract_candidates_var),
            ("Numeros validos", self.extract_unique_var),
            ("Remitentes", self.extract_phones_var),
        ]:
            box = ttk.Frame(metrics, style="Band.TFrame", padding=10)
            box.pack(side=LEFT, fill=X, expand=True, padx=(0, 8))
            ttk.Label(box, textvariable=var, style="Metric.TLabel").pack(anchor=W)
            ttk.Label(box, text=label, style="MetricSmall.TLabel").pack(anchor=W)

        columns = ("idx", "phone", "sender", "raw", "reason")
        self.visible_chat_list = ttk.Treeview(left, columns=columns, show="headings", selectmode="browse")
        for col, label, width in [
            ("idx", "#", 70),
            ("phone", "Numero final", 220),
            ("sender", "Remitente", 220),
            ("raw", "Detectado raw", 360),
            ("reason", "Filtro", 170),
        ]:
            self.visible_chat_list.heading(col, text=label)
            self.visible_chat_list.column(col, width=width, anchor=W)
        self.visible_chat_list.grid(row=4, column=0, sticky="nsew")
        right = self._panel(view)
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)
        ttk.Label(right, text="Debug", style="PanelTitle.TLabel").grid(row=0, column=0, sticky="w")
        self.extract_detail = tk.Text(right, wrap="word", bd=0, bg=PANEL, fg=INK, padx=12, pady=12)
        self.extract_detail.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
        return view

    def _build_config(self, parent: ttk.Frame) -> ttk.Frame:
        view = ttk.Frame(parent)
        view.columnconfigure(0, weight=1)
        card = self._panel(view)
        card.grid(row=0, column=0, sticky="nsew")
        ttk.Label(card, text="Config", style="PanelTitle.TLabel").pack(anchor=W)
        ttk.Label(card, text="Parametros locales para ventas, blaster, opt-out y LLM local.", style="PanelMuted.TLabel").pack(anchor=W, pady=(2, 16))
        self.require_review_var = tk.BooleanVar(value=True)
        self.daily_limit_var = tk.StringVar(value="40")
        self.delay_min_var = tk.StringVar(value="35")
        self.delay_max_var = tk.StringVar(value="120")
        self.opt_out_var = tk.StringVar(value="BAJA, STOP, no me escribas")
        self.local_llm_var = tk.StringVar(value="http://127.0.0.1:11434")
        for label, var in [("Limite diario", self.daily_limit_var), ("Pausa minima", self.delay_min_var), ("Pausa maxima", self.delay_max_var), ("Palabras opt-out", self.opt_out_var), ("LLM local", self.local_llm_var)]:
            self._config_row(card, label, var)
        ttk.Checkbutton(card, text="Requerir aprobacion antes de enviar", variable=self.require_review_var).pack(anchor=W, pady=(8, 12))
        ttk.Button(card, text="Guardar config", style="Accent.TButton", command=self.save_config).pack(anchor=W)
        return view

    def _config_row(self, parent: ttk.Frame, label: str, var: tk.StringVar) -> None:
        row = ttk.Frame(parent, style="Panel.TFrame")
        row.pack(fill=X, pady=(0, 10))
        ttk.Label(row, text=label, style="PanelMuted.TLabel", width=18).pack(side=LEFT)
        ttk.Entry(row, textvariable=var).pack(side=LEFT, fill=X, expand=True)

    def show_view(self, name: str) -> None:
        for key, frame in self.views.items():
            frame.pack_forget()
            self.view_buttons[key].configure(style="NavActive.TButton" if key == name else "Nav.TButton")
        self.views[name].pack(fill=BOTH, expand=True)

    def _load_leads(self) -> None:
        LOCAL_DIR.mkdir(parents=True, exist_ok=True)
        self.status_var.set("Edge: perfil existe" if EDGE_PROFILE.exists() else "Edge: abre WhatsApp Web")
        if LEADS_FILE.exists():
            try:
                self.leads = [Lead(**item) for item in json.loads(LEADS_FILE.read_text(encoding="utf-8"))]
            except (json.JSONDecodeError, TypeError):
                self.leads = []
        self.refresh_tree()
        self.load_config()
        self.load_blaster_state()

    def refresh_tree(self) -> None:
        self.tree.delete(*self.tree.get_children())
        for idx, lead in enumerate(self.leads):
            self.tree.insert("", END, iid=str(idx), values=(lead.nombre, lead.telefono, lead.etapa, lead.pendiente, lead.score))
        self.lead_count_var.set(str(len(self.leads)))
        self.pending_count_var.set(str(sum(1 for lead in self.leads if lead.pendiente and lead.pendiente.lower() != "revisado")))
        self.update_blast_metrics()
        if self.leads:
            current = "0" if self.selected_index is None else str(min(self.selected_index, len(self.leads) - 1))
            self.tree.selection_set(current)
            self.tree.focus(current)
            self.selected_index = int(current)
            self.show_lead(self.leads[self.selected_index])
        else:
            self.selected_index = None
            self.detail.delete("1.0", END)
            self.detail.insert(
                END,
                "No hay leads cargados.\n\nUsa `Leer WhatsApp` para traer chats visibles reales, "
                "o `Extractor afiliados` para seleccionar un grupo/chat autorizado y pasarlo al CRM.",
            )
            self.draft.delete("1.0", END)

    def on_select(self, _event: tk.Event) -> None:
        selected = self.tree.selection()
        if selected:
            self.selected_index = int(selected[0])
            self.show_lead(self.leads[self.selected_index])

    def show_lead(self, lead: Lead) -> None:
        self.detail.delete("1.0", END)
        self.detail.insert(END, f"Lead: {lead.nombre}\nContacto/chat: {lead.telefono}\nEtapa: {lead.etapa}\nScore: {lead.score}\n\nUltimo mensaje:\n{lead.ultimo_mensaje}\n\nPendiente:\n{lead.pendiente}")
        self.draft.delete("1.0", END)

    def refresh_from_whatsapp(self) -> None:
        try:
            result = self._run_bridge("list")
        except RuntimeError as exc:
            messagebox.showerror("No pude leer WhatsApp", str(exc))
            return
        chats = result.get("data", {}).get("chats", [])
        real_leads: list[Lead] = []
        for chat in chats:
            title = chat.get("title") or "Chat visible"
            text = " ".join((chat.get("text") or "").split())
            if not title or title == "sin titulo":
                continue
            real_leads.append(
                Lead(
                    nombre=title,
                    telefono=title,
                    etapa="whatsapp",
                    ultimo_mensaje=text[:240],
                    pendiente="Revisar conversacion real",
                    score=0,
                )
            )
        self.leads = real_leads
        self.selected_index = 0 if self.leads else None
        self.refresh_tree()
        messagebox.showinfo("WhatsApp leido", f"Se cargaron {len(self.leads)} chat(s) visibles reales.")

    def import_csv(self) -> None:
        path = filedialog.askopenfilename(title="Importar contactos CSV", filetypes=[("CSV", "*.csv"), ("Todos", "*.*")])
        if not path:
            return
        imported = self._read_leads_csv(path)
        if imported:
            self.leads = imported
            self.selected_index = 0
            self.refresh_tree()
            messagebox.showinfo("CSV importado", f"Se cargaron {len(imported)} contacto(s).")

    def import_blast_csv(self) -> None:
        path = filedialog.askopenfilename(title="Importar CSV para blaster", filetypes=[("CSV", "*.csv"), ("Todos", "*.*")])
        if not path:
            return
        imported = self._read_leads_csv(path)
        if not imported:
            messagebox.showwarning("CSV vacio", "No pude cargar contactos desde ese CSV.")
            return
        self.leads = imported
        self.selected_index = 0
        self.refresh_tree()
        self._write_leads_file()
        valid = sum(1 for lead in imported if self._has_blast_phone(lead))
        self.update_blast_metrics()
        messagebox.showinfo("CSV blaster", f"Se cargaron {len(imported)} contacto(s). Con telefono para blaster: {valid}.")

    def _read_leads_csv(self, path: str) -> list[Lead]:
        imported: list[Lead] = []
        with open(path, newline="", encoding="utf-8-sig") as handle:
            for row in csv.DictReader(handle):
                nombre = row.get("nombre") or row.get("name") or row.get("Nombre") or row.get("sender") or "Contacto CSV"
                telefono = row.get("telefono") or row.get("phone") or row.get("Telefono") or ""
                producto = row.get("producto") or row.get("product") or "producto"
                telefono = telefono.strip()
                pendiente = "Preparar mensaje" if telefono else "Falta telefono para blaster"
                imported.append(Lead(nombre.strip(), telefono or nombre.strip(), "importado", f"Contacto importado para {producto}.", pendiente, 0))
        return imported

    def generate_draft(self) -> None:
        lead = self.current_lead()
        if not lead:
            return
        if lead.etapa == "escalado":
            text = "Te paso con una persona del equipo para revisar esto bien. Gracias por avisarnos."
        elif lead.etapa in {"pendiente", "por-confirmar"}:
            text = "Lo reviso y te respondo con datos correctos. No quiero inventarte una respuesta."
        else:
            text = "Hola, gracias por escribir. Te puedo compartir opciones y revisar si esto encaja contigo. ¿Que objetivo quieres lograr?"
        self.draft.delete("1.0", END)
        self.draft.insert(END, text)

    def mark_reviewed(self) -> None:
        lead = self.current_lead()
        if lead is None or self.selected_index is None:
            return
        lead.pendiente = "Revisado"
        self.leads[self.selected_index] = lead
        self.refresh_tree()

    def prepare_blast_campaign(self) -> None:
        if self._active_blast_message_type() != "campaign":
            messagebox.showwarning("No es campana", "Selecciona o guarda este mensaje como tipo Campana para preparar cola.")
            return
        template = self.blast_template.get("1.0", END).strip()
        if not template:
            messagebox.showwarning("Sin plantilla", "Escribe una plantilla primero.")
            return
        self.queue.delete(0, END)
        product = self.blast_product_var.get().strip() or "tu servicio"
        added = 0
        skipped = 0
        for lead in self.leads:
            if not self._has_blast_phone(lead):
                skipped += 1
                continue
            msg = template.format(nombre=lead.nombre, telefono=lead.telefono, producto=product, etapa=lead.etapa)
            self.queue.insert(END, f"REVISION: {lead.telefono} -> {msg[:130]}")
            added += 1
        self.save_blaster_state(show_message=False)
        self.update_blast_metrics()
        messagebox.showinfo("Cola preparada", f"Listos para revision: {added}. Sin telefono: {skipped}.")

    def _has_blast_phone(self, lead: Lead) -> bool:
        digits = re.sub(r"\D", "", lead.telefono or "")
        return len(digits) >= 10

    def simulate_blast_round(self) -> None:
        if self.queue.size() == 0:
            messagebox.showwarning("Cola vacia", "Prepara una cola primero.")
            return
        for idx in range(min(3, self.queue.size())):
            value = self.queue.get(idx)
            self.queue.delete(idx)
            self.queue.insert(idx, value.replace("REVISION", "SIMULADO", 1))
        self.save_blaster_state(show_message=False)
        self.update_blast_metrics()

    def refresh_blast_message_list(self) -> None:
        self.blast_message_list.delete(0, END)
        self.blast_message_source_indices = []
        selected_filter = self.blast_message_filter_var.get() if hasattr(self, "blast_message_filter_var") else "Todos"
        for idx, message in enumerate(self.blast_messages):
            message_type = str(message.get("type") or "campaign")
            if selected_filter == "Campanas" and message_type != "campaign":
                continue
            if selected_filter == "Rapidos" and message_type != "quick":
                continue
            self.blast_message_source_indices.append(idx)
            self.blast_message_list.insert(END, f"{self._blast_type_label(message_type)}: {message.get('name', 'Mensaje sin nombre')}")
        self.update_blast_metrics()

    def current_blast_message_index(self) -> int | None:
        selected = self.blast_message_list.curselection()
        if not selected:
            return None
        visible_index = int(selected[0])
        if visible_index >= len(self.blast_message_source_indices):
            return None
        return self.blast_message_source_indices[visible_index]

    def on_blast_message_select(self, _event: tk.Event) -> None:
        index = self.current_blast_message_index()
        if index is None or index >= len(self.blast_messages):
            return
        message = self.blast_messages[index]
        self.blast_message_name_var.set(str(message.get("name", "Mensaje sin nombre")))
        self.blast_message_type_var.set(self._blast_type_label(str(message.get("type") or "campaign")))
        self.blast_template.delete("1.0", END)
        self.blast_template.insert(END, str(message.get("template", "")))

    def add_blast_message(self) -> None:
        name = self.blast_message_name_var.get().strip() or f"Mensaje {len(self.blast_messages) + 1}"
        template = self.blast_template.get("1.0", END).strip()
        if not template:
            messagebox.showwarning("Sin mensaje", "Escribe el mensaje antes de guardarlo.")
            return
        self.blast_messages.append({"name": name, "type": self._blast_type_key(), "template": template})
        self.blast_message_filter_var.set("Todos")
        self.refresh_blast_message_list()
        self.select_blast_message_by_source(len(self.blast_messages) - 1)
        self.save_blaster_state(show_message=False)

    def update_blast_message(self) -> None:
        index = self.current_blast_message_index()
        if index is None:
            self.add_blast_message()
            return
        name = self.blast_message_name_var.get().strip() or "Mensaje sin nombre"
        template = self.blast_template.get("1.0", END).strip()
        if not template:
            messagebox.showwarning("Sin mensaje", "Escribe el mensaje antes de actualizarlo.")
            return
        self.blast_messages[index] = {"name": name, "type": self._blast_type_key(), "template": template}
        self.blast_message_filter_var.set("Todos")
        self.refresh_blast_message_list()
        self.select_blast_message_by_source(index)
        self.save_blaster_state(show_message=False)

    def sync_active_blast_message(self) -> None:
        template = self.blast_template.get("1.0", END).strip()
        if not template:
            return
        name = self.blast_message_name_var.get().strip() or "Mensaje sin nombre"
        index = self.current_blast_message_index()
        if index is None or index >= len(self.blast_messages):
            self.blast_messages.append({"name": name, "type": self._blast_type_key(), "template": template})
            self.refresh_blast_message_list()
            self.select_blast_message_by_source(len(self.blast_messages) - 1)
            return
        self.blast_messages[index] = {"name": name, "type": self._blast_type_key(), "template": template}
        self.refresh_blast_message_list()
        self.select_blast_message_by_source(index)

    def _blast_type_key(self) -> str:
        return "quick" if self.blast_message_type_var.get() == "Rapido" else "campaign"

    def _blast_type_label(self, message_type: str) -> str:
        return "Rapido" if message_type == "quick" else "Campana"

    def _active_blast_message_type(self) -> str:
        index = self.current_blast_message_index()
        if index is not None and index < len(self.blast_messages):
            return str(self.blast_messages[index].get("type") or self._blast_type_key())
        return self._blast_type_key()

    def select_blast_message_by_source(self, source_index: int) -> None:
        self.blast_message_list.selection_clear(0, END)
        if source_index in self.blast_message_source_indices:
            visible_index = self.blast_message_source_indices.index(source_index)
            self.blast_message_list.selection_set(visible_index)

    def update_blast_metrics(self) -> None:
        if not hasattr(self, "blast_contacts_var"):
            return
        self.blast_contacts_var.set(str(len(self.leads)))
        self.blast_ready_var.set(str(sum(1 for lead in self.leads if self._has_blast_phone(lead))))
        self.blast_messages_var.set(str(sum(1 for item in self.blast_messages if item.get("type", "campaign") == "campaign")))
        self.blast_queue_var.set(str(self.queue.size() if hasattr(self, "queue") else 0))

    def delete_blast_message(self) -> None:
        index = self.current_blast_message_index()
        if index is None or index >= len(self.blast_messages):
            messagebox.showwarning("Sin seleccion", "Selecciona un mensaje para borrarlo.")
            return
        if not messagebox.askyesno("Borrar mensaje", f"Borrar `{self.blast_messages[index].get('name', 'Mensaje')}`?"):
            return
        del self.blast_messages[index]
        self.refresh_blast_message_list()
        if self.blast_messages:
            next_index = min(index, len(self.blast_messages) - 1)
            self.select_blast_message_by_source(next_index)
            self.on_blast_message_select(tk.Event())
        else:
            self.blast_message_name_var.set("Mensaje nuevo")
            self.blast_template.delete("1.0", END)
        self.save_blaster_state(show_message=False)

    def import_whatsapp_txt(self) -> None:
        path = filedialog.askopenfilename(
            title="Importar chat exportado de WhatsApp",
            initialdir=str(Path.home() / "Downloads"),
            filetypes=[("WhatsApp TXT", "*.txt"), ("Todos", "*.*")],
        )
        if not path:
            return
        text = Path(path).read_text(encoding="utf-8-sig", errors="replace")
        candidates = self._extract_candidates(text)
        participants = self._participants_from_export(text)
        self.extract_candidates_cache = candidates
        self.extract_participants_cache = participants
        numbers = self._numbers_from_candidates(candidates)
        review_rows = numbers or participants or candidates
        review_source = "txt" if numbers else "participants" if participants else "candidates"
        self.visible_chats = numbers or participants
        self._render_extractor_rows(review_rows, source=review_source)
        self.extract_file_var.set(Path(path).name[:18])
        self.extract_candidates_var.set(str(len(candidates)))
        self.extract_unique_var.set(str(len(numbers)))
        self.extract_phones_var.set(str(len(participants)))
        self.extract_detail.delete("1.0", END)
        self.extract_detail.insert(
            END,
            "Debug (primeros 20 candidatos detectados):\n"
            + ("\n".join(f"{c['raw']} | {c['sender'] or 'sin remitente'} | {c['field']} | {c['reason']}" for c in candidates[:20]) or "-"),
        )

    def rebuild_extractor_numbers(self) -> None:
        if not self.extract_candidates_cache:
            return
        numbers = self._numbers_from_candidates(self.extract_candidates_cache)
        review_rows = numbers or self.extract_participants_cache or self.extract_candidates_cache
        review_source = "txt" if numbers else "participants" if self.extract_participants_cache else "candidates"
        self.visible_chats = numbers or self.extract_participants_cache
        self._render_extractor_rows(review_rows, source=review_source)
        self.extract_unique_var.set(str(len(numbers)))
        self.extract_phones_var.set(str(len(self.extract_participants_cache)))

    def _render_extractor_rows(self, rows: list[dict], *, source: str) -> None:
        self.visible_chat_list.delete(*self.visible_chat_list.get_children())
        if source == "web":
            self.extract_file_var.set("WhatsApp Web")
            self.extract_candidates_var.set(str(len(rows)))
            self.extract_unique_var.set(str(len(rows)))
            self.extract_phones_var.set(str(sum(1 for item in rows if item.get("phone"))))
        for idx, item in enumerate(rows):
            if source == "txt":
                title = str(idx + 1)
                phone = item.get("final", "")
                sender = item.get("sender", "")
                context = item.get("raw", "")
                reason = item.get("reason", "")
            elif source == "candidates":
                title = str(idx + 1)
                phone = ""
                sender = item.get("sender", "")
                context = item.get("raw", "")
                reason = item.get("reason", "")
            elif source == "participants":
                title = str(idx + 1)
                phone = item.get("phone") or "sin numero en TXT"
                sender = item.get("sender", "")
                context = item.get("phone_raw") or "remitente exportado como nombre"
                reason = f"{item.get('messages', 0)} mensaje(s)"
            else:
                title = item.get("title") or "sin titulo"
                phone = item.get("phone") or ""
                sender = item.get("sender", "")
                context = " ".join((item.get("last_text") or item.get("text") or "").split())
                reason = ""
            self.visible_chat_list.insert(
                "",
                END,
                iid=str(idx),
                values=(title, phone, sender[:80], context[:220], reason[:80]),
            )

    def _extract_candidates(self, text: str) -> list[dict]:
        candidates: list[dict] = []
        line_pattern = re.compile(
            r"^(\d{1,2}/\d{1,2}/\d{2,4}),\s+(.+?)\s+-\s+([^:\n]+):\s*(.*)$"
        )
        for line_no, line in enumerate((text or "").splitlines(), start=1):
            clean_line = line.lstrip("\ufeff\u200e").strip()
            match = line_pattern.match(clean_line)
            if match:
                date, time_text, sender, body = match.groups()
                sender = sender.strip().lstrip("\u200e").strip()
                at = f"{date} {time_text}"
                fields = [("mensaje", body), ("remitente", sender)]
            else:
                sender = ""
                at = ""
                fields = [("linea", clean_line)]
            for field, source in fields:
                for raw in re.findall(r"\+?\d[\d\s().-]{6,}\d", source):
                    reason = self._candidate_reason(raw, source, sender, field)
                    candidates.append(
                        {
                            "raw": raw,
                            "sender": sender,
                            "line": line_no,
                            "at": at,
                            "field": field,
                            "context": source[:240],
                            "valid": reason == "valido",
                            "reason": reason,
                        }
                    )
        return candidates

    def _participants_from_export(self, text: str) -> list[dict]:
        participants: dict[str, dict] = {}
        line_pattern = re.compile(
            r"^(\d{1,2}/\d{1,2}/\d{2,4}),\s+(.+?)\s+-\s+([^:\n]+):\s*(.*)$"
        )
        for line_no, line in enumerate((text or "").splitlines(), start=1):
            match = line_pattern.match(line.lstrip("\ufeff\u200e").strip())
            if not match:
                continue
            date, time_text, sender, body = match.groups()
            sender = sender.strip().lstrip("\u200e").strip()
            if not sender:
                continue
            phone = ""
            phone_raw = ""
            for raw in re.findall(r"\+?\d[\d\s().-]{6,}\d", sender):
                phone = self._normalize_phone(raw) or ""
                if phone:
                    phone_raw = raw
                    break
            item = participants.setdefault(
                sender,
                {
                    "sender": sender,
                    "phone": phone,
                    "phone_raw": phone_raw,
                    "line": line_no,
                    "at": f"{date} {time_text}",
                    "messages": 0,
                    "last_text": "",
                    "source": "participant",
                },
            )
            item["messages"] += 1
            item["last_text"] = " ".join(body.split())[:220]
            item["at"] = f"{date} {time_text}"
            if phone and not item.get("phone"):
                item["phone"] = phone
                item["phone_raw"] = phone_raw
        return list(participants.values())

    def _candidate_reason(self, raw: str, context: str, sender: str, field: str) -> str:
        digits = re.sub(r"\D", "", raw)
        lowered = context.lower()
        if any(token in lowered for token in ["http://", "https://", "docs.google", "facebook.com", "youtube", "youtu.be", "spotify"]):
            return "descartado: link/id"
        if re.search(r"\d+\.\d+", raw):
            return "descartado: decimal/coordenada"
        if len(digits) not in {10, 12, 13}:
            return "descartado: longitud"
        if len(digits) == 12 and not digits.startswith("52"):
            return "descartado: pais no MX"
        if len(digits) == 13 and not digits.startswith("521"):
            return "descartado: pais no MX"
        if field != "remitente" and not sender and not raw.strip().startswith("+"):
            return "descartado: sin remitente"
        return "valido"

    def _numbers_from_candidates(self, candidates: list[dict]) -> list[dict]:
        seen: dict[str, dict] = {}
        for candidate in candidates:
            if not candidate.get("valid"):
                continue
            raw = candidate["raw"]
            final = self._normalize_phone(raw)
            if not final:
                continue
            seen.setdefault(
                final,
                {
                    "final": final,
                    "phone": final,
                    "raw": raw,
                    "sender": candidate.get("sender", ""),
                    "line": candidate.get("line", ""),
                    "at": candidate.get("at", ""),
                    "field": candidate.get("field", ""),
                    "reason": candidate.get("reason", ""),
                    "source": "txt",
                },
            )
        return list(seen.values())

    def _normalize_phone(self, raw: str) -> str:
        digits = re.sub(r"\D", "", raw)
        mx10 = ""
        if len(digits) == 13 and digits.startswith("521"):
            mx10 = digits[3:]
        elif len(digits) == 12 and digits.startswith("52"):
            mx10 = digits[2:]
        elif len(digits) == 10:
            mx10 = digits
        elif len(digits) > 10:
            mx10 = digits[-10:]
        if not mx10:
            return ""
        if self.extract_format_var.get() == "MX10":
            return mx10
        return "+52" + mx10

    def export_extractor_csv(self) -> None:
        if not self.visible_chats:
            messagebox.showwarning("Sin datos", "Primero importa un TXT.")
            return
        path = filedialog.asksaveasfilename(
            title="Guardar afiliados CSV",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            initialfile="afiliados_extraidos.csv",
        )
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=["nombre", "telefono", "phone", "raw", "sender", "line", "at", "field", "reason", "source"])
            writer.writeheader()
            for item in self.visible_chats:
                phone = item.get("final") or item.get("phone", "")
                sender = item.get("sender", "")
                writer.writerow({
                    "nombre": sender or item.get("title", ""),
                    "telefono": phone,
                    "phone": phone,
                    "raw": item.get("raw", ""),
                    "sender": sender,
                    "line": item.get("line", ""),
                    "at": item.get("at", ""),
                    "field": item.get("field", ""),
                    "reason": item.get("reason", ""),
                    "source": item.get("source", "txt"),
                })
        messagebox.showinfo("CSV exportado", f"Archivo guardado en {path}")

    def copy_extractor_column(self) -> None:
        phones = [item.get("final") or item.get("phone") for item in self.visible_chats]
        phones = [phone for phone in phones if phone]
        if not phones:
            messagebox.showwarning("Sin numeros", "No hay numeros para copiar.")
            return
        self.clipboard_clear()
        self.clipboard_append("\n".join(phones))
        messagebox.showinfo("Copiado", f"Se copiaron {len(phones)} numero(s).")

    def clear_extractor(self) -> None:
        self.visible_chats = []
        self.extract_candidates_cache = []
        self.extract_participants_cache = []
        self.visible_chat_list.delete(*self.visible_chat_list.get_children())
        self.extract_file_var.set("-")
        self.extract_candidates_var.set("0")
        self.extract_unique_var.set("0")
        self.extract_phones_var.set("0")
        self.extract_detail.delete("1.0", END)
        self.extract_detail.insert(END, "-")

    def read_selected_chat(self) -> None:
        lead = self.current_lead()
        if not lead:
            return
        try:
            result = self._run_bridge("read", "--chat", lead.telefono or lead.nombre)
        except RuntimeError as exc:
            messagebox.showerror("No pude leer el chat", str(exc))
            return
        self._show_chat_result(result.get("data", {}), update_lead=True)

    def read_active_chat(self) -> None:
        try:
            result = self._run_bridge("read")
        except RuntimeError as exc:
            messagebox.showerror("No pude leer WhatsApp Web", str(exc))
            return
        self._show_chat_result(result.get("data", {}), update_lead=False)

    def _show_chat_result(self, data: dict, *, update_lead: bool) -> None:
        messages = data.get("messages") or []
        last = data.get("last") or {}
        summary = [f"Chat: {data.get('title') or 'activo'}", f"Mensajes leidos: {len(messages)}", f"Ultimo remitente: {last.get('sender') or 'sin detectar'}", "", "Ultimos mensajes:"]
        for msg in messages[-8:]:
            sender = msg.get("sender") or msg.get("direction") or "?"
            text = " ".join((msg.get("text") or "").split())
            summary.append(f"- {sender}: {text[:180]}")
        self.detail.delete("1.0", END)
        self.detail.insert(END, "\n".join(summary))
        if update_lead and self.selected_index is not None and last:
            lead = self.leads[self.selected_index]
            lead.ultimo_mensaje = " ".join((last.get("text") or "").split())[:240]
            lead.pendiente = "Responder desde ventas"
            lead.etapa = "activo"
            self.leads[self.selected_index] = lead
            self.tree.item(
                str(self.selected_index),
                values=(lead.nombre, lead.telefono, lead.etapa, lead.pendiente, lead.score),
            )
            self.pending_count_var.set(str(sum(1 for item in self.leads if item.pendiente and item.pendiente.lower() != "revisado")))

    def send_draft_real(self) -> None:
        lead = self.current_lead()
        draft = self.draft.get("1.0", END).strip()
        if not lead or not draft:
            messagebox.showwarning("Falta borrador", "Selecciona un lead y escribe/genera un borrador.")
            return
        if not messagebox.askyesno("Confirmar envio real", f"Enviar al chat `{lead.telefono}`?\n\n{draft}"):
            return
        try:
            self._run_bridge("send", "--chat", lead.telefono or lead.nombre, "--text", draft)
        except RuntimeError as exc:
            messagebox.showerror("No pude enviar", str(exc))
            return
        lead.pendiente = "Mensaje enviado"
        if self.selected_index is not None:
            self.leads[self.selected_index] = lead
        self.refresh_tree()

    def load_config(self) -> None:
        if not CONFIG_FILE.exists():
            return
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return
        self.daily_limit_var.set(str(data.get("daily_limit", self.daily_limit_var.get())))
        self.delay_min_var.set(str(data.get("delay_min_seconds", self.delay_min_var.get())))
        self.delay_max_var.set(str(data.get("delay_max_seconds", self.delay_max_var.get())))
        self.opt_out_var.set(str(data.get("opt_out_words", self.opt_out_var.get())))
        self.local_llm_var.set(str(data.get("local_llm_url", self.local_llm_var.get())))
        self.require_review_var.set(bool(data.get("require_review", True)))

    def save_config(self) -> None:
        LOCAL_DIR.mkdir(parents=True, exist_ok=True)
        config = {
            "daily_limit": self.daily_limit_var.get(),
            "delay_min_seconds": self.delay_min_var.get(),
            "delay_max_seconds": self.delay_max_var.get(),
            "opt_out_words": self.opt_out_var.get(),
            "local_llm_url": self.local_llm_var.get(),
            "require_review": self.require_review_var.get(),
        }
        CONFIG_FILE.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
        messagebox.showinfo("Config guardada", f"Config guardada en {CONFIG_FILE}")

    def load_blaster_state(self) -> None:
        if not BLASTER_FILE.exists():
            return
        try:
            data = json.loads(BLASTER_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return
        self.blast_product_var.set(str(data.get("product", self.blast_product_var.get())))
        messages = data.get("messages", [])
        if isinstance(messages, list) and messages:
            self.blast_messages = [
                {
                    "name": str(item.get("name") or f"Mensaje {idx + 1}"),
                    "type": str(item.get("type") or "campaign"),
                    "template": str(item.get("template") or ""),
                }
                for idx, item in enumerate(messages)
                if isinstance(item, dict) and str(item.get("template") or "").strip()
            ]
        else:
            template = str(data.get("template", "")).strip()
            if template:
                self.blast_messages = [{"name": "Promo principal", "type": "campaign", "template": template}]
        self.refresh_blast_message_list()
        if self.blast_messages:
            self.blast_message_list.selection_set(0)
            self.on_blast_message_select(tk.Event())
        items = data.get("queue", [])
        if isinstance(items, list):
            self.queue.delete(0, END)
            for item in items:
                self.queue.insert(END, str(item))
        self.update_blast_metrics()

    def save_blaster_state(self, *, show_message: bool = True) -> None:
        LOCAL_DIR.mkdir(parents=True, exist_ok=True)
        self.sync_active_blast_message()
        data = {
            "product": self.blast_product_var.get(),
            "messages": self.blast_messages,
            "active_message": self.blast_message_name_var.get(),
            "template": self.blast_template.get("1.0", END).strip(),
            "queue": list(self.queue.get(0, END)),
        }
        BLASTER_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        self.update_blast_metrics()
        if show_message:
            messagebox.showinfo("Blaster guardado", f"Plantilla y cola guardadas en {BLASTER_FILE}")

    def _run_bridge(self, *args: str) -> dict:
        completed = subprocess.run([sys.executable, str(BRIDGE_SCRIPT), *args], cwd=str(ROOT), text=True, capture_output=True, check=False)
        payload = completed.stdout.strip().splitlines()[-1] if completed.stdout.strip() else ""
        try:
            result = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise RuntimeError(completed.stderr.strip() or completed.stdout.strip() or "El bridge no devolvio JSON.") from exc
        if not result.get("ok"):
            raise RuntimeError(result.get("message") or "El bridge fallo.")
        return result

    def save_leads(self) -> None:
        self._write_leads_file()
        messagebox.showinfo("Guardado", f"Datos guardados en {LEADS_FILE}")

    def _write_leads_file(self) -> None:
        LOCAL_DIR.mkdir(parents=True, exist_ok=True)
        LEADS_FILE.write_text(json.dumps([asdict(lead) for lead in self.leads], ensure_ascii=False, indent=2), encoding="utf-8")

    def open_edge(self) -> None:
        subprocess.Popen(["powershell", "-ExecutionPolicy", "Bypass", "-File", str(EDGE_SCRIPT)], cwd=str(ROOT))
        self.status_var.set("Edge: WhatsApp Web abierto")

    def current_lead(self) -> Lead | None:
        if self.selected_index is None or self.selected_index >= len(self.leads):
            messagebox.showwarning("Sin lead", "Selecciona un lead primero.")
            return None
        return self.leads[self.selected_index]


def main() -> int:
    app = ExplorerApp()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
