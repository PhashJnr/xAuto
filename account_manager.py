import os
import json
from constants import ACCOUNTS_FILE, COOKIE_DIR

class SeleniumAccount:
    def __init__(self, label, username, password=None, status=None, avatar_url=None, tags=None, proxy=None):
        self.label = label
        self.username = username
        self.password = password  # Only in memory, not saved to disk
        self.status = status      # Persisted
        self.avatar_url = avatar_url  # Persisted
        self.tags = tags or []   # List of tags
        self.proxy = proxy       # Proxy string (socks5:// or http://)

    def get_cookie_path(self):
        return os.path.join(COOKIE_DIR, f'{self.label}_cookies.pkl')

    def get_chrome_profile_path(self):
        """Get the Chrome profile path for this account"""
        # Create a safe profile name by replacing spaces and special characters
        safe_label = self.label.replace(' ', '_').replace('/', '_').replace('\\', '_')
        return os.path.join('chrome_profiles', safe_label)

    def to_dict(self):
        return {
            'label': self.label,
            'username': self.username,
            'status': self.status,
            'avatar_url': self.avatar_url,
            'tags': self.tags,
            'proxy': self.proxy
        }

    @staticmethod
    def from_dict(d):
        return SeleniumAccount(
            d['label'],
            d['username'],
            None,
            d.get('status'),
            d.get('avatar_url'),
            d.get('tags', []),
            d.get('proxy')
        )

def load_accounts():
    if os.path.exists(ACCOUNTS_FILE):
        with open(ACCOUNTS_FILE, 'r') as f:
            data = json.load(f)
            return [SeleniumAccount.from_dict(acc) for acc in data]
    return []

def save_accounts(accounts):
    with open(ACCOUNTS_FILE, 'w') as f:
        json.dump([acc.to_dict() for acc in accounts], f, indent=2) 