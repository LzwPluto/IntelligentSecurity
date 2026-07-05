from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from extensions import db
from database.models import User
from auth.forms import LoginForm, RegisterForm, ChangePasswordForm
from auth.utils import hash_password, verify_password

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and verify_password(form.password.data, user.password_hash):
            login_user(user)
            next_page = request.args.get('next')
            flash('登录成功', 'success')
            return redirect(next_page or url_for('main.dashboard'))
        flash('用户名或密码错误', 'danger')

    return render_template('auth/login.html', form=form)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    form = RegisterForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            password_hash=hash_password(form.password.data),
            role='homeowner',
            phone=form.phone.data,
            email=form.email.data
        )
        db.session.add(user)
        db.session.commit()
        flash('注册成功，请登录', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('已退出登录', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not verify_password(form.old_password.data, current_user.password_hash):
            flash('当前密码错误', 'danger')
        else:
            current_user.password_hash = hash_password(form.new_password.data)
            db.session.commit()
            flash('密码修改成功', 'success')
            return redirect(url_for('auth.profile'))

    return render_template('auth/profile.html', form=form)
