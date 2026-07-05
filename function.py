from tkinter import filedialog, messagebox
import os

def browse_file(file_var):
    file_path = filedialog.askopenfilename(title="Select a file")
    if file_path:
        file_var.set(file_path)

def encrypt_file(file_var):
    file_path = file_var.get().strip()
    if not file_path:
        messagebox.showwarning("No File", "Please select a file first.")
        return
    
    if not os.path.exists(file_path):
        messagebox.showerror("Error", "The selected file does not exist.")
        return
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        encrypted_chars = nibble_encrypt(content)

        enc_path = file_path + '.enc'
        with open(enc_path, 'wb') as f:
            f.write(bytes([ord(ch) for ch in encrypted_chars]))

        messagebox.showinfo("Success", f"File encrypted successfully!\nSaved to: {enc_path}")
    except Exception as e:
        messagebox.showerror("Error", f"Encryption failed:\n{e}")

def decrypt_file(file_var):
    file_path = file_var.get().strip()
    if not file_path:
        messagebox.showwarning("No File", "Please select a file first.")
        return
    if not os.path.exists(file_path):
        messagebox.showerror("Error", "The selected file does not exist.")
        return
    try:
        with open(file_path, 'rb') as f:
            encrypted_bytes = f.read()

        encrypted_chars = [chr(b) for b in encrypted_bytes]
        decrypted = nibble_decrypt(encrypted_chars)

        if file_path.endswith('.enc'):
            dec_path = file_path[:-4]
        else:
            dec_path = file_path + '.dec.txt'

        with open(dec_path, 'w', encoding='utf-8') as f:
            f.write(decrypted)

        messagebox.showinfo("Success", f"File decrypted successfully!\nSaved to: {dec_path}")
    except Exception as e:
        messagebox.showerror("Error", f"Decryption failed:\n{e}")

def nibble_encrypt(input_string):
    def rechunk(a):
        result = []
        for i in range(0, len(a), 4):
            if i + 2 < len(a):
                result.append(a[i] + a[i + 2])
            if i + 3 < len(a):
                result.append(a[i + 1] + a[i + 3])
        return result

    def binary_to_decimal(binary_str):
        decimal = 0
        for i, bit in enumerate(reversed(binary_str)):
            if bit == '1':
                decimal += 2 ** i
        return decimal
    if len(input_string) % 2 != 0:
        input_string = input_string.zfill(len(input_string) + 1)

    cipher = ''.join([bin(ord(ch))[2:].zfill(8) for ch in input_string])
    chunks = [cipher[i:i + 4] for i in range(0, len(cipher), 4)]
    encryptedlst = rechunk(chunks)
    encrypted = [chr(binary_to_decimal(b)) for b in encryptedlst]
    return encrypted

def nibble_decrypt(encrypted_chars):
    """Reverse of nibble_encrypt: undo the nibble interleave to recover plaintext."""
    def reverse_rechunk(a):
        """For every pair [AC, BD], extract the original four nibbles [A, B, C, D]."""
        result = []
        for i in range(0, len(a), 2):
            if i + 1 < len(a):
                ac = a[i]       
                bd = a[i + 1]   
                result.append(ac[:4])   
                result.append(bd[:4])   
                result.append(ac[4:])   
                result.append(bd[4:])   
        return result
    def binary_to_decimal(binary_str):
        decimal = 0
        for i, bit in enumerate(reversed(binary_str)):
            if bit == '1':
                decimal += 2 ** i
        return decimal

    encrypted_binary = [bin(ord(ch))[2:].zfill(8) for ch in encrypted_chars]
    
    original_nibbles = reverse_rechunk(encrypted_binary)
    
    original_binary = []
    for i in range(0, len(original_nibbles), 2):
        if i + 1 < len(original_nibbles):
            original_binary.append(original_nibbles[i] + original_nibbles[i + 1])

    decrypted = ''.join([chr(binary_to_decimal(b)) for b in original_binary])

    return decrypted
