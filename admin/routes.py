import os
from flask import Blueprint, request, jsonify, current_app
from bson import ObjectId
from werkzeug.utils import secure_filename
import uuid

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
        })

    return jsonify(dashboard_data), 200

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

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

@admin_bp.route('/add-hotels', methods=['POST'])
def add_hotels():
    mongo = current_app.mongo 

    if 'images' not in request.files:
        return jsonify({'error': 'No image part in the request'}), 400 
    
    images = request.files.getlist('images')

    if len(images) != 4:
        return jsonify({'error': 'Exactly 4 images are required'}), 400 
    
    saved_paths = []

    for image in images :
        if image and allowed_file(image.filename):
            filename = secure_filename(f"{uuid.uuid4().hex}_{image.filename}")
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            image.save(filepath)
            saved_paths.append(filepath)
        else:
            return jsonify({'error': f'Invalid file type: {image.filename}'}), 400 

    hotel_name = request.form.get('hotel_name')
    hotel_type = request.form.get('hotel_type')
    price_per_night = request.form.get('price_per_night')
    amentities = request.form.getlist('amenities')

    if not hotel_name or not hotel_type or not price_per_night or not amentities:
        return jsonify({'error': 'Missing required hotel fields'}), 400

    hotel_data = {
        'images': saved_paths,
        'hotel_name': hotel_name,
        'hotel_type': hotel_type,
        'price_per_night': float(price_per_night),
        'amenities': amentities
    } 

    mongo.db.admin.insert_one(hotel_data)
    
    return jsonify({'message': 'Hotel Added Successfully', 'hotel': hotel_data}), 201

