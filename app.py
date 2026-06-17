from flask import Flask, render_template, request, jsonify
import time
import os
import sys

app = Flask(__name__)

# Homepage - Pehle ye load karo
@app.route('/')
def home():
    try:
        return render_template('index.html')
    except Exception as e:
        return f"<h1>Error loading page: {str(e)}</h1>", 500

# Health check endpoint
@app.route('/health')
def health():
    return jsonify({
        'status': 'alive',
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
    })

# Test endpoint (Bina Selenium ke)
@app.route('/api/test')
def test():
    return jsonify({
        'message': 'Backend is working!',
        'chrome': 'Not tested yet'
    })

# Balance check endpoint
@app.route('/api/check_balance', methods=['POST'])
def check_balance():
    try:
        # Import yaha karo (agar module missing ho to error clear dikhe)
        try:
            from selenium import webdriver
            from selenium.webdriver.common.by import By
            from selenium.webdriver.chrome.options import Options
        except ImportError as e:
            return jsonify({
                'success': False, 
                'error': f'Selenium import failed: {str(e)}. Install: pip install selenium'
            })
        
        data = request.json
        email = data.get('email', '')
        password = data.get('password', '')
        
        if not email or not password:
            return jsonify({
                'success': False,
                'error': 'Email and password are required'
            })
        
        # Chrome options
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        
        # Chrome path for Render
        chrome_paths = [
            "/opt/render/project/.render/chrome/opt/google/chrome/chrome",
            "/usr/bin/google-chrome",
            "/usr/bin/chromium-browser",
            "/usr/bin/chromium"
        ]
        
        for path in chrome_paths:
            if os.path.exists(path):
                chrome_options.binary_location = path
                break
        
        # Driver setup
        try:
            driver = webdriver.Chrome(options=chrome_options)
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Chrome driver failed: {str(e)}'
            })
        
        # Quotex automation
        try:
            driver.get("https://qxbroker.com/en/sign-in")
            time.sleep(4)
            
            # JavaScript se login (more reliable)
            login_script = f"""
                var emailField = document.querySelector('input[type="email"]');
                var passField = document.querySelector('input[type="password"]');
                var submitBtn = document.querySelector('button[type="submit"]');
                
                if(emailField && passField && submitBtn) {{
                    emailField.value = '{email}';
                    passField.value = '{password}';
                    emailField.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    passField.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    submitBtn.click();
                    return 'login_clicked';
                }} else {{
                    return 'fields_not_found';
                }}
            """
            
            result = driver.execute_script(login_script)
            
            if result == 'fields_not_found':
                # Fallback: Selenium se find karo
                email_field = driver.find_element(By.CSS_SELECTOR, "input[type='email']")
                email_field.send_keys(email)
                pass_field = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
                pass_field.send_keys(password)
                driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
            
            # Wait for dashboard
            time.sleep(6)
            
            # Extract balance
            balance = driver.execute_script("""
                function findBalance() {
                    var all = document.querySelectorAll('*');
                    for(var i = 0; i < all.length; i++) {
                        var text = all[i].textContent || '';
                        text = text.trim();
                        if(text.match(/^\$[\d,]+\.?\d*/) || text.match(/^₹[\d,]+\.?\d*/)) {
                            return text;
                        }
                    }
                    return 'Balance not found';
                }
                return findBalance();
            """)
            
            driver.quit()
            
            return jsonify({
                'success': True,
                'balance': balance,
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            })
            
        except Exception as e:
            try:
                driver.quit()
            except:
                pass
            return jsonify({
                'success': False,
                'error': f'Automation error: {str(e)}'
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        })

# Error handlers
@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Page not found'}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({'error': 'Internal server error. Check logs.'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
