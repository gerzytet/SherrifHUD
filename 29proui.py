"""
Police Dashboard UI Application using PyQt5.

Displays data based on file system polling (updates, images) and
simulated GPS with nearest intersection calculation from CSV.
Includes real internet status check and placeholder for real GPS check.
Optimized for an 800x480 reflected display. Forced Fullscreen on Secondary Display.

Improvements Implemented (v34):
- Added console print statements for debugging GPS simulation and intersection calculation.
- Modified to hide ImageDisplayWidget and extend left column text fields when no images are received.
- (Includes previous fixes/features from v33)
- **ImageDisplayWidget.set_image_folder**:
  - Added `self.hide()` when no images are found or the folder doesn’t exist.
  - Added `self.show()` when images are available.
- **ImageDisplayWidget.check_for_new_images**:
  - Updated to hide the widget (`self.hide()`) when the folder is empty, doesn’t exist, or an error occurs.
  - Ensures the widget is shown (`self.show()`) when images are found.
- **PoliceDashboard.update_ui_for_selection**:
  - Adjusts the `main_layout` stretch factors to give the left column (`index 0`) all space (`stretch=1`) and the right column (`index 1`) no space (`stretch=0`) when no images are available.
  - Restores 1:1 stretch factors when images are present.
- **PoliceDashboard.poll_for_updates**:
  - Updates the stretch factors dynamically based on `self.imageDisplay.image_files` to ensure the layout reflects the current image availability.
- **IntersectionInfoWidget.initUI**:
  - Added `self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)` to ensure the widget can expand horizontally when the left column grows.

"""

# --- Standard Library Imports ---
import sys
import random
import re
import os
import time
import csv
import math
import socket 
from datetime import datetime
from glob import glob
import logging 

# --- PyQt5 Imports ---
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QTextEdit, QSizePolicy, QFrame, QPushButton 
)
from PyQt5.QtGui import QFont, QPixmap, QColor, QScreen, QTextOption
from PyQt5.QtCore import Qt, QTimer, QSize, QTime, QPoint, pyqtSignal, QTimeZone, QDateTime

# =============================================================================
# Configuration Constants
# =============================================================================

# --- UI / Officer Configuration ---
DATA_DIR = "police_data"
INTERSECTION_CSV_PATH = "C:/Users/gmax1/Desktop/SherrifHUD-main/intersections.csv"
POLLING_INTERVAL_MS = 1500
GPS_UPDATE_INTERVAL_MS = 10000
IMAGE_CYCLE_INTERVAL_MS = 5000
CRS_EPSG = 3857
CRS_UNITS_TO_FEET = 3.28084
FEET_PER_MILE = 5280.0
DISTANCE_UNIT_THRESHOLD_FT = 1320.0
GPS_LOCK_PROBABILITY = 0.75
SIM_GPS_MOVE_SCALE_DIVISOR = 500.0

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
COLOR_ACCENT = "#00BFFF"
COLOR_SEPARATOR = COLOR_ACCENT
COLOR_BOX_BORDER = COLOR_ACCENT
COLOR_ACTUAL_IMAGE_BORDER = "#FFFFFF"
COLOR_UPDATE_TIMESTAMP = "#00FFFF"
COLOR_TIMESTAMP_TRAFFIC = "#FFFF00"
COLOR_TIMESTAMP_BOLO = "#FFA500"
COLOR_CRITICAL_UPDATE = "#FF0000"
COLOR_CRITICAL_BG = "#400000"
COLOR_GPS_LOCKED = "#00FF00"
COLOR_GPS_NO_LOCK = COLOR_TEXT_SECONDARY
COLOR_CONN_OK = "#00FF00"
COLOR_CONN_BAD = COLOR_TEXT_SECONDARY
COLOR_STATUS_OK_BG = "#003000"
COLOR_STATUS_BAD_BG = "#303030"
COLOR_BUTTON_BG = "#303030"
COLOR_BUTTON_TEXT = COLOR_TEXT_PRIMARY
COLOR_BUTTON_BORDER = COLOR_ACCENT
COLOR_BUTTON_DISABLED_BG = "#505050"
COLOR_BUTTON_DISABLED_TEXT = "#808080"
COLOR_BUTTON_DISABLED_BORDER = "#606060"

# --- Font Settings ---
FONT_FAMILY = "Roboto Condensed"
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

def check_time():
    time_zone = QTimeZone(b"EST")
    date_time = QDateTime.currentDateTime()
    today = date_time.date()
    daylight = QDateTime(today, QTime(6, 0), time_zone)
    night = QDateTime(today, QTime(18, 0), time_zone)
    is_night = date_time >= night or date_time < daylight
    is_dst = time_zone.isDaylightTime(date_time)
    print(f"DST is {'active' if is_dst else 'not active'}")
    return is_night

def swap_color_palette(is_night):
    global COLOR_BACKGROUND, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_ACCENT
    global COLOR_SEPARATOR, COLOR_BOX_BORDER, COLOR_ACTUAL_IMAGE_BORDER
    global COLOR_UPDATE_TIMESTAMP, COLOR_TIMESTAMP_TRAFFIC, COLOR_TIMESTAMP_BOLO
    global COLOR_CRITICAL_UPDATE, COLOR_CRITICAL_BG, COLOR_GPS_LOCKED, COLOR_GPS_NO_LOCK
    global COLOR_CONN_OK, COLOR_CONN_BAD, COLOR_STATUS_OK_BG, COLOR_STATUS_BAD_BG
    global COLOR_BUTTON_BG, COLOR_BUTTON_TEXT, COLOR_BUTTON_BORDER
    global COLOR_BUTTON_DISABLED_BG, COLOR_BUTTON_DISABLED_TEXT, COLOR_BUTTON_DISABLED_BORDER

    if is_night:
        COLOR_BACKGROUND = "#000000"
        COLOR_TEXT_PRIMARY = "#E0E0E0"
        COLOR_TEXT_SECONDARY = "#A0A0A0"
        COLOR_ACCENT = "#00BFFF"
        COLOR_SEPARATOR = COLOR_ACCENT
        COLOR_BOX_BORDER = COLOR_ACCENT
        COLOR_ACTUAL_IMAGE_BORDER = "#FFFFFF"
        COLOR_UPDATE_TIMESTAMP = "#00FFFF"
        COLOR_TIMESTAMP_TRAFFIC = "#FFFF00"
        COLOR_TIMESTAMP_BOLO = "#FFA500"
        COLOR_CRITICAL_UPDATE = "#FF0000"
        COLOR_CRITICAL_BG = "#400000"
        COLOR_GPS_LOCKED = "#00FF00"
        COLOR_GPS_NO_LOCK = COLOR_TEXT_SECONDARY
        COLOR_CONN_OK = "#00FF00"
        COLOR_CONN_BAD = COLOR_TEXT_SECONDARY
        COLOR_STATUS_OK_BG = "#003000"
        COLOR_STATUS_BAD_BG = "#303030"
        COLOR_BUTTON_BG = "#303030"
        COLOR_BUTTON_TEXT = COLOR_TEXT_PRIMARY
        COLOR_BUTTON_BORDER = COLOR_ACCENT
        COLOR_BUTTON_DISABLED_BG = "#505050"
        COLOR_BUTTON_DISABLED_TEXT = "#808080"
        COLOR_BUTTON_DISABLED_BORDER = "#606060"
    else:
        COLOR_BACKGROUND = "#FFFFFF"
        COLOR_TEXT_PRIMARY = "#1A1A1A"
        COLOR_TEXT_SECONDARY = "#606060"
        COLOR_ACCENT = "#00BFFF"
        COLOR_SEPARATOR = COLOR_ACCENT
        COLOR_BOX_BORDER = COLOR_ACCENT
        COLOR_ACTUAL_IMAGE_BORDER = "#000000"
        COLOR_UPDATE_TIMESTAMP = "#00CCCC"
        COLOR_TIMESTAMP_TRAFFIC = "#CC9900"
        COLOR_TIMESTAMP_BOLO = "#E59400"
        COLOR_CRITICAL_UPDATE = "#CC0000"
        COLOR_CRITICAL_BG = "#FFCCCC"
        COLOR_GPS_LOCKED = "#008000"
        COLOR_GPS_NO_LOCK = COLOR_TEXT_SECONDARY
        COLOR_CONN_OK = "#008000"
        COLOR_CONN_BAD = COLOR_TEXT_SECONDARY
        COLOR_STATUS_OK_BG = "#CCFFCC"
        COLOR_STATUS_BAD_BG = "#E0E0E0"
        COLOR_BUTTON_BG = "#D0D0D0"
        COLOR_BUTTON_TEXT = COLOR_TEXT_PRIMARY
        COLOR_BUTTON_BORDER = COLOR_ACCENT
        COLOR_BUTTON_DISABLED_BG = "#B0B0B0"
        COLOR_BUTTON_DISABLED_TEXT = "#808080"
        COLOR_BUTTON_DISABLED_BORDER = "#A0A0A0"
    return

def create_label(text, font_size, bold=False, color=COLOR_TEXT_PRIMARY, alignment=Qt.AlignLeft | Qt.AlignVCenter, parent=None):
    label = QLabel(text, parent=parent)
    font = QFont(FONT_FAMILY, font_size)
    font.setBold(bold)
    label.setFont(font)
    label.setAlignment(alignment)
    label.setStyleSheet(f"color: {color}; background-color: transparent;")
    return label

def create_button(text, font_size, parent=None):
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
            min-width: 30px;
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
    if not officer_id or not isinstance(officer_id, str) or '/' in officer_id or '\\' in officer_id:
        raise ValueError("Invalid Officer ID")
    if not call_id or not isinstance(call_id, str) or '/' in call_id or '\\' in call_id:
        raise ValueError("Invalid Call ID")

    safe_officer_id = "".join(c if c.isalnum() or c in ('_','-') else '_' for c in officer_id)
    safe_call_id = "".join(c if c.isalnum() or c in ('_','-') else '_' for c in call_id)

    call_dir = os.path.join(DATA_DIR, safe_officer_id, safe_call_id)
    image_dir = os.path.join(call_dir, 'images')
    try:
        os.makedirs(image_dir, exist_ok=True)
    except OSError as e:
        logging.error(f"Error creating directory {image_dir}: {e}")
        raise
    return call_dir, image_dir

# Execute Time check and swap color
swap_color_palette(check_time())

# =============================================================================
# Component Widgets
# =============================================================================

class StatusBarWidget(QWidget):
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

        self.gps_text_label = create_label("GPS: ---", FONT_SIZE_STATUS_BAR, color=COLOR_TEXT_SECONDARY, parent=self)
        self.conn_text_label = create_label("NET: ---", FONT_SIZE_STATUS_BAR, color=COLOR_TEXT_SECONDARY, parent=self)
        self.gps_text_label.setStyleSheet(f"color: {COLOR_GPS_NO_LOCK}; background-color: {COLOR_STATUS_BAD_BG}; padding: 1px 3px; border-radius: 3px;")
        self.conn_text_label.setStyleSheet(f"color: {COLOR_CONN_BAD}; background-color: {COLOR_STATUS_BAD_BG}; padding: 1px 3px; border-radius: 3px;")

        self.prev_officer_btn = create_button(f"{ICON_PREV} Off.", FONT_SIZE_NAV_BUTTON, parent=self)
        self.next_officer_btn = create_button(f"Off. {ICON_NEXT}", FONT_SIZE_NAV_BUTTON, parent=self)
        self.prev_call_btn = create_button(f"{ICON_PREV} Call", FONT_SIZE_NAV_BUTTON, parent=self)
        self.next_call_btn = create_button(f"Call {ICON_NEXT}", FONT_SIZE_NAV_BUTTON, parent=self)
        self.nav_label = create_label("Officer: --- / Call: ---", FONT_SIZE_NAV_LABEL, bold=True, alignment=Qt.AlignCenter, parent=self)
        self.nav_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        self.time_label = create_label("00:00:00", FONT_SIZE_STATUS_BAR, color=COLOR_TEXT_PRIMARY, alignment=Qt.AlignRight | Qt.AlignVCenter, parent=self)

        layout.addWidget(self.gps_text_label)
        layout.addWidget(self.conn_text_label)
        layout.addStretch(1)
        layout.addWidget(self.prev_officer_btn)
        layout.addWidget(self.next_officer_btn)
        layout.addSpacing(MAIN_SPACING)
        layout.addWidget(self.nav_label)
        layout.addSpacing(MAIN_SPACING)
        layout.addWidget(self.prev_call_btn)
        layout.addWidget(self.next_call_btn)
        layout.addStretch(1)
        layout.addWidget(self.time_label)

        self.prev_officer_btn.clicked.connect(self.prevOfficerClicked.emit)
        self.next_officer_btn.clicked.connect(self.nextOfficerClicked.emit)
        self.prev_call_btn.clicked.connect(self.prevCallClicked.emit)
        self.next_call_btn.clicked.connect(self.nextCallClicked.emit)

    def update_status(self, gps_locked, conn_ok):
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
        officer_display = officer_id if officer_id else "---"
        call_display = call_id if call_id else "---"
        self.nav_label.setText(f"Officer: {officer_display} / Call: {call_display}")

    def update_button_states(self, can_prev_officer, can_next_officer, can_prev_call, can_next_call):
        self.prev_officer_btn.setEnabled(can_prev_officer)
        self.next_officer_btn.setEnabled(can_next_officer)
        self.prev_call_btn.setEnabled(can_prev_call)
        self.next_call_btn.setEnabled(can_next_call)

class IntersectionInfoWidget(QFrame):
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
        self.data_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.MinimumExpanding)
        layout.addWidget(self.timestamp_label)
        layout.addWidget(self.data_label)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

    def update_data(self, data_string, timestamp):
        self.timestamp_label.setText(f"GPS Fix: {timestamp}")
        self.data_label.setText(data_string if data_string else "Cannot determine intersection.")

class UpdatesLogWidget(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.updates_file_path = None
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
        return f"""
            QTextEdit#updatesTextEdit {{
                background-color: {COLOR_BACKGROUND};
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {border_color};
                border-radius: {BOX_BORDER_RADIUS}px;
                padding: {BOX_PADDING}px;
            }}
            p {{
                margin-top: 0px;
                margin-bottom: {UPDATE_SPACING_PX}px;
                padding: 0px;
                line-height: 110%;
            }}
        """

    def initUI(self):
        self.setObjectName("updatesTextEdit")
        self.setReadOnly(True)
        self.setFont(QFont(FONT_FAMILY, FONT_SIZE_UPDATE_TEXT))
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setWordWrapMode(QTextOption.WrapAnywhere)
        self.setStyleSheet(self._build_style_sheet(self.default_border_color))

    def set_updates_file(self, new_path):
        logging.info(f"UpdatesLogWidget: Setting updates file to {new_path}")
        self.updates_file_path = new_path
        self.last_read_pos = 0
        self.clear()
        self.load_initial_updates()

    def load_initial_updates(self):
        if not self.updates_file_path:
            logging.warning("UpdatesLogWidget: No updates file path set.")
            self.append("<p>No Call Selected</p>")
            return
        if os.path.exists(self.updates_file_path):
            try:
                with open(self.updates_file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    self.last_read_pos = f.tell()
                    logging.info(f"Updates file {self.updates_file_path} found, initial pos: {self.last_read_pos}, lines: {len(lines)}")
                    self.clear()
                    start_index = max(0, len(lines) - 20)
                    for line in lines[start_index:]:
                        line = line.strip()
                        if line: self.process_update_line(line, initial_load=True)
                    self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())
            except Exception as e:
                logging.error(f"Error reading initial updates file {self.updates_file_path}: {e}")
                self.append(f"<p>Error loading updates: {e}</p>")
        else:
            logging.warning(f"Updates file not found: {self.updates_file_path}. Awaiting creation.")
            self.append(f"<p>No updates file found for this call yet.</p>")
            self.last_read_pos = 0

    def check_for_new_updates(self):
        if not self.updates_file_path or not os.path.exists(self.updates_file_path):
            return
        try:
            current_size = os.path.getsize(self.updates_file_path)
            if current_size == self.last_read_pos:
                return
            elif current_size < self.last_read_pos:
                logging.info(f"Updates file {self.updates_file_path} size decreased. Reloading.")
                self.load_initial_updates()
                return
            with open(self.updates_file_path, 'r', encoding='utf-8') as f:
                f.seek(self.last_read_pos)
                new_lines = f.readlines()
                self.last_read_pos = f.tell()
                logging.debug(f"Read {len(new_lines)} new lines from {self.updates_file_path}")
                for line in new_lines:
                    line = line.strip()
                    if line: self.process_update_line(line)
                self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())
        except Exception as e:
            logging.error(f"Error checking for updates file {self.updates_file_path}: {e}")
            self.last_read_pos = 0

    def process_update_line(self, line, initial_load=False):
        timestamp_str = datetime.now().strftime('%H:%M:%S')
        message_text = line
        match = re.match(r"\[(.*?)\]\s*(.*)", line)
        if match:
            extracted_ts_str = match.group(1)
            try:
                dt_obj = datetime.strptime(extracted_ts_str, '%Y-%m-%d %H:%M:%S')
                timestamp_str = dt_obj.strftime('%H:%M:%S')
            except ValueError:
                time_parts = extracted_ts_str.split()
                if len(time_parts) > 0 and ':' in time_parts[-1]:
                    timestamp_str = time_parts[-1]
                else:
                    timestamp_str = extracted_ts_str
            message_text = match.group(2).strip()
        else:
            message_text = line.strip()

        category = 'INFO'
        if any(keyword in message_text.lower() for keyword in CRITICAL_MESSAGE_KEYWORDS):
            category = 'CRITICAL'
        elif "bolo" in message_text.lower():
            category = 'BOLO'
        elif "traffic" in message_text.lower() or "road closure" in message_text.lower():
            category = 'TRAFFIC'

        self.add_message_to_display(message_text, category, timestamp_str, trigger_flash=not initial_load)

    def add_message_to_display(self, message_text, category, timestamp, trigger_flash=True):
        if not message_text:
            return
        prefix = ""
        timestamp_color = COLOR_UPDATE_TIMESTAMP
        pulse_color = None
        pulse_count = 0
        is_critical_category = (category == 'CRITICAL')

        if category == 'TRAFFIC':
            prefix = PREFIX_TRAFFIC + " "
            timestamp_color = COLOR_TIMESTAMP_TRAFFIC
            pulse_color = COLOR_TIMESTAMP_TRAFFIC
            pulse_count = PULSE_COUNT_TRAFFIC
        elif category == 'BOLO':
            prefix = PREFIX_BOLO + " "
            timestamp_color = COLOR_TIMESTAMP_BOLO
            pulse_color = COLOR_TIMESTAMP_BOLO
            pulse_count = PULSE_COUNT_BOLO
        elif category == 'INFO':
            prefix = PREFIX_INFO + " "

        is_critical_keyword = any(keyword in message_text.lower() for keyword in CRITICAL_MESSAGE_KEYWORDS)
        is_critical = is_critical_category or is_critical_keyword

        icon = PREFIX_CRITICAL + " " if is_critical else prefix
        span_class = "critical_message" if is_critical else "message"
        inline_style = ""

        if is_critical:
            inline_style = f'style="color: {COLOR_CRITICAL_UPDATE}; background-color: {COLOR_CRITICAL_BG}; padding: 0px 2px;"'
            timestamp_color = COLOR_CRITICAL_UPDATE
            pulse_color = COLOR_CRITICAL_UPDATE
            pulse_count = PULSE_COUNT_CRITICAL
        else:
            inline_style = f'style="color: {COLOR_TEXT_PRIMARY};"'

        html_message = (
            f'<p style="margin-bottom: {UPDATE_SPACING_PX}px; margin-top: 0px; padding: 0px;">'
            f'<span style="color: {timestamp_color}; font-size: {FONT_SIZE_TIMESTAMP}pt;">[{timestamp}]</span><br>'
            f'<span class="{span_class}" {inline_style}>{icon}{message_text}</span>'
            f'</p>'
        )

        self.append(html_message)
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())

        if trigger_flash and pulse_color and pulse_count > 0:
            self.start_flash(pulse_color, pulse_count)

    def start_flash(self, color, pulse_on_count):
        if self.is_flashing:
            return
        self.flash_color = color
        self.pulse_max_on_count = pulse_on_count
        self.pulse_count = 0
        self.is_flashing = True
        self.flash_timer.start(self.pulse_interval)
        self._do_flash_pulse()

    def _do_flash_pulse(self):
        if not self.is_flashing:
            self.flash_timer.stop()
            return
        self.pulse_count += 1
        total_ticks = self.pulse_max_on_count * 2
        if self.pulse_count > total_ticks:
            self.flash_timer.stop()
            self.setStyleSheet(self._build_style_sheet(self.default_border_color))
            self.is_flashing = False
        elif self.pulse_count % 2 == 1:
            self.setStyleSheet(self._build_style_sheet(self.flash_color))
        else:
            self.setStyleSheet(self._build_style_sheet(self.default_border_color))

class ImageDisplayWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.image_folder_path = None
        self.image_files = []
        self.current_image_index = -1
        self.current_pixmap = None
        self.image_label = None
        self.image_description_label = None
        self.image_border_overlay_label = None
        self.last_scan_time = 0
        self.image_cycle_timer = QTimer(self)
        self.image_cycle_timer.timeout.connect(self.display_next_image)
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(RIGHT_COLUMN_SPACING)

        self.image_label = QLabel(ICON_IMAGE_LOADING, self)
        self.image_label.setObjectName("imageLabel")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.image_label.setStyleSheet(f"""QLabel#imageLabel {{ color: {COLOR_TEXT_SECONDARY}; font-size: {FONT_SIZE_IMAGE_PLACEHOLDER}pt; background-color: {COLOR_BACKGROUND}; border: 1px solid {COLOR_BOX_BORDER}; border-radius: {BOX_BORDER_RADIUS}px; }}""")
        layout.addWidget(self.image_label, 1)

        self.image_description_label = create_label("No Image Available", FONT_SIZE_IMAGE_DESC, color=COLOR_TEXT_SECONDARY, alignment=Qt.AlignCenter, parent=self)
        self.image_description_label.setWordWrap(True)
        layout.addWidget(self.image_description_label)

        self.image_border_overlay_label = QLabel(self.image_label)
        self.image_border_overlay_label.setObjectName("imageBorderOverlay")
        self.image_border_overlay_label.setStyleSheet(f"border: {ACTUAL_IMAGE_BORDER_WIDTH}px solid {COLOR_ACTUAL_IMAGE_BORDER}; background-color: transparent;")
        self.image_border_overlay_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.image_border_overlay_label.hide()

    def set_image_folder(self, new_path):
        logging.info(f"ImageDisplayWidget: Setting image folder to {new_path}")
        self.image_folder_path = new_path
        self.image_files = []
        self.current_image_index = -1
        self.current_pixmap = None
        self.last_scan_time = 0
        self.image_cycle_timer.stop()

        folder_exists = self.check_for_new_images(initial_load=True)

        if self.image_files:
            self.image_cycle_timer.start(IMAGE_CYCLE_INTERVAL_MS)
            self.show()
        elif not folder_exists:
            self.update_display(None, "Image Folder Not Found", True)
            self.hide()
        else:
            self.update_display(None, "No Images Found", True)
            self.hide()

    def check_for_new_images(self, initial_load=False):
        if not self.image_folder_path:
            logging.debug("ImageDisplayWidget: Image folder path not set.")
            if self.image_files:
                self.image_files = []
                self.current_image_index = -1
                self.update_display(None, "No Call Selected", True)
            self.hide()
            self.image_cycle_timer.stop()
            return False

        if not os.path.isdir(self.image_folder_path):
            logging.warning(f"ImageDisplayWidget: Image folder not found: {self.image_folder_path}")
            if self.image_files:
                self.image_files = []
                self.current_image_index = -1
                self.update_display(None, "Image Folder Not Found", True)
            self.hide()
            self.image_cycle_timer.stop()
            return False

        try:
            current_files = sorted(
                [os.path.join(self.image_folder_path, f) for f in os.listdir(self.image_folder_path)
                 if os.path.isfile(os.path.join(self.image_folder_path, f)) and f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))],
                key=os.path.getmtime
            )

            folder_updated = False
            latest_mod_time = os.path.getmtime(current_files[-1]) if current_files else 0

            if len(current_files) != len(self.image_files) or latest_mod_time > self.last_scan_time:
                folder_updated = True
                logging.info(f"Image folder {self.image_folder_path} updated. Found {len(current_files)} images.")
                self.image_files = current_files
                self.last_scan_time = latest_mod_time

                if self.image_files:
                    if initial_load or self.current_image_index == -1:
                        self.current_image_index = len(self.image_files) - 1
                        self.load_image(self.current_image_index)
                    elif self.current_image_index >= len(self.image_files):
                        self.current_image_index = len(self.image_files) - 1
                        self.load_image(self.current_image_index)
                    self.show()
                    self.image_cycle_timer.start(IMAGE_CYCLE_INTERVAL_MS)
                else:
                    self.current_image_index = -1
                    self.update_display(None, "No Images Found", True)
                    self.hide()
                    self.image_cycle_timer.stop()

            return True

        except Exception as e:
            logging.error(f"Error scanning image folder {self.image_folder_path}: {e}")
            self.image_files = []
            self.current_image_index = -1
            self.update_display(None, "Error Scanning Folder", True)
            self.hide()
            self.image_cycle_timer.stop()
            return True

    def display_next_image(self):
        if not self.image_files or len(self.image_files) < 2:
            return
        self.current_image_index = (self.current_image_index + 1) % len(self.image_files)
        self.load_image(self.current_image_index)

    def load_image(self, index):
        if not self.image_files or not (0 <= index < len(self.image_files)):
            self.update_display(None, "No Image Available", True)
            return
        filepath = self.image_files[index]
        pixmap = QPixmap(filepath)
        is_error = pixmap.isNull()

        display_desc = f"({index + 1}/{len(self.image_files)}) "
        base_name = os.path.basename(filepath)
        match = re.match(r"(\d{8}_\d{6}_\d{6})_(.*)", base_name)
        if match:
            try:
                ts = datetime.strptime(match.group(1), "%Y%m%d_%H%M%S_%f")
                display_desc += f"{match.group(2)} [{ts.strftime('%H:%M:%S')}]"
            except ValueError:
                display_desc += base_name
        else:
            display_desc += base_name

        if is_error:
            logging.warning(f"Failed to load image: {filepath}")
            display_desc = f"Error loading: {base_name}"

        self.update_display(pixmap if not is_error else None, display_desc, is_error)

    def update_display(self, pixmap, description, is_error):
        self.current_pixmap = pixmap if pixmap and not pixmap.isNull() else None
        self.image_description_label.setText(description if description else "No Description")
        self.image_description_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY if is_error else COLOR_TEXT_PRIMARY};")

        error_style = f"""QLabel#imageLabel {{ color: {COLOR_TEXT_SECONDARY}; font-size: {FONT_SIZE_IMAGE_PLACEHOLDER}pt; background-color: {COLOR_BACKGROUND}; border: 1px solid {COLOR_BOX_BORDER}; border-radius: {BOX_BORDER_RADIUS}px; qproperty-alignment: 'AlignCenter'; }}"""
        loaded_style = f"""QLabel#imageLabel {{ color: transparent; background-color: {COLOR_BACKGROUND}; border: 1px solid {COLOR_BOX_BORDER}; border-radius: {BOX_BORDER_RADIUS}px; }}"""

        if is_error or not self.current_pixmap:
            self.image_label.setPixmap(QPixmap())
            self.image_label.setText(ICON_IMAGE_ERROR if is_error else ICON_IMAGE_LOADING)
            self.image_label.setStyleSheet(error_style)
            if self.image_border_overlay_label:
                self.image_border_overlay_label.hide()
        else:
            self.image_label.setText("")
            self.image_label.setStyleSheet(loaded_style)
            self.scale_and_position_overlay()

        self.image_label.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.scale_and_position_overlay()

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(50, self.scale_and_position_overlay)

    def scale_and_position_overlay(self):
        if not self.image_label or not self.image_border_overlay_label:
            return
        if not self.current_pixmap:
            self.image_label.setPixmap(QPixmap())
            self.image_border_overlay_label.hide()
            return
        label_size = self.image_label.size()
        if label_size.width() <= 0 or label_size.height() <= 0:
            self.image_border_overlay_label.hide()
            return
        scaled_pixmap = self.current_pixmap.scaled(label_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.image_label.setPixmap(scaled_pixmap)
        scaled_size = scaled_pixmap.size()
        x_offset = (label_size.width() - scaled_size.width()) // 2
        y_offset = (label_size.height() - scaled_size.height()) // 2
        overlay_x = x_offset
        overlay_y = y_offset
        overlay_width = scaled_size.width()
        overlay_height = scaled_size.height()
        border_w = ACTUAL_IMAGE_BORDER_WIDTH * 2
        overlay_width = max(0, min(overlay_width, label_size.width() - overlay_x - border_w//2))
        overlay_height = max(0, min(overlay_height, label_size.height() - overlay_y - border_w//2))
        self.image_border_overlay_label.setGeometry(overlay_x, overlay_y, overlay_width, overlay_height)
        self.image_border_overlay_label.show()
        self.image_border_overlay_label.raise_()

# =============================================================================
# Main Application Window
# =============================================================================

class PoliceDashboard(QWidget):
    def __init__(self, initial_officer_id=None):
        super().__init__()
        self.officers = []
        self.current_officer_index = -1
        self.calls = []
        self.current_call_index = -1
        self.initial_officer_id_preference = initial_officer_id
        self.current_sim_coords = None
        self.intersections_data = self.load_intersections(INTERSECTION_CSV_PATH)
        self.intersection_bounds = self.calculate_bounds(self.intersections_data)
        self.initUI()
        self.scan_and_load_initial_data()
        self.setup_timers()
        self.move_to_secondary_display()

    def initUI(self):
        self.setWindowTitle("Police Dashboard")
        self.setStyleSheet(self.build_base_style_sheet())
        overall_layout = QVBoxLayout(self)
        overall_layout.setContentsMargins(0, 0, 0, 0)
        overall_layout.setSpacing(0)

        self.statusBar = StatusBarWidget(self)
        overall_layout.addWidget(self.statusBar)

        separator = QFrame(self)
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet(f"border: {SEPARATOR_HEIGHT}px solid {COLOR_SEPARATOR}; margin-left: {MAIN_MARGINS}px; margin-right: {MAIN_MARGINS}px;")
        overall_layout.addWidget(separator)

        main_content_widget = QWidget(self)
        main_content_widget.setStyleSheet("background-color: transparent;")
        self.main_layout = QHBoxLayout(main_content_widget)
        self.main_layout.setContentsMargins(MAIN_MARGINS, MAIN_MARGINS, MAIN_MARGINS, MAIN_MARGINS)
        self.main_layout.setSpacing(MAIN_SPACING)
        overall_layout.addWidget(main_content_widget, 1)

        self.left_column_layout = QVBoxLayout()
        self.left_column_layout.setSpacing(LEFT_COLUMN_SPACING)
        self.main_layout.addLayout(self.left_column_layout, 1)

        intersection_title = create_label("Nearest Intersection", FONT_SIZE_TITLE, bold=True, color=COLOR_ACCENT, parent=main_content_widget)
        self.intersectionInfo = IntersectionInfoWidget(main_content_widget)
        self.intersectionInfo.setObjectName("intersectionContainer")
        self.left_column_layout.addWidget(intersection_title)
        self.left_column_layout.addWidget(self.intersectionInfo)

        self.left_column_layout.addSpacing(MAIN_SPACING)
        updates_title = create_label("Important Updates", FONT_SIZE_TITLE, bold=True, color=COLOR_ACCENT, parent=main_content_widget)
        self.updatesLog = UpdatesLogWidget(parent=main_content_widget)
        self.left_column_layout.addWidget(updates_title)
        self.left_column_layout.addWidget(self.updatesLog, 1)

        self.imageDisplay = ImageDisplayWidget(parent=main_content_widget)
        self.main_layout.addWidget(self.imageDisplay, 1)

        self.statusBar.prevOfficerClicked.connect(self.select_previous_officer)
        self.statusBar.nextOfficerClicked.connect(self.select_next_officer)
        self.statusBar.prevCallClicked.connect(self.select_previous_call)
        self.statusBar.nextCallClicked.connect(self.select_next_call)

    def build_base_style_sheet(self):
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
            .message {{
            }}
            .critical_message {{
                font-weight: bold;
            }}
        """

    def setup_timers(self):
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
        if self.statusBar:
            current_time = QTime.currentTime()
            time_text = current_time.toString("HH:mm:ss")
            self.statusBar.update_time(time_text)

    def poll_for_updates(self):
        officer_changed = self.scan_officers()
        call_changed = False
        current_officer_id = self.officers[self.current_officer_index] if self.current_officer_index != -1 else None
        if current_officer_id:
            call_changed = self.scan_calls(current_officer_id)

        if officer_changed or call_changed:
            logging.info(f"Directory structure change detected (Officer: {officer_changed}, Call: {call_changed}). Updating UI selection state.")
            self.update_ui_for_selection(reload_widgets=False)

        if self.updatesLog:
            self.updatesLog.check_for_new_updates()
        if self.imageDisplay:
            image_folder_updated = self.imageDisplay.check_for_new_images()
            if self.imageDisplay.image_files:
                self.main_layout.setStretch(0, 1)
                self.main_layout.setStretch(1, 1)
            else:
                self.main_layout.setStretch(0, 1)
                self.main_layout.setStretch(1, 0)
            if not image_folder_updated and self.imageDisplay.image_files and not self.imageDisplay.image_cycle_timer.isActive():
                self.imageDisplay.image_cycle_timer.start(IMAGE_CYCLE_INTERVAL_MS)

        internet_ok_status = self.check_internet_connection()
        gps_locked_status = self.check_gps_lock()

        if self.statusBar:
            self.statusBar.update_status(gps_locked_status, internet_ok_status)

    def scan_officers(self):
        try:
            if not os.path.isdir(DATA_DIR):
                logging.warning(f"Data directory {DATA_DIR} not found.")
                if self.officers:
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
                new_index = -1
                if old_officer_id in self.officers:
                    new_index = self.officers.index(old_officer_id)
                elif self.officers:
                    new_index = 0
                self.current_officer_index = new_index
                if self.current_officer_index != -1:
                    self.load_calls_for_current_officer()
                else:
                    self.calls = []
                    self.current_call_index = -1
                return True
            return False
        except Exception as e:
            logging.error(f"Error scanning officer directories in {DATA_DIR}: {e}")
            if self.officers:
                self.officers = []
                self.current_officer_index = -1
                self.calls = []
                self.current_call_index = -1
                return True
            return False

    def scan_calls(self, officer_id):
        if not officer_id:
            if self.calls:
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

            entries = sorted([
                d for d in os.listdir(officer_dir)
                if os.path.isdir(os.path.join(officer_dir, d)) and d.lower() != 'images'
            ])

            if entries != self.calls:
                logging.info(f"Call list for {officer_id} changed: {self.calls} -> {entries}")
                old_call_id = self.calls[self.current_call_index] if self.current_call_index != -1 else None
                self.calls = entries
                new_index = -1
                if old_call_id in self.calls:
                    new_index = self.calls.index(old_call_id)
                elif self.calls:
                    new_index = 0
                self.current_call_index = new_index
                return True
            return False
        except Exception as e:
            logging.error(f"Error scanning call directories in {officer_dir}: {e}")
            if self.calls:
                self.calls = []
                self.current_call_index = -1
                return True
            return False

    def scan_and_load_initial_data(self):
        logging.info("Performing initial scan and load...")
        self.scan_officers()
        if self.initial_officer_id_preference and self.initial_officer_id_preference in self.officers:
            self.current_officer_index = self.officers.index(self.initial_officer_id_preference)
            logging.info(f"Initial officer preference '{self.initial_officer_id_preference}' found at index {self.current_officer_index}.")
        elif self.officers:
            self.current_officer_index = 0
            logging.info(f"Initial officer preference not found or not set. Defaulting to first officer: {self.officers[0]}")
        else:
            self.current_officer_index = -1
            logging.warning("No officer directories found on initial scan.")

        if self.current_officer_index != -1:
            self.load_calls_for_current_officer()
        else:
            self.calls = []
            self.current_call_index = -1

        self.update_ui_for_selection(reload_widgets=True)

    def load_calls_for_current_officer(self):
        if self.current_officer_index == -1:
            self.calls = []
            self.current_call_index = -1
            return
        officer_id = self.officers[self.current_officer_index]
        logging.info(f"Loading calls for officer: {officer_id}")
        self.scan_calls(officer_id)

    def select_previous_officer(self):
        if not self.officers or len(self.officers) < 2:
            return
        self.current_officer_index = (self.current_officer_index - 1 + len(self.officers)) % len(self.officers)
        logging.info(f"Navigating to previous officer: Index {self.current_officer_index} ({self.officers[self.current_officer_index]})")
        self.load_calls_for_current_officer()
        self.update_ui_for_selection(reload_widgets=True)

    def select_next_officer(self):
        if not self.officers or len(self.officers) < 2:
            return
        self.current_officer_index = (self.current_officer_index + 1) % len(self.officers)
        logging.info(f"Navigating to next officer: Index {self.current_officer_index} ({self.officers[self.current_officer_index]})")
        self.load_calls_for_current_officer()
        self.update_ui_for_selection(reload_widgets=True)

    def select_previous_call(self): 
        if not self.calls or len(self.calls) < 2:
            return
        self.current_call_index = (self.current_call_index - 1 + len(self.calls)) % len(self.calls)
        logging.info(f"Navigating to previous call: Index {self.current_call_index} ({self.calls[self.current_call_index]})")
        self.update_ui_for_selection(reload_widgets=True)

    def select_next_call(self):
        if not self.calls or len(self.calls) < 2:
            return
        self.current_call_index = (self.current_call_index + 1) % len(self.calls)
        logging.info(f"Navigating to next call: Index {self.current_call_index} ({self.calls[self.current_call_index]})")
        self.update_ui_for_selection(reload_widgets=True)

    def update_ui_for_selection(self, reload_widgets=True):
        officer_id = self.officers[self.current_officer_index] if self.current_officer_index != -1 else None
        call_id = self.calls[self.current_call_index] if self.current_call_index != -1 else None

        logging.info(f"Updating UI Display for Officer: {officer_id}, Call: {call_id}")

        if self.statusBar:
            self.statusBar.update_navigation_label(officer_id, call_id)
            can_prev_officer = len(self.officers) > 1
            can_next_officer = len(self.officers) > 1
            can_prev_call = len(self.calls) > 1
            can_next_call = len(self.calls) > 1
            self.statusBar.update_button_states(can_prev_officer, can_next_officer, can_prev_call, can_next_call)

        if reload_widgets:
            if officer_id and call_id:
                try:
                    call_dir, images_path = get_call_dir(officer_id, call_id)
                    updates_path = os.path.join(call_dir, 'updates.txt')
                    if self.updatesLog:
                        self.updatesLog.set_updates_file(updates_path)
                    if self.imageDisplay:
                        self.imageDisplay.set_image_folder(images_path)
                        if self.imageDisplay.image_files:
                            self.main_layout.setStretch(0, 1)
                            self.main_layout.setStretch(1, 1)
                        else:
                            self.main_layout.setStretch(0, 1)
                            self.main_layout.setStretch(1, 0)
                except ValueError as ve:
                    logging.error(f"Cannot update widgets, invalid ID: {ve}")
                    if self.updatesLog:
                        self.updatesLog.set_updates_file(None)
                        self.updatesLog.setText(f"Error: Invalid ID ({ve})")
                    if self.imageDisplay:
                        self.imageDisplay.set_image_folder(None)
                        self.imageDisplay.update_display(None, f"Error: Invalid ID", True)
                        self.main_layout.setStretch(0, 1)
                        self.main_layout.setStretch(1, 0)
                except Exception as e:
                    logging.error(f"Error updating widgets for {officer_id}/{call_id}: {e}")
                    if self.updatesLog:
                        self.updatesLog.set_updates_file(None)
                        self.updatesLog.setText(f"Error loading data.")
                    if self.imageDisplay:
                        self.imageDisplay.set_image_folder(None)
                        self.imageDisplay.update_display(None, f"Error loading images", True)
                        self.main_layout.setStretch(0, 1)
                        self.main_layout.setStretch(1, 0)
            else:
                logging.info("No valid officer/call selected, clearing widgets.")
                if self.updatesLog:
                    self.updatesLog.set_updates_file(None)
                    self.updatesLog.setText("<p>No Officer/Call selected.</p>")
                if self.imageDisplay:
                    self.imageDisplay.set_image_folder(None)
                    self.imageDisplay.update_display(None, "No Officer/Call selected", True)
                    self.main_layout.setStretch(0, 1)
                    self.main_layout.setStretch(1, 0)

        QApplication.processEvents()

    def load_intersections(self, csv_path):
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
                        name_b = row['name_b'].strip()
                        name_a = row['name_a'].strip()
                        display_name = f"{name_a} & {name_b}" if name_b and name_b != "/" else name_a
                        display_name = display_name.replace(" / ", " & ")
                        intersection_id = row['id']
                        data.append((intersection_id, display_name, x, y))
                    except (ValueError, KeyError, TypeError) as e:
                        logging.warning(f"Skipping row {i+1} in {csv_path} due to error: {row} - {e}")
            logging.info(f"Loaded {len(data)} intersections from {csv_path}.")
        except Exception as e:
            logging.error(f"Error reading intersection file {csv_path}: {e}")
        return data

    def calculate_bounds(self, intersection_data):
        if not intersection_data:
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
            return {'min_x': -9135000, 'max_x': -9115000, 'min_y': 3240000, 'max_y': 3270000}

    def update_nearest_intersection(self):
        if not self.intersectionInfo:
            return
        timestamp = datetime.now().strftime('%H:%M:%S')
        if not self.intersections_data:
            self.intersectionInfo.update_data("Intersection data not loaded.", timestamp)
            return
        current_coords = self.simulate_gps_coordinates()
        if not current_coords:
            self.intersectionInfo.update_data("GPS Unavailable", timestamp)
            return
        current_x, current_y = current_coords
        print(f"[{timestamp}] DEBUG: Sim GPS Coords: ({current_x:.2f}, {current_y:.2f})")
        nearest_info, min_dist_units = self.find_nearest_intersection(current_x, current_y)
        if nearest_info:
            intersection_id, name, intersection_x, intersection_y = nearest_info
            dist_feet, direction = self.calculate_distance_and_direction(current_x, current_y, intersection_x, intersection_y)
            print(f"[{timestamp}] DEBUG: Closest Intersection: ID={intersection_id}, Name='{name}', Coords=({intersection_x:.2f}, {intersection_y:.2f}), Dist={min_dist_units:.1f} units")
            if direction == "At Location":
                display_string = f"At {name}"
            elif dist_feet < DISTANCE_UNIT_THRESHOLD_FT:
                display_string = f"{dist_feet:.0f}ft {direction} of {name}"
            else:
                dist_miles = dist_feet / FEET_PER_MILE
                display_string = f"{dist_miles:.1f}mi {direction} of {name}"
            print(f"[{timestamp}] DEBUG: UI Output String: '{display_string}'")
        else:
            display_string = "Calculating..."
            logging.warning("Could not find nearest intersection.")
            print(f"[{timestamp}] DEBUG: Could not find nearest intersection.")
        self.intersectionInfo.update_data(display_string, timestamp)
        print("-" * 30)

    def simulate_gps_coordinates(self):
        if not self.intersection_bounds:
            logging.warning("Intersection bounds not calculated for sim coords.")
            return None
        if self.current_sim_coords:
            x_range = self.intersection_bounds['max_x'] - self.intersection_bounds['min_x']
            y_range = self.intersection_bounds['max_y'] - self.intersection_bounds['min_y']
            move_scale_x = x_range / SIM_GPS_MOVE_SCALE_DIVISOR if SIM_GPS_MOVE_SCALE_DIVISOR > 0 else 0
            move_scale_y = y_range / SIM_GPS_MOVE_SCALE_DIVISOR if SIM_GPS_MOVE_SCALE_DIVISOR > 0 else 0
            new_x = self.current_sim_coords[0] + random.uniform(-move_scale_x, move_scale_x)
            new_y = self.current_sim_coords[1] + random.uniform(-move_scale_y, move_scale_y)
            new_x = max(self.intersection_bounds['min_x'], min(new_x, self.intersection_bounds['max_x']))
            new_y = max(self.intersection_bounds['min_y'], min(new_y, self.intersection_bounds['max_y']))
            self.current_sim_coords = (new_x, new_y)
        else:
            start_x = (self.intersection_bounds['min_x'] + self.intersection_bounds['max_x']) / 2
            start_y = (self.intersection_bounds['min_y'] + self.intersection_bounds['max_y']) / 2
            self.current_sim_coords = (start_x, start_y)
            logging.info(f"Initial sim coords set: {self.current_sim_coords}")
        return self.current_sim_coords

    def find_nearest_intersection(self, current_x, current_y):
        if not self.intersections_data:
            return None, float('inf')
        min_dist_sq = float('inf')
        nearest_intersection_info = None
        for intersection_id, name, x, y in self.intersections_data:
            dist_sq = (x - current_x)**2 + (y - current_y)**2
            if dist_sq < min_dist_sq:
                min_dist_sq = dist_sq
                nearest_intersection_info = (intersection_id, name, x, y)
        min_dist = math.sqrt(min_dist_sq) if nearest_intersection_info else float('inf')
        return nearest_intersection_info, min_dist

    def calculate_distance_and_direction(self, x1, y1, x2, y2):
        dx = x2 - x1
        dy = y2 - y1
        dist_units = math.sqrt(dx**2 + dy**2)
        dist_feet = dist_units * CRS_UNITS_TO_FEET
        if dist_feet < 10.0:
            return dist_feet, "At Location"
        angle_rad = math.atan2(dy, dx)
        angle_deg = math.degrees(angle_rad)
        bearing = (90 - angle_deg + 360) % 360
        directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW", "N"]
        index = round(bearing / 45) % 8
        direction_str = directions[index]
        return dist_feet, direction_str

    def check_internet_connection(self, host="8.8.8.8", port=53, timeout=1):
        try:
            socket.setdefaulttimeout(timeout)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
            return True
        except socket.error:
            return False

    def check_gps_lock(self):
        has_lock = random.random() < GPS_LOCK_PROBABILITY
        return has_lock

    def move_to_secondary_display(self):
        screens = QApplication.screens()
        logging.info(f"Detected {len(screens)} screen(s).")
        if len(screens) > 1:
            secondary_screen = screens[1]
            logging.info(f"Attempting to move to secondary screen: {secondary_screen.name()}")
            screen_geometry = secondary_screen.geometry()
            self.setGeometry(screen_geometry)
            self.showFullScreen()
            logging.info(f"Window should be fullscreen on {secondary_screen.name()}")
        else:
            logging.info("Only one screen detected, showing fullscreen on primary screen.")
            self.showFullScreen()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.imageDisplay:
            QTimer.singleShot(50, self.imageDisplay.scale_and_position_overlay)

    def showEvent(self, event):
        super().showEvent(event)
        if self.imageDisplay:
            QTimer.singleShot(100, self.imageDisplay.scale_and_position_overlay)

# =============================================================================
# Main Execution
# =============================================================================
if __name__ == '__main__':
    app = QApplication(sys.argv)
    initial_officer = None
    if len(sys.argv) > 1:
        initial_officer = sys.argv[1]
        logging.info(f"Command line argument provided for initial officer: {initial_officer}")
        check_time()
    if not os.path.exists(DATA_DIR):
        try:
            os.makedirs(DATA_DIR)
            logging.info(f"Created data directory: {DATA_DIR}")
            dummy_officer = initial_officer if initial_officer else "Officer_Test"
            dummy_call = "CALL_001"
            try:
                dummy_call_dir, dummy_img_dir = get_call_dir(dummy_officer, dummy_call)
                dummy_updates_path = os.path.join(dummy_call_dir, 'updates.txt')
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

    dashboard = PoliceDashboard(initial_officer_id=initial_officer)
    sys.exit(app.exec_())


