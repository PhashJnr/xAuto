import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from constants import COLOR_TAUPE, COLOR_DARK, COLOR_WHITE
import threading
from selenium_manager import change_profile_pic
from utils import log_to_file

class ProfilePicPanel(ttk.Frame):
    def __init__(self, parent, accounts):
        super().__init__(parent)
        self.parent = parent
        self.accounts = accounts
        self.panel = None
        self.account_var = None
        self.image_path_var = None
        self.log_text = None
        self.selected_tag = None
        self.tag_filter_dropdown = None
        self.account_dropdown = None
        # State persistence
        self.state = {
            'selected_tag': 'All',
            'selected_account': '',
            'image_path': '',
            'log_messages': []
        }

    def build_panel(self):
        title = tk.Label(self, text="Change Profile Pic", font=('Segoe UI', 16, 'bold'), bg=COLOR_TAUPE, fg=COLOR_DARK)
        title.pack(anchor='nw', padx=20, pady=(20, 10))
        
        # Tag filter
        tk.Label(self, text="Filter by Tag:", bg=COLOR_TAUPE, fg=COLOR_DARK).pack(anchor='nw', padx=20)
        all_tags = set()
        for acc in self.accounts:
            all_tags.update(acc.tags)
        all_tags = sorted(all_tags)
        self.selected_tag = tk.StringVar(value=self.state['selected_tag'])
        tag_options = ['All'] + all_tags
        self.tag_filter_dropdown = ttk.Combobox(self, textvariable=self.selected_tag, values=tag_options, state='readonly', width=16)
        self.tag_filter_dropdown.pack(anchor='nw', padx=20, pady=2)
        self.tag_filter_dropdown.bind('<<ComboboxSelected>>', self.on_tag_filter_change)
        
        # Account selection
        tk.Label(self, text="Select Account:", bg=COLOR_TAUPE, fg=COLOR_DARK).pack(anchor='nw', padx=20)
        self.account_var = tk.StringVar(value=self.state['selected_account'])
        self.account_dropdown = ttk.Combobox(self, textvariable=self.account_var, state='readonly')
        self.account_dropdown.pack(anchor='nw', padx=20, pady=2)
        self.refresh_accounts_dropdown()
        
        # Image file selection
        tk.Label(self, text="Select Image:", bg=COLOR_TAUPE, fg=COLOR_DARK).pack(anchor='nw', padx=20)
        self.image_path_var = tk.StringVar(value=self.state['image_path'])
        ttk.Entry(self, textvariable=self.image_path_var, width=50, state='readonly').pack(anchor='nw', padx=20, pady=2)
        ttk.Button(self, text="Browse", command=self.browse_image).pack(anchor='nw', padx=20, pady=2)
        ttk.Button(self, text="Upload & Set Profile Pic", command=self.upload_profile_pic).pack(anchor='nw', padx=20, pady=10)
        
        # Log area
        self.log_text = tk.Text(self, height=8, state='disabled', bg=COLOR_DARK, fg=COLOR_WHITE)
        self.log_text.pack(anchor='nw', padx=20, pady=(10, 10), fill='x')
        
        # Restore log messages
        self.restore_log_messages()
        
        self.panel = self
        return self

    def on_tag_filter_change(self, event=None):
        """Handle tag filter change and save state"""
        self.state['selected_tag'] = self.selected_tag.get()
        self.refresh_accounts_dropdown()

    def restore_log_messages(self):
        """Restore log messages from state"""
        for message in self.state['log_messages']:
            self.log_text.config(state='normal')
            self.log_text.insert('end', message + '\n')
            self.log_text.see('end')
            self.log_text.config(state='disabled')

    def refresh_accounts_dropdown(self):
        """Refresh the accounts dropdown based on selected tag filter"""
        tag = self.selected_tag.get() if hasattr(self, 'selected_tag') else 'All'
        filtered_accounts = [a for a in self.accounts if tag == 'All' or tag in a.tags]
        account_options = []
        for acc in filtered_accounts:
            tags_text = f" [{', '.join(acc.tags)}]" if acc.tags else ""
            account_options.append(f"{acc.label} ({acc.username}){tags_text}")
        self.account_dropdown['values'] = account_options
        if account_options:
            if self.state['selected_account'] in account_options:
                self.account_var.set(self.state['selected_account'])
            else:
                self.account_var.set(account_options[0])
                self.state['selected_account'] = account_options[0]
        else:
            self.account_var.set('')
            self.state['selected_account'] = ''

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
        log_to_file('profile_pic', message)

    def browse_image(self):
        path = filedialog.askopenfilename(title="Select Profile Picture", filetypes=[("Image Files", "*.png;*.jpg;*.jpeg")])
        if path:
            self.image_path_var.set(path)
            self.state['image_path'] = path

    def upload_profile_pic(self):
        account_label = self.account_var.get()
        image_path = self.image_path_var.get()
        if not account_label:
            self.log("Select an account.", is_error=True)
            return
        if not image_path:
            self.log("Select an image file.", is_error=True)
            return
        
        # Get filtered accounts based on current tag filter
        tag = self.selected_tag.get() if hasattr(self, 'selected_tag') else 'All'
        filtered_accounts = [a for a in self.accounts if tag == 'All' or tag in a.tags]
        
        # Find the selected account from filtered list
        acc = None
        for a in filtered_accounts:
            tags_text = f" [{', '.join(a.tags)}]" if a.tags else ""
            if f"{a.label} ({a.username}){tags_text}" == account_label:
                acc = a
                break
        
        if not acc:
            self.log(f"[ERROR] Could not find account object for {account_label}", is_error=True)
            return
        
        self.log(f"[{acc.label}] Uploading profile pic...")
        threading.Thread(target=self._upload_pic_task, args=(acc, image_path)).start()

    def _upload_pic_task(self, acc, image_path):
        success, msg = change_profile_pic(acc, image_path)
        if success:
            self.log(f"[{acc.label}] ✅ {msg}")
        else:
            self.log(f"[{acc.label}] {msg}", is_error=True) 