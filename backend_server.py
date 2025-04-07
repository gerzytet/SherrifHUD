import os
import datetime
import logging
from flask import Flask, request, jsonify, render_template_string
from werkzeug.utils import secure_filename
from flask_cors import CORS

# --- Configuration ---
DATA_DIR = 'police_data' # Base directory for all officer data
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# --- Flask App Setup ---
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = DATA_DIR # Not strictly needed for saving, but good practice
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 # 16MB max upload size
CORS(app) # Enable CORS

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Helper Functions ---
def allowed_file(filename):
    """Checks if the file extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_call_dir(officer_id, call_id):
    """Constructs and ensures the officer's call directory exists."""
    if not officer_id or not isinstance(officer_id, str) or '/' in officer_id or '\\' in officer_id:
        raise ValueError("Invalid Officer ID")
    if not call_id or not isinstance(call_id, str) or '/' in call_id or '\\' in call_id:
        raise ValueError("Invalid Call ID")

    # Sanitize IDs further (replace spaces, etc.) - basic example
    safe_officer_id = "".join(c if c.isalnum() or c in ('_','-') else '_' for c in officer_id)
    safe_call_id = "".join(c if c.isalnum() or c in ('_','-') else '_' for c in call_id)

    call_dir = os.path.join(DATA_DIR, safe_officer_id, safe_call_id)
    image_dir = os.path.join(call_dir, 'images')
    os.makedirs(image_dir, exist_ok=True) # Create full path including images subdir
    return call_dir, image_dir

# --- Routes ---
@app.route('/')
def index():
    return "Dispatch Backend Server v2 is running."

@app.route('/upload', methods=['POST'])
def upload_data():
    """Handles text updates and image file uploads for a specific officer/call."""
    officer_id = request.form.get('officer_id')
    call_id_input = request.form.get('call_id')
    text_update = request.form.get('text_update') # Get text, might be None or empty
    image_files = request.files.getlist('image_files') # Get list of files

    if not officer_id:
        logging.warning("Upload attempt failed: Missing Officer ID")
        return jsonify(success=False, error="Officer ID is required"), 400
    if not call_id_input:
        logging.warning("Upload attempt failed: Missing Call ID")
        return jsonify(success=False, error="Call ID is required"), 400

    # --- Handle Call ID ---
    call_id = call_id_input
    new_call_generated = False
    if call_id == "NEW_CALL":
        # Generate a unique Call ID based on timestamp
        call_id = f"CALL_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        new_call_generated = True
        logging.info(f"New Call ID generated for {officer_id}: {call_id}")

    try:
        call_dir, image_dir = get_call_dir(officer_id, call_id)
        logging.info(f"Processing upload for Officer: {officer_id}, Call: {call_id}")

        results = {"text_saved": False, "images_saved": [], "errors": []}

        # --- Handle Text Update ---
        # Save text if it exists (even empty string, per user request)
        if text_update is not None:
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            # Append each line from the textarea separately
            updates_file_path = os.path.join(call_dir, 'updates.txt')
            lines_written = 0
            try:
                with open(updates_file_path, 'a', encoding='utf-8') as f:
                    # Split potentially multi-line text input and write each line
                    for line in text_update.splitlines():
                        # Append timestamp to each line for clarity in the file
                        update_line = f"[{timestamp}] {line}\n"
                        f.write(update_line)
                        lines_written += 1
                    # Handle case where input was just whitespace or empty - write one timestamped empty line
                    if lines_written == 0 and text_update is not None:
                         update_line = f"[{timestamp}] \n" # Write timestamped empty line
                         f.write(update_line)
                         lines_written = 1

                if lines_written > 0:
                    results["text_saved"] = True
                    logging.info(f"Appended {lines_written} text line(s) to {updates_file_path}")

            except Exception as e:
                logging.error(f"Error writing text update for {officer_id}/{call_id}: {e}")
                results["errors"].append(f"Could not save text update: {e}")

        # --- Handle Image Uploads ---
        for image_file in image_files:
            if image_file and image_file.filename != '' and allowed_file(image_file.filename):
                filename = secure_filename(image_file.filename)
                timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                base, ext = os.path.splitext(filename)
                unique_filename = f"{timestamp_str}_{base}{ext}"
                image_save_path = os.path.join(image_dir, unique_filename)
                try:
                    image_file.save(image_save_path)
                    results["images_saved"].append(unique_filename)
                    logging.info(f"Saved image file to {image_save_path}")
                except Exception as e:
                    logging.error(f"Error saving image file {filename} for {officer_id}/{call_id}: {e}")
                    results["errors"].append(f"Could not save image {filename}: {e}")
            elif image_file and image_file.filename != '':
                 logging.warning(f"Upload attempt failed for {officer_id}/{call_id}: File type not allowed ({image_file.filename})")
                 results["errors"].append(f"File type not allowed: {image_file.filename}")

        # --- Determine Overall Success ---
        success = not results["errors"] # Success if no errors occurred
        response = {"success": success}
        if new_call_generated:
            response["call_id"] = call_id # Let frontend know the new ID
        if results["errors"]:
            response["error"] = "; ".join(results["errors"])
        if results["text_saved"] or results["images_saved"]:
             response["message"] = "Data processed."
             if results["images_saved"]:
                 response["message"] += f" Saved {len(results['images_saved'])} image(s)."
        elif not results["errors"]:
             response["message"] = "No new data provided to save."


        return jsonify(response), 200 if success else 500

    except ValueError as ve:
         logging.error(f"Invalid Officer/Call ID received: {officer_id}/{call_id_input} - {ve}")
         return jsonify(success=False, error=str(ve)), 400
    except Exception as e:
        logging.error(f"An unexpected error occurred for {officer_id}/{call_id_input}: {e}", exc_info=True)
        return jsonify(success=False, error="An internal server error occurred"), 500


# --- Main Execution ---
if __name__ == '__main__':
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        logging.info(f"Created base data directory: {DATA_DIR}")
    app.run(host='0.0.0.0', port=5000, debug=True) # Use debug=False for production

