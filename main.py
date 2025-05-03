from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import logging
from contextlib import closing

# Настройка приложения
app = Flask(__name__)
app.secret_key = 'super-secret-key'
DATABASE = 'instance/marketplace.db'

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)


# Инициализация базы данных
def init_db():
    with closing(connect_db()) as db:
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()


def connect_db():
    return sqlite3.connect(DATABASE)


def get_db():
    db = connect_db()
    db.row_factory = sqlite3.Row
    return db


# Создаем файл schema.sql с SQL-запросами для создания таблиц
with open('schema.sql', 'w') as f:
    f.write("""
    CREATE TABLE IF NOT EXISTS user (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    );

CREATE TABLE IF NOT EXISTS product (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    price REAL NOT NULL,
    seller_id INTEGER,  -- Убрали NOT NULL
    FOREIGN KEY (seller_id) REFERENCES user (id)
);

    CREATE TABLE IF NOT EXISTS cart_item (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        quantity INTEGER DEFAULT 1,
        user_id INTEGER NOT NULL,
        FOREIGN KEY (product_id) REFERENCES product (id),
        FOREIGN KEY (user_id) REFERENCES user (id)
    );
    """)

# Инициализируем базу данных
with app.app_context():
    init_db()

    # Добавляем тестовые товары, если их нет
    db = get_db()
    if not db.execute("SELECT id FROM product LIMIT 1").fetchone():
        test_products = [
            ('Yellow Evil T-shirt', 'Cool yellow t-shirt', 20),
            ('Gray Evil T-shirt', 'Awesome gray t-shirt', 22),
            ('Green Evil T-shirt', 'Amazing green t-shirt', 18)
        ]
        db.executemany("INSERT INTO product (name, description, price) VALUES (?, ?, ?)", test_products)
        db.commit()


# Вспомогательные функции
def get_products():
    db = get_db()
    return db.execute("SELECT * FROM product").fetchall()


def get_product(product_id):
    db = get_db()
    return db.execute("SELECT * FROM product WHERE id = ?", (product_id,)).fetchone()


# Маршруты
@app.route('/')
def home():
    products = get_products()
    return render_template('index.html', products=products)


@app.route('/prereg')
def prereg():
    if 'user_id' not in session:
        return render_template('prereg.html')
    return redirect(url_for('profile'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        db = get_db()
        existing_user = db.execute("SELECT id FROM user WHERE username = ?", (username,)).fetchone()
        if existing_user:
            return render_template('register_finish.html')

        db.execute("INSERT INTO user (username, password) VALUES (?, ?)", (username, password))
        db.commit()

        user = db.execute("SELECT id FROM user WHERE username = ?", (username,)).fetchone()
        session['user_id'] = user['id']
        return redirect(url_for('profile'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        db = get_db()
        user = db.execute("SELECT id FROM user WHERE username = ? AND password = ?",
                          (username, password)).fetchone()
        if user:
            session['user_id'] = user['id']
            return redirect(url_for('profile'))
        return "Неверный логин или пароль!"

    return render_template('login.html')


@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('account.html')


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('prereg'))


@app.route('/catalog')
def catalog():
    products = get_products()
    return render_template('catalog.html', products=products)


@app.route('/product_view/<int:product_id>', methods=['GET', 'POST'])
def product_view(product_id):
    con = sqlite3.connect("instance/marketplace.db")
    cur = con.cursor()
    product_data = cur.execute("""SELECT name, description, price
     FROM product WHERE id = ?""", (product_id,)).fetchall()
    return render_template('product.html',
                           product_data=product_data[0])

@app.route('/add_to_cart/<int:product_id>')
def add_to_cart(product_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    db = get_db()
    product = get_product(product_id)
    if not product:
        return "Товар не найден", 404

    # Проверяем, есть ли товар уже в корзине
    existing_item = db.execute(
        "SELECT id, quantity FROM cart_item WHERE product_id = ? AND user_id = ?",
        (product_id, session['user_id'])
    ).fetchone()

    if existing_item:
        db.execute(
            "UPDATE cart_item SET quantity = quantity + 1 WHERE id = ?",
            (existing_item['id'],)
        )
    else:
        db.execute(
            "INSERT INTO cart_item (product_id, user_id, quantity) VALUES (?, ?, 1)",
            (product_id, session['user_id'])
        )

    db.commit()
    return redirect(url_for('cart'))


@app.route('/cart')
def cart():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    db = get_db()
    cart_items = db.execute("""
        SELECT cart_item.id, cart_item.quantity, product.id as product_id, 
               product.name, product.price 
        FROM cart_item 
        JOIN product ON cart_item.product_id = product.id
        WHERE cart_item.user_id = ?
    """, (session['user_id'],)).fetchall()

    total = sum(item['price'] * item['quantity'] for item in cart_items)
    return render_template('cart.html', cart_items=cart_items, total=total)


@app.route('/remove_from_cart/<int:item_id>')
def remove_from_cart(item_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    db = get_db()
    db.execute("DELETE FROM cart_item WHERE id = ? AND user_id = ?",
               (item_id, session['user_id']))
    db.commit()
    return redirect(url_for('cart'))


@app.route('/search')
def search():
    query = request.args.get('q', '').lower()
    products = get_products()
    results = [p for p in products if query in p['name'].lower()]
    return render_template('search_results.html', query=query, results=results)


if __name__ == '__main__':
    app.run(debug=True)
