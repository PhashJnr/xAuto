import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
from constants import COLOR_TAUPE, COLOR_DARK, COLOR_WHITE
from account_manager import SeleniumAccount, save_accounts
from selenium_manager import open_browser_with_profile, get_account_status_and_avatar
import shutil
import os
import threading
import requests
import csv
import time
import pickle
import json

class AccountsPanel(ttk.Frame):
    def __init__(self, parent, accounts):
        super().__init__(parent)
        self.parent = parent
        self.accounts = accounts
        self.log_text = None
        self.status_labels = {}  # Map acc.label to status label widget
        self.selected_tag = tk.StringVar(value='All')
        self.tag_filter_dropdown = None
        # State persistence
        self.state = {
            'selected_tag': 'All',
            'log_messages': []
        }

    def build_panel(self):
        # Initialize browser drivers dict
        self.browser_drivers = {}
        self._setting_up_proxies = False  # Flag to prevent multiple executions
        
        # Title
        title = tk.Label(self, text="Accounts", font=('Segoe UI', 16, 'bold'), bg=COLOR_TAUPE, fg=COLOR_DARK)
        title.pack(anchor='nw', padx=20, pady=(20, 10))
        
        # Control buttons
        controls_frame = ttk.Frame(self)
        controls_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Button(controls_frame, text="Add Account", command=self.add_account_dialog).pack(side='left', padx=5)
        ttk.Button(controls_frame, text="Import Accounts", command=self.import_accounts_dialog).pack(side='left', padx=5)
        ttk.Button(controls_frame, text="Export Accounts", command=self.export_accounts_dialog).pack(side='left', padx=5)
        ttk.Button(controls_frame, text="Check Status", command=self.check_selected_accounts_status).pack(side='left', padx=5)
        ttk.Button(controls_frame, text="Bulk Open", command=self.bulk_open_browsers).pack(side='left', padx=5)
        ttk.Button(controls_frame, text="Bulk Close", command=self.bulk_close_browsers).pack(side='left', padx=5)
        ttk.Button(controls_frame, text="Verify Profiles", command=self.verify_all_profiles).pack(side='left', padx=5)
        ttk.Button(controls_frame, text="Setup FoxyProxy", command=self.setup_foxyproxy_for_all).pack(side='left', padx=5)
        
        # Setup Proxies button (in controls frame so it doesn't get recreated)
        self.setup_proxies_btn = ttk.Button(controls_frame, text="Setup Proxies", command=self.setup_proxy_plugins)
        self.setup_proxies_btn.pack(side='left', padx=5)
        
        # Create table frame
        self.accounts_table_frame = ttk.Frame(self)
        self.accounts_table_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Create table headers
        headers = ['Label', 'Username', 'Status', 'Tags', 'Proxy', 'Browser', 'Actions']
        
        for i, header in enumerate(headers):
            header_label = ttk.Label(self.accounts_table_frame, text=header, font=('Arial', 10, 'bold'))
            header_label.grid(row=0, column=i, padx=5, pady=5, sticky='w')
            header_label.is_header = True # Mark headers so they don't get destroyed during refresh
        
        # Configure column widths for better display
        self.accounts_table_frame.grid_columnconfigure(0, minsize=80)  # Label
        self.accounts_table_frame.grid_columnconfigure(1, minsize=120) # Username
        self.accounts_table_frame.grid_columnconfigure(2, minsize=80)  # Status
        self.accounts_table_frame.grid_columnconfigure(3, minsize=120) # Tags (increased for button)
        self.accounts_table_frame.grid_columnconfigure(4, minsize=100) # Proxy
        self.accounts_table_frame.grid_columnconfigure(5, minsize=80)  # Browser
        self.accounts_table_frame.grid_columnconfigure(6, minsize=120) # Actions (reduced for compact buttons)
        
        # Populate table with accounts
        self.refresh_accounts_table()
        
        # Log frame
        log_frame = ttk.Frame(self)
        log_frame.pack(fill='x', pady=(10, 0))
        
        ttk.Label(log_frame, text="Log:").pack(anchor='w')
        self.log_text = tk.Text(log_frame, height=6, bg=COLOR_DARK, fg=COLOR_WHITE, state='disabled')
        self.log_text.pack(fill='x', pady=(5, 0))
        
        # Restore state
        self.restore_log_messages()
        
        # Initial table population (redundant, but harmless after first call)
        self.refresh_accounts_table()
        
        # Start browser polling
        self.start_browser_polling()

    def on_tag_filter_change(self, event=None):
        """Handle tag filter change and save state"""
        self.state['selected_tag'] = self.selected_tag.get()
        self.refresh_accounts_table()

    def restore_log_messages(self):
        """Restore log messages from state"""
        for message in self.state['log_messages']:
            self.log_text.config(state='normal')
            self.log_text.insert('end', message + '\n')
            self.log_text.see('end')
            self.log_text.config(state='disabled')

    def refresh_accounts_table(self):
        # Clear previous table rows (but keep headers)
        for widget in self.accounts_table_frame.winfo_children():
            if hasattr(widget, 'is_header') and widget.is_header:
                continue  # Skip headers
            widget.destroy()
        
        # Filter accounts by tag
        if hasattr(self, 'selected_tag') and self.selected_tag is not None:
            tag = self.selected_tag.get()
        else:
            tag = 'All'
        filtered_accounts = [a for a in self.accounts if tag == 'All' or tag in a.tags]
        
        self.selected_accounts = {}
        self.browser_status_labels = {}
        self.browser_buttons = {}
        
        for i, acc in enumerate(filtered_accounts):
            # Label
            label_lbl = ttk.Label(self.accounts_table_frame, text=acc.label)
            label_lbl.grid(row=i+1, column=0, padx=5, pady=2, sticky='w')
            
            # Username
            username_lbl = ttk.Label(self.accounts_table_frame, text=acc.username)
            username_lbl.grid(row=i+1, column=1, padx=5, pady=2, sticky='w')
            
            # Status
            status_text = acc.status if acc.status else "Unknown"
            status_fg = 'green' if acc.status == 'Active' else ('red' if acc.status == 'Inactive' else 'gray')
            status_lbl = ttk.Label(self.accounts_table_frame, text=status_text, foreground=status_fg)
            status_lbl.grid(row=i+1, column=2, padx=5, pady=2, sticky='w')
            self.status_labels[acc.label] = status_lbl
            
            # Tags display with edit button
            tags_frame = ttk.Frame(self.accounts_table_frame)
            tags_frame.grid(row=i+1, column=3, padx=5, pady=2, sticky='w')
            
            tags_str = ", ".join(acc.tags) if acc.tags else "None"
            tags_lbl = ttk.Label(tags_frame, text=tags_str)
            tags_lbl.pack(side='left')
            
            # Tags edit button
            def edit_tags(account):
                self.edit_tags_dialog(account, tags_lbl)
            
            tags_btn = ttk.Button(tags_frame, text="✏️", width=3,
                                command=lambda a=acc: edit_tags(a))
            tags_btn.pack(side='right', padx=(5, 0))
            
            # Proxy display
            proxy_str = acc.proxy if acc.proxy else "None"
            proxy_lbl = ttk.Label(self.accounts_table_frame, text=proxy_str)
            proxy_lbl.grid(row=i+1, column=4, padx=5, pady=2, sticky='w')
            
            # Browser Status indicator
            status_dot = "🟢" if acc.label in self.browser_drivers else "⚪"
            browser_status_lbl = ttk.Label(self.accounts_table_frame, text=status_dot, font=("Segoe UI", 12))
            browser_status_lbl.grid(row=i+1, column=5, padx=5, pady=2, sticky='w')
            self.browser_status_labels[acc.label] = browser_status_lbl
            
            # Actions frame (contains all action buttons) - compact layout
            actions_frame = ttk.Frame(self.accounts_table_frame)
            actions_frame.grid(row=i+1, column=6, padx=5, pady=2, sticky='w')
            
            print(f"Creating actions frame for account: {acc.label}")
            
            # Delete button (compact)
            def confirm_delete(account):
                result = messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete account '{account.label}'?\n\nThis will permanently remove the account and all associated data.")
                if result:
                    self.delete_account(account)
            
            del_btn = tk.Button(actions_frame, text="🗑️", 
                               command=lambda a=acc: confirm_delete(a),
                               bg='#ff4444', fg='white', 
                               font=('Arial', 8, 'bold'),
                               relief='raised', bd=1, width=4)
            del_btn.pack(side='left', padx=1)
            
            print(f"✅ Created delete button for account: {acc.label}")
            
            # Open/Close Browser button (compact)
            open_btn = ttk.Button(actions_frame, text="🌐", width=4)
            def toggle_browser(a=acc, btn=open_btn):
                if a.label in self.browser_drivers:
                    try:
                        self.browser_drivers[a.label].quit()
                    except Exception:
                        pass
                    from selenium_manager import log_browser_close
                    log_browser_close(a, "closed")
                    del self.browser_drivers[a.label]
                    btn.config(text="🌐")
                    self.log(f"Closed browser for {a.label}")
                else:
                    self.log(f"Opening browser for {a.label}...")
                    try:
                        from selenium_manager import open_browser_with_profile
                        driver = open_browser_with_profile(a)
                        if driver:
                            self.browser_drivers[a.label] = driver
                            btn.config(text="❌")
                            self.log(f"✅ Successfully opened browser for {a.label}")
                        else:
                            self.log(f"❌ Failed to open browser for {a.label}", is_error=True)
                    except Exception as e:
                        self.log(f"❌ Error opening browser for {a.label}: {e}", is_error=True)
            open_btn.config(text="❌" if acc.label in self.browser_drivers else "🌐", command=toggle_browser)
            open_btn.pack(side='left', padx=1)
            self.browser_buttons[acc.label] = open_btn
            
            # Manage Proxy button (compact)
            proxy_btn = ttk.Button(actions_frame, text="🔧", width=4,
                                 command=lambda a=acc: self.assign_proxy_to_account(a.label))
            proxy_btn.pack(side='left', padx=1)
            
            # Save Cookies button (compact)
            def save_cookies_for_account(account):
                from selenium_manager import manual_save_cookies
                self.log(f"💾 Manually saving cookies for {account.label}...")
                success = manual_save_cookies(account)
                if success:
                    self.log(f"✅ Cookies saved for {account.label}")
                else:
                    self.log(f"❌ Failed to save cookies for {account.label}", is_error=True)
            
            save_cookies_btn = ttk.Button(actions_frame, text="💾", width=4,
                                        command=lambda a=acc: save_cookies_for_account(a))
            save_cookies_btn.pack(side='left', padx=1)
            
            print(f"✅ Created browser button for account: {acc.label}")
            print(f"📊 Actions frame children count: {len(actions_frame.winfo_children())}")

    def start_browser_polling(self):
        """Start polling for browser status updates"""
        try:
            # Only poll if the panel is visible and table exists
            if hasattr(self, 'accounts_table_frame') and self.winfo_exists():
                # Check browser status for all accounts
                from account_manager import load_accounts
                accounts = load_accounts()
                
                if accounts:
                    # Update browser status in table (but don't rebuild everything)
                    self.update_browser_status_only()
                
                # Schedule next poll
                self.after(5000, self.start_browser_polling)  # Poll every 5 seconds
            else:
                # Stop polling if panel is not visible
                return
                
        except Exception as e:
            print(f"Error in browser polling: {e}")
            # Continue polling even if there's an error
            self.after(5000, self.start_browser_polling)
    
    def update_browser_status_only(self):
        """Update only browser status without rebuilding the entire table"""
        try:
            # Update browser status labels directly using stored references
            for account_label, status_label in self.browser_status_labels.items():
                if status_label is not None:
                    try:
                        status = "🟢 Open" if account_label in self.browser_drivers else "🔴 Closed"
                        status_label.config(text=status)
                    except Exception as e:
                        print(f"⚠️ Error updating browser status for {account_label}: {e}")
        except Exception as e:
            print(f"Error updating browser status: {e}")

    def log(self, message, is_error=False):
        if is_error:
            message = f"❌ {message}"
        
        # Check if log_text exists before using it
        if not hasattr(self, 'log_text') or self.log_text is None:
            print(f"⚠️ Log text widget not available: {message}")
            return
            
        try:
            self.log_text.config(state='normal')
            self.log_text.insert('end', message + '\n')
            self.log_text.see('end')
            self.log_text.config(state='disabled')
            # Save to state
            self.state['log_messages'].append(message)
            # Keep only last 100 messages to prevent memory issues
            if len(self.state['log_messages']) > 100:
                self.state['log_messages'] = self.state['log_messages'][-100:]
        except Exception as e:
            print(f"⚠️ Error logging message: {e}")
            print(f"Original message: {message}")

    def log_message(self, message):
        """Add message to log"""
        # Check if log_text exists before using it
        if not hasattr(self, 'log_text') or self.log_text is None:
            print(f"⚠️ Log text widget not available: {message}")
            return
            
        try:
            self.log_text.config(state='normal')
            self.log_text.insert('end', f"{message}\n")
            self.log_text.see('end')
            self.log_text.config(state='disabled')
        except Exception as e:
            print(f"Error logging message: {e}")
            print(f"Original message: {message}")
    
    def open_browser_for_account(self, acc):
        """Open browser for a specific account"""
        try:
            from selenium_manager import get_global_driver_manager
            
            self.log_message(f"🚀 Opening browser for {acc.label}...")
            
            # Open browser in a separate thread
            import threading
            def open_browser():
                try:
                    # Use the driver manager to get/create driver
                    driver = get_global_driver_manager().get_driver(acc)
                    if driver:
                        self.browser_drivers[acc.label] = driver
                        self.log_message(f"✅ Browser opened for {acc.label}")
                    else:
                        self.log_message(f"❌ Failed to open browser for {acc.label}")
                except Exception as e:
                    self.log_message(f"❌ Error opening browser for {acc.label}: {e}")
            
            thread = threading.Thread(target=open_browser)
            thread.daemon = True
            thread.start()
            
        except Exception as e:
            self.log_message(f"❌ Error opening browser: {e}")
    
    def close_browser_for_account(self, acc):
        """Close browser for a specific account"""
        try:
            from selenium_manager import get_global_driver_manager
            
            # Use the driver manager to close the driver (this will save cookies)
            driver_manager = get_global_driver_manager()
            driver_manager.close_driver(acc)
            
            # Remove from local tracking
            if acc.label in self.browser_drivers:
                del self.browser_drivers[acc.label]
            
            self.log_message(f"✅ Browser closed for {acc.label}")
                
        except Exception as e:
            self.log_message(f"❌ Error closing browser: {e}")

    def open_browser_account(self, acc):
        self.log(f"Opening browser for [{acc.label}]...")
        # Deprecated: now handled by toggle_browser
        pass

    def edit_account_dialog(self, acc):
        """Edit existing account"""
        self.account_form_dialog("Edit Account", acc)

    def add_account_dialog(self):
        """Add new account"""
        self.account_form_dialog("Add Account")

    def delete_account_dialog(self):
        # This method is deprecated since we now use a table with individual delete buttons
        # Users can delete accounts by editing them and removing them
        messagebox.showinfo("Delete Account", "To delete an account, edit it and remove all data, or manually edit accounts.json")

    def get_selected_account_index(self):
        # Since we're using a table with checkboxes now, this method is deprecated
        # Return None as we handle selection differently
        return None

    def account_form_dialog(self, title, acc=None):
        """Single dialog for adding/editing accounts with all fields"""
        dialog = tk.Toplevel(self.parent)
        dialog.title(title)
        dialog.grab_set()
        dialog.geometry("400x350")
        
        # Center the dialog
        dialog.transient(self.parent)
        dialog.grab_set()
        
        # Main frame
        main_frame = ttk.Frame(dialog, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Label
        ttk.Label(main_frame, text="Label:").grid(row=0, column=0, sticky='w', pady=2)
        label_entry = ttk.Entry(main_frame, width=40)
        label_entry.grid(row=0, column=1, columnspan=2, sticky='ew', pady=2, padx=(5, 0))
        
        # Username
        ttk.Label(main_frame, text="Username:").grid(row=1, column=0, sticky='w', pady=2)
        username_entry = ttk.Entry(main_frame, width=40)
        username_entry.grid(row=1, column=1, columnspan=2, sticky='ew', pady=2, padx=(5, 0))
        
        # Password
        ttk.Label(main_frame, text="Password:").grid(row=2, column=0, sticky='w', pady=2)
        password_frame = ttk.Frame(main_frame)
        password_frame.grid(row=2, column=1, columnspan=2, sticky='ew', pady=2, padx=(5, 0))
        
        password_entry = ttk.Entry(password_frame, width=30, show='*')
        password_entry.pack(side='left', fill='x', expand=True)
        
        # Password visibility toggle
        password_var = tk.BooleanVar()
        def toggle_password():
            password_entry.config(show='' if password_var.get() else '*')
        
        password_check = ttk.Checkbutton(password_frame, text="Show", variable=password_var, command=toggle_password)
        password_check.pack(side='right', padx=(5, 0))
        
        # Tags
        ttk.Label(main_frame, text="Tags (comma separated):").grid(row=3, column=0, sticky='w', pady=2)
        tags_entry = ttk.Entry(main_frame, width=40)
        tags_entry.grid(row=3, column=1, columnspan=2, sticky='ew', pady=2, padx=(5, 0))
        
        # Proxy
        ttk.Label(main_frame, text="Proxy (e.g., socks5://127.0.0.1:9050):").grid(row=4, column=0, sticky='w', pady=2)
        proxy_entry = ttk.Entry(main_frame, width=40)
        proxy_entry.grid(row=4, column=1, columnspan=2, sticky='ew', pady=2, padx=(5, 0))
        
        # Fill existing data if editing
        if acc:
            label_entry.insert(0, acc.label)
            username_entry.insert(0, acc.username)
            if acc.tags:
                tags_entry.insert(0, ', '.join(acc.tags))
            if acc.proxy:
                proxy_entry.insert(0, acc.proxy)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=5, column=0, columnspan=3, pady=20)
        
        def on_save():
            label = label_entry.get().strip()
            username = username_entry.get().strip()
            password = password_entry.get().strip()
            
            # Parse tags
            tags = [tag.strip() for tag in tags_entry.get().split(',') if tag.strip()] if tags_entry.get() else []
            
            # Parse proxy
            proxy = proxy_entry.get().strip()
            
            if not label or not username:
                self.log("Label and Username are required.", is_error=True)
                return
            
            # Check for duplicate username (except when editing the same account)
            existing_acc = next((a for a in self.accounts if a.username == username), None)
            if existing_acc and (not acc or existing_acc != acc):
                self.log(f"Username '{username}' already exists.", is_error=True)
                return
            
            if acc:
                # Update existing account
                acc.label = label
                acc.username = username
                acc.tags = tags
                # Password is not persisted but stored in memory
                acc.password = password
                acc.proxy = proxy
                self.log(f"Updated account: {label}")
            else:
                # Create new account
                new_acc = SeleniumAccount(label, username, password=password, tags=tags, proxy=proxy)
                self.accounts.append(new_acc)
                self.log(f"Added account: {label}")
            
            save_accounts(self.accounts)
            self.refresh_accounts_table()
            dialog.destroy()
        
        def on_cancel():
            dialog.destroy()
        
        ttk.Button(button_frame, text="Save", command=on_save).pack(side='left', padx=(0, 10))
        ttk.Button(button_frame, text="Cancel", command=on_cancel).pack(side='left')
        
        # Add browser selection toggle
        browser_frame = ttk.Frame(button_frame)
        browser_frame.pack(side='left', padx=5)
        
        ttk.Label(browser_frame, text="Browser:").pack(side='left')
        
        self.browser_var = tk.StringVar(value="firefox")
        browser_combo = ttk.Combobox(browser_frame, textvariable=self.browser_var, 
                                    values=["firefox", "chrome"], width=10, state="readonly")
        browser_combo.pack(side='left', padx=5)
        browser_combo.bind('<<ComboboxSelected>>', self.on_browser_change)

    def on_browser_change(self, event=None):
        """Handle browser selection change"""
        browser = self.browser_var.get()
        if browser == "firefox":
            os.environ['USE_FIREFOX'] = 'true'
            print("🔧 Switched to Firefox")
        else:
            os.environ['USE_FIREFOX'] = 'false'
            print("🔧 Switched to Chrome")

    def manual_login_selected(self):
        # This method is deprecated since we now use a table with individual action buttons
        # Users can open browsers and login manually through the table interface
        self.log("To login manually, use the 'Open' button for an account, then login in the browser.")

    def delete_account(self, acc):
        """Delete account and all associated data"""
        try:
            self.log(f"🗑️ Starting deletion of account: {acc.label}")
            self.log(f"📊 Accounts before deletion: {len(self.accounts)}")
            
            # Remove from accounts list
            if acc in self.accounts:
                self.accounts.remove(acc)
                save_accounts(self.accounts)
                self.log(f"✅ Removed account '{acc.label}' from accounts list")
                self.log(f"📊 Accounts after deletion: {len(self.accounts)}")
            else:
                self.log(f"⚠️ Account '{acc.label}' not found in accounts list")
            
            # Close browser if open
            if acc.label in self.browser_drivers:
                try:
                    self.browser_drivers[acc.label].quit()
                    del self.browser_drivers[acc.label]
                    self.log(f"✅ Closed browser for {acc.label}")
                except Exception as e:
                    self.log(f"❌ Error closing browser: {e}", is_error=True)
            
            # Remove Chrome profile directory (complete cleanup)
            profile_dir = os.path.abspath(os.path.join('chrome_profiles', acc.label))
            if os.path.exists(profile_dir):
                try:
                    shutil.rmtree(profile_dir)
                    self.log(f"✅ Deleted Chrome profile directory for {acc.label}")
                except Exception as e:
                    self.log(f"❌ Error deleting Chrome profile: {e}", is_error=True)
            else:
                self.log(f"⚠️ Chrome profile directory not found for {acc.label}")
            
            # Remove cookies file
            cookie_path = acc.get_cookie_path()
            if os.path.exists(cookie_path):
                try:
                    os.remove(cookie_path)
                    self.log(f"✅ Deleted cookies for {acc.label}")
                except Exception as e:
                    self.log(f"❌ Error deleting cookies: {e}", is_error=True)
            else:
                self.log(f"⚠️ Cookie file not found for {acc.label}")
            
            # Remove from browser buttons and status labels
            if acc.label in self.browser_buttons:
                del self.browser_buttons[acc.label]
            if acc.label in self.browser_status_labels:
                del self.browser_status_labels[acc.label]
            if acc.label in self.status_labels:
                del self.status_labels[acc.label]
            
            self.log(f"✅ Account '{acc.label}' completely deleted")
            
            # Refresh the table to update UI
            self.log(f"🔄 Refreshing table with {len(self.accounts)} accounts")
            self.refresh_accounts_table()
            
        except Exception as e:
            self.log(f"❌ Error deleting account {acc.label}: {e}", is_error=True)

    def check_all_accounts_status_and_avatar(self):
        for acc in self.accounts:
            self.update_account_status_and_avatar(acc)

    def check_selected_accounts_status(self):
        for acc in self.accounts:
            self.update_account_status_and_avatar(acc, persist=True)

    def update_account_status_and_avatar(self, acc, persist=False):
        def worker():
            status, avatar_url = get_account_status_and_avatar(acc, headless=False)
            acc.status = status
            acc.avatar_url = avatar_url
            
            # Check if the status label still exists before updating
            if acc.label in self.status_labels and self.status_labels[acc.label] is not None:
                try:
                    if status == 'Active':
                        self.status_labels[acc.label].config(text='Active', foreground='green')
                    else:
                        self.status_labels[acc.label].config(text='Inactive', foreground='red')
                except Exception as e:
                    print(f"⚠️ Error updating status label for {acc.label}: {e}")
            
            if persist:
                from account_manager import save_accounts
                save_accounts(self.accounts)
        threading.Thread(target=worker, daemon=True).start() 

    def bulk_open_browsers(self):
        for acc in self.accounts:
            if acc.label not in self.browser_drivers:
                from selenium_manager import open_browser_with_profile
                driver = open_browser_with_profile(acc)
                self.browser_drivers[acc.label] = driver
                btn = self.browser_buttons.get(acc.label)
                if btn and btn is not None:
                    try:
                        btn.config(text="Close")
                    except Exception as e:
                        print(f"⚠️ Error updating browser button for {acc.label}: {e}")
                lbl = self.browser_status_labels.get(acc.label)
                if lbl and lbl is not None:
                    try:
                        lbl.config(text="🟢")
                    except Exception as e:
                        print(f"⚠️ Error updating browser status for {acc.label}: {e}")

    def bulk_close_browsers(self):
        from selenium_manager import get_global_driver_manager
        
        driver_manager = get_global_driver_manager()
        
        for acc in self.accounts:
            if acc.label in self.browser_drivers:
                try:
                    # Use driver manager to close (this will save cookies)
                    driver_manager.close_driver(acc)
                except Exception as e:
                    print(f"⚠️ Error closing browser for {acc.label}: {e}")
                
                from selenium_manager import log_browser_close
                log_browser_close(acc, "closed")
                del self.browser_drivers[acc.label]
                
                btn = self.browser_buttons.get(acc.label)
                if btn and btn is not None:
                    try:
                        btn.config(text="Open")
                    except Exception as e:
                        print(f"⚠️ Error updating browser button for {acc.label}: {e}")
                lbl = self.browser_status_labels.get(acc.label)
                if lbl and lbl is not None:
                    try:
                        lbl.config(text="⚪")
                    except Exception as e:
                        print(f"⚠️ Error updating browser status for {acc.label}: {e}")
        self.log("✅ All browser sessions closed")

    def verify_all_profiles(self):
        """Verify that all Chrome profiles are using the correct approach"""
        def worker():
            try:
                self.log("🔍 Verifying all Chrome profiles...")
                
                for acc in self.accounts:
                    self.log(f"📋 Checking profile for {acc.label}...")
                    
                    # Import the verification function
                    from selenium_manager import check_profile_session_data, cleanup_chrome_profile_cache
                    
                    # Clean up cache directories
                    cleanup_chrome_profile_cache(acc)
                    
                    # Check session data
                    has_session = check_profile_session_data(acc)
                    
                    if has_session:
                        self.log(f"✅ {acc.label}: Profile has session data")
                    else:
                        self.log(f"⚠️ {acc.label}: No session data found")
                
                self.log("✅ Profile verification completed")
                
            except Exception as e:
                self.log(f"❌ Error verifying profiles: {e}")
        
        threading.Thread(target=worker, daemon=True).start()

    def setup_foxyproxy_for_all(self):
        """Set up FoxyProxy extension for all accounts"""
        def worker():
            try:
                self.log("🔧 Setting up FoxyProxy for all accounts...")
                
                from selenium_manager import setup_foxyproxy_for_account
                
                for acc in self.accounts:
                    self.log(f"📋 Setting up FoxyProxy for {acc.label}...")
                    
                    success = setup_foxyproxy_for_account(acc)
                    
                    if success:
                        self.log(f"✅ FoxyProxy setup completed for {acc.label}")
                    else:
                        self.log(f"❌ FoxyProxy setup failed for {acc.label}")
                
                self.log("✅ FoxyProxy setup completed for all accounts")
                
            except Exception as e:
                self.log(f"❌ Error setting up FoxyProxy: {e}")
        
        threading.Thread(target=worker, daemon=True).start()

    def edit_tags_dialog(self, acc, label_widget):
        import tkinter.simpledialog
        tags_str = ", ".join(acc.tags) if acc.tags else ""
        new_tags = tkinter.simpledialog.askstring("Edit Tags", f"Enter tags for {acc.label} (comma-separated):", initialvalue=tags_str)
        if new_tags is not None:
            acc.tags = [t.strip() for t in new_tags.split(",") if t.strip()]
            label_widget.config(text=", ".join(acc.tags))
            from account_manager import save_accounts
            save_accounts(self.accounts) 

    def quick_send_dm(self, acc):
        recipient = simpledialog.askstring("Send DM", f"Recipient username for {acc.label}:")
        if recipient:
            message = simpledialog.askstring("Send DM", "Message:")
            if message:
                self.log(f"Sending DM from [{acc.label}] to {recipient}...")
                def worker():
                    from selenium_manager import send_dm
                    success, msg = send_dm(acc, recipient, message)
                    if success:
                        self.log(f"✅ DM sent successfully from [{acc.label}]")
                    else:
                        self.log(f"❌ Failed to send DM from [{acc.label}]: {msg}", is_error=True)
                threading.Thread(target=worker, daemon=True).start()

    def quick_reply_tweet(self, acc):
        tweet_url = simpledialog.askstring("Reply to Tweet", f"Tweet URL for {acc.label}:")
        if tweet_url:
            reply_text = simpledialog.askstring("Reply to Tweet", "Reply text:")
            if reply_text:
                self.log(f"Replying to tweet from [{acc.label}]...")
                def worker():
                    from selenium_manager import reply_to_tweet
                    success, msg = reply_to_tweet(acc, tweet_url, reply_text)
                    if success:
                        self.log(f"✅ Reply posted successfully from [{acc.label}]")
                    else:
                        self.log(f"❌ Failed to reply from [{acc.label}]: {msg}", is_error=True)
                threading.Thread(target=worker, daemon=True).start()

    def quick_change_bio(self, acc):
        new_bio = simpledialog.askstring("Change Bio", f"New bio for {acc.label}:")
        if new_bio:
            self.log(f"Changing bio for [{acc.label}]...")
            def worker():
                from selenium_manager import change_bio
                success, msg = change_bio(acc, new_bio)
                if success:
                    self.log(f"✅ Bio updated successfully for [{acc.label}]")
                else:
                    self.log(f"❌ Failed to update bio for [{acc.label}]: {msg}", is_error=True)
            threading.Thread(target=worker, daemon=True).start()

    def quick_change_pic(self, acc):
        from tkinter import filedialog
        image_path = filedialog.askopenfilename(
            title=f"Select profile picture for {acc.label}",
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.gif *.bmp")]
        )
        if image_path:
            self.log(f"Changing profile picture for [{acc.label}]...")
            def worker():
                from selenium_manager import change_profile_pic
                success, msg = change_profile_pic(acc, image_path)
                if success:
                    self.log(f"✅ Profile picture updated successfully for [{acc.label}]")
                else:
                    self.log(f"❌ Failed to update profile picture for [{acc.label}]: {msg}", is_error=True)
            threading.Thread(target=worker, daemon=True).start() 

    def import_accounts_dialog(self):
        """Import accounts from TXT file with username;password format and auto-login"""
        file_path = filedialog.askopenfilename(
            title="Select TXT file to import",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if not file_path:
            return
        
        try:
            imported_accounts = []
            with open(file_path, 'r', encoding='utf-8') as file:
                for line_num, line in enumerate(file, 1):
                    line = line.strip()
                    if not line or line.startswith('#'):  # Skip empty lines and comments
                        continue
                    
                    # Extract username and password from format: username;password
                    # Handle cases where there might be email as third field: username;password;email
                    if ';' in line:
                        parts = line.split(';')
                        if len(parts) >= 2:
                            username = parts[0].strip()
                            password = parts[1].strip()
                        else:
                            self.log(f"Invalid format on line {line_num}: {line}", is_error=True)
                            continue
                    else:
                        # Fallback: assume line is username only
                        username = line.strip()
                        password = ""
                    
                    if not username:
                        self.log(f"Empty username on line {line_num}", is_error=True)
                        continue
                    
                    # Check for duplicate username
                    if any(acc.username == username for acc in self.accounts):
                        self.log(f"Skipping duplicate username: {username}", is_error=True)
                        continue
                    
                    # Create account with username as label
                    label = username
                    acc = SeleniumAccount(label, username, password=password)
                    imported_accounts.append(acc)
            
            if not imported_accounts:
                self.log("No valid accounts found in the file", is_error=True)
                return
            
            # Start the auto-login process
            self.log(f"Found {len(imported_accounts)} accounts to import. Starting auto-login process...")
            self.auto_login_imported_accounts(imported_accounts)
                
        except Exception as e:
            self.log(f"Error importing accounts: {e}", is_error=True)

    def auto_login_imported_accounts(self, accounts_to_import):
        """Automatically login imported accounts one at a time"""
        def worker():
            for i, acc in enumerate(accounts_to_import, 1):
                self.log(f"Processing account {i}/{len(accounts_to_import)}: {acc.username}")
                
                try:
                    # Add account to list first
                    self.accounts.append(acc)
                    save_accounts(self.accounts)
                    self.refresh_accounts_table()
                    
                    # Open browser for manual login
                    self.log(f"Opening browser for {acc.username}...")
                    driver = open_browser_with_profile(acc)
                    
                    if not driver:
                        self.log(f"Failed to open browser for {acc.username}", is_error=True)
                        continue
                    
                    # Navigate to login page
                    driver.get('https://x.com/login')
                    self.log(f"Please log in manually for {acc.username}")
                    
                    # Wait for user to complete login
                    input(f"Press Enter in terminal after logging in for {acc.username}...")
                    
                    # Wait 15-30 seconds to verify login success
                    self.log(f"Verifying login success for {acc.username}...")
                    time.sleep(20)  # 20 second delay
                    
                    # Check if login was successful
                    driver.get('https://x.com/home')
                    time.sleep(5)
                    
                    if 'login' in driver.current_url:
                        self.log(f"Login verification failed for {acc.username} - still on login page", is_error=True)
                        driver.quit()
                        continue
                    
                    # Save cookies
                    cookies = driver.get_cookies()
                    cookie_path = acc.get_cookie_path()
                    os.makedirs(os.path.dirname(cookie_path), exist_ok=True)
                    with open(cookie_path, 'wb') as f:
                        pickle.dump(cookies, f)
                    
                    # Update account status
                    acc.status = 'Active'
                    save_accounts(self.accounts)
                    self.refresh_accounts_table()
                    
                    self.log(f"✅ Successfully imported and logged in {acc.username}")
                    
                    # Close browser
                    driver.quit()
                    
                    # Small delay before next account
                    time.sleep(3)
                    
                except Exception as e:
                    self.log(f"Error processing {acc.username}: {e}", is_error=True)
                    try:
                        driver.quit()
                    except:
                        pass
                    continue
            
            self.log(f"Import process completed. {len(accounts_to_import)} accounts processed.")
        
        # Run in background thread
        threading.Thread(target=worker, daemon=True).start()

    def export_accounts_dialog(self):
        """Export accounts to a file"""
        file_path = filedialog.asksaveasfilename(
            title="Export Accounts",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'w') as f:
                    json.dump([acc.to_dict() for acc in self.accounts], f, indent=2)
                self.log(f"Exported {len(self.accounts)} accounts to {file_path}")
            except Exception as e:
                self.log(f"Error exporting accounts: {e}", is_error=True) 

    def setup_proxy_plugins(self):
        """Setup proxy plugins for all accounts"""
        try:
            # Prevent multiple simultaneous executions
            if self._setting_up_proxies:
                self.log_message("⏳ Proxy setup already in progress...")
                return
            
            self._setting_up_proxies = True
            self.setup_proxies_btn.config(state='disabled')
            
            self.log_message("🔧 Setting up proxy plugins for all accounts...")
            
            from create_proxy_plugin import setup_proxy_for_all_accounts
            success_count = setup_proxy_for_all_accounts()
            
            if success_count > 0:
                self.log_message(f"✅ Created {success_count} proxy plugins")
            else:
                self.log_message("ℹ️ No proxy plugins created (no proxies configured)")
            
            self.setup_proxies_btn.config(state='normal')
            self._setting_up_proxies = False
                
        except Exception as e:
            self.log_message(f"❌ Error setting up proxy plugins: {e}")
            self.setup_proxies_btn.config(state='normal')
            self._setting_up_proxies = False
    
    def assign_proxy_to_account(self, account_label):
        """Assign proxy to a specific account"""
        try:
            # Create proxy assignment dialog
            dialog = tk.Toplevel(self)
            dialog.title(f"Manage Proxy - {account_label}")
            dialog.geometry("600x400")
            dialog.transient(self)
            dialog.grab_set()
            
            # Main frame
            main_frame = ttk.Frame(dialog)
            main_frame.pack(fill='both', expand=True, padx=20, pady=20)
            
            # Current proxy status
            status_frame = ttk.LabelFrame(main_frame, text="Current Proxy Status")
            status_frame.pack(fill='x', pady=(0, 20))
            
            from account_manager import load_accounts
            accounts = load_accounts()
            current_proxy = None
            for acc in accounts:
                if acc.label == account_label:
                    current_proxy = acc.proxy
                    break
            
            if current_proxy:
                ttk.Label(status_frame, text=f"✅ Proxy configured:", font=('Arial', 10, 'bold')).pack(anchor='w', pady=(10, 5))
                ttk.Label(status_frame, text=current_proxy, font=('Courier', 9)).pack(anchor='w', padx=20)
            else:
                ttk.Label(status_frame, text="❌ No proxy configured", font=('Arial', 10, 'bold')).pack(anchor='w', pady=(10, 5))
            
            # Proxy configuration
            config_frame = ttk.LabelFrame(main_frame, text="Configure Proxy")
            config_frame.pack(fill='x', pady=(0, 20))
            
            ttk.Label(config_frame, text="Proxy URL:").pack(anchor='w', pady=(10, 5))
            proxy_var = tk.StringVar()
            proxy_entry = ttk.Entry(config_frame, textvariable=proxy_var, width=60, font=('Courier', 9))
            proxy_entry.pack(fill='x', pady=(0, 10))
            
            # Examples
            examples_frame = ttk.LabelFrame(main_frame, text="Proxy Format Examples")
            examples_frame.pack(fill='x', pady=(0, 20))
            
            examples = [
                "socks5://username:password@host.com:1080",
                "http://username:password@host.com:8080", 
                "socks5://host.com:1080 (no authentication)",
                "http://host.com:8080 (no authentication)"
            ]
            
            for example in examples:
                ttk.Label(examples_frame, text=f"• {example}", font=('Courier', 8)).pack(anchor='w', padx=10, pady=2)
            
            # Buttons
            button_frame = ttk.Frame(main_frame)
            button_frame.pack(fill='x', pady=(20, 0))
            
            def save_proxy():
                proxy = proxy_var.get().strip()
                if proxy:
                    try:
                        # Update account
                        from account_manager import load_accounts, save_accounts
                        accounts = load_accounts()
                        
                        account_updated = False
                        for acc in accounts:
                            if acc.label == account_label:
                                acc.proxy = proxy
                                account_updated = True
                                break
                        
                        if account_updated:
                            save_accounts(accounts)
                            
                            # Create proxy plugin
                            from create_proxy_plugin import setup_proxy_for_account
                            if setup_proxy_for_account(acc):
                                self.log_message(f"✅ Proxy assigned to {account_label}")
                                # Update the display
                                self.update_proxy_display(account_label, proxy)
                                dialog.destroy()
                            else:
                                self.log_message(f"❌ Failed to create proxy plugin for {account_label}")
                        else:
                            self.log_message(f"❌ Account {account_label} not found")
                        
                    except Exception as e:
                        self.log_message(f"❌ Error saving proxy: {e}")
                else:
                    tk.messagebox.showwarning("Warning", "Please enter a proxy URL")
            
            def clear_proxy():
                try:
                    # Remove proxy from account
                    from account_manager import load_accounts, save_accounts
                    accounts = load_accounts()
                    
                    account_updated = False
                    for acc in accounts:
                        if acc.label == account_label:
                            acc.proxy = None
                            account_updated = True
                            break
                    
                    if account_updated:
                        save_accounts(accounts)
                        self.log_message(f"✅ Proxy removed from {account_label}")
                        # Update the display
                        self.update_proxy_display(account_label, "None")
                        dialog.destroy()
                    else:
                        self.log_message(f"❌ Account {account_label} not found")
                    
                except Exception as e:
                    self.log_message(f"❌ Error clearing proxy: {e}")
            
            def test_proxy():
                proxy = proxy_var.get().strip()
                if not proxy:
                    tk.messagebox.showwarning("Warning", "Please enter a proxy URL to test")
                    return
                
                try:
                    import requests
                    from urllib.parse import urlparse
                    
                    # Parse proxy URL
                    parsed = urlparse(proxy)
                    proxy_dict = {
                        'http': proxy,
                        'https': proxy
                    }
                    
                    # Test with a simple request
                    response = requests.get('http://httpbin.org/ip', proxies=proxy_dict, timeout=10)
                    if response.status_code == 200:
                        ip_info = response.json()
                        tk.messagebox.showinfo("Proxy Test", f"✅ Proxy test successful!\n\nYour IP: {ip_info.get('origin', 'Unknown')}")
                    else:
                        tk.messagebox.showerror("Proxy Test", f"❌ Proxy test failed\nStatus: {response.status_code}")
                        
                except Exception as e:
                    tk.messagebox.showerror("Proxy Test", f"❌ Proxy test failed\nError: {str(e)}")
            
            # Load current proxy if exists
            if current_proxy:
                proxy_var.set(current_proxy)
            
            # Button layout
            ttk.Button(button_frame, text="💾 Save Proxy", command=save_proxy).pack(side='left', padx=(0, 5))
            ttk.Button(button_frame, text="🧪 Test Proxy", command=test_proxy).pack(side='left', padx=5)
            ttk.Button(button_frame, text="🗑️ Clear Proxy", command=clear_proxy).pack(side='left', padx=5)
            ttk.Button(button_frame, text="❌ Cancel", command=dialog.destroy).pack(side='right', padx=(5, 0))
            
        except Exception as e:
            self.log_message(f"❌ Error opening proxy dialog: {e}")
    
    def update_proxy_display(self, account_label, proxy_text):
        """Update proxy display for a specific account without refreshing entire table"""
        try:
            # Find the proxy label for this account and update it
            for widget in self.accounts_table_frame.winfo_children():
                if hasattr(widget, 'grid_info') and widget.grid_info()['row'] > 0:
                    # Find the account row
                    for child in widget.master.winfo_children():
                        if (hasattr(child, 'grid_info') and 
                            child.grid_info()['row'] == widget.grid_info()['row'] and 
                            child.grid_info()['column'] == 1):  # Label column
                            if child.cget("text") == account_label:
                                # Found the account row, now find the proxy column (column 5)
                                for proxy_child in widget.master.winfo_children():
                                    if (hasattr(proxy_child, 'grid_info') and 
                                        proxy_child.grid_info()['row'] == widget.grid_info()['row'] and 
                                        proxy_child.grid_info()['column'] == 5):
                                        # Update proxy display
                                        display_text = proxy_text
                                        if len(display_text) > 30:
                                            display_text = display_text[:27] + "..."
                                        proxy_child.config(text=display_text)
                                        return
        except Exception as e:
            print(f"Error updating proxy display: {e}")
    
    def refresh_accounts_table(self):
        """Refresh the accounts table with current data"""
        try:
            # Only refresh if the table exists and has been built
            if not hasattr(self, 'accounts_table_frame'):
                return
            
            # Initialize browser_buttons if it doesn't exist
            if not hasattr(self, 'browser_buttons'):
                self.browser_buttons = {}
            
            # Initialize other required attributes
            if not hasattr(self, 'selected_accounts'):
                self.selected_accounts = {}
            if not hasattr(self, 'browser_status_labels'):
                self.browser_status_labels = {}
            if not hasattr(self, 'status_labels'):
                self.status_labels = {}
            if not hasattr(self, 'browser_drivers'):
                self.browser_drivers = {}
            
            # Clear existing rows (but keep headers)
            for widget in self.accounts_table_frame.winfo_children():
                if hasattr(widget, 'grid_info') and widget.grid_info()['row'] > 0:
                    widget.destroy()
            
            # Use self.accounts instead of loading from file to maintain synchronization
            accounts = self.accounts
            
            self.log(f"🔄 Refreshing table with {len(accounts)} accounts")
            for acc in accounts:
                self.log(f"📋 Account in list: {acc.label}")
            
            if not accounts:
                return
            
            # Populate table
            for i, acc in enumerate(accounts):
                try:
                    row = i + 1  # Start after headers
                    
                    # Account info
                    ttk.Label(self.accounts_table_frame, text=acc.label).grid(row=row, column=0, padx=5, pady=2, sticky='w')
                    ttk.Label(self.accounts_table_frame, text=acc.username).grid(row=row, column=1, padx=5, pady=2, sticky='w')
                    ttk.Label(self.accounts_table_frame, text=acc.status or "Unknown").grid(row=row, column=2, padx=5, pady=2, sticky='w')
                    
                    # Tags column with button
                    tags_frame = ttk.Frame(self.accounts_table_frame)
                    tags_frame.grid(row=row, column=3, padx=5, pady=2, sticky='w')
                    
                    # Tags display
                    tags_text = ", ".join(acc.tags) if acc.tags else "None"
                    tags_label = ttk.Label(tags_frame, text=tags_text)
                    tags_label.pack(side='left')
                    
                    # Tags edit button
                    def edit_tags(account):
                        self.edit_tags_dialog(account, tags_label)
                    
                    tags_btn = ttk.Button(tags_frame, text="✏️", width=3,
                                        command=lambda a=acc: edit_tags(a))
                    tags_btn.pack(side='right', padx=(5, 0))
                    
                    # Proxy info
                    proxy_text = acc.proxy or "None"
                    if len(proxy_text) > 30:
                        proxy_text = proxy_text[:27] + "..."
                    ttk.Label(self.accounts_table_frame, text=proxy_text).grid(row=row, column=4, padx=5, pady=2, sticky='w')
                    
                    # Browser status
                    browser_status = "🟢 Open" if acc.label in self.browser_drivers else "🔴 Closed"
                    ttk.Label(self.accounts_table_frame, text=browser_status).grid(row=row, column=5, padx=5, pady=2, sticky='w')
                    
                    # Action buttons - reorganized for better fit
                    button_frame = ttk.Frame(self.accounts_table_frame)
                    button_frame.grid(row=row, column=6, padx=5, pady=2, sticky='w')
                    
                    # Delete button (compact)
                    def confirm_delete(account):
                        result = messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete account '{account.label}'?\n\nThis will permanently remove the account and all associated data.")
                        if result:
                            self.delete_account(account)
                    
                    del_btn = tk.Button(button_frame, text="🗑️", 
                                       command=lambda a=acc: confirm_delete(a),
                                       bg='#ff4444', fg='white', 
                                       font=('Arial', 8, 'bold'),
                                       relief='raised', bd=1, width=4)
                    del_btn.pack(side='left', padx=1)
                    
                    # Open/Close Browser button (compact)
                    open_btn = ttk.Button(button_frame, text="🌐", width=4)
                    def toggle_browser(a=acc, btn=open_btn):
                        if a.label in self.browser_drivers:
                            try:
                                self.browser_drivers[a.label].quit()
                            except Exception:
                                pass
                            from selenium_manager import log_browser_close
                            log_browser_close(a, "closed")
                            del self.browser_drivers[a.label]
                            btn.config(text="🌐")
                            self.log(f"Closed browser for {a.label}")
                        else:
                            self.log(f"Opening browser for {a.label}...")
                            try:
                                from selenium_manager import open_browser_with_profile
                                driver = open_browser_with_profile(a)
                                if driver:
                                    self.browser_drivers[a.label] = driver
                                    btn.config(text="❌")
                                    self.log(f"✅ Successfully opened browser for {a.label}")
                                else:
                                    self.log(f"❌ Failed to open browser for {a.label}", is_error=True)
                            except Exception as e:
                                self.log(f"❌ Error opening browser for {a.label}: {e}", is_error=True)
                    open_btn.config(text="❌" if acc.label in self.browser_drivers else "🌐", command=toggle_browser)
                    open_btn.pack(side='left', padx=1)
                    self.browser_buttons[acc.label] = open_btn
                    
                    # Manage Proxy button (compact)
                    proxy_btn = ttk.Button(button_frame, text="🔧", width=4,
                                         command=lambda a=acc: self.assign_proxy_to_account(a.label))
                    proxy_btn.pack(side='left', padx=1)
                    
                    # Save Cookies button (compact)
                    def save_cookies_for_account(account):
                        from selenium_manager import manual_save_cookies
                        self.log(f"💾 Manually saving cookies for {account.label}...")
                        success = manual_save_cookies(account)
                        if success:
                            self.log(f"✅ Cookies saved for {account.label}")
                        else:
                            self.log(f"❌ Failed to save cookies for {account.label}", is_error=True)
                    
                    save_cookies_btn = ttk.Button(button_frame, text="💾", width=4,
                                                command=lambda a=acc: save_cookies_for_account(a))
                    save_cookies_btn.pack(side='left', padx=1)
                    
                except Exception as e:
                    print(f"❌ Error creating row for account {acc.label}: {e}")
                    continue
        except Exception as e:
            import traceback
            print(f"❌ Error refreshing accounts table: {e}")
            print(f"📋 Full traceback:")
            traceback.print_exc() 