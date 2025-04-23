from flask import Flask, render_template, redirect, url_for, request, session

app = Flask(__name__)
app.secret_key = 'super-secret-key'

# Товары
products = [
    {'id': 1, 'name': 'Yellow Evil T-shirt', 'price': 20},
    {'id': 2, 'name': 'Gray Evil T-shirt', 'price': 22},
    {'id': 3, 'name': 'Green Evil T-shirt', 'price': 18}
]

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/catalog')
def catalog():
    return render_template('catalog.html', products=products)

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
        if request.form['username'] == 'admin' and request.form['password'] == '123':
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
