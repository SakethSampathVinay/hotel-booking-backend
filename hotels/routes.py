from flask import Blueprint, request, jsonify, current_app
from bson.objectid import ObjectId
from datetime import datetime

room_bp = Blueprint('room', __name__)

@room_bp.route('/add-hotel-room', methods=['POST'])
def add_room():
    mongo = current_app.mongo # Get the MongoDB instance from the current app context
    data = request.get_json() # Get the JSON data from the request
    new_room = {
        'hotelName': data['hotelName'],
        'streetAddress': data['streetAddress'],
        'roomType': data['roomType'],
        'pricePerNight': data['pricePerNight'],
        'amenities': data.get('amenities', []),
        'images': data.get('images', []),
        'isAvailable': True,
    } # Create a new room dictionary with the provided data
    result = mongo.db.rooms.insert_one(new_room) # Insert the new room into the MongoDB collection
    return jsonify({ # Return a success message and the ID of the new room
        'message': 'Room added successfully',
        'room_id': str(result.inserted_id)
    }), 201

@room_bp.route('/get-rooms', methods = ['GET'])
def get_all_rooms():
    mongo = current_app.mongo # Get the MongoDB instance from the current app context
    rooms = mongo.db.rooms.find({}) # Find all rooms in the database

    if not rooms: # If no rooms are found, return a 404 error
        return jsonify({'message': 'No rooms found'}), 404

    room_list = [] # Prepare a list to hold room data
    for room in rooms:  # Iterate through each room
        room['_id'] = str(room['_id']) # Convert ObjectId to string for JSON serialization
        room_list.append(room) # Append the room data to the list
    return jsonify(room_list), 200 # Return the list of rooms as a JSON response