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

#This is the booking routes file this includes the routes for booking a room, getting bookings, updating payment status,
# cancelling a booking, calculating booking, and sending email notificiations using Brevo

booking_bp = Blueprint('booking', __name__) #creating a blueprint for the booking routes

def send_brevo_email(to_email, username, booking_id, name, address, check_in, price):
    configuration = sib_api_v3_sdk.Configuration() #setting up the configuration for Brevo API
    configuration.api_key['api-key'] = os.getenv("BREVO_API_KEY") #getting the Brevo API key from the environment variables

    api_instance = sib_api_v3_sdk.TransactionalEmailsApi( #creating an instance of the TransactionalEmailsApi
        sib_api_v3_sdk.ApiClient(configuration)
    )

    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail( #creating an instance of the SendSmtpEmail class
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
                    <td>₹{price}</td>
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
        response = api_instance.send_transac_email(send_smtp_email) #sending the email using Brevo API
        print("✅ Email sent:", response)
    except ApiException as e:
        print("❌ Email sending failed:", e) #handling any exceptions that occur while sending the email

@booking_bp.route('/book-room', methods=['POST', 'OPTIONS'])
@jwt_required()
def book_room():
    if request.method == 'OPTIONS': # Handle CORS preflight request
        return jsonify({'message': 'CORS preflight successful'}), 200

    mongo = current_app.mongo #getting the instance of mongodb from the current app context
    data = request.get_json() #getting the json data from the client request
    user_id = get_jwt_identity() #getting the user id from the jwt token

    booking = { #creating a booking dictionary to store the booking data
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
        'created_at': datetime.utcnow(),
        'total_amount': data.get('totalAmount')
        }
    result = mongo.db.bookings.insert_one(booking) #inserting the booking data into the bookings collection in the database
    user = mongo.db.users.find_one({'_id': ObjectId(user_id)}) #finding the user in the users collection using the user id 
    username = user['name']
    useremail = user['email']

    send_brevo_email(useremail, username, str(result.inserted_id), booking['name'], booking['address'], booking['check_in'], booking['total_amount']) #


    return jsonify({ #returning a json response with a success message and the booking id
        'message': 'Room booked successfully',
        'booking_id': str(result.inserted_id)
    }), 201 

@booking_bp.route('/get-bookings', methods=['GET'])
@jwt_required()
def get_bookings():
    mongo = current_app.mongo #getting the instance of mongodb from teh current app context
    user_id = get_jwt_identity() #getting the user id from the jwt token

    bookings = mongo.db.bookings.find({'user': user_id}) #finding the bookings for the user in the bokings collection using the user id

    booking_list = [] #to store the bookings in a list

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
            'totalAmount': int(booking.get('total_amount', 0) or 0)
        })
    
    return jsonify({'message': 'Bookings retrieved successfully', "bookings": booking_list}), 200 #returning a json response with a success message and the list of bookings

@booking_bp.route('/update-pay', methods=['PUT', 'OPTIONS'])
@jwt_required()
def update_pay():
    if request.method == 'OPTIONS':
        return jsonify({'message': 'CORS preflight successful'}), 200

    mongo = current_app.mongo #getting the instance of mongodb from the current app context
    user_id = get_jwt_identity() #getting the user id from the jwt token

    data = request.get_json() #getting the json data from the client

    if not data: #handling the case where the request body is empty
        return jsonify({'error': 'Missing JSON body'}), 400

    booking_id = data.get('booking_id') #getting the booking id from the request data
    status = data.get('status', 'Paid') #getting the status from the request data, default to paid

    if not booking_id: #handling the case where the booking id is not provided
        return jsonify({'error': 'booking_id is required'}), 400

    try:
        result = mongo.db.bookings.update_one( #updating the booking status in the bookings collection using the booking id
            {'_id': ObjectId(booking_id)},
            {'$set': {'status': status}} #setting the status to the provided status
        )
        return jsonify({'message': 'Payment status updated successfully'}), 200 #returning a json response with a success message
    except Exception as e:
        return jsonify({'error': f'Update failed: {str(e)}'}), 500 #handling any exceptions that occur while updating the booking status

@booking_bp.route('/cancel-booking/<booking_id>', methods = ['DELETE', 'OPTIONS'])
@jwt_required()
def cancel_booking(booking_id):
    if request.method == "OPTIONS":
        return jsonify({'message': "CORS preflight successful"}), 200

    mongo = current_app.mongo #getting the instance of mongodb from the current app context
    user_id = get_jwt_identity() #getting the user id from the jwt token

    try:
        booking = mongo.db.bookings.find_one({'_id': ObjectId(booking_id), 'user': user_id}) #finding the booking in the bookings collection using the booking id and user id

        if not booking: #handling the case where the booking is not found or the user is not authorized to cancel the booking
            return jsonify({'message': "Booking not found or unauthorized"}), 404 
        
        if booking.get('status') == "Paid": #checking if the booking status is paid
            return jsonify({'message': "Cannot cancel a paid booking"}), 400 
        
        mongo.db.bookings.update_one({'_id': ObjectId(booking_id)},{'$set': {'status': "Cancelled"}}) #updating the booking status to cancelled in the bookings collection
        
        return jsonify({'message': 'Booking Cancelled Successfully'}), 200 #returning a json response with a success message

    except Exception as e: #handling any exceptions that occur while cancelling the booking
        return jsonify({'error': str(e)}), 500

@booking_bp.route('/calculate-booking', methods = ['POST'])
@jwt_required() #passing the jwt_required decorator to protect the route
def calculate_booking():
    data = request.get_json() #getting the json data from the client request
    mongo = current_app.mongo #getting the instance of mongodb from the current app context

    roomId = data.get('room_id') #getting the room id from the request data
    room_type = data.get('roomType') #getting the room type from the request data
    guest_count = data.get('guest_count') #getting the guest count from the request data
    check_in = data.get('check_in') #getting the check in date from the request data
    check_out = data.get('check_out') #getting the check out date fromm the request data

    try:
        room_obj_id = ObjectId(roomId) #converting the room id to an ObjectId
    except Exception: #handling the case where the room id is not a valid ObjectId
        return jsonify({'message': 'Invalid room ID'}), 400

    if not room_type or not guest_count or not check_in or not check_out: #handling the case where any of the required parameters are missing
        return jsonify({'message': 'Missing required parameters'}), 400
        
    booking = mongo.db.rooms.find_one({'_id': room_obj_id, 'roomType': room_type}, {'_id': 0, 'pricePerNight': 1}) #finding the room in the rooms collection using the room id and room type, returning only the price per night
    if not booking:
        return jsonify({'message': "Room type not found"}), 404
    
    rooms_capacity = { #defining the capacity of each room type
        'Single Bed': 1,
        'Double Bed': 2,
        "Suite": 4
    }

    check_in = datetime.strptime(check_in, "%Y-%m-%d") #converting the check in date to a datetime object
    check_out = datetime.strptime(check_out, "%Y-%m-%d") #converting the check out date to a datetime object

    nights = (check_out - check_in).days #calculating the number of nights between check in and check out
 
    if nights <= 0:
        return jsonify({'message': 'Invalid dates'}), 400 
    
    capacity = rooms_capacity.get(room_type) #getting the capacity of the room type from the rooms_capacity dictionary
    rooms_required = (int(guest_count) + capacity - 1) // capacity #calculating the number of rooms required based on the guest count and room capacity
    price_per_night = booking['pricePerNight'] #getting the price per night from the booking data
    total_price = price_per_night * nights * rooms_required #calculating the total price based on the price per night, number of nights, and number of rooms required
    return jsonify({
        'rooms_required': rooms_required,
        'guest_count': guest_count,
        'nights': nights,
        'price_per_night': price_per_night,
        'total_amount': total_price
    }), 200 #returning a json response with the number of rooms required, guest count, number of nights, price per night, and total amount