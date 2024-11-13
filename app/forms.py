from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, EmailField, SelectField
from wtforms.validators import DataRequired, Length, IPAddress, Optional
from app.models import User, AKSCluster, VM

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class UserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4)])
    email = EmailField('Email', validators=[DataRequired()])
    password = PasswordField('Password')
    is_admin = BooleanField('Admin User')
    submit = SubmitField('Submit')

class DynatraceEnvironmentForm(FlaskForm):
    environment_name = StringField('Environment Name', validators=[DataRequired()])
    environment_id = StringField('Environment ID', validators=[DataRequired()])
    environment_url = StringField('Environment URL', validators=[DataRequired()])
    environment_api_token = StringField('API Token', validators=[])
    environment_paas_token = StringField('PaaS Token', validators=[])
    user_id = SelectField('Link to User', coerce=int, validators=[DataRequired()])
    is_managed = BooleanField('Managed Environment')
    submit = SubmitField('Save')

    def __init__(self, *args, **kwargs):
        super(DynatraceEnvironmentForm, self).__init__(*args, **kwargs)
        self.user_id.choices = [(user.id, user.username) for user in User.query.all()]

class VMForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    ip_address = StringField('IP Address', validators=[DataRequired()])
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password')
    user_id = SelectField('User', coerce=int, validators=[DataRequired()])
    aks_cluster_id = SelectField('AKS Cluster', coerce=int, choices=[], validators=[Optional()])
    submit = SubmitField('Submit')

    def __init__(self, *args, **kwargs):
        super(VMForm, self).__init__(*args, **kwargs)
        self.user_id.choices = [(u.id, u.username) for u in User.query.all()]
        self.aks_cluster_id.choices = [(0, 'None')] + [(c.id, c.name) for c in AKSCluster.query.all()]

class AKSClusterForm(FlaskForm):
    name = StringField('Cluster Name', validators=[DataRequired()])
    subscription_id = StringField('Subscription ID', validators=[DataRequired()])
    azure_id = StringField('Azure ID', validators=[DataRequired()])
    user_id = SelectField('User', coerce=int, validators=[DataRequired()])
    vm_id = SelectField('VM', coerce=int)
    submit = SubmitField('Submit')

    def __init__(self, *args, **kwargs):
        super(AKSClusterForm, self).__init__(*args, **kwargs)
        self.user_id.choices = [(u.id, u.username) for u in User.query.all()]
        self.vm_id.choices = [(0, 'None')] + [(v.id, v.name) for v in VM.query.all()]
