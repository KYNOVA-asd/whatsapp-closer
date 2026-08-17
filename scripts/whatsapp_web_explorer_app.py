"""Desktop sales panel demo for the whatsapp-web-explorer branch."""

from __future__ import annotations

import csv
import json
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


DEMO_LEADS = [
    Lead("Yo Mero", "Yo Mero", "nuevo", "Hola", "Leer conversacion real y responder", 50),
    Lead("Lead curso bienes raices", "5215500000000", "calificado", "Cuanto sale? Se me hace caro.", "Responder objecion", 62),
    Lead("Lead molesto", "5215500000001", "escalado", "Ya van tres veces que pregunto lo mismo.", "Pasar a humano", 28),
]


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
        ttk.Button(actions, text="Refrescar demo", command=self.load_demo).pack(side=LEFT, padx=(0, 8))
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
        ttk.Button(top, text="Demo", command=self.load_demo).pack(side=tk.RIGHT)
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
        view.columnconfigure(0, weight=2)
        view.columnconfigure(1, weight=3)
        view.rowconfigure(0, weight=1)
        left = self._panel(view)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        ttk.Label(left, text="Blaster consentido", style="PanelTitle.TLabel").pack(anchor=W)
        ttk.Label(left, text="Promos a lista propia, afiliados o clientes con relacion previa.", style="PanelMuted.TLabel").pack(anchor=W, pady=(2, 12))
        self.blast_template = tk.Text(left, height=12, wrap="word", bd=0, bg="#f4efe6", fg=INK, padx=12, pady=12)
        self.blast_template.pack(fill=X)
        self.blast_template.insert(END, "Hola {nombre}, tenemos una promo de {producto}. Si quieres mas info responde SI.")
        ttk.Button(left, text="Preparar cola desde CRM", style="Accent.TButton", command=self.prepare_blast_campaign).pack(anchor=W, pady=(12, 0))
        ttk.Button(left, text="Simular ronda", style="Gold.TButton", command=self.simulate_blast_round).pack(anchor=W, pady=(8, 0))
        right = self._panel(view)
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)
        ttk.Label(right, text="Cola y reglas", style="PanelTitle.TLabel").grid(row=0, column=0, sticky="w")
        self.queue = tk.Listbox(right, bd=0, bg=PANEL, fg=INK, highlightthickness=1, highlightcolor=GOLD)
        self.queue.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
        for rule in ["Regla: consentimiento o relacion previa.", "Regla: limite diario y pausas.", "Regla: baja/stop cancela seguimiento."]:
            self.queue.insert(END, rule)
        return view

    def _build_extractor(self, parent: ttk.Frame) -> ttk.Frame:
        view = ttk.Frame(parent)
        view.columnconfigure(0, weight=1)
        view.columnconfigure(1, weight=1)
        view.rowconfigure(0, weight=1)
        left = self._panel(view)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        left.rowconfigure(2, weight=1)
        left.columnconfigure(0, weight=1)
        ttk.Label(left, text="Extractor de afiliados / grupo autorizado", style="PanelTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(left, text="Lista chats visibles, quien mando mensaje y actividad reciente.", style="PanelMuted.TLabel").grid(row=1, column=0, sticky="w", pady=(2, 10))
        self.visible_chat_list = tk.Listbox(left, bd=0, bg="#f4efe6", fg=INK, highlightthickness=1, highlightcolor=GOLD)
        self.visible_chat_list.grid(row=2, column=0, sticky="nsew")
        row = ttk.Frame(left, style="Panel.TFrame")
        row.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        ttk.Button(row, text="Listar chats visibles", style="Accent.TButton", command=self.load_visible_chats).pack(side=LEFT, padx=(0, 8))
        ttk.Button(row, text="Agregar a CRM", style="Gold.TButton", command=self.add_selected_visible_chat).pack(side=LEFT)
        right = self._panel(view)
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)
        ttk.Label(right, text="Detalle extraido", style="PanelTitle.TLabel").grid(row=0, column=0, sticky="w")
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
        if not self.leads:
            self.leads = DEMO_LEADS.copy()
        self.refresh_tree()
        self.load_config()

    def refresh_tree(self) -> None:
        self.tree.delete(*self.tree.get_children())
        for idx, lead in enumerate(self.leads):
            self.tree.insert("", END, iid=str(idx), values=(lead.nombre, lead.telefono, lead.etapa, lead.pendiente, lead.score))
        self.lead_count_var.set(str(len(self.leads)))
        self.pending_count_var.set(str(sum(1 for lead in self.leads if lead.pendiente and lead.pendiente.lower() != "revisado")))
        if self.leads:
            current = "0" if self.selected_index is None else str(min(self.selected_index, len(self.leads) - 1))
            self.tree.selection_set(current)
            self.tree.focus(current)
            self.selected_index = int(current)
            self.show_lead(self.leads[self.selected_index])

    def on_select(self, _event: tk.Event) -> None:
        selected = self.tree.selection()
        if selected:
            self.selected_index = int(selected[0])
            self.show_lead(self.leads[self.selected_index])

    def show_lead(self, lead: Lead) -> None:
        self.detail.delete("1.0", END)
        self.detail.insert(END, f"Lead: {lead.nombre}\nContacto/chat: {lead.telefono}\nEtapa: {lead.etapa}\nScore: {lead.score}\n\nUltimo mensaje:\n{lead.ultimo_mensaje}\n\nPendiente:\n{lead.pendiente}")
        self.draft.delete("1.0", END)

    def load_demo(self) -> None:
        self.leads = DEMO_LEADS.copy()
        self.selected_index = 0
        self.refresh_tree()

    def import_csv(self) -> None:
        path = filedialog.askopenfilename(title="Importar contactos CSV", filetypes=[("CSV", "*.csv"), ("Todos", "*.*")])
        if not path:
            return
        imported: list[Lead] = []
        with open(path, newline="", encoding="utf-8-sig") as handle:
            for row in csv.DictReader(handle):
                nombre = row.get("nombre") or row.get("name") or row.get("Nombre") or "Contacto CSV"
                telefono = row.get("telefono") or row.get("phone") or row.get("Telefono") or nombre
                producto = row.get("producto") or row.get("product") or "producto"
                imported.append(Lead(nombre.strip(), telefono.strip(), "importado", f"Contacto importado para {producto}.", "Preparar mensaje", 0))
        if imported:
            self.leads = imported
            self.selected_index = 0
            self.refresh_tree()
            messagebox.showinfo("CSV importado", f"Se cargaron {len(imported)} contacto(s).")

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
        template = self.blast_template.get("1.0", END).strip()
        if not template:
            messagebox.showwarning("Sin plantilla", "Escribe una plantilla primero.")
            return
        self.queue.delete(0, END)
        for lead in self.leads:
            msg = template.format(nombre=lead.nombre, telefono=lead.telefono, producto="tu servicio", etapa=lead.etapa)
            self.queue.insert(END, f"REVISION: {lead.telefono} -> {msg[:110]}")

    def simulate_blast_round(self) -> None:
        if self.queue.size() == 0:
            messagebox.showwarning("Cola vacia", "Prepara una cola primero.")
            return
        for idx in range(min(3, self.queue.size())):
            value = self.queue.get(idx)
            self.queue.delete(idx)
            self.queue.insert(idx, value.replace("REVISION", "SIMULADO", 1))

    def load_visible_chats(self) -> None:
        try:
            result = self._run_bridge("list")
        except RuntimeError as exc:
            messagebox.showerror("No pude listar chats", str(exc))
            return
        self.visible_chats = result.get("data", {}).get("chats", [])
        self.visible_chat_list.delete(0, END)
        for chat in self.visible_chats:
            title = chat.get("title") or "sin titulo"
            text = " ".join((chat.get("text") or "").split())
            unread = " · no leido" if chat.get("unread") else ""
            self.visible_chat_list.insert(END, f"{title}{unread} | {text[:130]}")
        self.extract_detail.delete("1.0", END)
        self.extract_detail.insert(END, json.dumps(self.visible_chats[:12], ensure_ascii=False, indent=2))

    def add_selected_visible_chat(self) -> None:
        selection = self.visible_chat_list.curselection()
        if not selection:
            messagebox.showwarning("Sin chat", "Selecciona un chat visible primero.")
            return
        chat = self.visible_chats[selection[0]]
        title = chat.get("title") or "Chat visible"
        text = " ".join((chat.get("text") or "").split())
        self.leads.append(Lead(title, title, "afiliado", text[:240], "Seguimiento de grupo autorizado", 0))
        self.selected_index = len(self.leads) - 1
        self.refresh_tree()

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
        LOCAL_DIR.mkdir(parents=True, exist_ok=True)
        LEADS_FILE.write_text(json.dumps([asdict(lead) for lead in self.leads], ensure_ascii=False, indent=2), encoding="utf-8")
        messagebox.showinfo("Guardado", f"Datos guardados en {LEADS_FILE}")

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
