from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import get_jwt_identity
from bson import ObjectId

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/dashboard', methods=['GET'])
def dashboard():
    mongo = current_app.mongo

    bookings = list(mongo.db.bookings.find({}, {
        'user': 1,
        'name': 1,
        'pricePerNight': 1,
        'status': 1,
        '_id': 0
    }))

    total_count = len(bookings)
    total_amount = 0
    for booking in bookings:
        total_amount += booking.get('pricePerNight', 0)

    user_ids = []
    for booking in bookings:
        try:
            user_ids.append(ObjectId(booking['user']))
        except:
            pass

    users = mongo.db.users.find(
        {'_id': {'$in': user_ids}},
        {'_id': 1, 'name': 1}
    )

    user_id_to_name = {str(user['_id']): user['name'] for user in users}

    dashboard_data = []
    for booking in bookings:
        user_id = str(booking['user'])
        dashboard_data.append({
            'user_name': user_id_to_name.get(user_id, 'Unknown'),
            'hotel_name': booking.get('name', 'N/A'),
            'amount': booking.get('pricePerNight', 0),
            'payment_status': booking.get('status', 'Unknown'),
            'total_amount': total_amount,
            'count': total_count,
        })

    return jsonify({'summary': {
        'total_bookings': total_count,
        'total_amount': total_amount
    },
    'bookings': dashboard_data}), 200

@admin_bp.route('/booking-summary', methods=['GET'])
def booking_summary():
    mongo = current_app.mongo

    bookings = list(mongo.db.bookings.find({}, {'pricePerNight': 1}))

    total_bookings = len(bookings)
    total_amount = 0 
    for b in bookings:
        total_amount += b.get('pricePerNight', 0)
    
    return jsonify({
        'total_bookings': total_bookings,
        'total_amount': total_amount
    }), 200