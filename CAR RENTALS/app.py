from flask import Flask, render_template, request, redirect, session
import sqlite3
import datetime

app = Flask(__name__)
app.secret_key = "super_secret_key_123"

def get_db():
    conn = sqlite3.connect("pricing.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS owner (
            id INTEGER PRIMARY KEY,
            username TEXT,
            password TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS cars (
            id INTEGER PRIMARY KEY,
            name TEXT,
            image TEXT,
            daily_price REAL,
            gps_price REAL,
            extra_driver_price REAL,
            available INTEGER
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY,
            car_id INTEGER,
            days INTEGER,
            gps INTEGER,
            extra_driver INTEGER,
            total REAL,
            created_at TEXT,
            FOREIGN KEY(car_id) REFERENCES cars(id)
        )
    """)

    # default owner
    if conn.execute("SELECT COUNT(*) AS c FROM owner").fetchone()["c"] == 0:
        conn.execute("INSERT INTO owner (username, password) VALUES ('admin', 'admin123')")

    conn.commit()
    conn.close()

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = request.form["username"]
        pw = request.form["password"]

        conn = get_db()
        owner = conn.execute("SELECT * FROM owner WHERE username=? AND password=?", (user, pw)).fetchone()
        conn.close()

        if owner:
            session["owner"] = True
            return redirect("/owner")
        else:
            return render_template("login.html", error="Invalid credentials")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/owner", methods=["GET", "POST"])
def owner_dashboard():
    if "owner" not in session:
        return redirect("/login")

    conn = get_db()

    if request.method == "POST":
        conn.execute("""
            UPDATE cars SET daily_price=?, gps_price=?, extra_driver_price=?, available=?
            WHERE id=?
        """, (
            request.form["daily_price"],
            request.form["gps_price"],
            request.form["extra_driver_price"],
            request.form["available"],
            request.form["car_id"]
        ))
        conn.commit()

    cars = conn.execute("SELECT * FROM cars").fetchall()
    conn.close()

    return render_template("owner_dashboard.html", cars=cars)

@app.route("/owner/cars", methods=["GET", "POST"])
def manage_cars():
    if "owner" not in session:
        return redirect("/login")

    conn = get_db()

    if request.method == "POST":
        conn.execute("""
            INSERT INTO cars (name, image, daily_price, gps_price, extra_driver_price, available)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            request.form["name"],
            request.form["image"],
            request.form["daily_price"],
            request.form["gps_price"],
            request.form["extra_driver_price"],
            request.form["available"]
        ))
        conn.commit()

    cars = conn.execute("SELECT * FROM cars").fetchall()
    conn.close()

    return render_template("cars.html", cars=cars)

@app.route("/owner/analytics")
def analytics():
    if "owner" not in session:
        return redirect("/login")

    conn = get_db()

    total_revenue = conn.execute("SELECT SUM(total) AS rev FROM bookings").fetchone()["rev"]
    total_bookings = conn.execute("SELECT COUNT(*) AS c FROM bookings").fetchone()["c"]

    revenue_per_car = conn.execute("""
        SELECT cars.name, SUM(bookings.total) AS rev
        FROM bookings
        JOIN cars ON bookings.car_id = cars.id
        GROUP BY cars.id
    """).fetchall()

    most_rented = conn.execute("""
        SELECT cars.name, COUNT(bookings.id) AS cnt
        FROM bookings
        JOIN cars ON bookings.car_id = cars.id
        GROUP BY cars.id
        ORDER BY cnt DESC
        LIMIT 1
    """).fetchone()

    conn.close()

    return render_template("analytics.html",
                           total_revenue=total_revenue,
                           total_bookings=total_bookings,
                           revenue_per_car=revenue_per_car,
                           most_rented=most_rented)

@app.route("/", methods=["GET", "POST"])
def booking():
    conn = get_db()
    cars = conn.execute("SELECT * FROM cars WHERE available=1").fetchall()

    if request.method == "POST":
        car_id = request.form["car_id"]
        days = int(request.form["days"])
        gps = 1 if "gps" in request.form else 0
        extra_driver = 1 if "extra_driver" in request.form else 0

        car = conn.execute("SELECT * FROM cars WHERE id=?", (car_id,)).fetchone()

        subtotal = car["daily_price"] * days
        if gps: subtotal += car["gps_price"]
        if extra_driver: subtotal += car["extra_driver_price"]

        total = subtotal

        conn.execute("""
            INSERT INTO bookings (car_id, days, gps, extra_driver, total, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (car_id, days, gps, extra_driver, total, datetime.datetime.now()))
        conn.commit()

        conn.close()
        return render_template("booking.html", cars=cars, message="Booking successful!")

    conn.close()
    return render_template("booking.html", cars=cars)

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
