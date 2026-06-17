from flask import Flask, render_template, request, jsonify
import requests
import time
import json

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
    return jsonify({
        'status': 'ok',
        'time': time.strftime('%H:%M:%S')
    })

@app.route('/api/check_balance', methods=['POST'])
def check_balance():
    try:
        data = request.get_json()
        email = data.get('email', '').strip()
        password = data.get('password', '').strip()
        
        if not email or not password:
            return jsonify({
                'success': False,
                'error': 'Email and password required'
            })
        
        # Quotex API endpoints
        session = requests.Session()
        
        # Headers to mimic browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Content-Type': 'application/json',
            'Origin': 'https://qxbroker.com',
            'Referer': 'https://qxbroker.com/en/sign-in'
        }
        
        # STEP 1: Get initial token
        print("[*] Connecting to Quotex...")
        main_page = session.get('https://qxbroker.com/en/sign-in', headers=headers, timeout=10)
        
        # STEP 2: Try login
        login_url = 'https://qxbroker.com/api/v1/auth/login'
        login_data = {
            'email': email,
            'password': password,
            'remember': True
        }
        
        print(f"[*] Attempting login for: {email[:20]}...")
        login_response = session.post(login_url, json=login_data, headers=headers, timeout=15)
        
        print(f"[*] Login response status: {login_response.status_code}")
        
        # STEP 3: Check login result
        if login_response.status_code == 200:
            resp_data = login_response.json()
            
            # Check if login was successful
            if resp_data.get('success') or resp_data.get('token') or resp_data.get('access_token'):
                print("[✓] Login successful!")
                
                # STEP 4: Get account info
                profile_url = 'https://qxbroker.com/api/v1/user/profile'
                profile_response = session.get(profile_url, headers=headers, timeout=10)
                
                if profile_response.status_code == 200:
                    profile_data = profile_response.json()
                    balance = profile_data.get('balance', 'Not found')
                    
                    return jsonify({
                        'success': True,
                        'balance': f'${balance}',
                        'real': True,
                        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
                    })
                
            elif resp_data.get('error') or resp_data.get('message'):
                error_msg = resp_data.get('error') or resp_data.get('message')
                return jsonify({
                    'success': False,
                    'error': f'❌ {error_msg}'
                })
        
        elif login_response.status_code == 401 or login_response.status_code == 403:
            return jsonify({
                'success': False,
                'error': '❌ Invalid email or password!'
            })
        
        elif login_response.status_code == 429:
            return jsonify({
                'success': False,
                'error': '❌ Too many attempts. Please wait and try again.'
            })
        
        # If API method fails, return clear error
        return jsonify({
            'success': False,
            'error': f'❌ Login failed (Status: {login_response.status_code}). Please check credentials.'
        })
        
    except requests.exceptions.Timeout:
        return jsonify({
            'success': False,
            'error': '❌ Connection timeout. Quotex server not responding.'
        })
    except requests.exceptions.ConnectionError:
        return jsonify({
            'success': False,
            'error': '❌ Cannot connect to Quotex. Network issue.'
        })
    except Exception as e:
        print(f"[!] Error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error: {str(e)}'
        })

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Page not found'}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({'error': 'Server error'}), 500

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
