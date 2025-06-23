from flask import Blueprint, request, jsonify
from flask_bcrypt import Bcrypt 
from flask_jwt_extended import create_access_token
from datetime import timedelta 

auth = Blueprint('auth', __name__)
bcrypt = Bcrypt()
mongo = None 

@auth.route('/signup', methods = ['POST'])
def signup():
    data = request.get_json()

    if not data.get('name') or not data or not data.get('email') or not data.get('password'):
        return jsonify({'message: ': 'Missing name or email or password'})

    if mongo.db.users.find_one({'email': data['email']}):
        return jsonify({'message': 'Email already exists'}), 409 
    
    hashed_password = bcrypt.generate_password_hash(data['password']).decode('utf-8')
    mongo.db.users.insert_one({
        'name': data['name'],
        'email': data['email'],
        'password': hashed_password
    })
    return jsonify({'message': 'User created successfully'}), 201

@auth.route('/login', methods = ['POST'])
def login():
    data = request.get_json()

    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'message': 'Missing email or password'}), 400

    user = mongo.db.users.find_one({
        'email': data['email']
    })

    if user and bcrypt.check_password_hash(user['password'], data['password']):
        token = create_access_token(identity = str(user['_id']), expires_delta = timedelta(days = 1))
        return jsonify({'token': token}), 200 
    return jsonify({'message': "Invalid credentails"}), 401 

