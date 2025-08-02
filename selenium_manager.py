import os
import pickle
import time
import threading
from selenium.webdriver.chrome.options import Options
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from constants import COOKIE_DIR
from account_manager import SeleniumAccount

# Global driver manager for persistent sessions
_global_driver_manager = None

def get_global_driver_manager():
    """Get or create the global driver manager"""
    global _global_driver_manager
    if _global_driver_manager is None:
        _global_driver_manager = SeleniumDriverManager()
    return _global_driver_manager

def load_cookies_safely(driver, cookie_path, acc_label):
    """Load cookies with better error handling"""
    try:
        if not os.path.exists(cookie_path):
            print(f"⚠️ No cookies found for {acc_label}")
            return
        
        with open(cookie_path, 'rb') as f:
            cookies = pickle.load(f)
        
        print(f"🍪 Loading {len(cookies)} cookies for {acc_label}")
        
        # Navigate to Twitter first
        driver.get('https://x.com/')
        time.sleep(2)
        
        # Add cookies with better error handling
        successful_cookies = 0
        for cookie in cookies:
            try:
                # Clean up cookie domain if needed
                if 'domain' in cookie:
                    # Remove leading dot if present
                    if cookie['domain'].startswith('.'):
                        cookie['domain'] = cookie['domain'][1:]
                    # Ensure domain is valid
                    if not cookie['domain'] or cookie['domain'] == '':
                        continue
                
                driver.add_cookie(cookie)
                successful_cookies += 1
            except Exception as e:
                # Skip invalid cookies silently
                continue
        
        if successful_cookies > 0:
            # Refresh to apply cookies
            driver.refresh()
            time.sleep(2)
            print(f"✅ Successfully loaded {successful_cookies}/{len(cookies)} cookies for {acc_label}")
        else:
            print(f"⚠️ No valid cookies loaded for {acc_label}")
            
    except Exception as e:
        print(f"⚠️ Error loading cookies for {acc_label}: {e}")

class SeleniumDriverManager:
    def __init__(self):
        self.driver = None
        self.driver_account_label = None
        self._lock = threading.Lock()
    
    def is_driver_valid(self, driver):
        """Check if driver is still valid"""
        try:
            driver.current_url
            return True
        except Exception:
            return False
    
    def get_driver(self, acc):
        """Get or create a driver for the account"""
        with self._lock:
            # Check if we have a valid driver for this account
            if (self.driver and 
                self.driver_account_label == acc.label and 
                self.is_driver_valid(self.driver)):
                print(f"🔄 Reusing existing browser session for {acc.label}")
                return self.driver
            
            # Close existing driver if it exists
            if self.driver:
                try:
                    self.driver.quit()
                except Exception:
                    pass
                self.driver = None
                self.driver_account_label = None
            
            # Create new driver using the new approach
            try:
                print(f"🆕 Creating new browser session for {acc.label}")
                
                # Use the new open_browser_with_profile function
                self.driver = open_browser_with_profile(acc)
                
                if self.driver:
                    self.driver_account_label = acc.label
                    print(f"✅ Browser session created for {acc.label}")
                    return self.driver
                else:
                    print(f"❌ Failed to create browser session for {acc.label}")
                    return None
                
            except Exception as e:
                print(f"❌ Error creating browser session for {acc.label}: {e}")
                self.driver = None
                self.driver_account_label = None
                return None

    def close_driver(self):
        """Close the current driver"""
        with self._lock:
            if self.driver:
                try:
                    self.driver.quit()
                except Exception:
                    pass
                self.driver = None
                self.driver_account_label = None

    def save_cookies(self, driver, acc):
        with open(acc.get_cookie_path(), 'wb') as f:
            pickle.dump(driver.get_cookies(), f)

    def load_cookies(self, driver, acc):
        path = acc.get_cookie_path()
        if os.path.exists(path):
            with open(path, 'rb') as f:
                cookies = pickle.load(f)
            driver.get('https://x.com/')
            for cookie in cookies:
                try:
                    driver.add_cookie(cookie)
                except Exception:
                    pass

def save_cookies(driver, acc):
    """Save cookies for the account"""
    try:
        with open(acc.get_cookie_path(), 'wb') as f:
            pickle.dump(driver.get_cookies(), f)
        print(f"🍪 Cookies saved for {acc.label}")
    except Exception as e:
        print(f"❌ Error saving cookies for {acc.label}: {e}")

def login_with_cookies(driver, acc, target_url=None):
    """Login using saved cookies"""
    try:
        cookie_path = acc.get_cookie_path()
        if not os.path.exists(cookie_path):
            print(f"⚠️ No cookies found for {acc.label}")
            return False
        
        # Load cookies
        load_cookies_safely(driver, cookie_path, acc.label)
        
        # Navigate to target URL or Twitter
        if target_url:
            driver.get(target_url)
        else:
            driver.get('https://x.com/')
        
        time.sleep(3)
        
        # Check if login was successful
        if 'x.com' in driver.current_url or 'twitter.com' in driver.current_url:
            print(f"✅ Successfully logged in with cookies for {acc.label}")
            return True
        else:
            print(f"⚠️ Cookie login may have failed for {acc.label}")
            return False
            
    except Exception as e:
        print(f"❌ Error during cookie login for {acc.label}: {e}")
        return False

def manual_login(acc):
    """Open browser for manual login"""
    try:
        driver = open_browser_with_profile(acc)
        if driver:
            print(f"🔓 Browser opened for manual login: {acc.label}")
            print("💡 Please log in manually and close the browser when done")
            return driver
        else:
            print(f"❌ Failed to open browser for manual login: {acc.label}")
            return None
    except Exception as e:
        print(f"❌ Error opening browser for manual login: {e}")
        return None

def check_tweet_accessibility(driver, tweet_url):
    """Check if tweet is accessible and get basic info"""
    try:
        driver.get(tweet_url)
        time.sleep(3)
        
        # Check if page loaded successfully
        if 'x.com' not in driver.current_url and 'twitter.com' not in driver.current_url:
            return False, "Page not loaded"
        
        # Check for common error elements
        error_selectors = [
            'div[data-testid="error-page"]',
            'div[data-testid="empty-state"]',
            'div[role="alert"]'
        ]
        
        for selector in error_selectors:
            try:
                error_element = driver.find_element(By.CSS_SELECTOR, selector)
                if error_element.is_displayed():
                    return False, f"Error element found: {selector}"
            except:
                pass
        
        # Check for tweet content
        try:
            tweet_content = driver.find_element(By.CSS_SELECTOR, 'div[data-testid="tweetText"]')
            if tweet_content.is_displayed():
                return True, "Tweet accessible"
        except:
            pass
        
        return True, "Page loaded successfully"
        
    except Exception as e:
        return False, f"Error checking tweet: {e}"

def reply_to_tweet(acc, tweet_url, reply_text):
    """Reply to a tweet"""
    try:
        driver = get_global_driver_manager().get_driver(acc)
        if not driver:
            print(f"❌ Failed to get driver for {acc.label}")
            return False, "Failed to get driver"
        
        # Navigate to tweet
        driver.get(tweet_url)
        time.sleep(3)
        
        # Check if tweet is accessible
        accessible, message = check_tweet_accessibility(driver, tweet_url)
        if not accessible:
            print(f"❌ Tweet not accessible: {message}")
            return False, f"Tweet not accessible: {message}"
        
        # Find and click reply button - try multiple selectors
        reply_button = None
        selectors = [
            'div[data-testid="reply"]',
            'div[data-testid="tweetButtonInline"]',
            'button[data-testid="reply"]',
            'button[data-testid="tweetButtonInline"]',
            '[data-testid="reply"]',
            '[data-testid="tweetButtonInline"]'
        ]
        
        for selector in selectors:
            try:
                reply_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                )
                print(f"✅ Found reply button with selector: {selector}")
                break
            except Exception:
                continue
        
        if not reply_button:
            print(f"❌ Could not find reply button with any selector")
            return False, "Could not find reply button"
        
        # Click reply button
        reply_button.click()
        time.sleep(2)
        
        # Find reply text box - try multiple selectors
        reply_box = None
        textarea_selectors = [
            'div[data-testid="tweetTextarea_0"]',
            'div[data-testid="tweetTextarea"]',
            'div[contenteditable="true"]',
            'div[role="textbox"]',
            '[data-testid="tweetTextarea_0"]',
            '[data-testid="tweetTextarea"]'
        ]
        
        for selector in textarea_selectors:
            try:
                reply_box = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                print(f"✅ Found reply box with selector: {selector}")
                break
            except Exception:
                continue
        
        if not reply_box:
            print(f"❌ Could not find reply text box")
            return False, "Could not find reply text box"
        
        # Clear and type reply
        try:
            # Clear the text area first
            reply_box.clear()
            time.sleep(1)
            
            # Clean the reply text to remove problematic characters
            cleaned_reply_text = _clean_text_for_typing(reply_text)
            
            # Try multiple methods to input text
            try:
                # Method 1: Human-like typing simulation
                _type_like_human(driver, reply_box, cleaned_reply_text)
                print(f"✅ Typed reply using human-like simulation")
            except Exception as e1:
                print(f"⚠️ Human-like typing failed: {e1}")
                try:
                    # Method 2: Direct send_keys with cleaned text
                    reply_box.send_keys(cleaned_reply_text)
                    print(f"✅ Typed reply using send_keys")
                except Exception as e2:
                    print(f"⚠️ send_keys failed: {e2}")
                    try:
                        # Method 3: Click to focus, then send_keys
                        reply_box.click()
                        time.sleep(1)
                        reply_box.send_keys(cleaned_reply_text)
                        print(f"✅ Typed reply using click + send_keys")
                    except Exception as e3:
                        print(f"⚠️ click + send_keys failed: {e3}")
                        try:
                            # Method 4: JavaScript to set value
                            driver.execute_script("arguments[0].innerHTML = arguments[1];", reply_box, cleaned_reply_text)
                            print(f"✅ Typed reply using JavaScript")
                        except Exception as e4:
                            print(f"⚠️ JavaScript failed: {e4}")
                            try:
                                # Method 5: Use Keys.CONTROL + "a" to select all, then type
                                reply_box.send_keys(Keys.CONTROL + "a")
                                time.sleep(0.5)
                                reply_box.send_keys(cleaned_reply_text)
                                print(f"✅ Typed reply using select all + send_keys")
                            except Exception as e5:
                                print(f"❌ All text input methods failed: {e5}")
                                return False, f"Could not input text: {e5}"
            
            # Verify text was entered
            time.sleep(1)
            actual_text = reply_box.get_attribute('innerHTML') or reply_box.get_attribute('textContent') or reply_box.text
            if not actual_text or actual_text.strip() == '':
                print(f"⚠️ Text verification failed, trying alternative input method")
                # Try one more time with JavaScript
                driver.execute_script("arguments[0].innerHTML = arguments[1];", reply_box, cleaned_reply_text)
                time.sleep(1)
            
            print(f"✅ Reply text entered: {cleaned_reply_text[:50]}...")
            
        except Exception as e:
            print(f"❌ Error entering reply text: {e}")
            return False, f"Error entering reply text: {e}"
        
        # Click reply button - try multiple selectors
        post_button = None
        post_selectors = [
            'div[data-testid="tweetButton"]',
            'div[data-testid="tweetButtonInline"]',
            'button[data-testid="tweetButton"]',
            'button[data-testid="tweetButtonInline"]',
            '[data-testid="tweetButton"]',
            '[data-testid="tweetButtonInline"]'
        ]
        
        for selector in post_selectors:
            try:
                post_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                )
                print(f"✅ Found post button with selector: {selector}")
                break
            except Exception:
                continue
        
        if not post_button:
            print(f"❌ Could not find post button")
            return False, "Could not find post button"
        
        # Click post button
        try:
            # Try to scroll the button into view first
            driver.execute_script("arguments[0].scrollIntoView(true);", post_button)
            time.sleep(1)
            
            # Wait for button to be interactable
            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, f'[data-testid="tweetButton"], [data-testid="tweetButtonInline"]'))
            )
            
            # Try JavaScript click first (more reliable)
            driver.execute_script("arguments[0].click();", post_button)
            time.sleep(2)
            
            # Verify the click worked by checking if we're still on the same page
            current_url = driver.current_url
            if tweet_url in current_url:
                print(f"✅ Reply posted successfully for {acc.label}")
                return True, "Reply posted successfully"
            else:
                print(f"⚠️ Click may not have worked, trying alternative method")
                
        except Exception as e:
            print(f"⚠️ JavaScript click failed: {e}")
            
            # Try to handle click interception
            if handle_click_interception(driver, post_button):
                time.sleep(3)
                print(f"✅ Reply posted successfully for {acc.label}")
                return True, "Reply posted successfully"
            
            # Fallback to regular click with retry
            try:
                # Wait a bit and try again
                time.sleep(2)
                
                # Try to find the button again (it might have changed)
                for selector in post_selectors:
                    try:
                        post_button = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                        print(f"✅ Found post button again with selector: {selector}")
                        break
                    except Exception:
                        continue
                
                if post_button:
                    post_button.click()
                    time.sleep(3)
                    print(f"✅ Reply posted successfully for {acc.label}")
                    return True, "Reply posted successfully"
                else:
                    print(f"❌ Could not find post button for retry")
                    return False, "Could not find post button for retry"
                    
            except Exception as e2:
                print(f"❌ Regular click also failed: {e2}")
                return False, f"Click failed: {e2}"
            
    except Exception as e:
        print(f"❌ Error replying to tweet: {e}")
        return False, f"Error replying to tweet: {e}"

def reply_to_comment(acc, tweet_url, comment_username, reply_text):
    """Reply to a specific comment on a tweet"""
    try:
        driver = get_global_driver_manager().get_driver(acc)
        if not driver:
            print(f"❌ Failed to get driver for {acc.label}")
            return False, "Failed to get driver"
        
        # Navigate to tweet
        driver.get(tweet_url)
        time.sleep(3)
        
        # Check if tweet is accessible
        accessible, message = check_tweet_accessibility(driver, tweet_url)
        if not accessible:
            print(f"❌ Tweet not accessible: {message}")
            return False, f"Tweet not accessible: {message}"
        
        # Scroll to load comments
        for _ in range(5):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
        
        # Find the specific comment by username
        articles = driver.find_elements(By.CSS_SELECTOR, 'article[data-testid="tweet"]')
        target_comment = None
        
        for article in articles[1:]:  # Skip the main tweet
            try:
                # Find username in the comment
                username_elem = article.find_element(By.CSS_SELECTOR, 'div[dir="ltr"] span')
                username = username_elem.text
                
                if username == comment_username:
                    target_comment = article
                    print(f"✅ Found comment by @{username}")
                    break
            except Exception:
                continue
        
        if not target_comment:
            print(f"❌ Could not find comment by @{comment_username}")
            return False, f"Could not find comment by @{comment_username}"
        
        # Scroll to the comment
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", target_comment)
        time.sleep(2)
        
        # Find reply button within this specific comment
        try:
            reply_button = target_comment.find_element(By.CSS_SELECTOR, '[data-testid="reply"]')
        except:
            try:
                reply_button = target_comment.find_element(By.CSS_SELECTOR, 'button[aria-label*="Reply"]')
            except:
                print(f"❌ Could not find reply button for comment by @{comment_username}")
                return False, f"Could not find reply button for comment by @{comment_username}"
        
        # Click reply button with interception handling
        try:
            # Scroll the button into view
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", reply_button)
            time.sleep(1)
            
            # Try JavaScript click first
            driver.execute_script("arguments[0].click();", reply_button)
            time.sleep(2)
        except Exception as e:
            print(f"⚠️ JavaScript click failed: {e}")
            if not handle_click_interception(driver, reply_button):
                print(f"❌ Could not click reply button for comment by @{comment_username}")
                return False, f"Could not click reply button for comment by @{comment_username}"
        
        # Find reply text box
        reply_box = None
        textarea_selectors = [
            'div[data-testid="tweetTextarea_0"]',
            'div[data-testid="tweetTextarea"]',
            'div[contenteditable="true"]',
            'div[role="textbox"]'
        ]
        
        for selector in textarea_selectors:
            try:
                reply_box = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                print(f"✅ Found reply box with selector: {selector}")
                break
            except Exception:
                continue
        
        if not reply_box:
            print(f"❌ Could not find reply text box")
            return False, "Could not find reply text box"
        
        # Clear and type reply
        try:
            # Clear the text area first
            reply_box.clear()
            time.sleep(1)
            
            # Clean the reply text
            cleaned_reply_text = _clean_text_for_typing(reply_text)
            
            # Type the reply
            _type_like_human(driver, reply_box, cleaned_reply_text)
            print(f"✅ Typed reply to comment by @{comment_username}")
            
        except Exception as e:
            print(f"❌ Error entering reply text: {e}")
            return False, f"Error entering reply text: {e}"
        
        # Click post button
        post_button = None
        post_selectors = [
            'div[data-testid="tweetButton"]',
            'div[data-testid="tweetButtonInline"]',
            'button[data-testid="tweetButton"]',
            'button[data-testid="tweetButtonInline"]'
        ]
        
        for selector in post_selectors:
            try:
                post_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                )
                print(f"✅ Found post button with selector: {selector}")
                break
            except Exception:
                continue
        
        if not post_button:
            print(f"❌ Could not find post button")
            return False, "Could not find post button"
        
        # Click post button
        try:
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", post_button)
            time.sleep(1)
            driver.execute_script("arguments[0].click();", post_button)
            time.sleep(3)
            
            print(f"✅ Successfully replied to comment by @{comment_username}")
            return True, f"Successfully replied to comment by @{comment_username}"
            
        except Exception as e:
            print(f"⚠️ JavaScript click failed: {e}")
            if handle_click_interception(driver, post_button):
                time.sleep(3)
                print(f"✅ Successfully replied to comment by @{comment_username}")
                return True, f"Successfully replied to comment by @{comment_username}"
            else:
                print(f"❌ Could not post reply to comment by @{comment_username}")
                return False, f"Could not post reply to comment by @{comment_username}"
            
    except Exception as e:
        print(f"❌ Error replying to comment: {e}")
        return False, f"Error replying to comment: {e}"

def send_dm(acc, recipient_username, message):
    """Send a direct message"""
    try:
        driver = get_global_driver_manager().get_driver(acc)
        if not driver:
            print(f"❌ Failed to get driver for {acc.label}")
            return False
        
        # Navigate to messages
        driver.get('https://x.com/messages')
        time.sleep(3)
        
        # Click new message button
        try:
            new_message_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'a[data-testid="NewDM_Button"]'))
            )
            new_message_button.click()
            time.sleep(2)
        except Exception as e:
            print(f"❌ Could not find new message button: {e}")
            return False
        
        # Enter recipient username
        try:
            recipient_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[data-testid="searchPeople"]'))
            )
            recipient_input.clear()
            recipient_input.send_keys(recipient_username)
            time.sleep(2)
            
            # Select first result
            first_result = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'div[data-testid="typeaheadResult"]'))
            )
            first_result.click()
            time.sleep(1)
            
        except Exception as e:
            print(f"❌ Could not find recipient: {e}")
            return False
        
        # Enter message
        try:
            message_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-testid="dmComposerTextInput"]'))
            )
            message_input.clear()
            message_input.send_keys(message)
            time.sleep(1)
            
        except Exception as e:
            print(f"❌ Could not find message input: {e}")
            return False
        
        # Send message
        try:
            send_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'div[data-testid="dmComposerSendButton"]'))
            )
            send_button.click()
            time.sleep(3)
            
            print(f"✅ DM sent successfully for {acc.label}")
            return True
            
        except Exception as e:
            print(f"❌ Could not send DM: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Error sending DM: {e}")
        return False

def change_bio(acc, new_bio):
    """Change account bio"""
    try:
        driver = get_global_driver_manager().get_driver(acc)
        if not driver:
            print(f"❌ Failed to get driver for {acc.label}")
            return False
        
        # Navigate to profile settings
        driver.get('https://x.com/settings/profile')
        time.sleep(3)
        
        # Find bio input
        try:
            bio_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'textarea[name="description"]'))
            )
            bio_input.clear()
            bio_input.send_keys(new_bio)
            time.sleep(1)
            
        except Exception as e:
            print(f"❌ Could not find bio input: {e}")
            return False
        
        # Save changes
        try:
            save_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'div[data-testid="saveButton"]'))
            )
            save_button.click()
            time.sleep(3)
            
            print(f"✅ Bio changed successfully for {acc.label}")
            return True
            
        except Exception as e:
            print(f"❌ Could not save bio: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Error changing bio: {e}")
        return False

def change_profile_pic(acc, image_path):
    """Change profile picture"""
    try:
        driver = get_global_driver_manager().get_driver(acc)
        if not driver:
            print(f"❌ Failed to get driver for {acc.label}")
            return False
        
        # Navigate to profile settings
        driver.get('https://x.com/settings/profile')
        time.sleep(3)
        
        # Find profile picture upload button
        try:
            upload_button = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="file"]'))
            )
            upload_button.send_keys(image_path)
            time.sleep(3)
            
        except Exception as e:
            print(f"❌ Could not find upload button: {e}")
            return False
        
        # Save changes
        try:
            save_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'div[data-testid="saveButton"]'))
            )
            save_button.click()
            time.sleep(3)
            
            print(f"✅ Profile picture changed successfully for {acc.label}")
            return True
            
        except Exception as e:
            print(f"❌ Could not save profile picture: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Error changing profile picture: {e}")
        return False

def find_reply_box(driver):
    """Find reply text box"""
    try:
        reply_box = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-testid="tweetTextarea_0"]'))
        )
        return reply_box
    except Exception as e:
        print(f"❌ Could not find reply box: {e}")
        return None

def create_preconfigured_chrome_profile(profile_dir):
    """Create a pre-configured Chrome profile to prevent profile selection dialog"""
    try:
        import json
        import os
        
        # Create profile directory structure
        os.makedirs(profile_dir, exist_ok=True)
        
        # Create Local State file to prevent profile selection
        local_state_path = os.path.join(profile_dir, "Local State")
        local_state = {
            "browser": {
                "last_known_google_url": "https://www.google.com/",
                "last_prompted_google_url": "https://www.google.com/"
            },
            "profile": {
                "last_used": "Default",
                "name_dictionary": {
                    "Default": {
                        "active_time": 0,
                        "avatar_icon": "chrome://theme/IDR_PROFILE_AVATAR_26",
                        "background_apps": False,
                        "managed_user_id": "",
                        "name": "Default",
                        "user_name": ""
                    }
                }
            },
            "session": {
                "restore_on_startup": 4
            },
            "shutdown": {
                "type": "Normal"
            }
        }
        
        with open(local_state_path, 'w', encoding='utf-8') as f:
            json.dump(local_state, f, indent=2)
        
        # Create Default profile directory
        default_profile = os.path.join(profile_dir, "Default")
        os.makedirs(default_profile, exist_ok=True)
        
        # Create Preferences file
        preferences_path = os.path.join(default_profile, "Preferences")
        preferences = {
            "account_id_migration_state": 2,
            "account_tracker_service_last_update": "1337",
            "browser": {
                "window_placement": {
                    "bottom": 1050,
                    "left": 100,
                    "right": 1420,
                    "top": 100
                }
            },
            "profile": {
                "name": "Default",
                "name_dictionary": {
                    "Default": {
                        "active_time": 0,
                        "avatar_icon": "chrome://theme/IDR_PROFILE_AVATAR_26",
                        "background_apps": False,
                        "managed_user_id": "",
                        "name": "Default",
                        "user_name": ""
                    }
                }
            },
            "session": {
                "restore_on_startup": 4
            }
        }
        
        with open(preferences_path, 'w', encoding='utf-8') as f:
            json.dump(preferences, f, indent=2)
        
        print(f"✅ Created pre-configured Chrome profile at: {profile_dir}")
        return True
        
    except Exception as e:
        print(f"❌ Error creating pre-configured profile: {e}")
        return False

def setup_chrome_for_account(acc):
    """Automatically setup extensions for a new account"""
    try:
        from download_extensions import install_extensions_for_profile
        
        profile_dir = acc.get_chrome_profile_path()
        print(f"🔧 Auto-setting up extensions for new account: {acc.label}")
        
        # Install default extensions for new account
        print(f"🔧 Installing extensions for {acc.label}...")
        install_extensions_for_profile(profile_dir)
        
        return True
            
    except Exception as e:
        print(f"❌ Error setting up extensions for {acc.label}: {e}")
        return False

def create_simple_isolated_chrome(acc):
    """Create simple isolated Chrome instance - Chrome only, no proxy"""
    import tempfile
    import uuid
    import os
    
    try:
        # Create isolated profile directory
        profile_dir = acc.get_chrome_profile_path()
        os.makedirs(profile_dir, exist_ok=True)
        
        # Create isolated directories
        unique_id = str(uuid.uuid4())[:8]
        isolated_cache = os.path.join(profile_dir, f"cache_{unique_id}")
        isolated_media = os.path.join(profile_dir, f"media_{unique_id}")
        
        os.makedirs(isolated_cache, exist_ok=True)
        os.makedirs(isolated_media, exist_ok=True)
        
        # CRITICAL: Pre-configure Chrome profile to prevent dialog
        create_preconfigured_chrome_profile(profile_dir)
        
        # Find system Chrome executable
        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            r"C:\Users\{}\AppData\Local\Google\Chrome\Application\chrome.exe".format(os.getenv('USERNAME')),
        ]
        
        chrome_executable = None
        for path in chrome_paths:
            if os.path.exists(path):
                chrome_executable = path
                print(f"🔍 Found system Chrome at: {chrome_executable}")
                break
        
        if not chrome_executable:
            print("❌ Chrome executable not found!")
            return None
        
        # CRITICAL: Create Chrome options for complete isolation
        options = Options()
        
        # ESSENTIAL: Force complete isolation from system Chrome
        options.add_argument('--no-first-run')
        options.add_argument('--no-default-browser-check')
        options.add_argument('--disable-default-apps')
        options.add_argument('--disable-sync')
        options.add_argument('--disable-background-timer-throttling')
        options.add_argument('--disable-backgrounding-occluded-windows')
        options.add_argument('--disable-renderer-backgrounding')
        
        # CRITICAL: Use unique user data directory with absolute path
        options.add_argument(f'--user-data-dir={os.path.abspath(profile_dir)}')
        options.add_argument(f'--disk-cache-dir={os.path.abspath(isolated_cache)}')
        options.add_argument(f'--media-cache-dir={os.path.abspath(isolated_media)}')
        
        # CRITICAL: Prevent connection to existing Chrome
        options.add_argument('--remote-debugging-port=0')
        options.add_argument('--disable-web-security')
        options.add_argument('--allow-running-insecure-content')
        
        # Performance optimizations
        options.add_argument('--disable-plugins')
        options.add_argument('--disable-images')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        
        # CRITICAL: Force new instance and prevent profile selection
        options.add_argument('--new-window')
        options.add_argument('--no-default-browser-check')
        options.add_argument('--disable-default-apps')
        
        # CRITICAL: Additional isolation flags
        options.add_argument('--disable-features=VizDisplayCompositor')
        options.add_argument('--disable-ipc-flooding-protection')
        options.add_argument('--disable-features=TranslateUI')
        options.add_argument('--disable-features=BlinkGenPropertyTrees')
        
        # CRITICAL: Prevent Chrome from using system profile
        options.add_argument('--disable-background-networking')
        options.add_argument('--disable-background-timer-throttling')
        options.add_argument('--disable-backgrounding-occluded-windows')
        options.add_argument('--disable-renderer-backgrounding')
        options.add_argument('--disable-features=TranslateUI,BlinkGenPropertyTrees')
        
        # CRITICAL: Load extensions from profile directory
        extensions_dir = os.path.join(profile_dir, "chrome_portable", "extensions")
        if os.path.exists(extensions_dir):
            extension_dirs = [d for d in os.listdir(extensions_dir) 
                            if os.path.isdir(os.path.join(extensions_dir, d))]
            if extension_dirs:
                extensions_path = os.path.abspath(extensions_dir)
                options.add_argument(f'--load-extension={extensions_path}')
                print(f"🔧 Loading {len(extension_dirs)} extensions from: {extensions_path}")
                
                # Check for proxy plugins
                proxy_plugins = []
                for ext_dir in extension_dirs:
                    manifest_path = os.path.join(extensions_dir, ext_dir, "manifest.json")
                    if os.path.exists(manifest_path):
                        try:
                            with open(manifest_path, 'r') as f:
                                manifest = json.load(f)
                                if "proxy" in manifest.get("name", "").lower():
                                    proxy_plugins.append(manifest.get("name", "Unknown"))
                        except:
                            pass
                
                if proxy_plugins:
                    print(f"🔧 Found proxy plugins: {', '.join(proxy_plugins)}")
            else:
                options.add_argument('--disable-extensions')
        else:
            options.add_argument('--disable-extensions')
        
        print(f"🚀 Opening ISOLATED CHROME for {acc.label}")
        print(f"📁 Isolated Profile: {profile_dir}")
        print(f"📁 Isolated Cache: {isolated_cache}")
        print(f"📁 Isolated Media: {isolated_media}")
        print(f"🔧 Chrome Executable: {chrome_executable}")
        
        # CRITICAL: Use undetected-chromedriver with ISOLATION
        driver = uc.Chrome(
            options=options, 
            use_subprocess=True,
            version_main=None,
            headless=False,
            suppress_welcome=True,
            driver_executable_path=None,
            browser_executable_path=chrome_executable,
            user_data_dir=os.path.abspath(profile_dir)
        )
        
        # Execute script to remove webdriver property
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        # Load cookies if they exist
        cookie_path = acc.get_cookie_path()
        load_cookies_safely(driver, cookie_path, acc.label)
        
        # Log the browser opening
        log_browser_close(acc, "opened")
        
        return driver
    except Exception as e:
        print(f"❌ Error opening isolated Chrome for {acc.label}: {e}")
        return None

def open_browser_with_profile(acc):
    """Open browser with profile - Chrome only, no proxy"""
    print(f"🔧 Using simple isolated Chrome for {acc.label}")
    return create_simple_isolated_chrome(acc)

def get_account_status_and_avatar(acc, headless=True):
    """Get account status and avatar - Chrome only"""
    try:
        driver = get_global_driver_manager().get_driver(acc)
        if not driver:
            return False, None
        
        # Navigate to profile
        driver.get(f'https://x.com/{acc.username}')
        time.sleep(3)
        
        # Check if account exists
        try:
            # Look for profile elements
            profile_elements = driver.find_elements(By.CSS_SELECTOR, 'div[data-testid="UserName"]')
            if profile_elements:
                # Get avatar
                try:
                    avatar_img = driver.find_element(By.CSS_SELECTOR, 'img[data-testid="UserAvatar-Container-unknown"]')
                    avatar_url = avatar_img.get_attribute('src')
                except:
                    avatar_url = None
                
                return True, avatar_url
            else:
                return False, None
                
        except Exception as e:
            print(f"❌ Error checking account status: {e}")
            return False, None
            
    except Exception as e:
        print(f"❌ Error getting account status: {e}")
        return False, None

def log_browser_close(acc, action):
    """Log browser actions"""
    print(f"📝 Browser {action} for {acc.label}")

def scrape_tweet_content_and_comments(driver, tweet_url: str) -> tuple:
    """Scrape tweet content and comments - Chrome only"""
    try:
        driver.get(tweet_url)
        time.sleep(3)
        
        # Get tweet content
        tweet_content = ""
        try:
            tweet_text_element = driver.find_element(By.CSS_SELECTOR, 'div[data-testid="tweetText"]')
            tweet_content = tweet_text_element.text
            print(f"📝 Tweet content: {tweet_content[:100]}...")
        except Exception as e:
            print(f"⚠️ Could not get tweet content: {e}")
        
        # Get comments
        comments = []
        try:
            # Scroll to load more comments
            print("📜 Scrolling to load comments...")
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)
            
            # Try multiple selectors for comments/replies
            comment_selectors = [
                'article[data-testid="tweet"] div[data-testid="tweetText"]',
                'div[data-testid="tweetText"]',
                'div[role="article"] div[data-testid="tweetText"]',
                'div[data-testid="cellInnerDiv"] div[data-testid="tweetText"]'
            ]
            
            all_comment_elements = []
            for selector in comment_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        print(f"🔍 Found {len(elements)} elements with selector: {selector}")
                        all_comment_elements.extend(elements)
                except Exception as e:
                    print(f"⚠️ Selector {selector} failed: {e}")
                    continue
            
            # Filter out the original tweet and get unique comments
            seen_comments = set()
            for element in all_comment_elements:
                try:
                    comment_text = element.text.strip()
                    if (comment_text and 
                        comment_text != tweet_content and 
                        comment_text not in seen_comments and
                        len(comment_text) > 10):  # Filter out very short texts
                        
                        seen_comments.add(comment_text)
                        comments.append(comment_text)
                        print(f"💬 Found comment: {comment_text[:50]}...")
                        
                        # Limit to 25 comments
                        if len(comments) >= 25:
                            break
                            
                except Exception as e:
                    print(f"⚠️ Error processing comment element: {e}")
                    continue
                    
        except Exception as e:
            print(f"⚠️ Error getting comments: {e}")
        
        print(f"📊 Scraped {len(comments)} comments")
        return tweet_content, comments
        
    except Exception as e:
        print(f"❌ Error scraping tweet: {e}")
        return "", []

def handle_click_interception(driver, element):
    """Handle element click interception by removing blocking elements"""
    try:
        # Try to remove or hide the blocking scroll snap list
        blocking_elements = driver.find_elements(By.CSS_SELECTOR, 'div[data-testid="ScrollSnap-List"]')
        for blocker in blocking_elements:
            try:
                driver.execute_script("arguments[0].style.display = 'none';", blocker)
            except:
                pass
        
        # Remove the specific div that's intercepting (based on the error message)
        intercepting_divs = driver.find_elements(By.CSS_SELECTOR, 'div[dir="ltr"][class*="css-146c3p1"]')
        for div in intercepting_divs:
            try:
                driver.execute_script("arguments[0].style.display = 'none';", div)
            except:
                pass
        
        # Also try to remove any overlays
        overlays = driver.find_elements(By.CSS_SELECTOR, 'div[role="dialog"], div[class*="overlay"], div[class*="modal"]')
        for overlay in overlays:
            try:
                driver.execute_script("arguments[0].style.display = 'none';", overlay)
            except:
                pass
        
        # Remove any elements with specific classes that might be blocking
        blocking_classes = ['css-146c3p1', 'r-bcqeeo', 'r-qvutc0', 'r-37j5jr']
        for class_name in blocking_classes:
            elements = driver.find_elements(By.CSS_SELECTOR, f'div[class*="{class_name}"]')
            for element in elements:
                try:
                    driver.execute_script("arguments[0].style.display = 'none';", element)
                except:
                    pass
        
        time.sleep(1)
        
        # Scroll the element into view
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
        time.sleep(1)
        
        # Now try the click with multiple methods
        try:
            # Method 1: JavaScript click
            driver.execute_script("arguments[0].click();", element)
            return True
        except:
            try:
                # Method 2: Regular click
                element.click()
                return True
            except:
                try:
                    # Method 3: Action chains
                    from selenium.webdriver.common.action_chains import ActionChains
                    actions = ActionChains(driver)
                    actions.move_to_element(element).click().perform()
                    return True
                except:
                    return False
        
    except Exception as e:
        print(f"⚠️ Failed to handle click interception: {e}")
        return False 

def _clean_text_for_typing(text):
    """Clean text to remove problematic characters for ChromeDriver"""
    import re
    
    # Remove or replace problematic characters
    # Replace emojis with text equivalents or remove them
    emoji_replacements = {
        '💰': ' money',
        '🤔': ' hmm',
        '🗨️': ' chat',
        '💪': ' strong',
        '🚀': ' rocket',
        '🎯': ' target',
        '🤖': ' robot',
        '📝': ' note',
        '✅': ' check',
        '❌': ' x',
        '⚠️': ' warning',
        '🔍': ' search',
        '📊': ' chart',
        '💭': ' thought',
        '🎉': ' celebration',
        '💡': ' idea',
        '🔥': ' fire',
        '💎': ' diamond',
        '⚡': ' lightning',
        '🌟': ' star',
        '💯': ' 100',
        '🎵': ' music',
        '📱': ' phone',
        '💻': ' computer',
        '🌍': ' world',
        '🏆': ' trophy',
        '🎪': ' circus',
        '🎨': ' art',
        '🎭': ' theater',
        '🎪': ' circus',
        '🎯': ' target',
        '🎲': ' dice',
        '🎳': ' bowling',
        '🎮': ' game',
        '🎲': ' dice',
        '🎯': ' target',
        '🎪': ' circus',
        '🎨': ' art',
        '🎭': ' theater',
        '🎪': ' circus',
        '🎯': ' target',
        '🎲': ' dice',
        '🎳': ' bowling',
        '🎮': ' game'
    }
    
    cleaned_text = text
    for emoji, replacement in emoji_replacements.items():
        cleaned_text = cleaned_text.replace(emoji, replacement)
    
    # Remove any remaining non-BMP characters (characters outside Basic Multilingual Plane)
    cleaned_text = ''.join(char for char in cleaned_text if ord(char) < 0x10000)
    
    # Remove any other problematic characters
    cleaned_text = re.sub(r'[^\x00-\x7F\u00A0-\uFFFF]', '', cleaned_text)
    
    # Ensure we're within Twitter's 280 character limit
    cleaned_text = cleaned_text.strip()
    if len(cleaned_text) > 280:
        cleaned_text = cleaned_text[:280]
        print(f"⚠️ Text truncated to 280 characters for Twitter")
    
    return cleaned_text

def _type_like_human(driver, element, text):
    """Simulate human-like typing with random delays"""
    import random
    
    # Check character limit (Twitter allows 280 characters)
    if len(text) > 280:
        text = text[:280]
        print(f"⚠️ Text truncated to 280 characters for Twitter")
    
    # Click to focus the element
    element.click()
    time.sleep(random.uniform(0.5, 1.0))
    
    # Clear any existing text
    element.clear()
    time.sleep(random.uniform(0.3, 0.7))
    
    # Type character by character with human-like delays
    for char in text:
        # Random delay between characters (50-150ms)
        time.sleep(random.uniform(0.05, 0.15))
        
        # Type the character
        element.send_keys(char)
        
        # Longer pause after punctuation
        if char in '.!?':
            time.sleep(random.uniform(0.2, 0.4))
        elif char in ',;:':
            time.sleep(random.uniform(0.1, 0.3))
    
    # Final pause after typing
    time.sleep(random.uniform(0.5, 1.0)) 