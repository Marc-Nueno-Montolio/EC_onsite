from flask.cli import FlaskGroup
from app import create_app, db
from flask_caching import Cache

app = create_app()
cli = FlaskGroup(app)

cache = Cache(config={'CACHE_TYPE': 'simple'})  # Use 'redis' or 'memcached' for production
cache.init_app(app)

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
