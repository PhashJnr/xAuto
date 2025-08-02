import tkinter as tk
from tkinter import ttk, messagebox
from constants import COLOR_TAUPE, COLOR_DARK

class HistoryPanel(ttk.Frame):
    def __init__(self, parent, history=None):
        super().__init__(parent)
        self.parent = parent
        self.history = history or ["Sample action 1", "Sample action 2"]
        self.history_listbox = None

    def build_panel(self):
        title = tk.Label(self, text="History", font=('Segoe UI', 16, 'bold'), bg=COLOR_TAUPE, fg=COLOR_DARK)
        title.pack(anchor='nw', padx=20, pady=(20, 10))
        # History list
        self.history_listbox = tk.Listbox(self, height=8)
        self.refresh_history_listbox()
        self.history_listbox.pack(anchor='nw', padx=20, pady=5)
        # Action buttons
        btn_frame = tk.Frame(self, bg=COLOR_TAUPE)
        btn_frame.pack(anchor='nw', padx=20, pady=5)
        ttk.Button(btn_frame, text="Clear History", command=self.clear_history).pack(side='left', padx=2)
        ttk.Button(btn_frame, text="Export History", command=self.export_history).pack(side='left', padx=2)

    def refresh_history_listbox(self):
        if self.history_listbox:
            self.history_listbox.delete(0, 'end')
            for item in self.history:
                self.history_listbox.insert('end', str(item))

    def clear_history(self):
        confirm = messagebox.askyesno("Clear History", "Are you sure you want to clear all history?")
        if confirm:
            self.history.clear()
            self.refresh_history_listbox()
            print("[HISTORY PANEL] Cleared history.")
            messagebox.showinfo("Clear History", "History cleared.") 