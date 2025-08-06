import tkinter as tk
from tkinter import ttk, messagebox
from constants import COLOR_TAUPE, COLOR_DARK
import threading
from selenium_manager import reply_to_tweet, reply_to_comment, scrape_tweet_content_and_comments
from utils import log_to_file
from selenium.webdriver.chrome.options import Options
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os
import pickle
import random
import re

class ReplyCommentPanel(ttk.Frame):
    def __init__(self, parent, accounts):
        super().__init__(parent)
        self.parent = parent
        self.accounts = accounts
        self.panel = None
        self.accounts_listbox = None
        self.tweet_url_entry = None
        self.comments_listbox = None
        self.reply_entry = None
        self.log_text = None
        self.comments = []  # List of (username, text)
        self.driver = None  # Keep browser open after loading comments
        
        # Auto reply variables
        self.auto_accounts_listbox = None
        self.auto_urls_text = None
        self.auto_reply_text = None
        self.auto_comments_count_var = None
        self.auto_min_interval_var = None
        self.auto_max_interval_var = None
        self.auto_running = False
        self.auto_paused = False
        self.auto_stats = {'processed': 0, 'successful': 0, 'failed': 0}

    def build_panel(self):
        title = tk.Label(self, text="Reply to Comments", font=('Segoe UI', 16, 'bold'), bg=COLOR_TAUPE, fg=COLOR_DARK)
        title.pack(anchor='nw', padx=20, pady=(20, 10))
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill='both', expand=True, padx=20, pady=10)
        
        # Manual tab
        self.manual_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.manual_frame, text="Manual Reply")
        self._build_manual_tab()
        
        # Auto tab
        self.auto_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.auto_frame, text="Auto Reply")
        self._build_auto_tab()
        
        self.panel = self
        return self

    def _build_manual_tab(self):
        """Build the manual reply tab"""
        # Account selection
        accounts_frame = ttk.LabelFrame(self.manual_frame, text="Select Accounts", padding="10")
        accounts_frame.pack(fill='x', padx=10, pady=5)
        
        self.accounts_listbox = tk.Listbox(accounts_frame, selectmode='multiple', height=5, exportselection=False)
        self.accounts_listbox.pack(fill='x', padx=5, pady=5)
        self.refresh_accounts_list()
        
        # Parent Tweet URL
        url_frame = ttk.LabelFrame(self.manual_frame, text="Parent Tweet URL", padding="10")
        url_frame.pack(fill='x', padx=10, pady=5)
        
        self.tweet_url_entry = ttk.Entry(url_frame, width=40)
        self.tweet_url_entry.pack(fill='x', padx=5, pady=5)
        
        # Load Comments button
        load_btn = ttk.Button(url_frame, text="Load Comments", command=self.load_comments)
        load_btn.pack(pady=5)
        
        # Comment selection
        comments_frame = ttk.LabelFrame(self.manual_frame, text="Select Comment to Reply To", padding="10")
        comments_frame.pack(fill='x', padx=10, pady=5)
        
        self.comments_listbox = tk.Listbox(comments_frame, selectmode='browse', height=5, exportselection=False)
        self.comments_listbox.pack(fill='x', padx=5, pady=5)
        
        # Reply text
        reply_frame = ttk.LabelFrame(self.manual_frame, text="Reply Text", padding="10")
        reply_frame.pack(fill='x', padx=10, pady=5)
        
        self.reply_entry = tk.Text(reply_frame, width=40, height=3)
        self.reply_entry.pack(fill='x', padx=5, pady=5)
        
        # Reply to Comment (Bulk) button
        reply_btn = ttk.Button(self.manual_frame, text="Reply to Comment (Bulk)", command=self.reply_to_comment_bulk)
        reply_btn.pack(pady=10)
        
        # Log area
        log_frame = ttk.LabelFrame(self.manual_frame, text="Activity Log", padding="10")
        log_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        self.log_text = tk.Text(log_frame, height=8, state='disabled', bg=COLOR_DARK, fg='white')
        self.log_text.pack(fill='both', expand=True)

    def _build_auto_tab(self):
        """Build the auto reply tab"""
        # Settings frame
        settings_frame = ttk.LabelFrame(self.auto_frame, text="Auto Reply Settings", padding="10")
        settings_frame.pack(fill='x', padx=10, pady=5)
        
        # Comments count setting
        comments_row = ttk.Frame(settings_frame)
        comments_row.pack(fill='x', pady=2)
        ttk.Label(comments_row, text="Comments to scrape per tweet:").pack(side='left')
        self.auto_comments_count_var = tk.StringVar(value="20")
        comments_entry = ttk.Entry(comments_row, textvariable=self.auto_comments_count_var, width=10)
        comments_entry.pack(side='right', padx=5)
        
        # Time interval settings
        interval_row = ttk.Frame(settings_frame)
        interval_row.pack(fill='x', pady=2)
        ttk.Label(interval_row, text="Time interval (seconds):").pack(side='left')
        self.auto_min_interval_var = tk.StringVar(value="10")
        self.auto_max_interval_var = tk.StringVar(value="30")
        ttk.Entry(interval_row, textvariable=self.auto_min_interval_var, width=8).pack(side='left', padx=5)
        ttk.Label(interval_row, text="to").pack(side='left')
        ttk.Entry(interval_row, textvariable=self.auto_max_interval_var, width=8).pack(side='left', padx=5)
        
        # Account selection
        accounts_frame = ttk.LabelFrame(self.auto_frame, text="Select Accounts", padding="10")
        accounts_frame.pack(fill='x', padx=10, pady=5)
        
        self.auto_accounts_listbox = tk.Listbox(accounts_frame, selectmode='multiple', height=5, exportselection=False)
        self.auto_accounts_listbox.pack(fill='x', padx=5, pady=5)
        self.refresh_auto_accounts_list()
        
        # URLs frame
        urls_frame = ttk.LabelFrame(self.auto_frame, text="Tweet URLs (one per line)", padding="10")
        urls_frame.pack(fill='x', padx=10, pady=5)
        
        # URLs input and load button frame
        urls_input_frame = ttk.Frame(urls_frame)
        urls_input_frame.pack(fill='x', pady=5)
        
        self.auto_urls_text = tk.Text(urls_input_frame, height=4, width=40)
        self.auto_urls_text.pack(side='left', fill='x', expand=True, padx=(5, 5))
        
        # Load from file button
        self.auto_load_from_file_button = tk.Button(urls_input_frame, text="📁 Load from File", 
                                                  command=self.auto_load_urls_from_file,
                                                  font=('Segoe UI', 9, 'bold'),
                                                  bg='#6c757d', fg='white',
                                                  relief='raised', bd=2,
                                                  padx=10, pady=3)
        self.auto_load_from_file_button.pack(side='right', padx=(0, 5))
        
        # Reply text
        reply_frame = ttk.LabelFrame(self.auto_frame, text="Reply Text", padding="10")
        reply_frame.pack(fill='x', padx=10, pady=5)
        
        self.auto_reply_text = tk.Text(reply_frame, height=3, width=40)
        self.auto_reply_text.pack(fill='x', padx=5, pady=5)
        
        # Control buttons
        controls_frame = ttk.Frame(self.auto_frame)
        controls_frame.pack(fill='x', padx=10, pady=10)
        
        self.start_auto_btn = ttk.Button(controls_frame, text="Start Auto Reply", command=self.start_auto_reply)
        self.start_auto_btn.pack(side='left', padx=5)
        
        self.stop_auto_btn = ttk.Button(controls_frame, text="Stop", command=self.stop_auto_reply, state='disabled')
        self.stop_auto_btn.pack(side='left', padx=5)
        
        self.pause_auto_btn = ttk.Button(controls_frame, text="Pause", command=self.pause_auto_reply, state='disabled')
        self.pause_auto_btn.pack(side='left', padx=5)
        
        # Progress and stats
        stats_frame = ttk.LabelFrame(self.auto_frame, text="Progress & Statistics", padding="10")
        stats_frame.pack(fill='x', padx=10, pady=5)
        
        self.progress_var = tk.StringVar(value="Ready")
        ttk.Label(stats_frame, textvariable=self.progress_var).pack(anchor='w')
        
        self.stats_var = tk.StringVar(value="Processed: 0 | Successful: 0 | Failed: 0")
        ttk.Label(stats_frame, textvariable=self.stats_var).pack(anchor='w')
        
        # Auto log area
        auto_log_frame = ttk.LabelFrame(self.auto_frame, text="Auto Reply Log", padding="10")
        auto_log_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        self.auto_log_text = tk.Text(auto_log_frame, height=8, state='disabled', bg=COLOR_DARK, fg='white')
        self.auto_log_text.pack(fill='both', expand=True)

    def refresh_accounts_list(self):
        """Refresh the accounts list in manual tab"""
        if self.accounts_listbox:
            self.accounts_listbox.delete(0, 'end')
            for acc in self.accounts:
                self.accounts_listbox.insert('end', f"{acc.label} ({acc.username})")

    def refresh_auto_accounts_list(self):
        """Refresh the accounts list in auto tab"""
        if self.auto_accounts_listbox:
            self.auto_accounts_listbox.delete(0, 'end')
            for acc in self.accounts:
                self.auto_accounts_listbox.insert('end', f"{acc.label} ({acc.username})")

    def log(self, message, is_error=False):
        if is_error:
            message = f"❌ {message}"
        self.log_text.config(state='normal')
        self.log_text.insert('end', message + '\n')
        self.log_text.see('end')
        self.log_text.config(state='disabled')
        log_to_file('reply_comment', message)

    def auto_log(self, message, is_error=False):
        if is_error:
            message = f"❌ {message}"
        self.auto_log_text.config(state='normal')
        self.auto_log_text.insert('end', message + '\n')
        self.auto_log_text.see('end')
        self.auto_log_text.config(state='disabled')
        log_to_file('reply_comment_auto', message)

    def load_comments(self):
        tweet_url = self.tweet_url_entry.get().strip()
        if not tweet_url:
            self.log("Parent Tweet URL is required.", is_error=True)
            return
        # Use the first account for scraping
        if not self.accounts:
            self.log("No accounts available to load comments.", is_error=True)
            return
        acc = self.accounts[0]
        self.log(f"Loading comments for {tweet_url} using [{acc.label}]...")
        threading.Thread(target=self._scrape_comments, args=(acc, tweet_url)).start()

    def _scrape_comments(self, acc, tweet_url):
        try:
            options = Options()
            options.add_argument('--start-maximized')
            # Add anti-detection options
            options.add_argument('--disable-blink-features=AutomationControlled')
            
            # Core optimizations (reduced for faster startup)
            options.add_argument('--disable-extensions')
            options.add_argument('--disable-plugins')
            options.add_argument('--disable-images')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-gpu')
            options.add_argument('--disable-dev-shm-usage')
            
            # Memory optimizations
            options.add_argument('--disable-background-timer-throttling')
            options.add_argument('--disable-backgrounding-occluded-windows')
            options.add_argument('--disable-renderer-backgrounding')
            
            # Startup optimizations
            options.add_argument('--no-first-run')
            options.add_argument('--no-default-browser-check')
            options.add_argument('--disable-default-apps')
            options.add_argument('--disable-sync')
            
            if acc.proxy:
                options.add_argument(f'--proxy-server={acc.proxy}')
            
            driver = uc.Chrome(options=options)
            
            # Execute script to remove webdriver property
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.driver = driver  # Keep browser open for future use
            cookie_path = acc.get_cookie_path()
            if os.path.exists(cookie_path):
                with open(cookie_path, 'rb') as f:
                    cookies = pickle.load(f)
                driver.get('https://x.com/')
                time.sleep(2)  # Reduced from default
                for cookie in cookies:
                    try:
                        driver.add_cookie(cookie)
                    except Exception:
                        pass
            driver.get(tweet_url)
            time.sleep(3)  # Reduced from 5 to 3 seconds
            # Scroll to load more comments
            for _ in range(3):
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)  # Reduced from 2 to 1 second
            # Scrape visible comments (replies)
            comments = []
            articles = driver.find_elements(By.CSS_SELECTOR, 'article[data-testid="tweet"]')
            self.log(f"[DEBUG] Found {len(articles)} article[data-testid='tweet'] elements.")
            for idx, article in enumerate(articles[1:], start=1):  # Skip the first (main tweet)
                try:
                    user_elem = article.find_element(By.CSS_SELECTOR, 'div[dir="ltr"] span')
                    username = user_elem.text
                except Exception:
                    username = None
                try:
                    text_elem = article.find_element(By.CSS_SELECTOR, 'div[data-testid="tweetText"]')
                    text = text_elem.text[:80]
                except Exception:
                    try:
                        text_elem = article.find_element(By.CSS_SELECTOR, 'span')
                        text = text_elem.text[:80]
                    except Exception:
                        text = None
                if username and text:
                    comments.append((username, text))
            # Do NOT close the browser here
            self.comments = comments
            self._update_comments_listbox()
            self.log(f"Loaded {len(comments)} comments.")
        except Exception as e:
            self.log(f"Error loading comments: {e}", is_error=True)

    def _update_comments_listbox(self):
        self.comments_listbox.delete(0, 'end')
        for username, text in self.comments:
            display = f"@{username}: {text}"
            self.comments_listbox.insert('end', display)

    def reply_to_comment_bulk(self):
        selected_indices = self.accounts_listbox.curselection()
        if not selected_indices:
            self.log("Select at least one account.", is_error=True)
            return
        tweet_url = self.tweet_url_entry.get().strip()
        if not tweet_url:
            self.log("Parent Tweet URL is required.", is_error=True)
            return
        comment_idx = self.comments_listbox.curselection()
        if not comment_idx:
            self.log("Select a comment to reply to.", is_error=True)
            return
        reply_text = self.reply_entry.get("1.0", "end").strip()
        if not reply_text:
            self.log("Reply text is required.", is_error=True)
            return
        selected_accounts = [self.accounts[i] for i in selected_indices]
        selected_comment = self.comments[comment_idx[0]] if self.comments else (None, None)
        threading.Thread(target=self._reply_comment_sequential, args=(selected_accounts, tweet_url, reply_text, selected_comment)).start()

    def _reply_comment_sequential(self, accounts, tweet_url, reply_text, selected_comment):
        for acc in accounts:
            self.log(f"[{acc.label}] Sending reply to comment @{selected_comment[0]}: {selected_comment[1]}")
            # For now, still reply to parent tweet (can be enhanced to reply to comment directly)
            success, msg = reply_to_tweet(acc, tweet_url, reply_text)
            if success:
                self.log(f"[{acc.label}] ✅ {msg}")
            else:
                self.log(f"[{acc.label}] {msg}", is_error=True)

    # Auto reply methods
    def start_auto_reply(self):
        """Start the auto reply process"""
        # Get selected accounts
        selected_indices = self.auto_accounts_listbox.curselection()
        if not selected_indices:
            self.auto_log("Select at least one account.", is_error=True)
            return
        
        # Get URLs
        urls_text = self.auto_urls_text.get("1.0", "end").strip()
        if not urls_text:
            self.auto_log("Enter at least one tweet URL.", is_error=True)
            return
        
        # Get reply text
        reply_text = self.auto_reply_text.get("1.0", "end").strip()
        if not reply_text:
            self.auto_log("Enter reply text.", is_error=True)
            return
        
        # Get settings
        try:
            comments_count = int(self.auto_comments_count_var.get())
            min_interval = int(self.auto_min_interval_var.get())
            max_interval = int(self.auto_max_interval_var.get())
        except ValueError:
            self.auto_log("Invalid settings values.", is_error=True)
            return
        
        # Parse URLs
        urls = [url.strip() for url in urls_text.split('\n') if url.strip()]
        
        # Get selected accounts
        selected_accounts = [self.accounts[i] for i in selected_indices]
        
        # Start auto reply process
        self.auto_running = True
        self.auto_paused = False
        self.auto_stats = {'processed': 0, 'successful': 0, 'failed': 0}
        
        # Update UI
        self.start_auto_btn.config(state='disabled')
        self.stop_auto_btn.config(state='normal')
        self.pause_auto_btn.config(state='normal')
        
        # Start worker thread
        threading.Thread(target=self._auto_reply_worker, 
                       args=(urls, selected_accounts, reply_text, comments_count, min_interval, max_interval)).start()

    def stop_auto_reply(self):
        """Stop the auto reply process"""
        self.auto_running = False
        self.auto_paused = False
        self.start_auto_btn.config(state='normal')
        self.stop_auto_btn.config(state='disabled')
        self.pause_auto_btn.config(state='disabled')
        self.auto_log("⏹️ Auto reply stopped by user.")

    def pause_auto_reply(self):
        """Pause/resume the auto reply process"""
        if self.auto_paused:
            self.auto_paused = False
            self.pause_auto_btn.config(text="Pause")
            self.auto_log("▶️ Auto reply resumed.")
        else:
            self.auto_paused = True
            self.pause_auto_btn.config(text="Resume")
            self.auto_log("⏸️ Auto reply paused.")

    def _auto_reply_worker(self, urls, accounts, reply_text, comments_count, min_interval, max_interval):
        """Worker thread for auto reply process"""
        try:
            self.auto_log(f"🚀 Starting Auto Reply with {len(accounts)} accounts...")
            self.auto_log(f"📊 Comments to scrape per tweet: {comments_count}")
            self.auto_log(f"⏱️ Time interval: {min_interval}-{max_interval} seconds")
            self.auto_log(f"📝 Reply text: {reply_text[:50]}...")
            
            for url_index, tweet_url in enumerate(urls):
                if not self.auto_running:
                    break
                
                self.auto_log(f"📝 Processing tweet {url_index + 1}/{len(urls)}: {tweet_url}")
                
                # Scrape comments for this tweet
                comments = self._scrape_comments_for_auto(tweet_url, comments_count)
                
                if not comments:
                    self.auto_log(f"❌ No comments found for {tweet_url}")
                    continue
                
                self.auto_log(f"📊 Found {len(comments)} comments to reply to")
                
                # Reply to each comment
                for comment_index, (username, comment_text) in enumerate(comments):
                    if not self.auto_running:
                        break
                    
                    while self.auto_paused:
                        time.sleep(1)
                        if not self.auto_running:
                            return
                    
                    self.auto_log(f"💬 Replying to comment {comment_index + 1}/{len(comments)}: @{username}")
                    
                    # Reply with each account
                    for account_index, account in enumerate(accounts):
                        if not self.auto_running:
                            break
                        
                        self.auto_log(f"🤖 Replying with account: {account.label}")
                        
                        try:
                            success, msg = reply_to_comment(account, tweet_url, username, reply_text)
                            
                            if success:
                                self.auto_log(f"✅ Successfully replied with {account.label}")
                                self.auto_stats['successful'] += 1
                            else:
                                self.auto_log(f"❌ Failed to reply with {account.label}: {msg}", is_error=True)
                                self.auto_stats['failed'] += 1
                            
                            self.auto_stats['processed'] += 1
                            self._update_auto_progress()
                            
                            # Wait between accounts
                            if account_index < len(accounts) - 1:
                                wait_time = random.randint(min_interval, max_interval)
                                self.auto_log(f"⏱️ Waiting {wait_time} seconds before next account...")
                                time.sleep(wait_time)
                                
                        except Exception as e:
                            self.auto_log(f"❌ Error replying with {account.label}: {e}", is_error=True)
                            self.auto_stats['failed'] += 1
                            self.auto_stats['processed'] += 1
                            self._update_auto_progress()
                    
                    # Wait between comments
                    if comment_index < len(comments) - 1:
                        wait_time = random.randint(min_interval, max_interval)
                        self.auto_log(f"⏱️ Waiting {wait_time} seconds before next comment...")
                        time.sleep(wait_time)
                
                # Wait between tweets
                if url_index < len(urls) - 1:
                    wait_time = random.randint(min_interval, max_interval)
                    self.auto_log(f"⏱️ Waiting {wait_time} seconds before next tweet...")
                    time.sleep(wait_time)
            
            self.auto_log("🎉 Auto reply completed!")
            
        except Exception as e:
            self.auto_log(f"❌ Error in auto reply: {e}", is_error=True)
        finally:
            # Update UI
            self.start_auto_btn.config(state='normal')
            self.stop_auto_btn.config(state='disabled')
            self.pause_auto_btn.config(state='disabled')
            self.auto_running = False

    def _scrape_comments_for_auto(self, tweet_url, max_comments):
        """Scrape comments for auto reply process"""
        try:
            if not self.accounts:
                return []
            
            # Use first account for scraping
            account = self.accounts[0]
            
            # Create driver
            options = Options()
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--disable-extensions')
            options.add_argument('--disable-plugins')
            options.add_argument('--disable-images')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-gpu')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-background-timer-throttling')
            options.add_argument('--disable-backgrounding-occluded-windows')
            options.add_argument('--disable-renderer-backgrounding')
            options.add_argument('--no-first-run')
            options.add_argument('--no-default-browser-check')
            options.add_argument('--disable-default-apps')
            options.add_argument('--disable-sync')
            
            if account.proxy:
                options.add_argument(f'--proxy-server={account.proxy}')
            
            driver = uc.Chrome(options=options)
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            try:
                # Load cookies
                cookie_path = account.get_cookie_path()
                if os.path.exists(cookie_path):
                    with open(cookie_path, 'rb') as f:
                        cookies = pickle.load(f)
                    driver.get('https://x.com/')
                    time.sleep(2)
                    for cookie in cookies:
                        try:
                            driver.add_cookie(cookie)
                        except Exception:
                            pass
                
                # Navigate to tweet
                driver.get(tweet_url)
                time.sleep(3)
                
                # Check if logged in
                current_url = driver.current_url
                if 'login' in current_url or 'i/flow/login' in current_url:
                    self.auto_log(f"❌ Account {account.label} is not logged in")
                    return []
                
                # Scroll to load comments
                for _ in range(5):  # More scrolls to load more comments
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(1)
                
                # Scrape comments
                comments = []
                articles = driver.find_elements(By.CSS_SELECTOR, 'article[data-testid="tweet"]')
                
                for article in articles[1:max_comments+1]:  # Skip main tweet, limit to max_comments
                    try:
                        # Get username
                        user_elem = article.find_element(By.CSS_SELECTOR, 'div[dir="ltr"] span')
                        username = user_elem.text
                        
                        # Get comment text
                        text_elem = article.find_element(By.CSS_SELECTOR, 'div[data-testid="tweetText"]')
                        text = text_elem.text
                        
                        if username and text:
                            comments.append((username, text))
                            
                    except Exception as e:
                        continue
                
                return comments
                
            finally:
                driver.quit()
                
        except Exception as e:
            self.auto_log(f"❌ Error scraping comments: {e}", is_error=True)
            return []

    def _update_auto_progress(self):
        """Update auto reply progress display"""
        self.progress_var.set(f"Processed: {self.auto_stats['processed']}")
        self.stats_var.set(f"Processed: {self.auto_stats['processed']} | Successful: {self.auto_stats['successful']} | Failed: {self.auto_stats['failed']}") 

    def auto_load_urls_from_file(self):
        """Load tweet URLs from a file named linkstocomment.txt"""
        file_path = 'linkstocomment.txt'
        if not os.path.exists(file_path):
            self.auto_log(f"Error: linkstocomment.txt not found at {file_path}", is_error=True)
            return
        
        try:
            with open(file_path, 'r') as f:
                urls = [line.strip() for line in f if line.strip()]
            
            if not urls:
                self.auto_log(f"No URLs found in {file_path}.", is_error=True)
                return
            
            self.auto_urls_text.delete('1.0', 'end')
            for url in urls:
                self.auto_urls_text.insert('end', url + '\n')
            self.auto_log(f"Loaded {len(urls)} URLs from {file_path}.")
        except Exception as e:
            self.auto_log(f"Error loading URLs from file: {e}", is_error=True) 