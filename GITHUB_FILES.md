# 📁 GitHub Repository Files

## ✅ Core Files (Keep These)

### Main Application

- `main_app.py` - Main application entry point
- `constants.py` - Application constants
- `utils.py` - Utility functions

### Core Modules

- `selenium_manager.py` - Browser automation core
- `account_manager.py` - Account management
- `ai_integration.py` - AI integration for replies
- `create_proxy_plugin.py` - Proxy plugin creation

### GUI

- `gui/` - Complete GUI directory
  - `gui/main_app.py` - Main GUI application
  - `gui/panels/` - All panel modules
    - `accounts_panel.py`
    - `yapping_panel.py`
    - `reply_comment_panel.py`
    - etc.

### Configuration

- `requirements.txt` - Python dependencies
- `requirements_ai.txt` - AI-specific dependencies
- `README.md` - Project documentation
- `.gitignore` - Git ignore rules

## ❌ Files to Exclude (Already in .gitignore)

### Personal Data

- `chrome_profiles/` - Browser profiles (contain personal data)
- `cookies/` - Cookie files (contain session data)
- `accounts.json` - Account data (contains sensitive info)
- `*.pkl` - Pickle files (contain session data)

### Test & Debug Files

- `test_*.py` - Test files
- `debug_*.py` - Debug files
- `verify_*.py` - Verification files
- `fix_*.py` - Fix scripts
- `install_*.py` - Installation scripts
- `setup_*.py` - Setup scripts
- `download_*.py` - Download scripts
- `persistent_*.py` - Persistent scripts
- `proxy_*.py` - Proxy test files
- `selenium_manager_old.py` - Old version

### Large Files

- `chrome.exe` - Chrome executable (too large)
- `chromium.exe` - Chromium executable (too large)
- `debug_*.png` - Debug screenshots
- `debug_*.jpg` - Debug images

### Logs & State

- `logs/` - Log files
- `*.log` - Log files
- `ai_settings_state.json` - AI state
- `sample_*.json` - Sample files

### Build Artifacts

- `dist/` - Distribution files
- `build/` - Build files
- `*.spec` - PyInstaller specs

## 🚀 GitHub Push Checklist

### Before Pushing:

1. ✅ Run cleanup script: `python cleanup_for_github.py`
2. ✅ Verify .gitignore is updated
3. ✅ Check no sensitive data is included
4. ✅ Ensure all core files are present

### Core Files to Include:

```
xAuto/
├── main_app.py
├── constants.py
├── utils.py
├── selenium_manager.py
├── account_manager.py
├── ai_integration.py
├── create_proxy_plugin.py
├── requirements.txt
├── requirements_ai.txt
├── README.md
├── .gitignore
└── gui/
    ├── main_app.py
    └── panels/
        ├── accounts_panel.py
        ├── yapping_panel.py
        ├── reply_comment_panel.py
        └── ...
```

### Files to Exclude:

- All test/debug files
- Personal data (profiles, cookies, accounts)
- Large executables
- Log files
- State files
- Build artifacts

## 🔒 Security Notes

### Never Include:

- `accounts.json` - Contains real account data
- `chrome_profiles/` - Contains personal browser data
- `cookies/` - Contains session cookies
- `*.pkl` - Contains serialized session data
- `ai_settings_state.json` - Contains AI state
- Any `.env` files
- API keys or secrets

### Safe to Include:

- Code files (`.py`)
- Configuration templates
- Documentation
- Requirements files
- GUI files
