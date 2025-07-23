from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
from bson.objectid import ObjectId
from flask_jwt_extended import jwt_required, get_jwt_identity
import razorpay 
from flask_cors import cross_origin


payment_bp = Blueprint('payments', __name__) # Blueprint for payment routes

razorpay_client = razorpay.Client(auth = ("rzp_test_L0PKrkZl2dGUmB", 'HQwPn5DMeQiCB1eiiZyGZ1ni')) # Initialize Razorpay client with API key and secret

@payment_bp.route("/api/create-order", methods=['POST', 'OPTIONS']) 
@cross_origin(origin='http://localhost:4200', supports_credentials=True) # Allow CORS for local development
@jwt_required()
def create_order():
    if request.method == 'OPTIONS':
        return jsonify({'message': 'CORS preflight OK'}), 200

    data = request.get_json() # Get the JSON data from the request
    mongo = current_app.mongo # Get the MongoDB instance from the current app context
    user_id = get_jwt_identity() # Get the user ID from the JWT token

    amount = int(data['amount']) * 100 # Convert amount to paise
    room_id = ObjectId(data['room_id']) # Convert room ID to ObjectId

    order = razorpay_client.order.create({ # Create a new order with Razorpay
        'amount': amount,
        'currency': 'INR',
        'payment_capture': 1
    })

    mongo.db.orders.insert_one({ # Insert the order details into the MongoDB collection
        "razorpay_order_id": order["id"],
        "amount": amount,
        "room_id": room_id,
        "user_id": ObjectId(user_id),
        "status": "created",
        "created_at": datetime.utcnow()
    })

    return jsonify(order) # Return the order details as JSON response

@payment_bp.route("/api/confirm-booking", methods=['POST'])
def confirm_booking():
    data = request.get_json() # Get the JSON data from the request
    mongo = current_app.mongo # Get the MongoDB instance from the current app context

    try:
        result = mongo.db.orders.update_one( # Update the order status in the database
            {"razorpay_order_id": data["razorpay_order_id"]},
            {
                "$set": {
                    "status": "paid",
                    "razorpay_payment_id": data["razorpay_payment_id"],
                    "razorpay_signature": data["razorpay_signature"],
                    "paid_at": datetime.utcnow()
                }
            }
        )

        mongo.db.bookings.update_one( # Update the booking status to "Paid"
            {"_id": ObjectId(data["booking_id"])},
            {"$set": {"status": "Paid"}}
        )

        if result.matched_count == 0: # If no order was found with the given Razorpay order ID
            return jsonify({"error": "Order not found"}), 404

        return jsonify({"message": "Booking confirmed and payment recorded"}), 200 # Return success response 

    except Exception as e: # Handle any exceptions that occur during the process
        return jsonify({"error": str(e)}), 500 # Return error response with exception message
