from flask import Blueprint, request, jsonify, current_app 
from datetime import datetime 
from bson.objectid import ObjectId 
from flask_jwt_extended import jwt_required, get_jwt_identity

booking_bp = Blueprint('booking', __name__)

@booking_bp.route('/book-room', methods=['POST', 'OPTIONS'])
@jwt_required()
def book_room():
    if request.method == 'OPTIONS':
        return jsonify({'message': 'CORS preflight successful'}), 200

    mongo = current_app.mongo
    data = request.get_json()
    user = get_jwt_identity()
    
    print(data)

    booking = {
        'user': user,
        'room_id': ObjectId(data['room_id']),
        'pricePerNight': data.get('pricePerNight'),
        'image': data.get('image', ''),
        'name': data.get('name', ''),
        'address': data.get('address', ''),
        'check_in': datetime.strptime(data['check_in'], '%Y-%m-%d'),
        'check_out': datetime.strptime(data['check_out'], '%Y-%m-%d'),
        'status': 'pending',
        'created_at': datetime.utcnow()
        }
        
    result = mongo.db.bookings.insert_one(booking)


    return jsonify({
        'message': 'Room booked successfully',
        'booking_id': str(result.inserted_id)
    }), 201 


@booking_bp.route('/get-bookings', methods=['GET'])
@jwt_required()
def get_bookings():
    mongo = current_app.mongo
    user_id = get_jwt_identity()

    bookings = mongo.db.bookings.find({'user': user_id})
    print(bookings)

    booking_list = []

    for booking in bookings:
        booking_list.append({
            '_id': str(booking.get('_id', '')),
            'room_id': str(booking.get('room_id', '')),
            'guest_count': booking.get('guest_count', ''),
            'pricePerNight': int(booking.get('pricePerNight', 0) or 0),
            'image': booking.get('image', ''),
            'name': booking.get('name', ''),
            'address': booking.get('address', ''),
            'check_in': booking.get('check_in').strftime('%Y-%m-%d') if booking.get('check_in') else '',
            'check_out': booking.get('check_out').strftime('%Y-%m-%d') if booking.get('check_out') else '',
            'created_at': booking.get('created_at').strftime('%Y-%m-%d %H:%M:%S') if booking.get('created_at') else '',
            'status': booking.get('status', ''),
        })
    
    return jsonify({'message': 'Bookings retrieved successfully', "bookings": booking_list}), 200


@booking_bp.route('/update-pay', methods=['PUT', 'OPTIONS'])
@jwt_required()
def update_pay():
    if request.method == 'OPTIONS':
        return jsonify({'message': 'CORS preflight successful'}), 200

    mongo = current_app.mongo
    user_id = get_jwt_identity()

    data = request.get_json()
    print("🧾 Incoming request body:", data)

    if not data:
        return jsonify({'error': 'Missing JSON body'}), 400

    booking_id = data.get('booking_id')
    status = data.get('status', 'Paid')

    if not booking_id:
        return jsonify({'error': 'booking_id is required'}), 400

    try:
        result = mongo.db.bookings.update_one(
            {'_id': ObjectId(booking_id)},
            {'$set': {'status': status}}
        )
        return jsonify({'message': 'Payment status updated successfully'}), 200
    except Exception as e:
        return jsonify({'error': f'Update failed: {str(e)}'}), 500