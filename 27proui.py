# -*- coding: utf-8 -*-
"""
Police Dashboard UI Application using PyQt5.

Displays data based on file system polling for a specific officer ID.
Optimized for an 800x480 reflected display. Forced Fullscreen on Secondary Display.

Improvements Implemented (v26):
- Fixed AttributeError for mock status variables. (Attribute Fix)
- Replaced mock data cycling with file system polling for updates and images.
- UI now monitors a specific OFFICER_ID's data directory.
- Added simple file polling mechanism using QTimer.
- Removed mock data lists and related cycling logic.
- (Includes previous fixes/features from v24)
"""

# --- Standard Library Imports ---
import sys
import random
import re
import os # Added for file system operations
import time # Added for modification time checking
from datetime import datetime
from glob import glob # To find image files

# --- PyQt5 Imports ---
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QTextEdit, QSizePolicy, QFrame
)
from PyQt5.QtGui import QFont, QPixmap, QColor, QScreen, QTextOption
from PyQt5.QtCore import Qt, QTimer, QSize, QTime, QPoint

# =============================================================================
# Configuration Constants
# =============================================================================

# --- UI / Officer Configuration ---
OFFICER_ID = "Officer_A"  # <<<--- SET THE ID FOR THIS UI INSTANCE
DATA_DIR = "police_data"  # <<<--- Base directory for all officer data
POLLING_INTERVAL_MS = 1500 # Check for file changes every 1.5 seconds

# --- Update Settings ---
# UPDATE_INTERVAL_MS = 3500 # No longer needed for mock cycling
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

# --- Font Settings ---
FONT_FAMILY = "Roboto Condensed"
FONT_SIZE_STATUS_BAR = 11
FONT_SIZE_TITLE = 18
FONT_SIZE_INTERSECTION_DATA = 13 # Intersection data is now static
FONT_SIZE_UPDATE_TEXT = 11
FONT_SIZE_TIMESTAMP = 9
FONT_SIZE_IMAGE_DESC = 10
FONT_SIZE_IMAGE_PLACEHOLDER = 48

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

# --- Icons & Prefixes ---
ICON_IMAGE_LOADING = "📷"
ICON_IMAGE_ERROR = "❌"
PREFIX_CRITICAL = "⚠️"
PREFIX_INFO = "[I]" # Default prefix if not specified in file
PREFIX_TRAFFIC = "[T]"
PREFIX_BOLO = "[B]"

# --- Keywords for Critical Highlighting (applied after prefix) ---
CRITICAL_MESSAGE_KEYWORDS = ["backup", "suspicious", "alert", "emergency", "pursuit"]

# =============================================================================
# Helper Functions
# =============================================================================

def create_label(text, font_size, bold=False, color=COLOR_TEXT_PRIMARY, alignment=Qt.AlignLeft | Qt.AlignVCenter, parent=None):
    """ Helper function to create and configure a QLabel. """
    label = QLabel(text, parent=parent)
    font = QFont(FONT_FAMILY, font_size)
    font.setBold(bold)
    label.setFont(font)
    label.setAlignment(alignment)
    label.setStyleSheet(f"color: {color}; background-color: transparent;")
    return label

# =============================================================================
# Component Widgets
# =============================================================================

class StatusBarWidget(QWidget):
    """ Widget for the top status bar. """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()
        # Status state is now managed by the parent PoliceDashboard

    def initUI(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(MAIN_MARGINS, 2, MAIN_MARGINS, 2)
        layout.setSpacing(MAIN_SPACING)
        self.gps_text_label = create_label("GPS: ---", FONT_SIZE_STATUS_BAR, color=COLOR_TEXT_SECONDARY, parent=self)
        self.conn_text_label = create_label("NET: ---", FONT_SIZE_STATUS_BAR, color=COLOR_TEXT_SECONDARY, parent=self)
        self.time_label = create_label("00:00:00", FONT_SIZE_STATUS_BAR, color=COLOR_TEXT_PRIMARY, alignment=Qt.AlignRight | Qt.AlignVCenter, parent=self)
        # Initial style set here, updated by update_status
        self.gps_text_label.setStyleSheet(f"color: {COLOR_GPS_NO_LOCK}; background-color: {COLOR_STATUS_BAD_BG}; padding: 1px 3px; border-radius: 3px;")
        self.conn_text_label.setStyleSheet(f"color: {COLOR_CONN_BAD}; background-color: {COLOR_STATUS_BAD_BG}; padding: 1px 3px; border-radius: 3px;")
        layout.addWidget(self.gps_text_label)
        layout.addSpacing(MAIN_SPACING)
        layout.addWidget(self.conn_text_label)
        layout.addStretch(1)
        layout.addWidget(self.time_label)

    def update_status(self, gps_locked, conn_ok):
        """ Updates status indicators based on parent state. """
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


class IntersectionInfoWidget(QFrame):
    """ Widget for displaying intersection information. (Now Static) """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()

    def initUI(self):
        self.setObjectName("intersectionContainer")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(BOX_PADDING, BOX_PADDING, BOX_PADDING, BOX_PADDING)
        layout.setSpacing(INTERSECTION_SPACING)
        self.timestamp_label = create_label("---", FONT_SIZE_TIMESTAMP, color=COLOR_UPDATE_TIMESTAMP, parent=self)
        self.data_label = create_label("Intersection: N/A", FONT_SIZE_INTERSECTION_DATA, color=COLOR_TEXT_PRIMARY, parent=self)
        self.data_label.setWordWrap(True)
        self.data_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.data_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.MinimumExpanding)
        layout.addWidget(self.timestamp_label)
        layout.addWidget(self.data_label)

    def update_data(self, data_string, timestamp):
        self.timestamp_label.setText(f"Updated: {timestamp}") # Or keep static
        self.data_label.setText(data_string if data_string else "Intersection: N/A")


class UpdatesLogWidget(QTextEdit):
    """ Widget for displaying the updates log with border pulse. Reads from file. """
    def __init__(self, updates_file_path, parent=None):
        super().__init__(parent)
        self.updates_file_path = updates_file_path
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
        self.load_initial_updates()

    def _build_style_sheet(self, border_color):
        return f"""
            QTextEdit#updatesTextEdit {{
                background-color: {COLOR_BACKGROUND}; color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {border_color}; border-radius: {BOX_BORDER_RADIUS}px;
                padding: {BOX_PADDING}px;
            }}
            p {{ margin-top: 0px; margin-bottom: {UPDATE_SPACING_PX}px; padding: 0px; line-height: 110%; }}
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

    def load_initial_updates(self):
        if os.path.exists(self.updates_file_path):
            try:
                with open(self.updates_file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    self.last_read_pos = f.tell()
                    print(f"Updates file found, initial position set to {self.last_read_pos}")
                    # Optionally display existing content on startup
                    # lines = content.strip().split('\n')
                    # for line in lines[-20:]: # Display last 20 lines maybe?
                    #    if line: self.process_update_line(line)
            except Exception as e:
                print(f"Error reading initial updates file {self.updates_file_path}: {e}")
        else:
             print(f"Updates file not found: {self.updates_file_path}. Will be created.")
             self.last_read_pos = 0


    def check_for_new_updates(self):
        if not os.path.exists(self.updates_file_path): return
        try:
            # Check modification time first to avoid reading if unchanged
            current_mod_time = os.path.getmtime(self.updates_file_path)
            # Need to store last mod time to compare... for simplicity, just read new bytes
            # self.last_mod_time = getattr(self, 'last_mod_time', 0)
            # if current_mod_time <= self.last_mod_time: return
            # self.last_mod_time = current_mod_time

            with open(self.updates_file_path, 'r', encoding='utf-8') as f:
                # Check size, seek only if size > last known position
                current_size = f.seek(0, os.SEEK_END)
                if current_size > self.last_read_pos:
                    f.seek(self.last_read_pos)
                    new_lines = f.readlines()
                    self.last_read_pos = f.tell()
                    for line in new_lines:
                        line = line.strip()
                        if line: self.process_update_line(line)
                else:
                    # Reset position if file shrank (e.g., cleared manually)
                    self.last_read_pos = current_size

        except Exception as e:
            print(f"Error checking for updates file {self.updates_file_path}: {e}")

    def process_update_line(self, line):
        timestamp_str = "??:??:??"
        message_text = line
        match = re.match(r"\[(.*?)\]\s*(.*)", line)
        if match:
            timestamp_str = match.group(1).split()[-1]
            message_text = match.group(2)

        category = 'INFO'
        if any(keyword in message_text.lower() for keyword in CRITICAL_MESSAGE_KEYWORDS):
             category = 'CRITICAL'
        elif "bolo" in message_text.lower(): category = 'BOLO'
        elif "traffic" in message_text.lower() or "road closure" in message_text.lower(): category = 'TRAFFIC'

        self.add_message_to_display(message_text, category, timestamp_str)


    def add_message_to_display(self, message_text, category, timestamp):
        if not message_text: return
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
        elif category == 'INFO': prefix = PREFIX_INFO + " "
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
        else: inline_style = f'style="color: {COLOR_TEXT_PRIMARY};"'
        html_message = (f'<p style="margin-bottom: {UPDATE_SPACING_PX}px; margin-top: 0px; padding: 0px;">'
                        f'<span style="color: {timestamp_color}; font-size: {FONT_SIZE_TIMESTAMP}pt;">[{timestamp}]</span><br>'
                        f'<span class="{span_class}" {inline_style}>{icon}{message_text}</span>'
                        f'</p>')
        self.append(html_message)
        if pulse_color and pulse_count > 0: self.start_flash(pulse_color, pulse_count)

    def start_flash(self, color, pulse_on_count):
        if self.is_flashing: return
        self.flash_color = color
        self.pulse_max_on_count = pulse_on_count
        self.pulse_count = 0
        self.is_flashing = True
        self.flash_timer.start(self.pulse_interval)
        self._do_flash_pulse()

    def _do_flash_pulse(self):
        if not self.is_flashing: self.flash_timer.stop(); return
        self.pulse_count += 1
        total_ticks = self.pulse_max_on_count * 2
        if self.pulse_count > total_ticks:
            self.flash_timer.stop()
            self.setStyleSheet(self._build_style_sheet(self.default_border_color))
            self.is_flashing = False
        elif self.pulse_count % 2 == 1: self.setStyleSheet(self._build_style_sheet(self.flash_color))
        else: self.setStyleSheet(self._build_style_sheet(self.default_border_color))


class ImageDisplayWidget(QWidget):
    """ Widget for displaying image, description, overlay. Reads from folder. """
    def __init__(self, image_folder_path, parent=None):
        super().__init__(parent)
        self.image_folder_path = image_folder_path
        self.image_files = []
        self.current_image_index = -1
        self.last_folder_check_time = 0
        self.current_pixmap = None
        self.image_label = None
        self.image_description_label = None
        self.image_border_overlay_label = None
        self.initUI()
        self.check_for_new_images(initial_load=True)

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
        self.image_description_label = create_label("No Image", FONT_SIZE_IMAGE_DESC, color=COLOR_TEXT_PRIMARY, alignment=Qt.AlignCenter | Qt.AlignTop, parent=self)
        self.image_description_label.setWordWrap(True)
        layout.addWidget(self.image_description_label, 0)
        self.image_border_overlay_label = QLabel(self)
        self.image_border_overlay_label.setObjectName("imageBorderOverlay")
        self.image_border_overlay_label.setStyleSheet(f"""QLabel#imageBorderOverlay {{ border: {ACTUAL_IMAGE_BORDER_WIDTH}px solid {COLOR_ACTUAL_IMAGE_BORDER}; background: transparent; }}""")
        self.image_border_overlay_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.image_border_overlay_label.hide()

    def check_for_new_images(self, initial_load=False):
        if not os.path.isdir(self.image_folder_path):
             if initial_load: print(f"Image directory not found: {self.image_folder_path}")
             if self.image_files: self.image_files = []; self.current_image_index = -1; self.update_display(None, "Image directory missing", True)
             return False
        try:
            current_files = sorted(glob(os.path.join(self.image_folder_path, '*.[jp][pn]g')) + glob(os.path.join(self.image_folder_path, '*.gif')))
            if current_files != self.image_files:
                print(f"Detected change in image folder: {self.image_folder_path}")
                self.image_files = current_files
                self.current_image_index = -1 if not self.image_files else 0
                return True
            return False
        except Exception as e: print(f"Error checking image directory {self.image_folder_path}: {e}"); return False

    def display_next_image(self):
        if not self.image_files: self.update_display(None, "No Images Available", True); return
        self.current_image_index = (self.current_image_index + 1) % len(self.image_files)
        image_path = self.image_files[self.current_image_index]
        base_name = os.path.basename(image_path)
        desc = base_name
        match = re.match(r"(\d{8}_\d{6}_\d{6})_(.*)", base_name)
        if match:
            try: ts = datetime.strptime(match.group(1), "%Y%m%d_%H%M%S_%f"); desc = f"{match.group(2)} ({ts.strftime('%H:%M:%S')})"
            except ValueError: desc = base_name
        pixmap = QPixmap(image_path)
        is_error = pixmap.isNull()
        display_desc = desc if not is_error else f"Error loading: {base_name}"
        self.update_display(pixmap if not is_error else None, display_desc, is_error)

    def update_display(self, pixmap, description, is_error):
        self.current_pixmap = pixmap
        self.image_description_label.setText(description if description else "No Description")
        error_style = f"""QLabel#imageLabel {{ color: {COLOR_TEXT_SECONDARY}; font-size: {FONT_SIZE_IMAGE_PLACEHOLDER}pt; background-color: {COLOR_BACKGROUND}; border: 1px solid {COLOR_BOX_BORDER}; border-radius: {BOX_BORDER_RADIUS}px; qproperty-alignment: 'AlignCenter'; }}"""
        loaded_style = f"""QLabel#imageLabel {{ color: transparent; background-color: {COLOR_BACKGROUND}; border: 1px solid {COLOR_BOX_BORDER}; border-radius: {BOX_BORDER_RADIUS}px; }}"""
        if is_error:
            self.image_label.setPixmap(QPixmap()); self.image_label.setText(ICON_IMAGE_ERROR)
            self.image_label.setStyleSheet(error_style)
            if self.image_border_overlay_label: self.image_border_overlay_label.hide()
            self.image_label.update()
        else:
            if pixmap and not pixmap.isNull():
                self.image_label.setText(""); self.image_label.setStyleSheet(loaded_style)
                self.scale_and_position_overlay()
            else:
                self.image_label.setPixmap(QPixmap()); self.image_label.setText(ICON_IMAGE_ERROR)
                self.image_label.setStyleSheet(error_style)
                if self.image_border_overlay_label: self.image_border_overlay_label.hide()
                self.image_label.update()

    def scale_and_position_overlay(self):
        if not self.current_pixmap or self.current_pixmap.isNull() or not self.image_border_overlay_label:
            if self.image_border_overlay_label: self.image_border_overlay_label.hide()
            if self.image_label and not self.image_label.text(): self.image_label.setPixmap(QPixmap())
            return
        label_size = self.image_label.size()
        if label_size.width() <= 0 or label_size.height() <= 0:
            if self.image_border_overlay_label: self.image_border_overlay_label.hide(); return
        scaled_pixmap = self.current_pixmap.scaled(label_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        scaled_size = scaled_pixmap.size()
        x_offset = (label_size.width() - scaled_size.width()) // 2; y_offset = (label_size.height() - scaled_size.height()) // 2
        overlay_x = x_offset; overlay_y = y_offset; overlay_width = scaled_size.width(); overlay_height = scaled_size.height()
        self.image_border_overlay_label.setGeometry(overlay_x, overlay_y, overlay_width, overlay_height)
        self.image_border_overlay_label.show(); self.image_border_overlay_label.raise_()
        self.image_label.setPixmap(scaled_pixmap)

# =============================================================================
# Main Application Window
# =============================================================================

class PoliceDashboard(QWidget):
    """ Main application window managing component widgets and data polling. """
    def __init__(self, officer_id):
        super().__init__()
        self.officer_id = officer_id
        self.officer_data_dir = os.path.join(DATA_DIR, self.officer_id)
        self.updates_file = os.path.join(self.officer_data_dir, 'updates.txt')
        self.image_folder = os.path.join(self.officer_data_dir, 'images')
        os.makedirs(self.image_folder, exist_ok=True)
        # --- Initialize mock status attributes --- (Fix v26)
        self.mock_gps_locked = True
        self.mock_connection_ok = True
        # --- End Fix ---
        self.statusBar = None; self.intersectionInfo = None; self.updatesLog = None; self.imageDisplay = None
        self.clock_timer = None; self.polling_timer = None
        self.initUI()
        self.setStyleSheet(self.generate_stylesheet())
        self.setup_timers()
        self.poll_for_updates() # Initial poll
        self.update_clock()
        self.move_to_secondary_display()

    def initUI(self):
        self.setWindowTitle(f"Police Dashboard - {self.officer_id}")
        self.setMinimumSize(800, 480); self.resize(800, 480)
        overall_layout = QVBoxLayout(self); overall_layout.setContentsMargins(0, 0, 0, 0); overall_layout.setSpacing(0)
        self.statusBar = StatusBarWidget(self); overall_layout.addWidget(self.statusBar)
        separator = QFrame(self); separator.setFrameShape(QFrame.HLine); separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet(f"border: {SEPARATOR_HEIGHT}px solid {COLOR_SEPARATOR}; margin-left: {MAIN_MARGINS}px; margin-right: {MAIN_MARGINS}px;")
        overall_layout.addWidget(separator)
        main_content_widget = QWidget(self); main_content_widget.setStyleSheet("background-color: transparent;")
        self.main_layout = QHBoxLayout(main_content_widget); self.main_layout.setContentsMargins(MAIN_MARGINS, MAIN_MARGINS, MAIN_MARGINS, MAIN_MARGINS); self.main_layout.setSpacing(MAIN_SPACING)
        self.left_column_layout = QVBoxLayout(); self.left_column_layout.setSpacing(LEFT_COLUMN_SPACING)
        intersection_title = create_label("Intersection Data", FONT_SIZE_TITLE, bold=True, color=COLOR_ACCENT, parent=main_content_widget)
        self.intersectionInfo = IntersectionInfoWidget(main_content_widget); self.intersectionInfo.setObjectName("intersectionContainer")
        updates_title = create_label("Important Updates", FONT_SIZE_TITLE, bold=True, color=COLOR_ACCENT, parent=main_content_widget)
        self.updatesLog = UpdatesLogWidget(self.updates_file, main_content_widget)
        self.left_column_layout.addWidget(intersection_title); self.left_column_layout.addWidget(self.intersectionInfo)
        self.left_column_layout.addSpacing(MAIN_SPACING); self.left_column_layout.addWidget(updates_title); self.left_column_layout.addWidget(self.updatesLog, 1)
        self.imageDisplay = ImageDisplayWidget(self.image_folder, main_content_widget)
        self.main_layout.addLayout(self.left_column_layout, 1); self.main_layout.addWidget(self.imageDisplay, 1)
        overall_layout.addWidget(main_content_widget, 1)

    def generate_stylesheet(self):
        return f""" QWidget {{ color: {COLOR_TEXT_PRIMARY}; background-color: {COLOR_BACKGROUND}; font-family: "{FONT_FAMILY}"; }} QFrame#intersectionContainer {{ background-color: {COLOR_BACKGROUND}; border: 1px solid {COLOR_BOX_BORDER}; border-radius: {BOX_BORDER_RADIUS}px; }} .message {{ }} .critical_message {{ font-weight: bold; }} """

    def setup_timers(self):
        self.clock_timer = QTimer(self); self.clock_timer.timeout.connect(self.update_clock); self.clock_timer.start(CLOCK_INTERVAL_MS)
        self.polling_timer = QTimer(self); self.polling_timer.timeout.connect(self.poll_for_updates); self.polling_timer.start(POLLING_INTERVAL_MS)

    def update_clock(self):
        if self.statusBar: current_time = QTime.currentTime(); time_text = current_time.toString("HH:mm:ss"); self.statusBar.update_time(time_text)

    def poll_for_updates(self):
        if self.updatesLog: self.updatesLog.check_for_new_updates()
        if self.imageDisplay:
            image_folder_updated = self.imageDisplay.check_for_new_images()
            self.imageDisplay.display_next_image()
            if not self.imageDisplay.image_files: self.imageDisplay.hide()
            else: self.imageDisplay.show()
        if random.random() < 0.1: self.mock_gps_locked = not self.mock_gps_locked
        if random.random() < 0.05: self.mock_connection_ok = not self.mock_connection_ok
        if self.statusBar: self.statusBar.update_status(self.mock_gps_locked, self.mock_connection_ok)

    def move_to_secondary_display(self):
        screens = QApplication.screens(); print(f"Detected {len(screens)} screen(s).")
        if len(screens) > 1:
            secondary_screen = screens[1]; screen_geometry = secondary_screen.geometry()
            print(f"Attempting to move to secondary screen (index 1) at {screen_geometry.topLeft()}.")
            self.move(screen_geometry.topLeft()); self.showFullScreen()
        else: print("Only one screen detected. Showing fullscreen on primary screen."); self.showFullScreen()

    def resizeEvent(self, event):
        super().resizeEvent(event);
        if self.imageDisplay: QTimer.singleShot(50, self.imageDisplay.scale_and_position_overlay)

    def showEvent(self, event):
        super().showEvent(event) # Call parent showEvent first
        if self.imageDisplay: QTimer.singleShot(100, self.imageDisplay.scale_and_position_overlay)

# =============================================================================
# Main Execution Block
# =============================================================================

if __name__ == '__main__':
    officer_id_to_run = OFFICER_ID
    if len(sys.argv) > 1: officer_id_to_run = sys.argv[1]; print(f"Running dashboard for Officer ID: {officer_id_to_run}")
    app = QApplication(sys.argv)
    main_window = PoliceDashboard(officer_id=officer_id_to_run)
    sys.exit(app.exec_())


