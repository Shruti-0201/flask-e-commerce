from flask import Flask, abort, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import requests

app = Flask(__name__, template_folder='templates')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///user.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'your_secret_key'

db = SQLAlchemy(app)

# User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False,default ='Guest')  
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    datetime = db.Column(db.DateTime, default=datetime.utcnow)


# --- Product Model ---
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    image = db.Column(db.String(200))  # Store image path or URL

# Create tables (only needed once or if you add new models)
with app.app_context():
    db.create_all()

    def __repr__(self):
        return f'<User {self.email}>'

# Register route with auto-login
@app.route('/', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        raw_password = request.form['password']
        hashed_password = generate_password_hash(raw_password)

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("User already exists. Please log in.", "warning")
            return redirect(url_for('login'))

        new_user = User(email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        # Auto-login after registration
        session['user_id'] = new_user.id
        session['email'] = new_user.email
        flash("Account created and logged in successfully!", "success")
        return redirect(url_for('home'))

    return render_template('register.html')

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email').strip()
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()

        if user:
            if check_password_hash(user.password, password):
                session['user_id'] = user.id
                session['email'] = user.email
                flash("Login successful!", "success")
                return redirect(url_for('home'))
            else:
                flash("Incorrect password", "danger")
        else:
            flash("Email not registered", "warning")

        return redirect(url_for('login'))

    return render_template('login.html')


# Home route
@app.route('/home')
def home():
    # Fetch products from external API
    response = requests.get('https://fakestoreapi.com/products')
    products = response.json()  # This gives a list of dictionaries
    
    # Store in session or a global variable if needed
    search_query = request.args.get('search')
    if search_query:
        products = [p for p in products if search_query.lower() in p['title'].lower()]
    
    return render_template('home.html', products=products)


# Product detail route      
@app.route('/product/<int:product_id>')
def product_detail(product_id):
    response = requests.get('https://fakestoreapi.com/products')
    if response.status_code == 200:
        try:
            products = response.json()
        except ValueError:
            return "Invalid JSON returned from API", 500
    else:
        return f"API failed: {response.status_code}", 500

    # Try to find the product
    product = next((p for p in products if p['id'] == product_id), None)
    if not product:
        return "Product not found", 404

    return render_template('product_detail.html', product=product)

# View cart
@app.route('/cart')
def view_cart():
    cart = session.get('cart', {})
    products = []
    total = 0

    for product_id, quantity in cart.items():
        res = requests.get(f'https://fakestoreapi.com/products/{product_id}')
        if res.status_code == 200:
            product = res.json()
            product['quantity'] = quantity
            product['subtotal'] = round(product['price'] * quantity, 2)
            total += product['subtotal']
            products.append(product)

    return render_template('cart.html', cart=products, total=round(total, 2))


# add to cart route
@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    cart = session.get('cart', {})
    if str(product_id) in cart:
        cart[str(product_id)] += 1
    else:
        cart[str(product_id)] = 1
    session['cart'] = cart
    flash("Product added to cart!", "success")
    return redirect(url_for('view_cart'))

# Checkout form
@app.route('/checkout')
def checkout():
    total = session.get('total', 0)  # retrieve saved total from cart page
    return render_template('checkout.html', total=total)


# Confirmation page
@app.route('/confirm')
def confirm():
    session.pop('cart', None)  # clear cart after confirmation
    return render_template('confirm.html')


# Logout route
@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
