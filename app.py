from flask import Flask, render_template, request, redirect, session, jsonify,flash,url_for
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mysqldb import MySQL
import MySQLdb.cursors
from datetime import date, timedelta
from db_config import init_db
import os

app = Flask(__name__)
app.secret_key = "mysecret"
app.config['UPLOAD_FOLDER'] = "static/uploads"

mysql = init_db(app)

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# ---------------- Home ----------------
@app.route("/")
def home():
    return render_template("homepage.html")

# ---------------- Owner Dashboard ----------------
@app.route("/owner_dashboard")
def owner_dashboard():
    return render_template("owner_dashboard.html")

# ---------------- Customer Home ----------------
@app.route("/customer_home")
def customer_home():
    return render_template("customer_home.html")

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        fullname = request.form.get('fullname')
        email = request.form.get('email')
        mobile = request.form.get('mobile')
        address = request.form.get('address')
        password = request.form.get('password')
        usertype = request.form.get('usertype')

        if not fullname or not email or not mobile or not address or not password  or not usertype:
            return render_template('register.html', error="All fields are required!")


        hashed_password = generate_password_hash(password)

        cur = mysql.connection.cursor()
        try:
            cur.execute("""
                INSERT INTO users (fullname, email, mobile, address, password, usertype)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (fullname, email, mobile, address, hashed_password, usertype))
            mysql.connection.commit()
        except Exception as e:
            return render_template('register.html', error="Email already exists!")
        finally:
            cur.close()

        return redirect('/login')

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if not email or not password:
            return render_template('login.html', error="All fields are required!")

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cur.fetchone()
        cur.close()

        if not user:
            return render_template("login.html", error="Email not registered!")

        if not check_password_hash(user['password'], password):
            return render_template("login.html", error="Invalid password!")

        # ✅ LOGIN SUCCESS
        session['email'] = user['email']
        session['usertype'] = user['usertype']
        session['customer_name'] = user['fullname']

        if user['email'] == "support@tastyhub.com":
            return redirect('/owner_dashboard')
        else:
            return redirect('/customer_home')

    return render_template('login.html')


@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    error = None
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        confirm = request.form.get('confirm')

        if not email or not password or not confirm:
            error = "All fields are required!"
        elif password != confirm:
            error = "Passwords do not match!"
        else:
            cur = mysql.connection.cursor()
            cur.execute("SELECT * FROM users WHERE email=%s", (email,))
            user = cur.fetchone()
            if user:
                hashed_password = generate_password_hash(password)
                cur.execute("UPDATE users SET password=%s WHERE email=%s", (hashed_password, email))
                mysql.connection.commit()
                cur.close()
                return redirect('/login')  # redirect to login page after successful reset
            else:
                error = "Email not found!"

    return render_template('forgot_password.html', error=error)


@app.route("/logout")
def logout_page():
    # ONLY show confirmation page
    return render_template("logout.html")


@app.route("/logout_confirm", methods=["POST"])
def logout_confirm():
    session.clear()
    flash("Logged out successfully!", "success")
    return redirect("/")

@app.route("/get_food")
def get_food():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM menu")
    rows = cur.fetchall()
    cur.close()
    menu = []
    for row in rows:
        menu.append({
            "id": row["id"],
            "name": row["name"],
            "category": row["category"],
            "price": float(row["price"]),
            "image": row["image"]  # Make sure path starts with /static/uploads/
        })
    return jsonify(menu)

# ---------------- Add Food ----------------
@app.route("/add_food", methods=["POST"])
def add_food():
    name = request.form.get("name")
    category = request.form.get("category")
    price = request.form.get("price")
    file = request.files.get("image")

    if not name or not category or not price or not file:
        return jsonify({"status":"error","message":"All fields required!"})

    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)

    cur = mysql.connection.cursor()
    cur.execute("""
        INSERT INTO menu (name, category, price, image)
        VALUES (%s,%s,%s,%s)
    """, (name, category, price, "/" + file_path))
    mysql.connection.commit()
    cur.close()
    return jsonify({"status":"success","message":"Food added!"})

# ---------------- Update Food ----------------
@app.route("/update_food", methods=["POST"])
def update_food():
    name = request.form.get("name")
    price = request.form.get("price")

    if not name or not price:
        return jsonify({"message": "Food name and new price required"})

    cur = mysql.connection.cursor()
    cur.execute(
        "UPDATE menu SET price=%s WHERE name=%s",
        (price, name)
    )
    mysql.connection.commit()
    cur.close()

    return jsonify({"message": "Price updated successfully"})



@app.route("/delete_food", methods=["POST"])
def delete_food():
    name = request.form.get("name")

    if not name:
        return jsonify({"message": "Food name required"})

    cur = mysql.connection.cursor()
    cur.execute(
        "DELETE FROM menu WHERE name=%s",
        (name,)
    )
    mysql.connection.commit()
    cur.close()

    return jsonify({"message": "Food deleted successfully"})


@app.route("/get_customers")
def get_customers():
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cur.execute("""
        SELECT 
            u.id AS user_id,
            u.fullname AS name,
            u.email,
            u.mobile,
            MAX(p.address) AS address,
            COUNT(CASE WHEN p.payment_status='Paid' THEN o.id END) AS total_orders,
            IFNULL(SUM(CASE WHEN p.payment_status='Paid' THEN o.total_amount END),0) AS total_bill
        FROM users u
        JOIN orders o ON u.id = o.user_id
        JOIN payment_history p ON o.id = p.order_id
        GROUP BY u.id, u.fullname, u.email, u.mobile
        HAVING total_orders > 0
        ORDER BY u.fullname
    """)

    customers = cur.fetchall()
    cur.close()

    for i, c in enumerate(customers, start=1):
        c['sr'] = i

    return jsonify(customers)

# ---------------- Add item to cart ----------------
@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    if 'email' not in session:
        return jsonify({"status":"error","message":"Login required!"})

    data = request.get_json()
    menu_id = data.get('menu_id')
    quantity = data.get('quantity', 1)

    cur = mysql.connection.cursor()
    # Get user_id from email
    cur.execute("SELECT id FROM users WHERE email=%s", (session['email'],))
    user = cur.fetchone()
    if not user:
        return jsonify({"status":"error","message":"User not found!"})
    user_id = user["id"]

    # Check if item already in cart
    cur.execute("SELECT * FROM cart WHERE user_id=%s AND menu_id=%s", (user_id, menu_id))
    existing = cur.fetchone()
    if existing:
        cur.execute("UPDATE cart SET quantity=quantity+%s WHERE user_id=%s AND menu_id=%s", (quantity, user_id, menu_id))
    else:
        cur.execute("INSERT INTO cart (user_id, menu_id, quantity) VALUES (%s,%s,%s)", (user_id, menu_id, quantity))

    mysql.connection.commit()
    cur.close()
    return jsonify({"status":"success","message":"Added to cart!"})


# ---------------- Get cart items ----------------
@app.route('/get_cart')
def get_cart():
    if 'email' not in session:
        return jsonify([])

    cur = mysql.connection.cursor()
    # Get user_id
    cur.execute("SELECT id FROM users WHERE email=%s", (session['email'],))
    user = cur.fetchone()
    if not user:
        return jsonify([])
    user_id = user["id"]

    cur.execute("""
        SELECT c.id AS cart_id, c.menu_id, c.quantity, m.name, m.price, m.image
        FROM cart c
        JOIN menu m ON c.menu_id = m.id
        WHERE c.user_id=%s
    """, (user_id,))
    items = cur.fetchall()
    cur.close()

    cart_list = []
    for i in items:
        cart_list.append({
            "cart_id": i["cart_id"],
            "menu_id": i["menu_id"],
            "name": i["name"],
            "price": float(i["price"]),
            "quantity": i["quantity"],
            "image": i["image"]
        })
    return jsonify(cart_list)


# ---------------- Update cart quantity ----------------
@app.route('/update_cart', methods=['POST'])
def update_cart():
    if 'email' not in session:
        return jsonify({"status":"error","message":"Login required!"})

    data = request.get_json()
    cart_id = data.get('cart_id')
    quantity = data.get('quantity', 1)

    cur = mysql.connection.cursor()
    # Get user_id
    cur.execute("SELECT id FROM users WHERE email=%s", (session['email'],))
    user = cur.fetchone()
    if not user:
        return jsonify({"status":"error","message":"User not found!"})
    user_id = user["id"]

    if quantity < 1:
        cur.execute("DELETE FROM cart WHERE id=%s AND user_id=%s", (cart_id, user_id))
        mysql.connection.commit()
        cur.close()
        return jsonify({"status":"success","message":"Item removed"})

    cur.execute("UPDATE cart SET quantity=%s WHERE id=%s AND user_id=%s", (quantity, cart_id, user_id))
    mysql.connection.commit()
    cur.close()
    return jsonify({"status":"success","message":"Quantity updated"})


@app.route('/place_order', methods=['POST'])
def place_order():
    if 'email' not in session:
        return jsonify({"status":"error","message":"Login required!"})

    cur = mysql.connection.cursor()
    # Get user info
    cur.execute("SELECT id, fullname, mobile, address FROM users WHERE email=%s", (session['email'],))
    user = cur.fetchone()
    if not user:
        return jsonify({"status":"error","message":"User not found!"})

    user_id = user["id"]

    # Get cart items
    cur.execute("""
        SELECT c.menu_id, c.quantity, m.price
        FROM cart c
        JOIN menu m ON c.menu_id = m.id
        WHERE c.user_id=%s
    """, (user_id,))
    cart_items = cur.fetchall()
    if not cart_items:
        cur.close()
        return jsonify({"status":"error","message":"Cart is empty!"})

    total_amount = sum([i["quantity"] * float(i["price"]) for i in cart_items])

    # Insert into orders
    cur.execute(
        "INSERT INTO orders (user_id, user_email, total_amount) VALUES (%s,%s,%s)",
        (user_id, session['email'], total_amount)
    )
    order_id = cur.lastrowid

    # Insert order items
    for item in cart_items:
        cur.execute("""
            INSERT INTO order_items (order_id, menu_id, quantity, price)
            VALUES (%s,%s,%s,%s)
        """, (order_id, item["menu_id"], item["quantity"], float(item["price"])))

    # Insert payment history
    cur.execute("""
        INSERT INTO payment_history (order_id, customer_name, mobile, address, total_amount)
        VALUES (%s,%s,%s,%s,%s)
    """, (order_id, user["fullname"], user["mobile"], user["address"], total_amount))

    # Clear user's cart
    cur.execute("DELETE FROM cart WHERE user_id=%s", (user_id,))
    mysql.connection.commit()
    cur.close()

    return jsonify({"status":"success","message":"Order placed!", "order_id": order_id})


# ---------------- Get order status ----------------
@app.route('/get_orders')
def get_orders():
    if 'email' not in session:
        return jsonify([])

    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT id, total_amount, status, order_date
        FROM orders
        WHERE user_email=%s
        ORDER BY order_date DESC
    """, (session['email'],))
    orders = cur.fetchall()
    cur.close()

    order_list = []
    for o in orders:
        order_list.append({
            "order_id": o["id"],
            "total": float(o["total_amount"]),
            "status": o["status"],
            "date": o["order_date"].strftime("%Y-%m-%d %H:%M:%S")
        })
    return jsonify(order_list)

@app.route('/order_bill/<int:order_id>')
def order_bill(order_id):
    if 'email' not in session:
        return redirect('/login')

    cur = mysql.connection.cursor()
    # Fetch order info
    cur.execute("SELECT * FROM orders WHERE id=%s AND user_email=%s", (order_id, session['email']))
    order = cur.fetchone()
    if not order:
        cur.close()
        return "Order not found!", 404

    # Fetch order items
    cur.execute("""
        SELECT oi.quantity, oi.price, m.name
        FROM order_items oi
        JOIN menu m ON oi.menu_id = m.id
        WHERE oi.order_id=%s
    """, (order_id,))
    items = cur.fetchall()

    # Fetch customer info from payment_history
    cur.execute("SELECT customer_name, mobile, address FROM payment_history WHERE order_id=%s", (order_id,))
    customer = cur.fetchone()
    cur.close()

    # Add customer info to order object for template
    order['customer_name'] = customer['customer_name']
    order['mobile'] = customer['mobile']
    order['address'] = customer['address']

    return render_template('order_bill.html', order=order, items=items)


@app.route("/payment_success/<int:order_id>")
def payment_success(order_id):
    return render_template("payment_success.html", order_id=order_id)

@app.route("/track_order")
def track_order():
    if 'email' not in session:
        return redirect('/login')

    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # user info
    cur.execute("SELECT id, fullname FROM users WHERE email=%s", (session['email'],))
    user = cur.fetchone()

    # orders
    cur.execute("""
        SELECT id, total_amount, status, order_date
        FROM orders
        WHERE user_email=%s
        ORDER BY order_date DESC
    """, (session['email'],))
    orders = cur.fetchall()

    for order in orders:
        cur.execute("""
            SELECT 
                m.name AS item_name,
                oi.quantity,
                oi.price,
                (oi.quantity * oi.price) AS subtotal
            FROM order_items oi
            JOIN menu m ON oi.menu_id = m.id
            WHERE oi.order_id = %s
        """, (order['id'],))
        order['items'] = cur.fetchall()

    cur.close()
    return render_template(
        "track_order.html",
        orders=orders,
        customer_name=user['fullname']
    )


@app.route("/contact_us", methods=["GET", "POST"])
def contact_us():
    if 'email' not in session or session.get('usertype') != 'customer':
        return jsonify({"status":"error","message":"Please login to contact us!"}), 401

    if request.method == "POST":
        name = request.form.get("name")
        mobile = request.form.get("mobile")
        email = session['email']
        message = request.form.get("message")

        if not name or not mobile or not message:
            return jsonify({"status":"error","message":"All fields are required!"}), 400

        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO contact_messages (name, mobile, email, message)
            VALUES (%s, %s, %s, %s)
        """, (name, mobile, email, message))
        mysql.connection.commit()
        cur.close()

        return jsonify({"status":"success","message":"Thank you! Your message has been submitted."})

    # GET request → render template
    return render_template("contact_us.html")

@app.route('/owner/get_orders')
def owner_get_orders():
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("""
        SELECT 
            o.id,
            o.status,
            p.payment_status,
            o.total_amount AS total,
            u.fullname AS name,
            p.address
        FROM orders o
        JOIN users u ON o.user_id = u.id
        LEFT JOIN payment_history p ON o.id = p.order_id
        ORDER BY o.id DESC
    """)
    rows = cur.fetchall()
    cur.close()

    orders = []
    for r in rows:
        orders.append({
            "id": r["id"],
            "name": r["name"],
            "address": r["address"],
            "total": float(r["total"]),
            "status": r["status"],
            "payment_status": r["payment_status"]
        })
    return jsonify(orders)


@app.route('/owner/complete_order/<int:order_id>', methods=['POST'])
def complete_order(order_id):
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # 🔒 payment check
    cur.execute("""
        SELECT payment_status
        FROM payment_history
        WHERE order_id=%s
    """, (order_id,))
    payment = cur.fetchone()

    if not payment or payment["payment_status"] != "Paid":
        cur.close()
        return jsonify({
            "status": "error",
            "message": "Payment not completed"
        }), 403

    # ✔️ allow complete
    cur.execute("""
        UPDATE orders
        SET status='Completed'
        WHERE id=%s
    """, (order_id,))

    mysql.connection.commit()
    cur.close()
    return jsonify({"status":"success"})


@app.route('/owner/dashboard_data')
def owner_dashboard_data():
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # 1️⃣ Total menus
    cur.execute("SELECT COUNT(*) AS total FROM menu")
    menu_count = cur.fetchone()['total']

    # 2️⃣ Today's PAID orders & income
    cur.execute("""
        SELECT 
            COUNT(o.id) AS orders,
            IFNULL(SUM(o.total_amount),0) AS income
        FROM orders o
        JOIN payment_history p ON o.id = p.order_id
        WHERE DATE(o.created_at) = CURDATE()
          AND p.payment_status = 'Paid'
    """)
    today = cur.fetchone()

    # 3️⃣ Total PAID orders & income
    cur.execute("""
        SELECT 
            COUNT(o.id) AS orders,
            IFNULL(SUM(o.total_amount),0) AS income
        FROM orders o
        JOIN payment_history p ON o.id = p.order_id
        WHERE p.payment_status = 'Paid'
    """)
    total = cur.fetchone()

    # 4️⃣ Orders graph (last 7 days) — PAID only
    cur.execute("""
        SELECT 
            DATE(o.created_at) AS day,
            COUNT(o.id) AS total
        FROM orders o
        JOIN payment_history p ON o.id = p.order_id
        WHERE p.payment_status = 'Paid'
          AND o.created_at >= CURDATE() - INTERVAL 6 DAY
        GROUP BY day
        ORDER BY day
    """)
    orders_graph = cur.fetchall()

    # 5️⃣ Revenue graph (last 7 days) — PAID only
    cur.execute("""
        SELECT 
            DATE(o.created_at) AS day,
            SUM(o.total_amount) AS revenue
        FROM orders o
        JOIN payment_history p ON o.id = p.order_id
        WHERE p.payment_status = 'Paid'
          AND o.created_at >= CURDATE() - INTERVAL 6 DAY
        GROUP BY day
        ORDER BY day
    """)
    revenue_graph = cur.fetchall()

    cur.close()

    return jsonify({
        "menu_count": menu_count,
        "today_orders": today["orders"],
        "today_income": today["income"],
        "total_orders": total["orders"],
        "total_income": total["income"],
        "orders_graph": orders_graph,
        "revenue_graph": revenue_graph
    })

@app.route('/update_owner_profile', methods=['POST'])
def update_owner_profile():
    if 'email' not in session:
        return redirect('/login')

    fullname = request.form['fullname']
    email = request.form['email']
    mobile = request.form['mobile']
    address = request.form['address']
    password = request.form.get('password')

    cur = mysql.connection.cursor()

    if password and password.strip():
        hashed_password = generate_password_hash(password)
        cur.execute("""
            UPDATE users
            SET fullname=%s, email=%s, mobile=%s, address=%s, password=%s
            WHERE email=%s AND usertype='owner'
        """, (fullname, email, mobile, address, hashed_password, session['email']))
    else:
        cur.execute("""
            UPDATE users
            SET fullname=%s, email=%s, mobile=%s, address=%s
            WHERE email=%s AND usertype='owner'
        """, (fullname, email, mobile, address, session['email']))

    mysql.connection.commit()
    cur.close()

    return redirect('/owner_profile')


@app.route('/owner_profile')
def owner_profile():
    if 'email' not in session:
        return redirect('/login')

    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT * FROM users WHERE usertype='owner' LIMIT 1")
    owner = cur.fetchone()
    cur.close()

    return render_template("owner_profile.html", owner=owner)

@app.route("/confirm_payment", methods=["POST"])
def confirm_payment():
    if 'email' not in session:
        return jsonify({"status":"error"}), 401

    data = request.get_json()
    order_id = data.get("order_id")

    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # verify order belongs to user
    cur.execute("""
        SELECT ph.id
        FROM payment_history ph
        JOIN orders o ON ph.order_id = o.id
        WHERE ph.order_id=%s AND o.user_email=%s
    """, (order_id, session['email']))

    record = cur.fetchone()

    if not record:
        cur.close()
        return jsonify({"status":"error","message":"Invalid order"}), 403

    # update payment
    cur.execute("""
        UPDATE payment_history
        SET payment_status='Paid'
        WHERE order_id=%s
    """, (order_id,))

    mysql.connection.commit()
    cur.close()

    return jsonify({"status":"success"})

@app.route("/payment/<int:order_id>")
def payment(order_id):
    if 'email' not in session:
        return redirect('/login')

    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("""
        SELECT * FROM payment_history
        WHERE order_id=%s
    """,(order_id,))
    order = cur.fetchone()
    cur.close()

    if not order:
        return "Invalid Order"

    return render_template("payment.html", order=order)

@app.route("/payment/later", methods=["POST"])
def payment_later():
    data = request.json
    order_id = data["order_id"]

    # already Pending so nothing to update
    return jsonify({"status":"pending"})


@app.route("/customer/pending_payments")
def pending_payments():
    if 'email' not in session:
        return jsonify([])

    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cur.execute("""
        SELECT 
            ph.order_id AS id,
            ph.total_amount
        FROM payment_history ph
        JOIN orders o ON ph.order_id = o.id
        WHERE o.user_email = %s
          AND ph.payment_status = 'Pending'
    """, (session['email'],))

    data = cur.fetchall()
    cur.close()

    return jsonify(data)


@app.route("/pending_payment")
def pending_payment_page():
    if 'email' not in session:
        return redirect('/login')
    return render_template("pending_payment.html")

@app.route('/food')
def food():
    return render_template('Food.html')

@app.route('/customers')
def customers():
    return render_template('customers.html')

@app.route('/orders')
def orders():
    return render_template('orders.html')

@app.route('/about_us')
def about_us():
    return render_template('about_us.html')

@app.route('/owner_logout')
def owner_logout():
    return redirect(url_for('login'))

@app.route('/cart')
def cart():
    return render_template('cart.html')

if __name__ == "__main__":
    app.run(debug=True)
