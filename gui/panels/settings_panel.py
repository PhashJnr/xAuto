import tkinter as tk
from tkinter import ttk, messagebox
from constants import COLOR_TAUPE, COLOR_DARK

class SettingsPanel(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.auto_rotate_var = None

    def build_panel(self):
        title = tk.Label(self, text="Settings", font=('Segoe UI', 16, 'bold'), bg=COLOR_TAUPE, fg=COLOR_DARK)
        title.pack(anchor='nw', padx=20, pady=(20, 10))
        # Global auto-rotate proxy option
        self.auto_rotate_var = tk.BooleanVar()
        auto_rotate_check = ttk.Checkbutton(self, text="Auto-rotate proxies", variable=self.auto_rotate_var)
        auto_rotate_check.pack(anchor='nw', padx=20, pady=5)

    def on_auto_rotate_toggle(self):
        value = self.auto_rotate_var.get()
        print(f"[SETTINGS PANEL] Auto-rotate proxy set to: {value}")
        messagebox.showinfo("Settings", f"Auto-rotate proxy is now {'enabled' if value else 'disabled'}.") 