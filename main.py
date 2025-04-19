from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///marketplace.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


# Модели данных
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    is_seller = db.Column(db.Boolean, default=False)


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    image = db.Column(db.String(100))
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    seller = db.relationship('User', backref=db.backref('products', lazy=True))
    category = db.Column(db.String(50))
    stock = db.Column(db.Integer, default=0)


class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    user = db.relationship('User', backref=db.backref('cart_items', lazy=True))
    product = db.relationship('Product', backref=db.backref('in_carts', lazy=True))


# Маршруты
@app.route('/')
def index():
    products = Product.query.filter(Product.stock > 0).limit(12).all()
    return render_template('index.html', products=products)


@app.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template('product.html', product=product)


@app.route('/cart')
def cart():
    if 'user_id' not in session:
        flash('Please login to view your cart', 'warning')
        return redirect(url_for('login'))

    cart_items = Cart.query.filter_by(user_id=session['user_id']).all()
    total = sum(item.product.price * item.quantity for item in cart_items)
    return render_template('cart.html', cart_items=cart_items, total=total)


@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    if 'user_id' not in session:
        flash('Please login to add items to cart', 'warning')
        return redirect(url_for('login'))

    product = Product.query.get_or_404(product_id)
    quantity = int(request.form.get('quantity', 1))

    if quantity > product.stock:
        flash('Not enough stock available', 'danger')
        return redirect(url_for('product_detail', product_id=product_id))

    cart_item = Cart.query.filter_by(user_id=session['user_id'], product_id=product_id).first()

    if cart_item:
        cart_item.quantity += quantity
    else:
        cart_item = Cart(user_id=session['user_id'], product_id=product_id, quantity=quantity)
        db.session.add(cart_item)

    db.session.commit()
    flash('Product added to cart', 'success')
    return redirect(url_for('cart'))


@app.route('/remove_from_cart/<int:cart_item_id>')
def remove_from_cart(cart_item_id):
    if 'user_id' not in session:
        flash('Please login to modify your cart', 'warning')
        return redirect(url_for('login'))

    cart_item = Cart.query.get_or_404(cart_item_id)
    if cart_item.user_id != session['user_id']:
        flash('You cannot modify this cart', 'danger')
        return redirect(url_for('cart'))

    db.session.delete(cart_item)
    db.session.commit()
    flash('Product removed from cart', 'success')
    return redirect(url_for('cart'))

# Аутентификация
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        is_seller = 'is_seller' in request.form

        if User.query.filter_by(username=username).first():
            flash('Username already taken', 'danger')
            return redirect(url_for('register'))

        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)
        new_user = User(username=username, email=email, password=hashed_password, is_seller=is_seller)
        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful. Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('auth/register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if not user or not check_password_hash(user.password, password):
            flash('Invalid username or password', 'danger')
            return redirect(url_for('login'))

        session['user_id'] = user.id
        session['username'] = user.username
        session['is_seller'] = user.is_seller

        flash('Login successful', 'success')
        return redirect(url_for('index'))

    return render_template('auth/login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))

# Панель продавца
@app.route('/seller/dashboard')
def seller_dashboard():
    if 'user_id' not in session or not session.get('is_seller'):
        flash('Access denied', 'danger')
        return redirect(url_for('index'))

    products = Product.query.filter_by(seller_id=session['user_id']).all()
    return render_template('seller/dashboard.html', products=products)

@app.route('/seller/add_product', methods=['GET', 'POST'])
def add_product():
    if 'user_id' not in session or not session.get('is_seller'):
        flash('Access denied', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = float(request.form['price'])
        category = request.form['category']
        stock = int(request.form['stock'])

        # В реальном приложении нужно обрабатывать загрузку изображений
        image = 'default_product.jpg'

        new_product = Product(
            name=name,
            description=description,
            price=price,
            image=image,
            seller_id=session['user_id'],
            category=category,
            stock=stock
        )

        db.session.add(new_product)
        db.session.commit()

        flash('Product added successfully', 'success')
        return redirect(url_for('seller_dashboard'))

    return render_template('seller/add_product.html')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
