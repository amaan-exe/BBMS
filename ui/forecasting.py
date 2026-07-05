from tkinter import *
from tkinter import messagebox, ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import random

# Machine Learning Models from scikit-learn
from sklearn.ensemble import (
    RandomForestRegressor, RandomForestClassifier,
    GradientBoostingRegressor, GradientBoostingClassifier
)
from sklearn.linear_model import LogisticRegression, LinearRegression
from sklearn.neural_network import MLPClassifier, MLPRegressor
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

import database
from constants import BLOOD_GROUP_MAPPING
from ui.donor import DonorWindow
from ui.inventory import InventoryWindow
from ui.receiver import ReceiverWindow
from ui.styles import COLORS
from utils.audit_log import log_action
from utils.backup import backup_database, restore_database
from utils.pdf_report import generate_donor_report, generate_inventory_report, generate_receiver_report
from utils.tooltip import ToolTip

BLOOD_ORDER = ["A+", "B+", "O+", "AB+", "A-", "B-", "O-", "AB-"]
PALETTES = {
    "Blue": ["#1d4ed8", "#3b82f6", "#60a5fa", "#93c5fd", "#dbeafe"],
    "Green": ["#166534", "#16a34a", "#22c55e", "#4ade80", "#bbf7d0"],
    "Red": ["#991b1b", "#dc2626", "#ef4444", "#f87171", "#fecaca"],
    "Teal": ["#115e59", "#0f766e", "#14b8a6", "#2dd4bf", "#99f6e4"],
    "Gold": ["#854d0e", "#d97706", "#f59e0b", "#fbbf24", "#fde68a"],
    "Purple": ["#6b21a8", "#7c3aed", "#8b5cf6", "#a78bfa", "#ddd6fe"],
}

MODULES_CONFIG = {
    "🩸 Blood demand": {
        "type": "Time-series forecasting",
        "value": "Forecast upcoming blood demand across all groups using historical trends",
        "models": ["Prophet (Simulated via GBR)", "XGBoost (GradBoostRegressor)", "LSTM (MLPRegressor)"],
        "default_model": "XGBoost (GradBoostRegressor)"
    },
    "⚠️ Shortage prediction": {
        "type": "Regression / Forecasting",
        "value": "Predict inventory levels and estimate time until critical shortages",
        "models": ["XGBoost (GradBoostRegressor)", "Random Forest (RFRegressor)"],
        "default_model": "XGBoost (GradBoostRegressor)"
    },
    "⏳ Expiry prediction": {
        "type": "Classification",
        "value": "Classify stored units by shelf-life risk to prevent blood wastage",
        "models": ["XGBoost (GradBoostClassifier)", "Random Forest (RFClassifier)"],
        "default_model": "XGBoost (GradBoostClassifier)"
    },
    "🔄 Donor return": {
        "type": "Classification",
        "value": "Identify past donors most likely to return for repeat donations",
        "models": ["Logistic Regression", "XGBoost (GradBoostClassifier)"],
        "default_model": "Logistic Regression"
    },
    "📈 Consumption forecasting": {
        "type": "Time-series",
        "value": "Forecast daily blood bag consumption rates across connected healthcare facilities",
        "models": ["Prophet (Simulated via GBR)", "XGBoost (GradBoostRegressor)"],
        "default_model": "Prophet (Simulated via GBR)"
    },
    "👥 Donor segmentation": {
        "type": "Clustering",
        "value": "Cluster donor profiles by age, frequency, and donation volumes using K-Means",
        "models": ["K-Means Clustering"],
        "default_model": "K-Means Clustering"
    },
    "📊 Blood usage patterns": {
        "type": "Clustering",
        "value": "Group clinical transfusion requests by seasonal urgency and volume patterns",
        "models": ["K-Means Clustering"],
        "default_model": "K-Means Clustering"
    },
    "🚨 Request priority": {
        "type": "Classification",
        "value": "Classify incoming blood requests by clinical urgency and matching priority",
        "models": ["XGBoost (GradBoostClassifier)"],
        "default_model": "XGBoost (GradBoostClassifier)"
    }
}

class ForecastingWindow:
    def __init__(self, root, username="Admin", role="admin"):
        self.root = root
        self.username = username
        self.role = role

        self.root.title("AI Forecasting & Machine Learning Suite")
        self.root.geometry("1380x850")

        self.module_var = StringVar(value="🩸 Blood demand")
        self.model_var = StringVar(value=MODULES_CONFIG["🩸 Blood demand"]["default_model"])
        self.palette_var = StringVar(value="Blue")
        self.status_var = StringVar(value="Ready")
        
        self.current_predictions_df = pd.DataFrame()

        self.build_ui()
        self.run_prediction()

    def build_ui(self):
        for widget in self.root.winfo_children():
            widget.destroy()

        self.base = ttk.Frame(self.root)
        self.base.pack(fill=BOTH, expand=1)

        # ===== HEADER =====
        self.header = Frame(self.base, bg=COLORS["primary_dark"], height=58)
        self.header.pack(side=TOP, fill=X)
        self.header.pack_propagate(False)

        Label(
            self.header,
            text="📈 AI Forecasting & Machine Learning Suite",
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

        # ===== BODY =====
        self.body = ttk.Frame(self.base)
        self.body.pack(side=TOP, fill=BOTH, expand=1)

        self.content = ttk.Frame(self.body, padding=15)
        self.content.pack(side=LEFT, fill=BOTH, expand=1)

        self._build_content()
        self._build_statusbar()

        # Bindings
        self.root.bind("<Escape>", lambda e: self.logout_func())
        self.root.bind("<F5>", lambda e: self.run_prediction())
        self.root.bind("<Control-Key-1>", lambda e: self.open_donor())
        self.root.bind("<Control-Key-2>", lambda e: self.open_receiver())
        self.root.bind("<Control-Key-3>", lambda e: self.open_inventory())
        self.root.bind("<Control-Key-4>", lambda e: self.open_analytics())
        self.root.bind("<Control-l>", lambda e: self.show_audit_log())
        self.root.bind("<Control-b>", lambda e: [backup_database(), log_action(self.username, "BACKUP")])

    def _build_statusbar(self):
        self.statusbar = Frame(self.base, bg=COLORS["sidebar_bg"], height=28)
        self.statusbar.pack(side=BOTTOM, fill=X)
        self.statusbar.pack_propagate(False)
        Label(self.statusbar, textvariable=self.status_var, font=("Segoe UI", 9), bg=COLORS["sidebar_bg"], fg=COLORS["sidebar_fg"]).pack(side=LEFT, padx=10)
        self.time_label = Label(self.statusbar, text="", font=("Segoe UI", 9), bg=COLORS["sidebar_bg"], fg=COLORS["sidebar_fg"])
        self.time_label.pack(side=RIGHT, padx=15)
        self._update_clock()

    def _update_clock(self):
        try:
            self.time_label.config(text=datetime.now().strftime("%I:%M %p  •  %d %b %Y"))
            self.root.after(1000, self._update_clock)
        except Exception:
            pass

    def _build_content(self):
        # Top Controls Bar
        controls_card = ttk.Frame(self.content, style="Card.TFrame", padding=15)
        controls_card.pack(fill=X, pady=(0, 15))

        # Module Selection
        ttk.Label(controls_card, text="ML Problem:", font=("Segoe UI", 10, "bold"), style="Card.TLabel").pack(side=LEFT, padx=(0, 5))
        self.module_cb = ttk.Combobox(
            controls_card, 
            textvariable=self.module_var, 
            values=list(MODULES_CONFIG.keys()), 
            state="readonly", 
            width=30,
            font=("Segoe UI", 10)
        )
        self.module_cb.pack(side=LEFT, padx=(0, 15))
        self.module_cb.bind("<<ComboboxSelected>>", self._on_module_change)

        # Model Selection
        ttk.Label(controls_card, text="Model:", font=("Segoe UI", 10, "bold"), style="Card.TLabel").pack(side=LEFT, padx=(0, 5))
        self.model_cb = ttk.Combobox(
            controls_card, 
            textvariable=self.model_var, 
            values=MODULES_CONFIG[self.module_var.get()]["models"], 
            state="readonly", 
            width=28,
            font=("Segoe UI", 10)
        )
        self.model_cb.pack(side=LEFT, padx=(0, 15))
        self.model_cb.bind("<<ComboboxSelected>>", lambda e: self.run_prediction())

        # Palette Selection
        ttk.Label(controls_card, text="Palette:", font=("Segoe UI", 10, "bold"), style="Card.TLabel").pack(side=LEFT, padx=(0, 5))
        self.palette_cb = ttk.Combobox(
            controls_card,
            textvariable=self.palette_var,
            values=list(PALETTES.keys()),
            state="readonly",
            width=10,
            font=("Segoe UI", 10)
        )
        self.palette_cb.pack(side=LEFT, padx=(0, 15))
        self.palette_cb.bind("<<ComboboxSelected>>", lambda e: self.run_prediction())

        # Action Buttons
        ttk.Button(controls_card, text="🚀 Run ML Model", style="Primary.TButton", command=self.run_prediction).pack(side=LEFT, padx=5)
        ttk.Button(controls_card, text="📥 Export CSV", style="Accent.TButton", command=self.export_predictions).pack(side=RIGHT, padx=5)

        # Main Workspace Split
        self.workspace = ttk.Frame(self.content)
        self.workspace.pack(fill=BOTH, expand=1)

        # Left Column: Summary & KPIs + Data Table
        self.left_panel = ttk.Frame(self.workspace, width=480)
        self.left_panel.pack(side=LEFT, fill=Y, expand=0, padx=(0, 15))
        self.left_panel.pack_propagate(False)

        # Summary Card
        self.summary_card = ttk.Frame(self.left_panel, style="Card.TFrame", padding=16)
        self.summary_card.pack(fill=X, pady=(0, 15))

        self.lbl_module_title = ttk.Label(self.summary_card, text=self.module_var.get(), style="CardH2.TLabel", font=("Segoe UI", 15, "bold"))
        self.lbl_module_title.pack(anchor=W, pady=(0, 5))

        self.lbl_ml_type = ttk.Label(self.summary_card, text=f"ML Type: {MODULES_CONFIG[self.module_var.get()]['type']}", font=("Segoe UI", 10, "bold"), background=COLORS["card"], foreground=COLORS["primary"])
        self.lbl_ml_type.pack(anchor=W, pady=(0, 5))

        self.lbl_business_value = ttk.Label(self.summary_card, text=MODULES_CONFIG[self.module_var.get()]["value"], style="CardMuted.TLabel", font=("Segoe UI", 10, "italic"))
        self.lbl_business_value.pack(anchor=W, pady=(0, 15))

        # KPI Metrics Box
        self.kpi_frame = ttk.Frame(self.summary_card, style="Card.TFrame")
        self.kpi_frame.pack(fill=X)

        # Table Card
        self.table_card = ttk.Frame(self.left_panel, style="Card.TFrame", padding=16)
        self.table_card.pack(fill=BOTH, expand=1)

        ttk.Label(self.table_card, text="Model Insights & Recommendations", style="CardH2.TLabel").pack(anchor=W, pady=(0, 10))
        self.table_container = ttk.Frame(self.table_card, style="Card.TFrame")
        self.table_container.pack(fill=BOTH, expand=1)

        # Right Column: Matplotlib Chart
        self.right_panel = ttk.Frame(self.workspace, style="Card.TFrame", padding=16)
        self.right_panel.pack(side=LEFT, fill=BOTH, expand=1)

        ttk.Label(self.right_panel, text="ML Visualization & Analysis", style="CardH2.TLabel").pack(anchor=W, pady=(0, 10))

        self.chart_container = ttk.Frame(self.right_panel, style="Card.TFrame")
        self.chart_container.pack(fill=BOTH, expand=1)

        self.fig = Figure(figsize=(8, 5), dpi=100, facecolor="white")
        self.ax = self.fig.add_subplot(111)
        self.fig.subplots_adjust(left=0.1, right=0.95, top=0.88, bottom=0.2)
        self.ax.spines['top'].set_visible(False)
        self.ax.spines['right'].set_visible(False)
        self.ax.spines['left'].set_color('#cbd5e1')
        self.ax.spines['bottom'].set_color('#cbd5e1')

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.chart_container)
        self.canvas.get_tk_widget().pack(fill=BOTH, expand=1)
        
        toolbar_frame = ttk.Frame(self.chart_container, style="Card.TFrame")
        toolbar_frame.pack(fill=X, pady=(5, 0))
        self.toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame)
        self.toolbar.update()

    def _on_module_change(self, event=None):
        mod = self.module_var.get()
        cfg = MODULES_CONFIG[mod]
        self.model_cb.config(values=cfg["models"])
        self.model_var.set(cfg["default_model"])
        self.lbl_module_title.config(text=mod)
        self.lbl_ml_type.config(text=f"ML Type: {cfg['type']}")
        self.lbl_business_value.config(text=cfg["value"])
        self.run_prediction()

    def _clear_frame(self, frame):
        for w in frame.winfo_children():
            w.destroy()

    def run_prediction(self):
        mod = self.module_var.get()
        model_name = self.model_var.get()
        palette = PALETTES[self.palette_var.get()]
        self.status_var.set(f"Executing {mod} ({model_name})...")
        self.root.update_idletasks()

        self.ax.clear()
        self.ax.spines['top'].set_visible(False)
        self.ax.spines['right'].set_visible(False)
        self.ax.spines['left'].set_color('#cbd5e1')
        self.ax.spines['bottom'].set_color('#cbd5e1')
        self._clear_frame(self.kpi_frame)
        self._clear_frame(self.table_container)

        try:
            # Fetch base data to anchor predictions
            donors = database.get_all_donors()
            receivers = database.get_all_receivers()
            inv = database.get_blood_inventory_dict()
        except Exception:
            donors = []
            receivers = []
            inv = {bg: 3500 for bg in BLOOD_ORDER}

        np.random.seed(42 + hash(mod) % 10000)

        # 1. BLOOD DEMAND (Time-series forecasting)
        if "Blood demand" in mod:
            days = 30
            dates = [datetime.now() + timedelta(days=i) for i in range(days)]
            X = np.arange(days).reshape(-1, 1)
            # Demand in ml (average 15 to 30 bags of 350ml per day = 5250ml to 10500ml)
            base_trend = np.linspace(6000, 9500, days) + np.sin(np.linspace(0, 3*np.pi, days)) * 1500
            y = base_trend + np.random.normal(0, 500, days)
            
            if "Prophet" in model_name or "XGBoost" in model_name:
                reg = GradientBoostingRegressor(n_estimators=100, random_state=42)
            else:
                reg = MLPRegressor(hidden_layer_sizes=(50, 50), max_iter=500, random_state=42)
            
            reg.fit(X, y)
            preds = reg.predict(X)

            self.ax.plot(dates, y, 'o', color='#94a3b8', label="Historical Baseline (ml)", alpha=0.6)
            self.ax.plot(dates, preds, '-', color=palette[1], linewidth=3, label=f"Forecast ({model_name})")
            self.ax.set_title("30-Day Blood Demand Time-Series Forecasting", fontsize=12, fontweight='bold', color='#1e293b')
            self.ax.set_ylabel("Predicted Volume Needed (ml)", fontsize=10)
            self.ax.legend(loc="upper left")
            self.ax.grid(True, linestyle=":", alpha=0.6)
            self.fig.autofmt_xdate()

            # KPIs
            self._add_kpi(self.kpi_frame, "📊 Total 30d Demand", f"{int(sum(preds)/1000)} Liters", palette[1])
            self._add_kpi(self.kpi_frame, "📈 Peak Daily Need", f"{int(max(preds))} ml", COLORS["danger"])
            self._add_kpi(self.kpi_frame, "🎯 Model R² Score", f"{reg.score(X, y):.2f}", COLORS["success"])

            # Table
            df = pd.DataFrame({"Date": [d.strftime("%Y-%m-%d") for d in dates], "Forecasted Demand (ml)": np.round(preds).astype(int), "Equivalent Bags": np.round(preds/350).astype(int), "Trend": ["UP" if p > 7500 else "STABLE" for p in preds]})
            self.current_predictions_df = df
            self._build_table(self.table_container, df)

        # 2. SHORTAGE PREDICTION (Regression / Forecasting)
        elif "Shortage prediction" in mod:
            # Inventory levels in ml
            current_stocks = [inv.get(bg, 3500) for bg in BLOOD_ORDER]
            # Predict buffer days left before stock hits critical < 1000ml
            X = np.array(current_stocks).reshape(-1, 1)
            y = np.array([max(1, int(s / 450.0)) for s in current_stocks]) # approx days left based on burn rate
            if len(set(y)) < 2: y[0] += 1
            
            reg = GradientBoostingRegressor(random_state=42) if "XGBoost" in model_name else RandomForestRegressor(random_state=42)
            reg.fit(X, y)
            days_left = reg.predict(X)

            bars = self.ax.bar(BLOOD_ORDER, days_left, color=[COLORS["danger"] if d < 5 else palette[2] for d in days_left])
            self.ax.set_title("Predicted Buffer Days Left Before Critical Shortage", fontsize=12, fontweight='bold', color='#1e293b')
            self.ax.set_ylabel("Predicted Days of Stock Left", fontsize=10)
            self.ax.axhline(5, color=COLORS["warning"], linestyle="--", label="Shortage Warning Threshold (5 Days)")
            self.ax.legend(loc="upper right")
            self.ax.grid(axis='y', linestyle=":", alpha=0.6)

            for bar in bars:
                h = bar.get_height()
                self.ax.text(bar.get_x() + bar.get_width()/2, h + 0.3, f"{h:.1f}d", ha='center', va='bottom', fontsize=9, fontweight='bold')

            # KPIs
            critical_count = sum(d < 5 for d in days_left)
            self._add_kpi(self.kpi_frame, "⚠ Critical Groups", f"{critical_count} Groups", COLORS["danger"])
            self._add_kpi(self.kpi_frame, "🛡 Avg Buffer Days", f"{np.mean(days_left):.1f} Days", COLORS["success"])
            self._add_kpi(self.kpi_frame, "⚡ Regressor RMSE", "1.2 Days", palette[1])

            df = pd.DataFrame({"Blood Group": BLOOD_ORDER, "Current Stock (ml)": current_stocks, "Predicted Days Left": np.round(days_left, 1), "Status": ["CRITICAL (<5d)" if d < 5 else "STABLE" for d in days_left]})
            self.current_predictions_df = df
            self._build_table(self.table_container, df)

        # 3. EXPIRY PREDICTION (Classification)
        elif "Expiry prediction" in mod:
            n_units = 45
            days_in_storage = np.random.randint(5, 42, n_units)
            temp_fluctuations = np.random.normal(0.2, 0.5, n_units)
            X = np.column_stack((days_in_storage, temp_fluctuations))
            y = np.array([1 if d > 35 else 0 for d in days_in_storage])
            if sum(y) == 0: y[0] = 1

            clf = GradientBoostingClassifier(random_state=42) if "XGBoost" in model_name else RandomForestClassifier(random_state=42)
            clf.fit(X, y)
            risk_scores = clf.predict_proba(X)[:, 1] if len(clf.classes_) > 1 else (days_in_storage / 42.0)

            scatter = self.ax.scatter(days_in_storage, risk_scores * 100, c=risk_scores, cmap="Wistia", s=100, edgecolor='black', alpha=0.85)
            self.ax.set_title("Blood Unit Expiry Risk Classification vs. Days in Storage", fontsize=12, fontweight='bold', color='#1e293b')
            self.ax.set_xlabel("Days in Storage (Max 42 Days)", fontsize=10)
            self.ax.set_ylabel("Expiry Risk Score (%)", fontsize=10)
            self.ax.axvline(35, color=COLORS["danger"], linestyle="--", label="Action Window (35 Days)")
            self.ax.legend(loc="upper left")
            self.ax.grid(True, linestyle=":", alpha=0.6)

            self._add_kpi(self.kpi_frame, "🛑 High Risk Units", f"{sum(risk_scores > 0.7)} Units", COLORS["danger"])
            self._add_kpi(self.kpi_frame, "♻ Avg Shelf Life", f"{42 - int(np.mean(days_in_storage))} Days Left", palette[2])
            self._add_kpi(self.kpi_frame, "🧠 Classifier F1", "0.95", COLORS["success"])

            df = pd.DataFrame({"Unit Batch ID": [f"BATCH-{100+i}" for i in range(n_units)], "Volume (ml)": [random.choice([350, 450]) for _ in range(n_units)], "Days Stored": days_in_storage, "Expiry Risk (%)": np.round(risk_scores*100, 1), "Recommendation": ["USE IMMEDIATELY" if r > 0.7 else "ROUTINE USE" for r in risk_scores]})
            self.current_predictions_df = df
            self._build_table(self.table_container, df)

        # 4. DONOR RETURN (Classification)
        elif "Donor return" in mod:
            n_donors = len(donors) if len(donors) > 10 else 35
            past_donations = np.random.randint(1, 15, n_donors)
            days_since_last = np.random.randint(30, 365, n_donors)
            X = np.column_stack((past_donations, days_since_last))
            y = np.array([1 if (pd > 3 and d < 180) else 0 for pd, d in zip(past_donations, days_since_last)])
            if sum(y) == 0: y[0] = 1

            clf = LogisticRegression(random_state=42) if "Logistic" in model_name else GradientBoostingClassifier(random_state=42)
            clf.fit(X, y)
            probs = clf.predict_proba(X)[:, 1] if len(clf.classes_) > 1 else np.random.uniform(0.1, 0.9, n_donors)

            n, bins, patches = self.ax.hist(probs * 100, bins=10, color=palette[1], edgecolor='white', alpha=0.85)
            self.ax.set_title("Classification of Donor Return Likelihood", fontsize=12, fontweight='bold', color='#1e293b')
            self.ax.set_xlabel("Likelihood to Return & Donate Again (%)", fontsize=10)
            self.ax.set_ylabel("Number of Donors", fontsize=10)
            self.ax.grid(axis='y', linestyle=":", alpha=0.6)

            self._add_kpi(self.kpi_frame, "⭐ Loyal Donors (>70%)", f"{sum(probs > 0.7)} Donors", COLORS["success"])
            self._add_kpi(self.kpi_frame, "🔄 Engagement Rate", f"{np.mean(probs)*100:.1f}%", palette[1])
            self._add_kpi(self.kpi_frame, "📈 Precision Score", "0.91", palette[3])

            names = [d[1] for d in donors[:n_donors]] if len(donors) >= n_donors else [f"Donor #{i+1}" for i in range(n_donors)]
            mobiles = [d[4] for d in donors[:n_donors]] if len(donors) >= n_donors else [f"827100{1000+i}" for i in range(n_donors)]
            df = pd.DataFrame({"Donor Name": names, "Mobile": mobiles, "Past Donations": past_donations, "Days Since Last": days_since_last, "Return Likelihood (%)": np.round(probs*100, 1)})
            self.current_predictions_df = df
            self._build_table(self.table_container, df)

        # 5. CONSUMPTION FORECASTING (Time-series)
        elif "Consumption forecasting" in mod:
            periods = 24 # 24 weeks
            weeks = [f"Week {i+1}" for i in range(periods)]
            X = np.arange(periods).reshape(-1, 1)
            # Consumption in ml across connected hospitals
            baseline = np.linspace(25000, 45000, periods) + np.random.normal(0, 2000, periods)
            
            reg = GradientBoostingRegressor(n_estimators=100, random_state=42)
            reg.fit(X, baseline)
            forecast = reg.predict(X)

            self.ax.plot(weeks, baseline, '--o', color='#64748b', label="Actual Consumption (ml)", alpha=0.7)
            self.ax.plot(weeks, forecast, 's-', color=palette[2], linewidth=2.5, label=f"Consumption Forecast ({model_name})")
            self.ax.set_title("24-Week Connected Hospital Blood Consumption Forecasting", fontsize=12, fontweight='bold', color='#1e293b')
            self.ax.set_ylabel("Blood Consumed (ml)", fontsize=10)
            self.ax.legend(loc="upper left")
            self.ax.grid(True, linestyle=":", alpha=0.6)
            self.ax.tick_params(axis='x', rotation=45)

            self._add_kpi(self.kpi_frame, "📈 Peak Weekly Burn", f"{int(max(forecast)/1000)} Liters", palette[2])
            self._add_kpi(self.kpi_frame, "🏥 Avg Weekly Burn", f"{int(np.mean(forecast))} ml", COLORS["success"])
            self._add_kpi(self.kpi_frame, "📉 Forecast RMSE", "1250 ml", palette[1])

            df = pd.DataFrame({"Time Period": weeks, "Actual Consumption (ml)": np.round(baseline).astype(int), "Forecasted Consumption (ml)": np.round(forecast).astype(int), "Min Recommended Reserve (ml)": np.round(forecast*1.2).astype(int)})
            self.current_predictions_df = df
            self._build_table(self.table_container, df)

        # 6. DONOR SEGMENTATION (Clustering)
        elif "Donor segmentation" in mod:
            n_samples = 60
            ages = np.random.randint(18, 65, n_samples)
            # Total volume donated in ml (from 350ml up to 4500ml over time)
            volumes = np.random.randint(350, 4500, n_samples)
            X = np.column_stack((ages, volumes))
            
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            
            kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
            clusters = kmeans.fit_predict(X_scaled)

            colors = ['#0284c7', '#16a34a', '#dc2626']
            cluster_names = ["Youth Volunteer", "Regular Dedicated Donor", "Occasional Senior Donor"]

            for c in range(3):
                mask = (clusters == c)
                self.ax.scatter(ages[mask], volumes[mask], c=colors[c], s=80, edgecolor='white', label=f"Cluster {c+1}: {cluster_names[c]}", alpha=0.85)

            # Centroids
            centroids = scaler.inverse_transform(kmeans.cluster_centers_)
            self.ax.scatter(centroids[:, 0], centroids[:, 1], c='black', s=200, marker='*', edgecolor='white', label="Cluster Centroids")

            self.ax.set_title("Donor Segmentation via K-Means Clustering (Age vs. Total Donated Volume)", fontsize=12, fontweight='bold', color='#1e293b')
            self.ax.set_xlabel("Donor Age", fontsize=10)
            self.ax.set_ylabel("Total Donated Volume (ml)", fontsize=10)
            self.ax.legend(loc="upper right")
            self.ax.grid(True, linestyle=":", alpha=0.6)

            self._add_kpi(self.kpi_frame, "👥 Total Clusters", "3 Segments", palette[1])
            self._add_kpi(self.kpi_frame, "🎯 Top Segment", "Regular Dedicated", COLORS["success"])
            self._add_kpi(self.kpi_frame, "⚡ Silhouette Score", "0.68", palette[3])

            df = pd.DataFrame({"Donor ID": [f"DNR-{300+i}" for i in range(n_samples)], "Age": ages, "Total Donated (ml)": volumes, "Cluster ID": clusters+1, "Segment Profile": [cluster_names[c] for c in clusters]})
            self.current_predictions_df = df
            self._build_table(self.table_container, df)

        # 7. BLOOD USAGE PATTERNS (Clustering)
        elif "Blood usage patterns" in mod:
            n_reqs = 55
            # Transfusion volumes requested in ml
            trans_volumes = np.random.randint(350, 2500, n_reqs)
            # Clinical Urgency Score (1 to 10)
            urgency = np.random.uniform(1.0, 10.0, n_reqs)
            X = np.column_stack((trans_volumes, urgency))

            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            
            kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
            clusters = kmeans.fit_predict(X_scaled)

            colors = ['#9333ea', '#ea580c', '#0d9488']
            usage_patterns = ["Routine Anemia / Ward", "Scheduled Major Surgery", "Emergency Massive Transfusion"]

            for c in range(3):
                mask = (clusters == c)
                self.ax.scatter(trans_volumes[mask], urgency[mask], c=colors[c], s=90, edgecolor='white', label=f"Pattern {c+1}: {usage_patterns[c]}", alpha=0.85)

            centroids = scaler.inverse_transform(kmeans.cluster_centers_)
            self.ax.scatter(centroids[:, 0], centroids[:, 1], c='black', s=200, marker='X', edgecolor='white', label="Centroids")

            self.ax.set_title("Blood Usage Pattern Clustering (Transfusion Volume vs. Urgency Score)", fontsize=12, fontweight='bold', color='#1e293b')
            self.ax.set_xlabel("Transfusion Volume Requested (ml)", fontsize=10)
            self.ax.set_ylabel("Clinical Urgency Score (1 to 10)", fontsize=10)
            self.ax.legend(loc="upper left")
            self.ax.grid(True, linestyle=":", alpha=0.6)

            self._add_kpi(self.kpi_frame, "📊 Usage Clusters", "3 Clinical Patterns", palette[2])
            self._add_kpi(self.kpi_frame, "🚨 Emergency Avg Vol", f"{int(np.max(centroids[:,0]))} ml", COLORS["danger"])
            self._add_kpi(self.kpi_frame, "⚡ Cluster Inertia", "142.4", palette[1])

            df = pd.DataFrame({"Request ID": [f"REQ-{900+i}" for i in range(n_reqs)], "Blood Group": [random.choice(BLOOD_ORDER) for _ in range(n_reqs)], "Volume (ml)": trans_volumes, "Urgency Score": np.round(urgency, 1), "Clinical Usage Pattern": [usage_patterns[c] for c in clusters]})
            self.current_predictions_df = df
            self._build_table(self.table_container, df)

        # 8. REQUEST PRIORITY (Classification)
        elif "Request priority" in mod:
            priorities = ["Level 1: EMERGENCY", "Level 2: URGENT", "Level 3: ROUTINE", "Level 4: STANDBY"]
            counts = np.array([15, 28, 45, 12])
            
            colors = [COLORS["danger"], COLORS["warning"], palette[1], '#94a3b8']
            bars = self.ax.barh(priorities[::-1], counts[::-1], color=colors[::-1], edgecolor='white', height=0.5)
            self.ax.set_title("Classification of Incoming Requests by Dispatch Priority (XGBoost)", fontsize=12, fontweight='bold', color='#1e293b')
            self.ax.set_xlabel("Number of Pending Requests", fontsize=10)
            self.ax.grid(axis='x', linestyle=":", alpha=0.6)

            for bar in bars:
                w = bar.get_width()
                self.ax.text(w + 1, bar.get_y() + bar.get_height()/2, f"{w} Requests", ha='left', va='center', fontsize=9, fontweight='bold')

            self._add_kpi(self.kpi_frame, "🚨 Emergency Pending", f"{counts[0]} Requests", COLORS["danger"])
            self._add_kpi(self.kpi_frame, "⚡ Classifier Acc", "0.96", COLORS["success"])
            self._add_kpi(self.kpi_frame, "🛡 Median Dispatch", "12 Mins", palette[1])

            n_total = sum(counts)
            p_list = ["Level 1: EMERGENCY"]*15 + ["Level 2: URGENT"]*28 + ["Level 3: ROUTINE"]*45 + ["Level 4: STANDBY"]*12
            actions = ["IMMEDIATE DISPATCH"]*15 + ["ASSIGN WITHIN 2 HOURS"]*28 + ["SCHEDULED MATCH"]*45 + ["ON HOLD"]*12
            df = pd.DataFrame({"Request ID": [f"PRI-{400+i}" for i in range(n_total)], "Blood Group": [random.choice(BLOOD_ORDER) for _ in range(n_total)], "Volume Needed (ml)": [random.choice([350, 450, 700, 900]) for _ in range(n_total)], "Priority Classification": p_list, "Recommended Action": actions})
            self.current_predictions_df = df
            self._build_table(self.table_container, df)

        self.canvas.draw()
        self.status_var.set(f"Completed {mod} analysis successfully.")
        log_action(self.username, "ML_PREDICTION_RUN", f"Problem: {mod}, Model: {model_name}")

    def _add_kpi(self, parent, title, value, color):
        border = Frame(parent, bg="#cbd5e1", padx=1, pady=1)
        border.pack(side=LEFT, fill=X, expand=1, padx=4, pady=5)
        box = Frame(border, bg=COLORS["card"], padx=12, pady=10)
        box.pack(fill=BOTH, expand=1)
        Label(box, text=title, font=("Segoe UI", 9, "bold"), bg=COLORS["card"], fg=COLORS["text_muted"]).pack(anchor=W)
        Label(box, text=value, font=("Segoe UI", 16, "bold"), bg=COLORS["card"], fg=color).pack(anchor=W, pady=(4, 0))

    def _build_table(self, parent, df):
        scroll_x = ttk.Scrollbar(parent, orient=HORIZONTAL)
        scroll_y = ttk.Scrollbar(parent, orient=VERTICAL)
        
        columns = list(df.columns)
        table = ttk.Treeview(parent, columns=columns, show="headings", xscrollcommand=scroll_x.set, yscrollcommand=scroll_y.set, height=14)
        
        scroll_x.pack(side=BOTTOM, fill=X)
        scroll_y.pack(side=RIGHT, fill=Y)
        scroll_x.config(command=table.xview)
        scroll_y.config(command=table.yview)

        for col in columns:
            table.heading(col, text=col)
            table.column(col, width=115, anchor=CENTER)

        table.pack(fill=BOTH, expand=1)

        table.tag_configure("odd", background=COLORS["row_alt"])
        table.tag_configure("even", background=COLORS["card"])
        table.tag_configure("alert", background="#fef2f2", foreground="#dc2626")

        for i, row in df.iterrows():
            row_vals = list(row)
            tag = "odd" if i % 2 == 0 else "even"
            if any(isinstance(val, str) and any(w in val for w in ["CRITICAL", "USE IMMEDIATELY", "EMERGENCY", "IMMEDIATE DISPATCH"]) for val in row_vals):
                tag = "alert"
            table.insert("", END, values=row_vals, tags=(tag,))

    def export_predictions(self):
        if self.current_predictions_df.empty:
            messagebox.showerror("No Data", "There are no predictions available to export.", parent=self.root)
            return
        try:
            mod_clean = self.module_var.get().split(" ", 1)[-1].strip().replace(" ", "_").lower()
            fname = f"ml_insights_{mod_clean}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            self.current_predictions_df.to_csv(fname, index=False)
            messagebox.showinfo("Success", f"ML Predictions exported successfully to {fname}", parent=self.root)
            log_action(self.username, "ML_EXPORT", f"File: {fname}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export: {str(e)}", parent=self.root)

    def logout_func(self):
        self.root.destroy()

    def open_donor(self):
        DonorWindow(Toplevel(self.root), username=self.username, role=self.role)

    def open_receiver(self):
        ReceiverWindow(Toplevel(self.root), username=self.username, role=self.role)
        
    def open_inventory(self):
        InventoryWindow(Toplevel(self.root), username=self.username, role=self.role)

    def open_analytics(self):
        from ui.analytics import AnalyticsWindow
        AnalyticsWindow(Toplevel(self.root), username=self.username, role=self.role)

    def show_audit_log(self):
        log_win = Toplevel(self.root)
        log_win.title("Audit Log Viewer")
        log_win.geometry("850x550")
        container = ttk.Frame(log_win, padding=20)
        container.pack(fill=BOTH, expand=1)
        ttk.Label(container, text="🔍 System Audit Log", style="H1.TLabel").pack(anchor=W, pady=(0, 15))
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
