from tkinter import *
from tkinter import ttk
import database
from utils.receipt import print_total_blood_inventory
from utils.export import export_to_csv
from constants import RESERVE_INVENTORY
from ui.styles import COLORS

class InventoryWindow:
    def __init__(self, root, username="admin", role="admin"):
        self.root = root
        self.username = username
        self.role = role
        self.root.title("Blood Inventory Management")
        self.root.geometry("900x500")
        
        # Main Layout container
        self.container = ttk.Frame(self.root, padding=20)
        self.container.pack(fill=BOTH, expand=1)

        # Header row
        header = ttk.Frame(self.container)
        header.pack(fill=X, pady=(0, 15))
        ttk.Label(header, text="📦  Blood Inventory", style="H1.TLabel").pack(side=LEFT)
        
        btn_row = ttk.Frame(header)
        btn_row.pack(side=RIGHT)
        ttk.Button(btn_row, text="🖨 Print Report", style="Primary.TButton", command=self.print_data).pack(side=LEFT, padx=5)
        ttk.Button(btn_row, text="📤 Export CSV", style="Accent.TButton", command=lambda: export_to_csv(self.table, "inventory")).pack(side=LEFT, padx=5)
        ttk.Button(btn_row, text="↻ Refresh", style="Outline.TButton", command=self.fetch_data).pack(side=LEFT, padx=5)

        # Main Table Card
        self.card = ttk.Frame(self.container, style="Card.TFrame", padding=20)
        self.card.pack(fill=BOTH, expand=1)

        # Table Viewer
        table_frame = ttk.Frame(self.card)
        table_frame.pack(fill=BOTH, expand=1, pady=(0, 15))

        self.table = ttk.Treeview(table_frame, column=("Aplus", "Bplus", "Oplus", "ABplus", "Aneg", "Bneg", "Oneg", "ABneg"), height=3)
        
        cols = ["A+", "B+", "O+", "AB+", "A-", "B-", "O-", "AB-"]
        col_ids = ["Aplus", "Bplus", "Oplus", "ABplus", "Aneg", "Bneg", "Oneg", "ABneg"]
        
        for col_id, text in zip(col_ids, cols):
            self.table.heading(col_id, text=text)
            self.table.column(col_id, anchor=CENTER, width=100)

        self.table["show"] = "headings"
        self.table.pack(fill=BOTH, expand=1)

        # Summary section
        self.summary_frame = ttk.Frame(self.card, style="Card.TFrame")
        self.summary_frame.pack(fill=X, pady=(0, 5))

        self.fetch_data()

        # Status Bar
        self.status_frame = Frame(self.root, bg=COLORS["sidebar_bg"], height=26)
        self.status_frame.pack(side=BOTTOM, fill=X)
        self.status_frame.pack_propagate(False)
        self.status_label = Label(self.status_frame, text="", font=("Segoe UI", 9),
                                   bg=COLORS["sidebar_bg"], fg=COLORS["sidebar_fg"])
        self.status_label.pack(side=LEFT, padx=10)

        # Keyboard Shortcuts
        self.root.bind("<Escape>", lambda e: self.root.destroy())
        self.root.bind("<Control-p>", lambda e: self.print_data())
        self.root.bind("<Control-e>", lambda e: export_to_csv(self.table, "inventory"))
        self.root.bind("<F5>", lambda e: self.fetch_data())

    def fetch_data(self):
        rows = database.get_blood_total()
        self.table.delete(*self.table.get_children())
        
        # Color-code inventory levels
        self.table.tag_configure("critical", background="#fef2f2", foreground="#dc2626")
        self.table.tag_configure("ok", background=COLORS["card"], foreground=COLORS["text_dark"])
        
        total = 0
        blood_types = ["A+", "B+", "O+", "AB+", "A-", "B-", "O-", "AB-"]
        if rows:
            for row in rows:
                reserve_breached = False
                for blood_type, amount in zip(blood_types, row[:8]):
                    if int(amount) <= RESERVE_INVENTORY.get(blood_type, 0):
                        reserve_breached = True
                        break

                if reserve_breached:
                    tag = "critical"
                else:
                    tag = "ok"
                self.table.insert("", END, values=row, tags=(tag,))
                total = sum(row[:8]) if len(row) >= 8 else 0

        # Update summary
        for widget in self.summary_frame.winfo_children():
            widget.destroy()
        
        ttk.Label(self.summary_frame, text=f"Total Units Available: {total}",
                  style="CardH2.TLabel", font=("Segoe UI", 14, "bold")).pack(side=LEFT, padx=5)
        
        # Color legend
        legend = ttk.Frame(self.summary_frame, style="Card.TFrame")
        legend.pack(side=RIGHT)
        Label(legend, text="● At Reserve", font=("Segoe UI", 9), bg=COLORS["card"], fg="#dc2626").pack(side=LEFT, padx=8)
        Label(legend, text="● Above Reserve", font=("Segoe UI", 9), bg=COLORS["card"], fg=COLORS["success"]).pack(side=LEFT, padx=8)
        
        # Update status bar
        try:
            self.status_label.config(text=f"  📦 {total} total units across 8 blood types")
        except Exception:
            pass

    def print_data(self):
        rows = database.get_blood_total()
        print_total_blood_inventory(rows)
