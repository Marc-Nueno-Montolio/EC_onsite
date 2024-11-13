from app import create_app, db
from app.models import User

app = create_app()

def create_admin():
    with app.app_context():
        # Check if admin already exists
        admin = User.query.filter_by(email='admin@example.com').first()
        if admin:
            print("Admin user already exists!")
            return

        # Create admin user
        admin = User(
            username='admin',
            email='admin@example.com',
            is_admin=True
        )
        from getpass import getpass
        password = getpass("Enter admin password: ")
        admin.set_password(password)  # Set the password using the User model method
        
        # Add to database
        db.session.add(admin)
        db.session.commit()
        
        print("Admin user created successfully!")

if __name__ == '__main__':
    create_admin()