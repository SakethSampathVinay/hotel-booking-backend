from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, timedelta
import google.generativeai as genai
import os
import json
import requests
from bson import ObjectId

chatbot_bp = Blueprint("chatbot", __name__)

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

model = genai.GenerativeModel(model_name="models/gemini-2.5-pro")

def parse_user_intent(message: str):
    prompt = f"""
You are a hotel booking assistant bot. Given a user query, extract the following information in JSON:
- intent: one of ["search_hotels", "book_hotel", "check_amenities"]
- city: if mentioned
- price: if user mentions price (e.g. under ₹2000)
- hotel: if a specific hotel name is mentioned
- date: if a booking date is mentioned
- amenities: if user asks about Wi-Fi, AC, etc.
- booking_id: if user mentions a booking ID
- amount: if user mentions a price to pay

User query: "{message}"
Respond only with a JSON object.
    """
    response = model.generate_content(prompt)
    
    cleaned = response.text.strip().strip("```").strip("json").strip()
    return cleaned

@chatbot_bp.route('/chat', methods=['POST'])
def chat():
    user_data = request.get_json()
    user_msg = user_data.get("message")

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
        return jsonify({
            "reply": reply_text,
            "hotels": hotel_list
        })

    elif intent == "check_amenities":
        hotel_name = parsed.get("hotel")

        hotel = hotels_collection.find_one({
            "hotelName": {"$regex": f"^{hotel_name}$", "$options": "i"}
        })

        if hotel:
            amenities = hotel.get("amenities", [])
            return jsonify({"reply": f"{hotel_name} offers: {', '.join(amenities)}"})
        else:
            return jsonify({"reply": "Sorry, I couldn’t find that hotel."})
    
    elif intent == "book_hotel":
        hotel_name = parsed.get("hotel")
        date = parsed.get("date")

        if not hotel_name or not date:
            return jsonify({"reply": "Please provide the hotel name and date to proceed with booking."})

        hotels_collection = current_app.mongo.db.rooms
        room = hotels_collection.find_one({"hotelName": {"$regex": f"^{hotel_name}$", "$options": "i"}})

        if not room:
            return jsonify({"reply": f"Sorry, I couldn’t find a hotel named '{hotel_name}'."})

        try:
            check_in = datetime.strptime(date, "%Y-%m-%d")
            check_out = check_in + timedelta(days=1)

            booking_payload = {
                "room_id": str(room["_id"]),
                "pricePerNight": room.get("pricePerNight", 0),
                "image": room.get("images", [""])[0],
                "name": room.get("hotelName"),
                "address": room.get("address", ""),
                "check_in": check_in.strftime("%Y-%m-%d"),
                "check_out": check_out.strftime("%Y-%m-%d")
            }

            booking_response = requests.post("https://hotel-booking-backend-74ai.onrender.com/book-room", json=booking_payload)

            if booking_response.status_code == 201:
                booking_id = booking_response.json().get("booking_id")
                return jsonify({
                    "reply": f"Booking confirmed at {hotel_name} for {date}. Your booking ID is {booking_id}."
                })
            else:
                print("Booking API error:", booking_response.text)
                return jsonify({
                    "reply": "Booking failed. Please try again later or choose a different hotel."
                })
        except Exception as e:
            print("Booking error:", e)
            return jsonify({
                "reply": "Something went wrong during booking. Please check the date format or try again later."
                })

    elif intent == "make_payment":
        return jsonify({
            "reply": "To complete your payment, please go to the *Bookings* page and follow the Razorpay payment process manually. Let me know if you need help!"
        })

    else:
        return jsonify({
            "reply": "I'm here to help you search, check amenities, and book hotels. Try asking a hotel-related question!"
        })
