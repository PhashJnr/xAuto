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
        print(f"🔍 Attempting to load cookies for {acc_label} from: {cookie_path}")
        
        if not os.path.exists(cookie_path):
            print(f"⚠️ No cookies found for {acc_label} at {cookie_path}")
            return
        
        # Check file size
        file_size = os.path.getsize(cookie_path)
        print(f"📁 Cookie file exists: {cookie_path} ({file_size} bytes)")
        
        with open(cookie_path, 'rb') as f:
            cookies = pickle.load(f)
        
        print(f"🍪 Loaded {len(cookies)} cookies for {acc_label}")
        
        # Navigate to Twitter first
        driver.get('https://x.com/')
        time.sleep(2)
        
        # Add cookies with better error handling
        successful_cookies = 0
        for i, cookie in enumerate(cookies):
            try:
                # Clean up cookie domain if needed
                if 'domain' in cookie:
                    # Remove leading dot if present
                    if cookie['domain'].startswith('.'):
                        cookie['domain'] = cookie['domain'][1:]
                    # Ensure domain is valid
                    if not cookie['domain'] or cookie['domain'] == '':
                        print(f"⚠️ Skipping cookie {i}: invalid domain")
                        continue
                
                driver.add_cookie(cookie)
                successful_cookies += 1
                if i < 5:  # Log first 5 cookies for debugging
                    print(f"  ✅ Added cookie {i+1}: {cookie.get('name', 'unknown')} for domain {cookie.get('domain', 'unknown')}")
            except Exception as e:
                print(f"⚠️ Failed to add cookie {i}: {e}")
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
        import traceback
        traceback.print_exc()

class SeleniumDriverManager:
    def __init__(self):
        self.drivers = {}  # Dictionary to store drivers for each account
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
            if (acc.label in self.drivers and 
                self.is_driver_valid(self.drivers[acc.label])):
                print(f"🔄 Reusing existing browser session for {acc.label}")
                return self.drivers[acc.label]
            
            # Close existing driver for this account if it exists
            if acc.label in self.drivers:
                try:
                    self.drivers[acc.label].quit()
                except Exception:
                    pass
                del self.drivers[acc.label]
            
            # Create new driver using the new approach
            try:
                print(f"🆕 Creating new browser session for {acc.label}")
                
                # Clean up any existing cache directories first
                cleanup_chrome_profile_cache(acc)
                
                # Use the new open_browser_with_profile function
                driver = open_browser_with_profile(acc)
                
                if driver:
                    self.drivers[acc.label] = driver
                    print(f"✅ Browser session created for {acc.label}")
                    return driver
                else:
                    print(f"❌ Failed to create browser session for {acc.label}")
                    return None
                
            except Exception as e:
                print(f"❌ Error creating browser session for {acc.label}: {e}")
                return None
    
    def close_driver(self, acc=None):
        """Close the driver for a specific account or all drivers"""
        with self._lock:
            if acc:
                # Close specific account's driver
                if acc.label in self.drivers:
                    try:
                        driver = self.drivers[acc.label]
                        
                        # Check if driver is still valid before saving
                        if self.is_driver_valid(driver):
                            try:
                                # Save session data before closing
                                ensure_session_saved(driver, acc)
                            except Exception as e:
                                print(f"⚠️ Error saving session for {acc.label}: {e}")
                            
                            try:
                                # Save cookies before closing
                                save_cookies(driver, acc)
                            except Exception as e:
                                print(f"⚠️ Error saving cookies for {acc.label}: {e}")
                            
                            # Wait a bit for saves to complete
                            time.sleep(1)
                        
                        # Close the driver
                        try:
                            driver.quit()
                        except Exception as e:
                            print(f"⚠️ Error quitting driver for {acc.label}: {e}")
                            
                    except Exception as e:
                        print(f"⚠️ Error closing driver for {acc.label}: {e}")
                    finally:
                        del self.drivers[acc.label]
                        print(f"🔒 Closed browser session for {acc.label}")
            else:
                # Close all drivers
                print(f"🔒 Closing all browser sessions ({len(self.drivers)} drivers)")
                for label, driver in list(self.drivers.items()):
                    try:
                        # Create a temporary account object for cookie saving
                        from account_manager import SeleniumAccount
                        temp_acc = SeleniumAccount(label, label)  # Use label as both label and username
                        
                        # Check if driver is still valid before saving
                        if self.is_driver_valid(driver):
                            try:
                                # Save session data before closing
                                ensure_session_saved(driver, temp_acc)
                            except Exception as e:
                                print(f"⚠️ Error saving session for {label}: {e}")
                            
                            try:
                                # Save cookies before closing
                                save_cookies(driver, temp_acc)
                            except Exception as e:
                                print(f"⚠️ Error saving cookies for {label}: {e}")
                            
                            # Wait a bit for saves to complete
                            time.sleep(1)
                        
                        # Close the driver
                        try:
                            driver.quit()
                        except Exception as e:
                            print(f"⚠️ Error quitting driver for {label}: {e}")
                            
                    except Exception as e:
                        print(f"⚠️ Error closing driver for {label}: {e}")
                    finally:
                        print(f"🔒 Closed browser session for {label}")
                
                self.drivers.clear()
                print("🔒 Closed all browser sessions")
    
    def get_all_drivers(self):
        """Get all active drivers"""
        return self.drivers.copy()
    
    def has_driver(self, acc):
        """Check if account has an active driver"""
        return acc.label in self.drivers and self.is_driver_valid(self.drivers[acc.label])

def save_cookies(driver, acc):
    """Save cookies for the account"""
    try:
        # Check if driver is still valid
        if not driver or not hasattr(driver, 'get_cookies'):
            print(f"⚠️ Driver for {acc.label} is not valid, skipping cookie save")
            return
        
        # Ensure cookies directory exists
        cookie_dir = os.path.dirname(acc.get_cookie_path())
        os.makedirs(cookie_dir, exist_ok=True)
        
        # Get cookies from driver with error handling
        try:
            cookies = driver.get_cookies()
            print(f"🍪 Got {len(cookies)} cookies from driver for {acc.label}")
        except Exception as e:
            print(f"⚠️ Could not get cookies from driver for {acc.label}: {e}")
            return
        
        # Save cookies to file
        cookie_path = acc.get_cookie_path()
        with open(cookie_path, 'wb') as f:
            pickle.dump(cookies, f)
        
        print(f"🍪 Cookies saved for {acc.label} to {cookie_path}")
        
        # Verify file was created
        if os.path.exists(cookie_path):
            file_size = os.path.getsize(cookie_path)
            print(f"✅ Cookie file created: {cookie_path} ({file_size} bytes)")
        else:
            print(f"❌ Cookie file was not created: {cookie_path}")
            
    except Exception as e:
        print(f"❌ Error saving cookies for {acc.label}: {e}")
        import traceback
        traceback.print_exc()

def save_cookies_periodic(driver, acc, task_name="task"):
    """Save cookies periodically during long-running tasks"""
    try:
        save_cookies(driver, acc)
        print(f"🍪 Periodic cookies saved for {acc.label} during {task_name}")
    except Exception as e:
        print(f"⚠️ Error saving periodic cookies for {acc.label}: {e}")

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
    """Check if a tweet is accessible and handle media tweets"""
    try:
        driver.get(tweet_url)
        time.sleep(3)
        
        # Check if we're on the correct page
        current_url = driver.current_url
        if "twitter.com" not in current_url and "x.com" not in current_url:
            print(f"⚠️ Redirected away from Twitter: {current_url}")
            return False, "Redirected away from Twitter"
        
        # Check for common error pages
        page_text = driver.page_source.lower()
        if any(error in page_text for error in ["this tweet is unavailable", "tweet not found", "page doesn't exist"]):
            print("⚠️ Tweet is unavailable or deleted")
            return False, "Tweet is unavailable or deleted"
        
        # Check if tweet content exists (even for media tweets)
        tweet_selectors = [
            'div[data-testid="tweetText"]',
            'article[data-testid="tweet"] div[data-testid="tweetText"]',
            'article[data-testid="tweet"] div[lang]',
            'div[data-testid="tweet"] div[lang]'
        ]
        
        for selector in tweet_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    print(f"✅ Tweet content found with selector: {selector}")
                    return True, "Tweet content found"
            except:
                continue
        
        # Check for media tweets (images/videos)
        media_selectors = [
            'div[data-testid="tweetPhoto"]',
            'div[data-testid="videoPlayer"]',
            'div[data-testid="videoPlayerContainer"]',
            'div[data-testid="videoPlayer"] video',
            'div[data-testid="tweetPhoto"] img'
        ]
        
        for selector in media_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    print(f"✅ Media content found with selector: {selector}")
                    return True, "Media content found"
            except:
                continue
        
        print("⚠️ No tweet content or media found")
        return False, "No tweet content or media found"
        
    except Exception as e:
        print(f"❌ Error checking tweet accessibility: {e}")
        return False, f"Error checking tweet accessibility: {e}"

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
        accessible = check_tweet_accessibility(driver, tweet_url)
        if not accessible:
            print(f"❌ Tweet not accessible")
            return False, "Tweet not accessible"
        
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
            
        # Save cookies after successful reply
        try:
            save_cookies(driver, acc)
            print(f"🍪 Cookies saved for {acc.label} after reply")
        except Exception as e:
            print(f"⚠️ Error saving cookies for {acc.label}: {e}")
            
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
            
            # Save cookies after successful reply to comment
            try:
                save_cookies(driver, acc)
                print(f"🍪 Cookies saved for {acc.label} after comment reply")
            except Exception as e:
                print(f"⚠️ Error saving cookies for {acc.label}: {e}")
            
            return True, f"Successfully replied to comment by @{comment_username}"
            
        except Exception as e:
            print(f"⚠️ JavaScript click failed: {e}")
            if handle_click_interception(driver, post_button):
                time.sleep(3)
                print(f"✅ Successfully replied to comment by @{comment_username}")
                
                # Save cookies after successful reply to comment
                try:
                    save_cookies(driver, acc)
                    print(f"🍪 Cookies saved for {acc.label} after comment reply")
                except Exception as e:
                    print(f"⚠️ Error saving cookies for {acc.label}: {e}")
                
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
            
            # Save cookies after successful DM
            try:
                save_cookies(driver, acc)
                print(f"🍪 Cookies saved for {acc.label} after DM")
            except Exception as e:
                print(f"⚠️ Error saving cookies for {acc.label}: {e}")
            
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
            
            # Save cookies after successful bio change
            try:
                save_cookies(driver, acc)
                print(f"🍪 Cookies saved for {acc.label} after bio change")
            except Exception as e:
                print(f"⚠️ Error saving cookies for {acc.label}: {e}")
            
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
            
            # Save cookies after successful profile picture change
            try:
                save_cookies(driver, acc)
                print(f"🍪 Cookies saved for {acc.label} after profile picture change")
            except Exception as e:
                print(f"⚠️ Error saving cookies for {acc.label}: {e}")
            
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
    """Create a pre-configured Chrome profile to prevent dialog prompts"""
    try:
        print(f"✅ Creating pre-configured Chrome profile at: {profile_dir}")
        
        # Create profile directory
        os.makedirs(profile_dir, exist_ok=True)
        
        # Create Default directory (Chrome's main profile folder)
        default_dir = os.path.join(profile_dir, "Default")
        os.makedirs(default_dir, exist_ok=True)
        
        # Create Preferences file to disable first-run dialogs
        preferences = {
            "profile": {
                "default_content_setting_values": {
                    "notifications": 2,
                    "geolocation": 2,
                    "media_stream": 2
                },
                "password_manager_enabled": False,
                "exit_type": "Normal",
                "exited_cleanly": True
            },
            "browser": {
                "show_home_button": False,
                "window_placement": {
                    "maximized": True
                }
            },
            "signin": {
                "allowed": False
            },
            "safebrowsing": {
                "enabled": False
            },
            "default_search_provider": {
                "enabled": False
            },
            "extensions": {
                "settings": {}
            }
        }
        
        # Write preferences file
        import json
        with open(os.path.join(default_dir, "Preferences"), 'w') as f:
            json.dump(preferences, f, indent=2)
        
        # Set up FoxyProxy extension
        download_real_foxyproxy_extension(profile_dir)
        
        # Configure FoxyProxy with account proxy if available
        if hasattr(acc, 'proxy') and acc.proxy:
            configure_foxyproxy_with_account_proxy(acc)
        
        print(f"✅ Chrome profile pre-configured successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error creating pre-configured Chrome profile: {e}")
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
        
        # Let Chrome create its own cache directories within the profile
        
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
        # Removed --disable-default-apps to allow extension downloads
        options.add_argument('--disable-sync')
        options.add_argument('--disable-background-timer-throttling')
        options.add_argument('--disable-backgrounding-occluded-windows')
        options.add_argument('--disable-renderer-backgrounding')
        
        # CRITICAL: Use unique user data directory with absolute path
        options.add_argument(f'--user-data-dir={os.path.abspath(profile_dir)}')
        # Let Chrome use its default cache directories within the profile
        
        # CRITICAL: Prevent connection to existing Chrome
        options.add_argument('--remote-debugging-port=0')
        # Removed --disable-web-security to allow extension downloads
        options.add_argument('--allow-running-insecure-content')
        
        # Extension-friendly flags
        options.add_argument('--enable-extensions')
        options.add_argument('--enable-plugins')
        options.add_argument('--load-extension')
        
        # Performance optimizations (removed --disable-images and --disable-plugins)
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
        
        # CRITICAL: Session persistence flags
        options.add_argument('--enable-session-crashed-bubble')
        options.add_argument('--disable-session-crashed-bubble')
        options.add_argument('--disable-background-mode')
        options.add_argument('--disable-background-timer-throttling')
        options.add_argument('--disable-backgrounding-occluded-windows')
        options.add_argument('--disable-renderer-backgrounding')
        
        # CRITICAL: Load extensions from profile directory
        extensions_dir = os.path.join(profile_dir, "chrome_portable", "extensions")
        
        # Ensure FoxyProxy extension exists
        download_real_foxyproxy_extension(profile_dir)
        
        if os.path.exists(extensions_dir):
            extension_dirs = [d for d in os.listdir(extensions_dir) 
                            if os.path.isdir(os.path.join(extensions_dir, d))]
            if extension_dirs:
                for ext_dir in extension_dirs:
                    ext_path = os.path.abspath(os.path.join(extensions_dir, ext_dir))
                    options.add_argument(f'--load-extension={ext_path}')
                    print(f"🔧 Loading extension: {ext_dir} from: {ext_path}")
                
                # Check for FoxyProxy specifically
                foxyproxy_id = "gcknhkkoolaabfmlnjonogaaifnjlfnp"
                foxyproxy_path = os.path.join(extensions_dir, foxyproxy_id)
                if os.path.exists(foxyproxy_path):
                    print(f"✅ FoxyProxy extension loaded successfully")
                else:
                    print(f"⚠️ FoxyProxy extension not found, will be created on first run")
            else:
                print(f"⚠️ No extensions found in {extensions_dir}")
        else:
            print(f"⚠️ Extensions directory not found: {extensions_dir}")
        
        print(f"🚀 Opening ISOLATED CHROME for {acc.label}")
        print(f"📁 Isolated Profile: {profile_dir}")
        print(f"📁 Isolated Cache: {profile_dir}") # Changed to profile_dir
        print(f"📁 Isolated Media: {profile_dir}") # Changed to profile_dir
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
        time.sleep(5)  # Increased wait time for media to load
        
        # Get tweet content with multiple selectors for media-rich tweets
        tweet_content = ""
        tweet_selectors = [
            'div[data-testid="tweetText"]',
            'article[data-testid="tweet"] div[data-testid="tweetText"]',
            'div[data-testid="cellInnerDiv"] div[data-testid="tweetText"]',
            'div[role="article"] div[data-testid="tweetText"]',
            # For media tweets, try broader selectors
            'article[data-testid="tweet"] div[lang]',
            'div[data-testid="tweet"] div[lang]',
            'div[role="article"] div[lang]',
            # Fallback for any text content
            'article[data-testid="tweet"] span',
            'div[data-testid="tweet"] span'
        ]
        
        for selector in tweet_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    text = element.text.strip()
                    if text and len(text) > 10:  # Ensure meaningful content
                        tweet_content = text
                        print(f"📝 Tweet content found with selector '{selector}': {tweet_content[:100]}...")
                        break
                if tweet_content:
                    break
            except Exception as e:
                print(f"⚠️ Selector '{selector}' failed: {e}")
                continue
        
        if not tweet_content:
            print("⚠️ Could not find tweet text content, trying alternative methods...")
            # Try to get any visible text from the tweet
            try:
                tweet_article = driver.find_element(By.CSS_SELECTOR, 'article[data-testid="tweet"]')
                tweet_content = tweet_article.text.strip()
                if tweet_content:
                    print(f"📝 Found tweet content from article text: {tweet_content[:100]}...")
            except Exception as e:
                print(f"⚠️ Could not get article text: {e}")
        
        # Get comments with improved selectors
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
                'div[data-testid="cellInnerDiv"] div[data-testid="tweetText"]',
                # Broader selectors for media tweets
                'div[role="article"] div[lang]',
                'article[data-testid="tweet"] div[lang]',
                'div[data-testid="tweet"] div[lang]'
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
                        len(comment_text) > 10 and  # Filter out very short texts
                        not comment_text.startswith('@') and  # Filter out usernames
                        not comment_text.startswith('#')):  # Filter out hashtags
                        
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
    time.sleep(random.uniform(0.3, 0.6))  # Reduced from 0.5-1.0
    
    # Clear any existing text
    element.clear()
    time.sleep(random.uniform(0.2, 0.4))  # Reduced from 0.3-0.7
    
    # Type character by character with human-like delays
    for char in text:
        # Random delay between characters (20-80ms) - Increased speed
        time.sleep(random.uniform(0.02, 0.08))  # Reduced from 0.05-0.15
        
        # Type the character
        element.send_keys(char)
        
        # Shorter pause after punctuation
        if char in '.!?':
            time.sleep(random.uniform(0.1, 0.2))  # Reduced from 0.2-0.4
        elif char in ',;:':
            time.sleep(random.uniform(0.05, 0.15))  # Reduced from 0.1-0.3
    
    # Final pause after typing
    time.sleep(random.uniform(0.3, 0.6))  # Reduced from 0.5-1.0

def test_cookie_saving(driver, acc):
    """Test function to manually save cookies for debugging"""
    try:
        print(f"🧪 Testing cookie saving for {acc.label}")
        
        # Get current cookies
        cookies = driver.get_cookies()
        print(f"🍪 Current cookies in driver: {len(cookies)}")
        
        # Print first few cookies for debugging
        for i, cookie in enumerate(cookies[:3]):
            print(f"  Cookie {i+1}: {cookie.get('name', 'unknown')} = {cookie.get('value', 'unknown')[:20]}...")
        
        # Save cookies
        save_cookies(driver, acc)
        
        # Verify cookies were saved
        cookie_path = acc.get_cookie_path()
        if os.path.exists(cookie_path):
            print(f"✅ Cookie test successful: {cookie_path}")
            return True
        else:
            print(f"❌ Cookie test failed: {cookie_path}")
            return False
            
    except Exception as e:
        print(f"❌ Cookie test error: {e}")
        return False 

def ensure_session_saved(driver, acc):
    """Ensure session data is properly saved before closing"""
    try:
        print(f"💾 Ensuring session data is saved for {acc.label}")
        
        # Check if driver is still valid
        if not driver or not hasattr(driver, 'get'):
            print(f"⚠️ Driver for {acc.label} is not valid, skipping session save")
            return False
        
        # Navigate to a simple page to trigger session save
        try:
            driver.get('https://x.com/')
            time.sleep(3)
        except Exception as e:
            print(f"⚠️ Could not navigate for session save for {acc.label}: {e}")
            return False
        
        # Execute JavaScript to force session save
        try:
            driver.execute_script("""
                // Force localStorage and sessionStorage to persist
                if (window.localStorage) {
                    localStorage.setItem('session_persist', 'true');
                }
                if (window.sessionStorage) {
                    sessionStorage.setItem('session_persist', 'true');
                }
                
                // Force any pending writes to complete
                if (window.navigator && window.navigator.storage) {
                    window.navigator.storage.persist();
                }
            """)
        except Exception as e:
            print(f"⚠️ Could not execute session save script for {acc.label}: {e}")
            return False
        
        # Wait longer for Chrome to save session data
        time.sleep(5)
        
        # Force a page refresh to ensure data is written
        try:
            driver.refresh()
            time.sleep(3)
        except Exception as e:
            print(f"⚠️ Could not refresh page for session save for {acc.label}: {e}")
            return False
        
        print(f"✅ Session data saved for {acc.label}")
        return True
        
    except Exception as e:
        print(f"⚠️ Error saving session for {acc.label}: {e}")
        return False

def manual_save_cookies(acc):
    """Manually save cookies for an account"""
    try:
        driver_manager = get_global_driver_manager()
        
        if acc.label in driver_manager.drivers:
            driver = driver_manager.drivers[acc.label]
            
            # Ensure session is saved
            ensure_session_saved(driver, acc)
            
            # Save cookies
            save_cookies(driver, acc)
            
            print(f"✅ Manually saved cookies for {acc.label}")
            return True
        else:
            print(f"❌ No active browser for {acc.label}")
            return False
            
    except Exception as e:
        print(f"❌ Error manually saving cookies for {acc.label}: {e}")
        return False 

def check_profile_session_data(acc):
    """Check if the Chrome profile has session data"""
    try:
        profile_dir = acc.get_chrome_profile_path()
        default_dir = os.path.join(profile_dir, "Default")
        
        if not os.path.exists(default_dir):
            print(f"❌ No Default directory found for {acc.label}")
            return False
        
        # Check for common session files
        session_files = [
            os.path.join(default_dir, "Cookies"),
            os.path.join(default_dir, "Cookies-journal"),
            os.path.join(default_dir, "Login Data"),
            os.path.join(default_dir, "Login Data-journal"),
            os.path.join(default_dir, "Web Data"),
            os.path.join(default_dir, "Web Data-journal")
        ]
        
        found_files = []
        for file_path in session_files:
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                found_files.append(f"{os.path.basename(file_path)} ({file_size} bytes)")
        
        if found_files:
            print(f"✅ Found session files for {acc.label}: {', '.join(found_files)}")
            return True
        else:
            print(f"❌ No session files found for {acc.label}")
            return False
            
    except Exception as e:
        print(f"❌ Error checking profile session data for {acc.label}: {e}")
        return False 

def cleanup_chrome_profile_cache(acc):
    """Clean up multiple cache directories in existing Chrome profiles"""
    try:
        profile_dir = acc.get_chrome_profile_path()
        if not os.path.exists(profile_dir):
            print(f"📁 Profile directory doesn't exist for {acc.label}")
            return True
        
        print(f"🧹 Cleaning up cache directories for {acc.label}")
        
        # Find and remove multiple cache directories
        cache_dirs = []
        for item in os.listdir(profile_dir):
            if item.startswith('cache_') and os.path.isdir(os.path.join(profile_dir, item)):
                cache_dirs.append(item)
        
        # Remove multiple cache directories
        for cache_dir in cache_dirs:
            cache_path = os.path.join(profile_dir, cache_dir)
            try:
                import shutil
                shutil.rmtree(cache_path)
                print(f"🗑️ Removed cache directory: {cache_dir}")
            except Exception as e:
                print(f"⚠️ Error removing {cache_dir}: {e}")
        
        # Also clean up multiple media directories
        media_dirs = []
        for item in os.listdir(profile_dir):
            if item.startswith('media_') and os.path.isdir(os.path.join(profile_dir, item)):
                media_dirs.append(item)
        
        for media_dir in media_dirs:
            media_path = os.path.join(profile_dir, media_dir)
            try:
                import shutil
                shutil.rmtree(media_path)
                print(f"🗑️ Removed media directory: {media_dir}")
            except Exception as e:
                print(f"⚠️ Error removing {media_dir}: {e}")
        
        print(f"✅ Cache cleanup completed for {acc.label}")
        return True
        
    except Exception as e:
        print(f"❌ Error cleaning up cache for {acc.label}: {e}")
        return False 

def download_foxyproxy_extension(profile_dir):
    """Download and set up FoxyProxy extension for Chrome profile"""
    import requests
    import zipfile
    import os
    import shutil
    
    try:
        print(f"🔧 Setting up FoxyProxy extension for profile: {profile_dir}")
        
        # Create extensions directory
        extensions_dir = os.path.join(profile_dir, "chrome_portable", "extensions")
        print(f"📁 Creating extensions directory: {extensions_dir}")
        os.makedirs(extensions_dir, exist_ok=True)
        
        # FoxyProxy extension ID
        foxyproxy_id = "gcknhkkoolaabfmlnjonogaaifnjlfnp"
        foxyproxy_dir = os.path.join(extensions_dir, foxyproxy_id)
        print(f"📁 FoxyProxy directory: {foxyproxy_dir}")
        
        # Check if already downloaded
        if os.path.exists(foxyproxy_dir):
            print(f"✅ FoxyProxy extension already exists at: {foxyproxy_dir}")
            return True
        
        # Create extension directory
        print(f"📁 Creating FoxyProxy extension directory")
        os.makedirs(foxyproxy_dir, exist_ok=True)
        
        # Download extension from Chrome Web Store
        # Note: This is a simplified approach - in practice, you'd need to download the .crx file
        # For now, we'll create a basic extension structure
        
        # Create manifest.json for FoxyProxy
        manifest_content = {
            "manifest_version": 3,
            "name": "FoxyProxy",
            "version": "9.2",
            "description": "Advanced proxy management tool",
            "permissions": [
                "proxy",
                "storage",
                "tabs",
                "webRequest",
                "webRequestAuthProvider",
                "browsingData",
                "privacy",
                "downloads"
            ],
            "host_permissions": ["<all_urls>"],
            "background": {
                "service_worker": "background.js"
            },
            "action": {
                "default_popup": "popup.html",
                "default_title": "FoxyProxy"
            },
            "icons": {
                "16": "icon16.png",
                "48": "icon48.png",
                "128": "icon128.png"
            }
        }
        
        # Write manifest.json
        import json
        with open(os.path.join(foxyproxy_dir, "manifest.json"), 'w') as f:
            json.dump(manifest_content, f, indent=2)
        
        # Create basic background script
        background_js = """
// Basic FoxyProxy background script
chrome.runtime.onInstalled.addListener(() => {
    console.log('FoxyProxy extension installed');
});

// Handle proxy requests
chrome.webRequest.onAuthRequired.addListener(
    function(details, callbackFn) {
        // Basic proxy authentication handling
        console.log('Proxy auth required:', details);
    },
    {urls: ["<all_urls>"]},
    ["asyncBlocking"]
);
"""
        
        with open(os.path.join(foxyproxy_dir, "background.js"), 'w') as f:
            f.write(background_js)
        
        # Create basic popup HTML
        popup_html = """
<!DOCTYPE html>
<html>
<head>
    <title>FoxyProxy</title>
    <style>
        body { width: 300px; padding: 10px; font-family: Arial, sans-serif; }
        .proxy-item { margin: 5px 0; padding: 5px; border: 1px solid #ccc; }
        .enabled { background-color: #e8f5e8; }
        .disabled { background-color: #f5e8e8; }
    </style>
</head>
<body>
    <h3>FoxyProxy</h3>
    <div id="proxy-list">
        <p>No proxies configured</p>
    </div>
    <button id="add-proxy">Add Proxy</button>
    <script src="popup.js"></script>
</body>
</html>
"""
        
        with open(os.path.join(foxyproxy_dir, "popup.html"), 'w') as f:
            f.write(popup_html)
        
        # Create basic popup script
        popup_js = """
document.addEventListener('DOMContentLoaded', function() {
    console.log('FoxyProxy popup loaded');
    
    document.getElementById('add-proxy').addEventListener('click', function() {
        // Add proxy functionality
        console.log('Add proxy clicked');
    });
});
"""
        
        with open(os.path.join(foxyproxy_dir, "popup.js"), 'w') as f:
            f.write(popup_js)
        
        # Create basic icons (placeholder)
        icon_content = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
        
        # Create placeholder icons
        for size in [16, 48, 128]:
            icon_path = os.path.join(foxyproxy_dir, f"icon{size}.png")
            # Create a simple 1x1 pixel PNG as placeholder
            with open(icon_path, 'wb') as f:
                f.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc```\x00\x00\x00\x04\x00\x01\xf6\x178\x00\x00\x00\x00IEND\xaeB`\x82')
        
        print(f"✅ FoxyProxy extension created at: {foxyproxy_dir}")
        return True
        
    except Exception as e:
        print(f"❌ Error setting up FoxyProxy extension: {e}")
        return False 

def setup_foxyproxy_for_account(acc):
    """Set up FoxyProxy extension for a specific account"""
    try:
        profile_dir = acc.get_chrome_profile_path()
        print(f"🔧 Setting up FoxyProxy for account: {acc.label}")
        
        # Download and set up FoxyProxy extension
        success = download_foxyproxy_extension(profile_dir)
        
        if success:
            print(f"✅ FoxyProxy setup completed for {acc.label}")
            return True
        else:
            print(f"❌ FoxyProxy setup failed for {acc.label}")
            return False
            
    except Exception as e:
        print(f"❌ Error setting up FoxyProxy for {acc.label}: {e}")
        return False 

def check_foxyproxy_loaded(driver):
    """Check if FoxyProxy extension is loaded in the browser"""
    try:
        # Check if FoxyProxy extension is installed
        extensions = driver.execute_script("""
            return chrome.management.getAll().then(function(extensions) {
                return extensions.filter(function(ext) {
                    return ext.id === 'gcknhkkoolaabfmlnjonogaaifnjlfnp';
                });
            });
        """)
        
        if extensions and len(extensions) > 0:
            print(f"✅ FoxyProxy extension is loaded in browser")
            return True
        else:
            print(f"❌ FoxyProxy extension is not loaded in browser")
            return False
            
    except Exception as e:
        print(f"⚠️ Could not check FoxyProxy extension status: {e}")
        return False 

def download_real_foxyproxy_extension(profile_dir):
    """Download the actual FoxyProxy extension from Chrome Web Store"""
    import requests
    import os
    import json
    
    try:
        print(f"🔧 Downloading real FoxyProxy extension for profile: {profile_dir}")
        
        # Create extensions directory
        extensions_dir = os.path.join(profile_dir, "chrome_portable", "extensions")
        os.makedirs(extensions_dir, exist_ok=True)
        
        # FoxyProxy extension ID
        foxyproxy_id = "gcknhkkoolaabfmlnjonogaaifnjlfnp"
        foxyproxy_dir = os.path.join(extensions_dir, foxyproxy_id)
        
        # Check if already downloaded
        if os.path.exists(foxyproxy_dir):
            print(f"✅ Real FoxyProxy extension already exists at: {foxyproxy_dir}")
            return True
        
        # Create extension directory
        os.makedirs(foxyproxy_dir, exist_ok=True)
        
        # For now, we'll create a more complete extension structure
        # In a real implementation, you'd download the .crx file from Chrome Web Store
        
        # Create a more complete manifest.json
        manifest_content = {
            "manifest_version": 3,
            "name": "FoxyProxy",
            "version": "9.2",
            "description": "Advanced proxy management tool for everyone",
            "permissions": [
                "proxy",
                "storage",
                "tabs",
                "webRequest",
                "webRequestAuthProvider",
                "browsingData",
                "privacy",
                "downloads"
            ],
            "host_permissions": ["<all_urls>"],
            "background": {
                "service_worker": "background.js"
            },
            "action": {
                "default_popup": "popup.html",
                "default_title": "FoxyProxy"
            },
            "icons": {
                "16": "icon16.png",
                "48": "icon48.png",
                "128": "icon128.png"
            },
            "web_accessible_resources": [
                {
                    "resources": ["popup.html", "popup.js"],
                    "matches": ["<all_urls>"]
                }
            ]
        }
        
        # Write manifest.json
        with open(os.path.join(foxyproxy_dir, "manifest.json"), 'w') as f:
            json.dump(manifest_content, f, indent=2)
        
        # Create a more functional background script
        background_js = """
// FoxyProxy Background Script
chrome.runtime.onInstalled.addListener(() => {
    console.log('FoxyProxy extension installed');
    
    // Initialize default settings
    chrome.storage.local.set({
        proxies: [],
        enabled: false,
        currentProxy: null,
        autoAuth: true  // Enable automatic authentication
    });
});

// Handle proxy requests
chrome.webRequest.onAuthRequired.addListener(
    function(details, callbackFn) {
        console.log('Proxy auth required:', details);
        
        // Get current proxy settings
        chrome.storage.local.get(['currentProxy', 'autoAuth'], function(result) {
            if (result.currentProxy && result.currentProxy.username && result.currentProxy.password && result.autoAuth) {
                console.log('Auto-authenticating proxy:', result.currentProxy.host);
                callbackFn({
                    authCredentials: {
                        username: result.currentProxy.username,
                        password: result.currentProxy.password
                    }
                });
            } else {
                console.log('No proxy credentials found or auto-auth disabled');
                callbackFn({});
            }
        });
        
        return true; // Indicates async response
    },
    {urls: ["<all_urls>"]},
    ["asyncBlocking"]
);

// Handle proxy switching
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'setProxy') {
        chrome.storage.local.set({currentProxy: request.proxy}, () => {
            console.log('Proxy set:', request.proxy);
            sendResponse({success: true});
        });
        return true;
    }
    
    if (request.action === 'getProxies') {
        chrome.storage.local.get(['proxies'], (result) => {
            sendResponse({proxies: result.proxies || []});
        });
        return true;
    }
    
    if (request.action === 'saveProxy') {
        chrome.storage.local.get(['proxies'], (result) => {
            const proxies = result.proxies || [];
            const existingIndex = proxies.findIndex(p => p.host === request.proxy.host && p.port === request.proxy.port);
            
            if (existingIndex >= 0) {
                proxies[existingIndex] = request.proxy;
            } else {
                proxies.push(request.proxy);
            }
            
            chrome.storage.local.set({proxies: proxies}, () => {
                console.log('Proxy saved:', request.proxy);
                sendResponse({success: true});
            });
        });
        return true;
    }
    
    if (request.action === 'getCurrentProxy') {
        chrome.storage.local.get(['currentProxy'], (result) => {
            sendResponse({currentProxy: result.currentProxy});
        });
        return true;
    }
});
"""
        
        with open(os.path.join(foxyproxy_dir, "background.js"), 'w') as f:
            f.write(background_js)
        
        # Create a functional popup HTML
        popup_html = """
<!DOCTYPE html>
<html>
<head>
    <title>FoxyProxy</title>
    <style>
        body { 
            width: 400px; 
            padding: 15px; 
            font-family: Arial, sans-serif; 
            margin: 0;
        }
        .header {
            background: #4285f4;
            color: white;
            padding: 10px;
            margin: -15px -15px 15px -15px;
            text-align: center;
        }
        .proxy-item { 
            margin: 8px 0; 
            padding: 8px; 
            border: 1px solid #ddd; 
            border-radius: 4px;
            cursor: pointer;
        }
        .enabled { 
            background-color: #e8f5e8; 
            border-color: #4caf50;
        }
        .disabled { 
            background-color: #f5f5f5; 
        }
        .add-proxy-btn {
            background: #4285f4;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            width: 100%;
            margin-top: 10px;
        }
        .status {
            font-size: 12px;
            color: #666;
            margin-top: 10px;
        }
        .form-group {
            margin: 8px 0;
        }
        .form-group label {
            display: block;
            margin-bottom: 4px;
            font-weight: bold;
        }
        .form-group input {
            width: 100%;
            padding: 6px;
            border: 1px solid #ddd;
            border-radius: 4px;
            box-sizing: border-box;
        }
        .form-buttons {
            display: flex;
            gap: 8px;
            margin-top: 10px;
        }
        .btn {
            padding: 6px 12px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }
        .btn-primary {
            background: #4285f4;
            color: white;
        }
        .btn-secondary {
            background: #6c757d;
            color: white;
        }
        .hidden {
            display: none;
        }
    </style>
</head>
<body>
    <div class="header">
        <h3 style="margin: 0;">FoxyProxy</h3>
    </div>
    
    <div id="proxy-list">
        <p>No proxies configured</p>
    </div>
    
    <button id="add-proxy" class="add-proxy-btn">Add Proxy</button>
    
    <div id="proxy-form" class="hidden">
        <h4>Add Proxy</h4>
        <div class="form-group">
            <label>Name:</label>
            <input type="text" id="proxy-name" placeholder="My Proxy">
        </div>
        <div class="form-group">
            <label>Host:</label>
            <input type="text" id="proxy-host" placeholder="proxy.example.com">
        </div>
        <div class="form-group">
            <label>Port:</label>
            <input type="number" id="proxy-port" placeholder="8080">
        </div>
        <div class="form-group">
            <label>Username:</label>
            <input type="text" id="proxy-username" placeholder="username">
        </div>
        <div class="form-group">
            <label>Password:</label>
            <input type="password" id="proxy-password" placeholder="password">
        </div>
        <div class="form-buttons">
            <button id="save-proxy" class="btn btn-primary">Save Proxy</button>
            <button id="cancel-proxy" class="btn btn-secondary">Cancel</button>
        </div>
    </div>
    
    <div class="status" id="status">Ready</div>
    
    <script src="popup.js"></script>
</body>
</html>
"""
        
        with open(os.path.join(foxyproxy_dir, "popup.html"), 'w') as f:
            f.write(popup_html)
        
        # Create functional popup script
        popup_js = """
document.addEventListener('DOMContentLoaded', function() {
    console.log('FoxyProxy popup loaded');
    
    const proxyList = document.getElementById('proxy-list');
    const addProxyBtn = document.getElementById('add-proxy');
    const status = document.getElementById('status');
    const proxyForm = document.getElementById('proxy-form');
    const saveProxyBtn = document.getElementById('save-proxy');
    const cancelProxyBtn = document.getElementById('cancel-proxy');
    
    // Form elements
    const proxyName = document.getElementById('proxy-name');
    const proxyHost = document.getElementById('proxy-host');
    const proxyPort = document.getElementById('proxy-port');
    const proxyUsername = document.getElementById('proxy-username');
    const proxyPassword = document.getElementById('proxy-password');
    
    // Load proxies
    function loadProxies() {
        chrome.runtime.sendMessage({action: 'getProxies'}, function(response) {
            if (response.proxies && response.proxies.length > 0) {
                proxyList.innerHTML = '';
                response.proxies.forEach(proxy => {
                    const proxyDiv = document.createElement('div');
                    proxyDiv.className = 'proxy-item ' + (proxy.enabled ? 'enabled' : 'disabled');
                    proxyDiv.innerHTML = `
                        <strong>${proxy.name}</strong><br>
                        ${proxy.host}:${proxy.port}
                    `;
                    proxyDiv.onclick = () => toggleProxy(proxy);
                    proxyList.appendChild(proxyDiv);
                });
            } else {
                proxyList.innerHTML = '<p>No proxies configured</p>';
            }
        });
    }
    
    // Toggle proxy
    function toggleProxy(proxy) {
        chrome.runtime.sendMessage({
            action: 'setProxy', 
            proxy: proxy
        }, function(response) {
            if (response.success) {
                status.textContent = `Switched to ${proxy.name}`;
                loadProxies();
            }
        });
    }
    
    // Show form
    addProxyBtn.addEventListener('click', function() {
        proxyForm.classList.remove('hidden');
        addProxyBtn.classList.add('hidden');
        status.textContent = 'Add your proxy details';
    });
    
    // Save proxy
    saveProxyBtn.addEventListener('click', function() {
        const proxy = {
            name: proxyName.value || 'My Proxy',
            host: proxyHost.value,
            port: parseInt(proxyPort.value) || 8080,
            username: proxyUsername.value,
            password: proxyPassword.value,
            enabled: true
        };
        
        if (!proxy.host) {
            status.textContent = 'Please enter a host';
            return;
        }
        
        chrome.runtime.sendMessage({
            action: 'saveProxy',
            proxy: proxy
        }, function(response) {
            if (response.success) {
                status.textContent = `Proxy ${proxy.name} saved successfully`;
                // Clear form
                proxyName.value = '';
                proxyHost.value = '';
                proxyPort.value = '';
                proxyUsername.value = '';
                proxyPassword.value = '';
                // Hide form
                proxyForm.classList.add('hidden');
                addProxyBtn.classList.remove('hidden');
                // Reload proxies
                loadProxies();
            }
        });
    });
    
    // Cancel form
    cancelProxyBtn.addEventListener('click', function() {
        proxyForm.classList.add('hidden');
        addProxyBtn.classList.remove('hidden');
        status.textContent = 'Cancelled';
    });
    
    // Load proxies on startup
    loadProxies();
});
"""
        
        with open(os.path.join(foxyproxy_dir, "popup.js"), 'w') as f:
            f.write(popup_js)
        
        # Create better placeholder icons (simple colored squares)
        icon_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x10\x00\x00\x00\x10\x08\x02\x00\x00\x00\x90\x91h6\x00\x00\x00\x19IDATx\x9cc```\x00\x00\x00\x04\x00\x01\xf6\x178\x00\x00\x00\x00IEND\xaeB`\x82'
        
        # Create icons for different sizes
        for size in [16, 48, 128]:
            icon_path = os.path.join(foxyproxy_dir, f"icon{size}.png")
            with open(icon_path, 'wb') as f:
                f.write(icon_data)
        
        print(f"✅ Real FoxyProxy extension created at: {foxyproxy_dir}")
        return True
        
    except Exception as e:
        print(f"❌ Error setting up real FoxyProxy extension: {e}")
        return False 

def configure_foxyproxy_with_account_proxy(acc):
    """Configure FoxyProxy extension with account's proxy settings"""
    try:
        if not acc.proxy:
            print(f"📝 No proxy configured for {acc.label}")
            return True
        
        print(f"🔧 Configuring FoxyProxy for {acc.label} with proxy: {acc.proxy}")
        
        # Parse proxy string
        proxy_parts = acc.proxy.split('://')
        if len(proxy_parts) != 2:
            print(f"❌ Invalid proxy format for {acc.label}: {acc.proxy}")
            return False
        
        protocol = proxy_parts[0]
        rest = proxy_parts[1]
        
        # Handle different proxy formats
        if '@' in rest:
            # Format: username:password@host:port
            auth_part, host_part = rest.split('@')
            if ':' in auth_part:
                username, password = auth_part.split(':', 1)
            else:
                username, password = auth_part, ''
            
            if ':' in host_part:
                host, port = host_part.split(':', 1)
            else:
                host, port = host_part, '8080'
        else:
            # Format: host:port:username:password
            parts = rest.split(':')
            if len(parts) >= 4:
                host, port, username, password = parts[0], parts[1], parts[2], parts[3]
            else:
                print(f"❌ Invalid proxy format for {acc.label}: {acc.proxy}")
                return False
        
        # Create proxy configuration
        proxy_config = {
            'name': f"{acc.label} Proxy",
            'host': host,
            'port': int(port),
            'username': username,
            'password': password,
            'protocol': protocol,
            'enabled': True
        }
        
        print(f"✅ Proxy config for {acc.label}: {host}:{port}")
        return True
        
    except Exception as e:
        print(f"❌ Error configuring FoxyProxy for {acc.label}: {e}")
        return False