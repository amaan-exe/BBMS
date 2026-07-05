from tkinter import messagebox, filedialog
import database

try:
    from fpdf import FPDF
    HAS_FPDF = True
except ImportError:
    HAS_FPDF = False

if HAS_FPDF:
    class BloodBankPDF(FPDF):
        def header(self):
            self.set_font("Helvetica", "B", 18)
            self.set_text_color(139, 0, 0)
            self.cell(0, 12, "Blood Bank Management System", new_x="LMARGIN", new_y="NEXT", align="C")
            self.set_font("Helvetica", "", 9)
            self.set_text_color(100, 100, 100)
            self.cell(0, 6, "Confidential Report", new_x="LMARGIN", new_y="NEXT", align="C")
            self.ln(5)
            self.set_draw_color(139, 0, 0)
            self.line(10, self.get_y(), 200, self.get_y())
            self.ln(5)

        def footer(self):
            self.set_y(-15)
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(128, 128, 128)
            self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

def generate_donor_report():
    if not HAS_FPDF:
        messagebox.showerror("Error", "PDF generation requires fpdf2.\nRun: pip install fpdf2")
        return
    
    filepath = filedialog.asksaveasfilename(
        defaultextension=".pdf", initialfile="donor_report.pdf",
        title="Save Donor Report", filetypes=(("PDF Files", "*.pdf"),)
    )
    if not filepath:
        return

    donors = database.get_all_donors()
    pdf = BloodBankPDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Donor Report", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 6, f"Total Records: {len(donors)}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    # Table Header
    headers = ["Date", "Name", "Gender", "Address", "Mobile", "Blood", "Units"]
    col_widths = [22, 35, 18, 30, 28, 18, 18]
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(139, 0, 0)
    pdf.set_text_color(255, 255, 255)
    for h, w in zip(headers, col_widths):
        pdf.cell(w, 8, h, border=1, fill=True, align="C")
    pdf.ln()

    # Table Rows
    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(0, 0, 0)
    for row in donors:
        vals = [str(row[0]), str(row[1]), str(row[2]), str(row[3]), str(row[4]), str(row[9]), str(row[10])]
        for v, w in zip(vals, col_widths):
            pdf.cell(w, 7, v[:20], border=1, align="C")
        pdf.ln()

    pdf.output(filepath)
    messagebox.showinfo("PDF Generated", f"Donor report saved to:\n{filepath}")

def generate_receiver_report():
    if not HAS_FPDF:
        messagebox.showerror("Error", "PDF generation requires fpdf2.\nRun: pip install fpdf2")
        return

    filepath = filedialog.asksaveasfilename(
        defaultextension=".pdf", initialfile="receiver_report.pdf",
        title="Save Receiver Report", filetypes=(("PDF Files", "*.pdf"),)
    )
    if not filepath:
        return

    receivers = database.get_all_receivers()
    pdf = BloodBankPDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Receiver Report", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 6, f"Total Records: {len(receivers)}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    headers = ["Date", "Name", "Gender", "Address", "Mobile", "Blood", "Units"]
    col_widths = [22, 35, 18, 30, 28, 18, 18]
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(139, 0, 0)
    pdf.set_text_color(255, 255, 255)
    for h, w in zip(headers, col_widths):
        pdf.cell(w, 8, h, border=1, fill=True, align="C")
    pdf.ln()

    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(0, 0, 0)
    for row in receivers:
        vals = [str(row[0]), str(row[1]), str(row[2]), str(row[3]), str(row[4]), str(row[9]), str(row[10])]
        for v, w in zip(vals, col_widths):
            pdf.cell(w, 7, v[:20], border=1, align="C")
        pdf.ln()

    pdf.output(filepath)
    messagebox.showinfo("PDF Generated", f"Receiver report saved to:\n{filepath}")

def generate_inventory_report():
    if not HAS_FPDF:
        messagebox.showerror("Error", "PDF generation requires fpdf2.\nRun: pip install fpdf2")
        return

    filepath = filedialog.asksaveasfilename(
        defaultextension=".pdf", initialfile="inventory_report.pdf",
        title="Save Inventory Report", filetypes=(("PDF Files", "*.pdf"),)
    )
    if not filepath:
        return

    inv = database.get_blood_inventory_dict()
    pdf = BloodBankPDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Blood Inventory Report", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    headers = list(inv.keys()) if inv else ["A+", "B+", "O+", "AB+", "A-", "B-", "O-", "AB-"]
    values = list(inv.values()) if inv else [0]*8
    col_w = 22

    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(139, 0, 0)
    pdf.set_text_color(255, 255, 255)
    for h in headers:
        pdf.cell(col_w, 10, h, border=1, fill=True, align="C")
    pdf.ln()

    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(0, 0, 0)
    for v in values:
        pdf.cell(col_w, 10, str(v), border=1, align="C")
    pdf.ln()

    total = sum(values)
    pdf.ln(10)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 10, f"Total Units Available: {total}", new_x="LMARGIN", new_y="NEXT")

    pdf.output(filepath)
    messagebox.showinfo("PDF Generated", f"Inventory report saved to:\n{filepath}")
