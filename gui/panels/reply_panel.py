import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import random
from constants import COLOR_TAUPE, COLOR_DARK, COLOR_WHITE
from selenium_manager import reply_to_tweet, scrape_tweet_content_and_comments
from utils import log_to_file

def scrape_tweet_content_and_comments_with_account(account, tweet_url: str) -> tuple:
    """Scrape tweet content and comments using a specific account"""
    try:
        from selenium_manager import get_global_driver_manager
        
        # Get driver from the driver manager (reuses existing sessions)
        driver = get_global_driver_manager().get_driver(account)
        if not driver:
            print(f"❌ Failed to get driver for {account.label}")
            return "", [], False
        
        try:
            # Navigate to tweet
            driver.get(tweet_url)
            time.sleep(3)
            
            # Check if logged in
            current_url = driver.current_url
            if 'login' in current_url or 'i/flow/login' in current_url:
                print(f"❌ Account {account.label} is not logged in (redirected to login)")
                return "", [], False
            
            # Scrape tweet content and comments
            tweet_content, comments = scrape_tweet_content_and_comments(driver, tweet_url)
            
            # Consider successful if we got tweet content
            success = len(tweet_content.strip()) > 10
            
            if success:
                print(f"✅ Successfully scraped tweet for {account.label}: {len(tweet_content)} chars, {len(comments)} comments")
            else:
                print(f"❌ Failed to scrape tweet for {account.label}")
            
            return tweet_content, comments, success
        except Exception as e:
            print(f"❌ Error during scraping for {account.label}: {e}")
            return "", [], False
                
    except Exception as e:
        print(f"❌ Error scraping tweet with account {account.label}: {e}")
        return "", [], False

class ReplyPanel(ttk.Frame):
    def __init__(self, parent, accounts):
        super().__init__(parent)
        self.parent = parent
        self.accounts = accounts
        self.panel = None
        self.accounts_listbox = None
        self.log_text = None
        self.selected_tag = None
        self.tag_filter_dropdown = None
        
        # Multi-tweet variables
        self.tweet_urls_text = None
        self.load_contents_button = None
        self.current_tweet_index = 0
        self.tweets_data = []  # List of {url, content, success, reply_text}
        self.tweet_content_display = None
        self.tweet_navigation_frame = None
        self.prev_button = None
        self.next_button = None
        self.tweet_counter_label = None
        self.time_interval_frame = None
        self.min_interval_entry = None
        self.max_interval_entry = None
        self.start_reply_button = None
        self.pause_button = None
        self.stop_button = None
        self.is_replying = False
        self.is_paused = False
        
        # Individual reply text per tweet
        self.individual_reply_text = None
        self.send_reply_button = None
        
        # State persistence
        self.state = {
            'selected_tag': 'All',
            'log_messages': [],
            'min_interval': '30',
            'max_interval': '60'
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
        
        self.accounts_listbox = tk.Listbox(accounts_frame, selectmode='multiple', height=3, exportselection=False)
        self.accounts_listbox.pack(fill='x', padx=5, pady=5)
        self.refresh_accounts_list()
        
        # Tweet URLs input area
        urls_frame = ttk.LabelFrame(content_frame, text="Tweet URLs (one per line)", padding="10")
        urls_frame.pack(fill='x', pady=5)
        
        # URLs input and load button frame
        urls_input_frame = ttk.Frame(urls_frame)
        urls_input_frame.pack(fill='x', pady=5)
        
        self.tweet_urls_text = tk.Text(urls_input_frame, height=3, wrap='word')
        self.tweet_urls_text.pack(side='left', fill='x', expand=True, padx=(5, 5))
        
        # Load from file button
        self.load_from_file_button = tk.Button(urls_input_frame, text="📁 Load from File", 
                                             command=self.load_urls_from_file,
                                             font=('Segoe UI', 9, 'bold'),
                                             bg='#6c757d', fg='white',
                                             relief='raised', bd=2,
                                             padx=10, pady=3)
        self.load_from_file_button.pack(side='right', padx=(0, 5))
        
        # Load contents button - make it more prominent
        button_frame = ttk.Frame(urls_frame)
        button_frame.pack(fill='x', pady=10)
        
        # Create a more prominent button
        self.load_contents_button = tk.Button(button_frame, text="🔍 Load Tweet Contents", 
                                            command=self.load_tweet_contents,
                                            font=('Segoe UI', 10, 'bold'),
                                            bg='#0078d4', fg='white',
                                            relief='raised', bd=2,
                                            padx=20, pady=5)
        self.load_contents_button.pack(pady=5)
        
        # Add some spacing
        ttk.Separator(urls_frame, orient='horizontal').pack(fill='x', pady=5)
        
        # Tweet content display - INCREASED HEIGHT TO 6 ROWS
        content_display_frame = ttk.LabelFrame(content_frame, text="Tweet Content", padding="10")
        content_display_frame.pack(fill='x', pady=5)
        
        # Navigation frame
        self.tweet_navigation_frame = ttk.Frame(content_display_frame)
        self.tweet_navigation_frame.pack(fill='x', pady=(0, 5))
        
        self.tweet_counter_label = ttk.Label(self.tweet_navigation_frame, text="No tweets loaded")
        self.tweet_counter_label.pack(side='left')
        
        self.prev_button = ttk.Button(self.tweet_navigation_frame, text="← Previous", command=self.prev_tweet, state='disabled')
        self.prev_button.pack(side='right', padx=(5, 0))
        
        self.next_button = ttk.Button(self.tweet_navigation_frame, text="Next →", command=self.next_tweet, state='disabled')
        self.next_button.pack(side='right')
        
        # Tweet content display - INCREASED HEIGHT TO 6 ROWS
        self.tweet_content_display = tk.Text(content_display_frame, height=6, wrap='word', state='disabled')
        self.tweet_content_display.pack(fill='x', padx=5, pady=5)
        
        # Individual reply text per tweet
        reply_frame = ttk.LabelFrame(content_frame, text="Reply for This Tweet", padding="10")
        reply_frame.pack(fill='x', pady=5)
        
        # Individual reply text
        self.individual_reply_text = tk.Text(reply_frame, height=3, wrap='word')
        self.individual_reply_text.pack(fill='x', pady=5)
        
        # Send reply button for current tweet
        send_frame = ttk.Frame(reply_frame)
        send_frame.pack(fill='x', pady=5)
        
        self.send_reply_button = tk.Button(send_frame, text="💬 Send Reply for This Tweet", 
                                         command=self.send_reply_for_current_tweet,
                                         font=('Segoe UI', 10, 'bold'),
                                         bg='#28a745', fg='white',
                                         relief='raised', bd=2,
                                         padx=15, pady=3,
                                         state='disabled')
        self.send_reply_button.pack(side='left')
        
        # Time interval settings
        self.time_interval_frame = ttk.Frame(content_frame)
        self.time_interval_frame.pack(fill='x', pady=5)
        
        ttk.Label(self.time_interval_frame, text="Time Interval:").pack(side='left')
        ttk.Label(self.time_interval_frame, text="Min:").pack(side='left', padx=(10, 0))
        self.min_interval_entry = ttk.Entry(self.time_interval_frame, width=8)
        self.min_interval_entry.pack(side='left', padx=5)
        self.min_interval_entry.insert(0, self.state['min_interval'])
        self.min_interval_entry.bind('<KeyRelease>', self.on_time_interval_change)
        
        ttk.Label(self.time_interval_frame, text="Max:").pack(side='left', padx=(10, 0))
        self.max_interval_entry = ttk.Entry(self.time_interval_frame, width=8)
        self.max_interval_entry.pack(side='left', padx=5)
        self.max_interval_entry.insert(0, self.state['max_interval'])
        self.max_interval_entry.bind('<KeyRelease>', self.on_time_interval_change)
        
        ttk.Label(self.time_interval_frame, text="seconds").pack(side='left', padx=5)
        
        # Control buttons
        control_frame = ttk.Frame(content_frame)
        control_frame.pack(fill='x', pady=10)
        
        self.start_reply_button = ttk.Button(control_frame, text="Start Auto Reply", command=self.start_replying, state='disabled')
        self.start_reply_button.pack(side='left', padx=(0, 5))
        
        self.pause_button = ttk.Button(control_frame, text="Pause", command=self.pause_replying, state='disabled')
        self.pause_button.pack(side='left', padx=(0, 5))
        
        self.stop_button = ttk.Button(control_frame, text="Stop", command=self.stop_replying, state='disabled')
        self.stop_button.pack(side='left')
        
        # Log area - INCREASED HEIGHT
        log_frame = ttk.LabelFrame(content_frame, text="Activity Log", padding="10")
        log_frame.pack(fill='both', expand=True, pady=10)
        
        self.log_text = tk.Text(log_frame, height=10, state='disabled', bg=COLOR_DARK, fg=COLOR_WHITE)
        self.log_text.pack(fill='both', expand=True)
        
        # Restore log messages
        self.restore_log_messages()
        
        self.panel = self
        return self

    def on_time_interval_change(self, event=None):
        """Save time interval changes to state"""
        try:
            min_val = self.min_interval_entry.get()
            max_val = self.max_interval_entry.get()
            
            if min_val and max_val:
                self.state['min_interval'] = min_val
                self.state['max_interval'] = max_val
        except Exception as e:
            print(f"Error saving time interval: {e}")

    def on_tag_filter_change(self, event=None):
        """Handle tag filter changes"""
        self.state['selected_tag'] = self.selected_tag.get()
        self.refresh_accounts_list()

    def restore_log_messages(self):
        """Restore log messages from state"""
        for msg in self.state.get('log_messages', []):
            self.log(msg)

    def refresh_accounts_list(self):
        """Refresh the accounts listbox based on tag filter"""
        if not hasattr(self, 'accounts_listbox') or self.accounts_listbox is None:
            return
            
        self.accounts_listbox.delete(0, tk.END)
        
        selected_tag = self.selected_tag.get()
        
        for account in self.accounts:
            if selected_tag == 'All' or selected_tag in (account.tags or []):
                self.accounts_listbox.insert(tk.END, account.label)

    def log(self, message, is_error=False):
        """Add message to log with timestamp"""
        timestamp = time.strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        
        # Save to state
        if 'log_messages' not in self.state:
            self.state['log_messages'] = []
        self.state['log_messages'].append(formatted_message)
        
        # Keep only last 100 messages
        if len(self.state['log_messages']) > 100:
            self.state['log_messages'] = self.state['log_messages'][-100:]
        
        # Update UI
        if hasattr(self, 'log_text') and self.log_text is not None:
            self.log_text.config(state='normal')
            self.log_text.insert(tk.END, formatted_message + '\n')
            self.log_text.see(tk.END)
            self.log_text.config(state='disabled')
        
        # Also log to file
        log_to_file("reply_panel", formatted_message)

    def update_button_state(self, enabled=True):
        """Update button states based on processing status"""
        state = 'normal' if enabled else 'disabled'
        
        if hasattr(self, 'load_contents_button') and self.load_contents_button is not None:
            self.load_contents_button.config(state=state)
        
        if hasattr(self, 'start_reply_button') and self.start_reply_button is not None:
            self.start_reply_button.config(state=state)

    def load_tweet_contents(self):
        """Load tweet contents from URLs"""
        urls_text = self.tweet_urls_text.get('1.0', 'end').strip()
        if not urls_text:
            messagebox.showwarning("No URLs", "Please enter tweet URLs first.")
            return
        
        urls = [url.strip() for url in urls_text.split('\n') if url.strip()]
        if not urls:
            messagebox.showwarning("No URLs", "Please enter valid tweet URLs.")
            return
        
        self.log(f"🔍 Loading {len(urls)} tweet contents...")
        self.update_button_state(False)
        
        # Start loading in background
        thread = threading.Thread(target=self._load_tweet_contents_worker, args=(urls,))
        thread.daemon = True
        thread.start()

    def _load_tweet_contents_worker(self, urls):
        """Worker thread to load tweet contents"""
        try:
            self.tweets_data = []
            
            # Get first account for scraping
            selected_accounts = self._get_selected_accounts()
            if not selected_accounts:
                self.after(0, lambda: self.log("❌ No accounts selected", is_error=True))
                return
            
            account = selected_accounts[0]  # Use first account for scraping
            
            for i, url in enumerate(urls):
                self.after(0, lambda url=url, i=i: self.log(f"📄 Loading tweet {i+1}/{len(urls)}: {url}"))
                
                try:
                    content, comments, success = scrape_tweet_content_and_comments_with_account(account, url)
                    
                    tweet_data = {
                        'url': url,
                        'content': content if success else f"Failed to load: {url}",
                        'success': success,
                        'reply_text': ''  # Individual reply text for this tweet
                    }
                    
                    self.tweets_data.append(tweet_data)
                    
                    if success:
                        self.after(0, lambda url=url: self.log(f"✅ Loaded tweet: {len(content)} chars"))
                    else:
                        self.after(0, lambda url=url: self.log(f"❌ Failed to load tweet: {url}", is_error=True))
                        
                except Exception as e:
                    self.after(0, lambda e=e, url=url: self.log(f"❌ Error loading tweet {url}: {e}", is_error=True))
                    self.tweets_data.append({
                        'url': url,
                        'content': f"Error: {str(e)}",
                        'success': False,
                        'reply_text': ''
                    })
            
            self.after(0, lambda: self._update_tweet_display())
            self.after(0, lambda: self.log(f"🎉 Loaded {len(self.tweets_data)} tweets"))
            
        except Exception as e:
            self.after(0, lambda e=e: self.log(f"❌ Error in load process: {e}", is_error=True))
        finally:
            self.after(0, lambda: self.update_button_state(True))

    def _update_tweet_display(self):
        """Update the tweet display with current tweet"""
        if not self.tweets_data:
            self.tweet_content_display.config(state='normal')
            self.tweet_content_display.delete('1.0', tk.END)
            self.tweet_content_display.insert('1.0', "No tweets loaded")
            self.tweet_content_display.config(state='disabled')
            
            self.tweet_counter_label.config(text="No tweets loaded")
            self.prev_button.config(state='disabled')
            self.next_button.config(state='disabled')
            self.send_reply_button.config(state='disabled')
            self.start_reply_button.config(state='disabled')
            return
        
        # Update counter
        self.tweet_counter_label.config(text=f"Tweet {self.current_tweet_index + 1} of {len(self.tweets_data)}")
        
        # Update navigation buttons
        self.prev_button.config(state='normal' if self.current_tweet_index > 0 else 'disabled')
        self.next_button.config(state='normal' if self.current_tweet_index < len(self.tweets_data) - 1 else 'disabled')
        
        # Update content display
        current_tweet = self.tweets_data[self.current_tweet_index]
        self.tweet_content_display.config(state='normal')
        self.tweet_content_display.delete('1.0', tk.END)
        self.tweet_content_display.insert('1.0', current_tweet['content'])
        self.tweet_content_display.config(state='disabled')
        
        # Update individual reply text
        self.individual_reply_text.delete('1.0', tk.END)
        self.individual_reply_text.insert('1.0', current_tweet.get('reply_text', ''))
        
        # Enable buttons
        self.send_reply_button.config(state='normal')
        self.start_reply_button.config(state='normal')

    def prev_tweet(self):
        """Go to previous tweet"""
        if self.current_tweet_index > 0:
            # Save current reply text
            self._save_current_reply_text()
            self.current_tweet_index -= 1
            self._update_tweet_display()

    def next_tweet(self):
        """Go to next tweet"""
        if self.current_tweet_index < len(self.tweets_data) - 1:
            # Save current reply text
            self._save_current_reply_text()
            self.current_tweet_index += 1
            self._update_tweet_display()

    def _save_current_reply_text(self):
        """Save the current reply text to the tweet data"""
        if self.tweets_data and 0 <= self.current_tweet_index < len(self.tweets_data):
            reply_text = self.individual_reply_text.get('1.0', 'end').strip()
            self.tweets_data[self.current_tweet_index]['reply_text'] = reply_text

    def send_reply_for_current_tweet(self):
        """Send reply for the current tweet only"""
        if not self.tweets_data or self.current_tweet_index >= len(self.tweets_data):
            messagebox.showwarning("No Tweet", "No tweet selected to reply to.")
            return
        
        selected_accounts = self._get_selected_accounts()
        if not selected_accounts:
            messagebox.showwarning("No Accounts", "Please select at least one account.")
            return
        
        # Save current reply text
        self._save_current_reply_text()
        
        current_tweet = self.tweets_data[self.current_tweet_index]
        reply_text = current_tweet.get('reply_text', '').strip()
        
        if not reply_text:
            messagebox.showwarning("No Reply", "Please enter a reply text for this tweet.")
            return
        
        self.log(f"💬 Sending reply for tweet {self.current_tweet_index + 1}/{len(self.tweets_data)}")
        
        # Send reply in background
        thread = threading.Thread(target=self._send_single_reply_worker, 
                                args=(current_tweet, selected_accounts, reply_text))
        thread.daemon = True
        thread.start()

    def _send_single_reply_worker(self, tweet_data, selected_accounts, reply_text):
        """Worker to send a single reply"""
        try:
            success_count = 0
            total_count = len(selected_accounts)
            
            for account in selected_accounts:
                try:
                    success, msg = reply_to_tweet(account, tweet_data['url'], reply_text)
                    if success:
                        self.after(0, lambda acc=account: self.log(f"[{acc.label}] ✅ Reply sent successfully"))
                        success_count += 1
                    else:
                        self.after(0, lambda acc=account, msg=msg: self.log(f"[{acc.label}] ❌ {msg}", is_error=True))
                except Exception as e:
                    self.after(0, lambda acc=account, e=e: self.log(f"[{acc.label}] ❌ Error: {e}", is_error=True))
            
            self.after(0, lambda: self.log(f"🎉 Reply sent: {success_count}/{total_count} accounts successful"))
            
        except Exception as e:
            self.after(0, lambda e=e: self.log(f"❌ Error sending reply: {e}", is_error=True))

    def start_replying(self):
        """Start the auto reply process"""
        if not self.tweets_data:
            messagebox.showwarning("No Tweets", "Please load tweet contents first.")
            return
        
        selected_accounts = self._get_selected_accounts()
        if not selected_accounts:
            messagebox.showwarning("No Accounts", "Please select at least one account.")
            return
        
        # Save current reply text
        self._save_current_reply_text()
        
        # Check if all tweets have reply text
        tweets_without_reply = [i for i, tweet in enumerate(self.tweets_data) if not tweet.get('reply_text', '').strip()]
        if tweets_without_reply:
            messagebox.showwarning("Missing Replies", 
                                f"Please enter reply text for tweets: {', '.join(str(i+1) for i in tweets_without_reply)}")
            return
        
        try:
            min_interval = int(self.min_interval_entry.get())
            max_interval = int(self.max_interval_entry.get())
        except ValueError:
            messagebox.showerror("Invalid Interval", "Please enter valid time intervals.")
            return
        
        self.is_replying = True
        self.is_paused = False
        
        # Update button states
        self.start_reply_button.config(state='disabled')
        self.pause_button.config(state='normal')
        self.stop_button.config(state='normal')
        self.load_contents_button.config(state='disabled')
        
        self.log("🚀 Starting auto reply process...")
        
        # Start reply process in background
        thread = threading.Thread(target=self._reply_worker, 
                                args=(selected_accounts, min_interval, max_interval))
        thread.daemon = True
        thread.start()

    def _reply_worker(self, selected_accounts, min_interval, max_interval):
        """Worker thread for auto reply process"""
        try:
            for i, tweet_data in enumerate(self.tweets_data):
                if not self.is_replying:
                    break
                
                # Wait for pause to be released
                while self.is_paused and self.is_replying:
                    time.sleep(1)
                
                if not self.is_replying:
                    break
                
                self.after(0, lambda i=i: self.log(f"📝 Processing tweet {i+1}/{len(self.tweets_data)}"))
                
                reply_text = tweet_data.get('reply_text', '').strip()
                if not reply_text:
                    self.after(0, lambda: self.log(f"⏭️ Skipping tweet {i+1} (no reply text)"))
                    continue
                
                # Send reply to all accounts
                success_count = 0
                total_count = len(selected_accounts)
                
                for account in selected_accounts:
                    if not self.is_replying:
                        break
                    
                    try:
                        success, msg = reply_to_tweet(account, tweet_data['url'], reply_text)
                        if success:
                            self.after(0, lambda acc=account: self.log(f"[{acc.label}] ✅ Reply sent"))
                            success_count += 1
                        else:
                            self.after(0, lambda acc=account, msg=msg: self.log(f"[{acc.label}] ❌ {msg}", is_error=True))
                    except Exception as e:
                        self.after(0, lambda acc=account, e=e: self.log(f"[{acc.label}] ❌ Error: {e}", is_error=True))
                
                self.after(0, lambda i=i, success=success_count, total=total_count: 
                          self.log(f"📊 Tweet {i+1} completed: {success}/{total} accounts"))
                
                # Wait before next tweet (if not the last one)
                if i < len(self.tweets_data) - 1 and self.is_replying:
                    interval = random.randint(min_interval, max_interval)
                    self.after(0, lambda interval=interval: self.log(f"⏱️ Waiting {interval} seconds before next tweet..."))
                    time.sleep(interval)
            
            self.after(0, lambda: self.log("🎉 Auto reply process completed!"))
            
        except Exception as e:
            self.after(0, lambda e=e: self.log(f"❌ Error in auto reply process: {e}", is_error=True))
        finally:
            self.after(0, lambda: self._stop_replying())

    def _get_selected_accounts(self):
        """Get selected accounts from listbox"""
        selected_indices = self.accounts_listbox.curselection()
        selected_accounts = []
        
        for index in selected_indices:
            account_label = self.accounts_listbox.get(index)
            for account in self.accounts:
                if account.label == account_label:
                    selected_accounts.append(account)
                    break
        
        return selected_accounts

    def pause_replying(self):
        """Pause/resume the reply process"""
        if self.is_paused:
            self.is_paused = False
            self.pause_button.config(text="Pause")
            self.log("▶️ Auto reply process resumed")
        else:
            self.is_paused = True
            self.pause_button.config(text="Resume")
            self.log("⏸️ Auto reply process paused")

    def stop_replying(self):
        """Stop the reply process"""
        self.is_replying = False
        self.is_paused = False
        self.log("⏹️ Auto reply process stopped")
        self._stop_replying()

    def _stop_replying(self):
        """Stop reply process and reset UI"""
        self.is_replying = False
        self.is_paused = False
        
        # Reset button states
        self.start_reply_button.config(state='normal')
        self.pause_button.config(state='disabled')
        self.stop_button.config(state='disabled')
        self.load_contents_button.config(state='normal') 

    def load_urls_from_file(self):
        """Load tweet URLs from a file (e.g., linkstocomment.txt)"""
        file_path = 'linkstocomment.txt' # Default file name
        try:
            with open(file_path, 'r') as f:
                urls = [line.strip() for line in f if line.strip()]
                if not urls:
                    messagebox.showwarning("No URLs Found", f"No URLs found in {file_path}.")
                    return
                self.tweet_urls_text.delete('1.0', tk.END)
                self.tweet_urls_text.insert('1.0', '\n'.join(urls))
                self.tweet_urls_text.see(tk.END)
                self.log(f"📁 Loaded {len(urls)} URLs from {file_path}")
        except FileNotFoundError:
            messagebox.showerror("File Not Found", f"The file '{file_path}' was not found.")
        except Exception as e:
            messagebox.showerror("Error Loading File", f"An error occurred while loading URLs from file: {e}")
            self.log(f"❌ Error loading URLs from file {file_path}: {e}", is_error=True) 