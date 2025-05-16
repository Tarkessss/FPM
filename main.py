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

@app.route('/comic1')
def comic1():
    return render_template('comic1.html')

@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html', products=products)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        password1 = hash_password(password)
        print(f"Username: {username}, Hash: {password1}")

        existing_user = query_db('SELECT * FROM users WHERE username = ?',
                                 [username], one=True)
        if existing_user:
            return render_template('register_finish.html')

        query_db('INSERT INTO users (username, password) VALUES (?, ?)',
                 [username, password1])

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


@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = query_db('SELECT * FROM users WHERE id = ?', [session['user_id']],
                    one=True)
    return render_template('account.html')


@app.route('/product_view/<int:product_id>', methods=['GET', 'POST'])
def product_view(product_id):
    con = sqlite3.connect("instance/marketplace.db")
    cur = con.cursor()
    product_data = cur.execute("""SELECT name, description, price
                                  FROM product
                                  WHERE id = ?""", (product_id,)).fetchall()
    con.close()
    return render_template('product.html',
                           product_data=product_data[0], product_id=product_id)


@app.route('/addtocart/<int:product_id>', methods=['GET', 'POST'])
def addtocart(product_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    try:
        con = sqlite3.connect("instance/marketplace.db")
        cur = con.cursor()
        cur.execute(
            """SELECT quantity FROM cart_item WHERE product_id = ? AND user_id = ?""",
            (product_id, session['user_id']))
        product_quantity = cur.fetchone()
        if product_quantity:
            cur.execute(
                """UPDATE cart_item SET quantity = ? WHERE product_id = ? AND user_id = ?""",
                (product_quantity[0] + 1, product_id, session['user_id']))
        else:
            cur.execute(
                """INSERT INTO cart_item (quantity, product_id, user_id) VALUES (?, ?, ?)""",
                (1, product_id, session['user_id']))
        con.commit()
        return redirect(url_for('cart'))

    except Exception as e:
        logging.error(f"Error adding to cart: {e}")
        return redirect(url_for('error'))
    finally:
        con.close()


@app.route('/cart', methods=['GET', 'POST'])
def cart():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    con = sqlite3.connect("instance/marketplace.db")
    cur = con.cursor()
    pre_cart_items = cur.execute("""
                             SELECT id, quantity, product_id
                             FROM cart_item
                             WHERE user_id = ?
                             """, (session['user_id'],)).fetchall()
    cart_items = []
    for i in pre_cart_items:
        name_price = cur.execute("""SELECT name, price
                                    FROM product
                                    WHERE id = ?""", (i[2],)).fetchall()
        cart_items.append({'name': name_price[0][0],
                           'price': name_price[0][1],
                           'quantity': i[1],
                           'id': i[0]
                           })
    con.close()
    total = sum(item['price'] * item['quantity'] for item in cart_items)
    return render_template('cart.html', cart_items=cart_items, total=total)


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('prereg'))


@app.route('/prereg')
def prereg():
    if 'user_id' not in session:
        return render_template('prereg.html')

    user = query_db('SELECT * FROM users WHERE id = ?', [session['user_id']],
                    one=True)
    return render_template('account.html')


@app.route('/catalog')
def catalog():
    return render_template('catalog.html', products=products)


@app.route('/search')
def search():
    query = request.args.get('q', '')
    results = [p for p in products if query.lower() in p['name'].lower()]
    return render_template('search_results.html', query=query, results=results)


@app.route('/ordering', methods=['GET', 'POST'])
def order():
    con = sqlite3.connect("instance/marketplace.db")
    cur = con.cursor()
    pre_cart_items = cur.execute("""
                             SELECT id, quantity, product_id
                             FROM cart_item
                             WHERE user_id = ?
                             """, (session['user_id'],)).fetchall()
    cart_items = []
    for i in pre_cart_items:
        name_price = cur.execute("""SELECT name, price
                                    FROM product
                                    WHERE id = ?""", (i[2],)).fetchall()
        cart_items.append({'name': name_price[0][0],
                           'price': name_price[0][1],
                           'quantity': i[1],
                           'id': i[0]
                           })
    total_prices = [i['price']*i['quantity'] for i in cart_items]
    total_price = sum(total_prices)
    if request.method == 'POST':
        return redirect(url_for('create_order', total_price=total_price,
                                cart_items=cart_items))
    return render_template('order.html', cart_items=cart_items,
                           total_price=total_price)


@app.route('/create_order', methods=['GET', 'POST'])
def create_order():
    # Передать аргументом не вышло так что снова берем из бд
    con = sqlite3.connect("instance/marketplace.db")
    cur = con.cursor()
    pre_cart_items = cur.execute("""
                             SELECT id, quantity, product_id
                             FROM cart_item
                             WHERE user_id = ?
                             """, (session['user_id'],)).fetchall()
    cart_items = []
    for i in pre_cart_items:
        name_price = cur.execute("""SELECT name, price
                                    FROM product
                                    WHERE id = ?""", (i[2],)).fetchall()
        cart_items.append({'name': name_price[0][0],
                           'price': name_price[0][1],
                           'quantity': i[1],
                           'id': i[0]
                           })
    if request.method == 'POST':
        customer_name = request.form.get('name', '')
        customer_phone = request.form.get('phone', '')
        delivery_address = request.form.get('address', '')
        order_comment = request.form.get('comment', '')

        try:
            for i in cart_items:
                cur.execute(
                    'INSERT INTO orders (product, name, phone, adress, price, quantity, comm) VALUES (?, ?, ?, ?, ?, ?, ?)',
                    (i['name'], customer_name, customer_phone, delivery_address,
                     i['price'] * i['quantity'], i['quantity'], order_comment))
            con.commit()
            return redirect(url_for('index'))
        except Exception as e:
            con.rollback()
            print(f"Error saving order: {e}")
            return redirect(url_for('error'))
        finally:
            con.close()


@app.route('/not_working')
def not_working():
    return render_template('not_working.html')


@app.route('/error')
def error():
    return render_template('error.html')


if __name__ == '__main__':
    app.run(debug=True)
