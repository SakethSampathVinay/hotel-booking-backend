import os # Configuration file for the backend application
from dotenv import load_dotenv # Load environment variables from a .env file

load_dotenv() # Load environment variables from the .env file

class Config: # Configuration class to hold application settings
    SECRET_KEY = os.getenv('SECRET_KEY')
    MONGO_URI = os.getenv('MONGO_URI')
    CLOUDINARY_CLOUD_NAME = os.getenv('CLOUDINARY_CLOUD_NAME')
    CLOUDINARY_API_KEY = os.getenv('CLOUDINARY_API_KEY')
    CLOUDINARY_API_SECRET = os.getenv('CLOUDINARY_API_SECRET')