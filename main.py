from tkinter import *
from ui.login import LoginWindow
from ui.dashboard import DashboardWindow
from ui.portal import UserPortalWindow
from ui.styles import apply_theme, COLORS
import database
from utils.audit_log import log_action

class AppManager:
    def __init__(self, root):
        self.root = root
        database.setup_tables()
        self.current_user = None
        self.show_splash()
        
    def show_splash(self):
        """Shows an animated splash screen before the login window."""
        self.splash_frame = Frame(self.root, bg="#0f172a")
        self.splash_frame.pack(fill=BOTH, expand=1)

        # Center content
        center = Frame(self.splash_frame, bg="#0f172a")
        center.place(relx=0.5, rely=0.5, anchor=CENTER)

        # Blood drop icon and title
        Label(center, text="BLOOD", font=("Segoe UI", 80), bg="#0f172a", fg="white").pack()
        Label(center, text="Blood Bank", font=("Segoe UI", 38, "bold"), bg="#0f172a", fg="#ef4444").pack(pady=(10, 0))
        Label(center, text="Management System", font=("Segoe UI", 16), bg="#0f172a", fg="#94a3b8").pack(pady=(2, 0))

        # Loading bar
        self.progress_frame = Frame(center, bg="#1e293b", height=6, width=360)
        self.progress_frame.pack(pady=(35, 8))
        self.progress_frame.pack_propagate(False)

        self.progress_bar = Frame(self.progress_frame, bg="#ef4444", height=6, width=0)
        self.progress_bar.place(x=0, y=0, relheight=1)

        self.loading_label = Label(center, text="Initializing modules...", font=("Segoe UI", 9), bg="#0f172a", fg="#475569")
        self.loading_label.pack()

        # Version at bottom
        Label(self.splash_frame, text="v2.0", font=("Segoe UI", 9), bg="#0f172a", fg="#334155").pack(side=BOTTOM, pady=15)

        # Animate progress bar
        self.animate_progress(0)

    def animate_progress(self, width):
        if width <= 360:
            self.progress_bar.place(x=0, y=0, relheight=1, width=width)
            self.root.after(6, self.animate_progress, width + 4)
        else:
            self.root.after(200, self.finish_splash)

    def finish_splash(self):
        self.splash_frame.destroy()
        self.show_login()

    def show_login(self):
        self.current_user = None
        for widget in self.root.winfo_children():
            widget.destroy()
        LoginWindow(self.root, self.show_dashboard)
        
    def show_dashboard(self, username="admin"):
        self.current_user = username
        user_role = database.get_user_role(username)
        log_action(username, "LOGIN", f"Role: {user_role}")
        for widget in self.root.winfo_children():
            widget.destroy()
        if user_role in {"donor", "receiver", "member"}:
            UserPortalWindow(self.root, self.show_login, username=username, role=user_role)
        else:
            DashboardWindow(self.root, self.show_login, username=username, role=user_role)

def create_app():
    root = Tk()
    root.title("Modern Blood Bank System")
    root.geometry("1360x768")
    root.minsize(1000, 700)
    
    # Set dark splash background initially 
    root.configure(bg="#0f172a")
    
    apply_theme()
    app = AppManager(root)
    root.mainloop()

if __name__ == "__main__":
    create_app()
