from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager 
from flask_pymongo import PyMongo 
from config import Config  

from auth.routes import auth as auth_bp
from hotels.routes import room_bp
from bookings.routes import booking_bp

app = Flask(__name__)
app.config.from_object(Config)

CORS(app, resources={r"/*": {"origins": "http://localhost:4200"}}, supports_credentials=True)
jwt = JWTManager(app)
mongo = PyMongo(app)
app.mongo = mongo

app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(room_bp)
app.register_blueprint(booking_bp)

if __name__ == "__main__":
    app.run(debug = True, port = 5000, host = '0.0.0.0')