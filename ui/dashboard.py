from tkinter import *
from tkinter import messagebox
from tkinter import ttk
from PIL import Image, ImageTk
from ui.donor import DonorWindow
from ui.receiver import ReceiverWindow
from ui.inventory import InventoryWindow
from ui.analytics import AnalyticsWindow
from ui.styles import toggle_dark_mode, is_dark_mode, COLORS, FONTS
import database
from constants import BLOOD_EXPIRY_DAYS
from utils.audit_log import log_action
from utils.backup import backup_database, restore_database
from utils.tooltip import ToolTip
from utils.pdf_report import generate_donor_report, generate_receiver_report, generate_inventory_report
from datetime import datetime


class DashboardWindow:
    def __init__(self, root, on_logout, username="admin", role="admin"):
        self.root = root
        self.on_logout = on_logout
        self.username = username
        self.role = role
        
        self.build_ui()

    def build_ui(self):
        # Clear existing widgets
        for widget in self.root.winfo_children():
            widget.destroy()

        self.base_frame = ttk.Frame(self.root)
        self.base_frame.pack(fill=BOTH, expand=1)

        # ===== HEADER BAR =====
        self.header = Frame(self.base_frame, bg=COLORS["primary_dark"], height=56)
        self.header.pack(side=TOP, fill=X)
        self.header.pack_propagate(False)

        Label(self.header, text="🩸 Blood Bank", font=("Segoe UI", 18, "bold"),
              bg=COLORS["primary_dark"], fg="white").pack(side=LEFT, padx=20)
        
        # Right controls
        controls = Frame(self.header, bg=COLORS["primary_dark"])
        controls.pack(side=RIGHT, padx=15)
        
        role_display = self.role.upper() if self.role else "STAFF"
        Label(controls, text=f"👤 {self.username}",
              font=("Segoe UI", 10), bg=COLORS["primary_dark"], fg="#ffcccc").pack(side=LEFT, padx=(0, 5))
        Label(controls, text=f"({role_display})",
              font=("Segoe UI", 9), bg=COLORS["primary_dark"], fg="#ff9999").pack(side=LEFT, padx=(0, 15))
        
        mode_text = "☀ Light" if is_dark_mode() else "🌙 Dark"
        self.dark_btn = ttk.Button(controls, text=mode_text, style="Outline.TButton", command=self.toggle_theme)
        self.dark_btn.pack(side=LEFT, padx=3)
        
        logout_btn = ttk.Button(controls, text="↪ Log Out", style="Outline.TButton", command=self.logout_func)
        logout_btn.pack(side=LEFT, padx=3)

        # ===== BODY =====
        self.body = ttk.Frame(self.base_frame)
        self.body.pack(side=TOP, fill=BOTH, expand=1)

        # ===== SIDEBAR =====
        self.sidebar = Frame(self.body, bg=COLORS["sidebar_bg"], width=240)
        self.sidebar.pack(side=LEFT, fill=Y)
        self.sidebar.pack_propagate(False)

        # Nav section
        Label(self.sidebar, text="NAVIGATION", font=("Segoe UI", 8, "bold"),
              bg=COLORS["sidebar_bg"], fg=COLORS["text_muted"]).pack(anchor=W, padx=18, pady=(18, 8))
        
        # Donations
        self._sidebar_btn("➕  Add Donor", lambda: DonorWindow(Toplevel(self.root), username=self.username, role=self.role, mode='add', on_db_change=self.refresh_dashboard), "Ctrl+1")
        self._sidebar_btn("📋  View Donors", lambda: DonorWindow(Toplevel(self.root), username=self.username, role=self.role, mode='view', on_db_change=self.refresh_dashboard), "Ctrl+2")
        # Receivers
        self._sidebar_btn("➕  Add Receiver", lambda: ReceiverWindow(Toplevel(self.root), username=self.username, role=self.role, mode='add', on_db_change=self.refresh_dashboard), "Ctrl+3")
        self._sidebar_btn("📋  View Receivers", lambda: ReceiverWindow(Toplevel(self.root), username=self.username, role=self.role, mode='view', on_db_change=self.refresh_dashboard), "Ctrl+4")
        # Inventory
        self._sidebar_btn("📦  Blood Inventory", self.open_inventory, "Ctrl+5")

        # Reports section
        Frame(self.sidebar, bg=COLORS["sidebar_hover"], height=1).pack(fill=X, padx=15, pady=12)
        Label(self.sidebar, text="REPORTS", font=("Segoe UI", 8, "bold"),
              bg=COLORS["sidebar_bg"], fg=COLORS["text_muted"]).pack(anchor=W, padx=18, pady=(0, 8))
        
        self._sidebar_btn("📄  Donor Report", generate_donor_report)
        self._sidebar_btn("📄  Receiver Report", generate_receiver_report)
        self._sidebar_btn("📄  Inventory Report", generate_inventory_report)

        # Admin section
        if self.role == "admin":
            Frame(self.sidebar, bg=COLORS["sidebar_hover"], height=1).pack(fill=X, padx=15, pady=12)
            Label(self.sidebar, text="ADMIN", font=("Segoe UI", 8, "bold"),
                  bg=COLORS["sidebar_bg"], fg=COLORS["text_muted"]).pack(anchor=W, padx=18, pady=(0, 8))
            
            self._sidebar_btn("📊  Analytics", self.open_analytics, "Ctrl+6")
            self._sidebar_btn("📈  Forecasting & AI", self.open_forecasting, "Ctrl+7")
            self._sidebar_btn("🔍  Audit Log", self.show_audit_log, "Ctrl+L")
            self._sidebar_btn("💾  Backup DB", lambda: [backup_database(), log_action(self.username, "BACKUP")], "Ctrl+B")
            self._sidebar_btn("🔄  Restore DB", lambda: [restore_database(), log_action(self.username, "RESTORE")])

        # ===== MAIN CONTENT =====
        self.content = ttk.Frame(self.body)
        self.content.pack(side=LEFT, fill=BOTH, expand=1, padx=0, pady=0)

        self.canvas = Canvas(self.content, highlightthickness=0, bg=COLORS["background"])
        self.scrollbar = ttk.Scrollbar(self.content, orient=VERTICAL, command=self.canvas.yview)
        self.scroll_frame = ttk.Frame(self.canvas)
        
        self.scroll_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.scrollbar.pack(side=RIGHT, fill=Y)
        self.canvas.pack(side=LEFT, fill=BOTH, expand=1)
        self.canvas.bind("<MouseWheel>", lambda e: self.canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        # Dashboard sections
        self.build_stats_cards()
        self.build_alerts_section()
        self.build_expiry_section()

        # ===== STATUS BAR =====
        self.statusbar = Frame(self.base_frame, bg=COLORS["sidebar_bg"], height=28)
        self.statusbar.pack(side=BOTTOM, fill=X)
        self.statusbar.pack_propagate(False)
        
        Label(self.statusbar, text=f"  👤 Logged in as {self.username} ({self.role})",
              font=("Segoe UI", 9), bg=COLORS["sidebar_bg"], fg=COLORS["sidebar_fg"]).pack(side=LEFT)
        
        self.time_label = Label(self.statusbar, text="", font=("Segoe UI", 9),
                                bg=COLORS["sidebar_bg"], fg=COLORS["sidebar_fg"])
        self.time_label.pack(side=RIGHT, padx=15)
        self._update_clock()
        
        # Keyboard shortcuts
        self.root.bind("<Control-Key-1>", lambda e: DonorWindow(Toplevel(self.root), username=self.username, role=self.role, mode='add', on_db_change=self.refresh_dashboard))
        self.root.bind("<Control-Key-2>", lambda e: DonorWindow(Toplevel(self.root), username=self.username, role=self.role, mode='view', on_db_change=self.refresh_dashboard))
        self.root.bind("<Control-Key-3>", lambda e: ReceiverWindow(Toplevel(self.root), username=self.username, role=self.role, mode='add', on_db_change=self.refresh_dashboard))
        self.root.bind("<Control-Key-4>", lambda e: ReceiverWindow(Toplevel(self.root), username=self.username, role=self.role, mode='view', on_db_change=self.refresh_dashboard))
        self.root.bind("<Control-Key-5>", lambda e: self.open_inventory())
        if self.role == "admin":
            self.root.bind("<Control-Key-6>", lambda e: self.open_analytics())
            self.root.bind("<Control-Key-7>", lambda e: self.open_forecasting())
        self.root.bind("<Escape>", lambda e: self.logout_func())
        if self.role == "admin":
            self.root.bind("<Control-l>", lambda e: self.show_audit_log())
            self.root.bind("<Control-b>", lambda e: [backup_database(), log_action(self.username, "BACKUP")])

    def _sidebar_btn(self, text, command, shortcut=None):
        """Creates a styled sidebar button."""
        btn = Button(self.sidebar, text=text, font=("Segoe UI", 10), anchor=W,
                     bg=COLORS["sidebar_bg"], fg=COLORS["sidebar_fg"],
                     activebackground=COLORS["sidebar_hover"], activeforeground="white",
                     relief=FLAT, padx=18, pady=8, cursor="hand2", command=command)
        btn.pack(fill=X)
        btn.bind("<Enter>", lambda e: btn.config(bg=COLORS["sidebar_hover"]))
        btn.bind("<Leave>", lambda e: btn.config(bg=COLORS["sidebar_bg"]))
        if shortcut:
            ToolTip(btn, shortcut)

    def _update_clock(self):
        """Updates the status bar clock every second."""
        try:
            now = datetime.now().strftime("%I:%M %p  •  %d %b %Y")
            self.time_label.config(text=now)
            self.root.after(1000, self._update_clock)
        except Exception:
            pass  # Window may have been destroyed

    def toggle_theme(self):
        toggle_dark_mode()
        self.build_ui()

    def refresh_dashboard(self):
        try:
            for widget in self.scroll_frame.winfo_children():
                widget.destroy()
            self.build_stats_cards()
            self.build_alerts_section()
            self.build_expiry_section()
        except Exception:
            pass

    # ===== STATS CARDS =====
    def build_stats_cards(self):
        stats_frame = ttk.Frame(self.scroll_frame, padding=(20, 20, 20, 5))
        stats_frame.pack(fill=X)

        ttk.Label(stats_frame, text="Dashboard Overview", style="H2.TLabel").pack(anchor=W, pady=(0, 15))

        cards_row = ttk.Frame(stats_frame)
        cards_row.pack(fill=X)
        cards_row.columnconfigure(0, weight=1)
        cards_row.columnconfigure(1, weight=1)
        cards_row.columnconfigure(2, weight=1)

        donor_count = database.get_total_donors_count()
        receiver_count = database.get_total_receivers_count()
        inv = database.get_blood_inventory_dict()
        total_units = sum(inv.values()) if inv else 0

        self._create_stat_card(cards_row, "🩸", "Total Donors", str(donor_count), COLORS["danger"], 0)
        self._create_stat_card(cards_row, "🏥", "Total Receivers", str(receiver_count), COLORS["accent"], 1)
        self._create_stat_card(cards_row, "📦", "Blood Units", str(total_units), COLORS["success"], 2)

    def _create_stat_card(self, parent, icon, title, value, color, col):
        card = ttk.Frame(parent, style="Card.TFrame", padding=20)
        card.grid(row=0, column=col, padx=8, sticky=NSEW)
        
        # Icon + value row
        top = ttk.Frame(card, style="Card.TFrame")
        top.pack(fill=X)
        Label(top, text=icon, font=("Segoe UI", 28), bg=COLORS["card"], fg=color).pack(side=LEFT)
        Label(top, text=value, font=("Segoe UI", 32, "bold"), bg=COLORS["card"], fg=color).pack(side=RIGHT)
        
        ttk.Label(card, text=title, style="CardMuted.TLabel", font=("Segoe UI", 11)).pack(anchor=W, pady=(8, 0))

    # ===== LOW INVENTORY ALERTS =====
    def build_alerts_section(self):
        alerts = database.get_low_inventory_alerts()
        if not alerts:
            return

        alert_frame = ttk.Frame(self.scroll_frame, padding=(20, 10, 20, 5))
        alert_frame.pack(fill=X)

        ttk.Label(alert_frame, text="⚠  Low Inventory Alerts", font=("Segoe UI", 14, "bold"), foreground=COLORS["danger"]).pack(anchor=W, pady=(0, 10))

        for blood_type, amount in alerts:
            row = Frame(alert_frame, bg="#fef2f2", padx=15, pady=10)
            row.pack(fill=X, pady=2)
            Label(row, text=f"🔴 {blood_type}", font=("Segoe UI", 11, "bold"), bg="#fef2f2", fg=COLORS["danger"]).pack(side=LEFT)
            Label(row, text=f"Only {amount} unit(s) remaining", font=("Segoe UI", 10), bg="#fef2f2", fg="#7f1d1d").pack(side=LEFT, padx=15)

    # ===== EXPIRY TRACKING =====
    def build_expiry_section(self):
        expiring = database.get_expiring_donations(BLOOD_EXPIRY_DAYS)
        
        expiry_frame = ttk.Frame(self.scroll_frame, padding=(20, 10, 20, 15))
        expiry_frame.pack(fill=X)

        ttk.Label(expiry_frame, text="⏳  Expiring Blood Units (Next 7 Days)", style="H2.TLabel").pack(anchor=W, pady=(0, 10))

        if not expiring:
            ttk.Label(expiry_frame, text="✅  No blood units are expiring within the next 7 days.", 
                      font=("Segoe UI", 11), foreground=COLORS["success"]).pack(anchor=W)
            return

        for item in expiring:
            row = ttk.Frame(expiry_frame, style="Card.TFrame", padding=12)
            row.pack(fill=X, pady=2)
            days_text = f"{item['days_left']} day(s) left"
            color = COLORS["danger"] if item['days_left'] <= 2 else COLORS["warning"]
            ttk.Label(row, text=f"🩸 {item['blood_type']}", style="Card.TLabel", font=("Segoe UI", 11, "bold")).pack(side=LEFT)
            ttk.Label(row, text=f"{item['units']}ml from {item['name']} — Donated: {item['donation_date']} — Expires: {item['expiry_date']}", style="Card.TLabel", font=("Segoe UI", 9)).pack(side=LEFT, padx=10)
            Label(row, text=days_text, font=("Segoe UI", 10, "bold"), bg=COLORS["card"], fg=color).pack(side=RIGHT)

    # ===== AUDIT LOG VIEWER =====
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

        log_text = Text(text_frame, wrap=WORD, yscrollcommand=scrollbar.set, 
                        font=("Consolas", 10), bg="#0f172a", fg="#4ade80", 
                        insertbackground="white", padx=15, pady=10, relief=FLAT)
        log_text.pack(fill=BOTH, expand=1)
        scrollbar.config(command=log_text.yview)

        try:
            with open("audit.log", "r", encoding="utf-8") as f:
                content = f.read()
                log_text.insert(END, content if content else "No audit events recorded yet.")
        except FileNotFoundError:
            log_text.insert(END, "No audit log file found.")
        log_text.config(state=DISABLED)

    # ===== NAVIGATION =====
    def logout_func(self):
        if messagebox.askyesno("Logout", "Do you want to logout?", parent=self.root):
            log_action(self.username, "LOGOUT")
            self.on_logout()

    def open_donor(self):
        DonorWindow(Toplevel(self.root), username=self.username, role=self.role, on_db_change=self.refresh_dashboard)

    def open_receiver(self):
        ReceiverWindow(Toplevel(self.root), username=self.username, role=self.role, on_db_change=self.refresh_dashboard)
        
    def open_inventory(self):
        InventoryWindow(Toplevel(self.root), username=self.username, role=self.role)

    def open_analytics(self):
        if self.role != "admin":
            messagebox.showerror("Access Denied", "Analytics is available to admin users only.", parent=self.root)
            return
        AnalyticsWindow(Toplevel(self.root), username=self.username, role=self.role)

    def open_forecasting(self):
        if self.role != "admin":
            messagebox.showerror("Access Denied", "Forecasting is available to admin users only.", parent=self.root)
            return
        from ui.forecasting import ForecastingWindow
        ForecastingWindow(Toplevel(self.root), username=self.username, role=self.role)
