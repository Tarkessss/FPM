from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import logging
import os
import hashlib


STATIC_SALT = "123abc"

def hash_password(password):
    salted_password = STATIC_SALT + password
    return hashlib.md5(salted_password.encode('utf-8')).hexdigest()

def verify_password(password1, input_password):
    return password1 == hash_password(input_password)

app = Flask(__name__)
app.secret_key = 'super-secret-key'
DATABASE = 'shop.db'

logging.basicConfig(level=logging.DEBUG)
app = Flask(__name__)
app.secret_key = 'super-secret-key'
con = sqlite3.connect("instance/marketplace.db")
cur = con.cursor()
products = []
try:
    for product in cur.execute("""SELECT * FROM product""").fetchall():
        products.append({'id': product[0],
                         'name': product[1],
                         'descr': product[2],
                         'price': product[3]})
except Exception as e:
    products = []
    logging.info(e)


def init_db():
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cart_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_name TEXT NOT NULL,
                quantity INTEGER DEFAULT 1,
                user_id INTEGER NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        conn.commit()


if not os.path.exists(DATABASE):
    init_db()


def query_db(query, args=(), one=False):
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, args)
        result = cursor.fetchall()
        conn.commit()
        return (result[0] if result else None) if one else result


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        password1 = hash_password(password)
        print(f"Username: {username}, Hash: {password1}")

        existing_user = query_db('SELECT * FROM users WHERE username = ?', [username], one=True)
        if existing_user:
            return render_template('register_finish.html')

        query_db('INSERT INTO users (username, password) VALUES (?, ?)', [username, password1])

        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        password1 = hash_password(password)
        user = query_db('SELECT * FROM users WHERE username = ?',
                        [username], one=True)

        if user and verify_password(user['password'], password):
            session['user_id'] = user['id']
            return redirect(url_for('profile'))
        else:
            return "Неверный логин или пароль!"

    return render_template('login.html')


@app.route('/product_view/<int:product_id>', methods=['GET', 'POST'])
def product_view(product_id):
    con = sqlite3.connect("instance/marketplace.db")
    cur = con.cursor()
    product_data = cur.execute("""SELECT name, description, price
     FROM product WHERE id = ?""", (product_id,)).fetchall()
    return render_template('product.html',
                           product_data=product_data[0])


@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = query_db('SELECT * FROM users WHERE id = ?', [session['user_id']], one=True)
    return render_template('account.html')


@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    product_name = request.form['product_name']
    user_id = session['user_id']

    existing_item = query_db('SELECT * FROM cart_items WHERE product_name = ? AND user_id = ?',
                             [product_name, user_id], one=True)

    if existing_item:
        query_db('UPDATE cart_items SET quantity = quantity + 1 WHERE id = ?',
                 [existing_item['id']])
    else:
        query_db('INSERT INTO cart_items (product_name, user_id) VALUES (?, ?)',
                 [product_name, user_id])

    return "Товар добавлен в корзину!"


@app.route('/cart')
def view_cart():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    cart_items = []
    if 'cart' in session:
        for pid in session['cart']:
            for product in products:
                if product['id'] == pid:
                    cart_items.append(product)
    return render_template('cart.html', cart_items=cart_items)


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('prereg'))


@app.route('/')
def index():
    return render_template('index.html', products=products)


@app.route('/prereg')
def prereg():
    if 'user_id' not in session:
        return render_template('prereg.html')

    user = query_db('SELECT * FROM users WHERE id = ?', [session['user_id']], one=True)
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
