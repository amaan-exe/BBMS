from tkinter import *
from tkinter import messagebox
from tkinter import ttk
from PIL import Image, ImageTk
import sqlite3
import database
import json
import os
import re

class LoginWindow:
    def __init__(self, root, on_success):
        self.root = root
        self.on_success = on_success
        
        # Full background container
        self.container = ttk.Frame(root)
        self.container.pack(expand=True, fill=BOTH)

        # Login Card (wider, more padding)
        self.card = ttk.Frame(self.container, style="Card.TFrame")
        self.card.place(relx=0.5, rely=0.5, anchor=CENTER, width=420)

        # Colored Header Band
        from ui.styles import COLORS
        header = Frame(self.card, bg=COLORS["primary_dark"], height=90)
        header.pack(fill=X)
        header.pack_propagate(False)
        Label(header, text="🩸 Blood Bank", font=("Segoe UI", 22, "bold"), bg=COLORS["primary_dark"], fg="white").pack(pady=(18, 0))
        Label(header, text="Sign in to your account", font=("Segoe UI", 10), bg=COLORS["primary_dark"], fg="#ffcccc").pack()

        # Form area
        form = ttk.Frame(self.card, style="Card.TFrame", padding=(30, 25, 30, 20))
        form.pack(fill=X)

        # Username Field with icon
        user_label = ttk.Frame(form, style="Card.TFrame")
        user_label.pack(fill=X)
        ttk.Label(user_label, text="👤  Username", style="Card.TLabel", font=("Segoe UI", 10, "bold")).pack(side=LEFT)
        self.txtuser = ttk.Entry(form, width=40, font=("Segoe UI", 11))
        self.txtuser.pack(fill=X, pady=(4, 15))

        # Password Field with icon
        pass_label = ttk.Frame(form, style="Card.TFrame")
        pass_label.pack(fill=X)
        ttk.Label(pass_label, text="🔒  Password", style="Card.TLabel", font=("Segoe UI", 10, "bold")).pack(side=LEFT)
        self.txtpass = ttk.Entry(form, width=40, show="*", font=("Segoe UI", 11))
        self.txtpass.pack(fill=X, pady=(4, 12))

        # Options Row
        options_frame = ttk.Frame(form, style="Card.TFrame")
        options_frame.pack(fill=X, pady=(0, 20))
        
        self.remember_var = BooleanVar()
        self.chk_remember = ttk.Checkbutton(options_frame, text="Remember Me", variable=self.remember_var, style="Card.TCheckbutton")
        self.chk_remember.pack(side=LEFT)

        self.show_pass_var = BooleanVar()
        self.chk_show = ttk.Checkbutton(options_frame, text="Show", variable=self.show_pass_var, style="Card.TCheckbutton", command=self.toggle_password)
        self.chk_show.pack(side=RIGHT)

        # Login Button
        self.login_btn = ttk.Button(form, text="Log In →", style="Primary.TButton", command=self.login)
        self.login_btn.pack(fill=X, pady=(0, 15))

        # Footer Links
        footer_frame = ttk.Frame(form, style="Card.TFrame")
        footer_frame.pack(fill=X)
        ttk.Button(footer_frame, text="Forgot Password?", style="CardLink.TButton", command=self.open_forgot_password).pack(side=LEFT)
        ttk.Button(footer_frame, text="Create Account", style="CardLink.TButton", command=self.open_register).pack(side=RIGHT)

        # Version label
        ttk.Label(self.card, text="v2.0", style="CardMuted.TLabel").pack(pady=(5, 10))

        self.load_remembered_user()

        # Keyboard bindings
        self._return_bind_id = self.root.bind("<Return>", lambda e: self.login())
        self.txtuser.bind("<Return>", lambda e: self.txtpass.focus_set())
        self.txtpass.bind("<Return>", lambda e: self.login())
        self.txtuser.focus_set()

    def toggle_password(self):
        if self.show_pass_var.get():
            self.txtpass.config(show="")
        else:
            self.txtpass.config(show="*")

    def load_remembered_user(self):
        try:
            if os.path.exists("config.json"):
                with open("config.json", "r") as f:
                    data = json.load(f)
                    if "remembered_username" in data:
                        self.txtuser.insert(0, data["remembered_username"])
                        self.remember_var.set(True)
        except Exception:
            pass

    def save_remembered_user(self, username):
        try:
            data = {}
            if os.path.exists("config.json"):
                with open("config.json", "r") as f:
                    data = json.load(f)
            
            if self.remember_var.get():
                data["remembered_username"] = username
            else:
                data.pop("remembered_username", None)
                
            with open("config.json", "w") as f:
                json.dump(data, f)
        except Exception:
            pass

    def login(self):
        # Guard against destroyed widgets (e.g. Enter pressed after transition)
        try:
            username = self.txtuser.get()
            password = self.txtpass.get()
        except Exception:
            return
        
        if not username or not password:
            messagebox.showerror("Error", "All fields required", parent=self.root)
            return

        row = database.login_user(username, password)
        if row is None:
            messagebox.showerror("Error", "Invalid Username or Password", parent=self.root)
        else:
            self.save_remembered_user(username)
            # Properly unbind login keyboard shortcuts before transitioning
            if hasattr(self, '_return_bind_id'):
                self.root.unbind("<Return>", self._return_bind_id)
            for widget in self.root.winfo_children():
                widget.destroy()
            self.on_success(username)

    def open_register(self):
        reg_win = Toplevel(self.root)
        RegisterWindow(reg_win)

    def open_forgot_password(self):
        username = self.txtuser.get()
        if not username:
            messagebox.showerror("Error", "Please enter your username first to reset your password", parent=self.root)
            return

        row = database.get_user_by_username(username)
        if row is None:
            messagebox.showerror("Error", "Username not found", parent=self.root)
            return

        pass_win = Toplevel(self.root)
        ForgotPasswordWindow(pass_win, username, row[6], self.root)

class RegisterWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("Register New Account")
        self.root.geometry("600x650")
        
        self.container = ttk.Frame(root, padding=30)
        self.container.pack(expand=True, fill=BOTH)

        ttk.Label(self.container, text="Create Account", style="H1.TLabel").pack(pady=(0, 20))

        # Form Grid Frame
        form_frame = ttk.Frame(self.container)
        form_frame.pack(fill=X)
        form_frame.columnconfigure(0, weight=1)
        form_frame.columnconfigure(1, weight=1)

        # First Name
        ttk.Label(form_frame, text="First Name").grid(row=0, column=0, sticky=W, padx=5, pady=5)
        self.fname_entry = ttk.Entry(form_frame)
        self.fname_entry.grid(row=1, column=0, sticky=EW, padx=5, pady=5)

        # Last/Username
        ttk.Label(form_frame, text="Username").grid(row=0, column=1, sticky=W, padx=5, pady=5)
        self.l_entry = ttk.Entry(form_frame)
        self.l_entry.grid(row=1, column=1, sticky=EW, padx=5, pady=5)

        # Contact
        ttk.Label(form_frame, text="Contact Number").grid(row=2, column=0, sticky=W, padx=5, pady=5)
        self.txt_contact = ttk.Entry(form_frame)
        self.txt_contact.grid(row=3, column=0, sticky=EW, padx=5, pady=5)

        # Security Q
        ttk.Label(form_frame, text="Security Question").grid(row=2, column=1, sticky=W, padx=5, pady=5)
        options = ["what is your nickname?", "what is your hobby?"]
        self.clicked = StringVar()
        self.clicked.set(options[0])
        self.drop = ttk.Combobox(form_frame, textvariable=self.clicked, values=options, state="readonly")
        self.drop.grid(row=3, column=1, sticky=EW, padx=5, pady=5)

        # Security A
        ttk.Label(form_frame, text="Security Answer").grid(row=4, column=0, columnspan=2, sticky=W, padx=5, pady=5)
        self.txt_recode = ttk.Entry(form_frame)
        self.txt_recode.grid(row=5, column=0, columnspan=2, sticky=EW, padx=5, pady=5)

        # Password
        ttk.Label(form_frame, text="Password").grid(row=6, column=0, sticky=W, padx=5, pady=5)
        self.txt_pass = ttk.Entry(form_frame, show="*")
        self.txt_pass.grid(row=7, column=0, sticky=EW, padx=5, pady=5)

        # Confirm Password
        ttk.Label(form_frame, text="Confirm Password").grid(row=6, column=1, sticky=W, padx=5, pady=5)
        self.txt_conpass = ttk.Entry(form_frame, show='*')
        self.txt_conpass.grid(row=7, column=1, sticky=EW, padx=5, pady=5)
        
        # Show Password
        self.show_reg_pass_var = BooleanVar()
        self.chk_show_reg = ttk.Checkbutton(form_frame, text="Show Passwords", variable=self.show_reg_pass_var, command=self.toggle_reg_passwords)
        self.chk_show_reg.grid(row=8, column=0, columnspan=2, sticky=W, padx=5, pady=5)

        # Submit
        self.btn_register = ttk.Button(self.container, text="Register", style="Primary.TButton", command=self.register_click)
        self.btn_register.pack(fill=X, pady=(20, 0))

        # Keyboard bindings
        self.root.bind("<Return>", lambda e: self.register_click())
        self.root.bind("<Escape>", lambda e: self.root.destroy())
        self.fname_entry.focus_set()

    def toggle_reg_passwords(self):
        show_char = "" if self.show_reg_pass_var.get() else "*"
        self.txt_pass.config(show=show_char)
        self.txt_conpass.config(show=show_char)

    def is_strong_password(self, password):
        # Requires at least 8 chars, 1 uppercase, 1 lowercase, 1 number
        if len(password) < 8: return False
        if not any(char.isupper() for char in password): return False
        if not any(char.islower() for char in password): return False
        if not any(char.isdigit() for char in password): return False
        return True

    def is_valid_username(self, username):
        return bool(re.fullmatch(r"[A-Za-z0-9_]+", username))

    def register_click(self):
        fname = self.fname_entry.get()
        lname = self.l_entry.get()
        contact = self.txt_contact.get()
        recode = self.txt_recode.get()
        pw = self.txt_pass.get()
        cpw = self.txt_conpass.get()
        req = self.clicked.get()

        if not all([fname, lname, contact, recode, pw, cpw, req]):
            messagebox.showerror("Error", "All fields are required", parent=self.root)
            return
        if not fname.isalpha():
            messagebox.showerror("Error", "First name must contain alphabets only", parent=self.root)
            return
        if not self.is_valid_username(lname):
            messagebox.showerror("Error", "Username can only contain letters, numbers, and underscores", parent=self.root)
            return
        if len(contact) != 10 or not contact.isdigit():
            messagebox.showerror("Error", "Please enter a valid 10 digit number", parent=self.root)
            return
        if not self.is_strong_password(pw):
            messagebox.showerror("Weak Password", "Password must be at least 8 characters long and contain uppercase, lowercase, and numbers.", parent=self.root)
            return
        if pw != cpw:
            messagebox.showerror("Error", "Passwords must match", parent=self.root)
            return

        row = database.get_user_by_username(lname)
        if row is not None:
             messagebox.showerror("Error", "Username already exists", parent=self.root)
             return

        try:
            database.register_user(fname, lname, contact, recode, pw, cpw, req)
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "That username is already registered.", parent=self.root)
            return

        messagebox.showinfo("Registered", "Account created successfully! Please Login.", parent=self.root)
        self.root.destroy()

class ForgotPasswordWindow:
    def __init__(self, root, username, sec_question, parent_root):
        self.root = root
        self.username = username
        self.root.title("Forgot Password")
        self.root.geometry("400x500")

        self.container = ttk.Frame(root, padding=30)
        self.container.pack(expand=True, fill=BOTH)

        ttk.Label(self.container, text="Reset Password", style="H1.TLabel").pack(pady=(0, 20))
        
        ttk.Label(self.container, text="Security Question:", font=("Segoe UI", 10, "bold")).pack(anchor=W)
        ttk.Label(self.container, text=sec_question, foreground="darkred").pack(anchor=W, pady=(0, 15))

        ttk.Label(self.container, text="Your Answer").pack(anchor=W)
        self.txt_recode = ttk.Entry(self.container)
        self.txt_recode.pack(fill=X, pady=(0, 15))
        
        ttk.Label(self.container, text="New Password").pack(anchor=W)
        self.txt_newpass = ttk.Entry(self.container, show='*')
        self.txt_newpass.pack(fill=X, pady=(0, 30))

        ttk.Button(self.container, text="Reset Password", style="Primary.TButton", command=self.reset_pass).pack(fill=X)

        # Keyboard bindings
        self.root.bind("<Return>", lambda e: self.reset_pass())
        self.root.bind("<Escape>", lambda e: self.root.destroy())
        self.txt_recode.focus_set()

    def reset_pass(self):
        answer = self.txt_recode.get()
        new_pass = self.txt_newpass.get()
        
        if not answer or not new_pass:
             messagebox.showerror("Error", "All fields required", parent=self.root)
             return

        row = database.verify_recovery(self.username, answer)
        if row is None:
             messagebox.showerror("Error", "Incorrect security answer", parent=self.root)
             return

        database.update_password(self.username, answer, new_pass)
        messagebox.showinfo("Success", "Password reset successful! You can now login.", parent=self.root)
        self.root.destroy()
