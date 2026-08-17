"""Demo desktop UI for the whatsapp-web-explorer branch.

This is intentionally a local prototype. It opens the persistent Edge profile used for
WhatsApp Web, stores demo CRM data under .local/, and lets the user explore the workflow before
any scraper or sender automation is added.
"""

from __future__ import annotations

import csv
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from tkinter import BOTH, END, LEFT, RIGHT, VERTICAL, W, X, filedialog, messagebox
import tkinter as tk
from tkinter import ttk


ROOT = Path(__file__).resolve().parent.parent
LOCAL_DIR = ROOT / ".local" / "whatsapp-web-explorer"
EDGE_PROFILE = ROOT / ".local" / "edge-whatsapp-profile"
LEADS_FILE = LOCAL_DIR / "leads.json"
EDGE_SCRIPT = ROOT / "scripts" / "abrir_whatsapp_web_edge.ps1"


@dataclass
class Lead:
    nombre: str
    telefono: str
    etapa: str
    ultimo_mensaje: str
    pendiente: str
    score: int


DEMO_LEADS = [
    Lead(
        "Lead curso bienes raices",
        "5215500000000",
        "calificado",
        "Hola, vi el curso. Cuanto sale? Se me hace caro.",
        "Responder objecion y ofrecer horarios",
        62,
    ),
    Lead(
        "Lead molesto",
        "5215500000001",
        "escalado",
        "Ya van tres veces que pregunto lo mismo.",
        "Pasar a humano",
        28,
    ),
    Lead(
        "Lead fuera de catalogo",
        "bsu_01HZK3M9QX7T2VW4",
        "pendiente",
        "Tambien venden el curso de trading?",
        "Revisar catalogo",
        41,
    ),
]


class ExplorerApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("WhatsApp Web Explorer")
        self.geometry("1180x760")
        self.minsize(980, 640)
        self.configure(bg="#f5f1e8")
        self.leads: list[Lead] = []
        self.selected_index: int | None = None

        self._configure_style()
        self._build()
        self._load_leads()

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(".", font=("Segoe UI", 10))
        style.configure("TFrame", background="#f5f1e8")
        style.configure("Surface.TFrame", background="#fffaf1", relief="solid", borderwidth=1)
        style.configure("Muted.TLabel", background="#f5f1e8", foreground="#6b665d")
        style.configure("Title.TLabel", background="#f5f1e8", foreground="#171814", font=("Segoe UI", 22, "bold"))
        style.configure("H2.TLabel", background="#fffaf1", foreground="#171814", font=("Segoe UI", 12, "bold"))
        style.configure("Small.TLabel", background="#fffaf1", foreground="#6b665d", font=("Segoe UI", 9))
        style.configure("Accent.TButton", background="#286846", foreground="#ffffff", padding=(14, 8))
        style.map("Accent.TButton", background=[("active", "#1f5739")])
        style.configure("TButton", padding=(12, 7))
        style.configure("Treeview", rowheight=34, fieldbackground="#fffaf1", background="#fffaf1", borderwidth=0)
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))

    def _build(self) -> None:
        container = ttk.Frame(self, padding=18)
        container.pack(fill=BOTH, expand=True)

        header = ttk.Frame(container)
        header.pack(fill=X, pady=(0, 16))

        left = ttk.Frame(header)
        left.pack(side=LEFT, fill=X, expand=True)
        ttk.Label(left, text="WhatsApp Web Explorer", style="Title.TLabel").pack(anchor=W)
        ttk.Label(
            left,
            text="Demo local: Edge persistente, CRM de leads, borradores IA y CSV controlado.",
            style="Muted.TLabel",
        ).pack(anchor=W, pady=(4, 0))

        actions = ttk.Frame(header)
        actions.pack(side=RIGHT)
        ttk.Button(actions, text="Abrir WhatsApp Web", style="Accent.TButton", command=self.open_edge).pack(side=LEFT, padx=(0, 8))
        ttk.Button(actions, text="Guardar local", command=self.save_leads).pack(side=LEFT)

        body = ttk.PanedWindow(container, orient=tk.HORIZONTAL)
        body.pack(fill=BOTH, expand=True)

        left_panel = ttk.Frame(body)
        right_panel = ttk.Frame(body)
        body.add(left_panel, weight=3)
        body.add(right_panel, weight=2)

        self._build_leads(left_panel)
        self._build_detail(right_panel)

    def _build_leads(self, parent: ttk.Frame) -> None:
        card = ttk.Frame(parent, style="Surface.TFrame", padding=14)
        card.pack(fill=BOTH, expand=True)

        top = ttk.Frame(card, style="Surface.TFrame")
        top.pack(fill=X, pady=(0, 10))
        ttk.Label(top, text="Bandeja CRM local", style="H2.TLabel").pack(side=LEFT)
        ttk.Button(top, text="Cargar demo", command=self.load_demo).pack(side=RIGHT)
        ttk.Button(top, text="Importar CSV", command=self.import_csv).pack(side=RIGHT, padx=(0, 8))

        columns = ("nombre", "telefono", "etapa", "pendiente", "score")
        self.tree = ttk.Treeview(card, columns=columns, show="headings", selectmode="browse")
        for col, label, width in [
            ("nombre", "Lead", 230),
            ("telefono", "Contacto", 150),
            ("etapa", "Etapa", 110),
            ("pendiente", "Pendiente", 250),
            ("score", "Score", 70),
        ]:
            self.tree.heading(col, text=label)
            self.tree.column(col, width=width, anchor=W)

        scroll = ttk.Scrollbar(card, orient=VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side=LEFT, fill=BOTH, expand=True)
        scroll.pack(side=RIGHT, fill=tk.Y)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

    def _build_detail(self, parent: ttk.Frame) -> None:
        card = ttk.Frame(parent, style="Surface.TFrame", padding=14)
        card.pack(fill=BOTH, expand=True, padx=(14, 0))

        ttk.Label(card, text="Panel del vendedor IA", style="H2.TLabel").pack(anchor=W)
        ttk.Label(
            card,
            text="Este panel aun no envia. Prepara borradores y deja todo en revision.",
            style="Small.TLabel",
        ).pack(anchor=W, pady=(2, 12))

        self.status_var = tk.StringVar(value="Perfil Edge: pendiente")
        ttk.Label(card, textvariable=self.status_var, style="Small.TLabel").pack(anchor=W, pady=(0, 12))

        self.detail = tk.Text(card, height=9, wrap="word", bd=0, bg="#f8f3ea", fg="#171814", padx=10, pady=10)
        self.detail.pack(fill=X)

        ttk.Label(card, text="Borrador sugerido", style="H2.TLabel").pack(anchor=W, pady=(16, 8))
        self.draft = tk.Text(card, height=8, wrap="word", bd=0, bg="#eef6f1", fg="#171814", padx=10, pady=10)
        self.draft.pack(fill=X)

        row = ttk.Frame(card, style="Surface.TFrame")
        row.pack(fill=X, pady=(10, 0))
        ttk.Button(row, text="Generar borrador", style="Accent.TButton", command=self.generate_draft).pack(side=LEFT)
        ttk.Button(row, text="Marcar revisado", command=self.mark_reviewed).pack(side=LEFT, padx=(8, 0))
        ttk.Button(row, text="Simular envio controlado", command=self.simulate_send).pack(side=LEFT, padx=(8, 0))

        ttk.Label(card, text="Cola de envio demo", style="H2.TLabel").pack(anchor=W, pady=(18, 8))
        self.queue = tk.Listbox(card, height=6, bd=0, bg="#fffaf1", fg="#171814", highlightthickness=1, highlightcolor="#d8d2c4")
        self.queue.pack(fill=BOTH, expand=True)

    def _load_leads(self) -> None:
        LOCAL_DIR.mkdir(parents=True, exist_ok=True)
        self.status_var.set(
            "Perfil Edge: existe" if EDGE_PROFILE.exists() else "Perfil Edge: se creara al abrir WhatsApp Web"
        )
        if LEADS_FILE.exists():
            try:
                raw = json.loads(LEADS_FILE.read_text(encoding="utf-8"))
                self.leads = [Lead(**item) for item in raw]
            except (json.JSONDecodeError, TypeError):
                self.leads = []
        if not self.leads:
            self.leads = DEMO_LEADS.copy()
        self.refresh_tree()

    def refresh_tree(self) -> None:
        self.tree.delete(*self.tree.get_children())
        for idx, lead in enumerate(self.leads):
            self.tree.insert(
                "",
                END,
                iid=str(idx),
                values=(lead.nombre, lead.telefono, lead.etapa, lead.pendiente, lead.score),
            )
        if self.leads:
            self.tree.selection_set("0")
            self.tree.focus("0")
            self.selected_index = 0
            self.show_lead(self.leads[0])

    def on_select(self, _event: tk.Event) -> None:
        selected = self.tree.selection()
        if not selected:
            return
        self.selected_index = int(selected[0])
        self.show_lead(self.leads[self.selected_index])

    def show_lead(self, lead: Lead) -> None:
        self.detail.delete("1.0", END)
        self.detail.insert(
            END,
            "\n".join(
                [
                    f"Nombre: {lead.nombre}",
                    f"Contacto: {lead.telefono}",
                    f"Etapa: {lead.etapa}",
                    f"Score: {lead.score}",
                    "",
                    f"Ultimo mensaje: {lead.ultimo_mensaje}",
                    f"Pendiente: {lead.pendiente}",
                ]
            ),
        )
        self.draft.delete("1.0", END)

    def load_demo(self) -> None:
        self.leads = DEMO_LEADS.copy()
        self.refresh_tree()
        self.queue.delete(0, END)

    def import_csv(self) -> None:
        path = filedialog.askopenfilename(
            title="Importar contactos CSV",
            filetypes=[("CSV", "*.csv"), ("Todos", "*.*")],
        )
        if not path:
            return
        imported: list[Lead] = []
        with open(path, newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                nombre = row.get("nombre") or row.get("name") or row.get("Nombre") or "Contacto CSV"
                telefono = row.get("telefono") or row.get("phone") or row.get("Telefono") or ""
                producto = row.get("producto") or row.get("product") or "producto"
                imported.append(
                    Lead(
                        nombre=nombre.strip(),
                        telefono=telefono.strip(),
                        etapa="importado",
                        ultimo_mensaje=f"Contacto importado para {producto}.",
                        pendiente="Preparar mensaje personalizado",
                        score=0,
                    )
                )
        if imported:
            self.leads = imported
            self.refresh_tree()
            messagebox.showinfo("CSV importado", f"Se cargaron {len(imported)} contacto(s).")
        else:
            messagebox.showwarning("CSV vacio", "No encontre contactos en el CSV.")

    def generate_draft(self) -> None:
        lead = self.current_lead()
        if not lead:
            return
        if lead.etapa == "escalado":
            text = (
                "Te paso con una persona del equipo para revisar esto bien. "
                "Gracias por avisarnos; no quiero darte una respuesta automatica cuando hace falta contexto."
            )
        elif lead.etapa == "pendiente":
            text = (
                "Ese producto no esta en mi catalogo confirmado. Lo dejo anotado para que una persona "
                "del equipo lo revise y te responda con datos correctos."
            )
        else:
            text = (
                "Gracias por escribir. El programa sale 12000 MXN y se puede pagar en tres partes. "
                "Si te sirve, puedo ofrecerte hoy 11:00, hoy 17:00 o manana 10:00 para revisar si encaja contigo."
            )
        self.draft.delete("1.0", END)
        self.draft.insert(END, text)

    def mark_reviewed(self) -> None:
        lead = self.current_lead()
        if lead is None or self.selected_index is None:
            return
        lead.pendiente = "Borrador revisado"
        self.leads[self.selected_index] = lead
        self.refresh_tree()

    def simulate_send(self) -> None:
        lead = self.current_lead()
        if not lead:
            return
        draft = self.draft.get("1.0", END).strip()
        if not draft:
            messagebox.showwarning("Sin borrador", "Genera o escribe un borrador antes de simular.")
            return
        self.queue.insert(END, f"DEMO: {lead.telefono} -> {draft[:72]}")
        messagebox.showinfo("Envio demo", "No se envio nada real. Quedo registrado en la cola demo.")

    def save_leads(self) -> None:
        LOCAL_DIR.mkdir(parents=True, exist_ok=True)
        LEADS_FILE.write_text(
            json.dumps([asdict(lead) for lead in self.leads], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        messagebox.showinfo("Guardado", f"Datos guardados en {LEADS_FILE}")

    def open_edge(self) -> None:
        if not EDGE_SCRIPT.exists():
            messagebox.showerror("Falta script", f"No existe {EDGE_SCRIPT}")
            return
        cmd = [
            "powershell",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(EDGE_SCRIPT),
        ]
        try:
            subprocess.Popen(cmd, cwd=str(ROOT))
        except OSError as exc:
            messagebox.showerror("No pude abrir Edge", str(exc))
            return
        self.status_var.set("Perfil Edge: abierto para WhatsApp Web")

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
