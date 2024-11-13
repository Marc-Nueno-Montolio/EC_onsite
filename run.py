from flask.cli import FlaskGroup
from app import create_app, db

app = create_app()
cli = FlaskGroup(app)

@cli.command("create-db")
def create_db():
    db.create_all()
    print("Database tables created")

@cli.command("drop-db")
def drop_db():
    db.drop_all()
    print("Database tables dropped")

if __name__ == '__main__':
    cli()
