# -*- coding: utf-8 -*-
"""
Police Dashboard UI Application using PyQt5.

Displays data based on file system polling (updates, images) and
simulated GPS with nearest intersection calculation from CSV.
Includes real internet status check and placeholder for real GPS check.
Optimized for an 800x480 reflected display. Forced Fullscreen on Secondary Display.

Improvements Implemented (v34):
- Added console print statements for debugging GPS simulation and intersection calculation.
- (Includes previous fixes/features from v33)
"""

# --- Standard Library Imports ---
import sys
import random
import re
import os
import time
import csv
import math
import socket # Added for internet check
from datetime import datetime
from glob import glob
import logging # Added for better logging

# --- PyQt5 Imports ---
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QTextEdit, QSizePolicy, QFrame, QPushButton # Added QPushButton
)
from PyQt5.QtGui import QFont, QPixmap, QColor, QScreen, QTextOption
from PyQt5.QtCore import Qt, QTimer, QSize, QTime, QPoint, pyqtSignal QTimeZone, QDateTime # Added QTimeZone, QDateTime, pyqtSignal

# =============================================================================
# Configuration Constants
# =============================================================================

# --- UI / Officer Configuration ---
DATA_DIR = "police_data"
INTERSECTION_CSV_PATH = "intersections.txt" # <<<--- Path to your CSV file
POLLING_INTERVAL_MS = 1500 # Check for file/dir updates every 1.5 seconds
GPS_UPDATE_INTERVAL_MS = 10000 # Update intersection every 10 seconds
IMAGE_CYCLE_INTERVAL_MS = 5000 # Cycle images every 5 seconds if folder hasn't changed
CRS_EPSG = 3857 # Confirmed Web Mercator
CRS_UNITS_TO_FEET = 3.28084 # Conversion factor from meters (assumed) to feet
FEET_PER_MILE = 5280.0
DISTANCE_UNIT_THRESHOLD_FT = 1320.0 # Threshold (in feet) to switch display to miles (1/4 mile)
GPS_LOCK_PROBABILITY = 0.75 # Chance (0.0 to 1.0) of GPS having a lock during simulation
SIM_GPS_MOVE_SCALE_DIVISOR = 500.0 # Controls simulated GPS movement. Higher value = smaller steps.

# --- Update Settings ---
CLOCK_INTERVAL_MS = 1000
PULSE_INTERVAL_MS = 200
PULSE_COUNT_CRITICAL = 4
PULSE_COUNT_BOLO = 3
PULSE_COUNT_TRAFFIC = 2

# --- Color Palette ---
COLOR_BACKGROUND = "#000000"
COLOR_TEXT_PRIMARY = "#E0E0E0"
COLOR_TEXT_SECONDARY = "#A0A0A0"
COLOR_ACCENT = "#00BFFF" # DeepSkyBlue
COLOR_SEPARATOR = COLOR_ACCENT
COLOR_BOX_BORDER = COLOR_ACCENT
COLOR_ACTUAL_IMAGE_BORDER = "#FFFFFF"
COLOR_UPDATE_TIMESTAMP = "#00FFFF" # Cyan
COLOR_TIMESTAMP_TRAFFIC = "#FFFF00" # Yellow
COLOR_TIMESTAMP_BOLO = "#FFA500" # Orange
COLOR_CRITICAL_UPDATE = "#FF0000" # Red
COLOR_CRITICAL_BG = "#400000" # Dark Red background for critical text
COLOR_GPS_LOCKED = "#00FF00" # Green
COLOR_GPS_NO_LOCK = COLOR_TEXT_SECONDARY
COLOR_CONN_OK = "#00FF00" # Green
COLOR_CONN_BAD = COLOR_TEXT_SECONDARY
COLOR_STATUS_OK_BG = "#003000" # Dark Green background
COLOR_STATUS_BAD_BG = "#303030" # Dark Gray background
COLOR_BUTTON_BG = "#303030"
COLOR_BUTTON_TEXT = COLOR_TEXT_PRIMARY
COLOR_BUTTON_BORDER = COLOR_ACCENT
COLOR_BUTTON_DISABLED_BG = "#505050"
COLOR_BUTTON_DISABLED_TEXT = "#808080"
COLOR_BUTTON_DISABLED_BORDER = "#606060"

# --- Font Settings ---
FONT_FAMILY = "Roboto Condensed" # Consider a readily available font like Arial or Tahoma if needed
FONT_SIZE_STATUS_BAR = 11
FONT_SIZE_TITLE = 18
FONT_SIZE_INTERSECTION_DATA = 13
FONT_SIZE_UPDATE_TEXT = 11
FONT_SIZE_TIMESTAMP = 9
FONT_SIZE_IMAGE_DESC = 10
FONT_SIZE_IMAGE_PLACEHOLDER = 48
FONT_SIZE_NAV_LABEL = 12
FONT_SIZE_NAV_BUTTON = 10

# --- UI Layout Settings ---
MAIN_MARGINS = 6
MAIN_SPACING = 8
LEFT_COLUMN_SPACING = 4
RIGHT_COLUMN_SPACING = 4
BOX_PADDING = 6
BOX_BORDER_RADIUS = 5
INTERSECTION_SPACING = 2
UPDATE_SPACING_PX = 3
ACTUAL_IMAGE_BORDER_WIDTH = 1
SEPARATOR_HEIGHT = 2
NAV_BUTTON_PADDING_X = 8
NAV_BUTTON_PADDING_Y = 3

# --- Icons & Prefixes ---
ICON_IMAGE_LOADING = "📷"
ICON_IMAGE_ERROR = "❌"
PREFIX_CRITICAL = "⚠️"
PREFIX_INFO = "[I]"
PREFIX_TRAFFIC = "[T]"
PREFIX_BOLO = "[B]"
ICON_PREV = "◀"
ICON_NEXT = "▶"

# --- Keywords for Critical Highlighting ---
CRITICAL_MESSAGE_KEYWORDS = ["backup", "suspicious", "alert", "emergency", "pursuit"]

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# =============================================================================
# Helper Functions
# =============================================================================

#New Function to check if it is night or daytime, as well as checking daylight savings time for accurate day-night prediction
#New Function to check if it is night or daytime, as well as checking daylight savings time for accurate day-night prediction
def check_time():
    # Get the system timezone (US/Pacific in this case)
    time_zone = QTimeZone(b"EST")  # Use correct IANA ID for US/Pacific

    # Get the current date and time in the specified time zone
    date_time = QDateTime.currentDateTime()

    # Define daylight (6:00 AM) and night (6:00 PM) for today
    today = date_time.date()  # QDate object for today
    daylight = QDateTime(today, QTime(6, 0), time_zone)  # 6:00 AM today
    night = QDateTime(today, QTime(18, 0), time_zone)   # 6:00 PM today

    # Check if current time is night (after or equal to 6:00 PM) or day (before 6:00 PM)
    is_night = date_time >= night or date_time < daylight

    # Check if DST is in effect (for reference, optional)
    is_dst = time_zone.isDaylightTime(date_time)
    print(f"DST is {'active' if is_dst else 'not active'}")  # Debugging DST status

    if(is_night):
        return True
    else:
        return False
    

def swap_color_palette(bool): # New Function to swap to light-mode color palette
    global COLOR_BACKGROUND
    global COLOR_TEXT_PRIMARY
    global COLOR_TEXT_SECONDARY
    global COLOR_ACCENT
    global COLOR_SEPARATOR
    global COLOR_BOX_BORDER
    global COLOR_ACTUAL_IMAGE_BORDER
    global COLOR_UPDATE_TIMESTAMP
    global COLOR_TIMESTAMP_TRAFFIC
    global COLOR_TIMESTAMP_BOLO
    global COLOR_CRITICAL_UPDATE
    global COLOR_CRITICAL_BG
    global COLOR_GPS_LOCKED
    global COLOR_GPS_NO_LOCK
    global COLOR_CONN_OK
    global COLOR_CONN_BAD
    global COLOR_STATUS_OK_BG
    global COLOR_STATUS_BAD_BG
    global COLOR_BUTTON_BG
    global COLOR_BUTTON_TEXT
    global COLOR_BUTTON_BORDER
    global COLOR_BUTTON_DISABLED_BG
    global COLOR_BUTTON_DISABLED_TEXT
    global COLOR_BUTTON_DISABLED_BORDER
    # --- Light Mode Color Palette ---
    if bool is True:
        COLOR_BACKGROUND = "#FFFFFF"          # White (replacing black)
        COLOR_TEXT_PRIMARY = "#1A1A1A"        # Dark Gray (near black for readability)
        COLOR_TEXT_SECONDARY = "#606060"      # Medium Gray (darker than original secondary)
        COLOR_ACCENT = "#00BFFF"              # DeepSkyBlue (unchanged, still works in light mode)
        COLOR_SEPARATOR = COLOR_ACCENT        # DeepSkyBlue (unchanged)
        COLOR_BOX_BORDER = COLOR_ACCENT       # DeepSkyBlue (unchanged)
        COLOR_ACTUAL_IMAGE_BORDER = "#000000" # Black (inverted from white)
        COLOR_UPDATE_TIMESTAMP = "#00CCCC"    # Slightly darker Cyan for better contrast
        COLOR_TIMESTAMP_TRAFFIC = "#CC9900"   # Darker Yellow (more readable on light BG)
        COLOR_TIMESTAMP_BOLO = "#E59400"      # Darker Orange (adjusted for light mode)
        COLOR_CRITICAL_UPDATE = "#CC0000"     # Slightly darker Red (more readable)
        COLOR_CRITICAL_BG = "#FFCCCC"         # Light Red background (inverted from dark red)
        COLOR_GPS_LOCKED = "#008000"          # Dark Green (better contrast on light BG)
        COLOR_GPS_NO_LOCK = COLOR_TEXT_SECONDARY  # Medium Gray (unchanged reference)
        COLOR_CONN_OK = "#008000"             # Dark Green (better contrast)
        COLOR_CONN_BAD = COLOR_TEXT_SECONDARY # Medium Gray (unchanged reference)
        COLOR_STATUS_OK_BG = "#CCFFCC"        # Light Green background (inverted from dark green)
        COLOR_STATUS_BAD_BG = "#E0E0E0"       # Light Gray background (inverted from dark gray)
        COLOR_BUTTON_BG = "#D0D0D0"           # Light Gray (lighter than dark mode)
        COLOR_BUTTON_TEXT = COLOR_TEXT_PRIMARY  # Dark Gray (unchanged reference)
        COLOR_BUTTON_BORDER = COLOR_ACCENT    # DeepSkyBlue (unchanged)
        COLOR_BUTTON_DISABLED_BG = "#B0B0B0"  # Medium Gray (lighter disabled state)
        COLOR_BUTTON_DISABLED_TEXT = "#808080"  # Gray (unchanged, still readable)
        COLOR_BUTTON_DISABLED_BORDER = "#A0A0A0"  # Lighter Gray (adjusted for light mode)
    return
    
def create_label(text, font_size, bold=False, color=COLOR_TEXT_PRIMARY, alignment=Qt.AlignLeft | Qt.AlignVCenter, parent=None):
    """ Helper function to create and configure a QLabel. """
    label = QLabel(text, parent=parent)
    font = QFont(FONT_FAMILY, font_size)
    font.setBold(bold)
    label.setFont(font)
    label.setAlignment(alignment)
    label.setStyleSheet(f"color: {color}; background-color: transparent;")
    return label

def create_button(text, font_size, parent=None):
    """ Helper function to create and configure a QPushButton. """
    button = QPushButton(text, parent=parent)
    font = QFont(FONT_FAMILY, font_size)
    button.setFont(font)
    button.setStyleSheet(f"""
        QPushButton {{
            background-color: {COLOR_BUTTON_BG};
            color: {COLOR_BUTTON_TEXT};
            border: 1px solid {COLOR_BUTTON_BORDER};
            border-radius: {BOX_BORDER_RADIUS}px;
            padding: {NAV_BUTTON_PADDING_Y}px {NAV_BUTTON_PADDING_X}px;
            min-width: 30px; /* Ensure buttons have minimum width */
        }}
        QPushButton:pressed {{
            background-color: {COLOR_ACCENT};
            color: {COLOR_BACKGROUND};
        }}
        QPushButton:disabled {{
            background-color: {COLOR_BUTTON_DISABLED_BG};
            color: {COLOR_BUTTON_DISABLED_TEXT};
            border-color: {COLOR_BUTTON_DISABLED_BORDER};
        }}
    """)
    return button

def get_call_dir(officer_id, call_id):
    """
    Constructs and ensures the officer's call directory exists.
    Returns tuple: (call_dir_path, image_dir_path).
    Raises ValueError for invalid IDs.
    Uses basic sanitization.
    (Adapted from backend_server.txt for consistency)
    """
    if not officer_id or not isinstance(officer_id, str) or '/' in officer_id or '\\' in officer_id:
        raise ValueError("Invalid Officer ID")
    if not call_id or not isinstance(call_id, str) or '/' in call_id or '\\' in call_id:
        raise ValueError("Invalid Call ID")

    # Basic sanitization (replace spaces, etc.) - adjust if needed
    safe_officer_id = "".join(c if c.isalnum() or c in ('_','-') else '_' for c in officer_id)
    safe_call_id = "".join(c if c.isalnum() or c in ('_','-') else '_' for c in call_id)

    call_dir = os.path.join(DATA_DIR, safe_officer_id, safe_call_id)
    image_dir = os.path.join(call_dir, 'images')
    try:
        os.makedirs(image_dir, exist_ok=True) # Create full path including images subdir if needed
    except OSError as e:
        logging.error(f"Error creating directory {image_dir}: {e}")
        raise # Re-raise the error if directory creation fails critically
    return call_dir, image_dir

#Execute Time check and swap color.
swap_color_palette(check_time())
# =============================================================================
# Component Widgets
# =============================================================================

class StatusBarWidget(QWidget):
    """ Widget for the top status bar including navigation. """
    # --- Signals for navigation button clicks ---\
    
    
    prevOfficerClicked = pyqtSignal()
    nextOfficerClicked = pyqtSignal()
    prevCallClicked = pyqtSignal()
    nextCallClicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()

    def initUI(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(MAIN_MARGINS, 2, MAIN_MARGINS, 2)
        layout.setSpacing(MAIN_SPACING)

        # Left Status Indicators
        self.gps_text_label = create_label("GPS: ---", FONT_SIZE_STATUS_BAR, color=COLOR_TEXT_SECONDARY, parent=self)
        self.conn_text_label = create_label("NET: ---", FONT_SIZE_STATUS_BAR, color=COLOR_TEXT_SECONDARY, parent=self)
        self.gps_text_label.setStyleSheet(f"color: {COLOR_GPS_NO_LOCK}; background-color: {COLOR_STATUS_BAD_BG}; padding: 1px 3px; border-radius: 3px;")
        self.conn_text_label.setStyleSheet(f"color: {COLOR_CONN_BAD}; background-color: {COLOR_STATUS_BAD_BG}; padding: 1px 3px; border-radius: 3px;")

        # Navigation Controls (Center)
        self.prev_officer_btn = create_button(f"{ICON_PREV} Off.", FONT_SIZE_NAV_BUTTON, parent=self)
        self.next_officer_btn = create_button(f"Off. {ICON_NEXT}", FONT_SIZE_NAV_BUTTON, parent=self)
        self.prev_call_btn = create_button(f"{ICON_PREV} Call", FONT_SIZE_NAV_BUTTON, parent=self)
        self.next_call_btn = create_button(f"Call {ICON_NEXT}", FONT_SIZE_NAV_BUTTON, parent=self)
        self.nav_label = create_label("Officer: --- / Call: ---", FONT_SIZE_NAV_LABEL, bold=True, alignment=Qt.AlignCenter, parent=self)
        self.nav_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred) # Allow label to expand

        # Right Clock
        self.time_label = create_label("00:00:00", FONT_SIZE_STATUS_BAR, color=COLOR_TEXT_PRIMARY, alignment=Qt.AlignRight | Qt.AlignVCenter, parent=self)

        # --- Layout ---
        layout.addWidget(self.gps_text_label)
        layout.addWidget(self.conn_text_label)
        layout.addStretch(1) # Push navigation towards center
        layout.addWidget(self.prev_officer_btn)
        layout.addWidget(self.next_officer_btn)
        layout.addSpacing(MAIN_SPACING) # Space between officer/call buttons
        layout.addWidget(self.nav_label) # Central label
        layout.addSpacing(MAIN_SPACING)
        layout.addWidget(self.prev_call_btn)
        layout.addWidget(self.next_call_btn)
        layout.addStretch(1) # Push clock to right
        layout.addWidget(self.time_label)

        # --- Connect Signals ---
        self.prev_officer_btn.clicked.connect(self.prevOfficerClicked.emit)
        self.next_officer_btn.clicked.connect(self.nextOfficerClicked.emit)
        self.prev_call_btn.clicked.connect(self.prevCallClicked.emit)
        self.next_call_btn.clicked.connect(self.nextCallClicked.emit)

    def update_status(self, gps_locked, conn_ok):
        """ Updates status indicators based on provided state. """
        if gps_locked:
            self.gps_text_label.setText("GPS: Lock")
            self.gps_text_label.setStyleSheet(f"color: {COLOR_GPS_LOCKED}; background-color: {COLOR_STATUS_OK_BG}; padding: 1px 3px; border-radius: 3px;")
        else:
            self.gps_text_label.setText("GPS: No Lock")
            self.gps_text_label.setStyleSheet(f"color: {COLOR_GPS_NO_LOCK}; background-color: {COLOR_STATUS_BAD_BG}; padding: 1px 3px; border-radius: 3px;")
        if conn_ok:
            self.conn_text_label.setText("NET: Online")
            self.conn_text_label.setStyleSheet(f"color: {COLOR_CONN_OK}; background-color: {COLOR_STATUS_OK_BG}; padding: 1px 3px; border-radius: 3px;")
        else:
            self.conn_text_label.setText("NET: Offline")
            self.conn_text_label.setStyleSheet(f"color: {COLOR_CONN_BAD}; background-color: {COLOR_STATUS_BAD_BG}; padding: 1px 3px; border-radius: 3px;")

    def update_time(self, time_text):
        self.time_label.setText(time_text)

    def update_navigation_label(self, officer_id, call_id):
        """Updates the central label showing current officer and call."""
        officer_display = officer_id if officer_id else "---"
        call_display = call_id if call_id else "---"
        self.nav_label.setText(f"Officer: {officer_display} / Call: {call_display}")

    def update_button_states(self, can_prev_officer, can_next_officer, can_prev_call, can_next_call):
        """Enables or disables navigation buttons."""
        self.prev_officer_btn.setEnabled(can_prev_officer)
        self.next_officer_btn.setEnabled(can_next_officer)
        self.prev_call_btn.setEnabled(can_prev_call)
        self.next_call_btn.setEnabled(can_next_call)


class IntersectionInfoWidget(QFrame):
    """ Widget for displaying nearest intersection information. """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()

    def initUI(self):
        self.setObjectName("intersectionContainer")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(BOX_PADDING, BOX_PADDING, BOX_PADDING, BOX_PADDING)
        layout.setSpacing(INTERSECTION_SPACING)
        self.timestamp_label = create_label("Waiting for GPS...", FONT_SIZE_TIMESTAMP, color=COLOR_UPDATE_TIMESTAMP, parent=self)
        self.data_label = create_label("Calculating nearest intersection...", FONT_SIZE_INTERSECTION_DATA, color=COLOR_TEXT_PRIMARY, parent=self)
        self.data_label.setWordWrap(True)
        self.data_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.data_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.MinimumExpanding) # Allow vertical expansion
        layout.addWidget(self.timestamp_label)
        layout.addWidget(self.data_label)

    def update_data(self, data_string, timestamp):
        """ Updates the intersection text and timestamp. """
        self.timestamp_label.setText(f"GPS Fix: {timestamp}")
        self.data_label.setText(data_string if data_string else "Cannot determine intersection.")


class UpdatesLogWidget(QTextEdit):
    """ Widget for displaying the updates log with border pulse. Reads from file. """
    def __init__(self, parent=None): # Removed updates_file_path from init
        super().__init__(parent)
        self.updates_file_path = None # Will be set later
        self.last_read_pos = 0
        self.default_border_color = COLOR_BOX_BORDER
        self.flash_color = self.default_border_color
        self.flash_timer = QTimer(self)
        self.flash_timer.timeout.connect(self._do_flash_pulse)
        self.pulse_interval = PULSE_INTERVAL_MS
        self.pulse_count = 0
        self.pulse_max_on_count = 0
        self.is_flashing = False
        self.initUI()

    def _build_style_sheet(self, border_color):
        """Builds the stylesheet string with the given border color."""
        return f"""
            QTextEdit#updatesTextEdit {{
                background-color: {COLOR_BACKGROUND};
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {border_color};
                border-radius: {BOX_BORDER_RADIUS}px;
                padding: {BOX_PADDING}px;
            }}
            /* Target paragraphs within the QTextEdit for spacing */
            p {{
                margin-top: 0px;
                margin-bottom: {UPDATE_SPACING_PX}px;
                padding: 0px;
                line-height: 110%; /* Adjust line spacing if needed */
            }}
        """

    def initUI(self):
        """Initializes the UI elements of the widget."""
        self.setObjectName("updatesTextEdit")
        self.setReadOnly(True)
        self.setFont(QFont(FONT_FAMILY, FONT_SIZE_UPDATE_TEXT))
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff) # Hide scrollbar
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff) # Hide scrollbar
        self.setWordWrapMode(QTextOption.WrapAnywhere) # Ensure long lines wrap
        self.setStyleSheet(self._build_style_sheet(self.default_border_color))

    def set_updates_file(self, new_path):
        """Sets the path for the updates file and reloads content."""
        logging.info(f"UpdatesLogWidget: Setting updates file to {new_path}")
        self.updates_file_path = new_path
        self.last_read_pos = 0
        self.clear() # Clear previous content
        self.load_initial_updates()

    def load_initial_updates(self):
        """Loads the last ~20 lines from the current updates file."""
        if not self.updates_file_path:
            logging.warning("UpdatesLogWidget: No updates file path set.")
            self.append("<p>No Call Selected</p>") # Show message if no file
            return
        if os.path.exists(self.updates_file_path):
            try:
                with open(self.updates_file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines() # Read all lines
                    self.last_read_pos = f.tell() # Set read position to the end
                    logging.info(f"Updates file {self.updates_file_path} found, initial pos: {self.last_read_pos}, lines: {len(lines)}")
                    self.clear()
                    # Display last 20 lines or fewer if the file is shorter
                    start_index = max(0, len(lines) - 20)
                    for line in lines[start_index:]:
                       line = line.strip()
                       if line: self.process_update_line(line, initial_load=True)
                    self.verticalScrollBar().setValue(self.verticalScrollBar().maximum()) # Scroll to bottom
            except Exception as e:
                logging.error(f"Error reading initial updates file {self.updates_file_path}: {e}")
                self.append(f"<p>Error loading updates: {e}</p>")
        else:
            logging.warning(f"Updates file not found: {self.updates_file_path}. Awaiting creation.")
            self.append(f"<p>No updates file found for this call yet.</p>")
            self.last_read_pos = 0

    def check_for_new_updates(self):
        """Checks the current updates file for new content."""
        if not self.updates_file_path or not os.path.exists(self.updates_file_path):
            return # Do nothing if no valid file path or file doesn't exist

        try:
            current_size = os.path.getsize(self.updates_file_path)
            if current_size == self.last_read_pos: # No change
                return
            elif current_size < self.last_read_pos: # File truncated or replaced
                logging.info(f"Updates file {self.updates_file_path} size decreased. Reloading.")
                self.load_initial_updates() # Reload from beginning
                return

            # File has grown, read new lines
            with open(self.updates_file_path, 'r', encoding='utf-8') as f:
                f.seek(self.last_read_pos)
                new_lines = f.readlines()
                self.last_read_pos = f.tell()
                logging.debug(f"Read {len(new_lines)} new lines from {self.updates_file_path}")
                for line in new_lines:
                    line = line.strip()
                    if line: self.process_update_line(line)
                self.verticalScrollBar().setValue(self.verticalScrollBar().maximum()) # Scroll to bottom after adding
        except Exception as e:
            logging.error(f"Error checking for updates file {self.updates_file_path}: {e}")
            self.last_read_pos = 0 # Reset position on error

    def process_update_line(self, line, initial_load=False):
        """Parses a line and adds it to the display with formatting."""
        timestamp_str = datetime.now().strftime('%H:%M:%S'); message_text = line
        # Try to extract timestamp from the beginning of the line (flexible format)
        match = re.match(r"\[(.*?)\]\s*(.*)", line)
        if match:
            extracted_ts_str = match.group(1)
            # Try specific format first, then fallback
            try: dt_obj = datetime.strptime(extracted_ts_str, '%Y-%m-%d %H:%M:%S'); timestamp_str = dt_obj.strftime('%H:%M:%S')
            except ValueError:
                # If specific format fails, try to grab just the time part if present
                time_parts = extracted_ts_str.split()
                if len(time_parts) > 0 and ':' in time_parts[-1]:
                     timestamp_str = time_parts[-1] # Assume last part is HH:MM:SS
                else:
                     timestamp_str = extracted_ts_str # Use the whole bracketed part if time isn't obvious
            message_text = match.group(2).strip() # Use the rest of the line as message
        else:
            # If no timestamp in brackets, use current time and the whole line as message
            message_text = line.strip()

        # Determine category based on keywords
        category = 'INFO'
        if any(keyword in message_text.lower() for keyword in CRITICAL_MESSAGE_KEYWORDS): category = 'CRITICAL'
        elif "bolo" in message_text.lower(): category = 'BOLO'
        elif "traffic" in message_text.lower() or "road closure" in message_text.lower(): category = 'TRAFFIC'

        self.add_message_to_display(message_text, category, timestamp_str, trigger_flash=not initial_load)

    def add_message_to_display(self, message_text, category, timestamp, trigger_flash=True):
        """Adds a formatted HTML message to the QTextEdit."""
        if not message_text: return
        prefix = ""; timestamp_color = COLOR_UPDATE_TIMESTAMP; pulse_color = None; pulse_count = 0
        is_critical_category = (category == 'CRITICAL')

        if category == 'TRAFFIC':
            prefix = PREFIX_TRAFFIC + " "; timestamp_color = COLOR_TIMESTAMP_TRAFFIC
            pulse_color = COLOR_TIMESTAMP_TRAFFIC; pulse_count = PULSE_COUNT_TRAFFIC
        elif category == 'BOLO':
            prefix = PREFIX_BOLO + " "; timestamp_color = COLOR_TIMESTAMP_BOLO
            pulse_color = COLOR_TIMESTAMP_BOLO; pulse_count = PULSE_COUNT_BOLO
        elif category == 'INFO':
             prefix = PREFIX_INFO + " "

        # Check for critical keywords *in addition* to category
        is_critical_keyword = any(keyword in message_text.lower() for keyword in CRITICAL_MESSAGE_KEYWORDS)
        is_critical = is_critical_category or is_critical_keyword

        icon = PREFIX_CRITICAL + " " if is_critical else prefix
        span_class = "critical_message" if is_critical else "message"
        inline_style = ""

        if is_critical:
            inline_style = f'style="color: {COLOR_CRITICAL_UPDATE}; background-color: {COLOR_CRITICAL_BG}; padding: 0px 2px;"'
            timestamp_color = COLOR_CRITICAL_UPDATE
            pulse_color = COLOR_CRITICAL_UPDATE; pulse_count = PULSE_COUNT_CRITICAL
        else:
            # Use primary text color for non-critical messages
            inline_style = f'style="color: {COLOR_TEXT_PRIMARY};"'

        # Construct HTML with timestamp on one line and message below
        html_message = (
            f'<p style="margin-bottom: {UPDATE_SPACING_PX}px; margin-top: 0px; padding: 0px;">'
            f'<span style="color: {timestamp_color}; font-size: {FONT_SIZE_TIMESTAMP}pt;">[{timestamp}]</span><br>'
            f'<span class="{span_class}" {inline_style}>{icon}{message_text}</span>'
            f'</p>'
        )

        self.append(html_message) # Append the HTML content
        # Ensure the view scrolls to the bottom after adding new content
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())

        # Trigger flashing border if specified
        if trigger_flash and pulse_color and pulse_count > 0:
            self.start_flash(pulse_color, pulse_count)

    def start_flash(self, color, pulse_on_count):
        """Starts the border flashing sequence."""
        if self.is_flashing: return # Don't restart if already flashing
        self.flash_color = color
        self.pulse_max_on_count = pulse_on_count
        self.pulse_count = 0 # Reset pulse counter
        self.is_flashing = True
        self.flash_timer.start(self.pulse_interval)
        self._do_flash_pulse() # Start immediately

    def _do_flash_pulse(self):
        """Handles one step of the flashing animation."""
        if not self.is_flashing:
            self.flash_timer.stop()
            return

        self.pulse_count += 1
        total_ticks = self.pulse_max_on_count * 2 # Total on/off cycles

        if self.pulse_count > total_ticks:
            # Stop flashing and reset to default border
            self.flash_timer.stop()
            self.setStyleSheet(self._build_style_sheet(self.default_border_color))
            self.is_flashing = False
        elif self.pulse_count % 2 == 1: # Odd counts = ON (flash color)
            self.setStyleSheet(self._build_style_sheet(self.flash_color))
        else: # Even counts = OFF (default color)
            self.setStyleSheet(self._build_style_sheet(self.default_border_color))


class ImageDisplayWidget(QWidget):
    """ Widget for displaying image, description, overlay. Reads from folder. """
    def __init__(self, parent=None): # Removed image_folder_path from init
        super().__init__(parent)
        self.image_folder_path = None # Will be set later
        self.image_files = []
        self.current_image_index = -1
        self.current_pixmap = None
        self.image_label = None
        self.image_description_label = None
        self.image_border_overlay_label = None
        self.last_scan_time = 0 # Track last scan time
        self.image_cycle_timer = QTimer(self) # Timer for cycling images
        self.image_cycle_timer.timeout.connect(self.display_next_image)
        self.initUI()

    def initUI(self):
        """Initializes the UI elements."""
        layout = QVBoxLayout(self); layout.setContentsMargins(0, 0, 0, 0); layout.setSpacing(RIGHT_COLUMN_SPACING)

        # Label to display the image (or placeholder)
        self.image_label = QLabel(ICON_IMAGE_LOADING, self); self.image_label.setObjectName("imageLabel")
        self.image_label.setAlignment(Qt.AlignCenter); self.image_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored) # Allow shrinking/expanding
        self.image_label.setStyleSheet(f"""QLabel#imageLabel {{ color: {COLOR_TEXT_SECONDARY}; font-size: {FONT_SIZE_IMAGE_PLACEHOLDER}pt; background-color: {COLOR_BACKGROUND}; border: 1px solid {COLOR_BOX_BORDER}; border-radius: {BOX_BORDER_RADIUS}px; }}""")
        layout.addWidget(self.image_label, 1) # Give image label stretch factor

        # Label for image description/filename/timestamp
        self.image_description_label = create_label("No Image Available", FONT_SIZE_IMAGE_DESC, color=COLOR_TEXT_SECONDARY, alignment=Qt.AlignCenter, parent=self)
        self.image_description_label.setWordWrap(True) # Allow description to wrap
        layout.addWidget(self.image_description_label) # No stretch factor

        # Overlay for the white border around the actual image pixels
        self.image_border_overlay_label = QLabel(self.image_label) # Child of image_label for positioning
        self.image_border_overlay_label.setObjectName("imageBorderOverlay")
        self.image_border_overlay_label.setStyleSheet(f"border: {ACTUAL_IMAGE_BORDER_WIDTH}px solid {COLOR_ACTUAL_IMAGE_BORDER}; background-color: transparent;")
        self.image_border_overlay_label.setAttribute(Qt.WA_TransparentForMouseEvents) # Pass mouse events through
        self.image_border_overlay_label.hide() # Hidden initially

    def set_image_folder(self, new_path):
        """Sets the path for the image folder and rescans."""
        logging.info(f"ImageDisplayWidget: Setting image folder to {new_path}")
        self.image_folder_path = new_path
        self.image_files = []
        self.current_image_index = -1
        self.current_pixmap = None
        self.last_scan_time = 0 # Reset scan time
        self.image_cycle_timer.stop() # Stop cycling timer

        folder_exists = self.check_for_new_images(initial_load=True) # Perform initial scan and load latest image if found

        if self.image_files:
             self.image_cycle_timer.start(IMAGE_CYCLE_INTERVAL_MS) # Start cycling if images exist
        elif not folder_exists:
             self.update_display(None, "Image Folder Not Found", True)
        else: # Folder exists but is empty
             self.update_display(None, "No Images Found", True)


    def check_for_new_images(self, initial_load=False):
        """
        Checks the folder for new or modified image files.
        Returns True if the folder exists (even if empty), False otherwise.
        Loads the newest image if initial_load is True or if the list was previously empty.
        """
        if not self.image_folder_path:
            logging.debug("ImageDisplayWidget: Image folder path not set.")
            if self.image_files: # Clear if path becomes invalid
                self.image_files = []; self.current_image_index = -1
                self.update_display(None, "No Call Selected", True)
            return False # Folder path not set

        if not os.path.isdir(self.image_folder_path):
            logging.warning(f"ImageDisplayWidget: Image folder not found: {self.image_folder_path}")
            if self.image_files: # Clear if folder becomes invalid
                self.image_files = []; self.current_image_index = -1
                self.update_display(None, "Image Folder Not Found", True)
            return False # Folder does not exist

        try:
            # Get list of image files, sorted by modification time (newest last)
            current_files = sorted(
                [os.path.join(self.image_folder_path, f) for f in os.listdir(self.image_folder_path)
                 if os.path.isfile(os.path.join(self.image_folder_path, f)) and f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))],
                key=os.path.getmtime
            )

            folder_updated = False
            latest_mod_time = os.path.getmtime(current_files[-1]) if current_files else 0

            # Detect update if file list changed OR the latest file is newer than last scan
            if len(current_files) != len(self.image_files) or latest_mod_time > self.last_scan_time:
                 folder_updated = True
                 logging.info(f"Image folder {self.image_folder_path} updated. Found {len(current_files)} images.")
                 self.image_files = current_files
                 self.last_scan_time = latest_mod_time # Update scan time

                 if self.image_files:
                     # If it's the initial load or we previously had no images, load the newest one
                     if initial_load or self.current_image_index == -1:
                         self.current_image_index = len(self.image_files) - 1
                         self.load_image(self.current_image_index)
                     # If folder updated but we already had an image displayed, check if current index is still valid
                     elif self.current_image_index >= len(self.image_files):
                         self.current_image_index = len(self.image_files) - 1 # Reset to last image
                         self.load_image(self.current_image_index)
                     # else: keep displaying the current image index if it's still valid

                     # Restart or start the cycle timer
                     self.image_cycle_timer.start(IMAGE_CYCLE_INTERVAL_MS)

                 else: # Folder updated but is now empty
                     self.current_image_index = -1
                     self.update_display(None, "No Images Found", True)
                     self.image_cycle_timer.stop()

            return True # Folder exists

        except Exception as e:
            logging.error(f"Error scanning image folder {self.image_folder_path}: {e}")
            self.image_files = []
            self.current_image_index = -1
            self.update_display(None, "Error Scanning Folder", True)
            self.image_cycle_timer.stop()
            return True # Folder might exist but error occurred

    def display_next_image(self):
        """Cycles to the next image if available. Called by timer."""
        if not self.image_files or len(self.image_files) < 2:
             # logging.debug("Image cycling skipped: Not enough images.")
             return # Don't cycle if 0 or 1 image
        self.current_image_index = (self.current_image_index + 1) % len(self.image_files)
        self.load_image(self.current_image_index)

    def load_image(self, index):
        """Loads and displays the image at the specified index."""
        if not self.image_files or not (0 <= index < len(self.image_files)):
            self.update_display(None, "No Image Available", True)
            return
        filepath = self.image_files[index]
        pixmap = QPixmap(filepath)
        is_error = pixmap.isNull()

        # --- Create Description ---
        display_desc = f"({index + 1}/{len(self.image_files)}) " # Add index count
        base_name = os.path.basename(filepath)
        # Try to extract timestamp and original name
        match = re.match(r"(\d{8}_\d{6}_\d{6})_(.*)", base_name)
        if match:
            try:
                ts = datetime.strptime(match.group(1), "%Y%m%d_%H%M%S_%f")
                display_desc += f"{match.group(2)} [{ts.strftime('%H:%M:%S')}]"
            except ValueError:
                display_desc += base_name # Fallback to full name if timestamp parse fails
        else:
            display_desc += base_name # Fallback if no timestamp prefix found

        if is_error:
            logging.warning(f"Failed to load image: {filepath}")
            display_desc = f"Error loading: {base_name}"

        self.update_display(pixmap if not is_error else None, display_desc, is_error)

    def update_display(self, pixmap, description, is_error):
        """Updates the image label, description, and overlay visibility."""
        self.current_pixmap = pixmap if pixmap and not pixmap.isNull() else None # Store valid pixmap or None
        self.image_description_label.setText(description if description else "No Description")
        self.image_description_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY if is_error else COLOR_TEXT_PRIMARY};") # Dim description on error

        error_style = f"""QLabel#imageLabel {{ color: {COLOR_TEXT_SECONDARY}; font-size: {FONT_SIZE_IMAGE_PLACEHOLDER}pt; background-color: {COLOR_BACKGROUND}; border: 1px solid {COLOR_BOX_BORDER}; border-radius: {BOX_BORDER_RADIUS}px; qproperty-alignment: 'AlignCenter'; }}"""
        loaded_style = f"""QLabel#imageLabel {{ color: transparent; background-color: {COLOR_BACKGROUND}; border: 1px solid {COLOR_BOX_BORDER}; border-radius: {BOX_BORDER_RADIUS}px; }}"""

        if is_error or not self.current_pixmap:
            self.image_label.setPixmap(QPixmap()) # Clear existing pixmap
            self.image_label.setText(ICON_IMAGE_ERROR if is_error else ICON_IMAGE_LOADING) # Show error or loading icon
            self.image_label.setStyleSheet(error_style)
            if self.image_border_overlay_label: self.image_border_overlay_label.hide()
        else:
            # Valid pixmap exists
            self.image_label.setText("") # Clear any placeholder icon/text
            self.image_label.setStyleSheet(loaded_style)
            # Scaling and overlay positioning will be handled by resizeEvent/showEvent
            # or explicitly called after this update if needed immediately.
            # We call scale_and_position_overlay directly to ensure it happens
            self.scale_and_position_overlay()

        self.image_label.update() # Ensure the label repaints

    def resizeEvent(self, event):
        """Handle resizing of the widget to rescale the image and overlay."""
        super().resizeEvent(event)
        self.scale_and_position_overlay() # Rescale on resize

    def showEvent(self, event):
        """Handle the widget becoming visible."""
        super().showEvent(event)
        # Needs a slight delay sometimes for layout to finalize after showing
        QTimer.singleShot(50, self.scale_and_position_overlay)

    def scale_and_position_overlay(self):
        """Scales the current pixmap to fit the label and positions the border overlay."""
        if not self.image_label or not self.image_border_overlay_label: return

        if not self.current_pixmap:
            self.image_label.setPixmap(QPixmap()) # Clear pixmap if none is loaded
            self.image_border_overlay_label.hide()
            return

        label_size = self.image_label.size()
        if label_size.width() <= 0 or label_size.height() <= 0:
            self.image_border_overlay_label.hide()
            return

        # Scale pixmap while maintaining aspect ratio
        scaled_pixmap = self.current_pixmap.scaled(label_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.image_label.setPixmap(scaled_pixmap) # Set the scaled pixmap on the label

        # Calculate geometry for the border overlay based on the scaled pixmap size
        scaled_size = scaled_pixmap.size()
        x_offset = (label_size.width() - scaled_size.width()) // 2
        y_offset = (label_size.height() - scaled_size.height()) // 2

        overlay_x = x_offset
        overlay_y = y_offset
        overlay_width = scaled_size.width()
        overlay_height = scaled_size.height()

        # Ensure overlay doesn't exceed label bounds (especially with border width)
        border_w = ACTUAL_IMAGE_BORDER_WIDTH * 2
        overlay_width = max(0, min(overlay_width, label_size.width() - overlay_x - border_w//2))
        overlay_height = max(0, min(overlay_height, label_size.height() - overlay_y - border_w//2))

        # Position and show the overlay
        self.image_border_overlay_label.setGeometry(overlay_x, overlay_y, overlay_width, overlay_height)
        self.image_border_overlay_label.show()
        self.image_border_overlay_label.raise_() # Ensure it's on top


# =============================================================================
# Main Application Window
# =============================================================================

class PoliceDashboard(QWidget):
    """ Main application window managing component widgets and data polling. """
    def __init__(self, initial_officer_id=None):
        super().__init__()
        # --- State Variables ---
        self.officers = []
        self.current_officer_index = -1
        self.calls = []
        self.current_call_index = -1
        self.initial_officer_id_preference = initial_officer_id # Store preference

        # self.mock_gps_locked = False # No longer needed for direct toggling
        self.current_sim_coords = None # Store simulated coordinates
        self.intersections_data = self.load_intersections(INTERSECTION_CSV_PATH)
        self.intersection_bounds = self.calculate_bounds(self.intersections_data)

        # --- Initialize UI ---
        self.initUI()
        self.scan_and_load_initial_data() # Scan directories and load initial data
        self.setup_timers()
        self.move_to_secondary_display()

    def initUI(self):
        """ Initialize the main UI layout and widgets. """
        self.setWindowTitle("Police Dashboard")
        self.setStyleSheet(self.build_base_style_sheet())
        overall_layout = QVBoxLayout(self); overall_layout.setContentsMargins(0, 0, 0, 0); overall_layout.setSpacing(0)

        # --- Status Bar (Top) ---
        self.statusBar = StatusBarWidget(self)
        overall_layout.addWidget(self.statusBar)

        # --- Separator ---
        separator = QFrame(self); separator.setFrameShape(QFrame.HLine); separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet(f"border: {SEPARATOR_HEIGHT}px solid {COLOR_SEPARATOR}; margin-left: {MAIN_MARGINS}px; margin-right: {MAIN_MARGINS}px;")
        overall_layout.addWidget(separator)

        # --- Main Content Area ---
        main_content_widget = QWidget(self); main_content_widget.setStyleSheet("background-color: transparent;")
        self.main_layout = QHBoxLayout(main_content_widget); self.main_layout.setContentsMargins(MAIN_MARGINS, MAIN_MARGINS, MAIN_MARGINS, MAIN_MARGINS); self.main_layout.setSpacing(MAIN_SPACING)
        overall_layout.addWidget(main_content_widget, 1) # Allow content to expand

        # --- Left Column ---
        self.left_column_layout = QVBoxLayout(); self.left_column_layout.setSpacing(LEFT_COLUMN_SPACING)
        self.main_layout.addLayout(self.left_column_layout, 1) # Left column takes 1 part of stretch

        # Intersection Info
        intersection_title = create_label("Nearest Intersection", FONT_SIZE_TITLE, bold=True, color=COLOR_ACCENT, parent=main_content_widget)
        self.intersectionInfo = IntersectionInfoWidget(main_content_widget); self.intersectionInfo.setObjectName("intersectionContainer")
        self.left_column_layout.addWidget(intersection_title)
        self.left_column_layout.addWidget(self.intersectionInfo)

        # Updates Log Title and Widget
        self.left_column_layout.addSpacing(MAIN_SPACING)
        updates_title = create_label("Important Updates", FONT_SIZE_TITLE, bold=True, color=COLOR_ACCENT, parent=main_content_widget)
        self.updatesLog = UpdatesLogWidget(parent=main_content_widget) # Path set dynamically
        self.left_column_layout.addWidget(updates_title)
        self.left_column_layout.addWidget(self.updatesLog, 1) # Allow log to expand vertically

        # --- Right Column ---
        self.imageDisplay = ImageDisplayWidget(parent=main_content_widget) # Path set dynamically
        self.main_layout.addWidget(self.imageDisplay, 1) # Right column takes 1 part of stretch

        # --- Connect Navigation Signals ---
        self.statusBar.prevOfficerClicked.connect(self.select_previous_officer)
        self.statusBar.nextOfficerClicked.connect(self.select_next_officer)
        self.statusBar.prevCallClicked.connect(self.select_previous_call)
        self.statusBar.nextCallClicked.connect(self.select_next_call)

    def build_base_style_sheet(self):
        """Generates the base stylesheet for the main window."""
        return f"""
            QWidget {{
                color: {COLOR_TEXT_PRIMARY};
                background-color: {COLOR_BACKGROUND};
                font-family: "{FONT_FAMILY}";
            }}
            QFrame#intersectionContainer {{
                background-color: {COLOR_BACKGROUND};
                border: 1px solid {COLOR_BOX_BORDER};
                border-radius: {BOX_BORDER_RADIUS}px;
            }}
             /* Style for QTextEdit is handled within its class */
            .message {{
                /* Standard message style if needed */
            }}
            .critical_message {{
                font-weight: bold; /* Example */
            }}
        """

    def setup_timers(self):
        """Initializes and starts all necessary QTimers."""
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self.update_clock)
        self.clock_timer.start(CLOCK_INTERVAL_MS)

        self.polling_timer = QTimer(self)
        self.polling_timer.timeout.connect(self.poll_for_updates)
        self.polling_timer.start(POLLING_INTERVAL_MS)

        self.gps_timer = QTimer(self)
        self.gps_timer.timeout.connect(self.update_nearest_intersection)
        self.gps_timer.start(GPS_UPDATE_INTERVAL_MS)

    def update_clock(self):
        """Updates the time display in the status bar."""
        if self.statusBar:
            current_time = QTime.currentTime()
            time_text = current_time.toString("HH:mm:ss")
            self.statusBar.update_time(time_text)

    def poll_for_updates(self):
        """ Polls data sources (files, directories) for changes and updates status bar. """
        # --- Check for Directory Structure Changes ---
        officer_changed = self.scan_officers() # Rescan officers
        call_changed = False
        current_officer_id = self.officers[self.current_officer_index] if self.current_officer_index != -1 else None
        if current_officer_id:
            call_changed = self.scan_calls(current_officer_id) # Rescan calls for current officer

        # If structure changed, update UI elements dependent on it (buttons, label)
        if officer_changed or call_changed:
            logging.info(f"Directory structure change detected (Officer: {officer_changed}, Call: {call_changed}). Updating UI selection state.")
            # Re-validate current selection and update button states/label
            self.update_ui_for_selection(reload_widgets=False) # Don't reload widgets just for button state change

        # --- Poll Individual Widgets for Content ---
        if self.updatesLog:
            self.updatesLog.check_for_new_updates() # Checks its current file
        if self.imageDisplay:
            # check_for_new_images handles rescanning its current folder
            image_folder_updated = self.imageDisplay.check_for_new_images()
            # Only cycle if the folder *didn't* just update (to avoid immediate cycle after new image loads)
            # and the timer isn't already running (or restart it if it stopped)
            if not image_folder_updated and self.imageDisplay.image_files and not self.imageDisplay.image_cycle_timer.isActive():
                 self.imageDisplay.image_cycle_timer.start(IMAGE_CYCLE_INTERVAL_MS)
            elif not self.imageDisplay.image_files and self.imageDisplay.image_cycle_timer.isActive():
                 self.imageDisplay.image_cycle_timer.stop()


        # --- Update Status Indicators ---
        internet_ok_status = self.check_internet_connection()
        # Get GPS status (simulated or real)
        gps_locked_status = self.check_gps_lock() # Use the result directly

        if self.statusBar:
            # Pass the actual checked statuses to the update function
            self.statusBar.update_status(gps_locked_status, internet_ok_status)


    # --- Directory Scanning ---
    def scan_officers(self):
        """Scans the DATA_DIR for officer directories and updates self.officers. Returns True if changed."""
        try:
            if not os.path.isdir(DATA_DIR):
                logging.warning(f"Data directory {DATA_DIR} not found.")
                if self.officers: # If it existed before but now doesn't
                    self.officers = []
                    self.current_officer_index = -1
                    self.calls = []
                    self.current_call_index = -1
                    return True
                return False

            entries = sorted([d for d in os.listdir(DATA_DIR) if os.path.isdir(os.path.join(DATA_DIR, d))])

            if entries != self.officers:
                logging.info(f"Officer list changed: {self.officers} -> {entries}")
                old_officer_id = self.officers[self.current_officer_index] if self.current_officer_index != -1 else None
                self.officers = entries

                # Try to maintain selection if possible, otherwise default to first
                new_index = -1
                if old_officer_id in self.officers:
                    new_index = self.officers.index(old_officer_id)
                elif self.officers:
                    new_index = 0 # Default to first officer if old one is gone or none was selected

                self.current_officer_index = new_index

                # Reload calls for the new current officer (or clear if no officer)
                if self.current_officer_index != -1:
                    self.load_calls_for_current_officer()
                else:
                    self.calls = []
                    self.current_call_index = -1
                return True # List changed
            return False # No change
        except Exception as e:
            logging.error(f"Error scanning officer directories in {DATA_DIR}: {e}")
            if self.officers: # Clear if error occurs
                self.officers = []
                self.current_officer_index = -1
                self.calls = []
                self.current_call_index = -1
                return True # Indicate change due to error
            return False

    def scan_calls(self, officer_id):
        """Scans the specific officer's directory for call directories. Returns True if changed."""
        if not officer_id:
            if self.calls: # Clear calls if officer becomes invalid
                self.calls = []
                self.current_call_index = -1
                return True
            return False

        officer_dir = os.path.join(DATA_DIR, officer_id)
        try:
            if not os.path.isdir(officer_dir):
                logging.warning(f"Officer directory not found: {officer_dir}")
                if self.calls:
                    self.calls = []
                    self.current_call_index = -1
                    return True
                return False

            # List directories, excluding 'images' if it exists
            entries = sorted([
                d for d in os.listdir(officer_dir)
                if os.path.isdir(os.path.join(officer_dir, d)) and d.lower() != 'images'
            ])

            if entries != self.calls:
                logging.info(f"Call list for {officer_id} changed: {self.calls} -> {entries}")
                old_call_id = self.calls[self.current_call_index] if self.current_call_index != -1 else None
                self.calls = entries

                 # Try to maintain selection if possible, otherwise default to first
                new_index = -1
                if old_call_id in self.calls:
                    new_index = self.calls.index(old_call_id)
                elif self.calls:
                    new_index = 0 # Default to first call if old one is gone or none was selected

                self.current_call_index = new_index
                return True # List changed
            return False # No change
        except Exception as e:
            logging.error(f"Error scanning call directories in {officer_dir}: {e}")
            if self.calls: # Clear if error occurs
                self.calls = []
                self.current_call_index = -1
                return True # Indicate change due to error
            return False

    def scan_and_load_initial_data(self):
        """Scans directories and loads data for the first available officer/call or preferred ID."""
        logging.info("Performing initial scan and load...")
        self.scan_officers()

        # Try to select the initial preference if provided and exists
        if self.initial_officer_id_preference and self.initial_officer_id_preference in self.officers:
            self.current_officer_index = self.officers.index(self.initial_officer_id_preference)
            logging.info(f"Initial officer preference '{self.initial_officer_id_preference}' found at index {self.current_officer_index}.")
        elif self.officers:
             self.current_officer_index = 0 # Default to first if preference not found or not set
             logging.info(f"Initial officer preference not found or not set. Defaulting to first officer: {self.officers[0]}")
        else:
             self.current_officer_index = -1 # No officers found
             logging.warning("No officer directories found on initial scan.")


        if self.current_officer_index != -1:
            self.load_calls_for_current_officer() # This sets self.calls and self.current_call_index
        else:
            self.calls = []
            self.current_call_index = -1

        self.update_ui_for_selection(reload_widgets=True) # Load data based on initial scan results

    def load_calls_for_current_officer(self):
        """Loads/rescans the call list for the currently selected officer and resets call index."""
        if self.current_officer_index == -1:
            self.calls = []
            self.current_call_index = -1
            return

        officer_id = self.officers[self.current_officer_index]
        logging.info(f"Loading calls for officer: {officer_id}")
        self.scan_calls(officer_id) # This updates self.calls and resets self.current_call_index

    # --- Navigation Slots ---
    def select_previous_officer(self):
        if not self.officers or len(self.officers) < 2: return
        self.current_officer_index = (self.current_officer_index - 1 + len(self.officers)) % len(self.officers)
        logging.info(f"Navigating to previous officer: Index {self.current_officer_index} ({self.officers[self.current_officer_index]})")
        self.load_calls_for_current_officer() # Load calls for the new officer, resets call index
        self.update_ui_for_selection(reload_widgets=True) # Reload content for new selection

    def select_next_officer(self):
        if not self.officers or len(self.officers) < 2: return
        self.current_officer_index = (self.current_officer_index + 1) % len(self.officers)
        logging.info(f"Navigating to next officer: Index {self.current_officer_index} ({self.officers[self.current_officer_index]})")
        self.load_calls_for_current_officer() # Load calls for the new officer, resets call index
        self.update_ui_for_selection(reload_widgets=True) # Reload content for new selection

    def select_previous_call(self):
        if not self.calls or len(self.calls) < 2: return
        self.current_call_index = (self.current_call_index - 1 + len(self.calls)) % len(self.calls)
        logging.info(f"Navigating to previous call: Index {self.current_call_index} ({self.calls[self.current_call_index]})")
        self.update_ui_for_selection(reload_widgets=True) # Reload content for new selection

    def select_next_call(self):
        if not self.calls or len(self.calls) < 2: return
        self.current_call_index = (self.current_call_index + 1) % len(self.calls)
        logging.info(f"Navigating to next call: Index {self.current_call_index} ({self.calls[self.current_call_index]})")
        self.update_ui_for_selection(reload_widgets=True) # Reload content for new selection

    def update_ui_for_selection(self, reload_widgets=True):
        """Updates all UI elements based on the current officer/call selection."""
        officer_id = self.officers[self.current_officer_index] if self.current_officer_index != -1 else None
        call_id = self.calls[self.current_call_index] if self.current_call_index != -1 else None

        logging.info(f"Updating UI Display for Officer: {officer_id}, Call: {call_id}")

        # Update Status Bar Label
        if self.statusBar:
            self.statusBar.update_navigation_label(officer_id, call_id)

            # Update Status Bar Button States
            can_prev_officer = len(self.officers) > 1
            can_next_officer = len(self.officers) > 1
            can_prev_call = len(self.calls) > 1
            can_next_call = len(self.calls) > 1
            self.statusBar.update_button_states(can_prev_officer, can_next_officer, can_prev_call, can_next_call)

        # Update File Paths and Reload Widgets if requested
        if reload_widgets:
            if officer_id and call_id:
                try:
                    # Use helper to ensure paths are correct and directories exist
                    call_dir, images_path = get_call_dir(officer_id, call_id)
                    updates_path = os.path.join(call_dir, 'updates.txt')

                    if self.updatesLog:
                        self.updatesLog.set_updates_file(updates_path)
                    if self.imageDisplay:
                        self.imageDisplay.set_image_folder(images_path)
                        if not self.imageDisplay.isVisible() and self.imageDisplay.image_files:
                             self.imageDisplay.show() # Show if it was hidden and now has images

                except ValueError as ve: # Handle invalid ID from get_call_dir
                     logging.error(f"Cannot update widgets, invalid ID: {ve}")
                     if self.updatesLog: self.updatesLog.set_updates_file(None); self.updatesLog.setText(f"Error: Invalid ID ({ve})")
                     if self.imageDisplay: self.imageDisplay.set_image_folder(None); self.imageDisplay.update_display(None, f"Error: Invalid ID", True)
                except Exception as e: # Catch other potential errors during path setting/loading
                     logging.error(f"Error updating widgets for {officer_id}/{call_id}: {e}")
                     if self.updatesLog: self.updatesLog.set_updates_file(None); self.updatesLog.setText(f"Error loading data.")
                     if self.imageDisplay: self.imageDisplay.set_image_folder(None); self.imageDisplay.update_display(None, f"Error loading images", True)

            else:
                # No valid selection, clear widgets
                logging.info("No valid officer/call selected, clearing widgets.")
                if self.updatesLog:
                    self.updatesLog.set_updates_file(None) # Pass None to indicate no file
                    self.updatesLog.setText("<p>No Officer/Call selected.</p>")
                if self.imageDisplay:
                    self.imageDisplay.set_image_folder(None) # Pass None to indicate no folder
                    self.imageDisplay.update_display(None, "No Officer/Call selected", True)
                    # Optionally hide: self.imageDisplay.hide()

        # Force immediate UI update if necessary (usually handled by Qt's event loop)
        QApplication.processEvents()


    # --- GPS and Intersection Logic ---
    def load_intersections(self, csv_path):
        """ Loads intersection data from CSV. Returns list of tuples: (id, name, x, y). """
        data = []
        if not os.path.exists(csv_path):
            logging.error(f"Intersection file not found at {csv_path}")
            return data
        try:
            with open(csv_path, mode='r', encoding='utf-8') as infile:
                reader = csv.DictReader(infile)
                if not all(col in reader.fieldnames for col in ['id', 'name_a', 'name_b', 'long', 'lat']):
                     logging.error(f"CSV {csv_path} missing required columns (id, name_a, name_b, long, lat).")
                     return data
                for i, row in enumerate(reader):
                    try:
                        x = float(row['long'])
                        y = float(row['lat'])
                        # Handle potentially missing or '/' name_b
                        name_b = row['name_b'].strip()
                        name_a = row['name_a'].strip()
                        display_name = f"{name_a} & {name_b}" if name_b and name_b != "/" else name_a
                        display_name = display_name.replace(" / ", " & ") # Standardize separator
                        intersection_id = row['id'] # Keep ID as string or int as needed
                        data.append((intersection_id, display_name, x, y))
                    except (ValueError, KeyError, TypeError) as e:
                        logging.warning(f"Skipping row {i+1} in {csv_path} due to error: {row} - {e}")
            logging.info(f"Loaded {len(data)} intersections from {csv_path}.")
        except Exception as e:
            logging.error(f"Error reading intersection file {csv_path}: {e}")
        return data

    def calculate_bounds(self, intersection_data):
        """ Calculates the min/max coordinate bounds for simulation. """
        if not intersection_data:
            # Provide some default reasonable bounds if no data loaded
            logging.warning("No intersection data for bounds calculation, using default.")
            return {'min_x': -9135000, 'max_x': -9115000, 'min_y': 3240000, 'max_y': 3270000}
        try:
            min_x = min(d[2] for d in intersection_data)
            max_x = max(d[2] for d in intersection_data)
            min_y = min(d[3] for d in intersection_data)
            max_y = max(d[3] for d in intersection_data)
            logging.info(f"Intersection bounds calculated: X({min_x:.1f}, {max_x:.1f}), Y({min_y:.1f}, {max_y:.1f})")
            return {'min_x': min_x, 'max_x': max_x, 'min_y': min_y, 'max_y': max_y}
        except Exception as e:
            logging.error(f"Error calculating bounds: {e}")
            return {'min_x': -9135000, 'max_x': -9115000, 'min_y': 3240000, 'max_y': 3270000} # Default fallback

    def update_nearest_intersection(self):
        """ Simulates GPS coords, finds nearest intersection, updates widget with dynamic units. """
        if not self.intersectionInfo: return
        timestamp = datetime.now().strftime('%H:%M:%S')

        if not self.intersections_data:
            self.intersectionInfo.update_data("Intersection data not loaded.", timestamp)
            return

        # --- Simulate GPS Coordinates ---
        current_coords = self.simulate_gps_coordinates()
        if not current_coords:
             self.intersectionInfo.update_data("GPS Unavailable", timestamp)
             return
        current_x, current_y = current_coords
        # --- Add Print Statement for GPS Coords ---
        print(f"[{timestamp}] DEBUG: Sim GPS Coords: ({current_x:.2f}, {current_y:.2f})")

        # --- Find Nearest Intersection ---
        nearest_info, min_dist_units = self.find_nearest_intersection(current_x, current_y)

        # --- Format Output ---
        if nearest_info:
            intersection_id, name, intersection_x, intersection_y = nearest_info
            dist_feet, direction = self.calculate_distance_and_direction(current_x, current_y, intersection_x, intersection_y)

            # --- Add Print Statement for Closest Intersection ---
            print(f"[{timestamp}] DEBUG: Closest Intersection: ID={intersection_id}, Name='{name}', Coords=({intersection_x:.2f}, {intersection_y:.2f}), Dist={min_dist_units:.1f} units")

            # --- Dynamic Unit Logic ---
            if direction == "At Location":
                 display_string = f"At {name}"
            elif dist_feet < DISTANCE_UNIT_THRESHOLD_FT:
                 # Display in feet if below threshold
                 display_string = f"{dist_feet:.0f}ft {direction} of {name}"
            else:
                 # Display in miles if above or equal to threshold
                 dist_miles = dist_feet / FEET_PER_MILE
                 display_string = f"{dist_miles:.1f}mi {direction} of {name}"
            # --- End Dynamic Unit Logic ---

            # --- Add Print Statement for UI Output ---
            print(f"[{timestamp}] DEBUG: UI Output String: '{display_string}'")

        else:
            display_string = "Calculating..."
            logging.warning("Could not find nearest intersection.")
            print(f"[{timestamp}] DEBUG: Could not find nearest intersection.")

        self.intersectionInfo.update_data(display_string, timestamp)
        print("-" * 30) # Separator for console output clarity

    def simulate_gps_coordinates(self):
        """ Simulates GPS coordinates within the bounds of loaded intersections. """
        if not self.intersection_bounds:
            logging.warning("Intersection bounds not calculated for sim coords.")
            return None # Return None if bounds aren't set

        # Simple random walk from last position or center
        if self.current_sim_coords:
             # Move slightly from the last position
             x_range = self.intersection_bounds['max_x'] - self.intersection_bounds['min_x']
             y_range = self.intersection_bounds['max_y'] - self.intersection_bounds['min_y']
             # Use the configurable divisor
             move_scale_x = x_range / SIM_GPS_MOVE_SCALE_DIVISOR if SIM_GPS_MOVE_SCALE_DIVISOR > 0 else 0
             move_scale_y = y_range / SIM_GPS_MOVE_SCALE_DIVISOR if SIM_GPS_MOVE_SCALE_DIVISOR > 0 else 0
             new_x = self.current_sim_coords[0] + random.uniform(-move_scale_x, move_scale_x)
             new_y = self.current_sim_coords[1] + random.uniform(-move_scale_y, move_scale_y)
             # Clamp within bounds
             new_x = max(self.intersection_bounds['min_x'], min(new_x, self.intersection_bounds['max_x']))
             new_y = max(self.intersection_bounds['min_y'], min(new_y, self.intersection_bounds['max_y']))
             self.current_sim_coords = (new_x, new_y)
        else:
             # Start somewhere near the middle
             start_x = (self.intersection_bounds['min_x'] + self.intersection_bounds['max_x']) / 2
             start_y = (self.intersection_bounds['min_y'] + self.intersection_bounds['max_y']) / 2
             self.current_sim_coords = (start_x, start_y)
             logging.info(f"Initial sim coords set: {self.current_sim_coords}")

        return self.current_sim_coords


    def find_nearest_intersection(self, current_x, current_y):
        """ Finds the nearest intersection. Returns (id, name, x, y), distance_in_crs_units. """
        if not self.intersections_data: return None, float('inf')
        min_dist_sq = float('inf')
        nearest_intersection_info = None
        for intersection_id, name, x, y in self.intersections_data:
            # Simple Euclidean distance squared for comparison
            dist_sq = (x - current_x)**2 + (y - current_y)**2
            if dist_sq < min_dist_sq:
                min_dist_sq = dist_sq
                nearest_intersection_info = (intersection_id, name, x, y) # Include ID
        min_dist = math.sqrt(min_dist_sq) if nearest_intersection_info else float('inf')
        return nearest_intersection_info, min_dist

    def calculate_distance_and_direction(self, x1, y1, x2, y2):
        """ Calculates distance (in feet) and direction string from point 1 to point 2. """
        dx = x2 - x1
        dy = y2 - y1
        dist_units = math.sqrt(dx**2 + dy**2)
        dist_feet = dist_units * CRS_UNITS_TO_FEET

        # Threshold for being "at" the location (e.g., within ~10 feet)
        if dist_feet < 10.0:
            return dist_feet, "At Location"

        angle_rad = math.atan2(dy, dx) # Note: atan2(y, x) convention
        angle_deg = math.degrees(angle_rad)
        bearing = (90 - angle_deg + 360) % 360 # Convert mathematical angle to compass bearing

        directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW", "N"]
        index = round(bearing / 45) % 8 # Index from 0 to 7
        direction_str = directions[index]

        return dist_feet, direction_str

    # --- Utility Functions ---
    def check_internet_connection(self, host="8.8.8.8", port=53, timeout=1):
        """ Checks for basic internet connectivity. """
        try:
            socket.setdefaulttimeout(timeout)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
            return True
        except socket.error:
            # logging.debug("Internet check failed.") # Can be noisy
            return False

    def check_gps_lock(self):
        """ Placeholder/Simulation for checking actual GPS status. """
        # --- REPLACE THIS SIMULATION WITH REAL GPS CHECK ---
        # Example: Check a serial port, API, or file for actual GPS status
        # Simulate lock based on probability
        has_lock = random.random() < GPS_LOCK_PROBABILITY # Use configured probability
        # logging.debug(f"Simulated GPS Lock Check: Returning {has_lock}")
        return has_lock
        # --- END: REPLACE THIS SIMULATION ---

    # --- Screen Handling ---
    def move_to_secondary_display(self):
        """ Attempts to move the window to the secondary display and show fullscreen. """
        screens = QApplication.screens()
        logging.info(f"Detected {len(screens)} screen(s).")
        if len(screens) > 1:
            secondary_screen = screens[1] # Assuming the second screen is the target
            logging.info(f"Attempting to move to secondary screen: {secondary_screen.name()}")
            screen_geometry = secondary_screen.geometry()
            self.setGeometry(screen_geometry) # Move and resize to screen geometry
            self.showFullScreen()
            logging.info(f"Window should be fullscreen on {secondary_screen.name()}")
        else:
            logging.info("Only one screen detected, showing fullscreen on primary screen.")
            # self.resize(800, 480) # Remove resize if always fullscreen
            self.showFullScreen() # Force fullscreen even on single display

    # --- Event Handlers ---
    def resizeEvent(self, event):
        """Handle window resize events, ensuring image scaling."""
        super().resizeEvent(event)
        # Delay slightly to allow layout to settle before rescaling image
        if self.imageDisplay:
            QTimer.singleShot(50, self.imageDisplay.scale_and_position_overlay)

    def showEvent(self, event):
        """Handle the window becoming visible."""
        super().showEvent(event)
        # Needs a slight delay sometimes for layout to finalize after showing
        if self.imageDisplay:
            QTimer.singleShot(100, self.imageDisplay.scale_and_position_overlay)

# =============================================================================
# Main Execution
# =============================================================================
if __name__ == '__main__':
    app = QApplication(sys.argv)

    # --- Determine Initial Officer (Optional Command Line Arg) ---
    initial_officer = None
    if len(sys.argv) > 1:
        initial_officer = sys.argv[1]
        logging.info(f"Command line argument provided for initial officer: {initial_officer}")

    # --- Ensure DATA_DIR exists ---
    if not os.path.exists(DATA_DIR):
        try:
            os.makedirs(DATA_DIR)
            logging.info(f"Created data directory: {DATA_DIR}")
            # Optional: Create dummy officer/call for initial testing if dir was just created
            dummy_officer = initial_officer if initial_officer else "Officer_Test"
            dummy_call = "CALL_001"
            try:
                # Use helper to create dirs safely
                dummy_call_dir, dummy_img_dir = get_call_dir(dummy_officer, dummy_call)
                dummy_updates_path = os.path.join(dummy_call_dir, 'updates.txt')
                # Create dummy updates file only if it doesn't exist
                if not os.path.exists(dummy_updates_path):
                    with open(dummy_updates_path, 'w', encoding='utf-8') as f:
                        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] System Initialized.\n")
                    logging.info(f"Created dummy data structure: {dummy_officer}/{dummy_call}")
                else:
                    logging.info(f"Dummy data structure already exists: {dummy_officer}/{dummy_call}")
            except Exception as dummy_e:
                 logging.error(f"Failed to create dummy data structure: {dummy_e}")

        except Exception as e:
            logging.error(f"Failed to create data directory {DATA_DIR}: {e}")
            # Consider exiting if the data directory is critical and cannot be created
            # sys.exit(f"Error: Cannot create data directory {DATA_DIR}")

    # --- Create and Show Dashboard ---
    dashboard = PoliceDashboard(initial_officer_id=initial_officer)
    # dashboard.show() # show() is called within move_to_secondary_display or its fallback

    sys.exit(app.exec_())

