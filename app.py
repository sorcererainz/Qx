from flask import Flask, render_template, request, jsonify
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
import time
import os
import json

app = Flask(__name__)

def create_driver():
    """Create Chrome driver with proper settings"""
    chrome_options = Options()
    
    # Required for Docker/Render
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # Disable images for speed
    prefs = {"profile.managed_default_content_settings.images": 2}
    chrome_options.add_experimental_option("prefs", prefs)
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(30)
        return driver
    except Exception as e:
        print(f"Driver creation error: {e}")
        return None

def login_quotex(driver, email, password):
    """Login to Quotex and return balance"""
    try:
        print("[*] Opening Quotex login page...")
        driver.get("https://qxbroker.com/en/sign-in")
        time.sleep(3)
        
        # Check if already logged in
        current_url = driver.current_url
        if 'trade' in current_url or 'platform' in current_url:
            print("[✓] Already logged in!")
            return extract_balance(driver)
        
        # Wait for login form
        print("[*] Waiting for login form...")
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email']"))
        )
        
        # Fill email
        print(f"[*] Entering email: {email[:20]}...")
        email_field = driver.find_element(By.CSS_SELECTOR, "input[type='email']")
        email_field.clear()
        time.sleep(0.5)
        email_field.send_keys(email)
        
        # Fill password
        print("[*] Entering password...")
        pass_field = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
        pass_field.clear()
        time.sleep(0.5)
        pass_field.send_keys(password)
        
        time.sleep(1)
        
        # Click login button
        print("[*] Clicking login...")
        login_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        login_btn.click()
        
        # Wait for redirect
        time.sleep(5)
        
        # Check if login successful
        current_url = driver.current_url
        page_text = driver.page_source.lower()
        
        # Check for error messages
        error_keywords = ['invalid', 'wrong', 'incorrect', 'not found', 'error', 'failed']
        for keyword in error_keywords:
            if keyword in page_text:
                print(f"[✗] Login failed: '{keyword}' found")
                return None, f"Login failed: Invalid credentials"
        
        # Check if redirected to trading platform
        if 'trade' in current_url or 'platform' in current_url or 'demo' in current_url:
            print("[✓] Login successful!")
            balance = extract_balance(driver)
            return balance, None
        else:
            print(f"[!] Unknown redirect: {current_url}")
            # Still try to extract balance
            balance = extract_balance(driver)
            return balance, None
            
    except TimeoutException:
        return None, "Timeout: Quotex page took too long to load"
    except Exception as e:
        return None, f"Login error: {str(e)}"

def extract_balance(driver):
    """Extract balance from page"""
    print("[*] Extracting balance...")
    time.sleep(2)
    
    # Method 1: JavaScript
    try:
        balance = driver.execute_script("""
            function findBalance() {
                // Look for currency elements
                let elements = document.querySelectorAll('div, span, p, h1, h2, h3');
                for (let el of elements) {
                    let text = el.textContent.trim();
                    // Match currency patterns
                    if (text.match(/^[\$₹€]?\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})?\s*[\$₹€]?$/)) {
                        let num = parseFloat(text.replace(/[^\d.]/g, ''));
                        if (num > 1 && num < 1000000000) {
                            // Check if this element is visible
                            let style = window.getComputedStyle(el);
                            if (style.display !== 'none' && style.visibility !== 'hidden') {
                                return text;
                            }
                        }
                    }
                }
                return null;
            }
            return findBalance();
        """)
        
        if balance:
            print(f"[✓] Balance found via JS: {balance}")
            return balance
    except Exception as e:
        print(f"[!] JS extraction failed: {e}")
    
    # Method 2: Common CSS selectors
    selectors = [
        "[class*='balance']",
        "[class*='amount']",
        "[class*='account'] span",
        ".header-balance",
        ".user-balance"
    ]
    
    for selector in selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            for element in elements:
                text = element.text.strip()
                if text and ('$' in text or '₹' in text):
                    print(f"[✓] Balance found via CSS: {text}")
                    return text
        except:
            continue
    
    # Method 3: Full page text search
    try:
        body = driver.find_element(By.TAG_NAME, "body").text
        lines = body.split('\n')
        for line in lines:
            if '$' in line or '₹' in line:
                if len(line) < 30:
                    print(f"[✓] Possible balance: {line}")
                    return line
    except:
        pass
    
    print("[✗] Balance not found")
    return None

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'time': time.strftime('%H:%M:%S')})

@app.route('/api/check_balance', methods=['POST'])
def check_balance():
    driver = None
    
    try:
        data = request.get_json()
        email = data.get('email', '').strip()
        password = data.get('password', '').strip()
        
        if not email or not password:
            return jsonify({
                'success': False,
                'error': 'Email and password required'
            })
        
        print(f"\n{'='*50}")
        print(f"[*] New request for: {email[:20]}...")
        
        # Create driver
        driver = create_driver()
        if not driver:
            return jsonify({
                'success': False,
                'error': 'Browser initialization failed'
            })
        
        # Login and get balance
        balance, error = login_quotex(driver, email, password)
        
        if driver:
            driver.quit()
        
        if error:
            return jsonify({
                'success': False,
                'error': error
            })
        
        if balance:
            return jsonify({
                'success': True,
                'balance': balance,
                'email': email[:15] + '...',
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'auto': True
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Could not find balance. Try refreshing.'
            })
            
    except Exception as e:
        if driver:
            try:
                driver.quit()
            except:
                pass
        
        print(f"[!] Critical error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'System error: {str(e)}'
        })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
