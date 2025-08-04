import tkinter as tk
from tkinter import ttk
from account_manager import load_accounts, SeleniumAccount
from gui.panels.dashboard_panel import DashboardPanel
from gui.panels.reply_panel import ReplyPanel
from gui.panels.dm_panel import DmPanel
from gui.panels.bio_panel import BioPanel
from gui.panels.profile_pic_panel import ProfilePicPanel
from gui.panels.accounts_panel import AccountsPanel
from gui.panels.yapping_panel import YappingPanel
from gui.panels.ai_settings_panel import AISettingsPanel
from gui.panels.settings_panel import SettingsPanel
from gui.panels.scheduled_tasks_panel import ScheduledTasksPanel
from gui.panels.history_panel import HistoryPanel
from gui.panels.reply_comment_panel import ReplyCommentPanel
from gui.panels.like_retweet_panel import LikeRetweetPanel
from selenium_manager import get_global_driver_manager, cleanup_chrome_profile_cache

class TwitterSeleniumGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("P_Tweet_Desk - X (Twitter) Browser Automation GUI")
        self.accounts = load_accounts()
        self.panels = {}
        self.current_panel = None
        
        # Clean up existing Chrome profiles at startup
        self._cleanup_existing_profiles()
        
        self._setup_gui()
        
        # Set up proper cleanup on window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _cleanup_existing_profiles(self):
        """Clean up existing Chrome profiles with multiple cache directories"""
        try:
            print("🧹 Cleaning up existing Chrome profiles...")
            for acc in self.accounts:
                cleanup_chrome_profile_cache(acc)
            print("✅ Chrome profile cleanup completed")
        except Exception as e:
            print(f"⚠️ Error during profile cleanup: {e}")

    def _setup_gui(self):
        self.root.geometry('1000x650')
        self.root.minsize(900, 500)
        # Sidebar
        self.sidebar = ttk.Frame(self.root, width=180)
        self.sidebar.pack(side='left', fill='y')
        self.sidebar.pack_propagate(False)
        self.menu_items = [
            ('Dashboard', self.show_dashboard),
            ('Reply to Tweet', self.show_reply),
            ('Reply to Comment', self.show_reply_comment),
            ('Like and Retweet', self.show_like_retweet),
            ('Send DM', self.show_dm),
            ('Change Bio', self.show_bio),
            ('Change Profile Pic', self.show_profile_pic),
            ('🤖 Yapping', self.show_yapping),
            ('🤖 AI Settings', self.show_ai_settings),
            ('Accounts', self.show_accounts),
            ('Settings', self.show_settings),
            ('Scheduled Tasks', self.show_scheduled_tasks),
            ('History', self.show_history)
        ]
        self.menu_buttons = []
        for idx, (label, cmd) in enumerate(self.menu_items):
            btn = ttk.Button(self.sidebar, text=label, command=cmd)
            btn.pack(fill='x', padx=0, pady=2, ipady=8)
            self.menu_buttons.append(btn)
        # Main content area
        self.content = ttk.Frame(self.root)
        self.content.pack(side='left', fill='both', expand=True)
        # Initialize panels
        self.panels['dashboard'] = DashboardPanel(self.content)
        self.panels['reply'] = ReplyPanel(self.content, self.accounts)
        self.panels['reply_comment'] = ReplyCommentPanel(self.content, self.accounts)
        self.panels['like_retweet'] = LikeRetweetPanel(self.content, self.accounts)
        self.panels['dm'] = DmPanel(self.content, self.accounts)
        self.panels['bio'] = BioPanel(self.content, self.accounts)
        self.panels['profile_pic'] = ProfilePicPanel(self.content, self.accounts)
        self.panels['yapping'] = YappingPanel(self.content, self.accounts)
        self.panels['ai_settings'] = AISettingsPanel(self.content)
        self.panels['accounts'] = AccountsPanel(self.content, self.accounts)
        self.panels['settings'] = SettingsPanel(self.content)
        self.panels['scheduled_tasks'] = ScheduledTasksPanel(self.content)
        self.panels['history'] = HistoryPanel(self.content)
        # Show dashboard by default
        self.show_dashboard()

    def _show_panel(self, key):
        if self.current_panel:
            self.current_panel.pack_forget()
        
        panel = self.panels[key]
        # Check if the panel has a build_panel method and hasn't been built yet
        if hasattr(panel, 'build_panel') and not hasattr(panel, '_built'):
            panel.build_panel()
            panel._built = True
            panel.pack(fill='both', expand=True)
            self.current_panel = panel
        else:
            # Panel is already a widget or has been built
            panel.pack(fill='both', expand=True)
            self.current_panel = panel

    def show_dashboard(self):
        self._show_panel('dashboard')
    def show_reply(self):
        self._show_panel('reply')
    def show_reply_comment(self):
        self._show_panel('reply_comment')
    def show_like_retweet(self):
        self._show_panel('like_retweet')
    def show_dm(self):
        self._show_panel('dm')
    def show_bio(self):
        self._show_panel('bio')
    def show_profile_pic(self):
        self._show_panel('profile_pic')
    def show_yapping(self):
        self._show_panel('yapping')
    def show_ai_settings(self):
        self._show_panel('ai_settings')
    def show_accounts(self):
        self._show_panel('accounts')
    def show_settings(self):
        self._show_panel('settings')
    def show_scheduled_tasks(self):
        self._show_panel('scheduled_tasks')
    def show_history(self):
        self._show_panel('history')

    def on_closing(self):
        """Clean up resources before closing"""
        try:
            # Close the global driver manager (this will save cookies for all accounts)
            driver_manager = get_global_driver_manager()
            driver_manager.close_driver()
            print("✅ Browser drivers closed and cookies saved successfully")
        except Exception as e:
            print(f"⚠️ Error closing browser drivers: {e}")
        
        # Destroy the window
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = TwitterSeleniumGUI(root)
    root.mainloop() 