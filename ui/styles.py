from tkinter import ttk

# ========== COLOR THEMES ==========
LIGHT_COLORS = {
    "primary": "#8b0000",
    "primary_light": "#b22222",
    "primary_dark": "#5c0000",
    "accent": "#2563eb",
    "accent_light": "#3b82f6",
    "success": "#16a34a",
    "success_light": "#22c55e",
    "warning": "#d97706",
    "warning_light": "#f59e0b",
    "danger": "#dc2626",
    "danger_light": "#ef4444",
    "background": "#f0f2f5",
    "white": "#ffffff",
    "card": "#ffffff",
    "sidebar_bg": "#1e293b",
    "sidebar_fg": "#e2e8f0",
    "sidebar_hover": "#334155",
    "text_dark": "#1e293b",
    "text_muted": "#64748b",
    "text_light": "#ffffff",
    "border": "#e2e8f0",
    "input_bg": "#f8fafc",
    "input_fg": "#1e293b",
    "input_border": "#cbd5e1",
    "hover": "#f1f5f9",
    "row_alt": "#f8fafc",
}

DARK_COLORS = {
    "primary": "#ef4444",
    "primary_light": "#f87171",
    "primary_dark": "#b91c1c",
    "accent": "#3b82f6",
    "accent_light": "#60a5fa",
    "success": "#22c55e",
    "success_light": "#4ade80",
    "warning": "#f59e0b",
    "warning_light": "#fbbf24",
    "danger": "#ef4444",
    "danger_light": "#f87171",
    "background": "#0f172a",
    "white": "#1e293b",
    "card": "#1e293b",
    "sidebar_bg": "#0f172a",
    "sidebar_fg": "#cbd5e1",
    "sidebar_hover": "#334155",
    "text_dark": "#e2e8f0",
    "text_muted": "#94a3b8",
    "text_light": "#ffffff",
    "border": "#334155",
    "input_bg": "#1e293b",
    "input_fg": "#e2e8f0",
    "input_border": "#475569",
    "hover": "#334155",
    "row_alt": "#1a2332",
}

# Active color scheme (mutable)
COLORS = dict(LIGHT_COLORS)

# Typography
FONTS = {
    "h1": ("Segoe UI", 24, "bold"),
    "h2": ("Segoe UI", 16, "bold"),
    "h3": ("Segoe UI", 13, "bold"),
    "body": ("Segoe UI", 10),
    "body_bold": ("Segoe UI", 10, "bold"),
    "small": ("Segoe UI", 9),
    "small_bold": ("Segoe UI", 9, "bold"),
    "button": ("Segoe UI", 10, "bold"),
    "mono": ("Consolas", 10),
}

# Track dark mode state
_dark_mode = False

def is_dark_mode():
    return _dark_mode

def toggle_dark_mode():
    """Toggles between light and dark themes."""
    global _dark_mode, COLORS
    _dark_mode = not _dark_mode
    source = DARK_COLORS if _dark_mode else LIGHT_COLORS
    COLORS.update(source)
    apply_theme()
    return _dark_mode

def apply_theme():
    """Initializes the ttk.Style configuration for the entire application."""
    style = ttk.Style()
    style.theme_use('clam')
    
    # ===== FRAMES =====
    style.configure("TFrame", background=COLORS["background"])
    style.configure("Card.TFrame", background=COLORS["card"], relief="flat", borderwidth=0)
    style.configure("Sidebar.TFrame", background=COLORS["sidebar_bg"])
    style.configure("Header.TFrame", background=COLORS["primary_dark"])
    style.configure("StatusBar.TFrame", background=COLORS["sidebar_bg"])
    
    # ===== LABELS =====
    style.configure("TLabel", background=COLORS["background"], foreground=COLORS["text_dark"], font=FONTS["body"])
    style.configure("H1.TLabel", background=COLORS["background"], foreground=COLORS["primary"], font=FONTS["h1"])
    style.configure("H2.TLabel", background=COLORS["background"], foreground=COLORS["text_dark"], font=FONTS["h2"])
    style.configure("H3.TLabel", background=COLORS["background"], foreground=COLORS["text_dark"], font=FONTS["h3"])
    style.configure("Muted.TLabel", background=COLORS["background"], foreground=COLORS["text_muted"], font=FONTS["small"])
    
    # Card-based labels (inherit card background)
    style.configure("Card.TLabel", background=COLORS["card"], foreground=COLORS["text_dark"], font=FONTS["body"])
    style.configure("CardH1.TLabel", background=COLORS["card"], foreground=COLORS["primary"], font=FONTS["h1"])
    style.configure("CardH2.TLabel", background=COLORS["card"], foreground=COLORS["text_dark"], font=FONTS["h2"])
    style.configure("CardMuted.TLabel", background=COLORS["card"], foreground=COLORS["text_muted"], font=FONTS["small"])

    # Management screens
    style.configure("Hero.TFrame", background=COLORS["card"], relief="flat")
    style.configure("HeroAccent.TFrame", background=COLORS["primary_dark"], relief="flat")
    style.configure("Section.TFrame", background=COLORS["card"], relief="flat")
    style.configure("Section.TLabel", background=COLORS["card"], foreground=COLORS["text_dark"], font=FONTS["h2"])
    style.configure("SectionSub.TLabel", background=COLORS["card"], foreground=COLORS["text_muted"], font=FONTS["small"])
    style.configure("Field.TLabel", background=COLORS["card"], foreground=COLORS["text_dark"], font=FONTS["body_bold"])
    style.configure("Hint.TLabel", background=COLORS["card"], foreground=COLORS["text_muted"], font=FONTS["small"])
    style.configure("Badge.TLabel", background=COLORS["hover"], foreground=COLORS["text_dark"], font=FONTS["small_bold"], padding=(10, 4))
    style.configure("BadgePrimary.TLabel", background=COLORS["primary"], foreground=COLORS["text_light"], font=FONTS["small_bold"], padding=(10, 4))
    style.configure("Value.TLabel", background=COLORS["card"], foreground=COLORS["primary"], font=("Segoe UI", 20, "bold"))
    
    # Sidebar labels
    style.configure("Sidebar.TLabel", background=COLORS["sidebar_bg"], foreground=COLORS["sidebar_fg"], font=FONTS["body"])
    style.configure("SidebarH2.TLabel", background=COLORS["sidebar_bg"], foreground=COLORS["text_light"], font=FONTS["h3"])
    
    # Status bar labels
    style.configure("StatusBar.TLabel", background=COLORS["sidebar_bg"], foreground=COLORS["sidebar_fg"], font=FONTS["small"])
    
    # Header labels
    style.configure("Header.TLabel", background=COLORS["primary_dark"], foreground=COLORS["text_light"], font=FONTS["body"])
    style.configure("HeaderH1.TLabel", background=COLORS["primary_dark"], foreground=COLORS["text_light"], font=FONTS["h1"])
    
    # ===== BUTTONS =====
    style.configure("Primary.TButton", 
                    background=COLORS["primary"], 
                    foreground=COLORS["text_light"], 
                    font=FONTS["button"], 
                    borderwidth=0, 
                    padding=(12, 8))
    style.map("Primary.TButton", 
              background=[('active', COLORS["primary_light"]), ('disabled', COLORS["border"])])

    style.configure("Success.TButton",
                    background=COLORS["success"],
                    foreground=COLORS["text_light"],
                    font=FONTS["button"],
                    borderwidth=0,
                    padding=(12, 8))
    style.map("Success.TButton",
              background=[('active', COLORS["success_light"]), ('disabled', COLORS["border"])])

    style.configure("Danger.TButton",
                    background=COLORS["danger"],
                    foreground=COLORS["text_light"],
                    font=FONTS["button"],
                    borderwidth=0,
                    padding=(12, 8))
    style.map("Danger.TButton",
              background=[('active', COLORS["danger_light"]), ('disabled', COLORS["border"])])

    style.configure("Accent.TButton",
                    background=COLORS["accent"],
                    foreground=COLORS["text_light"],
                    font=FONTS["button"],
                    borderwidth=0,
                    padding=(12, 8))
    style.map("Accent.TButton",
              background=[('active', COLORS["accent_light"]), ('disabled', COLORS["border"])])

    style.configure("Outline.TButton",
                    background=COLORS["card"],
                    foreground=COLORS["text_dark"],
                    font=FONTS["button"],
                    borderwidth=1,
                    padding=(12, 8))
    style.map("Outline.TButton",
              background=[('active', COLORS["hover"])])

    style.configure("Sidebar.TButton",
                    background=COLORS["sidebar_bg"],
                    foreground=COLORS["sidebar_fg"],
                    font=FONTS["button"],
                    borderwidth=0,
                    padding=(15, 10))
    style.map("Sidebar.TButton",
              background=[('active', COLORS["sidebar_hover"])])

    style.configure("Link.TButton",
                    background=COLORS["background"],
                    foreground=COLORS["primary"],
                    font=("Segoe UI", 10, "underline"),
                    borderwidth=0)
    style.map("Link.TButton",
              foreground=[('active', COLORS["primary_light"])])

    style.configure("CardLink.TButton",
                    background=COLORS["card"],
                    foreground=COLORS["primary"],
                    font=("Segoe UI", 10, "underline"),
                    borderwidth=0)
    style.map("CardLink.TButton",
              foreground=[('active', COLORS["primary_light"])])

    # ===== INPUTS =====
    style.configure("TEntry", padding=8, font=FONTS["body"],
                    fieldbackground=COLORS["input_bg"], foreground=COLORS["input_fg"],
                    bordercolor=COLORS["input_border"], lightcolor=COLORS["input_border"],
                    darkcolor=COLORS["input_border"])
    style.map("TEntry",
              bordercolor=[('focus', COLORS["primary"])],
              lightcolor=[('focus', COLORS["primary"])])
    
    style.configure("TCombobox", padding=8, font=FONTS["body"],
                    fieldbackground=COLORS["input_bg"], foreground=COLORS["input_fg"],
                    bordercolor=COLORS["input_border"])
    style.map("TCombobox",
              bordercolor=[('focus', COLORS["primary"])])
    
    # ===== CHECKBUTTONS =====
    style.configure("TCheckbutton", background=COLORS["background"], foreground=COLORS["text_dark"], font=FONTS["body"])
    style.configure("Card.TCheckbutton", background=COLORS["card"], foreground=COLORS["text_dark"], font=FONTS["body"])
    
    # ===== TREEVIEW =====
    style.configure("Treeview", 
                    background=COLORS["card"],
                    foreground=COLORS["text_dark"],
                    fieldbackground=COLORS["card"],
                    rowheight=34,
                    font=FONTS["body"],
                    borderwidth=0)
    
    style.map("Treeview", 
              background=[('selected', COLORS["primary"])],
              foreground=[('selected', COLORS["text_light"])])
    
    style.configure("Treeview.Heading", 
                    background=COLORS["primary_dark"], 
                    foreground=COLORS["text_light"], 
                    font=FONTS["body_bold"],
                    padding=8,
                    relief="flat")
    style.map("Treeview.Heading",
              background=[('active', COLORS["primary"])])
    
    # ===== SEPARATOR =====
    style.configure("TSeparator", background=COLORS["border"])
    
    # ===== NOTEBOOK =====
    style.configure("TNotebook", background=COLORS["background"])
    style.configure("TNotebook.Tab", background=COLORS["card"], padding=(12, 6), font=FONTS["body"])
    style.map("TNotebook.Tab",
              background=[('selected', COLORS["primary"])],
              foreground=[('selected', COLORS["text_light"])])

    # ===== PROGRESSBAR =====
    style.configure("red.Horizontal.TProgressbar",
                    troughcolor=COLORS["border"],
                    background=COLORS["primary"],
                    thickness=6)
    
    # ===== SCROLLBAR =====
    style.configure("TScrollbar",
                    background=COLORS["card"],
                    troughcolor=COLORS["background"],
                    borderwidth=0,
                    arrowsize=14)
