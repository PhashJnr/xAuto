import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from constants import COLOR_TAUPE, COLOR_DARK, COLOR_WHITE
import threading
import time
import random
from selenium_manager import get_global_driver_manager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

class LikeRetweetPanel(ttk.Frame):
    def __init__(self, parent, accounts):
        super().__init__(parent)
        self.parent = parent
        self.accounts = accounts
        self.log_text = None
        self.progress_bar = None
        self.progress_label = None
        self.is_running = False
        self.paused = False
        
        # State persistence
        self.state = {
            'tweet_urls': '',
            'min_interval': '10',
            'max_interval': '30',
            'enable_retweet': True,
            'enable_like': True,
            'log_messages': []
        }

    def build_panel(self):
        # Title
        title = tk.Label(self, text="Like and Retweet", font=('Segoe UI', 16, 'bold'), bg=COLOR_TAUPE, fg=COLOR_DARK)
        title.pack(anchor='nw', padx=20, pady=(20, 10))
        
        # Main content frame
        main_frame = ttk.Frame(self)
        main_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        # Left panel - Settings
        left_panel = ttk.LabelFrame(main_frame, text="⚙️ Settings", padding="10")
        left_panel.pack(side='left', fill='y', padx=(0, 10))
        
        # Tweet URLs input
        ttk.Label(left_panel, text="Tweet URLs (one per line):", font=('Segoe UI', 10, 'bold')).pack(anchor='w', pady=(0, 5))
        
        self.tweet_urls_text = scrolledtext.ScrolledText(left_panel, height=8, width=50, wrap='word')
        self.tweet_urls_text.pack(fill='x', pady=(0, 10))
        
        # Time interval settings
        interval_frame = ttk.LabelFrame(left_panel, text="⏱️ Time Intervals", padding="5")
        interval_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Label(interval_frame, text="Min Interval (seconds):").pack(anchor='w')
        self.min_interval_var = tk.StringVar(value=self.state['min_interval'])
        min_interval_entry = ttk.Entry(interval_frame, textvariable=self.min_interval_var, width=10)
        min_interval_entry.pack(anchor='w', pady=(0, 5))
        
        ttk.Label(interval_frame, text="Max Interval (seconds):").pack(anchor='w')
        self.max_interval_var = tk.StringVar(value=self.state['max_interval'])
        max_interval_entry = ttk.Entry(interval_frame, textvariable=self.max_interval_var, width=10)
        max_interval_entry.pack(anchor='w', pady=(0, 5))
        
        # Action options
        actions_frame = ttk.LabelFrame(left_panel, text="🎯 Actions", padding="5")
        actions_frame.pack(fill='x', pady=(0, 10))
        
        self.enable_like_var = tk.BooleanVar(value=self.state['enable_like'])
        self.enable_retweet_var = tk.BooleanVar(value=self.state['enable_retweet'])
        
        ttk.Checkbutton(actions_frame, text="Enable Liking", variable=self.enable_like_var).pack(anchor='w')
        ttk.Checkbutton(actions_frame, text="Enable Retweeting", variable=self.enable_retweet_var).pack(anchor='w')
        
        # Account selection
        accounts_frame = ttk.LabelFrame(left_panel, text="👤 Accounts", padding="5")
        accounts_frame.pack(fill='x', pady=(0, 10))
        
        self.accounts_listbox = tk.Listbox(accounts_frame, height=6, selectmode='multiple')
        self.accounts_listbox.pack(fill='x')
        
        # Control buttons
        buttons_frame = ttk.Frame(left_panel)
        buttons_frame.pack(fill='x', pady=(10, 0))
        
        self.start_button = ttk.Button(buttons_frame, text="🚀 Start", command=self.start_like_retweet)
        self.start_button.pack(side='left', padx=(0, 5))
        
        self.stop_button = ttk.Button(buttons_frame, text="⏹️ Stop", command=self.stop_like_retweet, state='disabled')
        self.stop_button.pack(side='left', padx=(0, 5))
        
        self.pause_button = ttk.Button(buttons_frame, text="⏸️ Pause", command=self.pause_like_retweet, state='disabled')
        self.pause_button.pack(side='left')
        
        # Right panel - Progress and Log
        right_panel = ttk.Frame(main_frame)
        right_panel.pack(side='right', fill='both', expand=True)
        
        # Progress section
        progress_frame = ttk.LabelFrame(right_panel, text="📊 Progress", padding="10")
        progress_frame.pack(fill='x', pady=(0, 10))
        
        self.progress_label = ttk.Label(progress_frame, text="Ready to start...")
        self.progress_label.pack(anchor='w', pady=(0, 5))
        
        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate')
        self.progress_bar.pack(fill='x', pady=(0, 5))
        
        # Stats frame
        stats_frame = ttk.Frame(progress_frame)
        stats_frame.pack(fill='x')
        
        self.stats_label = ttk.Label(stats_frame, text="Processed: 0 | Success: 0 | Failed: 0")
        self.stats_label.pack(anchor='w')
        
        # Log section
        log_frame = ttk.LabelFrame(right_panel, text="📝 Log", padding="10")
        log_frame.pack(fill='both', expand=True)
        
        self.log_text = tk.Text(log_frame, height=15, bg=COLOR_DARK, fg=COLOR_WHITE, state='disabled')
        self.log_text.pack(fill='both', expand=True)
        
        # Populate accounts list
        self.refresh_accounts_list()
        
        # Restore state
        self.restore_state()

    def refresh_accounts_list(self):
        """Refresh the accounts listbox"""
        self.accounts_listbox.delete(0, tk.END)
        for acc in self.accounts:
            self.accounts_listbox.insert(tk.END, f"{acc.label} ({acc.username})")

    def get_selected_accounts(self):
        """Get selected accounts from listbox"""
        selected_indices = self.accounts_listbox.curselection()
        return [self.accounts[i] for i in selected_indices]

    def log(self, message, is_error=False):
        """Add message to log"""
        timestamp = time.strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        
        if self.log_text:
            self.log_text.config(state='normal')
            self.log_text.insert(tk.END, log_message + "\n")
            self.log_text.see(tk.END)
            self.log_text.config(state='disabled')
        
        # Store in state
        self.state['log_messages'].append(log_message)
        if len(self.state['log_messages']) > 100:  # Keep only last 100 messages
            self.state['log_messages'] = self.state['log_messages'][-100:]

    def restore_state(self):
        """Restore panel state"""
        # Restore tweet URLs
        if self.state['tweet_urls']:
            self.tweet_urls_text.insert('1.0', self.state['tweet_urls'])
        
        # Restore log messages
        if self.state['log_messages']:
            for message in self.state['log_messages']:
                if self.log_text:
                    self.log_text.config(state='normal')
                    self.log_text.insert(tk.END, message + "\n")
                    self.log_text.config(state='disabled')

    def save_state(self):
        """Save current panel state"""
        self.state['tweet_urls'] = self.tweet_urls_text.get('1.0', tk.END).strip()
        self.state['min_interval'] = self.min_interval_var.get()
        self.state['max_interval'] = self.max_interval_var.get()
        self.state['enable_like'] = self.enable_like_var.get()
        self.state['enable_retweet'] = self.enable_retweet_var.get()

    def start_like_retweet(self):
        """Start the like and retweet process"""
        # Save state
        self.save_state()
        
        # Get settings
        tweet_urls_text = self.tweet_urls_text.get('1.0', tk.END).strip()
        if not tweet_urls_text:
            messagebox.showerror("Error", "Please enter tweet URLs")
            return
        
        selected_accounts = self.get_selected_accounts()
        if not selected_accounts:
            messagebox.showerror("Error", "Please select at least one account")
            return
        
        try:
            min_interval = int(self.min_interval_var.get())
            max_interval = int(self.max_interval_var.get())
        except ValueError:
            messagebox.showerror("Error", "Please enter valid time intervals")
            return
        
        if min_interval > max_interval:
            messagebox.showerror("Error", "Min interval cannot be greater than max interval")
            return
        
        # Parse tweet URLs
        tweet_urls = [url.strip() for url in tweet_urls_text.split('\n') if url.strip()]
        
        # Start processing
        self.is_running = True
        self.paused = False
        
        # Update UI
        self.start_button.config(state='disabled')
        self.stop_button.config(state='normal')
        self.pause_button.config(state='normal')
        
        # Start worker thread
        threading.Thread(target=self._like_retweet_worker, 
                       args=(tweet_urls, selected_accounts, min_interval, max_interval),
                       daemon=True).start()

    def stop_like_retweet(self):
        """Stop the like and retweet process"""
        self.is_running = False
        self.paused = False
        
        # Update UI
        self.start_button.config(state='normal')
        self.stop_button.config(state='disabled')
        self.pause_button.config(state='disabled')
        self.pause_button.config(text="⏸️ Pause")
        
        self.log("🛑 Process stopped by user")

    def pause_like_retweet(self):
        """Pause/resume the like and retweet process"""
        if self.paused:
            self.paused = False
            self.pause_button.config(text="⏸️ Pause")
            self.log("▶️ Process resumed")
        else:
            self.paused = True
            self.pause_button.config(text="▶️ Resume")
            self.log("⏸️ Process paused")

    def _like_retweet_worker(self, tweet_urls, accounts, min_interval, max_interval):
        """Worker thread for like and retweet processing"""
        try:
            total_tweets = len(tweet_urls)
            processed = 0
            success_count = 0
            failed_count = 0
            
            self.log(f"🚀 Starting like/retweet process with {len(accounts)} accounts")
            self.log(f"📊 Total tweets to process: {total_tweets}")
            
            for i, tweet_url in enumerate(tweet_urls):
                if not self.is_running:
                    break
                
                # Wait if paused
                while self.paused and self.is_running:
                    time.sleep(1)
                
                if not self.is_running:
                    break
                
                # Update progress
                processed += 1
                progress = (processed / total_tweets) * 100
                
                self.after(0, lambda p=progress, proc=processed, succ=success_count, fail=failed_count: 
                          self._update_progress(p, proc, succ, fail))
                
                self.log(f"📝 Processing tweet {processed}/{total_tweets}: {tweet_url}")
                
                # Process with each account
                for account in accounts:
                    if not self.is_running:
                        break
                    
                    try:
                        success = self._process_tweet_with_account(account, tweet_url, min_interval, max_interval)
                        if success:
                            success_count += 1
                        else:
                            failed_count += 1
                    except Exception as e:
                        self.log(f"❌ Error processing with {account.label}: {e}", is_error=True)
                        failed_count += 1
                    
                    # Wait between accounts
                    if account != accounts[-1]:
                        wait_time = random.randint(min_interval, max_interval)
                        self.log(f"⏱️ Waiting {wait_time} seconds before next account...")
                        time.sleep(wait_time)
                
                # Wait between tweets
                if i < len(tweet_urls) - 1:
                    wait_time = random.randint(min_interval, max_interval)
                    self.log(f"⏱️ Waiting {wait_time} seconds before next tweet...")
                    time.sleep(wait_time)
            
            # Final update
            self.after(0, lambda: self._update_progress(100, processed, success_count, failed_count))
            self.log(f"✅ Process completed! Success: {success_count}, Failed: {failed_count}")
            
        except Exception as e:
            self.log(f"❌ Error in worker thread: {e}", is_error=True)
        finally:
            self.after(0, self.stop_like_retweet)

    def _process_tweet_with_account(self, account, tweet_url, min_interval, max_interval):
        """Process a single tweet with one account"""
        try:
            driver_manager = get_global_driver_manager()
            driver = driver_manager.get_driver(account)
            
            if not driver:
                self.log(f"❌ No browser session for {account.label}")
                return False
            
            # Navigate to tweet
            self.log(f"🌐 Navigating to tweet with {account.label}")
            driver.get(tweet_url)
            time.sleep(3)
            
            # Check if logged in
            current_url = driver.current_url
            if 'login' in current_url or 'i/flow/login' in current_url:
                self.log(f"❌ {account.label} is not logged in")
                return False
            
            success = True
            
            # Like the tweet
            if self.enable_like_var.get():
                if self._like_tweet(driver):
                    self.log(f"❤️ Liked tweet with {account.label}")
                else:
                    self.log(f"❌ Failed to like tweet with {account.label}")
                    success = False
            
            # Retweet the tweet
            if self.enable_retweet_var.get():
                if self._retweet_tweet(driver):
                    self.log(f"🔄 Retweeted with {account.label}")
                else:
                    self.log(f"❌ Failed to retweet with {account.label}")
                    success = False
            
            return success
            
        except Exception as e:
            self.log(f"❌ Error processing tweet with {account.label}: {e}", is_error=True)
            return False

    def _like_tweet(self, driver):
        """Like a tweet"""
        try:
            # Find and click like button
            like_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-testid="like"]'))
            )
            
            # Check if already liked
            aria_label = like_button.get_attribute('aria-label')
            if 'Liked' in aria_label:
                return True  # Already liked
            
            like_button.click()
            time.sleep(2)
            return True
            
        except (TimeoutException, NoSuchElementException) as e:
            return False

    def _retweet_tweet(self, driver):
        """Retweet a tweet"""
        try:
            # Find and click retweet button
            retweet_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-testid="retweet"]'))
            )
            
            # Check if already retweeted
            aria_label = retweet_button.get_attribute('aria-label')
            if 'Retweeted' in aria_label:
                return True  # Already retweeted
            
            retweet_button.click()
            time.sleep(1)
            
            # Click "Retweet" in the dropdown
            retweet_confirm = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-testid="retweetConfirm"]'))
            )
            retweet_confirm.click()
            time.sleep(2)
            
            return True
            
        except (TimeoutException, NoSuchElementException) as e:
            return False

    def _update_progress(self, progress, processed, success, failed):
        """Update progress bar and stats"""
        if self.progress_bar:
            self.progress_bar['value'] = progress
        
        if self.progress_label:
            self.progress_label.config(text=f"Progress: {processed} tweets processed")
        
        if self.stats_label:
            self.stats_label.config(text=f"Processed: {processed} | Success: {success} | Failed: {failed}") 