from flask import Blueprint, request, jsonify, current_app 
from datetime import datetime 
from bson.objectid import ObjectId 
from flask_jwt_extended import jwt_required, get_jwt_identity
from sib_api_v3_sdk.rest import ApiException
import sib_api_v3_sdk
from pprint import pprint
from dotenv import load_dotenv
import os

load_dotenv()


booking_bp = Blueprint('booking', __name__)

def send_brevo_email(to_email, username, booking_id, name, address, check_in, price):
    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key['api-key'] = os.getenv("BREVO_API_KEY")

    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
        sib_api_v3_sdk.ApiClient(configuration)
    )

    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
        to=[{"email": to_email, "name": username}],
        sender={"name": "EasyStay", "email": "sakethsampath2006@gmail.com"},
        subject="🏨 Your Hotel Booking is Confirmed!",
        html_content=f"""
            <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <h2 style="color: #2C3E50;">Hello <span>{username}</span>,</h2>

                <p style="font-size: 16px;">
                <strong>Thank you</strong> for your booking! Below are your booking details:
                </p>

                <table style="font-size: 16px; margin-top: 10px;">
                <tr>
                    <td><strong>🔖 Booking ID:</strong></td>
                    <td>{booking_id}</td>
                </tr>
                <tr>
                    <td><strong>🏨 Hotel Name:</strong></td>
                    <td>{name}</td>
                </tr>
                <tr>
                    <td><strong>📍 Location:</strong></td>
                    <td>{address}</td>
                </tr>
                <tr>
                    <td><strong>📅 Check-in Date:</strong></td>
                    <td>{check_in.strftime('%d %B %Y')}</td>
                </tr>
                <tr>
                    <td><strong>💰 Booking Amount:</strong></td>
                    <td>${price}</td>
                </tr>
                </table>

                <p style="margin-top: 20px; font-size: 16px;">
                We look forward to welcoming you to <strong>{name}</strong>.<br>
                If you need to make any changes, feel free to contact us.
                </p>

                <p style="font-size: 16px;">Best regards,<br><strong>The EasyStay Team</strong></p>
            </body>
            </html>
            """
            )
    try:
        response = api_instance.send_transac_email(send_smtp_email)
        print("✅ Email sent:", response)
    except ApiException as e:
        print("❌ Email sending failed:", e)


@booking_bp.route('/book-room', methods=['POST', 'OPTIONS'])
@jwt_required()
def book_room():
    if request.method == 'OPTIONS':
        return jsonify({'message': 'CORS preflight successful'}), 200

    mongo = current_app.mongo
    data = request.get_json()
    user_id = get_jwt_identity()
    
    print(data)

    booking = {
        'user': user_id,
        'room_id': ObjectId(data['room_id']),
        'pricePerNight': data.get('pricePerNight'),
        'image': data.get('image', ''),
        'name': data.get('name', ''),
        'address': data.get('address', ''),
        'guest_count': data.get('guest_count', ''),
        'check_in': datetime.strptime(data['check_in'], '%Y-%m-%d'),
        'check_out': datetime.strptime(data['check_out'], '%Y-%m-%d'),
        'status': 'pending',
        'created_at': datetime.utcnow()
        }
    result = mongo.db.bookings.insert_one(booking)
    user = mongo.db.users.find_one({'_id': ObjectId(user_id)})
    username = user['name']
    useremail = user['email']

    send_brevo_email(useremail, username, str(result.inserted_id), booking['name'], booking['address'], booking['check_in'], booking['pricePerNight'])


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
    print("Incoming request body:", data)

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

@booking_bp.route('/cancel-booking/<booking_id>', methods = ['DELETE', 'OPTIONS'])
@jwt_required()
def cancel_booking(booking_id):
    if request.method == "OPTIONS":
        return jsonify({'message': "CORS prelight successfully"}), 201 
    
    mongo = current_app.mongo
    user_id = get_jwt_identity()

    try:
        booking = mongo.db.bookings.find_one({'_id': ObjectId(booking_id), 'user': user_id})

        if not booking:
            return jsonify({'message': "Booking not found or unauthorized"}), 404
        
        if booking.get('status') == "Paid":
            return jsonify({'message': "Cannot cancel a paid booking"}), 400 
        
        mongo.db.bookings.update_one({'_id': ObjectId(booking_id)},{'$set': {'status': "Cancelled"}})
        
        return jsonify({'message': 'Booking Cancelled Successfully'}), 200 

    except Exception as e:
        return jsonify({'error': str(e)}), 500