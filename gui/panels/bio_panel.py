import tkinter as tk
from tkinter import ttk, messagebox
from constants import COLOR_TAUPE, COLOR_DARK, COLOR_WHITE
import threading
from selenium_manager import change_bio
from utils import log_to_file

class BioPanel(ttk.Frame):
    def __init__(self, parent, accounts):
        super().__init__(parent)
        self.parent = parent
        self.accounts = accounts
        self.panel = None
        self.accounts_listbox = None
        self.bio_entry = None
        self.log_text = None
        self.selected_tag = None
        self.tag_filter_dropdown = None
        # State persistence
        self.state = {
            'selected_tag': 'All',
            'bio_text': '',
            'log_messages': []
        }

    def build_panel(self):
        title = tk.Label(self, text="Change Bio", font=('Segoe UI', 16, 'bold'), bg=COLOR_TAUPE, fg=COLOR_DARK)
        title.pack(anchor='nw', padx=20, pady=(20, 10))
        
        # Main content frame
        content_frame = ttk.Frame(self)
        content_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        # Tag filter
        filter_frame = ttk.Frame(content_frame)
        filter_frame.pack(fill='x', pady=5)
        
        tk.Label(filter_frame, text="Filter by Tag:", bg=COLOR_TAUPE, fg=COLOR_DARK).pack(side='left', padx=5)
        all_tags = set()
        for acc in self.accounts:
            if acc.tags:
                all_tags.update(acc.tags)
        
        self.selected_tag = tk.StringVar(value=self.state['selected_tag'])
        tag_options = ['All'] + list(all_tags)
        self.tag_filter_dropdown = ttk.Combobox(filter_frame, textvariable=self.selected_tag, values=tag_options, state='readonly', width=16)
        self.tag_filter_dropdown.pack(side='left', padx=5)
        self.tag_filter_dropdown.bind('<<ComboboxSelected>>', self.on_tag_filter_change)
        
        # Account selection
        accounts_frame = ttk.LabelFrame(content_frame, text="Select Accounts", padding="10")
        accounts_frame.pack(fill='x', pady=5)
        
        self.accounts_listbox = tk.Listbox(accounts_frame, selectmode='multiple', height=5, exportselection=False)
        self.accounts_listbox.pack(fill='x', padx=5, pady=5)
        self.refresh_accounts_list()
        
        # Bio input
        bio_frame = ttk.LabelFrame(content_frame, text="New Bio", padding="10")
        bio_frame.pack(fill='x', pady=10)
        
        self.bio_entry = tk.Text(bio_frame, width=50, height=3)
        self.bio_entry.pack(fill='x', padx=5, pady=5)
        self.bio_entry.insert('1.0', self.state['bio_text'])
        self.bio_entry.bind('<KeyRelease>', self.on_bio_change)
        
        # Change Bio (Bulk) button
        bio_btn = ttk.Button(content_frame, text="Change Bio (Bulk)", command=self.change_bio_bulk)
        bio_btn.pack(pady=10)
        
        # Log area
        log_frame = ttk.LabelFrame(content_frame, text="Activity Log", padding="10")
        log_frame.pack(fill='both', expand=True, pady=10)
        
        self.log_text = tk.Text(log_frame, height=8, state='disabled', bg=COLOR_DARK, fg=COLOR_WHITE)
        self.log_text.pack(fill='both', expand=True)
        
        # Restore log messages
        self.restore_log_messages()
        
        self.panel = self
        return self

    def on_bio_change(self, event=None):
        """Save bio text to state"""
        self.state['bio_text'] = self.bio_entry.get('1.0', 'end-1c')

    def on_tag_filter_change(self, event=None):
        """Handle tag filter change and save state"""
        self.state['selected_tag'] = self.selected_tag.get()
        self.refresh_accounts_list()

    def restore_log_messages(self):
        """Restore log messages from state"""
        for message in self.state['log_messages']:
            self.log_text.config(state='normal')
            self.log_text.insert('end', message + '\n')
            self.log_text.see('end')
            self.log_text.config(state='disabled')

    def refresh_accounts_list(self):
        """Refresh the accounts listbox based on selected tag filter"""
        self.accounts_listbox.delete(0, tk.END)
        tag = self.selected_tag.get() if hasattr(self, 'selected_tag') else 'All'
        filtered_accounts = [a for a in self.accounts if tag == 'All' or tag in a.tags]
        for acc in filtered_accounts:
            tags_text = f" [{', '.join(acc.tags)}]" if acc.tags else ""
            self.accounts_listbox.insert('end', f"{acc.label} ({acc.username}){tags_text}")

    def log(self, message, is_error=False):
        if is_error:
            message = f"❌ {message}"
        self.log_text.config(state='normal')
        self.log_text.insert('end', message + '\n')
        self.log_text.see('end')
        self.log_text.config(state='disabled')
        # Save to state
        self.state['log_messages'].append(message)
        # Keep only last 100 messages to prevent memory issues
        if len(self.state['log_messages']) > 100:
            self.state['log_messages'] = self.state['log_messages'][-100:]
        log_to_file('bio', message)

    def change_bio_bulk(self):
        selected_indices = self.accounts_listbox.curselection()
        if not selected_indices:
            self.log("Select at least one account.", is_error=True)
            return
        bio = self.bio_entry.get("1.0", "end").strip()
        if not bio:
            self.log("Bio is required.", is_error=True)
            return
        
        # Get filtered accounts based on current tag filter
        tag = self.selected_tag.get() if hasattr(self, 'selected_tag') else 'All'
        filtered_accounts = [a for a in self.accounts if tag == 'All' or tag in a.tags]
        selected_accounts = [filtered_accounts[i] for i in selected_indices]
        
        threading.Thread(target=self._change_bio_sequential, args=(selected_accounts, bio)).start()

    def _change_bio_sequential(self, accounts, bio):
        for acc in accounts:
            self.log(f"[{acc.label}] Changing bio...")
            success, msg = change_bio(acc, bio)
            if success:
                self.log(f"[{acc.label}] ✅ {msg}")
            else:
                self.log(f"[{acc.label}] {msg}", is_error=True) 