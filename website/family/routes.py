from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from extensions import db
from database.models import FamilyMember
from family.forms import FamilyMemberForm
from auth.utils import homeowner_required

family_bp = Blueprint('family', __name__, url_prefix='/family')


@family_bp.route('/')
@login_required
@homeowner_required
def list_members():
    members = FamilyMember.query.filter_by(user_id=current_user.id).all()
    return render_template('family/list.html', members=members)


@family_bp.route('/add', methods=['GET', 'POST'])
@login_required
@homeowner_required
def add_member():
    form = FamilyMemberForm()
    if form.validate_on_submit():
        member = FamilyMember(
            user_id=current_user.id,
            name=form.name.data,
            relationship=form.relationship.data,
            phone=form.phone.data
        )
        db.session.add(member)
        db.session.commit()
        flash('家人添加成功', 'success')
        return redirect(url_for('family.list_members'))
    return render_template('family/add.html', form=form)


@family_bp.route('/edit/<int:member_id>', methods=['GET', 'POST'])
@login_required
@homeowner_required
def edit_member(member_id):
    member = FamilyMember.query.filter_by(id=member_id, user_id=current_user.id).first_or_404()
    form = FamilyMemberForm(obj=member)
    if form.validate_on_submit():
        member.name = form.name.data
        member.relationship = form.relationship.data
        member.phone = form.phone.data
        db.session.commit()
        flash('家人信息已更新', 'success')
        return redirect(url_for('family.list_members'))
    return render_template('family/edit.html', form=form, member=member)


@family_bp.route('/delete/<int:member_id>', methods=['POST'])
@login_required
@homeowner_required
def delete_member(member_id):
    member = FamilyMember.query.filter_by(id=member_id, user_id=current_user.id).first_or_404()
    db.session.delete(member)
    db.session.commit()
    flash('已删除该家人', 'success')
    return redirect(url_for('family.list_members'))
