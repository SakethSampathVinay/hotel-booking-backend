import os # Import necessary modules
from flask import Blueprint, request, jsonify, current_app # Import Flask components for creating routes
from bson import ObjectId # Import ObjectId for MongoDB document IDs
from werkzeug.utils import secure_filename # Import secure_filename to handle file uploads safely
import uuid # Import uuid to generate unique filenames
import cloudinary # Import cloudinary for image uploads
import cloudinary.uploader # Import cloudinary uploader for uploading images

admin_bp = Blueprint('admin', __name__) # Blueprint for admin routes

@admin_bp.route('/dashboard', methods=['GET']) 
def dashboard():
    mongo = current_app.mongo # Get the MongoDB instance from the current app context
    bookings = list(mongo.db.bookings.find({}, { # Find all bookings and select specific fields
        'user': 1, 
        'name': 1,
        'pricePerNight': 1,
        'status': 1,
        '_id': 0
    }))

    user_ids = [] # Prepare a list to hold user IDs
    for booking in bookings: 
        try:
            user_ids.append(ObjectId(booking['user'])) # Convert user ID to ObjectId and append to the list
        except:
            pass

    users = mongo.db.users.find( # Find users by their IDs and select specific fields
        {'_id': {'$in': user_ids}},
        {'_id': 1, 'name': 1}
    )

    user_id_to_name = {str(user['_id']): user['name'] for user in users} # Create a mapping of user IDs to names for easy lookup

    dashboard_data = [] # Prepare a list to hold dashboard data
    for booking in bookings: # Iterate through each booking
        user_id = str(booking['user']) # Get the user ID as a string
        dashboard_data.append({ # Append booking details along with user name and hotel name
            'user_name': user_id_to_name.get(user_id, 'Unknown'),
            'hotel_name': booking.get('name', 'N/A'),
            'amount': booking.get('pricePerNight', 0),
            'payment_status': booking.get('status', 'Unknown'),
        })

    return jsonify(dashboard_data), 200 # Return the dashboard data as a JSON response

@admin_bp.route('/booking-summary', methods=['GET'])
def booking_summary():
    mongo = current_app.mongo # Get the MongoDB instance from the current app context

    bookings = list(mongo.db.bookings.find({}, {'pricePerNight': 1})) # Find all bookings and select only the pricePerNight field

    total_bookings = len(bookings) # Count the total number of bookings
    total_amount = 0    # Initialize total amount to 0
    for b in bookings: # Iterate through each booking
        total_amount += b.get('pricePerNight', 0)
    
    return jsonify({ # Return a summary of bookings
        'total_bookings': total_bookings,
        'total_amount': total_amount
    }), 200

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'} # Set of allowed file extensions for image uploads

def allowed_file(filename): # Check if the uploaded file has an allowed extension
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@admin_bp.route('/add-hotels', methods=['POST'])
def add_hotels():
    mongo = current_app.mongo  # Get the MongoDB instance from the current app context

    if 'images' not in request.files: # Check if 'images' part is in the request files
        return jsonify({'error': 'No image part in the request'}), 400 
    
    images = request.files.getlist('images') # Get the list of images from the request files

    if len(images) != 4: # Check if exactly 4 images are provided
        return jsonify({'error': 'Exactly 4 images are required'}), 400 

    cloudinary.config( # Configure Cloudinary with credentials from the current app context
        cloud_name=current_app.config['CLOUDINARY_CLOUD_NAME'],
        api_key=current_app.config['CLOUDINARY_API_KEY'],
        api_secret=current_app.config['CLOUDINARY_API_SECRET']
    )

    
    saved_paths = [] # Prepare a list to hold the saved image paths

    for image in images: # Iterate through each image
        if image and allowed_file(image.filename): # Check if the image is valid and has an allowed file extension
            try:
                result = cloudinary.uploader.upload(image, folder="hotel_images") # Upload the image to Cloudinary
                saved_paths.append(result['secure_url']) # Append the secure URL of the uploaded image to the list
            except Exception as e:
                return jsonify({'error': f'Failed to upload image: {str(e)}'}), 500
        else:
            return jsonify({'error': f'Invalid file type: {image.filename}'}), 400

    hotel_name = request.form.get('hotel_name') # Get the hotel name from the form data
    street_address = request.form.get("street_address") # Get the street address from the form data
    hotel_type = request.form.get('hotel_type') # Get the hotel type from the form data
    price_per_night = request.form.get('price_per_night') # Get the price per night from the form data
    amenities = request.form.getlist('amenities') # Get the list of amenities from the form data

    if not hotel_name or not hotel_type or not price_per_night or not amenities: # Check if any required fields are missing
        return jsonify({'error': 'Missing required hotel fields'}), 400

    hotel_data = {  # Create a dictionary to hold the hotel data
        'images': saved_paths,
        'hotelName': hotel_name,
        'streetAddress': street_address,
        'roomType': hotel_type,
        'pricePerNight': float(price_per_night),
        'amenities': amenities
    } 

    result = mongo.db.rooms.insert_one(hotel_data) # Insert the hotel data into the MongoDB collection
    hotel_data['_id'] = str(result.inserted_id) # Add the inserted ID to the hotel data

    return jsonify({'message': 'Hotel Added Successfully', 'hotel': hotel_data}), 201 # Return success response with hotel data

@admin_bp.route('/hotels-listing', methods = ['GET'])
def hotel_listing():
    mongo = current_app.mongo # Get the MongoDB instance from the current app context
    hotels = list(mongo.db.rooms.find({}, 
    {'hotelName': 1, "roomType": 1, "pricePerNight": 1, "amenities": 1})) # Find all hotels and select specific fields
    
    return jsonify(hotels), 200 # Return the list of hotels as a JSON response


@admin_bp.route('/delete-hotel/<hotel_id>', methods=['DELETE'])
def delete_hotel(hotel_id):
    mongo = current_app.mongo # Get the MongoDB instance from the current app context

    result = mongo.db.rooms.delete_one({'_id': ObjectId(hotel_id)}) # Delete the hotel by its ID
    if result.deleted_count == 1: # If the deletion was successful, return a success message
        return jsonify({'message': 'Hotel Deleted'}), 200 # If the hotel was deleted successfully
    else:
        return jsonify({'message': 'Hotel not found'}), 404 # If the hotel was not found, return an error message