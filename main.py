from flask import Flask, render_template, request, flash, session, redirect
import json
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import math
from werkzeug.utils import secure_filename
from flask_mail import Mail, Message
from dotenv import load_dotenv


load_dotenv()  # Load environment variables
SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY')

# Load config
with open('config.json', 'r') as c:
    params = json.load(c)["params"]


local_server = params.get("local_server") == "True"

app = Flask(__name__)
app.secret_key = 'super-secret-key'
app.config['UPLOAD_FOLDER'] = params['upload_location']

# Database config
if local_server:
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///nexapost.db"
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = params['prod_uri']

db = SQLAlchemy(app)

# ✅ Flask-Mail config
app.config.update(
    MAIL_SERVER='smtp.sendgrid.net',
    MAIL_PORT=587,
    MAIL_USE_TLS=True,
    MAIL_USERNAME='apikey',
    MAIL_PASSWORD=SENDGRID_API_KEY
)
mail = Mail(app)

# Database models
class Contact(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(50), nullable=False)
    phone_num = db.Column(db.String(15), nullable=False)
    msg = db.Column(db.String(120), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)

class Posts(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(50), nullable=False)
    tagline = db.Column(db.String(50), nullable=False)
    slug = db.Column(db.String(21), nullable=False, unique=True)
    content = db.Column(db.String(500), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    img_url = db.Column(db.String(200), nullable=True)


# Routes
@app.route("/")
def index():
    posts = Posts.query.order_by(Posts.date.desc()).all()
    posts_per_page = int(params['no_of_post'])
    last = math.ceil(len(posts) / posts_per_page)

    page = request.args.get('page')
    page = int(page) if page and str(page).isnumeric() else 1

    posts = posts[(page - 1) * posts_per_page: page * posts_per_page]

    if page == 1:
        prev = "#"
        next = "/?page=" + str(page + 1)
    elif page == last:
        prev = "/?page=" + str(page - 1)
        next = "#"
    else:
        prev = "/?page=" + str(page - 1)
        next = "/?page=" + str(page + 1)

    return render_template("index.html", params=params, posts=posts, prev=prev, next=next)

# @app.route("/post/<string:post_slug>", methods=['GET'])
# def post_route(post_slug):
#     post = Posts.query.filter_by(slug=post_slug).first_or_404()
#     return render_template("post.html", params=params, post=post)


@app.route("/about")
def about():
    return render_template("about.html", params=params)

@app.route("/dashboard", methods=['GET', 'POST'])
def dashboard():
    if 'username' in session and session['username'] == params['admin_user']:
        posts = Posts.query.order_by(Posts.date.desc()).all()
        return render_template('dashboard.html', params=params, posts=posts)

    if request.method == 'POST':
        username = request.form.get("username")
        password = request.form.get("password")

        if username == params['admin_user'] and password == params['admin_password']:
            session['username'] = username
            flash("Login successful", "success")
            posts = Posts.query.order_by(Posts.date.desc()).all()
            return render_template("dashboard.html", params=params, posts=posts)
        else:
            flash("Invalid username or password", "danger")

    return render_template("login.html", params=params)

@app.route("/edit/<string:sno>", methods=['GET', 'POST'])
def edit(sno):
    if 'username' in session and session['username'] == params['admin_user']:
        if sno == '0':
            post = None
        else:
            post = Posts.query.filter_by(sno=sno).first()
            if not post:
                flash("Post not found", "danger")
                return redirect('/dashboard')

        if request.method == 'POST':
            title = request.form['title']
            tagline = request.form['tagline']
            slug = request.form['slug']
            content = request.form['content']
            img_url = request.form['img_url']

            if post is None:
                # Add new post
                post = Posts(
                    title=title,
                    tagline=tagline,
                    slug=slug,
                    content=content,
                    img_url=img_url,
                    date=datetime.utcnow()
                )
                db.session.add(post)
            else:
                # Update existing post
                post.title = title
                post.tagline = tagline
                post.slug = slug
                post.content = content
                post.img_url = img_url

            db.session.commit()
            flash("Post saved successfully", "success")
            return redirect('/dashboard')

        return render_template("edit.html", params=params, post=post, sno=sno)

    flash("Please log in to access the dashboard", "warning")
    return redirect('/dashboard')

@app.route("/post/<string:post_slug>")
def post_route(post_slug):
    post = Posts.query.filter_by(slug=post_slug).first()
    if not post:
        return f"Post with slug '{post_slug}' not found in database."
    return render_template("post.html", params=params, post=post)

@app.route("/uploader", methods=['GET', 'POST'])
def uploader():
    if 'username' in session and session['username'] == params['admin_user']:

        if request.method == 'POST':
          f=request.files['file1']
          os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
          f.save(os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(f.filename)))
        return "uploaded successfully"

@app.route("/contact", methods=['GET','POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get("name")
        email = request.form.get("email")
        phone = request.form.get("phone")
        message = request.form.get("message")

        # Save in DB
        entry = Contact(name=name, email=email, phone_num=phone, msg=message)
        db.session.add(entry)
        db.session.commit()

        msg = Message(
            subject=f"New message from {name}",
            sender="menukakarki201@gmail.com",
            recipients=["menukakarki201@gmail.com"],
            body=f"Name: {name}\nEmail: {email}\nPhone: {phone}\n\nMessage:\n{message}"
        )
        mail.send(msg)

        flash("Message sent successfully!", "success")

    return render_template("contact.html", params=params)

@app.route("/logout")
def logout():
    session.pop('username', None)
    flash("You have been logged out", "info")
    return redirect('/dashboard')

@app.route("/delete/<string:sno>", methods=['GET','POST'])
def delete(sno):
    if 'username' in session and session['username'] == params['admin_user']:
     post = Posts.query.filter_by(sno=sno).first()
     db.session.delete(post)
     db.session.commit()

     return redirect('/dashboard')

if __name__ == "__main__":
    app.run(debug=True)
