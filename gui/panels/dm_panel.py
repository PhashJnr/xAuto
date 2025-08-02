import tkinter as tk
from tkinter import ttk, messagebox
from constants import COLOR_TAUPE, COLOR_DARK, COLOR_WHITE
import threading
from selenium_manager import send_dm
from utils import log_to_file

class DmPanel(ttk.Frame):
    def __init__(self, parent, accounts):
        super().__init__(parent)
        self.parent = parent
        self.accounts = accounts
        self.accounts_listbox = None
        self.recipient_entry = None
        self.message_entry = None
        self.log_text = None
        self.selected_tag = None
        self.tag_filter_dropdown = None
        # State persistence
        self.state = {
            'selected_tag': 'All',
            'recipient': '',
            'message': '',
            'log_messages': []
        }

    def build_panel(self):
        title = tk.Label(self, text="Send DM", font=('Segoe UI', 16, 'bold'), bg=COLOR_TAUPE, fg=COLOR_DARK)
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
        
        # Input fields frame
        input_frame = ttk.Frame(content_frame)
        input_frame.pack(fill='x', pady=10)
        
        # Recipient
        recipient_frame = ttk.Frame(input_frame)
        recipient_frame.pack(side='left', fill='x', expand=True, padx=(0, 10))
        
        tk.Label(recipient_frame, text="Recipient Username:", bg=COLOR_TAUPE, fg=COLOR_DARK).pack(anchor='w')
        self.recipient_entry = ttk.Entry(recipient_frame, width=20)
        self.recipient_entry.pack(fill='x', pady=2)
        self.recipient_entry.insert(0, self.state['recipient'])
        self.recipient_entry.bind('<KeyRelease>', self.on_recipient_change)
        
        # Message
        message_frame = ttk.Frame(input_frame)
        message_frame.pack(side='left', fill='x', expand=True, padx=(10, 0))
        
        tk.Label(message_frame, text="Message:", bg=COLOR_TAUPE, fg=COLOR_DARK).pack(anchor='w')
        self.message_entry = tk.Text(message_frame, width=30, height=3)
        self.message_entry.pack(fill='x', pady=2)
        self.message_entry.insert('1.0', self.state['message'])
        self.message_entry.bind('<KeyRelease>', self.on_message_change)
        
        # Send DM (Bulk) button
        send_btn = ttk.Button(content_frame, text="Send DM (Bulk)", command=self.send_dm_bulk)
        send_btn.pack(pady=10)
        
        # Log area
        log_frame = ttk.LabelFrame(content_frame, text="Activity Log", padding="10")
        log_frame.pack(fill='both', expand=True, pady=10)
        
        self.log_text = tk.Text(log_frame, height=8, state='disabled', bg=COLOR_DARK, fg=COLOR_WHITE)
        self.log_text.pack(fill='both', expand=True)
        
        # Restore log messages
        self.restore_log_messages()
        
        self.panel = self
        return self

    def on_recipient_change(self, event=None):
        """Save recipient to state"""
        self.state['recipient'] = self.recipient_entry.get()

    def on_message_change(self, event=None):
        """Save message to state"""
        self.state['message'] = self.message_entry.get('1.0', 'end-1c')

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
        log_to_file('dm', message)

    def send_dm_bulk(self):
        selected_indices = self.accounts_listbox.curselection()
        if not selected_indices:
            self.log("Select at least one account.", is_error=True)
            return
        recipient = self.recipient_entry.get().strip()
        message = self.message_entry.get("1.0", "end").strip()
        if not recipient or not message:
            self.log("Recipient and message are required.", is_error=True)
            return
        
        # Get filtered accounts based on current tag filter
        tag = self.selected_tag.get() if hasattr(self, 'selected_tag') else 'All'
        filtered_accounts = [a for a in self.accounts if tag == 'All' or tag in a.tags]
        selected_accounts = [filtered_accounts[i] for i in selected_indices]
        
        threading.Thread(target=self._send_dm_sequential, args=(selected_accounts, recipient, message)).start()

    def _send_dm_sequential(self, accounts, recipient, message):
        for acc in accounts:
            self.log(f"[{acc.label}] Sending DM...")
            success, msg = send_dm(acc, recipient, message)
            if success:
                self.log(f"[{acc.label}] ✅ {msg}")
            else:
                self.log(f"[{acc.label}] {msg}", is_error=True) 