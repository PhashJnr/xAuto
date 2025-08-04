#!/usr/bin/env python3
"""
Cleanup script for GitHub push - removes unnecessary files
"""

import os
import shutil
import glob

def cleanup_for_github():
    """Remove unnecessary files before GitHub push"""
    print("🧹 Cleaning up for GitHub push...")
    
    # Files to remove
    files_to_remove = [
        # Test and debug files
        "test_*.py",
        "debug_*.py", 
        "verify_*.py",
        "fix_*.py",
        "install_*.py",
        "setup_*.py",
        "download_*.py",
        "persistent_*.py",
        "proxy_*.py",
        "selenium_manager_old.py",
        
        # Development test files
        "test_auto_ui.py",
        "test_attributerror_fix.py",
        "test_contexts.py",
        "test_enhanced_auto.py",
        "test_logging.py",
        "test_comprehensive_logging.py",
        "test_auto_tab.py",
        "test_fix.py",
        "test_ui.py",
        "test_foxyproxy.py",
        "test_multi_tweet_reply.py",
        "test_button_visibility.py",
        "test_simple_reply_panel.py",
        
        # Sample files
        "sample_*.txt",
        "sample_*.json",
        
        # Large files
        "chrome.exe",
        "chromium.exe",
        
        # Proxy files
        "proxy_list.json",
        "sample_proxies.txt",
        "proxy_troubleshooting.md",
        "PROXY_GUIDE.md",
        
        # Debug images
        "debug_*.png",
        "debug_*.jpg",
        "debug_*.jpeg",
        
        # State files
        "ai_settings_state.json",
        "sample_ai_settings.json",
        
        # Build files
        "*.spec",
        "dist/",
        "build/",
        
        # Driver files
        "geckodriver*",
        "chromedriver*",
        
        # Temporary files
        "temp_*.py",
        "tmp_*.py",
        "*.tmp",
        "*.bak",
        "*.old",
        
        # Development artifacts
        "create_proxy_plugin.py",
        "install_socks_support.py",
        "proxy_diagnostic.py",
        "verify_proxy_credentials.py",
        "test_isolated_browsers.py",
        "test_chrome_isolation.py",
        "setup_portable_chrome.py",
        "test_profile_isolation.py",
        "test_proxy_connection.py",
        "test_proxy_parsing.py",
        "test_proxy_fix.py",
        "test_proxy_formats.py",
        "proxy_troubleshooting.md",
        "setup_proxy_extension.py",
        "install_proxy_extension.py",
        "persistent_proxy_setup.py",
        "test_simple_proxy.py",
        "debug_proxy_extension.py",
        "test_browser_isolation.py",
        "fix_proxy_parsing.py",
    ]
    
    # Directories to remove (only those NOT in .gitignore)
    dirs_to_remove = [
        "temp/",
        "tmp/",
        "test_outputs/",
        "debug_outputs/",
    ]
    
    removed_count = 0
    
    # Remove files
    for pattern in files_to_remove:
        for file_path in glob.glob(pattern):
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    print(f"🗑️ Removed file: {file_path}")
                    removed_count += 1
            except Exception as e:
                print(f"⚠️ Could not remove {file_path}: {e}")
    
    # Remove directories
    for dir_path in dirs_to_remove:
        if os.path.exists(dir_path):
            try:
                shutil.rmtree(dir_path)
                print(f"🗑️ Removed directory: {dir_path}")
                removed_count += 1
            except Exception as e:
                print(f"⚠️ Could not remove {dir_path}: {e}")
    
    print(f"\n✅ Cleanup completed! Removed {removed_count} files/directories")
    print("\n📋 Files that should remain:")
    print("- main_app.py")
    print("- gui/")
    print("- selenium_manager.py")
    print("- account_manager.py")
    print("- ai_integration.py")
    print("- create_proxy_plugin.py")
    print("- constants.py")
    print("- utils.py")
    print("- requirements.txt")
    print("- requirements_ai.txt")
    print("- README.md")
    print("- .gitignore")

if __name__ == "__main__":
    cleanup_for_github() 