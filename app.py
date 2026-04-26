import os
import sqlite3
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from model_utils import predict_disease, set_saved_model_path

app = Flask(__name__)
app.secret_key = "your_secret_key_here"
app.config["UPLOAD_FOLDER"] = "uploads"
app.config["MODEL_FOLDER"] = "uploads/models"
app.config["ALLOWED_EXTENSIONS"] = {"png", "jpg", "jpeg"}
app.config["ALLOWED_MODEL_EXTENSIONS"] = {"pth"}

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
os.makedirs(app.config["MODEL_FOLDER"], exist_ok=True)

DB_NAME = "apple_leaf.db"


def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS farmers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS admin (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in app.config["ALLOWED_EXTENSIONS"]


def allowed_model_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in app.config["ALLOWED_MODEL_EXTENSIONS"]


def farmer_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "farmer_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


def admin_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "admin_id" not in session:
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated_function


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = generate_password_hash(request.form["password"])

        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO farmers (name, email, password) VALUES (?, ?, ?)", (name, email, password))
            conn.commit()
            flash("Registration successful. Please login.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Email already registered.", "danger")
        finally:
            conn.close()

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db_connection()
        user = conn.execute("SELECT * FROM farmers WHERE email = ?", (email,)).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session.clear()
            session["farmer_id"] = user["id"]
            session["farmer_name"] = user["name"]
            return redirect(url_for("farmer_dashboard"))
        else:
            flash("Invalid farmer login credentials.", "danger")

    return render_template("login.html")


@app.route("/admin-login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db_connection()
        admin = conn.execute("SELECT * FROM admin WHERE username = ?", (username,)).fetchone()
        conn.close()

        if admin and check_password_hash(admin["password"], password):
            session.clear()
            session["admin_id"] = admin["id"]
            session["admin_username"] = admin["username"]
            return redirect(url_for("admin_dashboard"))
        else:
            flash("Invalid admin login credentials.", "danger")

    return render_template("admin_login.html")


@app.route("/farmer-dashboard", methods=["GET", "POST"])
@farmer_login_required
def farmer_dashboard():
    if request.method == "POST":
        if "leaf_image" not in request.files:
            flash("No file selected.", "danger")
            return redirect(request.url)

        file = request.files["leaf_image"]
        if file.filename == "":
            flash("Please choose an image.", "danger")
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(filepath)

            try:
                result = predict_disease(filepath)
                return render_template("result.html", result=result, image_path=filepath)
            except Exception as e:
                flash(f"Prediction failed: {str(e)}", "danger")
                return redirect(url_for("farmer_dashboard"))
        else:
            flash("Only png, jpg, jpeg files are allowed.", "danger")

    return render_template("farmer_dashboard.html")


@app.route("/admin-dashboard", methods=["GET", "POST"])
@admin_login_required
def admin_dashboard():
    if request.method == "POST":
        if "model_file" not in request.files:
            flash("No model file selected.", "danger")
            return redirect(request.url)

        file = request.files["model_file"]
        if file.filename == "":
            flash("Please choose a model file.", "danger")
            return redirect(request.url)

        if file and allowed_model_file(file.filename):
            filename = secure_filename(file.filename)
            model_path = os.path.join(app.config["MODEL_FOLDER"], filename)
            file.save(model_path)
            set_saved_model_path(model_path)
            flash("New model uploaded successfully.", "success")
        else:
            flash("Only .pth model files are allowed.", "danger")

    return render_template("admin_dashboard.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


if __name__ == "__main__":
    init_db()
    app.run(debug=True)