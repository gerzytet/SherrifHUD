import os
import datetime
import logging
from flask import Flask, request, jsonify, render_template_string
from werkzeug.utils import secure_filename
from flask_cors import CORS # Import CORS

# --- Configuration ---
UPLOAD_FOLDER = 'police_data' # Base directory for officer data
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# --- Flask App Setup ---
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 # 16MB max upload size
CORS(app) # Enable CORS for all routes - allows webpage to talk to server

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Helper Functions ---
def allowed_file(filename):
    """Checks if the file extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_officer_dir(officer_id):
    """Constructs and ensures the officer's directory exists."""
    if not officer_id or not isinstance(officer_id, str) or '/' in officer_id or '\\' in officer_id:
        raise ValueError("Invalid Officer ID") # Basic validation
    officer_dir = os.path.join(app.config['UPLOAD_FOLDER'], officer_id)
    os.makedirs(officer_dir, exist_ok=True) # Create base officer dir
    os.makedirs(os.path.join(officer_dir, 'images'), exist_ok=True) # Create images subdir
    return officer_dir

# --- Routes ---
@app.route('/')
def index():
    # Simple message indicating server is running (optional)
    # In a real app, you might serve the index.html here if not running separately
    return "Dispatch Backend Server is running."

@app.route('/upload', methods=['POST'])
def upload_data():
    """Handles text updates and image file uploads."""
    officer_id = request.form.get('officer_id')
    text_update = request.form.get('text_update')
    image_file = request.files.get('image_file')

    if not officer_id:
        logging.warning("Upload attempt failed: Missing Officer ID")
        return jsonify(success=False, error="Officer ID is required"), 400

    try:
        officer_dir = get_officer_dir(officer_id)
        logging.info(f"Processing upload for Officer ID: {officer_id}")

        # --- Handle Text Update ---
        if text_update:
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            update_line = f"[{timestamp}] {text_update}\n"
            updates_file_path = os.path.join(officer_dir, 'updates.txt')
            try:
                with open(updates_file_path, 'a', encoding='utf-8') as f:
                    f.write(update_line)
                logging.info(f"Appended text update to {updates_file_path}")
                # Return success immediately if only text was sent
                if not image_file:
                    return jsonify(success=True, message="Text update received")
            except Exception as e:
                logging.error(f"Error writing text update for {officer_id}: {e}")
                return jsonify(success=False, error=f"Could not save text update: {e}"), 500

        # --- Handle Image Upload ---
        if image_file:
            if image_file.filename == '':
                return jsonify(success=False, error="No selected image file"), 400

            if allowed_file(image_file.filename):
                filename = secure_filename(image_file.filename)
                # Create a unique filename using timestamp to avoid overwrites
                timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                base, ext = os.path.splitext(filename)
                unique_filename = f"{timestamp_str}_{base}{ext}"
                image_save_path = os.path.join(officer_dir, 'images', unique_filename)

                try:
                    image_file.save(image_save_path)
                    logging.info(f"Saved image file to {image_save_path}")
                    return jsonify(success=True, message="Image uploaded successfully", filename=unique_filename)
                except Exception as e:
                    logging.error(f"Error saving image file for {officer_id}: {e}")
                    return jsonify(success=False, error=f"Could not save image file: {e}"), 500
            else:
                logging.warning(f"Upload attempt failed for {officer_id}: File type not allowed ({image_file.filename})")
                return jsonify(success=False, error="File type not allowed"), 400

        # If neither text nor image was provided in the POST request
        if not text_update and not image_file:
             return jsonify(success=False, error="No text update or image file provided"), 400

    except ValueError as ve:
         logging.error(f"Invalid Officer ID received: {officer_id} - {ve}")
         return jsonify(success=False, error=str(ve)), 400
    except Exception as e:
        logging.error(f"An unexpected error occurred for {officer_id}: {e}", exc_info=True)
        return jsonify(success=False, error="An internal server error occurred"), 500


# --- Main Execution ---
if __name__ == '__main__':
    # Create base upload folder if it doesn't exist
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
        logging.info(f"Created base data directory: {UPLOAD_FOLDER}")
    # Run the app (debug=True is helpful for development)
    app.run(host='0.0.0.0', port=5000, debug=True)

