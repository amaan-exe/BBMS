import shutil
import os
from datetime import datetime
from tkinter import messagebox, filedialog

DB_NAME = "blood.db"

def backup_database():
    """Creates a timestamped backup of the database file."""
    if not os.path.exists(DB_NAME):
        messagebox.showerror("Backup Error", "Database file not found.")
        return False
    
    backup_dir = "backups"
    os.makedirs(backup_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(backup_dir, f"blood_backup_{timestamp}.db")
    
    try:
        shutil.copy2(DB_NAME, backup_path)
        messagebox.showinfo("Backup Successful", f"Database backed up to:\n{backup_path}")
        return True
    except Exception as e:
        messagebox.showerror("Backup Error", f"Failed to backup: {str(e)}")
        return False

def restore_database():
    """Restores the database from a user-selected backup file."""
    filepath = filedialog.askopenfilename(
        initialdir="backups",
        title="Select Backup File",
        filetypes=(("Database Files", "*.db"), ("All Files", "*.*"))
    )
    
    if not filepath:
        return False
    
    try:
        # Safety: backup current before restoring
        if os.path.exists(DB_NAME):
            shutil.copy2(DB_NAME, DB_NAME + ".pre_restore")
        
        shutil.copy2(filepath, DB_NAME)
        messagebox.showinfo("Restore Successful", "Database restored successfully!\nPlease restart the application.")
        return True
    except Exception as e:
        messagebox.showerror("Restore Error", f"Failed to restore: {str(e)}")
        return False
