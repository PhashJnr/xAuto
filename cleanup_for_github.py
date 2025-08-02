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
        
        # Log files
        "*.log",
        
        # Build files
        "*.spec",
        "dist/",
        "build/",
        
        # Driver files
        "geckodriver*",
        "chromedriver*",
    ]
    
    # Directories to remove
    dirs_to_remove = [
        "chrome_profiles/",
        "cookies/",
        "logs/",
        "drivers/",
        "chromium_portable/",
        "chrome_portable/",
        "firefox_profiles/",
        "__pycache__/",
        ".git/",
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