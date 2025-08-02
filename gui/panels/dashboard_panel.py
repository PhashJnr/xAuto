import tkinter as tk
from tkinter import ttk
from constants import COLOR_TAUPE, COLOR_DARK, COLOR_WHITE

class DashboardPanel(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

    def build_panel(self):
        title = tk.Label(self, text="Dashboard", font=('Segoe UI', 18, 'bold'), bg=COLOR_TAUPE, fg=COLOR_DARK, anchor='w')
        title.pack(anchor='nw', padx=20, pady=(20, 10))
        # Add more widgets as needed 