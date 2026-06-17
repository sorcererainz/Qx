from flask import Flask, render_template, request, jsonify
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os

app = Flask(__name__)

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST')
    return response

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/health')
def health():
    return jsonify({'status': 'ok'})

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
        
        # Setup Chrome
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        
        # Chrome path for Render
        if os.path.exists("/opt/render/project/.render/chrome/opt/google/chrome/chrome"):
            chrome_options.binary_location = "/opt/render/project/.render/chrome/opt/google/chrome/chrome"
        
        driver = webdriver.Chrome(options=chrome_options)
        
        # STEP 1: Open Quotex login page
        print("[*] Opening Quotex...")
        driver.get("https://qxbroker.com/en/sign-in")
        time.sleep(4)
        
        # STEP 2: Check if login form exists
        try:
            # Find email field
            email_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email']"))
            )
            email_field.clear()
            email_field.send_keys(email)
            print(f"[✓] Email entered: {email[:20]}...")
            
            # Find password field
            pass_field = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
            pass_field.clear()
            pass_field.send_keys(password)
            print("[✓] Password entered")
            
            # Find and click login button
            login_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            login_btn.click()
            print("[✓] Login button clicked")
            
            # STEP 3: Wait for response
            time.sleep(6)
            
            # STEP 4: Check if login successful
            current_url = driver.current_url
            page_source = driver.page_source.lower()
            
            # Check for error messages
            error_indicators = [
                "invalid email",
                "invalid password",
                "wrong password",
                "incorrect password",
                "user not found",
                "account not found",
                "login failed",
                "error"
            ]
            
            login_error = False
            for indicator in error_indicators:
                if indicator in page_source:
                    login_error = True
                    break
            
            if login_error:
                driver.quit()
                return jsonify({
                    'success': False,
                    'error': '❌ Login failed! Wrong email or password.'
                })
            
            # Check if redirected to trading platform
            if 'trade' in current_url or 'platform' in current_url or 'demo' in current_url:
                print("[✓] Login successful!")
            else:
                # Maybe still on login page = wrong credentials
                if 'sign-in' in current_url or 'login' in current_url:
                    driver.quit()
                    return jsonify({
                        'success': False,
                        'error': '❌ Invalid credentials. Please check email/password.'
                    })
            
            # STEP 5: Extract REAL balance
            balance = extract_balance_from_page(driver)
            
            driver.quit()
            
            if balance and balance != 'Balance not found':
                return jsonify({
                    'success': True,
                    'balance': balance,
                    'email': email[:15] + '...',
                    'real': True,
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Could not find balance. Login may have failed.'
                })
                
        except Exception as e:
            driver.quit()
            return jsonify({
                'success': False,
                'error': f'Quotex error: {str(e)}'
            })
            
    except Exception as e:
        if driver:
            try:
                driver.quit()
            except:
                pass
        return jsonify({
            'success': False,
            'error': f'System error: {str(e)}'
        })

def extract_balance_from_page(driver):
    """Real balance extract karne ke multiple methods"""
    
    # Method 1: CSS Selectors
    selectors = [
        ".balance-value",
        ".account-balance-value",
        ".trading-account__balance",
        "[class*='balance'] span",
        "[class*='balance'] div",
        ".header-balance",
        ".balance__value",
        ".current-balance"
    ]
    
    for selector in selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            for element in elements:
                text = element.text.strip()
                if text and ('$' in text or '₹' in text or 'USD' in text):
                    # Filter out small amounts
                    nums = text.replace('$','').replace('₹','').replace(',','').replace('USD','').strip()
                    try:
                        if float(nums) > 1:
                            print(f"[✓] Balance found: {text}")
                            return text
                    except:
                        continue
        except:
            continue
    
    # Method 2: JavaScript
    try:
        balance = driver.execute_script("""
            function findBalance() {
                // Look for elements with currency symbols
                let elements = document.querySelectorAll('div, span, p, h1, h2, h3, h4');
                for(let el of elements) {
                    let text = el.textContent.trim();
                    // Match currency patterns
                    if(text.match(/^[\$₹€]?\s*\d{1,3}(?:,\d{3})*\.?\d{0,2}\s*[\$₹€]?$/)) {
                        let num = text.replace(/[^\d.]/g, '');
                        if(parseFloat(num) > 1) {
                            return text;
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
    except:
        pass
    
    # Method 3: Screenshot text
    try:
        # Get entire page text
        body_text = driver.find_element(By.TAG_NAME, "body").text
        lines = body_text.split('\n')
        for line in lines:
            line = line.strip()
            if '$' in line or '₹' in line:
                if len(line) < 30:  # Short lines with currency
                    print(f"[✓] Possible balance: {line}")
                    return line
    except:
        pass
    
    print("[✗] Balance not found")
    return 'Balance not found'

# Error handlers
@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Page not found'}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({'error': 'Server error'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
