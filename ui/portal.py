from tkinter import *
from tkinter import messagebox, ttk

import pandas as pd

import database
from ui.styles import COLORS
from utils.audit_log import log_action


class UserPortalWindow:
    def __init__(self, root, on_logout, username, role):
        self.root = root
        self.on_logout = on_logout
        self.username = username
        self.role = role

        self.root.title("Patient Portal")
        self.root.geometry("1120x760")

        self.donor_summary = None
        self.receiver_summary = None
        self.donor_records = []
        self.receiver_records = []

        self.build_ui()

    def build_ui(self):
        for widget in self.root.winfo_children():
            widget.destroy()

        self.base = ttk.Frame(self.root)
        self.base.pack(fill=BOTH, expand=1)

        self.header = Frame(self.base, bg=COLORS["primary_dark"], height=58)
        self.header.pack(side=TOP, fill=X)
        self.header.pack_propagate(False)

        Label(self.header, text="🩸 Blood Bank Portal", font=("Segoe UI", 18, "bold"), bg=COLORS["primary_dark"], fg="white").pack(side=LEFT, padx=20)
        Label(self.header, text=f"👤 {self.username} ({self.role.upper()})", font=("Segoe UI", 10), bg=COLORS["primary_dark"], fg="#ffcccc").pack(side=RIGHT, padx=20)

        self.body = ttk.Frame(self.base)
        self.body.pack(fill=BOTH, expand=1)

        self.sidebar = Frame(self.body, bg=COLORS["sidebar_bg"], width=220)
        self.sidebar.pack(side=LEFT, fill=Y)
        self.sidebar.pack_propagate(False)

        self.content = ttk.Frame(self.body, padding=18)
        self.content.pack(side=LEFT, fill=BOTH, expand=1)

        self._build_sidebar()
        self._build_statusbar()
        self._build_content()

        self.root.bind("<Escape>", lambda e: self.logout())
        self.root.bind("<F5>", lambda e: self.refresh())

    def _build_sidebar(self):
        Label(self.sidebar, text="PORTAL", font=("Segoe UI", 8, "bold"), bg=COLORS["sidebar_bg"], fg=COLORS["text_muted"]).pack(anchor=W, padx=18, pady=(18, 8))
        self._sidebar_btn("🏠  Home", self.show_home)
        self._sidebar_btn("📋  My Records", self.show_records)
        if self.role == "member":
            self._sidebar_btn("🔁  Allocation Status", self.show_allocations)
        self._sidebar_btn("↪  Logout", self.logout)

    def _sidebar_btn(self, text, command):
        btn = Button(self.sidebar, text=text, font=("Segoe UI", 10), anchor=W, bg=COLORS["sidebar_bg"], fg=COLORS["sidebar_fg"], activebackground=COLORS["sidebar_hover"], activeforeground="white", relief=FLAT, padx=18, pady=8, cursor="hand2", command=command)
        btn.pack(fill=X)
        btn.bind("<Enter>", lambda e: btn.config(bg=COLORS["sidebar_hover"]))
        btn.bind("<Leave>", lambda e: btn.config(bg=COLORS["sidebar_bg"]))

    def _build_statusbar(self):
        self.statusbar = Frame(self.base, bg=COLORS["sidebar_bg"], height=28)
        self.statusbar.pack(side=BOTTOM, fill=X)
        self.statusbar.pack_propagate(False)
        self.status_label = Label(self.statusbar, text="", font=("Segoe UI", 9), bg=COLORS["sidebar_bg"], fg=COLORS["sidebar_fg"])
        self.status_label.pack(side=LEFT, padx=10)
        self._update_status()

    def _clear_content(self):
        for widget in self.content.winfo_children():
            widget.destroy()

    def _build_content(self):
        self.show_home()

    def _load_data(self):
        self.donor_summary = database.get_donor_portal_summary(self.username)
        self.receiver_summary = database.get_receiver_portal_summary(self.username)
        self.donor_records = database.get_donor_portal_records(self.username)
        self.receiver_records = database.get_receiver_portal_records(self.username)

        if self.donor_records:
            latest_used = next((record for record in reversed(self.donor_records) if record["used_units"] > 0), None)
            self.donor_summary["last_used_by"] = latest_used["used_by"] if latest_used else ""
            self.donor_summary["last_used_on"] = latest_used["used_on"] if latest_used else ""

        if self.receiver_records:
            latest_received = next((record for record in reversed(self.receiver_records) if record["allocated_units"] > 0), None)
            self.receiver_summary["last_received_from"] = latest_received["received_from"] if latest_received else ""
            self.receiver_summary["last_received_from_id"] = latest_received["received_from_id"] if latest_received else ""
            self.receiver_summary["last_received_on"] = latest_received["received_on"] if latest_received else ""

    def _update_status(self):
        self._load_data()
        if self.role == "donor":
            self.status_label.config(text=f"  Donated: {self.donor_summary['donated_units']} ml | Used: {self.donor_summary['used_units']} ml | Remaining: {self.donor_summary['remaining_units']} ml")
        elif self.role == "receiver":
            self.status_label.config(text=f"  Requested: {self.receiver_summary['requested_units']} ml | Allocated: {self.receiver_summary['allocated_units']} ml | Pending: {self.receiver_summary['pending_units']} ml")
        else:
            self.status_label.config(text=f"  Donor remaining: {self.donor_summary['remaining_units']} ml | Receiver pending: {self.receiver_summary['pending_units']} ml")

    def show_home(self):
        self._clear_content()
        self._load_data()

        ttk.Label(self.content, text="My Portal", style="H1.TLabel").pack(anchor=W, pady=(0, 14))

        cards = ttk.Frame(self.content)
        cards.pack(fill=X, pady=(0, 16))
        card_count = 4 if self.role == "member" else 3
        for index in range(card_count):
            cards.columnconfigure(index, weight=1)

        if self.role in ("donor", "member"):
            self._metric_card(cards, 0, "Donations", str(self.donor_summary["donation_count"]), COLORS["danger"])
            self._metric_card(cards, 1, "Donated (ml)", str(self.donor_summary["donated_units"]), COLORS["accent"])
            self._metric_card(cards, 2, "Used (ml)", str(self.donor_summary["used_units"]), COLORS["warning"])
            if self.role == "member":
                self._metric_card(cards, 3, "Remaining", str(self.donor_summary["remaining_units"]), COLORS["success"])
        else:
            self._metric_card(cards, 0, "Requests", str(self.receiver_summary["request_count"]), COLORS["accent"])
            self._metric_card(cards, 1, "Requested (ml)", str(self.receiver_summary["requested_units"]), COLORS["danger"])
            self._metric_card(cards, 2, "Allocated (ml)", str(self.receiver_summary["allocated_units"]), COLORS["success"])
            if self.role == "member":
                self._metric_card(cards, 3, "Pending", str(self.receiver_summary["pending_units"]), COLORS["warning"])

        panel = ttk.Frame(self.content)
        panel.pack(fill=BOTH, expand=1)

        left = ttk.Frame(panel, style="Card.TFrame", padding=16)
        left.pack(side=LEFT, fill=BOTH, expand=1, padx=(0, 10))
        right = ttk.Frame(panel, style="Card.TFrame", padding=16)
        right.pack(side=LEFT, fill=BOTH, expand=1, padx=(10, 0))

        if self.role in ("donor", "member"):
            self._summary_panel(left, "Donor Summary", self.donor_summary, donor=True)
        else:
            self._summary_panel(left, "Receiver Summary", self.receiver_summary, donor=False)

        if self.role == "member":
            self._summary_panel(right, "Receiver Summary", self.receiver_summary, donor=False)
        else:
            self._render_status_block(right)

        self._update_status()

    def _metric_card(self, parent, column, title, value, color):
        card = ttk.Frame(parent, style="Card.TFrame", padding=14)
        card.grid(row=0, column=column, padx=8, sticky=NSEW)
        ttk.Label(card, text=title, style="CardMuted.TLabel").pack(anchor=W)
        Label(card, text=value, font=("Segoe UI", 26, "bold"), bg=COLORS["card"], fg=color).pack(anchor=W, pady=(8, 0))

    def _summary_panel(self, parent, title, summary, donor=True):
        ttk.Label(parent, text=title, style="H2.TLabel").pack(anchor=W, pady=(0, 8))
        if donor:
            last_used_by = summary.get("last_used_by", "") or "Not used yet"
            last_used_on = summary.get("last_used_on", "") or "-"
            rows = [
                ("Name", summary["name"]),
                ("Donations", summary["donation_count"]),
                ("Total Donated", f"{summary['donated_units']} ml"),
                ("Used", f"{summary['used_units']} ml"),
                ("Remaining", f"{summary['remaining_units']} ml"),
                ("Last Used By", last_used_by),
                ("Last Used On", last_used_on),
            ]
        else:
            last_received_on = summary.get("last_received_on", "") or "-"
            rows = [
                ("Name", summary["name"]),
                ("Requests", summary["request_count"]),
                ("Total Requested", f"{summary['requested_units']} ml"),
                ("Allocated", f"{summary['allocated_units']} ml"),
                ("Pending", f"{summary['pending_units']} ml"),
                ("Received On", last_received_on),
            ]
        for label, value in rows:
            row = ttk.Frame(parent, style="Card.TFrame")
            row.pack(fill=X, pady=4)
            ttk.Label(row, text=f"{label}:", style="CardMuted.TLabel", width=18).pack(side=LEFT)
            ttk.Label(row, text=str(value), style="Card.TLabel").pack(side=LEFT)

    def _render_status_block(self, parent):
        ttk.Label(parent, text="Status", style="H2.TLabel").pack(anchor=W, pady=(0, 8))
        if self.role == "donor":
            status = "Fully used" if self.donor_summary["remaining_units"] == 0 else "Partially used" if self.donor_summary["used_units"] else "Unused"
            text = f"Your donated blood batches are currently: {status}."
        else:
            status = "Fulfilled" if self.receiver_summary["pending_units"] == 0 else "Partially fulfilled" if self.receiver_summary["allocated_units"] else "Pending"
            text = f"Your request status is currently: {status}."
        ttk.Label(parent, text=text, style="Card.TLabel", wraplength=300, justify=LEFT).pack(anchor=W, pady=(0, 10))

        if self.role == "donor":
            self._records_table(parent, self.donor_records, donor=True)
        else:
            self._records_table(parent, self.receiver_records, donor=False)

    def _records_table(self, parent, records, donor=True):
        if donor:
            columns = ("date", "idnumber", "blood_type", "donated_units", "used_units", "used_by", "used_on", "status")
            headings = [("date", "Date"), ("idnumber", "Batch ID"), ("blood_type", "Blood Type"), ("donated_units", "Donated"), ("used_units", "Used"), ("used_by", "Used By"), ("used_on", "Used On"), ("status", "Status")]
        else:
            columns = ("date", "idnumber", "blood_type", "requested_units", "allocated_units", "received_on", "status")
            headings = [("date", "Date"), ("idnumber", "Request ID"), ("blood_type", "Blood Type"), ("requested_units", "Requested"), ("allocated_units", "Allocated"), ("received_on", "Received On"), ("status", "Status")]

        table = ttk.Treeview(parent, columns=columns, show="headings", height=12)
        for key, title in headings:
            table.heading(key, text=title)
            table.column(key, width=95, anchor=CENTER)
        table.pack(fill=BOTH, expand=1, pady=(8, 0))

        for record in records:
            if donor:
                table.insert("", END, values=(record["date"], record["idnumber"], record["blood_type"], record["donated_units"], record["used_units"], record["used_by"] or "-", record["used_on"] or "-", record["status"]))
            else:
                table.insert("", END, values=(record["date"], record["idnumber"], record["blood_type"], record["requested_units"], record["allocated_units"], record["received_on"] or "-", record["status"]))

    def show_records(self):
        self._clear_content()
        self._load_data()

        if self.role == "donor":
            ttk.Label(self.content, text="My Donation History", style="H1.TLabel").pack(anchor=W, pady=(0, 12))
            self._records_table(self.content, self.donor_records, donor=True)
        elif self.role == "receiver":
            ttk.Label(self.content, text="My Request History", style="H1.TLabel").pack(anchor=W, pady=(0, 12))
            self._records_table(self.content, self.receiver_records, donor=False)
        else:
            notebook = ttk.Notebook(self.content)
            notebook.pack(fill=BOTH, expand=1)
            donor_tab = ttk.Frame(notebook, padding=10)
            receiver_tab = ttk.Frame(notebook, padding=10)
            notebook.add(donor_tab, text="Donations")
            notebook.add(receiver_tab, text="Requests")
            self._records_table(donor_tab, self.donor_records, donor=True)
            self._records_table(receiver_tab, self.receiver_records, donor=False)

    def show_allocations(self):
        if self.role != "member":
            self.show_home()
            return
        self._clear_content()
        self._load_data()
        ttk.Label(self.content, text="Allocation Status", style="H1.TLabel").pack(anchor=W, pady=(0, 12))
        ttk.Label(self.content, text="This view shows both donation batches and request fulfillment for linked donor/receiver access.", style="CardMuted.TLabel").pack(anchor=W, pady=(0, 12))
        notebook = ttk.Notebook(self.content)
        notebook.pack(fill=BOTH, expand=1)
        donor_tab = ttk.Frame(notebook, padding=10)
        receiver_tab = ttk.Frame(notebook, padding=10)
        notebook.add(donor_tab, text="Donation Batches")
        notebook.add(receiver_tab, text="Request Fulfillment")
        self._records_table(donor_tab, self.donor_records, donor=True)
        self._records_table(receiver_tab, self.receiver_records, donor=False)

    def refresh(self):
        self.show_home()
        log_action(self.username, "PORTAL_REFRESH", f"Role: {self.role}")

    def logout(self):
        if messagebox.askyesno("Logout", "Do you want to logout?", parent=self.root):
            log_action(self.username, "LOGOUT", f"Role: {self.role}")
            self.on_logout()
