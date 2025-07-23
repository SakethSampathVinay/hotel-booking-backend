from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson import ObjectId
from flask_cors import cross_origin

profile_bp = Blueprint('userProfile', __name__)
mongo = None

@profile_bp.route('/get-profile', methods=['GET'])
@jwt_required()
def get_profile():
    mongo = current_app.mongo # Get the MongoDB instance from the current app context
    user_id = get_jwt_identity() # Get the user ID from the JWT token

    email = request.args.get('email') # Get the email from the request arguments
    name = request.args.get('name') # Get the name from the request arguments

    result = mongo.db.users.find_one({'_id': ObjectId(user_id)}); # Find the user profile by user ID
    if(result): # If the user profile is found, convert ObjectId to string for JSON serialization
        result['_id'] = str(result['_id']) # Convert ObjectId to string
        return jsonify({"message": "Successfully gettig the data", "profileData": result}), 200 # Return the profile data as JSON response
    return jsonify({"message": "Failed to get the profile data", "result": result}), 400 # If the user profile is not found, return an error message

@profile_bp.route("/update-profile", methods=['POST'])
@jwt_required()
def update_profile():
    mongo = current_app.mongo # Get the MongoDB instance from the current app context
    user_id = get_jwt_identity() # Get the user ID from the JWT token
    data = request.get_json() # Get the JSON data from the request

    if '_id' in data: # Remove the '_id' field from the data to prevent updating it
        del data['_id'] 

    result = mongo.db.users.update_one({"_id": ObjectId(user_id)}, {"$set": data}) # Update the user profile with the provided data

    if result.modified_count == 1: # If the update was successful, return a success message
        return jsonify({"message": "Profile updated successfully"}), 200 
    else:
        return jsonify({"message": "No changes made or user not found"}), 400

@profile_bp.route('/delete-profile', methods=['DELETE', 'OPTIONS'])
@cross_origin(origins="http://localhost:4200", supports_credentials=True) # Allow CORS for local development
@jwt_required()
def delete_profile():
    mongo = current_app.mongo   # Get the MongoDB instance from the current app context
    user_id = get_jwt_identity() # Get the user ID from the JWT token

    result = mongo.db.users.delete_one({'_id': ObjectId(user_id)}) # Delete the user profile by user ID

    if result.deleted_count == 1: # If the deletion was successful, return a success message
        return jsonify({"message": "Profile Deleted Successfully"}), 200 # If the profile was deleted successfully
    else: 
        return jsonify({"message": "Error Deleting the Profile"}), 400 # If the profile was not found or deletion failed