from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = 'super-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///shop.db'  # Файл БД
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Модель пользователя
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(50), nullable=False)
    cart = db.relationship('CartItem', backref='user', lazy=True)  # Связь с корзиной

# Модель товара в корзине
class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# Создаём таблицы в БД
with app.app_context():
    db.create_all()

# Товары
products = [
    {'id': 1, 'name': 'Yellow Evil T-shirt', 'price': 20},
    {'id': 2, 'name': 'Gray Evil T-shirt', 'price': 22},
    {'id': 3, 'name': 'Green Evil T-shirt', 'price': 18}
]


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Проверяем, нет ли уже такого пользователя
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return render_template('register_finish.html')

        # Создаём нового пользователя
        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username, password=password).first()

        if user:
            session['user_id'] = user.id  # Сохраняем ID в сессии
            return redirect(url_for('profile'))
        else:
            return "Неверный логин или пароль!"

    return render_template('login.html')


@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    return render_template('account.html')


@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    product_name = request.form['product_name']
    user = User.query.get(session['user_id'])

    # Проверяем, есть ли товар уже в корзине
    existing_item = CartItem.query.filter_by(product_name=product_name, user_id=user.id).first()

    if existing_item:
        existing_item.quantity += 1
    else:
        new_item = CartItem(product_name=product_name, user_id=user.id)
        db.session.add(new_item)

    db.session.commit()
    return "Товар добавлен в корзину!"


@app.route('/cart')
def view_cart():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    cart_items = user.cart
    return render_template('cart.html', cart_items=cart_items)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('prereg'))

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/prereg')
def prereg():
    if 'user_id' not in session:
        return render_template('prereg.html')


    user = User.query.get(session['user_id'])
    return render_template('account.html')


@app.route('/catalog')
def catalog():
    return render_template('catalog.html', products=products)

@app.route('/search')
def search():
    query = request.args.get('q', '')
    # Пример "поиска" по товарам — просто фильтруем по вхождению
    products = [
        "Rollercoaster T-shirt",
        "Destruct-inator",
        "Deflate-inator",
        "Age Accelerator-inator"
    ]
    results = [p for p in products if query.lower() in p.lower()]
    return render_template('search_results.html', query=query, results=results)


if __name__ == '__main__':
    app.run(debug=True)
