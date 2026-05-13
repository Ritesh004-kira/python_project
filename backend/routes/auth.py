from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from backend.models.database import db, User
from werkzeug.security import generate_password_hash, check_password_hash

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email    = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session['user_id']   = user.id
            session['user_name'] = user.name
            return redirect(url_for('main.index'))
        flash('Invalid email or password.')
    return render_template('login.html')


@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name     = request.form.get('name', '').strip()
        email    = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        if User.query.filter_by(email=email).first():
            flash('An account with that email already exists.')
            return redirect(url_for('auth.signup'))
        new_user = User(name=name, email=email,
                        password=generate_password_hash(password))
        db.session.add(new_user)
        db.session.commit()
        flash('Account created! Please log in.')
        return redirect(url_for('auth.login'))
    return render_template('signup.html')


@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('main.index'))
