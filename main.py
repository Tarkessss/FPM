from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import logging

# Настройка приложения
app = Flask(__name__)
app.secret_key = 'super-secret-key'
DATABASE = 'instance/marketplace.db'

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)

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


# Маршруты
@app.route('/')
def home():
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

        con = sqlite3.connect("instance/marketplace.db")
        cur = con.cursor()
        existing_user = cur.execute("SELECT id FROM user WHERE username = ?", (username,)).fetchone()
        if existing_user:
            return render_template('register_finish.html')

        cur.execute("INSERT INTO user (username, password) VALUES (?, ?)", (username, password))
        cur.commit()

        user = cur.execute("SELECT id FROM user WHERE username = ?", (username,)).fetchone()
        session['user_id'] = user['id']
        return redirect(url_for('profile'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        con = sqlite3.connect("instance/marketplace.db")
        cur = con.cursor()
        user = cur.execute("SELECT id FROM user WHERE username = ? AND password = ?",
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

    con = sqlite3.connect("instance/marketplace.db")
    cur = con.cursor()
    if not product:
        return "Товар не найден", 404

    # Проверяем, есть ли товар уже в корзине
    existing_item = cur.execute(
        "SELECT id, quantity FROM cart_item WHERE product_id = ? AND user_id = ?",
        (product_id, session['user_id'])
    ).fetchone()

    if existing_item:
        cur.execute(
            "UPDATE cart_item SET quantity = quantity + 1 WHERE id = ?",
            (existing_item['id'],)
        )
    else:
        cur.execute(
            "INSERT INTO cart_item (product_id, user_id, quantity) VALUES (?, ?, 1)",
            (product_id, session['user_id'])
        )

    cur.commit()
    return redirect(url_for('cart'))


@app.route('/cart')
def cart():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    con = sqlite3.connect("instance/marketplace.db")
    cur = con.cursor()
    cart_items = cur.execute("""
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

    con = sqlite3.connect("instance/marketplace.db")
    cur = con.cursor()
    cur.execute("DELETE FROM cart_item WHERE id = ? AND user_id = ?",
               (item_id, session['user_id']))
    cur.commit()
    return redirect(url_for('cart'))


@app.route('/search')
def search():
    query = request.args.get('q', '').lower()
    results = [p for p in products if query in p['name'].lower()]
    return render_template('search_results.html', query=query, results=results)


if __name__ == '__main__':
    app.run(debug=True)
