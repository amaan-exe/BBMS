from tkinter import *
from tkinter import messagebox
from tkinter import ttk
import re
import database
from constants import FORMAT_DATE, BLOOD_GROUP_MAPPING
from utils.receipt import print_receipt as generate_receipt
from utils.export import export_to_csv
from utils.audit_log import log_action
from tkcalendar import Calendar
from datetime import datetime
from utils.tooltip import ToolTip
from ui.styles import COLORS

class DonorWindow:
    def __init__(self, root, username="admin", role="admin", mode="both", on_db_change=None):
        self.root = root
        self.username = username
        self.role = role
        self.mode = mode  # 'both', 'add', or 'view'
        self.on_db_change = on_db_change
        self.current_row = None
        self.root.title("Donor Management")
        self.root.geometry("1280x760")
        self.root.minsize(1180, 720)
        self._build_ui()
        self.fetch_data()

    def _build_ui(self):
        self.container = ttk.Frame(self.root, padding=20)
        self.container.pack(fill=BOTH, expand=1)

        hero = ttk.Frame(self.container, style="Hero.TFrame", padding=18)
        hero.pack(fill=X, pady=(0, 16))
        hero.columnconfigure(0, weight=3)
        hero.columnconfigure(1, weight=1)

        hero_left = ttk.Frame(hero, style="Hero.TFrame")
        hero_left.grid(row=0, column=0, sticky=W)
        ttk.Label(hero_left, text="Donor Management", style="Section.TLabel").pack(anchor=W)
        ttk.Label(
            hero_left,
            text="Register donors, update inventory in one pass, and keep every record searchable.",
            style="SectionSub.TLabel",
        ).pack(anchor=W, pady=(4, 0))

        badge_row = ttk.Frame(hero_left, style="Hero.TFrame")
        badge_row.pack(anchor=W, pady=(12, 0))
        ttk.Label(badge_row, text="Mobile login", style="BadgePrimary.TLabel").pack(side=LEFT, padx=(0, 8))
        ttk.Label(badge_row, text="Search by name, mobile, ID", style="Badge.TLabel").pack(side=LEFT, padx=(0, 8))
        ttk.Label(badge_row, text="Printable receipt", style="Badge.TLabel").pack(side=LEFT)

        hero_right = ttk.Frame(hero, style="HeroAccent.TFrame", padding=14)
        hero_right.grid(row=0, column=1, sticky=NSEW, padx=(16, 0))
        ttk.Label(hero_right, text="Quick actions", style="Header.TLabel").pack(anchor=W)
        ttk.Label(hero_right, text="Add donor records fast, then review or export them from the table.", style="Header.TLabel", wraplength=220, justify=LEFT).pack(anchor=W, pady=(8, 0))

        self.body = ttk.Frame(self.container)
        self.body.pack(fill=BOTH, expand=1)

        self.left_col = ttk.Frame(self.body, style="Card.TFrame", padding=20)
        self.left_col.pack(side=LEFT, fill=Y, padx=(0, 10))

        self._build_form_panel()

        self.right_col = ttk.Frame(self.body, style="Card.TFrame", padding=20)
        self.right_col.pack(side=LEFT, fill=BOTH, expand=1, padx=(10, 0))
        if self.mode == "add":
            self._build_add_summary_panel()
        else:
            self._build_table_panel()

        self.status_frame = ttk.Frame(self.root, style="StatusBar.TFrame", height=26)
        self.status_frame.pack(side=BOTTOM, fill=X)
        self.status_frame.pack_propagate(False)
        self.status_label = ttk.Label(self.status_frame, text="", style="StatusBar.TLabel")
        self.status_label.pack(side=LEFT, padx=10)

        if self.mode == "view":
            self.left_col.forget()

        self.root.bind("<Escape>", lambda e: self.reset_donor())
        self.root.bind("<Control-s>", lambda e: self.add_donor())
        self.root.bind("<Control-u>", lambda e: self.update_donor())
        self.root.bind("<Control-f>", lambda e: self.txtSearch.focus_set() if hasattr(self, "txtSearch") else self.txtcname.focus_set())
        self.root.bind("<Control-p>", lambda e: self.print_receipt() if hasattr(self, "txtSearch") else None)
        self.root.bind("<Control-r>", lambda e: self.fetch_data() if hasattr(self, "table") else None)
        if hasattr(self, "txtSearch"):
            self.txtSearch.bind("<Return>", lambda e: self.search_donor())
        self.txtcname.bind("<Return>", lambda e: self.add_donor())
        if self.role == "admin":
            self.root.bind("<Control-d>", lambda e: self.delete_donor())

    def _build_form_panel(self):
        # Configure columns for 2-column layout
        self.left_col.columnconfigure(0, weight=1)
        self.left_col.columnconfigure(1, weight=2)
        self.left_col.columnconfigure(2, minsize=15) # spacer column
        self.left_col.columnconfigure(3, weight=1)
        self.left_col.columnconfigure(4, weight=2)

        header = ttk.Frame(self.left_col, style="Card.TFrame")
        header.grid(row=0, column=0, columnspan=5, sticky=EW)
        ttk.Label(header, text="Donor Details", style="Section.TLabel").pack(anchor=W)
        ttk.Label(
            header,
            text="Fields marked here feed the donor portal account and inventory update.",
            style="SectionSub.TLabel",
        ).pack(anchor=W, pady=(4, 10))

        # Row 2: Full Name & Gender
        ttk.Label(self.left_col, text="Full Name", style="Field.TLabel").grid(row=2, column=0, sticky=W, pady=4)
        self.txtcname = ttk.Entry(self.left_col, width=18)
        self.txtcname.grid(row=2, column=1, sticky=EW, pady=4)

        ttk.Label(self.left_col, text="Gender", style="Field.TLabel").grid(row=2, column=3, sticky=W, pady=4)
        self.combo_Gender = ttk.Combobox(self.left_col, values=("Male", "Female", "Transgender", "Other"), state="readonly", width=16)
        self.combo_Gender.grid(row=2, column=4, sticky=EW, pady=4)
        self.combo_Gender.current(0)

        # Row 3: Address & Mobile Number
        ttk.Label(self.left_col, text="Address", style="Field.TLabel").grid(row=3, column=0, sticky=W, pady=4)
        self.txtpostcode = ttk.Entry(self.left_col, width=18)
        self.txtpostcode.grid(row=3, column=1, sticky=EW, pady=4)

        ttk.Label(self.left_col, text="Mobile Number", style="Field.TLabel").grid(row=3, column=3, sticky=W, pady=4)
        self.txtmobile = ttk.Entry(self.left_col, width=18)
        self.txtmobile.grid(row=3, column=4, sticky=EW, pady=4)

        # Row 4: Nationality & ID Proof
        ttk.Label(self.left_col, text="Nationality", style="Field.TLabel").grid(row=4, column=0, sticky=W, pady=4)
        self.combo_nationality = ttk.Combobox(self.left_col, values=("Indian", "American", "British", "Russian", "Other"), state="readonly", width=16)
        self.combo_nationality.grid(row=4, column=1, sticky=EW, pady=4)
        self.combo_nationality.current(0)

        ttk.Label(self.left_col, text="ID Proof", style="Field.TLabel").grid(row=4, column=3, sticky=W, pady=4)
        self.combo_idproof = ttk.Combobox(self.left_col, values=("Aadhaar Card", "Driving Licence", "Passport", "Visa", "Voter ID", "Pan Card"), state="readonly", width=16)
        self.combo_idproof.grid(row=4, column=4, sticky=EW, pady=4)
        self.combo_idproof.current(0)

        # Row 5: ID Number & Age Group
        ttk.Label(self.left_col, text="ID Number", style="Field.TLabel").grid(row=5, column=0, sticky=W, pady=4)
        self.txtidnumber = ttk.Entry(self.left_col, width=18)
        self.txtidnumber.grid(row=5, column=1, sticky=EW, pady=4)

        ttk.Label(self.left_col, text="Age Group", style="Field.TLabel").grid(row=5, column=3, sticky=W, pady=4)
        self.combo_age = ttk.Combobox(self.left_col, values=("18-20", "21-30", "31-40", "41-50", "51-60", "61-70"), state="readonly", width=16)
        self.combo_age.grid(row=5, column=4, sticky=EW, pady=4)
        self.combo_age.current(0)

        # Row 6: Blood Type & Units (ml)
        ttk.Label(self.left_col, text="Blood Type", style="Field.TLabel").grid(row=6, column=0, sticky=W, pady=4)
        self.combo_bloodtype = ttk.Combobox(self.left_col, values=list(BLOOD_GROUP_MAPPING.keys()), state="readonly", width=16)
        self.combo_bloodtype.grid(row=6, column=1, sticky=EW, pady=4)
        self.combo_bloodtype.current(0)

        ttk.Label(self.left_col, text="Units (ml)", style="Field.TLabel").grid(row=6, column=3, sticky=W, pady=4)
        self.txtunit = ttk.Entry(self.left_col, width=18)
        self.txtunit.grid(row=6, column=4, sticky=EW, pady=4)

        # Row 7: Any Disease & Donation Date
        ttk.Label(self.left_col, text="Any Disease", style="Field.TLabel").grid(row=7, column=0, sticky=W, pady=4)
        self.combo_anydi = ttk.Combobox(self.left_col, values=("Yes", "No"), state="readonly", width=16)
        self.combo_anydi.grid(row=7, column=1, sticky=EW, pady=4)
        self.combo_anydi.current(1)

        ttk.Label(self.left_col, text="Donation Date", style="Field.TLabel").grid(row=7, column=3, sticky=W, pady=4)
        date_row = ttk.Frame(self.left_col, style="Card.TFrame")
        date_row.grid(row=7, column=4, sticky=EW, pady=4)
        date_row.columnconfigure(0, weight=1)
        self.date_var = StringVar(value=datetime.now().strftime("%d/%m/%y"))
        self.date_entry = ttk.Entry(date_row, textvariable=self.date_var, state="readonly")
        self.date_entry.grid(row=0, column=0, sticky=EW)
        ttk.Button(date_row, text="📅", width=3, style="Outline.TButton", command=self.open_date_picker).grid(row=0, column=1, padx=(6, 0))

        # Footer Row 8
        footer = ttk.Frame(self.left_col, style="Card.TFrame")
        footer.grid(row=8, column=0, columnspan=5, pady=(14, 0), sticky=EW)
        footer.columnconfigure(0, weight=1)
        footer.columnconfigure(1, weight=1)
        ttk.Button(footer, text="Save Donor", style="Success.TButton", command=self.add_donor).grid(row=0, column=0, sticky=EW, padx=(0, 6))
        ttk.Button(footer, text="Reset", style="Outline.TButton", command=self.reset_donor).grid(row=0, column=1, sticky=EW, padx=(6, 0))

    def open_date_picker(self):
        picker = Toplevel(self.root)
        picker.title("Select Donation Date")
        picker.transient(self.root)
        picker.grab_set()
        picker.resizable(False, False)

        wrapper = ttk.Frame(picker, padding=12)
        wrapper.pack(fill=BOTH, expand=1)
        cal = Calendar(
            wrapper,
            selectmode="day",
            date_pattern="dd/mm/yy",
            background=COLORS["primary"],
            foreground=COLORS["text_light"],
            headersbackground=COLORS["primary_dark"],
            selectbackground=COLORS["primary_dark"],
            selectforeground=COLORS["text_light"],
        )
        cal.pack(fill=BOTH, expand=1)

        def apply_date():
            self.date_var.set(cal.get_date())
            picker.destroy()

        actions = ttk.Frame(wrapper)
        actions.pack(fill=X, pady=(10, 0))
        ttk.Button(actions, text="Use Date", style="Success.TButton", command=apply_date).pack(side=LEFT, expand=1, fill=X, padx=(0, 6))
        ttk.Button(actions, text="Cancel", style="Outline.TButton", command=picker.destroy).pack(side=LEFT, expand=1, fill=X, padx=(6, 0))

    def _build_table_panel(self):
        toolbar = ttk.Frame(self.right_col, style="Card.TFrame")
        toolbar.pack(fill=X, pady=(0, 12))

        ttk.Label(toolbar, text="Records", style="Section.TLabel").pack(side=LEFT)
        ttk.Label(toolbar, text="Search, export, print, or open a profile card.", style="SectionSub.TLabel").pack(side=LEFT, padx=(10, 0))

        actions = ttk.Frame(self.right_col, style="Card.TFrame")
        actions.pack(fill=X, pady=(0, 12))
        ttk.Label(actions, text="🔍", style="Card.TLabel", font=("Segoe UI", 12)).pack(side=LEFT, padx=(0, 5))
        self.combo_Search = ttk.Combobox(actions, values=("Name", "Mobile", "Idnumber", "Bloodtype"), state="readonly", width=14)
        self.combo_Search.current(0)
        self.combo_Search.pack(side=LEFT, padx=(0, 6))

        self.txtSearch = ttk.Entry(actions, width=24)
        self.txtSearch.pack(side=LEFT, padx=(0, 6))

        ttk.Button(actions, text="Search", style="Accent.TButton", command=self.search_donor).pack(side=LEFT, padx=3)
        ttk.Button(actions, text="All", style="Outline.TButton", command=self.fetch_data).pack(side=LEFT, padx=3)
        ttk.Button(actions, text="Print", style="Outline.TButton", command=self.print_receipt).pack(side=RIGHT, padx=3)
        ttk.Button(actions, text="Export", style="Outline.TButton", command=lambda: export_to_csv(self.table, "donors")).pack(side=RIGHT, padx=3)
        if self.mode == "view":
            ttk.Button(actions, text="Update Selected", style="Accent.TButton", command=self._update_selected_donor).pack(side=LEFT, padx=3)
            ttk.Button(actions, text="Delete Selected", style="Danger.TButton", command=self._delete_selected_donor).pack(side=LEFT, padx=3)

        table_frame = ttk.Frame(self.right_col, style="Card.TFrame")
        table_frame.pack(fill=BOTH, expand=1)

        scroll_x = ttk.Scrollbar(table_frame, orient=HORIZONTAL)
        scroll_y = ttk.Scrollbar(table_frame, orient=VERTICAL)

        self.table = ttk.Treeview(
            table_frame,
            column=("date", "Name", "Gender", "Pincode", "Mobile", "Nationality", "Idproof", "Idnumber", "Age", "Bloodtype", "Unitml"),
            xscrollcommand=scroll_x.set,
            yscrollcommand=scroll_y.set,
            selectmode="browse",
        )

        scroll_x.pack(side=BOTTOM, fill=X)
        scroll_y.pack(side=RIGHT, fill=Y)
        scroll_x.config(command=self.table.xview)
        scroll_y.config(command=self.table.yview)

        cols = ["Date", "Name", "Gender", "Address", "Mobile", "Nationality", "ID Proof", "ID Number", "Age", "Blood Type", "Unit(ml)"]
        widths = [90, 130, 85, 130, 110, 110, 120, 120, 85, 95, 90]
        self.sort_reverse = {}

        for col, width, text in zip(self.table["columns"], widths, cols):
            self.sort_reverse[col] = False
            self.table.heading(col, text=text, command=lambda c=col: self.sort_column(c))
            self.table.column(col, width=width, anchor=CENTER, stretch=True)

        self.table["show"] = "headings"
        self.table.pack(fill=BOTH, expand=1)
        self.table.bind("<ButtonRelease-1>", self.get_cursor)
        self.table.bind("<Double-1>", self.show_profile_card)

    def _build_add_summary_panel(self):
        header = ttk.Frame(self.right_col, style="Card.TFrame")
        header.pack(fill=X, pady=(0, 14))
        ttk.Label(header, text="Live Overview", style="Section.TLabel").pack(anchor=W)
        ttk.Label(header, text="A quick snapshot while you register a new donor.", style="SectionSub.TLabel").pack(anchor=W, pady=(4, 0))

        stats = ttk.Frame(self.right_col, style="Card.TFrame")
        stats.pack(fill=X, pady=(0, 14))
        stats.columnconfigure(0, weight=1)
        stats.columnconfigure(1, weight=1)
        stats.columnconfigure(2, weight=1)

        self._summary_card(stats, 0, "Total donors", str(database.get_total_donors_count()), COLORS["danger"])
        self._summary_card(stats, 1, "Inventory groups", str(len(database.get_blood_inventory_dict() or {})), COLORS["accent"])
        low_inventory = len(database.get_low_inventory_alerts())
        self._summary_card(stats, 2, "Low stock alerts", str(low_inventory), COLORS["warning"])

        inventory_frame = ttk.Frame(self.right_col, style="Card.TFrame")
        inventory_frame.pack(fill=X, pady=(0, 14))
        ttk.Label(inventory_frame, text="Inventory balance", style="Section.TLabel").pack(anchor=W)
        ttk.Label(inventory_frame, text="Blood stock updates automatically after a donation is saved.", style="SectionSub.TLabel").pack(anchor=W, pady=(4, 10))

        inv = database.get_blood_inventory_dict()
        inv_grid = ttk.Frame(inventory_frame, style="Card.TFrame")
        inv_grid.pack(fill=X)
        inv_grid.columnconfigure(0, weight=1)
        inv_grid.columnconfigure(1, weight=1)
        inv_grid.columnconfigure(2, weight=1)
        inv_grid.columnconfigure(3, weight=1)

        for idx, blood_type in enumerate(["A+", "B+", "O+", "AB+", "A-", "B-", "O-", "AB-"]):
            # Cell border
            cell_border = Frame(inv_grid, bg=COLORS["border"], bd=0)
            cell_border.grid(row=idx // 4, column=idx % 4, padx=6, pady=6, sticky=NSEW)
            
            cell = Frame(cell_border, bg=COLORS["card"], bd=0, padx=10, pady=10)
            cell.pack(fill=BOTH, expand=1, padx=1, pady=1)
            
            # Top row: Blood Type pill
            top_row = Frame(cell, bg=COLORS["card"])
            top_row.pack(fill=X, anchor=W)
            
            # Badge
            badge_color = COLORS["primary"] if "+" in blood_type else "#3b82f6"
            badge = Label(top_row, text=f" {blood_type} ", font=("Segoe UI", 9, "bold"), fg=COLORS["text_light"], bg=badge_color, padx=4, pady=1)
            badge.pack(side=LEFT)
            
            # Value
            amount = inv.get(blood_type, 0)
            val_str = f"{amount:,}"
            
            val_frame = Frame(cell, bg=COLORS["card"])
            val_frame.pack(fill=X, pady=(6, 0))
            
            val_lbl = Label(val_frame, text=val_str, font=("Segoe UI", 13, "bold"), fg=COLORS["text_dark"], bg=COLORS["card"])
            val_lbl.pack(side=LEFT, anchor=S)
            
            ml_lbl = Label(val_frame, text=" ml", font=("Segoe UI", 8), fg=COLORS["text_muted"], bg=COLORS["card"])
            ml_lbl.pack(side=LEFT, anchor=S, padx=(2, 0))
            
            # Progress bar
            max_capacity = 250000
            percentage = min(1.0, max(0.01, amount / max_capacity))
            
            bar_wrap = Frame(cell, bg=COLORS["border"], height=4, bd=0)
            bar_wrap.pack(fill=X, pady=(6, 0))
            
            w_fill = int(percentage * 100)
            w_empty = 100 - w_fill
            bar_wrap.columnconfigure(0, weight=w_fill)
            bar_wrap.columnconfigure(1, weight=w_empty)
            
            bar_color = COLORS["danger"] if percentage < 0.15 else COLORS["success"]
            fill_frame = Frame(bar_wrap, bg=bar_color, height=4)
            fill_frame.grid(row=0, column=0, sticky=EW)

        recent_frame = ttk.Frame(self.right_col, style="Card.TFrame")
        recent_frame.pack(fill=BOTH, expand=1)
        ttk.Label(recent_frame, text="Recent donors", style="Section.TLabel").pack(anchor=W)
        ttk.Label(recent_frame, text="Newest records appear here once the form is saved.", style="SectionSub.TLabel").pack(anchor=W, pady=(4, 10))

        table_frame = ttk.Frame(recent_frame, style="Card.TFrame")
        table_frame.pack(fill=BOTH, expand=1)

        scroll_y = ttk.Scrollbar(table_frame, orient=VERTICAL)
        self.summary_table = ttk.Treeview(
            table_frame,
            columns=("Name", "Blood", "Units", "Mobile"),
            show="headings",
            height=5,
            yscrollcommand=scroll_y.set,
            selectmode="browse",
        )
        scroll_y.pack(side=RIGHT, fill=Y)
        scroll_y.config(command=self.summary_table.yview)

        for col, text, width, alignment in [
            ("Name", "Donor", 160, W),
            ("Blood", "Blood", 70, CENTER),
            ("Units", "Units", 70, CENTER),
            ("Mobile", "Mobile", 120, CENTER),
        ]:
            self.summary_table.heading(col, text=text, anchor=alignment)
            self.summary_table.column(col, width=width, anchor=alignment, stretch=True)
        self.summary_table.pack(fill=BOTH, expand=1)

    def _summary_card(self, parent, column, title, value, color):
        # Outer border frame
        border_frame = Frame(parent, bg=COLORS["border"], bd=0)
        border_frame.grid(row=0, column=column, padx=4, pady=4, sticky=NSEW)
        
        # Inner container frame
        inner = Frame(border_frame, bg=COLORS["card"], bd=0)
        inner.pack(fill=BOTH, expand=1, padx=1, pady=1)
        
        # Left accent color strip
        accent_bar = Frame(inner, bg=color, width=4)
        accent_bar.pack(side=LEFT, fill=Y)
        
        # Content container
        content = Frame(inner, bg=COLORS["card"], padx=12, pady=10)
        content.pack(side=LEFT, fill=BOTH, expand=1)
        
        # Labels
        lbl_title = Label(content, text=title.upper(), font=("Segoe UI", 8, "bold"), fg=COLORS["text_muted"], bg=COLORS["card"])
        lbl_title.pack(anchor=W)
        
        lbl_value = Label(content, text=value, font=("Segoe UI", 20, "bold"), fg=color, bg=COLORS["card"])
        lbl_value.pack(anchor=W, pady=(4, 0))

    def _create_field_row(self, parent, row, label_text, widget):
        ttk.Label(parent, text=label_text, style="Field.TLabel").grid(row=row, column=0, sticky=W, pady=6, padx=(0, 12))
        widget.grid(row=row, column=1, sticky=EW, pady=6)

    def _populate_table(self, rows, status_text):
        if hasattr(self, "table"):
            self.table.delete(*self.table.get_children())
            self.table.tag_configure("oddrow", background=COLORS["row_alt"])
            self.table.tag_configure("evenrow", background=COLORS["card"])
            for index, row in enumerate(rows):
                tag = "oddrow" if index % 2 == 0 else "evenrow"
                self.table.insert("", END, values=row, tags=(tag,))
        if hasattr(self, "summary_table"):
            self.summary_table.delete(*self.summary_table.get_children())
            recent_rows = sorted(rows, key=lambda r: r[0], reverse=True)[:8]
            for row in recent_rows:
                self.summary_table.insert("", END, values=(row[1], row[9], row[10], row[4]))
        self.status_label.config(text=status_text)

    def _bind_mousewheel(self, widget):
        def on_mousewheel(event):
            widget.yview_scroll(int(-1 * (event.delta / 120)), "units")

        widget.bind("<MouseWheel>", on_mousewheel)
        widget.bind("<Button-4>", lambda e: widget.yview_scroll(-1, "units"))
        widget.bind("<Button-5>", lambda e: widget.yview_scroll(1, "units"))

    def sort_column(self, col):
        """Sort treeview by clicking column headers."""
        data = [(self.table.set(item, col), item) for item in self.table.get_children("")]
        self.sort_reverse[col] = not self.sort_reverse.get(col, False)
        data.sort(reverse=self.sort_reverse[col])
        for index, (val, item) in enumerate(data):
            self.table.move(item, "", index)

    def show_profile_card(self, event=""):
        """Shows a popup profile card for the selected donor record."""
        cursor_row = self.table.focus()
        content = self.table.item(cursor_row)
        row = content["values"]
        if not row:
            return
        
        card_win = Toplevel(self.root)
        card_win.title(f"Donor Profile — {row[1]}")
        card_win.geometry("400x500")
        card_win.resizable(False, False)
        
        container = ttk.Frame(card_win, padding=25)
        container.pack(fill=BOTH, expand=1)
        
        # Header
        ttk.Label(container, text="🩸", font=("Segoe UI", 40)).pack()
        ttk.Label(container, text=str(row[1]), font=("Segoe UI", 20, "bold")).pack(pady=(5, 2))
        ttk.Label(container, text=f"{row[9]} Donor", font=("Segoe UI", 12), foreground="#888888").pack()
        
        ttk.Separator(container).pack(fill=X, pady=15)
        
        # Details grid
        details = ttk.Frame(container)
        details.pack(fill=X)
        
        fields = [
            ("Date", row[0]), ("Gender", row[2]), ("Address", row[3]),
            ("Mobile", row[4]), ("Nationality", row[5]), ("ID Proof", row[6]),
            ("ID Number", row[7]), ("Age Group", row[8]), ("Units (ml)", row[10])
        ]
        for i, (label, value) in enumerate(fields):
            ttk.Label(details, text=f"{label}:", font=("Segoe UI", 10, "bold")).grid(row=i, column=0, sticky=W, pady=2)
            ttk.Label(details, text=str(value), font=("Segoe UI", 10)).grid(row=i, column=1, sticky=W, padx=15, pady=2)

    def is_valid_mobile(self, s):
        pattern = re.compile(r"^(0|91)?[6-9][0-9]{9}$")
        return pattern.fullmatch(s)

    def fetch_data(self):
        rows = database.get_all_donors()
        self._populate_table(rows, f"  📋 {len(rows)} donor record(s) loaded")

    def add_donor(self):
        if not all([self.txtcname.get(), self.combo_age.get(), self.combo_nationality.get(), self.combo_idproof.get(), self.combo_Gender.get(), self.txtmobile.get(), self.txtpostcode.get(), self.combo_bloodtype.get(), self.txtidnumber.get(), self.combo_anydi.get(), self.txtunit.get()]):
            messagebox.showerror("Error", "All fields are required", parent=self.root)
            return

        if self.combo_anydi.get().lower() == "yes":
            messagebox.showerror("Sorry", "You can't Donate Blood\nYou are suffering from Disease", parent=self.root)
            return

        if not self.is_valid_mobile(self.txtmobile.get()):
            messagebox.showerror("Error", "Incorrect Mobile Number", parent=self.root)
            return

        try:
            units = int(self.txtunit.get())
            if units <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Units must be a positive number", parent=self.root)
            return

        try:
            database.add_donor_with_portal_and_inventory(
                self.date_entry.get(),
                self.txtcname.get(),
                self.combo_Gender.get(),
                self.txtpostcode.get(),
                self.txtmobile.get(),
                self.combo_nationality.get(),
                self.combo_idproof.get(),
                self.txtidnumber.get(),
                self.combo_age.get(),
                self.combo_bloodtype.get(),
                self.txtunit.get(),
            )
            
            messagebox.showinfo("Success", f"Donation has been added.\nPortal Username: {self.txtmobile.get()}\nPassword: {self.txtmobile.get()}", parent=self.root)
            log_action(self.username, "ADD_DONOR", f"Name: {self.txtcname.get()}, Mobile: {self.txtmobile.get()}, Blood: {self.combo_bloodtype.get()}")
            self.fetch_data()
            self.reset_donor()
            if self.on_db_change:
                self.on_db_change()
        except Exception as es:
            messagebox.showwarning("Warning", f"Something went wrong: {str(es)}", parent=self.root)

    def update_donor(self):
        if not self.current_row:
            messagebox.showwarning("Warning", "Select a donor first", parent=self.root)
            return
            
        messagebox.showinfo("Note", "You can update Mobile, Address, Age, and Units", parent=self.root)
        try:
            old_mobile = self.current_row[4] if self.current_row else self.txtmobile.get()
            database.update_donor(
                self.txtmobile.get(), self.current_row[4], self.txtpostcode.get(),
                self.combo_age.get(), self.txtunit.get(), self.txtidnumber.get()
            )
            portal_password, _ = database.sync_portal_account(
                old_mobile,
                self.txtcname.get(),
                self.txtmobile.get(),
                self.txtidnumber.get(),
                "donor",
                question="Auto-generated donor portal account",
            )
            messagebox.showinfo("Update", "Donor details updated successfully", parent=self.root)
            log_action(self.username, "UPDATE_DONOR", f"Mobile: {self.txtmobile.get()}")
            self.fetch_data()
            self.reset_donor()
            if self.on_db_change:
                self.on_db_change()
        except Exception as es:
            messagebox.showwarning("Warning", f"Something went wrong: {str(es)}", parent=self.root)

    def delete_donor(self):
        if self.role != "admin":
            messagebox.showerror("Access Denied", "Only admins can delete records.", parent=self.root)
            return
        if not self.current_row:
            messagebox.showwarning("Warning", "Select a donor first", parent=self.root)
            return
        if messagebox.askyesno("Confirm Delete", "Do you want to delete this Donor?", parent=self.root):
            try:
                blood_type = str(self.current_row[9])
                units = int(self.current_row[10])
                col_name = BLOOD_GROUP_MAPPING.get(blood_type)
                if col_name:
                    current_avl = database.get_specific_blood_total(col_name)
                    new_amount = max(0, current_avl - units)
                    database.update_blood_total(col_name, new_amount)
            except (ValueError, KeyError):
                pass  # If inventory can't be reconciled, still delete the record
            database.delete_portal_account(self.current_row[4])
            log_action(self.username, "DELETE_DONOR", f"Mobile: {self.txtmobile.get()}")
            database.delete_donor(self.txtmobile.get())
            self.fetch_data()
            self.reset_donor()
            if self.on_db_change:
                self.on_db_change()
            messagebox.showinfo("Deleted", "Donor details deleted successfully", parent=self.root)       

    def search_donor(self):
        rows = database.search_donor(self.combo_Search.get(), self.txtSearch.get())
        if rows:
            self._populate_table(rows, f"  🔎 {len(rows)} donor match(es) found")
        else:
            messagebox.showerror("Error", "No Donor details found", parent=self.root)

    def get_cursor(self, event=""):
        cursor_row = self.table.focus()
        content = self.table.item(cursor_row)
        row = content["values"]
        if not row:
            return
            
        self.current_row = row
        self.reset_donor()   
        self.txtcname.insert(0, str(row[1]))
        self.combo_Gender.set(str(row[2]))
        self.txtpostcode.insert(0, str(row[3]))
        self.txtmobile.insert(0, str(row[4]))
        self.combo_nationality.set(str(row[5]))
        self.combo_idproof.set(str(row[6]))
        self.txtidnumber.insert(0, str(row[7]))
        self.combo_age.set(str(row[8]))
        self.combo_bloodtype.set(str(row[9]))
        self.txtunit.insert(0, str(row[10]))
        self.combo_anydi.set("No")

    def reset_donor(self):
        self.txtcname.delete(0, END)
        self.combo_Gender.current(0)
        self.txtpostcode.delete(0, END)
        self.txtmobile.delete(0, END)
        self.combo_nationality.current(0)
        self.combo_idproof.current(0)
        self.txtidnumber.delete(0, END)
        self.combo_age.current(0)
        self.combo_bloodtype.current(0)
        self.txtunit.delete(0, END)
        self.combo_anydi.current(1)
        self.date_var.set(datetime.now().strftime("%d/%m/%y"))

    def print_receipt(self):
        mobile = self.txtmobile.get()
        if not mobile:
            messagebox.showerror("Error", "Please select a donor first.", parent=self.root)
            return
        rows = database.get_donor_by_mobile(mobile)
        if rows:
            generate_receipt("Donater", mobile, rows[0])
        else:
            messagebox.showerror("Error", "Donor not found for printing.", parent=self.root)

    def _update_selected_donor(self):
        cursor_row = self.table.focus()
        content = self.table.item(cursor_row)
        row = content.get("values")
        if not row:
            messagebox.showwarning("Warning", "Select a donor first", parent=self.root)
            return

        old_mobile = row[4]
        old_id = row[7]

        dlg = Toplevel(self.root)
        dlg.title("Update Donor — " + str(row[1]))
        dlg.geometry("400x300")
        frm = ttk.Frame(dlg, padding=12)
        frm.pack(fill=BOTH, expand=1)

        ttk.Label(frm, text="Mobile:").grid(row=0, column=0, sticky=W)
        ent_mobile = ttk.Entry(frm)
        ent_mobile.grid(row=0, column=1, sticky=EW)
        ent_mobile.insert(0, str(row[4]))

        ttk.Label(frm, text="Address:").grid(row=1, column=0, sticky=W)
        ent_addr = ttk.Entry(frm)
        ent_addr.grid(row=1, column=1, sticky=EW)
        ent_addr.insert(0, str(row[3]))

        ttk.Label(frm, text="Age Group:").grid(row=2, column=0, sticky=W)
        ent_age = ttk.Entry(frm)
        ent_age.grid(row=2, column=1, sticky=EW)
        ent_age.insert(0, str(row[8]))

        ttk.Label(frm, text="Units (ml):").grid(row=3, column=0, sticky=W)
        ent_units = ttk.Entry(frm)
        ent_units.grid(row=3, column=1, sticky=EW)
        ent_units.insert(0, str(row[10]))

        ttk.Label(frm, text="ID Number:").grid(row=4, column=0, sticky=W)
        ent_id = ttk.Entry(frm)
        ent_id.grid(row=4, column=1, sticky=EW)
        ent_id.insert(0, str(row[7]))

        def on_save():
            try:
                new_mobile = ent_mobile.get()
                new_addr = ent_addr.get()
                new_age = ent_age.get()
                new_units = ent_units.get()
                new_id = ent_id.get()
                database.update_donor(new_mobile, old_mobile, new_addr, new_age, new_units, new_id)
                # sync portal account if mobile/id changed
                try:
                    database.sync_portal_account(old_mobile, row[1], new_mobile, new_id, 'donor')
                except Exception:
                    pass
                # Recompute allocations/totals to keep inventory consistent
                try:
                    database.rebuild_allocations_and_totals()
                except Exception:
                    pass
                self.fetch_data()
                if self.on_db_change:
                    self.on_db_change()
                dlg.destroy()
                messagebox.showinfo("Updated", "Donor updated successfully", parent=self.root)
            except Exception as e:
                messagebox.showwarning("Warning", f"Update failed: {e}", parent=dlg)

        ttk.Button(frm, text="Save", style="Accent.TButton", command=on_save).grid(row=5, column=0, columnspan=2, pady=10)

    def _delete_selected_donor(self):
        cursor_row = self.table.focus()
        content = self.table.item(cursor_row)
        row = content.get("values")
        if not row:
            messagebox.showwarning("Warning", "Select a donor first", parent=self.root)
            return
        if messagebox.askyesno("Confirm Delete", f"Delete donor {row[1]}?", parent=self.root):
            try:
                database.delete_portal_account(row[4])
            except Exception:
                pass
            try:
                database.delete_donor(row[4])
            except Exception:
                pass
            try:
                database.rebuild_allocations_and_totals()
            except Exception:
                pass
            self.fetch_data()
            if self.on_db_change:
                self.on_db_change()
            messagebox.showinfo("Deleted", "Donor deleted successfully", parent=self.root)
