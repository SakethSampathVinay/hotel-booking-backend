from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
import google.generativeai as genai
import os
import json
import requests
from bson import ObjectId
import dateparser

chatbot_bp = Blueprint("chatbot", __name__)

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel(model_name="models/gemini-2.5-pro")

def parse_user_intent(message: str):
    prompt = f"""
You are a hotel booking assistant bot. Given a user query, extract the following information in JSON:
- intent: one of ["search_hotels", "book_hotel", "check_amenities", "greetings", "farewell"]
- city: if mentioned
- price: if user mentions price (e.g. under ₹2000)
- hotel: if a specific hotel name is mentioned
- check_in: if booking start date is mentioned
- check_out: if booking end date is mentioned
- room_type: if mentioned (e.g. Single Bed, Double Bed, Suite)
- amenities: if user asks about Wi-Fi, AC, etc.
- booking_id: if user mentions a booking ID
- amount: if user mentions a price to pay
- guest_count: if user mentions number of guests

Use natural language dates (like "tomorrow" or "July 15") if needed.
Respond only with a JSON object.

User query: "{message}"
    """
    response = model.generate_content(prompt)
    cleaned = response.text.strip().strip("```").strip("json").strip()
    return cleaned

@chatbot_bp.route('/chat', methods=['POST'])
@jwt_required()
def chat():
    user_data = request.get_json()
    user_msg = user_data.get("message")
    access_token = request.headers.get("Authorization")
    user_id = get_jwt_identity()

    if not access_token.startswith("Bearer "):
        access_token = f"Bearer {access_token}"

    headers = {"Authorization": access_token}

    try:
        parsed_str = parse_user_intent(user_msg)
        parsed = json.loads(parsed_str)
    except Exception as e:
        return jsonify({"reply": "Sorry, I couldn't understand that. Can you rephrase?"})

    intent = parsed.get("intent")
    db = current_app.mongo.db
    hotels_collection = db.rooms

    if intent == "search_hotels":
        city = parsed.get("city")
        max_price = parsed.get("price")

        query = {}
        if city:
            query["city"] = city
        if max_price:
            max_price_number = int(''.join(filter(str.isdigit, str(max_price))))
            query["pricePerNight"] = {"$lte": max_price_number}

        hotels = list(hotels_collection.find(query))
        hotel_list = [{"hotelName": h["hotelName"], "pricePerNight": h["pricePerNight"]} for h in hotels]

        reply_text = f"Here are hotels under ₹{max_price}:" if max_price else "Here are available hotels:"
        return jsonify({"reply": reply_text, "hotels": hotel_list})

    elif intent == "check_amenities":
        hotel_name = parsed.get("hotel")

        hotel = hotels_collection.find_one({"hotelName": {"$regex": f"^{hotel_name}$", "$options": "i"}})
        if hotel:
            amenities = hotel.get("amenities", [])
            return jsonify({"reply": f"{hotel_name} offers: {', '.join(amenities)}"})
        else:
            return jsonify({"reply": "Sorry, I couldn’t find that hotel."})

    elif intent == "greetings":
        return jsonify({"reply": "Hi! 👋 How can I assist you with your hotel booking today?"})

    elif intent == "farewell":
        return jsonify({"reply": "You're welcome! 😊 Let me know if you need any more help. Have a great day!"})

    elif intent == "book_hotel":
        hotel_name = parsed.get("hotel")
        check_in_str = parsed.get("check_in")
        check_out_str = parsed.get("check_out")
        guest_count = parsed.get("guest_count", 1)
        room_type = parsed.get("room_type", "Double Bed")

        if not hotel_name or not check_in_str or not check_out_str:
            return jsonify({"reply": "Please provide hotel name, check-in and check-out dates to book the hotel."})

        room = hotels_collection.find_one({"hotelName": {"$regex": f"^{hotel_name}$", "$options": "i"}})
        if not room:
            return jsonify({"reply": f"Sorry, I couldn’t find a hotel named '{hotel_name}'."})

        try:
            check_in = dateparser.parse(check_in_str)
            check_out = dateparser.parse(check_out_str)
            if not check_in or not check_out:
                return jsonify({"reply": "⚠️ Please provide valid check-in and check-out dates."})

            nights = (check_out - check_in).days
            if nights <= 0:
                return jsonify({"reply": "❌ Check-out date must be after check-in date."})
            
            room_type = room.get("roomType", "Double Bed")
            rooms_capacity = {"Single Bed": 1, "Double Bed": 2, "Suite": 4}
            capacity = rooms_capacity.get(room_type, 2)
            rooms_required = (int(guest_count) + capacity - 1) // capacity

            price = room.get("pricePerNight", 0)
            total_amount = price * nights * rooms_required

            booking_payload = {
                "user": user_id,
                "room_id": str(room["_id"]),
                "pricePerNight": price,
                "image": room.get("images", [""])[0],
                "name": room.get("hotelName"),
                "address": room.get("streetAddress", ""),
                "guest_count": guest_count,
                "check_in": check_in.strftime('%Y-%m-%d'),
                "check_out": check_out.strftime('%Y-%m-%d'),
                "status": "Pending",
                "created_at": datetime.utcnow().isoformat(),
                "totalAmount": total_amount
            }

            booking_response = requests.post(
                "https://hotel-booking-backend-74ai.onrender.com/book-room",
                headers=headers,
                json=booking_payload
            )

            if booking_response.status_code == 201:
                booking_id = booking_response.json().get("booking_id")
                return jsonify({
                    "reply": f"✅ Booking confirmed at {hotel_name} from {check_in.strftime('%Y-%m-%d')} to {check_out.strftime('%Y-%m-%d')} for {guest_count} guests\n💰 Total: ₹{total_amount}\n🆔 Booking ID: `{booking_id}`"
                })
            else:
                print("Booking API error:", booking_response.text)
                return jsonify({"reply": "❌ Booking failed. Please try again later."})

        except Exception as e:
            print("Booking error:", e)
            return jsonify({"reply": "⚠️ Something went wrong. Please check your inputs or try again."})

    elif intent == "make_payment":
        return jsonify({"reply": "To complete your payment, please go to the *Bookings* page and follow the Razorpay payment process manually."})

    else:
        return jsonify({"reply": "I'm here to help you search, check amenities, and book hotels. Try asking a hotel-related question!"})
