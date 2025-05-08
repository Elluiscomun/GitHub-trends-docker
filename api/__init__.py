from flask import Flask

def create_app():
    app = Flask(__name__)
    app.config['DATABASE'] = 'db/database.sqlite'

    with app.app_context():
        from database import init_db
        init_db()

    from routes import register_routes
    register_routes(app)

    return app