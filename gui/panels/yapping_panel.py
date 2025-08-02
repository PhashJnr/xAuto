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
        from selenium_manager import create_simple_isolated_chrome
        
        # Create a new driver for scraping
        driver = create_simple_isolated_chrome(account)
        if not driver:
            print(f"❌ Failed to create driver for {account.label}")
            return "", [], False
        
        try:
            # Navigate to tweet
            driver.get(tweet_url)
            time.sleep(3)
            
            # Check if logged in
            current_url = driver.current_url
            if 'login' in current_url or 'i/flow/login' in current_url:
                print(f"❌ Account {account.label} is not logged in (redirected to login)")
                driver.quit()
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
        finally:
            # Always close the driver
            try:
                driver.quit()
            except:
                pass
                
    except Exception as e:
        print(f"❌ Error scraping tweet with account {account.label}: {e}")
        return "", [], False

class YappingPanel(ttk.Frame):
    def __init__(self, parent, accounts):
        super().__init__(parent)
        self.parent = parent
        self.accounts = accounts
        self.panel = None
        self.accounts_listbox = None
        self.tweet_url_entry = None
        self.ai_prompt_entry = None
        self.log_text = None
        self.selected_tag = None
        self.tag_filter_dropdown = None
        self.ai_enabled_var = None
        self.context_analysis_var = None
        self.auto_reply_var = None
        # Initialize AI integration
        self.ai_integration = create_ai_integration()
        # Store scraped data
        self.scraped_tweet_content = None
        self.scraped_comments = []
        # State persistence
        self.state = {
            'selected_tag': 'All',
            'tweet_url': '',
            'ai_prompt': '',
            'ai_enabled': True,
            'context_analysis': True,
            'auto_reply': False,
            'log_messages': []
        }
    
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
        """Save tweet URL to state"""
        self.state['tweet_url'] = self.tweet_url_entry.get()

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
        
        # Also refresh auto accounts list if it exists
        if hasattr(self, 'auto_accounts_listbox'):
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
        # Tweet URL Input
        url_frame = ttk.LabelFrame(self.manual_frame, text="Tweet URL", padding="10")
        url_frame.grid(row=0, column=0, columnspan=3, sticky='ew', padx=20, pady=10)
        
        self.tweet_url_entry = tk.Entry(url_frame, width=80)
        self.tweet_url_entry.grid(row=0, column=0, sticky='ew', padx=5, pady=2)
        self.tweet_url_entry.bind('<KeyRelease>', self.on_tweet_url_change)
        
        ttk.Button(url_frame, text="🔍 Analyze Tweet & Comments", command=self.analyze_tweet_context).grid(row=0, column=1, padx=5, pady=2)
        
        # Account Selection
        accounts_frame = ttk.LabelFrame(self.manual_frame, text="Select Accounts", padding="10")
        accounts_frame.grid(row=1, column=0, columnspan=3, sticky='ew', padx=20, pady=10)
        
        # Tag filter
        filter_frame = ttk.Frame(accounts_frame)
        filter_frame.grid(row=0, column=0, columnspan=2, sticky='ew', pady=5)
        
        tk.Label(filter_frame, text="Filter by Tag:", bg=COLOR_TAUPE, fg=COLOR_DARK).grid(row=0, column=0, sticky='w', padx=5)
        self.selected_tag = tk.StringVar(value='All')
        self.tag_filter_dropdown = ttk.Combobox(filter_frame, textvariable=self.selected_tag, state='readonly', width=20)
        self.tag_filter_dropdown.grid(row=0, column=1, sticky='w', padx=5)
        self.tag_filter_dropdown.bind('<<ComboboxSelected>>', self.on_tag_filter_change)
        
        # Accounts listbox
        listbox_frame = ttk.Frame(accounts_frame)
        listbox_frame.grid(row=1, column=0, columnspan=2, sticky='ew', pady=5)
        
        self.accounts_listbox = tk.Listbox(listbox_frame, height=8, selectmode='multiple')
        self.accounts_listbox.grid(row=0, column=0, sticky='ew', padx=5)
        
        scrollbar_accounts = ttk.Scrollbar(listbox_frame, orient="vertical", command=self.accounts_listbox.yview)
        scrollbar_accounts.grid(row=0, column=1, sticky='ns')
        self.accounts_listbox.configure(yscrollcommand=scrollbar_accounts.set)
        
        # AI Configuration
        ai_frame = ttk.LabelFrame(self.manual_frame, text="AI Configuration", padding="10")
        ai_frame.grid(row=2, column=0, columnspan=3, sticky='ew', padx=20, pady=10)
        
        # AI Enable checkbox
        self.ai_enabled_var = tk.BooleanVar(value=self.state['ai_enabled'])
        ai_check = ttk.Checkbutton(ai_frame, text="Enable AI Comments", variable=self.ai_enabled_var, command=self.on_ai_enabled_change)
        ai_check.grid(row=0, column=0, sticky='w', padx=5, pady=2)
        
        # Context analysis checkbox
        self.context_analysis_var = tk.BooleanVar(value=self.state['context_analysis'])
        context_check = ttk.Checkbutton(ai_frame, text="Analyze Tweet Context", variable=self.context_analysis_var, command=self.on_context_analysis_change)
        context_check.grid(row=1, column=0, sticky='w', padx=5, pady=2)
        
        # Auto reply checkbox
        self.auto_reply_var = tk.BooleanVar(value=self.state['auto_reply'])
        auto_check = ttk.Checkbutton(ai_frame, text="Auto Reply Mode", variable=self.auto_reply_var, command=self.on_auto_reply_change)
        auto_check.grid(row=2, column=0, sticky='w', padx=5, pady=2)
        
        # AI Prompt
        prompt_frame = ttk.Frame(ai_frame)
        prompt_frame.grid(row=3, column=0, sticky='ew', padx=5, pady=5)
        
        tk.Label(prompt_frame, text="🎯 Custom Reply Instructions:", bg=COLOR_TAUPE, fg=COLOR_DARK, font=('Segoe UI', 10, 'bold')).grid(row=0, column=0, sticky='w', padx=5, pady=(5,2))
        
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
        examples_label.grid(row=1, column=0, sticky='w', padx=5, pady=(0,5))
        
        self.ai_prompt_entry = tk.Text(prompt_frame, height=4, width=60, wrap='word')
        self.ai_prompt_entry.grid(row=2, column=0, sticky='ew', padx=5, pady=2)
        self.ai_prompt_entry.bind('<KeyRelease>', self.on_ai_prompt_change)
        
        # Add placeholder text
        placeholder_text = "Enter your custom instructions for how to reply to the tweet..."
        self.ai_prompt_entry.insert('1.0', placeholder_text)
        self.ai_prompt_entry.bind('<FocusIn>', self._on_prompt_focus_in)
        self.ai_prompt_entry.bind('<FocusOut>', self._on_prompt_focus_out)
        
        # AI Comment Generation
        ai_frame = ttk.LabelFrame(self.manual_frame, text="🤖 AI Comment Generation", padding="10")
        ai_frame.grid(row=3, column=0, columnspan=3, sticky='ew', padx=20, pady=10)
        
        # Generate AI Comments Button
        self.generate_ai_button = ttk.Button(
            ai_frame, 
            text="Generate AI Comment", 
            command=self.generate_ai_comments,
            style="Accent.TButton"
        )
        self.generate_ai_button.pack(pady=5)
        
        # AI Comments Display
        self.ai_comments_text = tk.Text(ai_frame, height=6, width=80, wrap='word')
        self.ai_comments_text.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Action Buttons
        buttons_frame = ttk.Frame(self.manual_frame)
        buttons_frame.grid(row=4, column=0, columnspan=3, sticky='ew', padx=20, pady=10)
        
        ttk.Button(buttons_frame, text="🚀 Start Auto-Yapping", command=self.start_auto_yapping).pack(side='left', padx=5)
        
        # Log Area
        log_frame = ttk.LabelFrame(self.manual_frame, text="Activity Log", padding="10")
        log_frame.grid(row=5, column=0, columnspan=3, sticky='ew', padx=20, pady=10)
        
        # Create text widget with scrollbar for logs
        log_text_frame = ttk.Frame(log_frame)
        log_text_frame.grid(row=0, column=0, sticky='ew', padx=5, pady=5)
        
        self.log_text = tk.Text(log_text_frame, height=12, width=80, wrap='word')
        self.log_text.grid(row=0, column=0, sticky='ew')
        
        log_scrollbar = ttk.Scrollbar(log_text_frame, orient="vertical", command=self.log_text.yview)
        log_scrollbar.grid(row=0, column=1, sticky='ns')
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        # Restore state
        self.restore_log_messages()
        self.refresh_accounts_list()

    def _build_auto_tab(self):
        """Build the auto yapping tab"""
        # Search Query Input
        query_frame = ttk.LabelFrame(self.auto_frame, text="🔍 Search Query", padding="10")
        query_frame.grid(row=0, column=0, columnspan=3, sticky='ew', padx=20, pady=10)
        
        tk.Label(query_frame, text="Twitter Search Query:", bg=COLOR_TAUPE, fg=COLOR_DARK).grid(row=0, column=0, sticky='w', padx=5, pady=2)
        
        self.search_query_entry = tk.Text(query_frame, height=3, width=80, wrap='word')
        self.search_query_entry.grid(row=1, column=0, sticky='ew', padx=5, pady=2)
        
        # Add example query
        example_query = 'filter:blue_verified ("cysic" OR @cysic_xyz) -filter:nativeretweets -filter:retweets -filter:replies min_replies:20 lang:en within_time:1440min'
        self.search_query_entry.insert('1.0', example_query)
        
        # Settings Frame
        settings_frame = ttk.LabelFrame(self.auto_frame, text="⚙️ Auto Yapping Settings", padding="10")
        settings_frame.grid(row=1, column=0, columnspan=3, sticky='ew', padx=20, pady=10)
        
        # Time intervals
        interval_frame = ttk.Frame(settings_frame)
        interval_frame.grid(row=0, column=0, sticky='w', padx=5, pady=5)
        
        tk.Label(interval_frame, text="Time Interval (seconds):", bg=COLOR_TAUPE, fg=COLOR_DARK).grid(row=0, column=0, sticky='w', padx=5)
        self.min_interval_var = tk.StringVar(value="60")
        self.max_interval_var = tk.StringVar(value="180")
        
        ttk.Entry(interval_frame, textvariable=self.min_interval_var, width=10).grid(row=0, column=1, padx=5)
        tk.Label(interval_frame, text="to", bg=COLOR_TAUPE, fg=COLOR_DARK).grid(row=0, column=2, padx=5)
        ttk.Entry(interval_frame, textvariable=self.max_interval_var, width=10).grid(row=0, column=3, padx=5)
        
        # Max tweets to process
        max_frame = ttk.Frame(settings_frame)
        max_frame.grid(row=1, column=0, sticky='w', padx=5, pady=5)
        
        tk.Label(max_frame, text="Max Tweets to Process:", bg=COLOR_TAUPE, fg=COLOR_DARK).grid(row=0, column=0, sticky='w', padx=5)
        self.max_tweets_var = tk.StringVar(value="50")
        ttk.Entry(max_frame, textvariable=self.max_tweets_var, width=10).grid(row=0, column=1, padx=5)
        
        # Character limit settings
        char_frame = ttk.Frame(settings_frame)
        char_frame.grid(row=2, column=0, sticky='w', padx=5, pady=5)
        
        tk.Label(char_frame, text="Reply Length (chars):", bg=COLOR_TAUPE, fg=COLOR_DARK).grid(row=0, column=0, sticky='w', padx=5)
        self.min_chars_var = tk.StringVar(value="180")
        self.max_chars_var = tk.StringVar(value="280")
        
        ttk.Entry(char_frame, textvariable=self.min_chars_var, width=8).grid(row=0, column=1, padx=2)
        tk.Label(char_frame, text="to", bg=COLOR_TAUPE, fg=COLOR_DARK).grid(row=0, column=2, padx=2)
        ttk.Entry(char_frame, textvariable=self.max_chars_var, width=8).grid(row=0, column=3, padx=2)
        
        # Account Selection for Auto
        auto_accounts_frame = ttk.LabelFrame(self.auto_frame, text="Select Accounts for Auto Yapping", padding="10")
        auto_accounts_frame.grid(row=2, column=0, columnspan=3, sticky='ew', padx=20, pady=10)
        
        # Auto accounts listbox
        auto_listbox_frame = ttk.Frame(auto_accounts_frame)
        auto_listbox_frame.grid(row=0, column=0, sticky='ew', pady=5)
        
        self.auto_accounts_listbox = tk.Listbox(auto_listbox_frame, height=6, selectmode='multiple')
        self.auto_accounts_listbox.grid(row=0, column=0, sticky='ew', padx=5)
        
        auto_scrollbar = ttk.Scrollbar(auto_listbox_frame, orient="vertical", command=self.auto_accounts_listbox.yview)
        auto_scrollbar.grid(row=0, column=1, sticky='ns')
        self.auto_accounts_listbox.configure(yscrollcommand=auto_scrollbar.set)
        
        # Auto AI Prompt
        auto_prompt_frame = ttk.LabelFrame(self.auto_frame, text="🎯 Auto Reply Instructions", padding="10")
        auto_prompt_frame.grid(row=3, column=0, columnspan=3, sticky='ew', padx=20, pady=10)
        
        tk.Label(auto_prompt_frame, text="Custom Instructions for Auto Replies:", bg=COLOR_TAUPE, fg=COLOR_DARK, font=('Segoe UI', 10, 'bold')).grid(row=0, column=0, sticky='w', padx=5, pady=(5,2))
        
        self.auto_ai_prompt_entry = tk.Text(auto_prompt_frame, height=3, width=80, wrap='word')
        self.auto_ai_prompt_entry.grid(row=1, column=0, sticky='ew', padx=5, pady=2)
        
        # Add placeholder text
        auto_placeholder = "Enter custom instructions for auto replies (optional)..."
        self.auto_ai_prompt_entry.insert('1.0', auto_placeholder)
        self.auto_ai_prompt_entry.bind('<FocusIn>', self._on_auto_prompt_focus_in)
        self.auto_ai_prompt_entry.bind('<FocusOut>', self._on_auto_prompt_focus_out)
        
        # Control Buttons
        control_frame = ttk.Frame(self.auto_frame)
        control_frame.grid(row=4, column=0, columnspan=3, sticky='ew', padx=20, pady=10)
        
        self.start_auto_button = ttk.Button(control_frame, text="🚀 Start Auto Yapping", command=self.start_auto_yapping_search)
        self.start_auto_button.pack(side='left', padx=5)
        
        self.stop_auto_button = ttk.Button(control_frame, text="⏹️ Stop Auto Yapping", command=self.stop_auto_yapping_search, state='disabled')
        self.stop_auto_button.pack(side='left', padx=5)
        
        self.pause_auto_button = ttk.Button(control_frame, text="⏸️ Pause", command=self.pause_auto_yapping_search, state='disabled')
        self.pause_auto_button.pack(side='left', padx=5)
        
        # Progress Frame
        progress_frame = ttk.LabelFrame(self.auto_frame, text="📊 Progress", padding="10")
        progress_frame.grid(row=5, column=0, columnspan=3, sticky='ew', padx=20, pady=10)
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=0, column=0, sticky='ew', padx=5, pady=5)
        
        # Progress labels
        self.progress_label = tk.Label(progress_frame, text="Ready to start", bg=COLOR_TAUPE, fg=COLOR_DARK)
        self.progress_label.grid(row=1, column=0, sticky='w', padx=5)
        
        self.stats_label = tk.Label(progress_frame, text="Processed: 0 | Successful: 0 | Failed: 0", bg=COLOR_TAUPE, fg=COLOR_DARK)
        self.stats_label.grid(row=2, column=0, sticky='w', padx=5)
        
        # Auto Log Area
        auto_log_frame = ttk.LabelFrame(self.auto_frame, text="Auto Yapping Log", padding="10")
        auto_log_frame.grid(row=6, column=0, columnspan=3, sticky='ew', padx=20, pady=10)
        
        auto_log_text_frame = ttk.Frame(auto_log_frame)
        auto_log_text_frame.grid(row=0, column=0, sticky='ew', padx=5, pady=5)
        
        self.auto_log_text = tk.Text(auto_log_text_frame, height=10, width=80, wrap='word')
        self.auto_log_text.grid(row=0, column=0, sticky='ew')
        
        auto_log_scrollbar = ttk.Scrollbar(auto_log_text_frame, orient="vertical", command=self.auto_log_text.yview)
        auto_log_scrollbar.grid(row=0, column=1, sticky='ns')
        self.auto_log_text.configure(yscrollcommand=auto_log_scrollbar.set)
        
        # Initialize auto yapping state
        self.auto_yapping_running = False
        self.auto_yapping_paused = False
        self.auto_yapping_stats = {'processed': 0, 'successful': 0, 'failed': 0}
        self.replied_tweets_db = {}  # Simple in-memory database
        
        # Populate auto accounts list
        self.refresh_auto_accounts_list()

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

    def start_auto_yapping_search(self):
        """Start auto yapping based on search query"""
        search_query = self.search_query_entry.get('1.0', 'end-1c').strip()
        if not search_query:
            self.auto_log("Please enter a search query.", is_error=True)
            return
        
        # Get selected accounts
        selected_indices = self.auto_accounts_listbox.curselection()
        if not selected_indices:
            self.auto_log("Please select at least one account.", is_error=True)
            return
        
        # Get filtered accounts
        filtered_accounts = [a for a in self.accounts]
        selected_accounts = [filtered_accounts[i] for i in selected_indices if i < len(filtered_accounts)]
        
        if not selected_accounts:
            self.auto_log("No accounts selected.", is_error=True)
            return
        
        # Get settings
        try:
            min_interval = int(self.min_interval_var.get())
            max_interval = int(self.max_interval_var.get())
            max_tweets = int(self.max_tweets_var.get())
            min_chars = int(self.min_chars_var.get())
            max_chars = int(self.max_chars_var.get())
        except ValueError:
            self.auto_log("Please enter valid numbers for intervals, max tweets, and character limits.", is_error=True)
            return
        
        # Get custom prompt
        custom_prompt = self.auto_ai_prompt_entry.get('1.0', 'end-1c').strip()
        if custom_prompt == "Enter custom instructions for auto replies (optional)...":
            custom_prompt = ""
        
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
        """Log a message to the auto yapping log area"""
        if is_error:
            message = f"❌ {message}"
        
        self.auto_log_text.config(state='normal')
        self.auto_log_text.insert('end', f"[{time.strftime('%H:%M:%S')}] {message}\n")
        self.auto_log_text.see('end')
        self.auto_log_text.config(state='disabled')

    def update_progress(self, current, total, stats):
        """Update progress bar and stats"""
        if total > 0:
            progress = (current / total) * 100
            self.progress_var.set(progress)
        
        self.progress_label.config(text=f"Processing tweet {current}/{total}")
        self.stats_label.config(text=f"Processed: {stats['processed']} | Successful: {stats['successful']} | Failed: {stats['failed']}")

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
            tweets = self._get_tweets_from_search(search_url, max_tweets)
            
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
                
                # Wait before next tweet
                if i < len(tweets) - 1 and self.auto_yapping_running:
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

    def _get_tweets_from_search(self, search_url, max_tweets):
        """Get tweet URLs from search results"""
        try:
            # Use the first account to scrape search results
            scraping_account = self.accounts[0] if self.accounts else None
            if not scraping_account:
                self.auto_log("❌ No accounts available for scraping.", is_error=True)
                return []
            
            from selenium_manager import create_simple_isolated_chrome
            driver = create_simple_isolated_chrome(scraping_account)
            if not driver:
                self.auto_log("❌ Failed to create driver for scraping.", is_error=True)
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
            # Scrape tweet content
            scraping_account = accounts[0]
            tweet_content, _, success = scrape_tweet_content_and_comments_with_account(scraping_account, tweet_url)
            
            if not success or not tweet_content.strip():
                self.auto_log(f"❌ Failed to scrape tweet content: {tweet_url}")
                return False
            
            # Generate AI reply for each account separately
            ai_provider = self.get_current_ai_provider()
            if not ai_provider:
                self.auto_log("❌ No AI provider available.")
                return False
            
            # Clean the tweet content for AI
            cleaned_content = tweet_content[:500]  # Limit content length
            
            # Reply with each account
            for account in accounts:
                if not self.auto_yapping_running:
                    break
                
                self.auto_log(f"🤖 Replying with account: {account.label}")
                
                # Generate unique reply for this specific account
                unique_reply = self._generate_unique_reply(ai_provider, cleaned_content, custom_prompt, account.label, tweet_url, min_chars, max_chars)
                
                if not unique_reply:
                    self.auto_log(f"❌ Failed to generate unique reply for {account.label}")
                    continue
                
                self.auto_log(f"💭 Generated unique reply for {account.label}: {unique_reply[:50]}...")
                
                try:
                    from selenium_manager import reply_to_tweet
                    success, message = reply_to_tweet(account, tweet_url, unique_reply)
                    
                    if success:
                        self.auto_log(f"✅ Successfully replied with {account.label}")
                    else:
                        self.auto_log(f"❌ Failed to reply with {account.label}: {message}")
                        
                except Exception as e:
                    self.auto_log(f"❌ Error replying with {account.label}: {e}")
                
                # Wait between accounts
                if account != accounts[-1]:
                    time.sleep(random.randint(10, 30))
            
            return True
            
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

    def refresh_auto_accounts_list(self):
        """Populate the auto accounts listbox with available accounts"""
        self.auto_accounts_listbox.delete(0, tk.END)
        for account in self.accounts:
            tags_text = f" [{', '.join(account.tags)}]" if account.tags else ""
            self.auto_accounts_listbox.insert('end', f"{account.label} ({account.username}){tags_text}") 