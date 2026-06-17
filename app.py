from flask import Flask, render_template, request, jsonify
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time
import os

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/check_balance', methods=['POST'])
def check_balance():
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')
        
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.binary_location = "/opt/render/project/.render/chrome/opt/google/chrome/chrome"
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.get("https://qxbroker.com/en/sign-in")
        time.sleep(3)
        
        email_field = driver.find_element(By.CSS_SELECTOR, "input[type='email']")
        email_field.send_keys(email)
        
        pass_field = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
        pass_field.send_keys(password)
        
        submit_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        submit_btn.click()
        time.sleep(5)
        
        balance = driver.execute_script("""
            let elements = document.querySelectorAll('*');
            for(let el of elements) {
                if(el.innerText && el.innerText.match(/[\$₹][\d,]+/)) {
                    return el.innerText;
                }
            }
            return 'Balance not found';
        """)
        
        driver.quit()
        return jsonify({'success': True, 'balance': balance})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
