from app.database import db
from flask_login import UserMixin
from app.utils.security import generate_password_hash, check_password_hash
from datetime import datetime
import hashlib
from cryptography.fernet import Fernet
from flask import current_app

def get_encryption_key():
    return current_app.config['ENCRYPTION_KEY'].encode()

def encrypt_value(value):
    if not value:
        return None
    f = Fernet(get_encryption_key())
    return f.encrypt(value.encode()).decode()

def decrypt_value(encrypted_value):
    if not encrypted_value:
        return None
    f = Fernet(get_encryption_key())
    return f.decrypt(encrypted_value.encode()).decode()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        # Custom implementation for password hashing
        import hashlib
        self.password_hash = hashlib.sha256(password.encode()).hexdigest()

    def check_password(self, password):
        # Custom implementation for password checking
        return self.password_hash == hashlib.sha256(password.encode()).hexdigest()

class UserProgress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    course_id = db.Column(db.String(50), nullable=False)
    section_id = db.Column(db.String(50), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    user = db.relationship('User', backref='progress')

class SectionCompletion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    course_id = db.Column(db.String(50), nullable=False)
    section_id = db.Column(db.String(50), nullable=False)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'course_id', 'section_id', name='unique_user_section'),
    )

class DynatraceEnvironment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    environment_name = db.Column(db.String(150), nullable=False)
    environment_id = db.Column(db.String(100), unique=True, nullable=False)
    environment_url = db.Column(db.String(200), nullable=False)
    environment_api_token = db.Column(db.String(200), nullable=False)
    environment_paas_token = db.Column(db.String(200), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    is_managed = db.Column(db.Boolean, nullable=False, default=True)
    user = db.relationship('User', backref='dynatrace_environments')

    def __repr__(self):
        return f'<DynatraceEnvironment {self.environment_name}>'
    def environment_base_url(self):
        if self.is_managed:
            return f'{self.environment_url}/e/{self.environment_id}'
        else:
            return f'{self.environment_url}'
    
    def environment_api_endpoint(self):
        if 'https://dynatrace.acceptance.tech.ec.europa.eu' in self.environment_url:
            return f'https://apmactivegate.acceptance.tech.ec.europa.eu/e/{self.environment_id}'
        else:
            return self.environment_base_url()

    @property
    def api_token(self):
        return decrypt_value(self.environment_api_token)
    
    @api_token.setter
    def api_token(self, value):
        self.environment_api_token = encrypt_value(value)
    
    @property
    def paas_token(self):
        return decrypt_value(self.environment_paas_token)
    
    @paas_token.setter
    def paas_token(self, value):
        self.environment_paas_token = encrypt_value(value)

class VM(db.Model):
    __tablename__ = 'vms'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    ip_address = db.Column(db.String(45), nullable=False)
    username = db.Column(db.String(50), nullable=False)
    password = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', name='fk_vm_user'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('vms', lazy=True))

    @property
    def vm_password(self):
        return decrypt_value(self.password)
    
    @vm_password.setter
    def vm_password(self, value):
        self.password = encrypt_value(value)
    
    @property
    def vm_ip(self):
        return decrypt_value(self.ip_address)
    
    @vm_ip.setter
    def vm_ip(self, value):
        self.ip_address = encrypt_value(value)

class AKSCluster(db.Model):
    __tablename__ = 'aks_clusters'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    subscription_id = db.Column(db.String(36), nullable=False)
    azure_id = db.Column(db.String(200), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', name='fk_aks_cluster_user'), nullable=False)
    vm_id = db.Column(db.Integer, db.ForeignKey('vms.id', name='fk_aks_cluster_vm'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('aks_clusters', lazy=True))
    vm = db.relationship('VM', backref=db.backref('aks_cluster', uselist=False))

    def __repr__(self):
        return f'<AKSCluster {self.name}>'

class Deployment(db.Model):
    __tablename__ = 'deployments'
    
    id = db.Column(db.Integer, primary_key=True)
    cluster_id = db.Column(db.Integer, db.ForeignKey('aks_clusters.id', name='fk_deployment_cluster'), nullable=False, unique=True)
    namespace = db.Column(db.String(100), nullable=False, default='easytrade')
    frontend_service = db.Column(db.String(100), nullable=False, default='frontend')
    frontend_ip = db.Column(db.String(100))
    frontend_port = db.Column(db.Integer, default=80)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship with AKS Cluster
    cluster = db.relationship('AKSCluster', backref=db.backref('deployment', uselist=False, cascade='all, delete-orphan'))

    def __repr__(self):
        return f'<Deployment {self.namespace} on {self.cluster.name}>'