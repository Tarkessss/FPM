import sqlite3

from flask import Flask, render_template, redirect, url_for, request, session
import logging

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

@app.route('/')
def index():
    return render_template('index.html', products=products)


@app.route('/product_view/<int:product_id>', methods=['GET', 'POST'])
def product_view(product_id):
    con = sqlite3.connect("instance/marketplace.db")
    cur = con.cursor()
    product_data = cur.execute("""SELECT name, description, price
     FROM product WHERE id = ?""", (product_id, )).fetchall()
    return render_template('product.html',
                           product_data=product_data[0])


@app.route('/catalog')
def catalog():
    return render_template('catalog.html')


@app.route('/add_to_cart/<int:product_id>')
def add_to_cart(product_id):
    if 'cart' not in session:
        session['cart'] = []
    session['cart'].append(product_id)
    return redirect(url_for('cart'))


@app.route('/cart')
def cart():
    cart_items = []
    if 'cart' in session:
        for pid in session['cart']:
            for product in products:
                if product['id'] == pid:
                    cart_items.append(product)
    return render_template('cart.html', cart_items=cart_items)


@app.route('/account', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if (request.form['username'] == 'admin' and
                request.form['password'] == '123'):
            session['user'] = request.form['username']
            return redirect(url_for('home'))
        return "Неверный логин или пароль"
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('home'))


if __name__ == '__main__':
    app.run(debug=True)
