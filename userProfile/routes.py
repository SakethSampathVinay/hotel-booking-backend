from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson import ObjectId
from flask_cors import cross_origin

profile_bp = Blueprint('userProfile', __name__)
mongo = None

@profile_bp.route('/get-profile', methods=['GET'])
@jwt_required()
def get_profile():
    mongo = current_app.mongo
    user_id = get_jwt_identity()

    email = request.args.get('email')
    name = request.args.get('name')

    result = mongo.db.users.find_one({'_id': ObjectId(user_id)});
    if(result):
        result['_id'] = str(result['_id'])
        return jsonify({"message": "Successfully gettig the data", "profileData": result}), 200 
    return jsonify({"message": "Failed to get the profile data", "result": result}), 400

@profile_bp.route("/update-profile", methods=['POST'])
@jwt_required()
def update_profile():
    mongo = current_app.mongo
    user_id = get_jwt_identity()
    data = request.get_json()

    if '_id' in data:
        del data['_id']

    result = mongo.db.users.update_one({"_id": ObjectId(user_id)}, {"$set": data})

    if result.modified_count == 1:
        return jsonify({"message": "Profile updated successfully"}), 200 
    else:
        return jsonify({"message": "No changes made or user not found"}), 400

@profile_bp.route('/delete-profile', methods=['DELETE', 'OPTIONS'])
@cross_origin(origins="http://localhost:4200", supports_credentials=True)
@jwt_required()
def delete_profile():
    mongo = current_app.mongo
    user_id = get_jwt_identity()

    result = mongo.db.users.delete_one({'_id': ObjectId(user_id)})

    if result.deleted_count == 1:
        return jsonify({"message": "Profile Deleted Successfully"}), 200 
    else:
        return jsonify({"message": "Error Deleting the Profile"}), 400