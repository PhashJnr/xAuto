import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from constants import COLOR_TAUPE, COLOR_DARK, COLOR_WHITE
import threading
import requests
import json
import time
from selenium_manager import reply_to_tweet, scrape_tweet_content_and_comments
from utils import log_to_file
from ai_integration import create_ai_integration
from typing import Dict, List
from selenium.webdriver.common.by import By
import random
import urllib.parse
import re
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

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

class YappingPanel(ttk.Frame):
    def __init__(self, parent, accounts):
        super().__init__(parent)
        self.parent = parent
        self.accounts = accounts
        
        # Manual yapping variables
        self.tweet_urls_text = None
        self.load_from_file_button = None
        self.load_contents_button = None
        self.accounts_listbox = None
        self.ai_prompt_entry = None
        self.ai_comments_text = None
        self.log_text = None
        self.selected_tag = None
        self.tag_filter_dropdown = None
        self.ai_enabled_var = None
        self.context_analysis_var = None
        self.auto_reply_var = None
        
        # Enhanced manual yapping variables
        self.tweet_content_display = None
        self.tweet_navigation_frame = None
        self.prev_button = None
        self.next_button = None
        self.tweet_counter_label = None
        self.individual_reply_text = None
        self.generate_ai_button = None
        self.edit_comment_button = None
        self.send_reply_button = None
        self.min_interval_entry = None
        self.max_interval_entry = None
        self.start_reply_button = None
        self.pause_button = None
        self.stop_button = None
        self.progress_bar = None
        self.progress_label = None
        self.stats_label = None
        self.current_tweet_index = 0
        self.tweets_data = []  # List of {url, content, success, reply_text}
        self.is_replying = False
        self.is_paused = False
        
        # Auto yapping variables
        self.auto_search_entry = None
        self.auto_accounts_listbox = None
        self.auto_min_interval = None
        self.auto_max_interval = None
        self.auto_max_tweets = None
        self.auto_min_chars = None
        self.auto_max_chars = None
        self.auto_custom_prompt = None
        self.review_before_posting_var = None
        self.review_info_label = None
        self.start_auto_button = None
        self.stop_auto_button = None
        self.pause_auto_button = None
        self.auto_progress_bar = None
        self.auto_stats_label = None
        self.auto_log_text = None
        
        # Enhanced search query builder variables
        self.auto_keywords_entry = None
        self.auto_language_var = None
        self.auto_language_combo = None
        self.auto_time_range_var = None
        self.auto_time_range_combo = None
        self.auto_min_replies = None
        self.auto_filter_verified = None
        self.auto_filter_native_retweets = None
        self.auto_filter_retweets = None
        self.auto_filter_replies = None
        self.auto_generated_query = None
        self.auto_selected_tag = None
        self.auto_tag_filter_dropdown = None
        
        # Auto yapping state
        self.auto_yapping_running = False
        self.auto_yapping_paused = False
        self.auto_yapping_stats = {'processed': 0, 'successful': 0, 'failed': 0}
        self.replied_tweets_db = {}
        self._review_dialog_open = False
        
        # Initialize AI integration
        self.ai_integration = create_ai_integration()
        
        # Store scraped data
        self.scraped_tweet_content = None
        self.scraped_comments = []
        
        # State persistence
        self.state = {
            'selected_tag': 'All',
            'tweet_url': '',
            'reply_text': '',
            'log_messages': [],
            'ai_enabled': True,
            'context_analysis': True,
            'auto_reply': False,
            'review_before_posting': False,
            'min_interval': '30',
            'max_interval': '60'
        }
        
        # Don't call build_panel() here - it will be called by the main app
    
    def get_current_ai_provider(self):
        """Get the current AI provider from the AI settings"""
        try:
            # Get the main app from the parent structure
            main_app = self.parent.master
            if hasattr(main_app, 'panels') and 'ai_settings' in main_app.panels:
                ai_settings_panel = main_app.panels['ai_settings']
                
                # Get the OpenAI provider from the AI settings
                current_provider_name = ai_settings_panel.provider_var.get()
                
                # Debug logging
                log_to_file('yapping', f"Current provider name: {current_provider_name}")
                
                # Always use OpenAI provider
                provider = ai_settings_panel.ai_manager.provider
                log_to_file('yapping', f"Using provider: {provider.name}")
                return provider
            else:
                # Fallback to our own AI integration
                log_to_file('yapping', "AI settings panel not found, using fallback")
                return self.ai_integration.provider
        except Exception as e:
            # Fallback to our own AI integration
            log_to_file('yapping', f"Error getting AI provider: {e}")
            return self.ai_integration.provider

    def on_tweet_url_change(self, event=None):
        """Save tweet URLs to state"""
        if hasattr(self, 'tweet_urls_text') and self.tweet_urls_text:
            self.state['tweet_url'] = self.tweet_urls_text.get('1.0', tk.END).strip()

    def on_ai_prompt_change(self, event=None):
        """Save AI prompt to state"""
        self.state['ai_prompt'] = self.ai_prompt_entry.get('1.0', 'end-1c')

    def on_ai_enabled_change(self):
        """Save AI enabled state"""
        self.state['ai_enabled'] = self.ai_enabled_var.get()

    def on_context_analysis_change(self):
        """Save context analysis state"""
        self.state['context_analysis'] = self.context_analysis_var.get()

    def on_auto_reply_change(self):
        """Save auto reply state"""
        self.state['auto_reply'] = self.auto_reply_var.get()

    def on_tag_filter_change(self, event=None):
        """Handle tag filter change and save state"""
        self.state['selected_tag'] = self.selected_tag.get()
        self.refresh_accounts_list()

    def refresh_accounts_list(self):
        """Refresh the accounts listbox"""
        if not hasattr(self, 'accounts_listbox'):
            return
            
        self.accounts_listbox.delete(0, tk.END)
        
        # Get current tag filter
        tag = self.selected_tag.get() if hasattr(self, 'selected_tag') else 'All'
        
        # Filter accounts based on tag
        filtered_accounts = [a for a in self.accounts if tag == 'All' or tag in a.tags]
        
        for account in filtered_accounts:
            tags_text = f" [{', '.join(account.tags)}]" if account.tags else ""
            self.accounts_listbox.insert('end', f"{account.label} ({account.username}){tags_text}")
        
        # Also refresh auto accounts list if it exists and has been initialized
        if hasattr(self, 'auto_accounts_listbox') and self.auto_accounts_listbox is not None:
            self.refresh_auto_accounts_list()

    def build_panel(self):
        # Configure the frame
        self.configure(style='Panel.TFrame')
        
        # Create canvas for scrolling
        canvas = tk.Canvas(self, bg=COLOR_TAUPE)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas, style='Panel.TFrame')
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Title
        title = tk.Label(scrollable_frame, text="🤖 AI-Powered Yapping", font=('Segoe UI', 16, 'bold'), bg=COLOR_TAUPE, fg=COLOR_DARK)
        title.grid(row=0, column=0, columnspan=3, sticky='w', padx=20, pady=(20, 10))
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(scrollable_frame)
        self.notebook.grid(row=1, column=0, columnspan=3, sticky='ew', padx=20, pady=10)
        
        # Manual Yapping Tab
        self.manual_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.manual_frame, text="📝 Manual Yapping")
        self._build_manual_tab()
        
        # Auto Yapping Tab
        self.auto_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.auto_frame, text="🤖 Auto Yapping")
        self._build_auto_tab()
        
        # Pack the canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Bind mouse wheel to canvas
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        canvas.bind_all("<MouseWheel>", _on_mousewheel) 

    def _build_manual_tab(self):
        """Build the manual yapping tab"""
        # Tweet URLs Input (Multi-URL support)
        url_frame = ttk.LabelFrame(self.manual_frame, text="📝 Tweet URLs (one per line)", padding="10")
        url_frame.grid(row=0, column=0, columnspan=3, sticky='ew', padx=20, pady=10)
        
        # URLs input and load button frame
        urls_input_frame = ttk.Frame(url_frame)
        urls_input_frame.pack(fill='x', pady=(0, 10))
        
        # Create a frame for the text area and scrollbar
        urls_text_frame = ttk.Frame(urls_input_frame)
        urls_text_frame.pack(side='left', fill='x', expand=True)
        
        self.tweet_urls_text = tk.Text(urls_text_frame, height=6, width=80, wrap='word')
        self.tweet_urls_text.pack(side='left', fill='x', expand=True)
        
        # Add scrollbar for tweet URLs text area
        urls_scrollbar = ttk.Scrollbar(urls_text_frame, orient="vertical", command=self.tweet_urls_text.yview)
        urls_scrollbar.pack(side='right', fill='y')
        self.tweet_urls_text.configure(yscrollcommand=urls_scrollbar.set)
        
        # Load from file button
        self.load_from_file_button = tk.Button(urls_input_frame, text="📁 Load from File", 
                                             command=self.load_urls_from_file,
                                             font=('Segoe UI', 9, 'bold'),
                                             bg='#6c757d', fg='white',
                                             relief='raised', bd=2,
                                             padx=10, pady=3)
        self.load_from_file_button.pack(side='right', padx=(5, 0))
        
        # Load tweet contents button
        self.load_contents_button = tk.Button(url_frame, text="🔍 Load Tweet Contents", 
                                            command=self.load_tweet_contents,
                                            font=('Segoe UI', 9, 'bold'),
                                            bg='#28a745', fg='white',
                                            relief='raised', bd=2,
                                            padx=10, pady=3)
        self.load_contents_button.pack(pady=5)
        
        # Account Selection
        accounts_frame = ttk.LabelFrame(self.manual_frame, text="👤 Select Accounts", padding="10")
        accounts_frame.grid(row=1, column=0, columnspan=3, sticky='ew', padx=20, pady=10)
        
        # Tag filter
        filter_frame = ttk.Frame(accounts_frame)
        filter_frame.pack(fill='x', pady=5)
        
        tk.Label(filter_frame, text="Filter by Tag:", bg=COLOR_TAUPE, fg=COLOR_DARK).pack(side='left', padx=5)
        self.selected_tag = tk.StringVar(value='All')
        self.tag_filter_dropdown = ttk.Combobox(filter_frame, textvariable=self.selected_tag, state='readonly', width=20)
        self.tag_filter_dropdown.pack(side='left', padx=5)
        self.tag_filter_dropdown.bind('<<ComboboxSelected>>', self.on_tag_filter_change)
        
        # Accounts listbox
        listbox_frame = ttk.Frame(accounts_frame)
        listbox_frame.pack(fill='x', pady=5)
        
        self.accounts_listbox = tk.Listbox(listbox_frame, height=6, selectmode='multiple')
        self.accounts_listbox.pack(side='left', fill='x', expand=True, padx=5)
        
        scrollbar_accounts = ttk.Scrollbar(listbox_frame, orient="vertical", command=self.accounts_listbox.yview)
        scrollbar_accounts.pack(side='right', fill='y')
        self.accounts_listbox.configure(yscrollcommand=scrollbar_accounts.set)
        
        # Tweet Content Display with Navigation
        content_frame = ttk.LabelFrame(self.manual_frame, text="📊 Tweet Content", padding="10")
        content_frame.grid(row=2, column=0, columnspan=3, sticky='ew', padx=20, pady=10)
        
        # Navigation frame
        self.tweet_navigation_frame = ttk.Frame(content_frame)
        self.tweet_navigation_frame.pack(fill='x', pady=(0, 5))
        
        self.prev_button = tk.Button(self.tweet_navigation_frame, text="◀ Previous", 
                                    command=self.prev_tweet,
                                    font=('Segoe UI', 9, 'bold'),
                                    bg='#6c757d', fg='white',
                                    relief='raised', bd=2,
                                    padx=10, pady=3)
        self.prev_button.pack(side='left', padx=(0, 5))
        
        self.tweet_counter_label = tk.Label(self.tweet_navigation_frame, text="Tweet 0 of 0", 
                                          font=('Segoe UI', 10, 'bold'),
                                          bg=COLOR_TAUPE, fg=COLOR_DARK)
        self.tweet_counter_label.pack(side='left', padx=10)
        
        self.next_button = tk.Button(self.tweet_navigation_frame, text="Next ▶", 
                                    command=self.next_tweet,
                                    font=('Segoe UI', 9, 'bold'),
                                    bg='#6c757d', fg='white',
                                    relief='raised', bd=2,
                                    padx=10, pady=3)
        self.next_button.pack(side='left', padx=(5, 0))
        
        # Tweet content display with scrollbar
        content_text_frame = ttk.Frame(content_frame)
        content_text_frame.pack(fill='x', pady=5)
        
        self.tweet_content_display = tk.Text(content_text_frame, height=8, width=80, wrap='word', state='disabled')
        self.tweet_content_display.pack(side='left', fill='x', expand=True)
        
        # Add scrollbar for tweet content display
        content_scrollbar = ttk.Scrollbar(content_text_frame, orient="vertical", command=self.tweet_content_display.yview)
        content_scrollbar.pack(side='right', fill='y')
        self.tweet_content_display.configure(yscrollcommand=content_scrollbar.set)
        
        # Individual Reply Text
        reply_frame = ttk.LabelFrame(self.manual_frame, text="💬 Individual Reply Text", padding="10")
        reply_frame.grid(row=3, column=0, columnspan=3, sticky='ew', padx=20, pady=10)
        
        # Create a frame for the reply text area and scrollbar
        reply_text_frame = ttk.Frame(reply_frame)
        reply_text_frame.pack(fill='x', pady=5)
        
        self.individual_reply_text = tk.Text(reply_text_frame, height=4, width=80, wrap='word')
        self.individual_reply_text.pack(side='left', fill='x', expand=True)
        
        # Add scrollbar for individual reply text area
        reply_scrollbar = ttk.Scrollbar(reply_text_frame, orient="vertical", command=self.individual_reply_text.yview)
        reply_scrollbar.pack(side='right', fill='y')
        self.individual_reply_text.configure(yscrollcommand=reply_scrollbar.set)
        
        # Reply action buttons
        reply_buttons_frame = ttk.Frame(reply_frame)
        reply_buttons_frame.pack(fill='x', pady=5)
        
        self.generate_ai_button = tk.Button(reply_buttons_frame, text="🤖 Generate AI Comment", 
                                          command=self.generate_ai_comment_for_current_tweet,
                                          font=('Segoe UI', 9, 'bold'),
                                          bg='#17a2b8', fg='white',
                                          relief='raised', bd=2,
                                          padx=10, pady=3)
        self.generate_ai_button.pack(side='left', padx=(0, 5))
        
        self.edit_comment_button = tk.Button(reply_buttons_frame, text="✏️ Edit Comment", 
                                           command=self.edit_current_comment,
                                           font=('Segoe UI', 9, 'bold'),
                                           bg='#ffc107', fg='black',
                                           relief='raised', bd=2,
                                           padx=10, pady=3)
        self.edit_comment_button.pack(side='left', padx=(0, 5))
        
        self.send_reply_button = tk.Button(reply_buttons_frame, text="✅ Send Reply", 
                                         command=self.send_reply_for_current_tweet,
                                         font=('Segoe UI', 9, 'bold'),
                                         bg='#28a745', fg='white',
                                         relief='raised', bd=2,
                                         padx=10, pady=3)
        self.send_reply_button.pack(side='left')
        
        # AI Configuration
        ai_frame = ttk.LabelFrame(self.manual_frame, text="🤖 AI Configuration", padding="10")
        ai_frame.grid(row=4, column=0, columnspan=3, sticky='ew', padx=20, pady=10)
        
        # AI Enable checkbox
        self.ai_enabled_var = tk.BooleanVar(value=self.state['ai_enabled'])
        ai_check = ttk.Checkbutton(ai_frame, text="Enable AI Comments", variable=self.ai_enabled_var, command=self.on_ai_enabled_change)
        ai_check.pack(anchor='w', padx=5, pady=2)
        
        # Context analysis checkbox
        self.context_analysis_var = tk.BooleanVar(value=self.state['context_analysis'])
        context_check = ttk.Checkbutton(ai_frame, text="Analyze Tweet Context", variable=self.context_analysis_var, command=self.on_context_analysis_change)
        context_check.pack(anchor='w', padx=5, pady=2)
        
        # Auto reply checkbox
        self.auto_reply_var = tk.BooleanVar(value=self.state['auto_reply'])
        auto_check = ttk.Checkbutton(ai_frame, text="Auto Reply Mode", variable=self.auto_reply_var, command=self.on_auto_reply_change)
        auto_check.pack(anchor='w', padx=5, pady=2)
        
        # AI Prompt
        prompt_frame = ttk.Frame(ai_frame)
        prompt_frame.pack(fill='x', padx=5, pady=5)
        
        tk.Label(prompt_frame, text="🎯 Custom Reply Instructions:", bg=COLOR_TAUPE, fg=COLOR_DARK, font=('Segoe UI', 10, 'bold')).pack(anchor='w', padx=5, pady=(5,2))
        
        # Add helpful examples
        examples_text = """Examples:
• "Reply as a supportive friend"
• "Ask a thought-provoking question"
• "Share a personal experience"
• "Be humorous and lighthearted"
• "Show expertise and knowledge"
• "Be encouraging and motivational"
• "Ask for their opinion on the topic"
• "Share a relevant fact or statistic"
• "Express genuine curiosity"
• "Be empathetic and understanding\""""
        
        examples_label = tk.Label(prompt_frame, text=examples_text, bg=COLOR_TAUPE, fg=COLOR_DARK, font=('Segoe UI', 8), justify='left', anchor='w')
        examples_label.pack(anchor='w', padx=5, pady=(0,5))
        
        self.ai_prompt_entry = tk.Text(prompt_frame, height=4, width=60, wrap='word')
        self.ai_prompt_entry.pack(fill='x', padx=5, pady=2)
        self.ai_prompt_entry.bind('<KeyRelease>', self.on_ai_prompt_change)
        
        # Add placeholder text
        placeholder_text = "Enter your custom instructions for how to reply to the tweet..."
        self.ai_prompt_entry.insert('1.0', placeholder_text)
        self.ai_prompt_entry.bind('<FocusIn>', self._on_prompt_focus_in)
        self.ai_prompt_entry.bind('<FocusOut>', self._on_prompt_focus_out)
        
        # Time Interval Settings
        interval_frame = ttk.LabelFrame(self.manual_frame, text="⏱️ Time Intervals", padding="10")
        interval_frame.grid(row=5, column=0, columnspan=3, sticky='ew', padx=20, pady=10)
        
        interval_input_frame = ttk.Frame(interval_frame)
        interval_input_frame.pack(fill='x', pady=5)
        
        ttk.Label(interval_input_frame, text="Min Interval (seconds):").pack(side='left', padx=(0, 5))
        self.min_interval_entry = ttk.Entry(interval_input_frame, width=10)
        self.min_interval_entry.pack(side='left', padx=(0, 20))
        self.min_interval_entry.insert(0, '30')
        self.min_interval_entry.bind('<KeyRelease>', self.on_time_interval_change)
        
        ttk.Label(interval_input_frame, text="Max Interval (seconds):").pack(side='left', padx=(0, 5))
        self.max_interval_entry = ttk.Entry(interval_input_frame, width=10)
        self.max_interval_entry.pack(side='left')
        self.max_interval_entry.insert(0, '60')
        self.max_interval_entry.bind('<KeyRelease>', self.on_time_interval_change)
        
        # Control Buttons
        buttons_frame = ttk.Frame(self.manual_frame)
        buttons_frame.grid(row=6, column=0, columnspan=3, sticky='ew', padx=20, pady=10)
        
        self.start_reply_button = tk.Button(buttons_frame, text="🚀 Start Reply Process", 
                                          command=self.start_manual_reply_process,
                                          font=('Segoe UI', 10, 'bold'),
                                          bg='#28a745', fg='white',
                                          relief='raised', bd=2,
                                          padx=15, pady=5)
        self.start_reply_button.pack(side='left', padx=(0, 5))
        
        self.pause_button = tk.Button(buttons_frame, text="⏸️ Pause", 
                                    command=self.pause_manual_reply_process,
                                    font=('Segoe UI', 9, 'bold'),
                                    bg='#ffc107', fg='black',
                                    relief='raised', bd=2,
                                    padx=10, pady=3,
                                    state='disabled')
        self.pause_button.pack(side='left', padx=(0, 5))
        
        self.stop_button = tk.Button(buttons_frame, text="⏹️ Stop", 
                                   command=self.stop_manual_reply_process,
                                   font=('Segoe UI', 9, 'bold'),
                                   bg='#dc3545', fg='white',
                                   relief='raised', bd=2,
                                   padx=10, pady=3,
                                   state='disabled')
        self.stop_button.pack(side='left')
        
        # Progress Section
        progress_frame = ttk.LabelFrame(self.manual_frame, text="📊 Progress", padding="10")
        progress_frame.grid(row=7, column=0, columnspan=3, sticky='ew', padx=20, pady=10)
        
        self.progress_label = ttk.Label(progress_frame, text="Ready to start...")
        self.progress_label.pack(anchor='w', pady=(0, 5))
        
        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate')
        self.progress_bar.pack(fill='x', pady=(0, 5))
        
        # Stats frame
        stats_frame = ttk.Frame(progress_frame)
        stats_frame.pack(fill='x')
        
        self.stats_label = ttk.Label(stats_frame, text="Processed: 0 | Success: 0 | Failed: 0")
        self.stats_label.pack(anchor='w')
        
        # Log Area
        log_frame = ttk.LabelFrame(self.manual_frame, text="📝 Activity Log", padding="10")
        log_frame.grid(row=8, column=0, columnspan=3, sticky='ew', padx=20, pady=10)
        
        # Create text widget with scrollbar for logs
        log_text_frame = ttk.Frame(log_frame)
        log_text_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        self.log_text = tk.Text(log_text_frame, height=10, width=80, wrap='word', bg=COLOR_DARK, fg=COLOR_WHITE)
        self.log_text.pack(side='left', fill='both', expand=True)
        
        log_scrollbar = ttk.Scrollbar(log_text_frame, orient="vertical", command=self.log_text.yview)
        log_scrollbar.pack(side='right', fill='y')
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        # Initialize multi-tweet variables
        self.current_tweet_index = 0
        self.tweets_data = []  # List of {url, content, success, reply_text}
        self.is_replying = False
        self.is_paused = False
        
        # Restore state
        self.restore_log_messages()
        self.refresh_accounts_list()

    def _build_auto_tab(self):
        """Build the auto yapping tab with improved responsiveness"""
        try:
            # Create main frame with better layout management
            auto_frame = ttk.Frame(self.auto_frame)
            auto_frame.pack(fill='both', expand=True, padx=10, pady=10)
            
            # Use grid for better layout control
            auto_frame.columnconfigure(0, weight=1)
            auto_frame.rowconfigure(1, weight=1)  # Make log area expandable
            
            # Search section
            search_frame = ttk.LabelFrame(auto_frame, text="Search Settings", padding=10)
            search_frame.grid(row=0, column=0, sticky='ew', padx=(0, 0), pady=(0, 10))
            search_frame.columnconfigure(1, weight=1)
            
            # Search query builder
            query_builder_frame = ttk.LabelFrame(search_frame, text="Search Query Builder", padding=5)
            query_builder_frame.grid(row=0, column=0, columnspan=2, sticky='ew', pady=(0, 10))
            query_builder_frame.columnconfigure(1, weight=1)
            query_builder_frame.columnconfigure(3, weight=1)
            
            # Keywords/Phrases
            ttk.Label(query_builder_frame, text="Keywords/Phrases:").grid(row=0, column=0, sticky='w', padx=(0, 10))
            self.auto_keywords_entry = ttk.Entry(query_builder_frame, width=30)
            self.auto_keywords_entry.grid(row=0, column=1, sticky='ew', padx=(0, 20))
            self.auto_keywords_entry.insert(0, '"cysic" OR @cysic_xyz')
            
            # Language
            ttk.Label(query_builder_frame, text="Language:").grid(row=0, column=2, sticky='w', padx=(0, 10))
            self.auto_language_var = tk.StringVar(value='en')
            self.auto_language_combo = ttk.Combobox(query_builder_frame, textvariable=self.auto_language_var, 
                                                   values=['en', 'es', 'fr', 'de', 'it', 'pt', 'ja', 'ko', 'zh'], width=8)
            self.auto_language_combo.grid(row=0, column=3, sticky='w')
            
            # Time range
            ttk.Label(query_builder_frame, text="Time Range:").grid(row=1, column=0, sticky='w', padx=(0, 10), pady=(10, 0))
            self.auto_time_range_var = tk.StringVar(value='1440min')
            self.auto_time_range_combo = ttk.Combobox(query_builder_frame, textvariable=self.auto_time_range_var,
                                                     values=['1h', '6h', '12h', '24h', '1440min', '7d', '30d'], width=10)
            self.auto_time_range_combo.grid(row=1, column=1, sticky='w', pady=(10, 0))
            
            # Min replies
            ttk.Label(query_builder_frame, text="Min Replies:").grid(row=1, column=2, sticky='w', padx=(0, 10), pady=(10, 0))
            self.auto_min_replies = ttk.Entry(query_builder_frame, width=8)
            self.auto_min_replies.grid(row=1, column=3, sticky='w', pady=(10, 0))
            self.auto_min_replies.insert(0, "20")
            
            # Filters
            filters_frame = ttk.Frame(query_builder_frame)
            filters_frame.grid(row=2, column=0, columnspan=4, sticky='ew', pady=(10, 0))
            
            self.auto_filter_verified = tk.BooleanVar(value=True)
            ttk.Checkbutton(filters_frame, text="Verified Only", variable=self.auto_filter_verified).grid(row=0, column=0, sticky='w', padx=(0, 20))
            
            self.auto_filter_native_retweets = tk.BooleanVar(value=True)
            ttk.Checkbutton(filters_frame, text="Exclude Native Retweets", variable=self.auto_filter_native_retweets).grid(row=0, column=1, sticky='w', padx=(0, 20))
            
            self.auto_filter_retweets = tk.BooleanVar(value=True)
            ttk.Checkbutton(filters_frame, text="Exclude Retweets", variable=self.auto_filter_retweets).grid(row=0, column=2, sticky='w', padx=(0, 20))
            
            self.auto_filter_replies = tk.BooleanVar(value=True)
            ttk.Checkbutton(filters_frame, text="Exclude Replies", variable=self.auto_filter_replies).grid(row=0, column=3, sticky='w')
            
            # Generated query display
            ttk.Label(search_frame, text="Generated Query:").grid(row=1, column=0, sticky='w', padx=(0, 10), pady=(10, 0))
            self.auto_generated_query = ttk.Entry(search_frame, width=80, state='readonly')
            self.auto_generated_query.grid(row=1, column=1, sticky='ew', padx=(0, 10), pady=(10, 0))
            
            # Update query button
            ttk.Button(search_frame, text="🔄 Update Query", command=self._update_auto_search_query).grid(row=2, column=0, columnspan=2, sticky='w', pady=(5, 0))
            
            # Account filtering
            account_filter_frame = ttk.LabelFrame(search_frame, text="Account Filtering", padding=5)
            account_filter_frame.grid(row=3, column=0, columnspan=2, sticky='ew', pady=(10, 0))
            account_filter_frame.columnconfigure(1, weight=1)
            
            # Tag filter for auto yapping
            ttk.Label(account_filter_frame, text="Filter by Tag:").grid(row=0, column=0, sticky='w', padx=(0, 10))
            self.auto_selected_tag = tk.StringVar(value='All')
            self.auto_tag_filter_dropdown = ttk.Combobox(account_filter_frame, textvariable=self.auto_selected_tag, state='readonly', width=20)
            self.auto_tag_filter_dropdown.grid(row=0, column=1, sticky='w', padx=(0, 20))
            self.auto_tag_filter_dropdown.bind('<<ComboboxSelected>>', self._on_auto_tag_filter_change)
            
            # Accounts selection
            ttk.Label(account_filter_frame, text="Selected Accounts:").grid(row=1, column=0, sticky='w', padx=(0, 10), pady=(10, 0))
            accounts_frame = ttk.Frame(account_filter_frame)
            accounts_frame.grid(row=1, column=1, sticky='ew', pady=(10, 0))
            accounts_frame.columnconfigure(0, weight=1)
            
            # Accounts listbox with scrollbar
            listbox_frame = ttk.Frame(accounts_frame)
            listbox_frame.grid(row=0, column=0, sticky='ew')
            listbox_frame.columnconfigure(0, weight=1)
            
            self.auto_accounts_listbox = tk.Listbox(listbox_frame, height=4, selectmode='multiple')
            auto_accounts_scrollbar = ttk.Scrollbar(listbox_frame, orient='vertical', command=self.auto_accounts_listbox.yview)
            self.auto_accounts_listbox.configure(yscrollcommand=auto_accounts_scrollbar.set)
            
            self.auto_accounts_listbox.grid(row=0, column=0, sticky='ew')
            auto_accounts_scrollbar.grid(row=0, column=1, sticky='ns')
            
            # Refresh accounts button
            ttk.Button(accounts_frame, text="🔄 Refresh", command=self.refresh_auto_accounts_list).grid(row=1, column=0, sticky='w', pady=(5, 0))
            
            # Initialize accounts list and update query
            self.refresh_auto_accounts_list()
            self._update_auto_search_query()
            
            # Settings section
            settings_frame = ttk.LabelFrame(auto_frame, text="Settings", padding=10)
            settings_frame.grid(row=2, column=0, sticky='ew', pady=(0, 10))
            settings_frame.columnconfigure(1, weight=1)
            settings_frame.columnconfigure(3, weight=1)
            
            # Time intervals
            ttk.Label(settings_frame, text="Min Interval (s):").grid(row=0, column=0, sticky='w', padx=(0, 10))
            self.auto_min_interval = ttk.Entry(settings_frame, width=10)
            self.auto_min_interval.grid(row=0, column=1, sticky='w', padx=(0, 20))
            self.auto_min_interval.insert(0, "60")
            
            ttk.Label(settings_frame, text="Max Interval (s):").grid(row=0, column=2, sticky='w', padx=(0, 10))
            self.auto_max_interval = ttk.Entry(settings_frame, width=10)
            self.auto_max_interval.grid(row=0, column=3, sticky='w')
            self.auto_max_interval.insert(0, "120")
            
            # Max tweets
            ttk.Label(settings_frame, text="Max Tweets:").grid(row=1, column=0, sticky='w', padx=(0, 10), pady=(10, 0))
            self.auto_max_tweets = ttk.Entry(settings_frame, width=10)
            self.auto_max_tweets.grid(row=1, column=1, sticky='w', padx=(0, 20), pady=(10, 0))
            self.auto_max_tweets.insert(0, "10")
            
            # Character limits
            ttk.Label(settings_frame, text="Min Chars:").grid(row=1, column=2, sticky='w', padx=(0, 10), pady=(10, 0))
            self.auto_min_chars = ttk.Entry(settings_frame, width=10)
            self.auto_min_chars.grid(row=1, column=3, sticky='w', pady=(10, 0))
            self.auto_min_chars.insert(0, "180")
            
            ttk.Label(settings_frame, text="Max Chars:").grid(row=2, column=0, sticky='w', padx=(0, 10), pady=(10, 0))
            self.auto_max_chars = ttk.Entry(settings_frame, width=10)
            self.auto_max_chars.grid(row=2, column=1, sticky='w', padx=(0, 20), pady=(10, 0))
            self.auto_max_chars.insert(0, "280")
            
            # Custom prompt
            ttk.Label(settings_frame, text="Custom Instructions:").grid(row=2, column=2, sticky='w', padx=(0, 10), pady=(10, 0))
            self.auto_custom_prompt = ttk.Entry(settings_frame, width=30)
            self.auto_custom_prompt.grid(row=2, column=3, sticky='ew', pady=(10, 0))
            
            # Review before posting checkbox
            self.review_before_posting_var = tk.BooleanVar()
            review_checkbox = ttk.Checkbutton(settings_frame, text="Review Before Posting", 
                                           variable=self.review_before_posting_var,
                                           command=self._on_review_checkbox_change)
            review_checkbox.grid(row=3, column=0, columnspan=2, sticky='w', pady=(10, 0))
            
            # Info label for review
            self.review_info_label = ttk.Label(settings_frame, text="", foreground="blue")
            self.review_info_label.grid(row=3, column=2, columnspan=2, sticky='w', pady=(10, 0))
            
            # Control buttons
            control_frame = ttk.Frame(auto_frame)
            control_frame.grid(row=3, column=0, sticky='ew', pady=(0, 10))
            control_frame.columnconfigure(1, weight=1)
            
            self.start_auto_button = ttk.Button(control_frame, text="🚀 Start Auto Yapping", 
                                              command=self.start_auto_yapping_search)
            self.start_auto_button.grid(row=0, column=0, padx=(0, 10))
            
            self.stop_auto_button = ttk.Button(control_frame, text="⏹️ Stop", 
                                             command=self.stop_auto_yapping_search, state='disabled')
            self.stop_auto_button.grid(row=0, column=1, padx=(0, 10))
            
            self.pause_auto_button = ttk.Button(control_frame, text="⏸️ Pause", 
                                              command=self.pause_auto_yapping_search, state='disabled')
            self.pause_auto_button.grid(row=0, column=2)
            
            # Progress section
            progress_frame = ttk.LabelFrame(auto_frame, text="Progress", padding=10)
            progress_frame.grid(row=4, column=0, sticky='ew', pady=(0, 10))
            progress_frame.columnconfigure(0, weight=1)
            
            # Progress bar
            self.auto_progress_bar = ttk.Progressbar(progress_frame, mode='determinate')
            self.auto_progress_bar.grid(row=0, column=0, sticky='ew', pady=(0, 5))
            
            # Stats label
            self.auto_stats_label = ttk.Label(progress_frame, text="Ready to start")
            self.auto_stats_label.grid(row=1, column=0, sticky='w')
            
            # Log section
            log_frame = ttk.LabelFrame(auto_frame, text="Log", padding=10)
            log_frame.grid(row=5, column=0, sticky='ew', pady=(0, 10))
            log_frame.columnconfigure(0, weight=1)
            log_frame.rowconfigure(0, weight=1)
            
            # Log text with scrollbar
            log_text_frame = ttk.Frame(log_frame)
            log_text_frame.grid(row=0, column=0, sticky='nsew')
            log_text_frame.columnconfigure(0, weight=1)
            log_text_frame.rowconfigure(0, weight=1)
            
            self.auto_log_text = tk.Text(log_text_frame, height=8, wrap='word', state='disabled')
            auto_log_scrollbar = ttk.Scrollbar(log_text_frame, orient='vertical', command=self.auto_log_text.yview)
            self.auto_log_text.configure(yscrollcommand=auto_log_scrollbar.set)
            
            self.auto_log_text.grid(row=0, column=0, sticky='nsew')
            auto_log_scrollbar.grid(row=0, column=1, sticky='ns')
            
        except Exception as e:
            print(f"Error building auto tab: {e}")
            import traceback
            traceback.print_exc()

    def get_default_openai_contexts(self):
        """Get a list of default contexts sent to OpenAI for analysis"""
        contexts = {
            "System Context": [
                "You are a casual Twitter user who replies naturally and briefly.",
                "Use conversational language and keep responses between 180-280 characters.",
                "No hashtags or emojis."
            ],
            "Tweet Analysis Context": [
                "Analyze tweet content for:",
                "- Topic and subject matter",
                "- Tone (casual, formal, excited, concerned, etc.)",
                "- Content type (news, opinion, question, announcement, etc.)",
                "- Sentiment (positive, negative, neutral)",
                "- Engagement level (high, medium, low)"
            ],
            "Reply Generation Instructions": [
                "Generate a brief, natural reply that:",
                "- Sounds like a real person, not AI",
                "- Uses casual, conversational language",
                "- Uses natural contractions (you're, that's, etc.)",
                "- Avoids overly formal or perfect responses",
                "- Keeps it brief and to the point",
                "- NO hashtags or emojis"
            ],
            "Character Limit Enforcement": [
                "Ensure reply is between 180-280 characters",
                "If too short, expand naturally with follow-up thoughts",
                "If too long, truncate to fit within limit",
                "Remove any remaining hashtags and emojis",
                "Clean whitespace and formatting"
            ],
            "Unique Generation Markers": [
                "For auto-yapping, add unique elements to prevent caching:",
                "- Account label",
                "- Timestamp",
                "- Random number",
                "- Unique ID",
                "This ensures each account gets different replies"
            ],
            "Custom Prompt Integration": [
                "If custom prompt provided:",
                "Include it in the generation context",
                "Allow user to specify reply style and tone",
                "Override default behavior with user preferences"
            ]
        }
        return contexts

    def analyze_tweet_context(self):
        """Analyze tweet context and generate AI comments"""
        tweet_url = self.tweet_url_entry.get().strip()
        if not tweet_url:
            self.log("Please enter a tweet URL.", is_error=True)
            return
        
        # Get selected accounts for scraping
        selected_indices = self.accounts_listbox.curselection()
        if not selected_indices:
            self.log("Please select at least one account for scraping.", is_error=True)
            return
        
        # Get filtered accounts based on current tag filter
        tag = self.selected_tag.get() if hasattr(self, 'selected_tag') else 'All'
        filtered_accounts = [a for a in self.accounts if tag == 'All' or tag in a.tags]
        selected_accounts = [filtered_accounts[i] for i in selected_indices]
        
        # Use the first selected account for scraping
        scraping_account = selected_accounts[0]
        
        # Start analysis in separate thread
        import threading
        thread = threading.Thread(target=self._analyze_tweet_context_worker, args=(tweet_url, scraping_account))
        thread.daemon = True
        thread.start()
    
    def _analyze_tweet_context_worker(self, tweet_url, scraping_account):
        """Worker thread for tweet context analysis"""
        try:
            self.log("🔍 Starting tweet context analysis...")
            
            # Scrape only tweet content (no comments)
            tweet_content, _, success = scrape_tweet_content_and_comments_with_account(scraping_account, tweet_url)
            
            if not success or not tweet_content.strip():
                self.log("❌ Failed to scrape tweet content. Check if URL is valid and account is logged in.", is_error=True)
                return
            
            self.log(f"📝 Tweet content: {tweet_content[:100]}...")
            
            # Store the scraped tweet content for later use
            self.scraped_tweet_content = tweet_content
            self.scraped_comments = []  # Empty since we're not using comments
            
            # Generate AI comment based only on tweet content
            if self.ai_enabled_var.get():
                self.log("🤖 Generating AI comment based on tweet content...")
                
                # Get custom prompt if provided
                custom_prompt = self.ai_prompt_entry.get('1.0', 'end-1c').strip()
                
                # Check if it's the placeholder text
                if custom_prompt == "Enter your custom instructions for how to reply to the tweet...":
                    custom_prompt = ""
                
                if custom_prompt:
                    self.log(f"🎯 Using custom instructions: {custom_prompt}")
                else:
                    self.log("ℹ️ No custom instructions provided, using default AI behavior")
                
                # Generate comment using AI
                self._generate_ai_comments_worker(tweet_content, {}, custom_prompt)
            else:
                self.log("ℹ️ AI is disabled. Enable AI to generate comments.")
                
        except Exception as e:
            self.log(f"❌ Error analyzing tweet context: {e}", is_error=True)

    def generate_ai_comments(self):
        """Generate AI comments for the analyzed tweet"""
        if not hasattr(self, 'scraped_tweet_content') or not self.scraped_tweet_content:
            self.log("No tweet content available. Please analyze a tweet first.", is_error=True)
            return
        
        # Get custom prompt if provided
        custom_prompt = self.ai_prompt_entry.get('1.0', 'end-1c').strip()
        
        # Check if it's the placeholder text
        if custom_prompt == "Enter your custom instructions for how to reply to the tweet...":
            custom_prompt = ""
        
        if custom_prompt:
            self.log(f"🎯 Using custom instructions: {custom_prompt}")
        else:
            self.log("ℹ️ No custom instructions provided, using default AI behavior")
        
        self.log("🤖 Generating AI comments...")
        threading.Thread(
            target=self._generate_ai_comments_worker,
            args=(self.scraped_tweet_content, {}, custom_prompt)
        ).start()

    def _generate_ai_comments_worker(self, tweet_content: str, analysis: Dict, custom_prompt: str = None):
        """Generate AI comments based on tweet content"""
        try:
            # Get current AI provider
            ai_provider = self.get_current_ai_provider()
            
            # Generate comment based only on tweet content
            if custom_prompt:
                self.log(f"🤖 Generating comment with custom prompt...")
                comment = ai_provider.generate_comment_from_tweet(tweet_content, custom_prompt)
            else:
                self.log(f"🤖 Generating comment based on tweet content...")
                comment = ai_provider.generate_comment_from_tweet(tweet_content)
            
            if comment:
                self.log(f"✅ Generated comment: {comment}")
                # Update the comment display
                self.after(0, lambda: self._update_ai_comments_display([comment]))
            else:
                self.log("❌ Failed to generate comment", is_error=True)
                
        except Exception as e:
            self.log(f"❌ Error generating AI comment: {e}", is_error=True)

    def _update_ai_comments_display(self, comments: List[str]):
        """Update the AI comments display with the generated comments"""
        # Clear previous comments
        self.ai_comments_text.delete('1.0', tk.END)
        
        if not comments:
            self.ai_comments_text.insert('1.0', "No AI comments generated yet.")
            return
        
        # Display the single comment with better formatting
        for i, comment in enumerate(comments, 1):
            self.ai_comments_text.insert(tk.END, f"💭 AI Comment {i}:\n")
            self.ai_comments_text.insert(tk.END, f"{comment}\n\n")
        
        # Auto-scroll to the end
        self.ai_comments_text.see(tk.END) 

    def start_auto_yapping(self):
        """Start auto-yapping process"""
        tweet_url = self.tweet_url_entry.get().strip()
        if not tweet_url:
            self.log("Tweet URL is required.", is_error=True)
            return
        
        # Get selected accounts
        selected_indices = self.accounts_listbox.curselection()
        if not selected_indices:
            self.log("Please select at least one account.", is_error=True)
            return
        
        tag = self.selected_tag.get() if hasattr(self, 'selected_tag') else 'All'
        filtered_accounts = [a for a in self.accounts if tag == 'All' or tag in a.tags]
        selected_accounts = [filtered_accounts[i] for i in selected_indices if i < len(filtered_accounts)]
        
        if not selected_accounts:
            self.log("No accounts selected.", is_error=True)
            return
        
        self.log(f"🚀 Starting auto-yapping with {len(selected_accounts)} accounts...")
        threading.Thread(target=self._auto_yapping_worker, args=(selected_accounts, tweet_url)).start()

    def _auto_yapping_worker(self, accounts, tweet_url):
        """Worker thread for auto-yapping"""
        try:
            # Get custom prompt if provided
            custom_prompt = self.ai_prompt_entry.get('1.0', 'end-1c').strip()
            
            # Check if it's the placeholder text
            if custom_prompt == "Enter your custom instructions for how to reply to the tweet...":
                custom_prompt = ""
            
            if custom_prompt:
                self.log(f"🎯 Using custom instructions for all accounts: {custom_prompt}")
            else:
                self.log("ℹ️ No custom instructions provided, using default AI behavior")
            
            for i, account in enumerate(accounts, 1):
                self.log(f"🤖 Processing account {i}/{len(accounts)}: {account.label}")
                
                if self.ai_enabled_var.get():
                    ai_provider = self.get_current_ai_provider()
                    
                    # Debug: Check if we have the required data
                    if not ai_provider:
                        self.log(f"❌ No AI provider available for {account.label}")
                        continue
                    
                    if not hasattr(self, 'scraped_tweet_content') or not self.scraped_tweet_content:
                        self.log(f"❌ No tweet content available for {account.label}. Please analyze tweet first.")
                        continue
                    
                    # Generate comment using tweet-only approach
                    self.log(f"🤖 Generating comment for {account.label}...")
                    comment = ai_provider.generate_comment_from_tweet(self.scraped_tweet_content, custom_prompt)
                    
                    if not comment:
                        self.log(f"❌ Failed to generate comment for {account.label}")
                        continue
                    
                    self.log(f"💭 Generated comment: {comment[:50]}...")
                    
                    max_retries = 3
                    for attempt in range(max_retries):
                        try:
                            success, message = reply_to_tweet(account, tweet_url, comment)
                            if success:
                                self.log(f"✅ Posted comment for {account.label}")
                                break
                            else:
                                if "Chrome" in message or "connection" in message.lower() or "reply button" in message.lower():
                                    self.log(f"⚠️ Chrome/reply button issue (attempt {attempt + 1}/{max_retries})")
                                    if attempt < max_retries - 1:
                                        time.sleep(5)
                                    else:
                                        self.log(f"❌ Failed to post comment for {account.label} after {max_retries} attempts")
                                else:
                                    self.log(f"❌ Failed to post comment for {account.label}: {message}")
                                    break
                        except Exception as e:
                            self.log(f"⚠️ Error posting comment (attempt {attempt + 1}/{max_retries}): {str(e)}")
                            if attempt < max_retries - 1:
                                time.sleep(5)
                            else:
                                self.log(f"❌ Failed to post comment for {account.label} after {max_retries} attempts")
                else:
                    self.log(f"⚠️ AI is disabled for {account.label}")
                
                if i < len(accounts):
                    time.sleep(3)
            self.log("🎉 Auto-yapping completed!")
        except Exception as e:
            self.log(f"❌ Error in auto-yapping: {e}")
            log_to_file('yapping_panel', f"Error in _auto_yapping_worker: {e}")

    def log(self, message, is_error=False):
        """Log a message to the log area"""
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
        log_to_file('yapping', message)

    def restore_log_messages(self):
        """Restore log messages from state"""
        for message in self.state['log_messages']:
            self.log_text.config(state='normal')
            self.log_text.insert('end', message + '\n')
            self.log_text.see('end')
            self.log_text.config(state='disabled') 

    def _on_prompt_focus_in(self, event):
        """Handle focus in for the AI prompt entry"""
        if self.ai_prompt_entry.get('1.0', tk.END).strip() == "Enter your custom instructions for how to reply to the tweet...":
            self.ai_prompt_entry.delete('1.0', tk.END)
            self.ai_prompt_entry.insert('1.0', "") # Clear placeholder

    def _on_prompt_focus_out(self, event):
        """Handle focus out for the AI prompt entry"""
        if not self.ai_prompt_entry.get('1.0', tk.END).strip():
            self.ai_prompt_entry.insert('1.0', "Enter your custom instructions for how to reply to the tweet...") # Restore placeholder
            self.ai_prompt_entry.see('1.0') # Scroll to the beginning 

    def _on_auto_prompt_focus_in(self, event):
        """Handle focus in for the auto AI prompt entry"""
        if self.auto_ai_prompt_entry.get('1.0', tk.END).strip() == "Enter custom instructions for auto replies (optional)...":
            self.auto_ai_prompt_entry.delete('1.0', tk.END)
            self.auto_ai_prompt_entry.insert('1.0', "")

    def _on_auto_prompt_focus_out(self, event):
        """Handle focus out for the auto AI prompt entry"""
        if not self.auto_ai_prompt_entry.get('1.0', tk.END).strip():
            self.auto_ai_prompt_entry.insert('1.0', "Enter custom instructions for auto replies (optional)...")

    def _on_review_checkbox_change(self):
        """Handle review comments checkbox change"""
        if hasattr(self, 'review_before_posting_var'):
            self.state['review_before_posting'] = self.review_before_posting_var.get()
            if self.review_before_posting_var.get():
                self.auto_log("📝 Review mode enabled - comments will be shown for approval before posting")
            else:
                self.auto_log("⚡ Review mode disabled - comments will be posted immediately")

    def start_auto_yapping_search(self):
        """Start auto yapping based on search query"""
        # Get the generated search query
        search_query = self.auto_generated_query.get().strip()
        if not search_query:
            self.auto_log("Please generate a search query first.", is_error=True)
            return
        
        # Get selected accounts
        selected_indices = self.auto_accounts_listbox.curselection()
        if not selected_indices:
            self.auto_log("Please select at least one account.", is_error=True)
            return
        
        # Get filtered accounts based on tag filter
        selected_tag = self.auto_selected_tag.get() if hasattr(self, 'auto_selected_tag') else 'All'
        if selected_tag == 'All':
            filtered_accounts = self.accounts
        else:
            filtered_accounts = [a for a in self.accounts if selected_tag in a.tags]
        
        selected_accounts = [filtered_accounts[i] for i in selected_indices if i < len(filtered_accounts)]
        
        if not selected_accounts:
            self.auto_log("No accounts selected.", is_error=True)
            return
        
        # Get settings
        try:
            min_interval = int(self.auto_min_interval.get())
            max_interval = int(self.auto_max_interval.get())
            max_tweets = int(self.auto_max_tweets.get())
            min_chars = int(self.auto_min_chars.get())
            max_chars = int(self.auto_max_chars.get())
        except ValueError:
            self.auto_log("Please enter valid numbers for intervals, max tweets, and character limits.", is_error=True)
            return
        
        # Get custom prompt
        custom_prompt = self.auto_custom_prompt.get().strip()
        
        self.auto_log(f"🚀 Starting Auto Yapping with {len(selected_accounts)} accounts...")
        self.auto_log(f"🔍 Search Query: {search_query}")
        self.auto_log(f"⏱️ Time Interval: {min_interval}-{max_interval} seconds")
        self.auto_log(f"📊 Max Tweets: {max_tweets}")
        self.auto_log(f"📝 Reply Length: {min_chars}-{max_chars} characters")
        if custom_prompt:
            self.auto_log(f"🎯 Custom Instructions: {custom_prompt}")
        else:
            self.auto_log("ℹ️ No custom instructions provided")
        
        # Start auto yapping in separate thread
        import threading
        self.auto_yapping_running = True
        self.auto_yapping_paused = False
        
        # Update UI
        self.start_auto_button.config(state='disabled')
        self.stop_auto_button.config(state='normal')
        self.pause_auto_button.config(state='normal')
        
        thread = threading.Thread(
            target=self._auto_yapping_search_worker,
            args=(search_query, selected_accounts, min_interval, max_interval, max_tweets, custom_prompt, min_chars, max_chars)
        )
        thread.daemon = True
        thread.start()

    def stop_auto_yapping_search(self):
        """Stop auto yapping"""
        self.auto_yapping_running = False
        self.auto_yapping_paused = False
        self.auto_log("⏹️ Auto yapping stopped by user.")
        
        # Update UI
        self.start_auto_button.config(state='normal')
        self.stop_auto_button.config(state='disabled')
        self.pause_auto_button.config(state='disabled')

    def pause_auto_yapping_search(self):
        """Pause/resume auto yapping"""
        if self.auto_yapping_paused:
            self.auto_yapping_paused = False
            self.pause_auto_button.config(text="⏸️ Pause")
            self.auto_log("▶️ Auto yapping resumed.")
        else:
            self.auto_yapping_paused = True
            self.pause_auto_button.config(text="▶️ Resume")
            self.auto_log("⏸️ Auto yapping paused.")

    def auto_log(self, message, is_error=False):
        """Log message to auto yapping log with timestamp"""
        try:
            timestamp = time.strftime("[%H:%M:%S]")
            log_message = f"{timestamp} {message}"
            
            # Use after() to update UI from main thread
            self.after(0, lambda: self._update_auto_log_safe(log_message, is_error))
            
        except Exception as e:
            print(f"Error in auto_log: {e}")

    def _update_auto_log_safe(self, log_message, is_error=False):
        """Safely update the auto log from main thread"""
        try:
            if hasattr(self, 'auto_log_text') and self.auto_log_text:
                # Enable the text widget for writing
                self.auto_log_text.config(state='normal')
                
                # Configure tag for error messages
                if is_error:
                    self.auto_log_text.tag_configure("error", foreground="red")
                    self.auto_log_text.insert('end', log_message + '\n', "error")
                else:
                    self.auto_log_text.insert('end', log_message + '\n')
                
                # Auto-scroll to bottom
                self.auto_log_text.see('end')
                
                # Limit log size to prevent memory issues
                lines = self.auto_log_text.get('1.0', 'end').split('\n')
                if len(lines) > 1000:  # Keep only last 1000 lines
                    self.auto_log_text.delete('1.0', f'{len(lines)-1000}.0')
                
                # Disable the text widget to make it read-only
                self.auto_log_text.config(state='disabled')
                    
        except Exception as e:
            print(f"Error updating auto log: {e}")
            import traceback
            traceback.print_exc()

    def update_progress(self, current, total, stats):
        """Update progress bar and stats safely from main thread"""
        try:
            if hasattr(self, 'auto_progress_bar') and self.auto_progress_bar:
                # Calculate percentage
                percentage = (current / total) * 100 if total > 0 else 0
                
                # Update progress bar
                self.auto_progress_bar['value'] = percentage
                
                # Update stats labels
                if hasattr(self, 'auto_stats_label') and self.auto_stats_label:
                    stats_text = f"Processed: {stats.get('processed', 0)} | Successful: {stats.get('successful', 0)} | Failed: {stats.get('failed', 0)}"
                    self.auto_stats_label.config(text=stats_text)
                    
        except Exception as e:
            print(f"Error updating progress: {e}")

    def _auto_yapping_search_worker(self, search_query, accounts, min_interval, max_interval, max_tweets, custom_prompt, min_chars, max_chars):
        """Worker thread for auto yapping search"""
        try:
            # Get custom prompt if provided
            if custom_prompt:
                self.auto_log(f"🎯 Using custom instructions: {custom_prompt}")
            else:
                self.auto_log("ℹ️ No custom instructions provided, using default AI behavior")
            
            # Build search URL properly
            import urllib.parse
            encoded_query = urllib.parse.quote(search_query)
            search_url = f"https://x.com/search?q={encoded_query}&src=typed_query&f=top"
            
            self.auto_log(f"🔍 Searching: {search_url}")
            
            # Get tweets from search results
            tweets = self._get_tweets_from_search(search_url, max_tweets, accounts)
            
            if not tweets:
                self.auto_log("❌ No tweets found for the search query.", is_error=True)
                return
            
            self.auto_log(f"📊 Found {len(tweets)} tweets to process")
            
            # Process tweets
            for i, tweet_url in enumerate(tweets):
                if not self.auto_yapping_running:
                    break
                
                while self.auto_yapping_paused:
                    time.sleep(1)
                    if not self.auto_yapping_running:
                        return
                
                # Clean the URL to get base tweet URL
                base_tweet_url = tweet_url.split('/photo/')[0].split('/video/')[0].split('/gif/')[0]
                
                # Check if already replied
                if base_tweet_url in self.replied_tweets_db:
                    self.auto_log(f"⏭️ Skipping already replied tweet: {base_tweet_url}")
                    continue
                
                self.auto_log(f"📝 Processing tweet {i+1}/{len(tweets)}: {base_tweet_url}")
                
                # Process this tweet
                success = self._process_single_tweet(base_tweet_url, accounts, custom_prompt, min_chars, max_chars)
                
                if success:
                    self.auto_yapping_stats['successful'] += 1
                    self.replied_tweets_db[base_tweet_url] = time.time()
                else:
                    self.auto_yapping_stats['failed'] += 1
                
                self.auto_yapping_stats['processed'] += 1
                
                # Update progress
                self.after(0, lambda: self.update_progress(i+1, len(tweets), self.auto_yapping_stats))
                
                # Wait before next tweet - but only if review is not enabled or review is complete
                if i < len(tweets) - 1 and self.auto_yapping_running:
                    # Check if review is enabled
                    review_enabled = hasattr(self, 'review_before_posting_var') and self.review_before_posting_var.get()
                    
                    if review_enabled:
                        # Wait for review dialog to be closed
                        self.auto_log("⏳ Waiting for user review completion...")
                        while hasattr(self, '_review_dialog_open') and self._review_dialog_open:
                            time.sleep(0.5)  # Check every 500ms
                            if not self.auto_yapping_running:
                                return
                        
                        # After review is complete, apply the time interval
                        wait_time = random.randint(min_interval, max_interval)
                        self.auto_log(f"⏱️ Review completed. Waiting {wait_time} seconds before next tweet...")
                        time.sleep(wait_time)
                    else:
                        # No review enabled, apply timer immediately
                        wait_time = random.randint(min_interval, max_interval)
                        self.auto_log(f"⏱️ Waiting {wait_time} seconds before next tweet...")
                        time.sleep(wait_time)
            
            self.auto_log("🎉 Auto yapping completed!")
            
        except Exception as e:
            self.auto_log(f"❌ Error in auto yapping: {e}", is_error=True)
        finally:
            # Update UI
            self.after(0, lambda: self.stop_auto_button.config(state='disabled'))
            self.after(0, lambda: self.start_auto_button.config(state='normal'))
            self.after(0, lambda: self.pause_auto_button.config(state='disabled'))
            self.auto_yapping_running = False

    def _get_tweets_from_search(self, search_url, max_tweets, selected_accounts=None):
        """Get tweet URLs from search results"""
        try:
            # Use the first selected account to scrape search results
            if not selected_accounts:
                # Fallback: Get selected accounts from the listbox
                selected_indices = self.auto_accounts_listbox.curselection()
                if not selected_indices:
                    self.auto_log("❌ No accounts selected for scraping.", is_error=True)
                    return []
                
                # Get the selected accounts
                selected_accounts = []
                for index in selected_indices:
                    account_label = self.auto_accounts_listbox.get(index)
                    # Find the account object
                    for acc in self.accounts:
                        if acc.label == account_label:
                            selected_accounts.append(acc)
                            break
            
            if not selected_accounts:
                self.auto_log("❌ No valid accounts found for scraping.", is_error=True)
                return []
            
            scraping_account = selected_accounts[0]  # Use first selected account
            self.auto_log(f"🔍 Using account '{scraping_account.label}' for scraping search results")
            
            from selenium_manager import get_global_driver_manager
            driver = get_global_driver_manager().get_driver(scraping_account)
            if not driver:
                self.auto_log("❌ Failed to get driver for scraping.", is_error=True)
                return []
            
            try:
                self.auto_log(f"🌐 Navigating to search URL: {search_url}")
                driver.get(search_url)
                time.sleep(5)  # Wait longer for search results to load
                
                # Check if we're on the search page
                current_url = driver.current_url
                self.auto_log(f"📍 Current URL: {current_url}")
                
                # Check if redirected to login
                if 'login' in current_url.lower() or 'i/flow/login' in current_url.lower():
                    self.auto_log("❌ Account is not logged in. Please log in first.")
                    return []
                
                if 'search' not in current_url.lower():
                    self.auto_log("⚠️ Not on search page, trying to navigate again...")
                    driver.get(search_url)
                    time.sleep(3)
                    
                    # Check again after retry
                    current_url = driver.current_url
                    if 'login' in current_url.lower() or 'i/flow/login' in current_url.lower():
                        self.auto_log("❌ Account is not logged in after retry. Please log in first.")
                        return []
                
                # Wait for search results to load
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, 'article[data-testid="tweet"]'))
                    )
                    self.auto_log("✅ Search results loaded successfully")
                except Exception as e:
                    self.auto_log(f"⚠️ Search results not found: {e}")
                    # Check if we're still on search page
                    current_url = driver.current_url
                    if 'search' not in current_url.lower():
                        self.auto_log("❌ Not on search page. Check if account is logged in.")
                        return []
                
                # Scroll to load more tweets
                self.auto_log("📜 Scrolling to load tweets...")
                for i in range(5):  # Scroll 5 times
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(2)
                    self.auto_log(f"📜 Scroll {i+1}/5 completed")
                
                # Extract tweet URLs with better selectors
                tweet_urls = []
                
                # Method 1: Find all tweet articles and extract URLs
                tweet_articles = driver.find_elements(By.CSS_SELECTOR, 'article[data-testid="tweet"]')
                self.auto_log(f"📊 Found {len(tweet_articles)} tweet articles")
                
                for i, article in enumerate(tweet_articles):
                    try:
                        # Look for links within the article
                        links = article.find_elements(By.CSS_SELECTOR, 'a[href*="/status/"]')
                        for link in links:
                            href = link.get_attribute('href')
                            if href and '/status/' in href:
                                # Clean the URL to get the base tweet URL (remove photo/1, etc.)
                                base_url = href.split('/photo/')[0].split('/video/')[0].split('/gif/')[0]
                                if base_url not in tweet_urls:
                                    tweet_urls.append(base_url)
                                    self.auto_log(f"📝 Found tweet {len(tweet_urls)}: {base_url}")
                                    break  # Only take the first link per article
                    except Exception as e:
                        continue
                
                # Method 2: If Method 1 didn't work well, try direct link extraction
                if len(tweet_urls) < 5:
                    self.auto_log("🔄 Trying alternative URL extraction method...")
                    all_links = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/status/"]')
                    self.auto_log(f"🔗 Found {len(all_links)} total links")
                    
                    for link in all_links:
                        href = link.get_attribute('href')
                        if href and '/status/' in href:
                            # Clean the URL to get the base tweet URL
                            base_url = href.split('/photo/')[0].split('/video/')[0].split('/gif/')[0]
                            if base_url not in tweet_urls:
                                tweet_urls.append(base_url)
                                self.auto_log(f"📝 Found tweet {len(tweet_urls)}: {base_url}")
                
                # Remove duplicates and limit
                unique_urls = list(dict.fromkeys(tweet_urls))[:max_tweets]
                
                self.auto_log(f"📊 Found {len(tweet_urls)} total URLs")
                self.auto_log(f"📊 Extracted {len(unique_urls)} unique tweets")
                
                # Log some example URLs for debugging
                for i, url in enumerate(unique_urls[:3]):
                    self.auto_log(f"📝 Example URL {i+1}: {url}")
                
                if len(unique_urls) == 0:
                    self.auto_log("❌ No tweets found in search results. Check if the search query is valid.")
                
                return unique_urls
                
            finally:
                driver.quit()
                
        except Exception as e:
            self.auto_log(f"❌ Error getting tweets from search: {e}", is_error=True)
            return []

    def _process_single_tweet(self, tweet_url, accounts, custom_prompt, min_chars, max_chars):
        """Process a single tweet with all accounts"""
        try:
            # Use the first selected account for scraping
            scraping_account = accounts[0] if accounts else None
            if not scraping_account:
                self.auto_log("❌ No accounts available for scraping.")
                return False
            
            # First check if tweet is accessible
            self.auto_log(f"🔍 Checking tweet accessibility using account: {scraping_account.label}")
            from selenium_manager import check_tweet_accessibility, get_global_driver_manager
            
            driver_manager = get_global_driver_manager()
            driver = driver_manager.get_driver(scraping_account)
            
            if not driver:
                self.auto_log(f"❌ No driver available for {scraping_account.label}")
                return False
            
            # Check accessibility first
            if not check_tweet_accessibility(driver, tweet_url):
                self.auto_log(f"❌ Tweet is not accessible: {tweet_url}")
                return False
            
            self.auto_log(f"✅ Tweet is accessible, scraping content...")
            tweet_content, comments, success = scrape_tweet_content_and_comments_with_account(scraping_account, tweet_url)
            
            if not success or not tweet_content.strip():
                self.auto_log(f"❌ Failed to scrape tweet content: {tweet_url}")
                return False
            
            # Generate AI reply for each account separately
            ai_provider = self.get_current_ai_provider()
            if not ai_provider:
                self.auto_log("❌ No AI provider available.")
                return False
            
            # Clean the tweet content for AI and include comments context
            cleaned_content = tweet_content[:500]  # Limit content length
            
            # Store comments for review dialog
            self.scraped_comments = comments
            
            # Add comments context if available
            if comments and len(comments) > 0:
                comments_context = "\n\n--- Comments Context ---\n"
                # Include up to 5 comments for context
                for i, comment in enumerate(comments[:5]):
                    comments_context += f"Comment {i+1}: {comment}\n"
                cleaned_content += comments_context
                self.auto_log(f"📝 Added {len(comments[:5])} comments to AI context")
            
            # Generate comments for all accounts
            generated_comments = {}
            for account in accounts:
                if not self.auto_yapping_running:
                    break
                
                self.auto_log(f"🤖 Generating reply for account: {account.label}")
                
                # Generate unique reply for this specific account
                unique_reply = self._generate_unique_reply(ai_provider, cleaned_content, custom_prompt, account.label, tweet_url, min_chars, max_chars)
                
                if not unique_reply:
                    self.auto_log(f"❌ Failed to generate unique reply for {account.label}")
                    continue
                
                generated_comments[account.label] = unique_reply
                self.auto_log(f"💭 Generated unique reply for {account.label}: {unique_reply[:50]}...")
            
            # Check if review is enabled
            if hasattr(self, 'review_before_posting_var') and self.review_before_posting_var.get():
                # Show review dialog
                self.auto_log(f"📝 Showing review dialog for tweet: {tweet_url}")
                
                # Set a flag to indicate the dialog is open
                self._review_dialog_open = True
                
                # Use after() to ensure dialog is shown in main thread
                self.after(0, lambda: self._show_review_dialog(
                    tweet_url, tweet_content, accounts, generated_comments, custom_prompt, min_chars, max_chars
                ))
                
                # Wait for dialog to be closed (this will be handled by the dialog)
                return True
            else:
                # Post immediately without review
                success_count = 0
                for account in accounts:
                    if not self.auto_yapping_running:
                        break
                    
                    if account.label not in generated_comments:
                        continue
                    
                    comment = generated_comments[account.label]
                    self.auto_log(f"🤖 Replying with account: {account.label}")
                    
                    try:
                        from selenium_manager import reply_to_tweet
                        success, message = reply_to_tweet(account, tweet_url, comment)
                        
                        if success:
                            self.auto_log(f"✅ Successfully replied with {account.label}")
                            success_count += 1
                        else:
                            self.auto_log(f"❌ Failed to reply with {account.label}: {message}")
                            
                    except Exception as e:
                        self.auto_log(f"❌ Error replying with {account.label}: {e}")
                    
                    # Wait between accounts
                    if account != accounts[-1]:
                        time.sleep(random.randint(10, 30))
                
                return success_count > 0
            
        except Exception as e:
            self.auto_log(f"❌ Error processing tweet: {e}", is_error=True)
            return False 

    def _generate_unique_reply(self, ai_provider, tweet_content, custom_prompt, account_label, tweet_url, min_chars, max_chars):
        """Generate a unique reply for each account to avoid caching"""
        try:
            # Add unique elements to prevent caching
            import random
            import time
            
            # Create unique content by adding account, timestamp, and random elements
            unique_content = f"{tweet_content}\n\n[Account: {account_label}]\n[Timestamp: {int(time.time())}]\n[Random: {random.randint(1000, 9999)}]\n[UniqueID: {random.randint(100000, 999999)}]"
            
            # Generate reply with enhanced context and character limits
            # The tweet_content now includes comments context from _process_single_tweet
            reply_text = ai_provider.generate_comment_from_tweet_with_limits(unique_content, custom_prompt, min_chars, max_chars)
            
            if not reply_text:
                return None
            
            # Remove any remaining hashtags and emojis
            import re
            reply_text = re.sub(r'#\w+', '', reply_text)  # Remove hashtags
            reply_text = re.sub(r'[^\x00-\x7F\u00A0-\uFFFF]', '', reply_text)  # Remove emojis
            reply_text = re.sub(r'\s+', ' ', reply_text).strip()  # Clean whitespace
            
            # Ensure it's within character limit
            if len(reply_text) > max_chars:
                reply_text = reply_text[:max_chars]
            elif len(reply_text) < min_chars:
                # If too short, try to expand naturally
                reply_text = ai_provider._expand_short_reply_with_limits(reply_text, tweet_content, min_chars, max_chars)
            
            # Final length check
            if len(reply_text) < min_chars:
                # If still too short, add a natural follow-up
                follow_ups = [
                    " What do you think about this?",
                    " I'm curious about your thoughts.",
                    " How has your experience been?",
                    " Any insights to share?",
                    " What's your take on this?"
                ]
                reply_text += random.choice(follow_ups)
                if len(reply_text) > max_chars:
                    reply_text = reply_text[:max_chars]
            
            return reply_text
            
        except Exception as e:
            self.auto_log(f"❌ Error generating unique reply: {e}", is_error=True)
            return None

    def _show_review_dialog(self, tweet_url, tweet_content, accounts, generated_comments, custom_prompt, min_chars, max_chars):
        """Show review dialog for generated comments"""
        try:
            # Create review dialog
            review_dialog = tk.Toplevel(self)
            review_dialog.title("Review Comments Before Posting")
            review_dialog.geometry("1000x800")  # Increased size
            review_dialog.minsize(900, 700)  # Set minimum size
            review_dialog.transient(self)
            review_dialog.grab_set()
            
            # Center the dialog on screen
            review_dialog.update_idletasks()
            x = (review_dialog.winfo_screenwidth() // 2) - (1000 // 2)
            y = (review_dialog.winfo_screenheight() // 2) - (800 // 2)
            review_dialog.geometry(f"1000x800+{x}+{y}")
            
            # Main frame with scrollbar
            main_canvas = tk.Canvas(review_dialog)
            main_scrollbar = ttk.Scrollbar(review_dialog, orient="vertical", command=main_canvas.yview)
            main_frame = ttk.Frame(main_canvas)
            
            main_canvas.configure(yscrollcommand=main_scrollbar.set)
            
            # Pack scrollbar and canvas
            main_scrollbar.pack(side="right", fill="y")
            main_canvas.pack(side="left", fill="both", expand=True)
            
            # Create window in canvas
            main_canvas.create_window((0, 0), window=main_frame, anchor="nw")
            
            # Configure canvas scrolling
            def configure_scroll_region(event):
                main_canvas.configure(scrollregion=main_canvas.bbox("all"))
            
            main_frame.bind("<Configure>", configure_scroll_region)
            
            # Bind mouse wheel to canvas
            def on_mousewheel(event):
                main_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            
            main_canvas.bind_all("<MouseWheel>", on_mousewheel)
            
            # Content padding
            content_frame = ttk.Frame(main_frame)
            content_frame.pack(fill='both', expand=True, padx=20, pady=20)
            
            # Tweet info
            tweet_frame = ttk.LabelFrame(content_frame, text="📝 Tweet Information", padding="10")
            tweet_frame.pack(fill='x', pady=(0, 20))
            
            ttk.Label(tweet_frame, text=f"Tweet URL: {tweet_url}", font=('Segoe UI', 9, 'bold')).pack(anchor='w')
            ttk.Label(tweet_frame, text="Tweet Content:", font=('Segoe UI', 9, 'bold')).pack(anchor='w', pady=(10, 5))
            
            # Show tweet content with scrollbar (full content, not truncated)
            tweet_text_frame = ttk.Frame(tweet_frame)
            tweet_text_frame.pack(fill='x', pady=(0, 10))
            
            tweet_text = tk.Text(tweet_text_frame, height=6, width=80, wrap='word', state='disabled')
            tweet_scrollbar = ttk.Scrollbar(tweet_text_frame, orient="vertical", command=tweet_text.yview)
            tweet_text.configure(yscrollcommand=tweet_scrollbar.set)
            
            tweet_text.pack(side='left', fill='both', expand=True)
            tweet_scrollbar.pack(side='right', fill='y')
            
            tweet_text.config(state='normal')
            tweet_text.insert('1.0', tweet_content)
            tweet_text.config(state='disabled')
            
            # Add comment context display if available
            if hasattr(self, 'scraped_comments') and self.scraped_comments:
                comment_context_frame = ttk.LabelFrame(content_frame, text="💬 Comment Context (Used for AI Generation)", padding="10")
                comment_context_frame.pack(fill='x', pady=(0, 20))
                
                comment_context_text = tk.Text(comment_context_frame, height=4, width=80, wrap='word', state='disabled')
                comment_context_scrollbar = ttk.Scrollbar(comment_context_frame, orient="vertical", command=comment_context_text.yview)
                comment_context_text.configure(yscrollcommand=comment_context_scrollbar.set)
                
                comment_context_text.pack(side='left', fill='both', expand=True)
                comment_context_scrollbar.pack(side='right', fill='y')
                
                comment_context_text.config(state='normal')
                comment_context = "\n".join([f"• {comment}" for comment in self.scraped_comments[:5]])
                comment_context_text.insert('1.0', comment_context)
                comment_context_text.config(state='disabled')
            
            # Comments review frame
            comments_frame = ttk.LabelFrame(content_frame, text="💬 Review Generated Comments", padding="10")
            comments_frame.pack(fill='both', expand=True, pady=(0, 20))
            
            # Create scrollable frame for comments
            canvas = tk.Canvas(comments_frame)
            scrollbar = ttk.Scrollbar(comments_frame, orient="vertical", command=canvas.yview)
            scrollable_frame = ttk.Frame(canvas)
            
            scrollable_frame.bind(
                "<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
            )
            
            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)
            
            # Store edited comments
            edited_comments = {}
            comment_widgets = {}
            
            # Create comment edit sections
            for i, account in enumerate(accounts):
                if account.label not in generated_comments:
                    continue
                    
                # Account comment frame
                account_frame = ttk.LabelFrame(scrollable_frame, text=f"Account: {account.label}", padding="10")
                account_frame.pack(fill='x', pady=(0, 10))
                
                # Original comment display
                original_comment = generated_comments[account.label]
                ttk.Label(account_frame, text="Generated Comment:", font=('Segoe UI', 9, 'bold')).pack(anchor='w')
                
                original_text = tk.Text(account_frame, height=2, width=80, wrap='word', state='disabled')
                original_text.pack(fill='x', pady=(0, 5))
                original_text.config(state='normal')
                original_text.insert('1.0', original_comment)
                original_text.config(state='disabled')
                
                # Edit comment section
                ttk.Label(account_frame, text="Edit Comment (optional):", font=('Segoe UI', 9, 'bold')).pack(anchor='w', pady=(10, 5))
                
                edit_text = tk.Text(account_frame, height=3, width=80, wrap='word')
                edit_text.pack(fill='x', pady=(0, 5))
                edit_text.insert('1.0', original_comment)
                
                # Character count label
                char_count_label = tk.Label(account_frame, text=f"Characters: {len(original_comment)}/{max_chars}", 
                                          font=('Segoe UI', 8), fg='green' if len(original_comment) <= max_chars else 'red')
                char_count_label.pack(anchor='w')
                
                # Store references
                edited_comments[account.label] = original_comment
                comment_widgets[account.label] = {
                    'edit_text': edit_text,
                    'char_count_label': char_count_label,
                    'account': account
                }
                
                # Bind character count update
                def update_char_count(account_label=account.label):
                    text = comment_widgets[account_label]['edit_text'].get('1.0', 'end-1c')
                    count = len(text)
                    color = 'green' if count <= max_chars else 'red'
                    comment_widgets[account_label]['char_count_label'].config(text=f"Characters: {count}/{max_chars}", fg=color)
                    edited_comments[account_label] = text
                
                edit_text.bind('<KeyRelease>', lambda e, acc=account.label: update_char_count(acc))
            
            # Pack canvas and scrollbar
            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            
            # Action buttons - Fixed at bottom
            button_frame = ttk.Frame(content_frame)
            button_frame.pack(fill='x', pady=(20, 0), side='bottom')
            
            # Button container with proper spacing
            button_container = ttk.Frame(button_frame)
            button_container.pack(expand=True)
            
            def approve_and_post():
                """Approve and post all comments"""
                try:
                    # Validate character counts
                    invalid_comments = []
                    for account_label, comment in edited_comments.items():
                        if len(comment) > max_chars:
                            invalid_comments.append(f"{account_label}: {len(comment)} chars (max {max_chars})")
                    
                    if invalid_comments:
                        messagebox.showerror("Character Limit Exceeded", 
                                          f"The following comments exceed the character limit:\n\n" + "\n".join(invalid_comments))
                        return
                    
                    # Post comments
                    success_count = 0
                    for account_label, comment in edited_comments.items():
                        if comment.strip():  # Only post non-empty comments
                            try:
                                from selenium_manager import reply_to_tweet
                                success, message = reply_to_tweet(comment_widgets[account_label]['account'], tweet_url, comment)
                                if success:
                                    success_count += 1
                                    self.auto_log(f"✅ Posted comment for {account_label}")
                                else:
                                    self.auto_log(f"❌ Failed to post comment for {account_label}: {message}")
                            except Exception as e:
                                self.auto_log(f"❌ Error posting comment for {account_label}: {e}")
                    
                    self.auto_log(f"✅ Posted {success_count}/{len(edited_comments)} comments")
                    # Clear the review dialog flag before destroying
                    if hasattr(self, '_review_dialog_open'):
                        self._review_dialog_open = False
                    review_dialog.destroy()
                    
                except Exception as e:
                    messagebox.showerror("Error", f"Error posting comments: {e}")
            
            def skip_tweet():
                """Skip this tweet"""
                self.auto_log(f"⏭️ Skipped tweet: {tweet_url}")
                # Clear the review dialog flag before destroying
                if hasattr(self, '_review_dialog_open'):
                    self._review_dialog_open = False
                review_dialog.destroy()
            
            def edit_individual_comment(account_label):
                """Edit individual comment in a separate dialog"""
                if account_label in comment_widgets:
                    self._edit_individual_comment_dialog(review_dialog, account_label, comment_widgets[account_label])
            
            # Buttons with better spacing and visibility
            ttk.Button(button_container, text="✅ Approve & Post All", command=approve_and_post, style='Accent.TButton').pack(side='left', padx=(0, 15))
            ttk.Button(button_container, text="⏭️ Skip Tweet", command=skip_tweet).pack(side='left', padx=(0, 15))
            ttk.Button(button_container, text="❌ Cancel", command=lambda: [setattr(self, '_review_dialog_open', False) if hasattr(self, '_review_dialog_open') else None, review_dialog.destroy()]).pack(side='right')
            
            # Ensure buttons are visible by scrolling to bottom if needed
            def ensure_buttons_visible():
                main_canvas.yview_moveto(1.0)  # Scroll to bottom
                review_dialog.after(100, lambda: main_canvas.yview_moveto(1.0))  # Double-check
            
            review_dialog.after(500, ensure_buttons_visible)  # Ensure buttons are visible after dialog loads
            
        except Exception as e:
            self.auto_log(f"❌ Error showing review dialog: {e}", is_error=True)
            messagebox.showerror("Error", f"Error showing review dialog: {e}")

    def _edit_individual_comment_dialog(self, parent_dialog, account_label, comment_widget):
        """Edit individual comment in a separate dialog"""
        try:
            # Create edit dialog
            edit_dialog = tk.Toplevel(parent_dialog)
            edit_dialog.title(f"Edit Comment - {account_label}")
            edit_dialog.geometry("600x400")
            edit_dialog.transient(parent_dialog)
            edit_dialog.grab_set()
            
            # Main frame
            main_frame = ttk.Frame(edit_dialog)
            main_frame.pack(fill='both', expand=True, padx=20, pady=20)
            
            # Account info
            ttk.Label(main_frame, text=f"Editing comment for: {account_label}", font=('Segoe UI', 12, 'bold')).pack(anchor='w', pady=(0, 20))
            
            # Comment edit area
            ttk.Label(main_frame, text="Edit your comment:", font=('Segoe UI', 10, 'bold')).pack(anchor='w')
            
            edit_text = tk.Text(main_frame, height=8, width=70, wrap='word')
            edit_text.pack(fill='both', expand=True, pady=(10, 10))
            edit_text.insert('1.0', comment_widget['edit_text'].get('1.0', 'end-1c'))
            
            # Character count
            char_count_label = tk.Label(main_frame, text=f"Characters: {len(edit_text.get('1.0', 'end-1c'))}/280", 
                                      font=('Segoe UI', 9))
            char_count_label.pack(anchor='w')
            
            def update_char_count():
                text = edit_text.get('1.0', 'end-1c')
                count = len(text)
                color = 'green' if count <= 280 else 'red'
                char_count_label.config(text=f"Characters: {count}/280", fg=color)
            
            edit_text.bind('<KeyRelease>', lambda e: update_char_count())
            
            # Buttons
            button_frame = ttk.Frame(main_frame)
            button_frame.pack(fill='x', pady=(20, 0))
            
            def save_changes():
                """Save changes to the main dialog"""
                new_text = edit_text.get('1.0', 'end-1c')
                comment_widget['edit_text'].delete('1.0', 'end')
                comment_widget['edit_text'].insert('1.0', new_text)
                edit_dialog.destroy()
            
            def cancel_edit():
                """Cancel editing"""
                edit_dialog.destroy()
            
            ttk.Button(button_frame, text="💾 Save Changes", command=save_changes).pack(side='left', padx=(0, 10))
            ttk.Button(button_frame, text="❌ Cancel", command=cancel_edit).pack(side='right')
            
        except Exception as e:
            messagebox.showerror("Error", f"Error editing comment: {e}")

    def refresh_auto_accounts_list(self):
        """Refresh the auto yapping accounts list with tag filtering"""
        try:
            if hasattr(self, 'auto_accounts_listbox') and self.auto_accounts_listbox is not None:
                self.auto_accounts_listbox.delete(0, tk.END)
                
                # Get selected tag filter
                selected_tag = self.auto_selected_tag.get() if hasattr(self, 'auto_selected_tag') else 'All'
                
                # Filter accounts based on tag
                if selected_tag == 'All':
                    filtered_accounts = self.accounts
                else:
                    filtered_accounts = [a for a in self.accounts if selected_tag in a.tags]
                
                # Add accounts to listbox
                for account in filtered_accounts:
                    display_text = f"{account.label} ({account.username})"
                    if hasattr(account, 'tags') and account.tags:
                        display_text += f" [{' '.join(account.tags)}]"
                    self.auto_accounts_listbox.insert(tk.END, display_text)
                
                # Update tag filter dropdown
                if hasattr(self, 'auto_tag_filter_dropdown'):
                    all_tags = set()
                    for account in self.accounts:
                        if hasattr(account, 'tags'):
                            all_tags.update(account.tags)
                    
                    tag_values = ['All'] + sorted(list(all_tags))
                    self.auto_tag_filter_dropdown['values'] = tag_values
                
                self.auto_log(f"📋 Loaded {len(filtered_accounts)} accounts for auto yapping (filter: {selected_tag})")
                if selected_tag != 'All':
                    self.auto_log(f"🏷️ Filtered by tag: {selected_tag}")
                
        except Exception as e:
            self.auto_log(f"❌ Error refreshing auto accounts list: {e}", is_error=True)
            import traceback
            traceback.print_exc()

    def display_default_openai_contexts(self):
        """Display the default OpenAI contexts in a readable format"""
        contexts = self.get_default_openai_contexts()
        
        print("\n" + "="*80)
        print("DEFAULT OPENAI CONTEXTS SENT TO AI")
        print("="*80)
        
        for category, context_list in contexts.items():
            print(f"\n📋 {category.upper()}:")
            print("-" * 50)
            for item in context_list:
                print(f"  • {item}")
        
        print("\n" + "="*80)
        print("DETAILED ANALYSIS OF CONTEXTS:")
        print("="*80)
        
        print("\n🔍 **System Context**:")
        print("   - Defines the AI's role as a casual Twitter user")
        print("   - Sets character limits (180-280 characters)")
        print("   - Prohibits hashtags and emojis")
        
        print("\n📊 **Tweet Analysis Context**:")
        print("   - Analyzes tweet topic, tone, content type, sentiment")
        print("   - Determines engagement level")
        print("   - Provides context for generating appropriate replies")
        
        print("\n💬 **Reply Generation Instructions**:")
        print("   - Ensures human-like, conversational responses")
        print("   - Uses natural contractions and casual language")
        print("   - Avoids overly formal or perfect responses")
        
        print("\n📏 **Character Limit Enforcement**:")
        print("   - Enforces 180-280 character limits")
        print("   - Expands short replies naturally")
        print("   - Truncates long replies to fit limits")
        print("   - Removes hashtags, emojis, and cleans formatting")
        
        print("\n🔄 **Unique Generation Markers**:")
        print("   - Adds account labels, timestamps, random numbers")
        print("   - Prevents AI caching for auto-yapping")
        print("   - Ensures each account gets different replies")
        
        print("\n⚙️ **Custom Prompt Integration**:")
        print("   - Allows user-defined reply styles and tones")
        print("   - Overrides default behavior with user preferences")
        print("   - Integrates custom instructions into generation context")
        
        print("\n" + "="*80)
        return contexts

    def _on_auto_tag_filter_change(self, event=None):
        """Handle auto yapping tag filter change"""
        try:
            selected_tag = self.auto_selected_tag.get()
            self.auto_log(f"🏷️ Account filter changed to: {selected_tag}")
            self.refresh_auto_accounts_list()
        except Exception as e:
            self.auto_log(f"❌ Error changing tag filter: {e}", is_error=True)
    
    def _update_auto_search_query(self):
        """Update the generated search query based on user inputs"""
        try:
            # Get keywords/phrases
            keywords = self.auto_keywords_entry.get().strip()
            if not keywords:
                keywords = '"cysic" OR @cysic_xyz'
            
            # Build the query
            query_parts = []
            
            # Add keywords
            query_parts.append(f"({keywords})")
            
            # Add filters
            if self.auto_filter_verified.get():
                query_parts.append("filter:blue_verified")
            
            if self.auto_filter_native_retweets.get():
                query_parts.append("-filter:nativeretweets")
            
            if self.auto_filter_retweets.get():
                query_parts.append("-filter:retweets")
            
            if self.auto_filter_replies.get():
                query_parts.append("-filter:replies")
            
            # Add min replies
            min_replies = self.auto_min_replies.get().strip()
            if min_replies and min_replies.isdigit():
                query_parts.append(f"min_replies:{min_replies}")
            
            # Add language
            language = self.auto_language_var.get()
            if language:
                query_parts.append(f"lang:{language}")
            
            # Add time range
            time_range = self.auto_time_range_var.get()
            if time_range:
                query_parts.append(f"within_time:{time_range}")
            
            # Combine all parts
            final_query = " ".join(query_parts)
            
            # Update the generated query display
            self.auto_generated_query.config(state='normal')
            self.auto_generated_query.delete(0, tk.END)
            self.auto_generated_query.insert(0, final_query)
            self.auto_generated_query.config(state='readonly')
            
            self.auto_log(f"🔍 Updated search query: {final_query}")
            self.auto_log(f"📊 Query components: Keywords='{keywords}', Language='{language}', Time='{time_range}', Min Replies='{min_replies}'")
            
        except Exception as e:
            self.auto_log(f"❌ Error updating search query: {e}", is_error=True)
            import traceback
            traceback.print_exc()

    def on_time_interval_change(self, event=None):
        """Handle time interval changes"""
        try:
            min_interval = int(self.min_interval_entry.get())
            max_interval = int(self.max_interval_entry.get())
            if min_interval > max_interval:
                self.log("⚠️ Min interval cannot be greater than max interval", is_error=True)
        except ValueError:
            pass  # Allow partial input
    
    def load_urls_from_file(self):
        """Load tweet URLs from a file named linkstocomment.txt"""
        file_path = "linkstocomment.txt"
        try:
            with open(file_path, "r") as f:
                urls = [line.strip() for line in f if line.strip()]
                self.tweet_urls_text.delete('1.0', tk.END)
                self.tweet_urls_text.insert('1.0', "\n".join(urls))
                self.log(f"📁 Loaded {len(urls)} URLs from {file_path}")
            messagebox.showinfo("Success", f"Loaded {len(urls)} URLs from {file_path}")
        except FileNotFoundError:
            messagebox.showerror("Error", f"File not found: {file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Error loading URLs from file: {e}")
            self.log(f"Error loading URLs from file: {e}", is_error=True)
    
    def load_tweet_contents(self):
        """Load tweet contents for all URLs"""
        urls_text = self.tweet_urls_text.get('1.0', tk.END).strip()
        if not urls_text:
            messagebox.showerror("Error", "Please enter tweet URLs first")
            return
        
        urls = [url.strip() for url in urls_text.split('\n') if url.strip()]
        if not urls:
            messagebox.showerror("Error", "No valid URLs found")
            return
        
        self.log(f"🔍 Loading tweet contents for {len(urls)} URLs...")
        
        # Start worker thread
        threading.Thread(target=self._load_tweet_contents_worker, args=(urls,), daemon=True).start()
    
    def _load_tweet_contents_worker(self, urls):
        """Worker thread for loading tweet contents"""
        try:
            self.tweets_data = []
            total_urls = len(urls)
            
            # Get first account for scraping
            selected_accounts = self.get_selected_accounts()
            if not selected_accounts:
                self.log("❌ No accounts selected for scraping", is_error=True)
                return
            
            scraping_account = selected_accounts[0]
            
            for i, url in enumerate(urls):
                self.log(f"📝 Loading tweet {i+1}/{total_urls}: {url}")
                
                # Scrape tweet content
                tweet_content, comments, success = scrape_tweet_content_and_comments_with_account(scraping_account, url)
                
                tweet_data = {
                    'url': url,
                    'content': tweet_content,
                    'comments': comments,
                    'success': success,
                    'reply_text': ''
                }
                
                self.tweets_data.append(tweet_data)
                
                # Update progress
                progress = ((i + 1) / total_urls) * 100
                self.after(0, lambda p=progress: self._update_progress(p))
                
                if success:
                    self.log(f"✅ Successfully loaded tweet {i+1}/{total_urls}")
                else:
                    self.log(f"❌ Failed to load tweet {i+1}/{total_urls}")
            
            # Update UI
            self.after(0, self._update_tweet_display)
            self.log(f"✅ Completed loading {len(self.tweets_data)} tweets")
            
        except Exception as e:
            self.log(f"❌ Error loading tweet contents: {e}", is_error=True)
    
    def _update_progress(self, progress):
        """Update progress bar"""
        if self.progress_bar:
            self.progress_bar['value'] = progress
        if self.progress_label:
            self.progress_label.config(text=f"Loading tweets... {progress:.1f}%")
    
    def _update_tweet_display(self):
        """Update the tweet content display"""
        if not self.tweets_data:
            self.tweet_content_display.config(state='normal')
            self.tweet_content_display.delete('1.0', tk.END)
            self.tweet_content_display.insert('1.0', "No tweets loaded. Click 'Load Tweet Contents' to load tweets.")
            self.tweet_content_display.config(state='disabled')
            self.tweet_counter_label.config(text="Tweet 0 of 0")
            return
        
        # Update counter
        self.tweet_counter_label.config(text=f"Tweet {self.current_tweet_index + 1} of {len(self.tweets_data)}")
        
        # Update navigation buttons
        self.prev_button.config(state='normal' if self.current_tweet_index > 0 else 'disabled')
        self.next_button.config(state='normal' if self.current_tweet_index < len(self.tweets_data) - 1 else 'disabled')
        
        # Display current tweet content
        current_tweet = self.tweets_data[self.current_tweet_index]
        self.tweet_content_display.config(state='normal')
        self.tweet_content_display.delete('1.0', tk.END)
        
        if current_tweet['success']:
            content = f"Tweet Content:\n{current_tweet['content']}\n\n"
            if current_tweet['comments']:
                content += f"Comments ({len(current_tweet['comments'])}):\n"
                for i, comment in enumerate(current_tweet['comments'][:5], 1):  # Show first 5 comments
                    content += f"{i}. {comment}\n"
                if len(current_tweet['comments']) > 5:
                    content += f"... and {len(current_tweet['comments']) - 5} more comments"
        else:
            content = f"Failed to load tweet content for: {current_tweet['url']}"
        
        self.tweet_content_display.insert('1.0', content)
        self.tweet_content_display.config(state='disabled')
        
        # Load reply text for current tweet
        self.individual_reply_text.delete('1.0', tk.END)
        self.individual_reply_text.insert('1.0', current_tweet.get('reply_text', ''))
    
    def prev_tweet(self):
        """Navigate to previous tweet"""
        if self.current_tweet_index > 0:
            self._save_current_reply_text()
            self.current_tweet_index -= 1
            self._update_tweet_display()
    
    def next_tweet(self):
        """Navigate to next tweet"""
        if self.current_tweet_index < len(self.tweets_data) - 1:
            self._save_current_reply_text()
            self.current_tweet_index += 1
            self._update_tweet_display()
    
    def _save_current_reply_text(self):
        """Save the current reply text to the tweet data"""
        if self.tweets_data and 0 <= self.current_tweet_index < len(self.tweets_data):
            reply_text = self.individual_reply_text.get('1.0', tk.END).strip()
            self.tweets_data[self.current_tweet_index]['reply_text'] = reply_text
    
    def generate_ai_comment_for_current_tweet(self):
        """Generate AI comment for the current tweet"""
        if not self.tweets_data or self.current_tweet_index >= len(self.tweets_data):
            messagebox.showerror("Error", "No tweet selected")
            return
        
        current_tweet = self.tweets_data[self.current_tweet_index]
        if not current_tweet['success']:
            messagebox.showerror("Error", "Cannot generate AI comment for failed tweet")
            return
        
        # Get AI prompt
        custom_prompt = self.ai_prompt_entry.get('1.0', tk.END).strip()
        if custom_prompt == "Enter your custom instructions for how to reply to the tweet...":
            custom_prompt = ""
        
        self.log(f"🤖 Generating AI comment for tweet {self.current_tweet_index + 1}...")
        
        # Start worker thread
        threading.Thread(target=self._generate_ai_comment_worker, 
                       args=(current_tweet, custom_prompt), daemon=True).start()
    
    def _generate_ai_comment_worker(self, tweet_data, custom_prompt):
        """Worker thread for generating AI comment"""
        try:
            # Get AI provider
            ai_provider = self.get_current_ai_provider()
            if not ai_provider:
                self.after(0, lambda: self.log("❌ No AI provider configured", is_error=True))
                return
            
            # Generate comment
            comment = self._generate_unique_reply(
                ai_provider, 
                tweet_data['content'], 
                custom_prompt, 
                "Manual", 
                tweet_data['url'],
                50,  # min_chars
                280  # max_chars
            )
            
            if comment:
                # Update the reply text
                self.after(0, lambda: self._update_reply_text(comment))
                self.after(0, lambda: self.log(f"✅ Generated AI comment: {len(comment)} characters"))
            else:
                self.after(0, lambda: self.log("❌ Failed to generate AI comment", is_error=True))
                
        except Exception as e:
            self.after(0, lambda: self.log(f"❌ Error generating AI comment: {e}", is_error=True))
    
    def _update_reply_text(self, comment):
        """Update the reply text with generated comment"""
        self.individual_reply_text.delete('1.0', tk.END)
        self.individual_reply_text.insert('1.0', comment)
        self._save_current_reply_text()
    
    def edit_current_comment(self):
        """Open edit dialog for current comment"""
        if not self.tweets_data or self.current_tweet_index >= len(self.tweets_data):
            messagebox.showerror("Error", "No tweet selected")
            return
        
        current_tweet = self.tweets_data[self.current_tweet_index]
        current_reply = self.individual_reply_text.get('1.0', tk.END).strip()
        
        # Create edit dialog
        edit_dialog = tk.Toplevel(self)
        edit_dialog.title(f"Edit Reply for Tweet {self.current_tweet_index + 1}")
        edit_dialog.geometry("600x400")
        edit_dialog.resizable(True, True)
        
        # Center the dialog
        edit_dialog.transient(self)
        edit_dialog.grab_set()
        
        # Content frame
        content_frame = ttk.Frame(edit_dialog, padding="10")
        content_frame.pack(fill='both', expand=True)
        
        # Tweet content display
        ttk.Label(content_frame, text="Tweet Content:", font=('Segoe UI', 10, 'bold')).pack(anchor='w')
        tweet_display = tk.Text(content_frame, height=6, wrap='word', state='disabled')
        tweet_display.pack(fill='x', pady=(0, 10))
        tweet_display.config(state='normal')
        tweet_display.insert('1.0', current_tweet['content'])
        tweet_display.config(state='disabled')
        
        # Reply text editor
        ttk.Label(content_frame, text="Your Reply:", font=('Segoe UI', 10, 'bold')).pack(anchor='w')
        reply_editor = tk.Text(content_frame, height=8, wrap='word')
        reply_editor.pack(fill='both', expand=True, pady=(0, 10))
        reply_editor.insert('1.0', current_reply)
        
        # Character count
        char_count_label = ttk.Label(content_frame, text=f"Characters: {len(current_reply)}/280")
        char_count_label.pack(anchor='w')
        
        def update_char_count():
            text = reply_editor.get('1.0', tk.END).strip()
            char_count_label.config(text=f"Characters: {len(text)}/280")
        
        reply_editor.bind('<KeyRelease>', lambda e: update_char_count())
        
        # Buttons
        button_frame = ttk.Frame(content_frame)
        button_frame.pack(fill='x', pady=(10, 0))
        
        def save_changes():
            new_reply = reply_editor.get('1.0', tk.END).strip()
            self.individual_reply_text.delete('1.0', tk.END)
            self.individual_reply_text.insert('1.0', new_reply)
            self._save_current_reply_text()
            self.log(f"✅ Updated reply for tweet {self.current_tweet_index + 1}")
            edit_dialog.destroy()
        
        def cancel_edit():
            edit_dialog.destroy()
        
        ttk.Button(button_frame, text="Save Changes", command=save_changes).pack(side='right', padx=(5, 0))
        ttk.Button(button_frame, text="Cancel", command=cancel_edit).pack(side='right')
        
    def send_reply_for_current_tweet(self):
        """Send reply for the current tweet"""
        if not self.tweets_data or self.current_tweet_index >= len(self.tweets_data):
            messagebox.showerror("Error", "No tweet selected")
            return
        
        selected_accounts = self.get_selected_accounts()
        if not selected_accounts:
            messagebox.showerror("Error", "Please select at least one account")
            return
        
        reply_text = self.individual_reply_text.get('1.0', tk.END).strip()
        if not reply_text:
            messagebox.showerror("Error", "Please enter a reply text")
            return
        
        current_tweet = self.tweets_data[self.current_tweet_index]
        
        self.log(f"📤 Sending reply for tweet {self.current_tweet_index + 1}...")
        
        # Start worker thread
        threading.Thread(target=self._send_single_reply_worker, 
                       args=(current_tweet, selected_accounts, reply_text), daemon=True).start()
    
    def _send_single_reply_worker(self, tweet_data, selected_accounts, reply_text):
        """Worker thread for sending a single reply"""
        try:
            success_count = 0
            failed_count = 0
            
            for account in selected_accounts:
                try:
                    # Send reply
                    success, message = reply_to_tweet(account, tweet_data['url'], reply_text)
                    
                    if success:
                        self.after(0, lambda acc=account: self.log(f"✅ Reply sent successfully with {acc.label}"))
                        success_count += 1
                    else:
                        self.after(0, lambda acc=account, msg=message: self.log(f"❌ Failed to send reply with {acc.label}: {msg}", is_error=True))
                        failed_count += 1
                    
                    # Wait between accounts
                    if account != selected_accounts[-1]:
                        wait_time = random.randint(5, 15)
                        self.after(0, lambda wt=wait_time: self.log(f"⏱️ Waiting {wt} seconds before next account..."))
                        time.sleep(wait_time)
                        
                except Exception as e:
                    self.after(0, lambda acc=account, err=str(e): self.log(f"❌ Error sending reply with {acc.label}: {err}", is_error=True))
                    failed_count += 1
            
            # Final summary
            self.after(0, lambda: self.log(f"📊 Reply process completed: {success_count} success, {failed_count} failed"))
            
        except Exception as e:
            self.after(0, lambda: self.log(f"❌ Error in reply worker: {e}", is_error=True))
    
    def start_manual_reply_process(self):
        """Start the manual reply process for all tweets"""
        if not self.tweets_data:
            messagebox.showerror("Error", "No tweets loaded. Please load tweet contents first.")
            return
        
        selected_accounts = self.get_selected_accounts()
        if not selected_accounts:
            messagebox.showerror("Error", "Please select at least one account")
            return
        
        try:
            min_interval = int(self.min_interval_entry.get())
            max_interval = int(self.max_interval_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Please enter valid time intervals")
            return
        
        if min_interval > max_interval:
            messagebox.showerror("Error", "Min interval cannot be greater than max interval")
            return
        
        # Start processing
        self.is_replying = True
        self.is_paused = False
        
        # Update UI
        self.start_reply_button.config(state='disabled')
        self.pause_button.config(state='normal')
        self.stop_button.config(state='normal')
        
        # Start worker thread
        threading.Thread(target=self._manual_reply_worker, 
                       args=(selected_accounts, min_interval, max_interval), daemon=True).start()
    
    def _manual_reply_worker(self, selected_accounts, min_interval, max_interval):
        """Worker thread for manual reply process"""
        try:
            total_tweets = len(self.tweets_data)
            processed = 0
            success_count = 0
            failed_count = 0
            
            self.log(f"🚀 Starting manual reply process with {len(selected_accounts)} accounts")
            self.log(f"📊 Total tweets to process: {total_tweets}")
            
            for i, tweet_data in enumerate(self.tweets_data):
                if not self.is_replying:
                    break
                
                # Wait if paused
                while self.is_paused and self.is_replying:
                    time.sleep(1)
                
                if not self.is_replying:
                    break
                
                # Update progress
                processed += 1
                progress = (processed / total_tweets) * 100
                
                self.after(0, lambda p=progress, proc=processed, succ=success_count, fail=failed_count: 
                          self._update_manual_progress(p, proc, succ, fail))
                
                self.log(f"📝 Processing tweet {processed}/{total_tweets}: {tweet_data['url']}")
                
                # Get reply text for this tweet
                reply_text = tweet_data.get('reply_text', '').strip()
                if not reply_text:
                    self.log(f"⏭️ Skipping tweet {processed} - no reply text")
                    continue
                
                # Process with each account
                for account in selected_accounts:
                    if not self.is_replying:
                        break
                    
                    try:
                        success, message = reply_to_tweet(account, tweet_data['url'], reply_text)
                        
                        if success:
                            self.log(f"✅ Reply sent successfully with {account.label}")
                            success_count += 1
                        else:
                            self.log(f"❌ Failed to send reply with {account.label}: {message}", is_error=True)
                            failed_count += 1
                        
                        # Wait between accounts
                        if account != selected_accounts[-1]:
                            wait_time = random.randint(min_interval, max_interval)
                            self.log(f"⏱️ Waiting {wait_time} seconds before next account...")
                            time.sleep(wait_time)
                            
                    except Exception as e:
                        self.log(f"❌ Error processing with {account.label}: {e}", is_error=True)
                        failed_count += 1
                
                # Wait between tweets
                if i < len(self.tweets_data) - 1:
                    wait_time = random.randint(min_interval, max_interval)
                    self.log(f"⏱️ Waiting {wait_time} seconds before next tweet...")
                    time.sleep(wait_time)
            
            # Final update
            self.after(0, lambda: self._update_manual_progress(100, processed, success_count, failed_count))
            self.log(f"✅ Manual reply process completed! Success: {success_count}, Failed: {failed_count}")
            
        except Exception as e:
            self.log(f"❌ Error in manual reply worker: {e}", is_error=True)
        finally:
            self.after(0, self.stop_manual_reply_process)
    
    def _update_manual_progress(self, progress, processed, success, failed):
        """Update progress bar and stats for manual reply process"""
        if self.progress_bar:
            self.progress_bar['value'] = progress
        
        if self.progress_label:
            self.progress_label.config(text=f"Progress: {processed} tweets processed")
        
        if self.stats_label:
            self.stats_label.config(text=f"Processed: {processed} | Success: {success} | Failed: {failed}")
    
    def pause_manual_reply_process(self):
        """Pause/resume the manual reply process"""
        if self.is_paused:
            self.is_paused = False
            self.pause_button.config(text="⏸️ Pause")
            self.log("▶️ Manual reply process resumed")
        else:
            self.is_paused = True
            self.pause_button.config(text="▶️ Resume")
            self.log("⏸️ Manual reply process paused")
    
    def stop_manual_reply_process(self):
        """Stop the manual reply process"""
        self.is_replying = False
        self.is_paused = False
        
        # Update UI
        self.start_reply_button.config(state='normal')
        self.pause_button.config(state='disabled')
        self.stop_button.config(state='disabled')
        self.pause_button.config(text="⏸️ Pause")
        
        self.log("🛑 Manual reply process stopped")

    def get_selected_accounts(self):
        """Get selected accounts from listbox"""
        if not hasattr(self, 'accounts_listbox') or not self.accounts_listbox:
            return []
        
        selected_indices = self.accounts_listbox.curselection()
        return [self.accounts[i] for i in selected_indices]