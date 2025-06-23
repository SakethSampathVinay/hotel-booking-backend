from flask import Blueprint, request, jsonify, current_app 
from datetime import datetime 
from bson.objectid import ObjectId 

booking_bp = Blueprint('booking', __name__)

@booking_bp.route('/book-room', methods=['POST', 'OPTIONS'])
def book_room():
    if request.method == 'OPTIONS':
        return jsonify({'message': 'CORS preflight successful'}), 200

    mongo = current_app.mongo
    data = request.get_json()

    booking = {
    'room_id': ObjectId(data['room_id']),
    'guest_count': data['guest_count'],
    'image': data.get('image', ''),
    'name': data.get('name', ''),
    'address': data.get('address', ''),
    'check_in': datetime.strptime(data['check_in'], '%Y-%m-%d'),
    'check_out': datetime.strptime(data['check_out'], '%Y-%m-%d'),
    'created_at': datetime.utcnow()
}


    result = mongo.db.bookings.insert_one(booking)
    return jsonify({
        'message': 'Room booked successfully',
        'booking_id': str(result.inserted_id)
    }), 201 

@booking_bp.route('/get-bookings', methods=['GET'])
def get_bookings():
    mongo = current_app.mongo
    bookings = mongo.db.bookings.find()

    booking_list = []

    for booking in bookings:
        booking_list.append({
            'room_id': str(booking.get('room_id', '')),
            'guest_count': booking.get('guest_count', ''),
            'image': booking.get('image', ''),
            'name': booking.get('name', ''),
            'address': booking.get('address', ''),
            'check_in': booking.get('check_in').strftime('%Y-%m-%d') if booking.get('check_in') else '',
            'check_out': booking.get('check_out').strftime('%Y-%m-%d') if booking.get('check_out') else '',
            'created_at': booking.get('created_at').strftime('%Y-%m-%d %H:%M:%S') if booking.get('created_at') else ''
        })

    return jsonify({'message': 'Bookings retrieved successfully', "bookings": booking_list}), 200
