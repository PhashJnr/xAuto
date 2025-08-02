import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
from constants import COLOR_TAUPE, COLOR_DARK, COLOR_WHITE
from selenium_manager import reply_to_tweet
from utils import log_to_file

class ReplyPanel(ttk.Frame):
    def __init__(self, parent, accounts):
        super().__init__(parent)
        self.parent = parent
        self.accounts = accounts
        self.panel = None
        self.accounts_listbox = None
        self.tweet_url_entry = None
        self.reply_entry = None
        self.log_text = None
        self.selected_tag = None
        self.tag_filter_dropdown = None
        self.reply_button = None
        self.is_processing = False
        # State persistence
        self.state = {
            'selected_tag': 'All',
            'tweet_url': '',
            'reply_text': '',
            'log_messages': []
        }

    def build_panel(self):
        title = tk.Label(self, text="Reply to Tweet", font=('Segoe UI', 16, 'bold'), bg=COLOR_TAUPE, fg=COLOR_DARK)
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
        
        # Tweet URL
        url_frame = ttk.Frame(input_frame)
        url_frame.pack(side='left', fill='x', expand=True, padx=(0, 10))
        
        tk.Label(url_frame, text="Tweet URL:", bg=COLOR_TAUPE, fg=COLOR_DARK).pack(anchor='w')
        self.tweet_url_entry = ttk.Entry(url_frame, width=40)
        self.tweet_url_entry.pack(fill='x', pady=2)
        self.tweet_url_entry.insert(0, self.state['tweet_url'])
        self.tweet_url_entry.bind('<KeyRelease>', self.on_tweet_url_change)
        
        # Reply text
        reply_frame = ttk.Frame(input_frame)
        reply_frame.pack(side='left', fill='x', expand=True, padx=(10, 0))
        
        tk.Label(reply_frame, text="Reply Text:", bg=COLOR_TAUPE, fg=COLOR_DARK).pack(anchor='w')
        self.reply_entry = tk.Text(reply_frame, width=40, height=3)
        self.reply_entry.pack(fill='x', pady=2)
        self.reply_entry.insert('1.0', self.state['reply_text'])
        self.reply_entry.bind('<KeyRelease>', self.on_reply_text_change)
        
        # Reply (Bulk) button
        self.reply_button = ttk.Button(content_frame, text="Reply (Bulk)", command=self.reply_bulk)
        self.reply_button.pack(pady=10)
        
        # Log area
        log_frame = ttk.LabelFrame(content_frame, text="Activity Log", padding="10")
        log_frame.pack(fill='both', expand=True, pady=10)
        
        self.log_text = tk.Text(log_frame, height=8, state='disabled', bg=COLOR_DARK, fg=COLOR_WHITE)
        self.log_text.pack(fill='both', expand=True)
        
        # Restore log messages
        self.restore_log_messages()
        
        self.panel = self
        return self

    def on_tweet_url_change(self, event=None):
        """Save tweet URL to state"""
        self.state['tweet_url'] = self.tweet_url_entry.get()

    def on_reply_text_change(self, event=None):
        """Save reply text to state"""
        self.state['reply_text'] = self.reply_entry.get('1.0', 'end-1c')

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
        log_to_file('reply', message)

    def update_button_state(self, enabled=True):
        """Update button state to prevent multiple operations"""
        if self.reply_button:
            if enabled:
                self.reply_button.config(text="Reply (Bulk)", state='normal')
            else:
                self.reply_button.config(text="Processing...", state='disabled')

    def reply_bulk(self):
        """Start bulk reply operation in a separate thread"""
        if self.is_processing:
            return
            
        selected_indices = self.accounts_listbox.curselection()
        if not selected_indices:
            self.log("Select at least one account.", is_error=True)
            return
        tweet_url = self.tweet_url_entry.get().strip()
        if not tweet_url:
            self.log("Tweet URL is required.", is_error=True)
            return
        reply_text = self.reply_entry.get("1.0", "end").strip()
        if not reply_text:
            self.log("Reply text is required.", is_error=True)
            return
        
        # Get filtered accounts based on current tag filter
        tag = self.selected_tag.get() if hasattr(self, 'selected_tag') else 'All'
        filtered_accounts = [a for a in self.accounts if tag == 'All' or tag in a.tags]
        selected_accounts = [filtered_accounts[i] for i in selected_indices]
        
        # Start processing in separate thread
        self.is_processing = True
        self.update_button_state(False)
        
        thread = threading.Thread(target=self._reply_bulk_worker, args=(selected_accounts, tweet_url, reply_text))
        thread.daemon = True
        thread.start()

    def _reply_bulk_worker(self, selected_accounts, tweet_url, reply_text):
        """Worker thread for bulk reply operations"""
        try:
            for i, acc in enumerate(selected_accounts):
                # Update GUI from main thread
                self.after(0, lambda acc=acc, i=i: self.log(f"[{acc.label}] Sending reply... ({i+1}/{len(selected_accounts)})"))
                
                success, msg = reply_to_tweet(acc, tweet_url, reply_text)
                
                # Update GUI from main thread
                if success:
                    self.after(0, lambda acc=acc, msg=msg: self.log(f"[{acc.label}] ✅ {msg}"))
                else:
                    self.after(0, lambda acc=acc, msg=msg: self.log(f"[{acc.label}] {msg}", is_error=True))
                
                # Add delay between accounts
                if i < len(selected_accounts) - 1:
                    time.sleep(2)
                    
        except Exception as e:
            self.after(0, lambda e=e: self.log(f"Error during bulk reply: {e}", is_error=True))
        finally:
            # Re-enable button
            self.after(0, lambda: self.update_button_state(True))
            self.after(0, lambda: setattr(self, 'is_processing', False)) 