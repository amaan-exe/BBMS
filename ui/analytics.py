from tkinter import *
from tkinter import messagebox, ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
import numpy as np
import pandas as pd

import database
from constants import BLOOD_GROUP_MAPPING
from ui.donor import DonorWindow
from ui.inventory import InventoryWindow
from ui.receiver import ReceiverWindow
from ui.styles import COLORS
from utils.audit_log import log_action
from utils.backup import backup_database, restore_database
from utils.pdf_report import generate_donor_report, generate_inventory_report, generate_receiver_report


BLOOD_ORDER = ["A+", "B+", "O+", "AB+", "A-", "B-", "O-", "AB-"]
AGE_ORDER = ["18-20", "21-30", "31-40", "41-50", "51-60", "61-70"]
PALETTES = {
    "Blue": ["#1d4ed8", "#3b82f6", "#60a5fa", "#93c5fd", "#dbeafe"],
    "Green": ["#166534", "#16a34a", "#22c55e", "#4ade80", "#bbf7d0"],
    "Red": ["#991b1b", "#dc2626", "#ef4444", "#f87171", "#fecaca"],
    "Teal": ["#115e59", "#0f766e", "#14b8a6", "#2dd4bf", "#99f6e4"],
    "Gold": ["#854d0e", "#d97706", "#f59e0b", "#fbbf24", "#fde68a"],
    "Purple": ["#6b21a8", "#7c3aed", "#8b5cf6", "#a78bfa", "#ddd6fe"],
}


class AnalyticsWindow:
    def __init__(self, root, username="Admin", role="admin"):
        self.root = root
        self.username = username
        self.role = role
        self.current_frame = pd.DataFrame()
        self.current_scope = "Combined"

        self.root.title("Admin Home - Medical Analytics")
        self.root.geometry("1360x820")

        self.scope_var = StringVar(value="Combined")
        self.chart_var = StringVar(value="Blood Group Count")
        self.style_var = StringVar(value="Bar")
        self.palette_var = StringVar(value="Blue")
        self.sort_var = StringVar(value="Descending")
        self.top_n_var = IntVar(value=8)
        self.show_values_var = BooleanVar(value=True)
        self.show_pct_var = BooleanVar(value=True)
        self.normalize_var = BooleanVar(value=False)
        self.group_by_var = StringVar(value="Blood Group")
        self.status_var = StringVar(value="Ready")
        self._refresh_job = None

        self.build_ui()
        self._wire_live_updates()

    def build_ui(self):
        for widget in self.root.winfo_children():
            widget.destroy()

        self.base = ttk.Frame(self.root)
        self.base.pack(fill=BOTH, expand=1)

        self.header = Frame(self.base, bg=COLORS["primary_dark"], height=58)
        self.header.pack(side=TOP, fill=X)
        self.header.pack_propagate(False)

        Label(
            self.header,
            text="🩸 Blood Bank - Admin Home",
            font=("Segoe UI", 18, "bold"),
            bg=COLORS["primary_dark"],
            fg="white",
        ).pack(side=LEFT, padx=20)

        Label(
            self.header,
            text=f"👤 {self.username} ({self.role.upper()})",
            font=("Segoe UI", 10),
            bg=COLORS["primary_dark"],
            fg="#ffcccc",
        ).pack(side=RIGHT, padx=20)

        self.body = ttk.Frame(self.base)
        self.body.pack(side=TOP, fill=BOTH, expand=1)

        self.content = ttk.Frame(self.body)
        self.content.pack(side=LEFT, fill=BOTH, expand=1)

        self._build_content()
        self._build_statusbar()

        self.root.bind("<Escape>", lambda e: self.logout_func())
        self.root.bind("<F5>", lambda e: self.refresh())
        self.root.bind("<Control-Key-1>", lambda e: self.open_donor())
        self.root.bind("<Control-Key-2>", lambda e: self.open_receiver())
        self.root.bind("<Control-Key-3>", lambda e: self.open_inventory())
        self.root.bind("<Control-Key-4>", lambda e: self.select_charts_tab())
        self.root.bind("<Control-Key-5>", lambda e: self.open_forecasting())
        self.root.bind("<Control-l>", lambda e: self.show_audit_log())
        self.root.bind("<Control-b>", lambda e: [backup_database(), log_action(self.username, "BACKUP")])

    def _build_content(self):
        self.notebook = ttk.Notebook(self.content)
        self.notebook.pack(fill=BOTH, expand=1)

        self.overview_tab = ttk.Frame(self.notebook, padding=20)
        self.charts_tab = ttk.Frame(self.notebook, padding=20)
        self.tables_tab = ttk.Frame(self.notebook, padding=20)

        self.notebook.add(self.overview_tab, text="Overview")
        self.notebook.add(self.charts_tab, text="Charts")
        self.notebook.add(self.tables_tab, text="Tables")

        self._build_overview_tab()
        self._build_charts_tab()
        self._build_tables_tab()

    def _build_statusbar(self):
        self.statusbar = Frame(self.base, bg=COLORS["sidebar_bg"], height=28)
        self.statusbar.pack(side=BOTTOM, fill=X)
        self.statusbar.pack_propagate(False)
        Label(self.statusbar, textvariable=self.status_var, font=("Segoe UI", 9), bg=COLORS["sidebar_bg"], fg=COLORS["sidebar_fg"]).pack(side=LEFT, padx=10)
        self.time_label = Label(self.statusbar, text="", font=("Segoe UI", 9), bg=COLORS["sidebar_bg"], fg=COLORS["sidebar_fg"])
        self.time_label.pack(side=RIGHT, padx=15)
        self._update_clock()

    def _sidebar_btn(self, text, command, shortcut=None):
        btn = Button(
            self.sidebar,
            text=text,
            font=("Segoe UI", 10),
            anchor=W,
            bg=COLORS["sidebar_bg"],
            fg=COLORS["sidebar_fg"],
            activebackground=COLORS["sidebar_hover"],
            activeforeground="white",
            relief=FLAT,
            padx=18,
            pady=8,
            cursor="hand2",
            command=command,
        )
        btn.pack(fill=X)
        btn.bind("<Enter>", lambda e: btn.config(bg=COLORS["sidebar_hover"]))
        btn.bind("<Leave>", lambda e: btn.config(bg=COLORS["sidebar_bg"]))
        if shortcut:
            btn.tooltip_text = shortcut

    def _update_clock(self):
        try:
            self.time_label.config(text=pd.Timestamp.now().strftime("%I:%M %p  •  %d %b %Y"))
            self.root.after(1000, self._update_clock)
        except Exception:
            pass

    def _clear_frame(self, frame):
        for widget in frame.winfo_children():
            widget.destroy()

    def load_records(self, scope=None):
        scope = scope or self.scope_var.get()

        def build_rows(rows, record_type):
            result = []
            for row in rows:
                result.append(
                    {
                        "record_type": record_type,
                        "date": row[0],
                        "name": row[1],
                        "gender": row[2],
                        "pincode": row[3],
                        "mobile": row[4],
                        "nationality": row[5],
                        "idproof": row[6],
                        "idnumber": row[7],
                        "age_group": row[8],
                        "blood_type": row[9],
                        "units": pd.to_numeric(row[10], errors="coerce"),
                    }
                )
            return result

        rows = []
        if scope in ("Combined", "Donors"):
            rows.extend(build_rows(database.get_all_donors(), "Donor"))
        if scope in ("Combined", "Receivers"):
            rows.extend(build_rows(database.get_all_receivers(), "Receiver"))

        df = pd.DataFrame(rows)
        if df.empty:
            self.current_frame = df
            return df

        df["units"] = pd.to_numeric(df["units"], errors="coerce").fillna(0).astype(float)
        df["date_dt"] = pd.to_datetime(df["date"], format="%d/%m/%y", errors="coerce")
        fallback = pd.date_range(end=pd.Timestamp.today(), periods=len(df), freq="D")
        mask = df["date_dt"].isna()
        if mask.any():
            df.loc[mask, "date_dt"] = fallback[mask.to_numpy()]
        df["month"] = df["date_dt"].dt.to_period("M").astype(str)
        df["age_group"] = pd.Categorical(df["age_group"], categories=AGE_ORDER, ordered=True)
        self.current_frame = df
        self.current_scope = scope
        return df

    def _palette(self):
        return PALETTES.get(self.palette_var.get(), PALETTES["Blue"])

    def _make_card(self, parent, column, title, value, color):
        border = Frame(parent, bg="#cbd5e1", padx=1, pady=1)
        border.grid(row=0, column=column, padx=8, sticky=NSEW)
        card = Frame(border, bg=COLORS["card"], padx=16, pady=16)
        card.pack(fill=BOTH, expand=1)
        Label(card, text=title, font=("Segoe UI", 9, "bold"), bg=COLORS["card"], fg=COLORS["text_muted"]).pack(anchor=W)
        Label(card, text=value, font=("Segoe UI", 26, "bold"), bg=COLORS["card"], fg=color).pack(anchor=W, pady=(8, 0))

    def _build_overview_tab(self):
        self._clear_frame(self.overview_tab)
        df = self.load_records()

        cards = ttk.Frame(self.overview_tab)
        cards.pack(fill=X, pady=(0, 16))
        for index in range(6):
            cards.columnconfigure(index, weight=1)

        donor_count = database.get_total_donors_count()
        receiver_count = database.get_total_receivers_count()
        inventory = database.get_blood_inventory_dict()
        total_units = sum(inventory.values()) if inventory else 0
        low_alerts = database.get_low_inventory_alerts()
        most_stocked = max(inventory.items(), key=lambda item: item[1])[0] if inventory else "N/A"
        most_requested = self._most_common_blood_group(database.get_requests_by_blood_type())

        self._make_card(cards, 0, "Donors", str(donor_count), COLORS["danger"])
        self._make_card(cards, 1, "Receivers", str(receiver_count), COLORS["accent"])
        self._make_card(cards, 2, "Stock Units", str(total_units), COLORS["success"])
        self._make_card(cards, 3, "Low Stock Types", str(len(low_alerts)), COLORS["warning"])
        self._make_card(cards, 4, "Most Stocked", most_stocked, COLORS["primary_dark"])
        self._make_card(cards, 5, "Most Requested", most_requested, COLORS["accent"])

        split = ttk.Frame(self.overview_tab)
        split.pack(fill=BOTH, expand=1)

        left = ttk.Frame(split, style="Card.TFrame", padding=16)
        left.pack(side=LEFT, fill=BOTH, expand=1, padx=(0, 10))

        right = ttk.Frame(split, style="Card.TFrame", padding=16)
        right.pack(side=LEFT, fill=BOTH, expand=1, padx=(10, 0))

        ttk.Label(left, text="Inventory Balance", style="CardH2.TLabel").pack(anchor=W, pady=(0, 10))
        self._draw_inventory_bars(left, inventory)

        ttk.Label(right, text="Medical Snapshot", style="CardH2.TLabel").pack(anchor=W, pady=(0, 10))
        self._draw_snapshot_panel(right, df)

    def _draw_inventory_bars(self, parent, inventory):
        fig = Figure(figsize=(5.5, 3.6), dpi=100, facecolor="white")
        ax = fig.add_subplot(111)
        blood_types = list(inventory.keys())
        values = list(inventory.values())
        colors = self._palette()[: len(blood_types)]
        ax.bar(blood_types, values, color=colors)
        ax.set_ylabel("Units")
        ax.set_title("Current Available Blood by Group")
        ax.tick_params(axis="x", labelrotation=25)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#cbd5e1')
        ax.spines['bottom'].set_color('#cbd5e1')
        ax.grid(axis="y", linestyle=":", alpha=0.3)
        for index, value in enumerate(values):
            ax.text(index, value + max(values) * 0.02 if values else 0, str(value), ha="center", va="bottom", fontsize=9)
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.get_tk_widget().pack(fill=BOTH, expand=1)
        canvas.draw()

    def _draw_snapshot_panel(self, parent, df):
        if df.empty:
            ttk.Label(parent, text="No patient data available.", foreground=COLORS["danger"]).pack(anchor=W)
            return

        stats = [
            ("Total Records", len(df)),
            ("Donor Records", int((df["record_type"] == "Donor").sum())),
            ("Receiver Records", int((df["record_type"] == "Receiver").sum())),
            ("Unique Blood Groups", df["blood_type"].nunique()),
            ("Unique Nationalities", df["nationality"].nunique()),
            ("Age Bands", df["age_group"].nunique()),
        ]

        for title, value in stats:
            row = ttk.Frame(parent, style="Card.TFrame")
            row.pack(fill=X, pady=4)
            ttk.Label(row, text=title + ":", style="CardMuted.TLabel", width=22).pack(side=LEFT)
            ttk.Label(row, text=str(value), style="Card.TLabel").pack(side=LEFT)

        top_groups = df["blood_type"].value_counts().dropna().head(3)
        ttk.Label(parent, text="Top blood groups in records:", style="CardMuted.TLabel").pack(anchor=W, pady=(10, 4))
        for blood_type, count in top_groups.items():
            ttk.Label(parent, text=f"• {blood_type}: {int(count)} record(s)", style="Card.TLabel").pack(anchor=W)

    def _build_charts_tab(self):
        self._clear_frame(self.charts_tab)

        top = ttk.Frame(self.charts_tab)
        top.pack(fill=X, pady=(0, 12))
        ttk.Label(top, text="Medical Charts", style="H1.TLabel").pack(side=LEFT)
        ttk.Label(top, textvariable=self.status_var, style="CardMuted.TLabel").pack(side=RIGHT)

        body = ttk.Frame(self.charts_tab)
        body.pack(fill=BOTH, expand=1)

        self.controls = ttk.Frame(body, style="Card.TFrame", padding=16, width=340)
        self.controls.pack(side=LEFT, fill=Y, padx=(0, 10))
        self.controls.pack_propagate(False)

        self.chart_host = ttk.Frame(body, style="Card.TFrame", padding=10)
        self.chart_host.pack(side=LEFT, fill=BOTH, expand=1, padx=(10, 0))

        self._build_chart_controls()
        self._build_figure()

    def _build_chart_controls(self):
        ttk.Label(self.controls, text="Chart Settings", style="CardH2.TLabel").pack(anchor=W, pady=(0, 10))

        self._combo_row(self.controls, "Dataset", self.scope_var, ["Combined", "Donors", "Receivers"])
        self._combo_row(self.controls, "Report Chart", self.chart_var, [
            "Blood Group Count",
            "Blood Units by Group",
            "Supply vs Demand",
            "Gender Distribution",
            "Age Distribution",
            "Monthly Activity",
            "Nationality Mix",
        ])
        self._combo_row(self.controls, "Chart Style", self.style_var, ["Bar", "Horizontal", "Pie"])
        self._combo_row(self.controls, "Palette", self.palette_var, list(PALETTES.keys()))
        self._combo_row(self.controls, "Sort", self.sort_var, ["Descending", "Ascending", "Alphabetical"])

        top_row = ttk.Frame(self.controls, style="Card.TFrame")
        top_row.pack(fill=X, pady=(8, 4))
        ttk.Label(top_row, text="Top N / bars", style="Card.TLabel").pack(anchor=W)
        top_scale = Scale(top_row, from_=3, to=12, orient=HORIZONTAL, variable=self.top_n_var, resolution=1, bg=COLORS["card"], highlightthickness=0)
        top_scale.pack(fill=X)

        ttk.Checkbutton(self.controls, text="Show values", variable=self.show_values_var, style="Card.TCheckbutton").pack(anchor=W)
        ttk.Checkbutton(self.controls, text="Show percentages", variable=self.show_pct_var, style="Card.TCheckbutton").pack(anchor=W)
        ttk.Checkbutton(self.controls, text="Normalize values", variable=self.normalize_var, style="Card.TCheckbutton").pack(anchor=W)

        ttk.Label(self.controls, text="Blood Group Rank", style="CardH2.TLabel").pack(anchor=W, pady=(12, 6))
        self.rank_box = Listbox(self.controls, height=8, font=("Segoe UI", 10), bg=COLORS["input_bg"], fg=COLORS["input_fg"], relief=FLAT, highlightbackground=COLORS["input_border"])
        self.rank_box.pack(fill=X)

        action_row = ttk.Frame(self.controls, style="Card.TFrame")
        action_row.pack(fill=X, pady=(12, 4))
        ttk.Button(action_row, text="Update", style="Primary.TButton", command=self.render_chart).pack(side=LEFT, fill=X, expand=1, padx=(0, 4))
        ttk.Button(action_row, text="Overview", style="Outline.TButton", command=self.select_overview_tab).pack(side=LEFT, fill=X, expand=1, padx=(4, 0))

    def _combo_row(self, parent, label, variable, values):
        box = ttk.Frame(parent, style="Card.TFrame")
        box.pack(fill=X, pady=4)
        ttk.Label(box, text=label, style="Card.TLabel").pack(anchor=W)
        combo = ttk.Combobox(box, values=values, textvariable=variable, state="readonly")
        combo.pack(fill=X)
        combo.bind("<<ComboboxSelected>>", lambda e: self.schedule_refresh())

    def _wire_live_updates(self):
        watched_vars = [
            self.scope_var,
            self.chart_var,
            self.style_var,
            self.palette_var,
            self.sort_var,
            self.top_n_var,
            self.show_values_var,
            self.show_pct_var,
            self.normalize_var,
        ]
        for watched_var in watched_vars:
            watched_var.trace_add("write", lambda *_: self.schedule_refresh())

    def schedule_refresh(self):
        try:
            if self._refresh_job is not None:
                self.root.after_cancel(self._refresh_job)
        except Exception:
            pass
        self._refresh_job = self.root.after(120, self._apply_refresh)

    def _apply_refresh(self):
        self._refresh_job = None
        try:
            self.render_chart()
            self._populate_tables()
            self._build_overview_tab()
        except Exception:
            pass

    def _build_figure(self):
        self.figure = Figure(figsize=(8.8, 6.4), dpi=100, facecolor="white")
        self.ax_main = self.figure.add_subplot(211)
        self.ax_detail = self.figure.add_subplot(212)
        self.figure.tight_layout(pad=2.0)

        self.canvas = FigureCanvasTkAgg(self.figure, master=self.chart_host)
        self.canvas.get_tk_widget().pack(fill=BOTH, expand=1)

        toolbar = NavigationToolbar2Tk(self.canvas, self.chart_host)
        toolbar.update()

        self.render_chart()

    def _build_tables_tab(self):
        self._clear_frame(self.tables_tab)

        ttk.Label(self.tables_tab, text="Data Tables", style="H1.TLabel").pack(anchor=W, pady=(0, 12))

        note = ttk.Label(
            self.tables_tab,
            text="Tables summarize the current filtered dataset. Use the Charts tab to change the scope and chart type.",
            style="CardMuted.TLabel",
        )
        note.pack(anchor=W, pady=(0, 12))

        notebook = ttk.Notebook(self.tables_tab)
        notebook.pack(fill=BOTH, expand=1)

        self.table_blood = ttk.Frame(notebook, padding=10)
        self.table_gender = ttk.Frame(notebook, padding=10)
        self.table_age = ttk.Frame(notebook, padding=10)
        self.table_month = ttk.Frame(notebook, padding=10)

        notebook.add(self.table_blood, text="Blood Groups")
        notebook.add(self.table_gender, text="Gender")
        notebook.add(self.table_age, text="Age Bands")
        notebook.add(self.table_month, text="Monthly Activity")

        self._populate_tables()

    def _populate_tables(self):
        df = self.load_records()
        self._table_from_series(self.table_blood, "Blood Type", df["blood_type"].value_counts().reindex(BLOOD_ORDER).fillna(0).astype(int))
        self._table_from_series(self.table_gender, "Gender", df["gender"].value_counts())
        self._table_from_series(self.table_age, "Age Group", df["age_group"].value_counts().reindex(AGE_ORDER).fillna(0).astype(int))
        self._table_from_series(self.table_month, "Month", df["month"].value_counts().sort_index())

    def _table_from_series(self, parent, label_col, series):
        self._clear_frame(parent)
        tree = ttk.Treeview(parent, columns=(label_col, "Count"), show="headings", height=10)
        tree.heading(label_col, text=label_col)
        tree.heading("Count", text="Count")
        tree.column(label_col, width=220, anchor=W)
        tree.column("Count", width=120, anchor=CENTER)
        tree.pack(fill=BOTH, expand=1)
        for label, count in series.items():
            tree.insert("", END, values=(label, int(count)))

    def select_charts_tab(self):
        self.notebook.select(self.charts_tab)
        self.render_chart()

    def select_overview_tab(self):
        self.notebook.select(self.overview_tab)
        self._build_overview_tab()

    def refresh(self):
        log_action(self.username, "OPEN_ANALYTICS", f"Scope: {self.scope_var.get()} | Chart: {self.chart_var.get()}")
        self._build_overview_tab()
        self.render_chart()
        self._populate_tables()

    def _dataset_for_scope(self):
        df = self.load_records(self.scope_var.get()).copy()
        if df.empty:
            return df
        return df

    def _sort_series(self, series):
        if self.sort_var.get() == "Alphabetical":
            return series.sort_index()
        ascending = self.sort_var.get() == "Ascending"
        return series.sort_values(ascending=ascending)

    def _normalize(self, series):
        if not self.normalize_var.get():
            return series
        total = float(series.sum())
        if total <= 0:
            return series
        return (series / total) * 100.0

    def _blood_group_series(self, df):
        series = df["blood_type"].value_counts().reindex(BLOOD_ORDER).fillna(0)
        return self._sort_series(series)

    def _blood_units_series(self, df):
        series = df.groupby("blood_type")["units"].sum().reindex(BLOOD_ORDER).fillna(0)
        return self._sort_series(series)

    def _gender_series(self, df):
        return self._sort_series(df["gender"].value_counts())

    def _age_series(self, df):
        return self._sort_series(df["age_group"].value_counts().reindex(AGE_ORDER).fillna(0))

    def _month_series(self, df):
        return self._sort_series(df["month"].value_counts().sort_index())

    def _nationality_series(self, df):
        return self._sort_series(df["nationality"].value_counts())

    def _most_common_blood_group(self, counts):
        if not counts:
            return "N/A"
        return max(counts.items(), key=lambda item: item[1])[0]

    def render_chart(self):
        df = self._dataset_for_scope()
        if df.empty:
            messagebox.showerror("No Data", "There is no data available to generate charts.", parent=self.root)
            return

        self.ax_main.clear()
        self.ax_detail.clear()
        for ax in (self.ax_main, self.ax_detail):
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['left'].set_color('#cbd5e1')
            ax.spines['bottom'].set_color('#cbd5e1')
        palette = self._palette()
        chart_type = self.chart_var.get()
        style = self.style_var.get()
        top_n = max(3, int(self.top_n_var.get()))

        if chart_type == "Blood Group Count":
            series = self._blood_group_series(df).head(top_n)
            self._render_categorical_chart(self.ax_main, series, palette, style, "Blood Group Frequency", "Records")
            self._render_distribution_detail(df, self.ax_detail)
        elif chart_type == "Blood Units by Group":
            series = self._blood_units_series(df).head(top_n)
            self._render_categorical_chart(self.ax_main, series, palette, style, "Total Units by Blood Group", "Units")
            self._render_inventory_detail(self.ax_detail)
        elif chart_type == "Supply vs Demand":
            self._render_supply_demand(self.ax_main, palette)
            self._render_net_balance(self.ax_detail)
        elif chart_type == "Gender Distribution":
            series = self._gender_series(df).head(top_n)
            self._render_categorical_chart(self.ax_main, series, palette, style, "Gender Distribution", "Records")
            self._render_age_detail(df, self.ax_detail)
        elif chart_type == "Age Distribution":
            series = self._age_series(df).head(top_n)
            self._render_categorical_chart(self.ax_main, series, palette, style, "Age Band Distribution", "Records")
            self._render_month_detail(df, self.ax_detail)
        elif chart_type == "Monthly Activity":
            series = self._month_series(df)
            self._render_categorical_chart(self.ax_main, series, palette, "Bar", "Monthly Activity", "Records")
            self._render_nationality_detail(df, self.ax_detail)
        elif chart_type == "Nationality Mix":
            series = self._nationality_series(df).head(top_n)
            self._render_categorical_chart(self.ax_main, series, palette, style, "Nationality Mix", "Records")
            self._render_distribution_detail(df, self.ax_detail)

        self.figure.tight_layout(pad=2.0)
        self.canvas.draw_idle()
        self._update_rank_box(df)
        self._update_status(df)
        log_action(self.username, "OPEN_ANALYTICS", f"Scope: {self.scope_var.get()} | Chart: {self.chart_var.get()}")

    def _render_categorical_chart(self, ax, series, palette, style, title, ylabel):
        series = series.fillna(0)
        labels = list(series.index.astype(str))
        values = [float(v) for v in series.values]

        if style == "Pie":
            colors = [palette[i % len(palette)] for i in range(len(values))]
            wedges, texts, autotexts = ax.pie(values, labels=labels, colors=colors, autopct="%1.1f%%" if self.show_pct_var.get() else None, startangle=90)
            for text in texts:
                text.set_fontsize(9)
            for text in autotexts:
                text.set_color("white")
                text.set_fontsize(8)
            ax.axis("equal")
            ax.set_title(title)
            return

        if style == "Horizontal":
            bars = ax.barh(labels, values, color=[palette[i % len(palette)] for i in range(len(values))])
            ax.set_xlabel(ylabel)
            ax.set_title(title)
            ax.grid(axis="x", linestyle=":", alpha=0.35)
            if self.show_values_var.get():
                for bar, value in zip(bars, values):
                    ax.text(bar.get_width() + max(values) * 0.01 if values else 0, bar.get_y() + bar.get_height() / 2, f"{value:.0f}", va="center", fontsize=9)
        else:
            bars = ax.bar(labels, values, color=[palette[i % len(palette)] for i in range(len(values))])
            ax.set_ylabel(ylabel)
            ax.set_title(title)
            ax.grid(axis="y", linestyle=":", alpha=0.35)
            ax.tick_params(axis="x", labelrotation=25)
            if self.show_values_var.get():
                for bar, value in zip(bars, values):
                    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + (max(values) * 0.02 if values else 0), f"{value:.0f}", ha="center", va="bottom", fontsize=9)

    def _render_supply_demand(self, ax, palette):
        donor_counts = database.get_donations_by_blood_type()
        receiver_counts = database.get_requests_by_blood_type()

        donor_values = [donor_counts.get(group, 0) for group in BLOOD_ORDER]
        receiver_values = [receiver_counts.get(group, 0) for group in BLOOD_ORDER]

        x = np.arange(len(BLOOD_ORDER))
        width = 0.36

        donor_bars = ax.bar(x - width / 2, donor_values, width=width, label="Donors", color=palette[1])
        receiver_bars = ax.bar(x + width / 2, receiver_values, width=width, label="Receivers", color=palette[0])
        ax.set_xticks(x)
        ax.set_xticklabels(BLOOD_ORDER, rotation=25)
        ax.set_ylabel("Record Count")
        ax.set_title("Supply vs Demand by Blood Group")
        ax.legend()
        ax.grid(axis="y", linestyle=":", alpha=0.35)

        if self.show_values_var.get():
            for bar in list(donor_bars) + list(receiver_bars):
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.4, f"{int(bar.get_height())}", ha="center", fontsize=8)

    def _render_net_balance(self, ax):
        inventory = database.get_blood_inventory_dict()
        labels = list(inventory.keys())
        values = list(inventory.values())
        colors = ["#16a34a" if value >= 25 else "#f59e0b" if value >= 10 else "#dc2626" for value in values]
        bars = ax.bar(labels, values, color=colors)
        ax.set_ylabel("Available Units")
        ax.set_title("Current Inventory Balance")
        ax.grid(axis="y", linestyle=":", alpha=0.35)
        ax.tick_params(axis="x", labelrotation=25)
        for bar, value in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5, f"{int(value)}", ha="center", fontsize=8)

    def _render_distribution_detail(self, df, ax):
        counts = df["record_type"].value_counts()
        ax.pie(counts.values, labels=counts.index, autopct="%1.1f%%", startangle=90, colors=["#2563eb", "#dc2626"])
        ax.set_title("Donor vs Receiver Share")
        ax.axis("equal")

    def _render_inventory_detail(self, ax):
        inventory = database.get_blood_inventory_dict()
        labels = list(inventory.keys())
        values = list(inventory.values())
        ax.plot(labels, values, marker="o", color="#0f766e", linewidth=2)
        ax.fill_between(range(len(values)), values, color="#99f6e4", alpha=0.35)
        ax.set_title("Inventory Trend by Blood Type")
        ax.grid(axis="y", linestyle=":", alpha=0.35)
        ax.tick_params(axis="x", labelrotation=25)

    def _render_age_detail(self, df, ax):
        series = df["age_group"].value_counts().reindex(AGE_ORDER).fillna(0)
        ax.bar(series.index.astype(str), series.values, color="#7c3aed")
        ax.set_title("Age Group Distribution")
        ax.grid(axis="y", linestyle=":", alpha=0.35)
        ax.tick_params(axis="x", labelrotation=25)

    def _render_month_detail(self, df, ax):
        series = df.groupby("month").size().sort_index()
        ax.plot(series.index.astype(str), series.values, marker="o", color="#d97706", linewidth=2)
        ax.set_title("Monthly Activity")
        ax.grid(axis="y", linestyle=":", alpha=0.35)
        ax.tick_params(axis="x", labelrotation=25)

    def _render_nationality_detail(self, df, ax):
        series = df["nationality"].value_counts().head(6)
        ax.barh(series.index.astype(str), series.values, color="#1d4ed8")
        ax.set_title("Top Nationalities")
        ax.grid(axis="x", linestyle=":", alpha=0.35)

    def _update_rank_box(self, df):
        self.rank_box.delete(0, END)
        counts = df["blood_type"].value_counts().reindex(BLOOD_ORDER).fillna(0).astype(int)
        for blood_type, count in counts.sort_values(ascending=False).items():
            self.rank_box.insert(END, f"{blood_type}: {count}")

    def _update_status(self, df):
        donor_count = int((df["record_type"] == "Donor").sum())
        receiver_count = int((df["record_type"] == "Receiver").sum())
        stock = database.get_blood_inventory_dict()
        lowest = min(stock.items(), key=lambda item: item[1])[0] if stock else "N/A"
        self.status_var.set(
            f"Scope: {self.scope_var.get()} | Donors: {donor_count} | Receivers: {receiver_count} | Lowest stock: {lowest}"
        )

    def show_audit_log(self):
        log_win = Toplevel(self.root)
        log_win.title("Audit Log Viewer")
        log_win.geometry("850x550")

        container = ttk.Frame(log_win, padding=20)
        container.pack(fill=BOTH, expand=1)

        ttk.Label(container, text="🔍  System Audit Log", style="H1.TLabel").pack(anchor=W, pady=(0, 15))

        text_frame = ttk.Frame(container)
        text_frame.pack(fill=BOTH, expand=1)

        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.pack(side=RIGHT, fill=Y)

        log_text = Text(text_frame, wrap=WORD, yscrollcommand=scrollbar.set, font=("Consolas", 10), bg="#0f172a", fg="#4ade80", insertbackground="white", padx=15, pady=10, relief=FLAT)
        log_text.pack(fill=BOTH, expand=1)
        scrollbar.config(command=log_text.yview)

        try:
            with open("audit.log", "r", encoding="utf-8") as f:
                content = f.read()
                log_text.insert(END, content if content else "No audit events recorded yet.")
        except FileNotFoundError:
            log_text.insert(END, "No audit log file found.")
        log_text.config(state=DISABLED)

    def logout_func(self):
        if messagebox.askyesno("Logout", "Do you want to logout?", parent=self.root):
            log_action(self.username, "LOGOUT")
            self.root.destroy()

    def open_donor(self):
        DonorWindow(Toplevel(self.root), username=self.username, role=self.role)

    def open_receiver(self):
        ReceiverWindow(Toplevel(self.root), username=self.username, role=self.role)

    def open_inventory(self):
        InventoryWindow(Toplevel(self.root), username=self.username, role=self.role)

    def open_forecasting(self):
        from ui.forecasting import ForecastingWindow
        ForecastingWindow(Toplevel(self.root), username=self.username, role=self.role)
