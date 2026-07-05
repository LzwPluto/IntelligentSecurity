from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length


class FamilyMemberForm(FlaskForm):
    name = StringField('姓名', validators=[
        DataRequired(message='请输入姓名'),
        Length(max=80, message='姓名不超过80个字符')
    ])
    relationship = StringField('关系', validators=[Length(max=40)])
    phone = StringField('手机号', validators=[Length(max=20)])
    submit = SubmitField('保存')
