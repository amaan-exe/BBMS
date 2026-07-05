import csv
from tkinter import messagebox, filedialog

def export_to_csv(treeview, filename_prefix="export"):
    """
    Exports the contents of a ttk.Treeview to a CSV file.
    """
    # Ask the user for a file location to save the CSV
    filepath = filedialog.asksaveasfilename(
        defaultextension=".csv",
        initialfile=f"{filename_prefix}_data.csv",
        title="Save as CSV",
        filetypes=(("CSV Files", "*.csv"), ("All Files", "*.*"))
    )

    if not filepath:
        return  # User cancelled

    try:
        with open(filepath, mode="w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)

            # Write headers
            headers = [treeview.heading(col)["text"] for col in treeview["columns"]]
            writer.writerow(headers)

            # Write data rows
            for item in treeview.get_children():
                row_data = [str(val) for val in treeview.item(item)["values"]]
                writer.writerow(row_data)

        messagebox.showinfo("Export Successful", f"Data successfully exported to {filepath}")
    except Exception as e:
        messagebox.showerror("Export Error", f"Failed to export data: {str(e)}")
