from flask import Flask, redirect, url_for, render_template, flash, session, request
import random
from product import item
import json
from flask_sqlalchemy import SQLAlchemy
from form import Login, Signup


app = Flask(__name__)


app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:1234d@awesome-db.ap-southeast-1.psdb.io/usersdb'


app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config["SECRET_KEY"] = "084c798ae26ad8bb088a191feb8224f772"
db = SQLAlchemy(app)

# for user
class User(db.Model):
   
    username = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(120), primary_key=True)
    password = db.Column(db.String(255), nullable=False)
    
    
#add to cart in db
class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_email = db.Column(db.String(120), db.ForeignKey('user.email'), nullable=False)
    product_id = db.Column(db.Integer, nullable=False)
    product_name = db.Column(db.String(255),nullable=False )
    price = db.Column(db.Float, nullable=False)
    image = db.Column(db.String(255))
    selection = db.Column(db.String(50))  
    quantity = db.Column(db.Integer, default=1)


class Orders(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_email = db.Column(db.String(120), nullable=False)
    address = db.Column(db.Text, nullable=False)
    city = db.Column(db.String(100), nullable=False)
    pincode = db.Column(db.String(10), nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    items = db.Column(db.Text, nullable=False)  # Store JSON or a serialized string of items
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), default='Placed')



with app.app_context():
    db.create_all()
    
    
@app.template_filter('loads')
def json_loads_filter(s):
    return json.loads(s)

@app.route("/")
def landingpage():
  
    return render_template("landingpage.html")
@app.route("/home")
def home():
    items = dict(random.sample(list(item.items()), min(8, len(item))))
    return render_template("home.html", products=items)

class Contact(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100))
    message = db.Column(db.Text)


@app.route('/contact', methods=['GET','POST'])
def contact():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        message = request.form['message']

        new_contact = Contact(name=name, email=email, message=message)
        db.session.add(new_contact)
        db.session.commit()

        return "<h1>message sent successfully</h1>"
    return render_template("contact.html")

@app.route("/account")
def account():
    username = session.get('username')
    email = session.get('email')
    return render_template("account.html", username=username, email=email)

@app.route("/login", methods=['GET', 'POST'])
def logins():
    form = Login()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data

        
        if email == "admin@gmail.com" and password == "admin12":
            session['username'] = "Admin"
            session['email'] = email
            flash("Admin login successful.")
            return redirect(url_for('admin_dashboard'))  

        
        user = User.query.filter_by(email=email).first()
        if user and user.password == password:
            session['username'] = user.username
            session['email'] = user.email
            flash('Login Successfully.')
            return redirect(url_for('home'))
        else:
            flash('Invalid Email or Password.')
    
    return render_template("login.html", title="Login", form=form)


@app.route("/signup", methods=['GET', 'POST'])
def signups():
    form = Signup()
    if form.validate_on_submit():
        existing_user = User.query.filter_by(email=form.email.data).first()
        if existing_user:
            flash(f"Email already registered: {form.email.data}. Use another email.")
        else:

            new_user = User(username=form.username.data, email=form.email.data, password=form.password.data)
            db.session.add(new_user)
            db.session.commit()
            flash(f"Successfully registered {form.username.data}.")
            return redirect(url_for('logins'))
    return render_template("signup.html", title="Signup", form=form)

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for('home'))

@app.route("/search", methods=["GET", "POST"])
def search():
    query = request.args.get("q", "").lower()
    results = {}
    if query:
        for product_id, product in item.items():
            name = product.get("name", "").lower()
            category = product.get("category", "").lower()
            type_ = product.get("type", "").lower()
            if query in name or query in category or query in type_:
                results[product_id] = product
    return render_template("search.html", query=query, results=results)

@app.route("/offer")
def offer():
    return render_template("offer.html", products=item)



@app.route('/add-to-cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    if 'email' not in session:
        flash("Please login to add items to cart.")
        return redirect(url_for('logins'))

    product = item.get(product_id)
    if not product:
        flash("Product not found.")
        return redirect(url_for('home'))

    selection = request.form.get("selection")
    user_email = session['email']

    existing = CartItem.query.filter_by(user_email=user_email, product_id=product_id, selection=selection).first()
    if existing:
        existing.quantity += 1
    else:
        new_cart = CartItem(
            user_email=user_email,
            product_id=product_id,
            product_name=product['name'],
            price=product['price'] if product['price'] else product['original_price'],
            image=product['image'],
            selection=selection,
            quantity=1
        )
        db.session.add(new_cart)

    db.session.commit()
    flash("Item added to cart.")
    return redirect(url_for('cart_page'))


@app.route('/cart')
def cart_page():
    if 'email' not in session:
        flash("Please login to view cart.")
        return redirect(url_for('logins'))

    user_email = session['email']
    cart_items = CartItem.query.filter_by(user_email=user_email).all()
    return render_template('cart.html', cart_items=cart_items)


@app.route('/remove-from-cart/<int:item_id>')
def remove_from_cart(item_id):
    if 'email' not in session:
        flash("Please log in.")
        return redirect(url_for('logins'))

    item = CartItem.query.filter_by(id=item_id, user_email=session['email']).first()
    if item:
        db.session.delete(item)
        db.session.commit()
        flash("Item removed from cart.")
    else:
        flash("Item not found in your cart.")
    
    return redirect(url_for('cart_page'))



@app.route('/clear-cart')
def clear_cart_route():
    if 'email' not in session:
        flash("Please log in.")
        return redirect(url_for('logins'))

    CartItem.query.filter_by(user_email=session['email']).delete()
    db.session.commit()
    flash("All items cleared from cart.")
    return redirect(url_for('cart_page'))

@app.route('/increase-qty/<int:item_id>')
def increase_qty(item_id):
    if 'email' not in session:
        flash("Please log in.")
        return redirect(url_for('logins'))

    item = CartItem.query.filter_by(id=item_id, user_email=session['email']).first()
    if item:
        item.quantity += 1
        db.session.commit()
    return redirect(url_for('cart_page'))

@app.route('/decrease-qty/<int:item_id>')
def decrease_qty(item_id):
    if 'email' not in session:
        flash("Please log in.")
        return redirect(url_for('logins'))

    item = CartItem.query.filter_by(id=item_id, user_email=session['email']).first()
    if item:
        if item.quantity > 1:
            item.quantity -= 1
            db.session.commit()
        else:
            # Optional: remove item if quantity hits 0
            db.session.delete(item)
            db.session.commit()
    return redirect(url_for('cart_page'))



@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    if 'email' not in session:
        flash("Please login to proceed.")
        return redirect(url_for('logins'))

    user_email = session['email']
    cart_items = CartItem.query.filter_by(user_email=user_email).all()

    if request.method == "POST":
        address = request.form.get("address")
        city = request.form.get("city")
        pincode = request.form.get("pincode")
        phone = request.form.get("phone")

        # Serialize cart items
        items_list = [{
            'name': item.product_name,
            'price': item.price,
            'selection': item.selection,
            'quantity': item.quantity
        } for item in cart_items]

        total_amount = sum(item.price * item.quantity for item in cart_items)

        order = Orders(
            user_email=user_email,
            address=address,
            city=city,
            pincode=pincode,
            phone=phone,
            items=json.dumps(items_list),
            total_amount=total_amount
        )
        db.session.add(order)
        db.session.commit()

        # Clear cart
        CartItem.query.filter_by(user_email=user_email).delete()
        db.session.commit()

        flash("Order placed successfully!")
        return redirect(url_for('home'))

    return render_template("checkout.html", cart_items=cart_items)

@app.route('/my-orders')
def my_orders():
    if 'email' not in session:
        flash("Please log in to view your orders.")
        return redirect(url_for('logins'))

    user_email = session['email']
    orders = Orders.query.filter_by(user_email=user_email).all()

    # Decode JSON for each order's items
    for order in orders:
        order.decoded_items = json.loads(order.items)

    return render_template("order.html", orders=orders)

@app.route('/cancel-order/<int:order_id>', methods=['POST'])
def cancel_order(order_id):
    if 'email' not in session:
        flash("Please log in.")
        return redirect(url_for('logins'))

    order = Orders.query.get_or_404(order_id)
    if order.user_email != session['email']:
        flash("You are not authorized to cancel this order.")
        return redirect(url_for('my_orders'))

    if order.status != 'Cancelled':
        order.status = 'Cancelled'
        db.session.commit()
        flash("Order has been cancelled.", "info")
    else:
        flash("Order is already cancelled.", "warning")

    return redirect(url_for('my_orders'))



@app.route('/admin/dashboard')
def admin_dashboard():
    total_orders = Orders.query.count()
    placed_orders = Orders.query.filter_by(status='Placed').count()
    cancelled_orders = Orders.query.filter_by(status='Cancelled').count()
    delivered_orders = Orders.query.filter_by(status='Delivered').count()
    total_revenue = db.session.query(db.func.sum(Orders.total_amount))\
        .filter(Orders.status == 'Placed').scalar() or 0

    # Revenue from placed orders only
    total_revenue = db.session.query(db.func.sum(Orders.total_amount)).filter_by(status='Placed').scalar() or 0.0

    chart_data = {
    "labels": ["Placed", "Cancelled", "Delivered"],
    "data": [placed_orders, cancelled_orders, delivered_orders]
}

    return render_template("admin.html",
                           total_orders=total_orders,
                           placed_orders=placed_orders,
                           cancelled_orders=cancelled_orders,
                           total_revenue=total_revenue,
                           chart_data=chart_data)




@app.route('/admin/orders')
def admin_orders():
    if 'email' not in session or session['email'] != 'admin@gmail.com':
        flash("Admin access only.")
        return redirect(url_for('logins'))

    all_orders = Orders.query.order_by(Orders.id.desc()).all()
    for order in all_orders:
        order.decoded_items = json.loads(order.items)

    return render_template("admin_order.html", orders=all_orders)



@app.route('/admin/cancel-order/<int:order_id>', methods=['POST'])
def admin_cancel_order(order_id):
    if 'email' not in session or session['email'] != 'admin@gmail.com':
        flash("Admin access only.")
        return redirect(url_for('logins'))

    order = Orders.query.get_or_404(order_id)
    if order.status != 'Cancelled':
        order.status = 'Cancelled'
        db.session.commit()
        flash("Order cancelled by admin.", "info")
    else:
        flash("Order is already cancelled.", "warning")

    return redirect(url_for('admin_orders'))


@app.route('/admin/deliver-order/<int:order_id>', methods=['POST'])
def admin_deliver_order(order_id):
    order = Orders.query.get(order_id)
    if order and order.status != 'Cancelled':
        order.status = 'Delivered'
        db.session.commit()
        flash(f"Order #{order_id} marked as Delivered.")
    else:
        flash("Order not found or already cancelled.")
    return redirect(url_for('admin_orders'))




@app.route("/men")
def men():
    return render_template("men.html", products=item)

@app.route("/men/topwear")
def topwear():
    return render_template("topwear.html", products=item)

@app.route("/men/bottomwear")
def bottomwear():
    return render_template("bottomwear.html", products=item)

@app.route("/men/ethnicwear")
def ethnicwear():
    return render_template("ethnicwear.html", products=item)

@app.route("/men/formals")
def formal():
    return render_template("formal.html", products=item)

@app.route("/women")
def women():
    return render_template("women.html", products=item)

@app.route("/women/westernwear")
def westernwear():
    return render_template("westernwear.html", products=item)

@app.route("/women/nightwear")
def gnightwear():
    return render_template("Gnightwear.html", products=item)

@app.route("/women/gymwear")
def gymwear():
    return render_template("gymwear.html", products=item)

@app.route("/women/ethnics")
def ethnics():
    return render_template("ethnics.html", products=item)

@app.route("/women/accessories")
def accessories():
    return render_template("accessories.html", products=item)

@app.route("/kids")
def kids():
    return render_template("kids.html", products=item)

@app.route("/kids/infants")
def infants():
    return render_template("infants.html", products=item)

@app.route("/kids/boys")
def boys():
    return render_template("boys.html", products=item)

@app.route("/kids/girls")
def girls():
    return render_template("girls.html", products=item)


@app.route("/women/product/<int:product_id>")
def product_detail_women(product_id):
    product = item.get(product_id)
    if not product:
        return "Product not found", 404
    return render_template("product_details.html", product=product, product_id=product_id)

@app.route("/men/product/<int:product_id>")
def product_detail_men(product_id):
    product = item.get(product_id)
    if not product:
        return "Product not found", 404
    return render_template("product_details.html", product=product, product_id=product_id)

@app.route("/kids/product/<int:product_id>")
def product_detail_kids(product_id):
    product = item.get(product_id)
    if not product:
        return "Product not found", 404
    return render_template("product_details.html", product=product, product_id=product_id)

if __name__ == "__main__":
    app.run(debug=True)
