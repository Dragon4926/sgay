from flask import Flask, render_template, flash, url_for, session, request, redirect
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

@app.route('/')
def index():
    return render_template('login.html')

@app.route('/register')
def register():
    return render_template('register.html')

@app.route('/login-otp')
def login_otp():
    return render_template('login_otp.html')

@app.route('/verify-otp')
def verify_otp():
    # Simulate a phone number for testing
    return render_template('verify_otp.html', phone_to_verify='9876543210')

@app.route('/flash-test')
def flash_test():
    # Send some test flash messages
    flash('This is a success message', 'success')
    flash('This is an error message', 'error')
    flash('This is an info message', 'info')
    flash('This is a warning message', 'warning')
    return redirect(url_for('verify_otp'))

if __name__ == '__main__':
    # Enable Jinja template debug for better error messages
    app.jinja_env.auto_reload = True
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    
    # Run the test app
    app.run(debug=True, port=5050) 