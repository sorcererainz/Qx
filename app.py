from flask import Flask, render_template, request, jsonify
import os

app = Flask(__name__)

@app.route('/')
def home():
    # Check if template exists
    try:
        return render_template('index.html')
    except Exception as e:
        return f"""
        <h1>Error: {str(e)}</h1>
        <p>Make sure 'templates/index.html' exists in your GitHub repo.</p>
        <p>Current error: Template not found</p>
        """, 500

@app.route('/health')
def health():
    return jsonify({
        'status': 'ok',
        'message': 'Server is running'
    })

@app.route('/api/check_balance', methods=['POST'])
def check_balance():
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({
                'success': False,
                'error': 'Email and password required'
            })
        
        # Simple test response (Selenium ke bina)
        # Baad me Selenium add karenge
        return jsonify({
            'success': True,
            'balance': '$10,500.00',
            'message': 'Test mode - Selenium coming soon'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
