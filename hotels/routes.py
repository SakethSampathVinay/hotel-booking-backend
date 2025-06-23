# rooms/routes.py

from flask import Blueprint, request, jsonify, current_app
from bson.objectid import ObjectId
from datetime import datetime

room_bp = Blueprint('room', __name__)

@room_bp.route('/add-hotel-room', methods=['POST'])
def add_room():
    mongo = current_app.mongo
    data = request.get_json()
    
    new_room = {
        'hotelName': data['hotelName'],
        'streetAddress': data['streetAddress'],
        'roomType': data['roomType'],
        'pricePerNight': data['pricePerNight'],
        'amenities': data.get('amenities', []),
        'images': data.get('images', []),
        'isAvailable': True,
        'createdAt': datetime.utcnow(),
        'updatedAt': datetime.utcnow()
    }
    result = mongo.db.rooms.insert_one(new_room)
    return jsonify({
        'message': 'Room added successfully',
        'room_id': str(result.inserted_id)
    }), 201

@room_bp.route('/hotels/<room_id>/rooms', methods=['GET'])
def get_rooms_by_hotel(room_id):
    mongo = current_app.mongo
    rooms = mongo.db.rooms.find({'_id': ObjectId(room_id)})
    room_list = []
    for room in rooms:
        room['_id'] = str(room['_id'])
        room['createdAt'] = room['createdAt'].isoformat()
        room_list.append(room)
    return jsonify(room_list), 200

@room_bp.route('/get-rooms', methods = ['GET'])
def get_all_rooms():
    mongo = current_app.mongo
    rooms = mongo.db.rooms.find()
    room_list = []
    for room in rooms:
        room['_id'] = str(room['_id'])
        room['createdAt'] = room['createdAt'].isoformat()
        room_list.append(room)
    return jsonify(room_list), 200