from flask import Flask, current_app, Blueprint, request, jsonify
from bson.objectid import ObjectId
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime

feedback_bp = Blueprint('feedback', __name__) # Blueprint for feedback routes

@feedback_bp.route("/add-feedback", methods = ['POST'])
@jwt_required()
def create_feedback():
    mongo = current_app.mongo # Get the MongoDB instance from the current app context
    data = request.get_json() # Get the JSON data from the request
    user_id = get_jwt_identity() # Get the user ID from the JWT token

    feedback = {
        'hotel_id': ObjectId(data['hotel_id']),
        'user_id': ObjectId(user_id),
        'rating': int(data['rating']),
        'comment': data['comment'],
        'timeStamp': datetime.utcnow()
    } # Create a feedback dictionary with hotel ID, user ID, rating, comment, and timestamp

    result = mongo.db.feedback.insert_one(feedback) # Insert the feedback into the MongoDB collection
    if(result): # If the insertion is successful, return a success message
        return jsonify({'message': 'Feedback Submitted Successfully'}), 200 
    return jsonify({'message': 'Error Submitting the Feedback'}), 400 

@feedback_bp.route('/get-feedback/<hotel_id>', methods = ['GET'])
@jwt_required()
def get_feedback(hotel_id):
    mongo = current_app.mongo # Get the MongoDB instance from the current app context
    feedbacks = list(mongo.db.feedback.find({'hotel_id': ObjectId(hotel_id)}, {'_id': 0, 'rating': 1, 'comment': 1, 'timestamp': 1})) # Find feedbacks for the specified hotel ID, excluding the MongoDB ID field
    return jsonify(feedbacks), 200 # Return the list of feedbacks as JSON response
