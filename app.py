from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager 
from flask_pymongo import PyMongo 
from config import Config  
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from dotenv import load_dotenv
load_dotenv()


from auth.routes import auth as auth_bp
from hotels.routes import room_bp
from bookings.routes import booking_bp
from payments.routes import payment_bp
from userProfile.routes import profile_bp
from admin.routes import admin_bp
from chatbot.routes import chatbot_bp

app = Flask(__name__)
app.config.from_object(Config)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
print("Mongo DB Connected Successfully")


CORS(app, origins=["https://easystay-admin.vercel.app", "https://easystay-snowy.vercel.app", "http://localhost:4200"])
jwt = JWTManager(app)
mongo = PyMongo(app)
app.mongo = mongo

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(room_bp)
app.register_blueprint(booking_bp)
app.register_blueprint(payment_bp)
app.register_blueprint(profile_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(chatbot_bp)

if __name__ == "__main__":
    app.run(debug = True, port = 5000, host = '0.0.0.0')
