#!/usr/bin/env python3
"""
Create proxy authentication plugins for Chrome profiles
"""

import os
import json
import re
import shutil
from urllib.parse import urlparse

def parse_proxy(proxy_string):
    """Parse proxy string and extract components"""
    if not proxy_string:
        return None
    
    try:
        # Handle complex proxy strings with multiple colons
        if '@' in proxy_string:
            # Has authentication
            auth_part, server_part = proxy_string.split('@', 1)
            protocol_part = auth_part.split('://')[0] + '://'
            user_pass = auth_part.split('://')[1]
            
            # Handle complex usernames with colons
            if ':' in user_pass:
                # Find the last colon which should be the password separator
                last_colon_index = user_pass.rfind(':')
                username = user_pass[:last_colon_index]
                password = user_pass[last_colon_index + 1:]
            else:
                username, password = user_pass, ""
            
            host_port = server_part
            if ':' in host_port:
                # Find the last colon which should be the port separator
                last_colon_index = host_port.rfind(':')
                host = host_port[:last_colon_index]
                port = host_port[last_colon_index + 1:]
            else:
                host = host_port
                port = "1080" if protocol_part == "socks5://" else "80"
            
            return {
                'protocol': protocol_part.rstrip('://'),
                'host': host,
                'port': int(port),
                'username': username,
                'password': password
            }
        else:
            # No authentication
            if '://' in proxy_string:
                protocol, rest = proxy_string.split('://', 1)
                if ':' in rest:
                    # Find the last colon which should be the port separator
                    last_colon_index = rest.rfind(':')
                    host = rest[:last_colon_index]
                    port = rest[last_colon_index + 1:]
                else:
                    host = rest
                    port = "1080" if protocol == "socks5" else "80"
                
                return {
                    'protocol': protocol,
                    'host': host,
                    'port': int(port),
                    'username': "",
                    'password': ""
                }
            else:
                return None
                
    except Exception as e:
        print(f"❌ Error parsing proxy: {e}")
        return None

def create_proxy_plugin(profile_dir, proxy_string):
    """Create a proxy authentication plugin for a Chrome profile"""
    try:
        # Parse proxy
        proxy_info = parse_proxy(proxy_string)
        if not proxy_info:
            print(f"❌ Invalid proxy string: {proxy_string}")
            return False
        
        # Create extensions directory
        extensions_dir = os.path.join(profile_dir, "chrome_portable", "extensions")
        os.makedirs(extensions_dir, exist_ok=True)
        
        # Create unique extension ID based on profile and proxy
        import hashlib
        extension_id = hashlib.md5(f"{profile_dir}_{proxy_string}".encode()).hexdigest()[:32]
        extension_dir = os.path.join(extensions_dir, extension_id)
        os.makedirs(extension_dir, exist_ok=True)
        
        # Create manifest.json
        manifest = {
            "manifest_version": 3,
            "name": f"Proxy Auth - {proxy_info['host']}",
            "version": "1.0",
            "description": f"Proxy authentication for {proxy_info['protocol']}://{proxy_info['host']}:{proxy_info['port']}",
            "permissions": [
                "proxy",
                "webRequest",
                "webRequestAuthProvider"
            ],
            "background": {
                "service_worker": "background.js"
            },
            "host_permissions": [
                "<all_urls>"
            ]
        }
        
        with open(os.path.join(extension_dir, "manifest.json"), 'w') as f:
            json.dump(manifest, f, indent=2)
        
        # Create background.js
        background_js = f"""
// Proxy Authentication Plugin
const PROXY_CONFIG = {{
    protocol: '{proxy_info['protocol']}',
    host: '{proxy_info['host']}',
    port: {proxy_info['port']},
    username: '{proxy_info['username']}',
    password: '{proxy_info['password']}'
}};

// Set up proxy
chrome.proxy.settings.set({{
    value: {{
        mode: "fixed_servers",
        rules: {{
            singleProxy: {{
                scheme: PROXY_CONFIG.protocol,
                host: PROXY_CONFIG.host,
                port: PROXY_CONFIG.port
            }}
        }}
    }},
    scope: 'regular'
}});

// Handle proxy authentication
chrome.webRequest.onAuthRequired.addListener(
    function(details, callback) {{
        if (PROXY_CONFIG.username && PROXY_CONFIG.password) {{
            callback({{
                authCredentials: {{
                    username: PROXY_CONFIG.username,
                    password: PROXY_CONFIG.password
                }}
            }});
        }} else {{
            callback({{}});
        }}
    }},
    {{urls: ["<all_urls>"]}},
    ["asyncBlocking"]
);

console.log('Proxy plugin loaded:', PROXY_CONFIG);
"""
        
        with open(os.path.join(extension_dir, "background.js"), 'w') as f:
            f.write(background_js)
        
        print(f"✅ Created proxy plugin for {os.path.basename(profile_dir)}")
        print(f"   Protocol: {proxy_info['protocol']}")
        print(f"   Host: {proxy_info['host']}:{proxy_info['port']}")
        if proxy_info['username']:
            print(f"   Auth: {proxy_info['username']}:***")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating proxy plugin: {e}")
        return False

def setup_proxy_for_account(acc):
    """Setup proxy plugin for a specific account"""
    if not acc.proxy:
        print(f"ℹ️ No proxy configured for {acc.label}")
        return True
    
    profile_dir = acc.get_chrome_profile_path()
    return create_proxy_plugin(profile_dir, acc.proxy)

def setup_proxy_for_all_accounts():
    """Setup proxy plugins for all accounts"""
    from account_manager import load_accounts
    
    accounts = load_accounts()
    if not accounts:
        print("❌ No accounts found")
        return False
    
    print(f"🔧 Setting up proxy plugins for {len(accounts)} accounts...")
    
    success_count = 0
    for acc in accounts:
        if acc.proxy:
            if setup_proxy_for_account(acc):
                success_count += 1
        else:
            print(f"ℹ️ No proxy for {acc.label}")
    
    print(f"✅ Created {success_count} proxy plugins")
    return success_count

def remove_proxy_plugins():
    """Remove all proxy plugins from profiles"""
    chrome_profiles_dir = "chrome_profiles"
    if not os.path.exists(chrome_profiles_dir):
        print("❌ No chrome_profiles directory found")
        return
    
    profiles = [d for d in os.listdir(chrome_profiles_dir) 
                if os.path.isdir(os.path.join(chrome_profiles_dir, d))]
    
    removed_count = 0
    for profile in profiles:
        profile_path = os.path.join(chrome_profiles_dir, profile)
        extensions_dir = os.path.join(profile_path, "chrome_portable", "extensions")
        
        if os.path.exists(extensions_dir):
            # Remove proxy plugins (extensions with proxy in name)
            for ext_dir in os.listdir(extensions_dir):
                ext_path = os.path.join(extensions_dir, ext_dir)
                if os.path.isdir(ext_path):
                    manifest_path = os.path.join(ext_path, "manifest.json")
                    if os.path.exists(manifest_path):
                        try:
                            with open(manifest_path, 'r') as f:
                                manifest = json.load(f)
                                if "proxy" in manifest.get("name", "").lower():
                                    shutil.rmtree(ext_path)
                                    print(f"✅ Removed proxy plugin from {profile}")
                                    removed_count += 1
                        except:
                            pass
    
    print(f"✅ Removed {removed_count} proxy plugins")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "setup":
            setup_proxy_for_all_accounts()
        elif sys.argv[1] == "remove":
            remove_proxy_plugins()
        elif sys.argv[1] == "test":
            # Test proxy parsing
            test_proxies = [
                "socks5://user:pass@host.com:1080",
                "http://user:pass@host.com:8080",
                "socks5://host.com:1080",
                "http://host.com:8080"
            ]
            for proxy in test_proxies:
                result = parse_proxy(proxy)
                print(f"Proxy: {proxy}")
                print(f"Parsed: {result}")
                print()
        else:
            print("Usage:")
            print("  python create_proxy_plugin.py setup")
            print("  python create_proxy_plugin.py remove")
            print("  python create_proxy_plugin.py test")
    else:
        # Default: setup proxy plugins for all accounts
        setup_proxy_for_all_accounts() 