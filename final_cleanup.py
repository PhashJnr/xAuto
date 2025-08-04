#!/usr/bin/env python3
"""
Final cleanup script for GitHub push - removes remaining unnecessary files
"""

import os
import shutil

def final_cleanup():
    """Remove remaining unnecessary files before GitHub push"""
    print("🧹 Final cleanup for GitHub push...")
    
    # Directories to remove (only those NOT in .gitignore)
    dirs_to_remove = [
        "temp/",
        "tmp/",
        "test_outputs/",
        "debug_outputs/",
    ]
    
    # Files to remove (only those NOT in .gitignore)
    files_to_remove = [
        "GITHUB_FILES.md",
        "SETUP_GITHUB.md",
        "create_proxy_plugin.py",
        "cleanup_for_github.py",
        "final_cleanup.py",
    ]
    
    removed_count = 0
    
    # Remove directories
    for dir_path in dirs_to_remove:
        if os.path.exists(dir_path):
            try:
                shutil.rmtree(dir_path)
                print(f"🗑️ Removed directory: {dir_path}")
                removed_count += 1
            except Exception as e:
                print(f"⚠️ Could not remove {dir_path}: {e}")
    
    # Remove files
    for file_path in files_to_remove:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"🗑️ Removed file: {file_path}")
                removed_count += 1
            except Exception as e:
                print(f"⚠️ Could not remove {file_path}: {e}")
    
    print(f"\n✅ Final cleanup completed! Removed {removed_count} files/directories")
    
    # Show remaining files
    print("\n📋 Files that should remain for GitHub:")
    remaining_files = [
        "main_app.py",
        "gui/",
        "selenium_manager.py", 
        "account_manager.py",
        "ai_integration.py",
        "constants.py",
        "utils.py",
        "requirements.txt",
        "requirements_ai.txt",
        "README.md",
        ".gitignore"
    ]
    
    for file in remaining_files:
        if os.path.exists(file):
            print(f"✅ {file}")
        else:
            print(f"❌ {file} (missing)")

if __name__ == "__main__":
    final_cleanup() 