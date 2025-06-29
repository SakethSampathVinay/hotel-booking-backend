from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
from bson.objectid import ObjectId
from flask_jwt_extended import jwt_required, get_jwt_identity
import razorpay 
from flask_cors import cross_origin


payment_bp = Blueprint('payments', __name__)

razorpay_client = razorpay.Client(auth = ("rzp_test_L0PKrkZl2dGUmB", 'HQwPn5DMeQiCB1eiiZyGZ1ni'))

@payment_bp.route("/api/create-order", methods=['POST', 'OPTIONS'])
@cross_origin(origin='http://localhost:4200', supports_credentials=True)
@jwt_required()
def create_order():
    if request.method == 'OPTIONS':
        return jsonify({'message': 'CORS preflight OK'}), 200

    data = request.get_json()
    mongo = current_app.mongo
    user_id = get_jwt_identity()

    amount = int(data['amount']) * 100
    room_id = ObjectId(data['room_id'])

    order = razorpay_client.order.create({
        'amount': amount,
        'currency': 'INR',
        'payment_capture': 1
    })

    mongo.db.orders.insert_one({
        "razorpay_order_id": order["id"],
        "amount": amount,
        "room_id": room_id,
        "user_id": ObjectId(user_id),
        "status": "created",
        "created_at": datetime.utcnow()
    })

    return jsonify(order)

@payment_bp.route("/api/confirm-booking", methods=['POST'])
def confirm_booking():
    data = request.get_json()
    mongo = current_app.mongo

    try:
        result = mongo.db.orders.update_one(
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

        mongo.db.bookings.update_one(
            {"_id": ObjectId(data["booking_id"])},
            {"$set": {"status": "Paid"}}
        )

        if result.matched_count == 0:
            return jsonify({"error": "Order not found"}), 404

        return jsonify({"message": "Booking confirmed and payment recorded"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
