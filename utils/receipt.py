import random
import os
from tkinter import *
from tkinter import ttk, messagebox

try:
    from fpdf import FPDF
    HAS_FPDF = True
except ImportError:
    HAS_FPDF = False


def print_receipt(slip_type, mobile, k):
    """
    Shows a modern styled receipt popup and offers PDF save.
    Args:
        slip_type (str): "Donater" or "Receiver"
        mobile (str): Mobile number
        k (tuple): DB row of the donor/receiver
    """
    slipno = random.randint(10000, 99999)

    # ===== Modern Receipt Popup =====
    win = Toplevel()
    win.title(f"Receipt — {slip_type}")
    win.geometry("420x620")
    win.resizable(False, False)
    win.configure(bg="#1a1a2e")

    # Main card
    card = Frame(win, bg="#ffffff", highlightbackground="#e0e0e0", highlightthickness=1)
    card.pack(padx=20, pady=20, fill=BOTH, expand=1)

    # Header
    header = Frame(card, bg="#8b0000", height=80)
    header.pack(fill=X)
    header.pack_propagate(False)
    Label(header, text="🩸 Blood Bank", font=("Segoe UI", 18, "bold"), bg="#8b0000", fg="white").pack(pady=(12, 0))
    Label(header, text="Management System", font=("Segoe UI", 10), bg="#8b0000", fg="#ffcccc").pack()

    # Slip info bar
    info_bar = Frame(card, bg="#f8f8f8", padx=15, pady=8)
    info_bar.pack(fill=X)
    Label(info_bar, text=f"SLIP #{slipno}", font=("Consolas", 11, "bold"), bg="#f8f8f8", fg="#8b0000").pack(side=LEFT)
    Label(info_bar, text=slip_type.upper(), font=("Segoe UI", 10, "bold"), bg="#f8f8f8", fg="#555555").pack(side=RIGHT)

    # Divider
    Frame(card, bg="#e0e0e0", height=1).pack(fill=X)

    # Details section
    details = Frame(card, bg="white", padx=20, pady=15)
    details.pack(fill=X)

    fields = [
        ("Name", str(k[1])),
        ("Date", str(k[0])),
        ("Gender", str(k[2])),
        ("Address", str(k[3])),
        ("Mobile", str(k[4])),
        ("Nationality", str(k[5])),
        ("ID Proof", str(k[6])),
        ("ID Number", str(k[7])),
        ("Age Group", str(k[8])),
    ]

    for i, (label, value) in enumerate(fields):
        row = Frame(details, bg="white")
        row.pack(fill=X, pady=1)
        Label(row, text=f"{label}:", font=("Segoe UI", 9), bg="white", fg="#888888", width=12, anchor=W).pack(side=LEFT)
        Label(row, text=value, font=("Segoe UI", 9, "bold"), bg="white", fg="#333333", anchor=W).pack(side=LEFT)

    # Blood info card
    Frame(card, bg="#e0e0e0", height=1).pack(fill=X, padx=15)

    blood_section = Frame(card, bg="#fff5f5", padx=20, pady=15)
    blood_section.pack(fill=X, padx=15, pady=10)

    Label(blood_section, text="Blood Details", font=("Segoe UI", 11, "bold"), bg="#fff5f5", fg="#8b0000").pack(anchor=W, pady=(0, 8))

    blood_row = Frame(blood_section, bg="#fff5f5")
    blood_row.pack(fill=X)

    # Blood type badge
    type_frame = Frame(blood_row, bg="#8b0000", padx=12, pady=6)
    type_frame.pack(side=LEFT)
    Label(type_frame, text=str(k[9]), font=("Segoe UI", 16, "bold"), bg="#8b0000", fg="white").pack()

    # Quantity
    qty_frame = Frame(blood_row, bg="#fff5f5", padx=20)
    qty_frame.pack(side=LEFT)
    Label(qty_frame, text="Quantity", font=("Segoe UI", 9), bg="#fff5f5", fg="#888888").pack(anchor=W)
    Label(qty_frame, text=f"{k[10]} ml", font=("Segoe UI", 18, "bold"), bg="#fff5f5", fg="#333333").pack(anchor=W)

    # Footer
    Frame(card, bg="#e0e0e0", height=1).pack(fill=X, padx=15)

    footer = Frame(card, bg="white", padx=20, pady=12)
    footer.pack(fill=BOTH, expand=1)

    Label(footer, text="Thank you for your contribution!", font=("Segoe UI", 9, "italic"), bg="white", fg="#888888").pack(pady=(5, 10))

    # Action buttons
    btn_frame = Frame(footer, bg="white")
    btn_frame.pack()

    if HAS_FPDF:
        Button(btn_frame, text="💾 Save as PDF", font=("Segoe UI", 10, "bold"),
               bg="#8b0000", fg="white", relief=FLAT, padx=15, pady=5, cursor="hand2",
               command=lambda: _save_receipt_pdf(slip_type, slipno, k, win)).pack(side=LEFT, padx=5)

    Button(btn_frame, text="✕ Close", font=("Segoe UI", 10),
           bg="#eeeeee", fg="#333333", relief=FLAT, padx=15, pady=5, cursor="hand2",
           command=win.destroy).pack(side=LEFT, padx=5)


def _save_receipt_pdf(slip_type, slipno, k, parent_win):
    """Generates a professional PDF receipt."""
    from tkinter import filedialog

    filepath = filedialog.asksaveasfilename(
        defaultextension=".pdf",
        initialfile=f"receipt_{slipno}.pdf",
        title="Save Receipt",
        filetypes=(("PDF Files", "*.pdf"),),
        parent=parent_win
    )
    if not filepath:
        return

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=False)

    # Header
    pdf.set_fill_color(139, 0, 0)
    pdf.rect(0, 0, 210, 35, 'F')
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(0, 8)
    pdf.cell(210, 10, "Blood Bank Management System", align="C")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_xy(0, 20)
    pdf.cell(210, 8, f"Receipt #{slipno}  |  {slip_type}", align="C")

    # Details
    pdf.set_text_color(0, 0, 0)
    pdf.set_xy(20, 45)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Personal Details", new_x="LMARGIN", new_y="NEXT")

    fields = [
        ("Name", str(k[1])), ("Date", str(k[0])), ("Gender", str(k[2])),
        ("Address", str(k[3])), ("Mobile", str(k[4])), ("Nationality", str(k[5])),
        ("ID Proof", str(k[6])), ("ID Number", str(k[7])), ("Age Group", str(k[8]))
    ]

    pdf.set_x(20)
    for label, value in fields:
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(120, 120, 120)
        pdf.cell(40, 7, label)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 7, value, new_x="LMARGIN", new_y="NEXT")
        pdf.set_x(20)

    # Blood section
    pdf.ln(5)
    pdf.set_x(20)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(139, 0, 0)
    pdf.cell(0, 8, "Blood Details", new_x="LMARGIN", new_y="NEXT")

    pdf.set_x(20)
    pdf.set_fill_color(139, 0, 0)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(30, 15, str(k[9]), border=0, fill=True, align="C")

    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(50, 15, f"  {k[10]} ml")
    pdf.ln(20)

    # Footer
    pdf.set_x(20)
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 10, "Thank you for your contribution!", align="L")

    pdf.output(filepath)
    messagebox.showinfo("Saved", f"Receipt saved to:\n{filepath}", parent=parent_win)


def print_total_blood_inventory(rows):
    """Shows a modern styled inventory summary popup."""
    win = Toplevel()
    win.title("Blood Inventory Report")
    win.geometry("500x350")
    win.resizable(False, False)
    win.configure(bg="#1a1a2e")

    card = Frame(win, bg="#ffffff", highlightbackground="#e0e0e0", highlightthickness=1)
    card.pack(padx=20, pady=20, fill=BOTH, expand=1)

    # Header
    header = Frame(card, bg="#8b0000", height=60)
    header.pack(fill=X)
    header.pack_propagate(False)
    Label(header, text="🩸 Blood Inventory Report", font=("Segoe UI", 16, "bold"), bg="#8b0000", fg="white").pack(pady=15)

    # Table
    blood_types = ["A+", "B+", "O+", "AB+", "A-", "B-", "O-", "AB-"]
    table_frame = Frame(card, bg="white", padx=15, pady=15)
    table_frame.pack(fill=BOTH, expand=1)

    # Header row
    for col, bt in enumerate(blood_types):
        Label(table_frame, text=bt, font=("Segoe UI", 10, "bold"), bg="#8b0000", fg="white",
              width=6, relief=RIDGE).grid(row=0, column=col, padx=1, pady=1)

    # Data rows
    if rows:
        for row_idx, row in enumerate(rows):
            for col_idx in range(min(8, len(row))):
                val = str(row[col_idx])
                bg_color = "#fff5f5" if int(row[col_idx]) <= 5 else "white"
                fg_color = "#cc0000" if int(row[col_idx]) <= 5 else "#333333"
                Label(table_frame, text=val, font=("Segoe UI", 11), bg=bg_color, fg=fg_color,
                      width=6, relief=RIDGE).grid(row=row_idx + 1, column=col_idx, padx=1, pady=1)

    # Total
    if rows and len(rows) > 0:
        total = sum(rows[0][:8])
        Label(card, text=f"Total Units: {total}", font=("Segoe UI", 12, "bold"), bg="white", fg="#8b0000").pack(pady=(0, 10))

    # Close button
    Button(card, text="✕ Close", font=("Segoe UI", 10), bg="#eeeeee", fg="#333333",
           relief=FLAT, padx=15, pady=5, cursor="hand2", command=win.destroy).pack(pady=(0, 15))
