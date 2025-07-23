from flask import Blueprint, request, jsonify, current_app
from flask_bcrypt import Bcrypt 
from flask_jwt_extended import create_access_token
from datetime import timedelta 

auth = Blueprint('auth', __name__) #creating a blueprint for the auth routes
bcrypt = Bcrypt() #to hash passwords
mongo = None #to store the mongo instance

@auth.route('/signup', methods=['POST'])
def signup():
    mongo = current_app.mongo # get the mongo instance from the current app context
    data = request.get_json() # get the json data from the client

    if not data.get('name') or not data.get('email') or not data.get('password') or not data.get('phone'):
        return jsonify({'message': 'Missing name or email or password or phone'}), 400 #implementing basic validation

    if mongo.db.users.find_one({'email': data['email']}): #checking if the email is already exits in the database
        return jsonify({'message': 'Email already exists'}), 409 #if email already exists, it will return an error message
    
    hashed_password = bcrypt.generate_password_hash(data['password']).decode('utf-8') #hashing the password using bcrypt

    result = mongo.db.users.insert_one({
        'name': data['name'],
        'email': data['email'],
        'phone': data['phone'],
        'password': hashed_password
    }) #inserting into the users collection in the database

    user_id = result.inserted_id #getting the inserted user id

    token = create_access_token(identity=str(user_id), expires_delta=timedelta(hours=12)) #creating a JWT token for the user with an expire time for 12 hours with the user id as the identity

    return jsonify({'message': 'User created successfully', 'token': token}), 201 #returning a success message with a token

@auth.route('/login', methods = ['POST'])
def login():
    mongo = current_app.mongo #getting the instance of mongo from the current app context
    data = request.get_json() #getting the data from the client 

    if not data or not data.get('email') or not data.get('password'): #adding basic validation to check if the email and password is presnt in the request
        return jsonify({'message': 'Missing email or password'}), 400 #returning an error message if email or password is not present

    user = mongo.db.users.find_one({ #checking if the user exists in the database
        'email': data['email']
    })

    if user and bcrypt.check_password_hash(user['password'], data['password']): #checking if the user exists and if the hashed password matches the password provided by the user
        token = create_access_token(identity=str(user['_id']), expires_delta=timedelta(hours=12)) #if the user exists and the password matches it will create a jwt totken with the user identity and an expiry time of 12 hours 
        return jsonify({'token': token}), 200 #returning the json response with the token
    return jsonify({'message': "Invalid credentails"}), 401 #if the user does not exist or the password does not match, it will return an error message with a 401 status code 