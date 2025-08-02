import tkinter as tk
from tkinter import ttk, messagebox
from constants import COLOR_TAUPE, COLOR_DARK, COLOR_WHITE
import os
import json
from ai_integration import create_ai_integration
from datetime import datetime
from utils import log_to_file
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class AISettingsPanel(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.ai_manager = create_ai_integration()
        self.provider_var = None
        self.api_key_entry = None
        self.usage_label = None
        self.provider_status_label = None
        self.pricing_tree = None
        self.recommendations_text = None
        
        # Load saved state
        self.saved_state = self.load_state()
        
        # Initialize state
        self.state = {
            'selected_provider': self.saved_state.get('selected_provider', 'openai'),
            'api_keys': self.saved_state.get('api_keys', {}),
            'log_messages': []
        }
        
        # AI Provider Info
        self.provider_info = {
            'openai': {
                'name': 'OpenAI GPT-4',
                'pricing': '$0.03/1K input, $0.06/1K output',
                'quality': 'Excellent',
                'speed': 'Fast (1-3s)',
                'best_for': 'High-quality, context-aware comments',
                'setup_url': 'https://platform.openai.com/api-keys',
                'cost_per_comment': '~$0.01-0.02',
                'models': ['gpt-4', 'gpt-3.5-turbo', 'gpt-4-turbo']
            }
        }

    def load_state(self):
        """Load saved state from file"""
        try:
            with open('ai_settings_state.json', 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {
                'selected_provider': 'local',
                'api_keys': {},
                'daily_budget': 10.0,
                'monthly_budget': 100.0
            }
    
    def save_state(self):
        """Save current state to file"""
        try:
            state = {
                'selected_provider': self.provider_var.get() if hasattr(self, 'provider_var') else 'local',
                'api_keys': self.saved_state.get('api_keys', {}),
                'daily_budget': float(self.daily_budget_var.get()) if hasattr(self, 'daily_budget_var') else 10.0,
                'monthly_budget': float(self.monthly_budget_var.get()) if hasattr(self, 'monthly_budget_var') else 100.0
            }
            with open('ai_settings_state.json', 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            log_to_file('ai_settings', f"Error saving state: {e}")

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
        title = tk.Label(scrollable_frame, text="🤖 AI Settings & Configuration", font=('Segoe UI', 16, 'bold'), bg=COLOR_TAUPE, fg=COLOR_DARK)
        title.grid(row=0, column=0, columnspan=3, sticky='w', padx=20, pady=(20, 10))
        
        # Current Provider Info
        current_info = self.ai_manager.get_current_provider_info()
        current_frame = ttk.LabelFrame(scrollable_frame, text="Current AI Provider", padding="10")
        current_frame.grid(row=1, column=0, columnspan=3, sticky='ew', padx=20, pady=10)
        
        self.current_provider_label = tk.Label(current_frame, text=f"Provider: {current_info['name']}", bg=COLOR_TAUPE, fg=COLOR_DARK)
        self.current_provider_label.grid(row=0, column=0, sticky='w')
        
        status = "✅ Configured" if current_info['configured'] else "❌ Not Configured"
        self.current_status_label = tk.Label(current_frame, text=f"Status: {status}", bg=COLOR_TAUPE, fg=COLOR_DARK)
        self.current_status_label.grid(row=1, column=0, sticky='w')
        
        # Provider Selection
        provider_frame = ttk.LabelFrame(scrollable_frame, text="Select AI Provider", padding="10")
        provider_frame.grid(row=2, column=0, columnspan=3, sticky='ew', padx=20, pady=10)
        
        available_providers = self.ai_manager.get_available_providers()
        saved_provider = self.saved_state.get('selected_provider', 'openai')
        
        # Use saved provider if available, otherwise use OpenAI
        if saved_provider in available_providers:
            self.provider_var = tk.StringVar(value=saved_provider)
        else:
            self.provider_var = tk.StringVar(value='openai')
        
        # Create provider radio button (only OpenAI)
        provider_info = self.provider_info['openai']
        provider_status = self.get_provider_status('openai')
        provider_text = f"{provider_info['name']} ({provider_status})"
        
        provider_btn = ttk.Radiobutton(
            provider_frame, 
            text=provider_text,
            variable=self.provider_var,
            value='openai',
            command=self.on_provider_change
        )
        provider_btn.grid(row=0, column=0, sticky='w', padx=5, pady=2)
        self.provider_buttons = {'openai': provider_btn}
        
        # Provider Details
        details_frame = ttk.LabelFrame(scrollable_frame, text="Provider Details", padding="10")
        details_frame.grid(row=3, column=0, columnspan=3, sticky='ew', padx=20, pady=10)
        
        self.details_labels = {}
        details = ['name', 'pricing', 'quality', 'speed', 'best_for', 'cost_per_comment']
        for i, detail in enumerate(details):
            label = tk.Label(details_frame, text=f"{detail.title()}: ", bg=COLOR_TAUPE, fg=COLOR_DARK, font=('Segoe UI', 9, 'bold'))
            label.grid(row=i, column=0, sticky='w', padx=5, pady=2)
            
            value_label = tk.Label(details_frame, text="", bg=COLOR_TAUPE, fg=COLOR_DARK)
            value_label.grid(row=i, column=1, sticky='w', padx=5, pady=2)
            self.details_labels[detail] = value_label
        
        # Model Selection
        model_frame = ttk.LabelFrame(scrollable_frame, text="Model Selection", padding="10")
        model_frame.grid(row=4, column=0, columnspan=3, sticky='ew', padx=20, pady=10)
        
        tk.Label(model_frame, text="Model:", bg=COLOR_TAUPE, fg=COLOR_DARK).grid(row=0, column=0, sticky='w', padx=5, pady=2)
        self.model_var = tk.StringVar()
        self.model_dropdown = ttk.Combobox(model_frame, textvariable=self.model_var, state="readonly", width=30)
        self.model_dropdown.grid(row=0, column=1, sticky='w', padx=5, pady=2)
        
        # API Key Configuration
        api_frame = ttk.LabelFrame(scrollable_frame, text="API Key Configuration", padding="10")
        api_frame.grid(row=5, column=0, columnspan=3, sticky='ew', padx=20, pady=10)
        
        tk.Label(api_frame, text="API Key:", bg=COLOR_TAUPE, fg=COLOR_DARK).grid(row=0, column=0, sticky='w', padx=5, pady=2)
        self.api_key_entry = tk.Entry(api_frame, show="*", width=50)
        self.api_key_entry.grid(row=0, column=1, sticky='w', padx=5, pady=2)
        
        button_frame = ttk.Frame(api_frame)
        button_frame.grid(row=1, column=0, columnspan=2, sticky='w', padx=5, pady=5)
        
        ttk.Button(button_frame, text="Save API Key", command=self.save_api_key).pack(side='left', padx=2)
        ttk.Button(button_frame, text="Test Connection", command=self.test_connection).pack(side='left', padx=2)
        ttk.Button(button_frame, text="Get API Key", command=self.open_setup_url).pack(side='left', padx=2)
        
        # Cost Monitoring
        cost_frame = ttk.LabelFrame(scrollable_frame, text="Cost Monitoring", padding="10")
        cost_frame.grid(row=6, column=0, columnspan=3, sticky='ew', padx=20, pady=10)
        
        tk.Label(cost_frame, text="Daily Budget ($):", bg=COLOR_TAUPE, fg=COLOR_DARK).grid(row=0, column=0, sticky='w', padx=5, pady=2)
        self.daily_budget_var = tk.StringVar(value="10.0")
        tk.Entry(cost_frame, textvariable=self.daily_budget_var, width=15).grid(row=0, column=1, sticky='w', padx=5, pady=2)
        
        tk.Label(cost_frame, text="Monthly Budget ($):", bg=COLOR_TAUPE, fg=COLOR_DARK).grid(row=1, column=0, sticky='w', padx=5, pady=2)
        self.monthly_budget_var = tk.StringVar(value="100.0")
        tk.Entry(cost_frame, textvariable=self.monthly_budget_var, width=15).grid(row=1, column=1, sticky='w', padx=5, pady=2)
        
        self.daily_usage_label = tk.Label(cost_frame, text="Today: $0.00 / $10.00", bg=COLOR_TAUPE, fg=COLOR_DARK)
        self.daily_usage_label.grid(row=2, column=0, columnspan=2, sticky='w', padx=5, pady=2)
        
        self.monthly_usage_label = tk.Label(cost_frame, text="This Month: $0.00 / $100.00", bg=COLOR_TAUPE, fg=COLOR_DARK)
        self.monthly_usage_label.grid(row=3, column=0, columnspan=2, sticky='w', padx=5, pady=2)
        
        # Pricing Comparison
        pricing_frame = ttk.LabelFrame(scrollable_frame, text="Pricing Information", padding="10")
        pricing_frame.grid(row=7, column=0, columnspan=3, sticky='ew', padx=20, pady=10)
        
        # Create treeview for pricing information
        columns = ('Provider', 'Quality', 'Speed', 'Cost/Comment', 'Best For')
        self.pricing_tree = ttk.Treeview(pricing_frame, columns=columns, show='headings', height=1)
        
        for col in columns:
            self.pricing_tree.heading(col, text=col)
            self.pricing_tree.column(col, width=120)
        
        # Add pricing data for OpenAI only
        info = self.provider_info['openai']
        self.pricing_tree.insert('', 'end', values=(
            info['name'],
            info['quality'],
            info['speed'],
            info['cost_per_comment'],
            info['best_for']
        ))
        
        self.pricing_tree.grid(row=0, column=0, sticky='ew', padx=5, pady=5)
        
        # Recommendations
        rec_frame = ttk.LabelFrame(scrollable_frame, text="OpenAI Integration Guide", padding="10")
        rec_frame.grid(row=8, column=0, columnspan=3, sticky='ew', padx=20, pady=10)
        
        recommendations = [
            "💡 OpenAI GPT-4 provides the highest quality AI responses",
            "💰 Each comment costs approximately $0.01-0.02",
            "⚡ Fast response times (1-3 seconds per comment)",
            "🎯 Perfect for engaging, context-aware social media comments"
        ]
        
        for i, rec in enumerate(recommendations):
            tk.Label(rec_frame, text=rec, bg=COLOR_TAUPE, fg=COLOR_DARK).grid(row=i, column=0, sticky='w', padx=5, pady=2)
        
        # Update initial display
        self.update_provider_details()
        self.update_usage_display()
        
        # Set the provider in AI manager based on current selection
        current_provider = self.provider_var.get()
        if current_provider == 'openai':
            self.ai_manager.set_provider(current_provider)
        
        # Pack the canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Bind mouse wheel to canvas
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        return self

    def update_usage_display(self):
        """Update the usage display"""
        try:
            current_provider = self.provider_var.get()
            if current_provider == 'openai':
                cost_tracker = self.ai_manager.provider.cost_tracker
                
                # Get daily and monthly costs
                daily_cost = sum(cost_tracker.daily_costs.values())
                monthly_cost = sum(cost_tracker.monthly_costs.values())
                
                # Get budgets
                daily_budget = float(self.daily_budget_var.get())
                monthly_budget = float(self.monthly_budget_var.get())
                
                # Update labels
                self.daily_usage_label.config(text=f"Today: ${daily_cost:.2f} / ${daily_budget:.2f}")
                self.monthly_usage_label.config(text=f"This Month: ${monthly_cost:.2f} / ${monthly_budget:.2f}")
                
                # Color coding for budget warnings
                if daily_cost > daily_budget * 0.8:  # 80% of budget
                    self.daily_usage_label.config(fg="orange")
                elif daily_cost > daily_budget:
                    self.daily_usage_label.config(fg="red")
                else:
                    self.daily_usage_label.config(fg=COLOR_DARK)
                    
                if monthly_cost > monthly_budget * 0.8:  # 80% of budget
                    self.monthly_usage_label.config(fg="orange")
                elif monthly_cost > monthly_budget:
                    self.monthly_usage_label.config(fg="red")
                else:
                    self.monthly_usage_label.config(fg=COLOR_DARK)
                    
        except Exception as e:
            log_to_file('ai_settings', f"Error updating usage display: {e}")

    def update_model_options(self):
        """Update model dropdown options based on selected provider"""
        current_provider = self.provider_var.get()
        if current_provider in self.provider_info:
            models = self.provider_info[current_provider]['models']
            self.model_dropdown['values'] = models
            if models and self.model_var.get() not in models:
                self.model_var.set(models[0])

    def get_provider_status(self, provider: str) -> str:
        """Get the status of a provider"""
        if provider == 'openai':
            if self.ai_manager.provider.is_configured:
                return "✅ Configured"
            else:
                return "❌ Not Configured"
        return "❌ Not Available"

    def update_provider_status_display(self):
        """Update the provider status display"""
        # Update current provider info
        current_info = self.ai_manager.get_current_provider_info()
        self.current_provider_label.config(text=f"Provider: {current_info['name']}")
        
        status = "✅ Configured" if current_info['configured'] else "❌ Not Configured"
        self.current_status_label.config(text=f"Status: {status}")
        
        # Update provider radio button
        provider_status = self.get_provider_status('openai')
        provider_info = self.provider_info['openai']
        provider_text = f"{provider_info['name']} ({provider_status})"
        self.provider_buttons['openai'].config(text=provider_text)

    def on_provider_change(self):
        """Handle provider selection change"""
        current_provider = self.provider_var.get()
        
        # Set the provider in AI manager
        self.ai_manager.set_provider(current_provider)
        
        # Update provider details
        self.update_provider_details()
        
        # Update model options
        self.update_model_options()
        
        # Load API key for selected provider
        api_key = self.get_api_key(current_provider)
        if api_key:
            self.api_key_entry.delete(0, tk.END)
            self.api_key_entry.insert(0, api_key)
        else:
            self.api_key_entry.delete(0, tk.END)
        
        # Update provider status display
        self.update_provider_status_display()
        
        # Save state
        self.save_state()

    def update_provider_details(self):
        """Update the provider details display"""
        current_provider = self.provider_var.get()
        info = self.provider_info[current_provider]
        
        self.details_labels['name'].config(text=f"Name: {info['name']}")
        self.details_labels['pricing'].config(text=f"Pricing: {info['pricing']}")
        self.details_labels['quality'].config(text=f"Quality: {info['quality']}")
        self.details_labels['speed'].config(text=f"Speed: {info['speed']}")
        self.details_labels['best_for'].config(text=f"Best For: {info['best_for']}")
        self.details_labels['cost_per_comment'].config(text=f"Cost/Comment: {info['cost_per_comment']}")

    def save_api_key(self):
        """Save API key for current provider"""
        current_provider = self.provider_var.get()
        api_key = self.api_key_entry.get().strip()
        
        if not api_key:
            messagebox.showwarning("Warning", "Please enter an API key.")
            return
        
        # Save to environment variable
        env_var_name = f"{current_provider.upper()}_API_KEY"
        os.environ[env_var_name] = api_key
        
        # Save to .env file
        self._save_to_env_file(env_var_name, api_key)
        
        # Save to state
        if 'api_keys' not in self.saved_state:
            self.saved_state['api_keys'] = {}
        self.saved_state['api_keys'][current_provider] = api_key
        self.save_state()
        
        # Reinitialize AI manager
        self.ai_manager = create_ai_integration()
        
        # Update provider status
        self.update_provider_status_display()
        
        messagebox.showinfo("Success", f"API key saved for {current_provider}!")
        
        # Log the action
        log_to_file('ai_settings', f"API key saved for {current_provider}")
    
    def _save_to_env_file(self, env_var_name: str, value: str):
        """Save environment variable to .env file"""
        try:
            env_file_path = '.env'
            
            # Read existing .env file
            env_vars = {}
            if os.path.exists(env_file_path):
                with open(env_file_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, val = line.split('=', 1)
                            env_vars[key] = val
            
            # Update the specific variable
            env_vars[env_var_name] = value
            
            # Write back to .env file
            with open(env_file_path, 'w') as f:
                for key, val in env_vars.items():
                    f.write(f"{key}={val}\n")
            
            log_to_file('ai_settings', f"Saved {env_var_name} to .env file")
            
        except Exception as e:
            log_to_file('ai_settings', f"Error saving to .env file: {e}")
    
    def get_api_key(self, provider: str) -> str:
        """Get API key for provider from environment or saved state"""
        # First try environment variable
        env_var = f"{provider.upper()}_API_KEY"
        api_key = os.getenv(env_var)
        
        if api_key:
            return api_key
        
        # Then try saved state
        return self.saved_state.get('api_keys', {}).get(provider, '')

    def test_connection(self):
        """Test API connection for current provider"""
        current_provider = self.provider_var.get()
        api_key = self.api_key_entry.get().strip()
        
        if not api_key:
            messagebox.showwarning("Warning", "Please enter an API key first.")
            return
        
        try:
            # Set the API key in environment first
            env_var_name = f"{current_provider.upper()}_API_KEY"
            os.environ[env_var_name] = api_key
            
            # Test the connection
            provider = self.ai_manager.provider
            if hasattr(provider, 'test_connection'):
                success = provider.test_connection(api_key)
                if success:
                    messagebox.showinfo("Success", f"Connection successful for {current_provider}!")
                    
                    # Save API key if test is successful
                    if 'api_keys' not in self.saved_state:
                        self.saved_state['api_keys'] = {}
                    self.saved_state['api_keys'][current_provider] = api_key
                    self.save_state()
                    
                    # Update provider status
                    self.update_provider_status_display()
                    
                    log_to_file('ai_settings', f"Connection test successful for {current_provider}")
                else:
                    messagebox.showerror("Error", f"Connection failed for {current_provider}. Check your API key.")
            else:
                messagebox.showinfo("Info", f"Connection testing not available for {current_provider}")
                
        except Exception as e:
            messagebox.showerror("Error", f"Connection test failed: {str(e)}")
            log_to_file('ai_settings', f"Connection test failed for {current_provider}: {e}")

    def open_setup_url(self):
        """Open the setup URL for the current provider"""
        provider = self.provider_var.get()
        setup_url = self.provider_info[provider]['setup_url']
        
        import webbrowser
        webbrowser.open(setup_url) 