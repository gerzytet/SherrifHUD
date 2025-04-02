# -*- coding: utf-8 -*-
"""
Police Dashboard UI Application using PyQt5.

Displays mock intersection data, important updates, and cycling images.
Optimized for an 800x480 reflected display (e.g., HUD on glass/acrylic)
with high contrast and clear visuals. Forced Fullscreen on Secondary Display (if available).

Improvements Implemented (v24):
- Fixed auto-move to secondary display logic. (Multi-screen Fix v2)
- Changed box/separator borders to accent color (blue).
- Implemented border flash on UpdatesLogWidget for new critical messages.
- Fixed missing border on Intersection Info box using QFrame base class + global style.
- Fixed image error display bug.
- Changed timestamp color for critical messages to red.
- Componentized UI into separate QWidget classes.
- Enhanced status indicators with background colors.
- Added update message categorization (visual prefixes).
- Changed font to "Roboto Condensed".
- Made status bar separator more distinct.
- Improved image description contrast.
- Restored border on main image container (now has two borders: container + overlay).
- Added image description label below the image.
- Added mock descriptions.
- Adjusted update log spacing using <p> tags and CSS margin.
- Fixed timestamp color/size styling in updates log via inline HTML styles.
- Explicitly disabled scrollbar on updates box.
- Reverted intersection data to single-line format ("Dist Dir of Location").
- Replaced status bar icons with text indicators for compatibility.
- Positioned update timestamps above message text.
- Optimized font sizes for 800x480.
- Adjusted spacing/padding for density.
- Removed glow effects for clarity on reflection.
- Enhanced update log (critical icon, background highlight).
- Added a minimal status bar (Time, GPS, Connection).
- Refactored data update logic.
"""

# --- Standard Library Imports ---
import sys
import random
import re
from datetime import datetime

# --- PyQt5 Imports ---
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QTextEdit, QSizePolicy, QFrame # Ensure QFrame is imported
)
from PyQt5.QtGui import QFont, QPixmap, QColor, QScreen, QTextOption
from PyQt5.QtCore import Qt, QTimer, QSize, QTime, QPoint

# =============================================================================
# Configuration Constants
# =============================================================================

# --- Update Settings ---
UPDATE_INTERVAL_MS = 3500
CLOCK_INTERVAL_MS = 1000
PULSE_INTERVAL_MS = 200
PULSE_COUNT_CRITICAL = 4
PULSE_COUNT_BOLO = 3
PULSE_COUNT_TRAFFIC = 2

# --- Color Palette (High Contrast Black Background) ---
COLOR_BACKGROUND = "#000000"
COLOR_TEXT_PRIMARY = "#E0E0E0"
COLOR_TEXT_SECONDARY = "#A0A0A0"
COLOR_ACCENT = "#00BFFF" # Blue Accent
COLOR_SEPARATOR = COLOR_ACCENT
COLOR_BOX_BORDER = COLOR_ACCENT # Default border color
COLOR_ACTUAL_IMAGE_BORDER = "#FFFFFF"
COLOR_UPDATE_TIMESTAMP = "#00FFFF" # Cyan (Default/Info)
COLOR_TIMESTAMP_TRAFFIC = "#FFFF00" # Yellow for Traffic / Traffic Pulse
COLOR_TIMESTAMP_BOLO = "#FFA500"   # Orange for BOLO / BOLO Pulse
COLOR_CRITICAL_UPDATE = "#FF0000" # Bright Red (Used for text, background, timestamp, pulse)
COLOR_CRITICAL_BG = "#400000"
COLOR_GPS_LOCKED = "#00FF00" # Bright Green
COLOR_GPS_NO_LOCK = COLOR_TEXT_SECONDARY
COLOR_CONN_OK = "#00FF00" # Bright Green
COLOR_CONN_BAD = COLOR_TEXT_SECONDARY
COLOR_STATUS_OK_BG = "#003000" # Dark Green background for OK status
COLOR_STATUS_BAD_BG = "#303030" # Dark Gray background for BAD status

# --- Font Settings ---
FONT_FAMILY = "Roboto Condensed"
FONT_SIZE_STATUS_BAR = 11
FONT_SIZE_TITLE = 18
FONT_SIZE_INTERSECTION_DATA = 13
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
PREFIX_INFO = "[I]"
PREFIX_TRAFFIC = "[T]"
PREFIX_BOLO = "[B]"

# --- Mock Data ---
MOCK_INTERSECTION_DATA = [
    "300ft, NE, Elm St & Maple Ave (4-way)", "0.5mi, S, Highway 2 & Exit 15 (Turn)",
    "150m, W, Park Dr & Lake Rd (3-way)", "20ft, N, Cul-de-sac Ct (Dead End)",
    "1.2mi, E, Main St & Central Plaza (Roundabout)", "500m, SW, Industrial Pkwy & Rail Rd (Crossing)",
]
MOCK_IMAGE_PATHS = [
    "/Images/cat.jpg",
    "/Images/hacker.jpg",
    None, # Simulate no image available
    "/Images/dog.jpg",
    "/Images/poly.jpg",
    "/invalid/path/should_fail.jpg", # Simulate load error
    "/Images/redbackground.jpg",
    None, # Simulate no image available again
    "/Images/tall.jpg",
]
MOCK_IMAGE_DESCRIPTIONS = [
    "Subject: Domestic Feline",
    "POI: Unknown Hacker Signature",
    None, # No description when no image
    "Asset: K9 Unit 'Rex'",
    "Location: Florida Polytechnic University",
    "Error: Image Not Found", # Description for invalid path
    "Background: Abstract Red",
    None, # No description when no image
    "Building: Tall Skyscraper",
]
MOCK_UPDATE_MESSAGES = [
    ('INFO', "Unit 12 reporting clear."), ('TRAFFIC', "Traffic stop initiated on Green St."),
    ('INFO', "Possible suspect match identified."), ('BOLO', "BOLO issued for blue sedan."),
    ('CRITICAL', "Requesting backup at 1st & Main."), ('INFO', "Perimeter established."),
    ('INFO', "Air support en route."), ('CRITICAL', "Suspicious activity reported near warehouse."),
    ('TRAFFIC', "Road closure active on Bridge Rd."), ('INFO', "All units hold position."),
    ('CRITICAL', "Emergency: Vehicle pursuit in progress."),
]
CRITICAL_MESSAGE_KEYWORDS = ["backup", "suspicious", "alert", "emergency", "pursuit"]

# Ensure descriptions match paths
if len(MOCK_IMAGE_DESCRIPTIONS) != len(MOCK_IMAGE_PATHS):
    print("Warning: Mismatch between image paths and descriptions!")
    new_descs = []
    for i in range(len(MOCK_IMAGE_PATHS)):
        if i < len(MOCK_IMAGE_DESCRIPTIONS):
            new_descs.append(MOCK_IMAGE_DESCRIPTIONS[i])
        else:
            new_descs.append("No Description" if MOCK_IMAGE_PATHS[i] else None)
    MOCK_IMAGE_DESCRIPTIONS = new_descs

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

    def initUI(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(MAIN_MARGINS, 2, MAIN_MARGINS, 2)
        layout.setSpacing(MAIN_SPACING)
        self.gps_text_label = create_label("GPS: No Lock", FONT_SIZE_STATUS_BAR, color=COLOR_GPS_NO_LOCK, parent=self)
        self.conn_text_label = create_label("NET: Offline", FONT_SIZE_STATUS_BAR, color=COLOR_CONN_BAD, parent=self)
        self.time_label = create_label("00:00:00", FONT_SIZE_STATUS_BAR, color=COLOR_TEXT_PRIMARY, alignment=Qt.AlignRight | Qt.AlignVCenter, parent=self)
        self.gps_text_label.setStyleSheet(f"color: {COLOR_GPS_NO_LOCK}; background-color: {COLOR_STATUS_BAD_BG}; padding: 1px 3px; border-radius: 3px;")
        self.conn_text_label.setStyleSheet(f"color: {COLOR_CONN_BAD}; background-color: {COLOR_STATUS_BAD_BG}; padding: 1px 3px; border-radius: 3px;")
        layout.addWidget(self.gps_text_label)
        layout.addSpacing(MAIN_SPACING)
        layout.addWidget(self.conn_text_label)
        layout.addStretch(1)
        layout.addWidget(self.time_label)

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


class IntersectionInfoWidget(QFrame): # Inherit from QFrame
    """ Widget for displaying intersection information. Styled by main stylesheet. """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()

    def initUI(self):
        self.setObjectName("intersectionContainer")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(BOX_PADDING, BOX_PADDING, BOX_PADDING, BOX_PADDING)
        layout.setSpacing(INTERSECTION_SPACING)
        self.timestamp_label = create_label("Updated: --:--:--", FONT_SIZE_TIMESTAMP, color=COLOR_UPDATE_TIMESTAMP, parent=self)
        self.data_label = create_label("Loading...", FONT_SIZE_INTERSECTION_DATA, color=COLOR_TEXT_PRIMARY, parent=self)
        self.data_label.setWordWrap(True)
        self.data_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.data_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.MinimumExpanding)
        layout.addWidget(self.timestamp_label)
        layout.addWidget(self.data_label)

    def update_data(self, data_string, timestamp):
        self.timestamp_label.setText(f"Updated: {timestamp}")
        formatted_string = "No intersection data available."
        if data_string:
            try:
                parts = [p.strip() for p in data_string.split(',', 2)]
                if len(parts) == 3:
                    distance, direction, location_full = parts
                    location = re.sub(r'\s*\(.*\)\s*$', '', location_full).strip()
                    formatted_string = f"{distance} {direction} of {location}"
                else: formatted_string = data_string
            except Exception as e:
                print(f"Error parsing intersection data '{data_string}': {e}")
                formatted_string = data_string
        self.data_label.setText(formatted_string)


class UpdatesLogWidget(QTextEdit):
    """ Widget for displaying the scrolling updates log with border pulse. """
    def __init__(self, parent=None):
        super().__init__(parent)
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
        """ Helper to build the full stylesheet string with a dynamic border color. """
        return f"""
            QTextEdit#updatesTextEdit {{
                background-color: {COLOR_BACKGROUND}; color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {border_color}; /* Dynamic border color */
                border-radius: {BOX_BORDER_RADIUS}px;
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

    def add_message(self, message_text, category, timestamp):
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

        if pulse_color and pulse_count > 0:
            self.start_flash(pulse_color, pulse_count)

    def start_flash(self, color, pulse_on_count):
        if self.is_flashing: return
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
        elif self.pulse_count % 2 == 1: # Odd count: Turn ON
            self.setStyleSheet(self._build_style_sheet(self.flash_color))
        else: # Even count: Turn OFF
            self.setStyleSheet(self._build_style_sheet(self.default_border_color))


class ImageDisplayWidget(QWidget):
    """ Widget for displaying the image, description, and overlay border. """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_pixmap = None
        self.image_label = None
        self.image_description_label = None
        self.image_border_overlay_label = None
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(RIGHT_COLUMN_SPACING)

        self.image_label = QLabel(ICON_IMAGE_LOADING, self)
        self.image_label.setObjectName("imageLabel")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.image_label.setStyleSheet(f"""
            QLabel#imageLabel {{
                color: {COLOR_TEXT_SECONDARY}; font-size: {FONT_SIZE_IMAGE_PLACEHOLDER}pt;
                background-color: {COLOR_BACKGROUND}; border: 1px solid {COLOR_BOX_BORDER};
                border-radius: {BOX_BORDER_RADIUS}px;
            }}""")
        layout.addWidget(self.image_label, 1)

        self.image_description_label = create_label("Loading description...", FONT_SIZE_IMAGE_DESC, color=COLOR_TEXT_PRIMARY, alignment=Qt.AlignCenter | Qt.AlignTop, parent=self)
        self.image_description_label.setWordWrap(True)
        layout.addWidget(self.image_description_label, 0)

        self.image_border_overlay_label = QLabel(self)
        self.image_border_overlay_label.setObjectName("imageBorderOverlay")
        self.image_border_overlay_label.setStyleSheet(f"""
            QLabel#imageBorderOverlay {{
                border: {ACTUAL_IMAGE_BORDER_WIDTH}px solid {COLOR_ACTUAL_IMAGE_BORDER};
                background: transparent;
            }}""")
        self.image_border_overlay_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.image_border_overlay_label.hide()

    def update_display(self, pixmap, description, is_error):
        self.current_pixmap = pixmap
        self.image_description_label.setText(description if description else "No Description")

        error_style = f"""
            QLabel#imageLabel {{
                color: {COLOR_TEXT_SECONDARY}; font-size: {FONT_SIZE_IMAGE_PLACEHOLDER}pt;
                background-color: {COLOR_BACKGROUND}; border: 1px solid {COLOR_BOX_BORDER};
                border-radius: {BOX_BORDER_RADIUS}px; qproperty-alignment: 'AlignCenter';
            }}"""
        loaded_style = f"""
            QLabel#imageLabel {{
                color: transparent; background-color: {COLOR_BACKGROUND};
                border: 1px solid {COLOR_BOX_BORDER}; border-radius: {BOX_BORDER_RADIUS}px;
            }}"""

        if is_error:
            self.image_label.setPixmap(QPixmap())
            self.image_label.setText(ICON_IMAGE_ERROR)
            self.image_label.setStyleSheet(error_style)
            self.image_border_overlay_label.hide()
            self.image_label.update()
        else:
            if pixmap and not pixmap.isNull():
                self.image_label.setText("")
                self.image_label.setStyleSheet(loaded_style)
                self.scale_and_position_overlay()
            else: # Treat invalid pixmap as error case
                self.image_label.setPixmap(QPixmap())
                self.image_label.setText(ICON_IMAGE_ERROR)
                self.image_label.setStyleSheet(error_style)
                self.image_border_overlay_label.hide()
                self.image_label.update()


    def scale_and_position_overlay(self):
        if not self.current_pixmap or self.current_pixmap.isNull() or not self.image_border_overlay_label:
            if self.image_border_overlay_label: self.image_border_overlay_label.hide()
            if self.image_label and not self.image_label.text():
                 self.image_label.setPixmap(QPixmap())
            return

        label_size = self.image_label.size()
        if label_size.width() <= 0 or label_size.height() <= 0:
            if self.image_border_overlay_label: self.image_border_overlay_label.hide()
            return

        scaled_pixmap = self.current_pixmap.scaled(label_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        scaled_size = scaled_pixmap.size()
        x_offset = (label_size.width() - scaled_size.width()) // 2
        y_offset = (label_size.height() - scaled_size.height()) // 2
        overlay_x = x_offset
        overlay_y = y_offset
        overlay_width = scaled_size.width()
        overlay_height = scaled_size.height()

        self.image_border_overlay_label.setGeometry(overlay_x, overlay_y, overlay_width, overlay_height)
        self.image_border_overlay_label.show()
        self.image_border_overlay_label.raise_()
        self.image_label.setPixmap(scaled_pixmap)


# =============================================================================
# Main Application Window
# =============================================================================

class PoliceDashboard(QWidget):
    """ Main application window managing component widgets. """
    def __init__(self):
        super().__init__()
        self.current_image_index = -1
        self.current_intersection_index = -1
        self.mock_gps_locked = True
        self.mock_connection_ok = True
        self.statusBar = None
        self.intersectionInfo = None
        self.updatesLog = None
        self.imageDisplay = None
        self.initUI()
        self.setStyleSheet(self.generate_stylesheet()) # Apply base styles
        self.setup_timers()
        self.update_content()
        self.update_clock()
        # Call move/show logic at the end of init (Fix for multi-screen)
        self.move_to_secondary_display()

    def initUI(self):
        self.setWindowTitle("Police Dashboard")
        self.setMinimumSize(800, 480)
        self.resize(800, 480)
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
        main_layout = QHBoxLayout(main_content_widget)
        main_layout.setContentsMargins(MAIN_MARGINS, MAIN_MARGINS, MAIN_MARGINS, MAIN_MARGINS)
        main_layout.setSpacing(MAIN_SPACING)

        # --- Left Column ---
        left_column_layout = QVBoxLayout()
        left_column_layout.setSpacing(LEFT_COLUMN_SPACING)
        intersection_title = create_label("Intersection Data", FONT_SIZE_TITLE, bold=True, color=COLOR_ACCENT, parent=main_content_widget)
        self.intersectionInfo = IntersectionInfoWidget(main_content_widget)
        self.intersectionInfo.setObjectName("intersectionContainer") # Set object name for main stylesheet
        updates_title = create_label("Important Updates", FONT_SIZE_TITLE, bold=True, color=COLOR_ACCENT, parent=main_content_widget)
        self.updatesLog = UpdatesLogWidget(main_content_widget) # Uses direct styling internally
        left_column_layout.addWidget(intersection_title)
        left_column_layout.addWidget(self.intersectionInfo)
        left_column_layout.addSpacing(MAIN_SPACING)
        left_column_layout.addWidget(updates_title)
        left_column_layout.addWidget(self.updatesLog, 1)

        # --- Right Column ---
        self.imageDisplay = ImageDisplayWidget(main_content_widget)
        main_layout.addLayout(left_column_layout, 1)
        main_layout.addWidget(self.imageDisplay, 1)

        overall_layout.addWidget(main_content_widget, 1)

    def generate_stylesheet(self):
        # Define styles globally using object names where needed
        return f"""
            QWidget {{
                color: {COLOR_TEXT_PRIMARY};
                background-color: {COLOR_BACKGROUND};
                font-family: "{FONT_FAMILY}";
            }}
            QFrame#intersectionContainer {{ /* Style rule for IntersectionInfoWidget */
                background-color: {COLOR_BACKGROUND};
                border: 1px solid {COLOR_BOX_BORDER};
                border-radius: {BOX_BORDER_RADIUS}px;
                /* Padding handled by the layout margins inside the widget */
            }}
            /* Styles for HTML spans used in updates log */
            .message {{ }}
            .critical_message {{ font-weight: bold; }}
        """

    def setup_timers(self):
        self.content_timer = QTimer(self)
        self.content_timer.timeout.connect(self.update_content)
        self.content_timer.start(UPDATE_INTERVAL_MS)
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self.update_clock)
        self.clock_timer.start(CLOCK_INTERVAL_MS)

    def update_clock(self):
        if self.statusBar:
            current_time = QTime.currentTime()
            time_text = current_time.toString("HH:mm:ss")
            self.statusBar.update_time(time_text)

    def update_content(self):
        """ Fetches data and updates component widgets. """
        intersection_data_str = self._get_next_intersection_data()
        image_path, image_desc = self._get_next_image_info()
        update_info = self._get_next_update_message()
        timestamp_str = datetime.now().strftime('%H:%M:%S')

        if random.random() < 0.1: self.mock_gps_locked = not self.mock_gps_locked
        if random.random() < 0.05: self.mock_connection_ok = not self.mock_connection_ok
        if self.statusBar:
            self.statusBar.update_status(self.mock_gps_locked, self.mock_connection_ok)
        if self.intersectionInfo:
            self.intersectionInfo.update_data(intersection_data_str, timestamp_str)

        # Update Image Display or Hide it
        if image_path is None:
            if self.imageDisplay: self.imageDisplay.hide()
        else:
            if self.imageDisplay:
                self.imageDisplay.show()
                pixmap = QPixmap(image_path)
                is_error = pixmap.isNull()
                display_desc = image_desc if not is_error else "Error loading image"
                self.imageDisplay.update_display(pixmap if not is_error else None, display_desc, is_error)

        # Add Update Message (triggers internal flash if needed)
        if self.updatesLog and update_info:
            category, message_text = update_info
            self.updatesLog.add_message(message_text, category, timestamp_str)


    # --- Data Fetching Methods ---
    def _get_next_intersection_data(self):
        if not MOCK_INTERSECTION_DATA: return None
        self.current_intersection_index = (self.current_intersection_index + 1) % len(MOCK_INTERSECTION_DATA)
        return MOCK_INTERSECTION_DATA[self.current_intersection_index]

    def _get_next_image_info(self):
        if not MOCK_IMAGE_PATHS: return None, None
        self.current_image_index = (self.current_image_index + 1) % len(MOCK_IMAGE_PATHS)
        path = MOCK_IMAGE_PATHS[self.current_image_index]
        desc = None
        if path is not None:
            desc = MOCK_IMAGE_DESCRIPTIONS[self.current_image_index] if self.current_image_index < len(MOCK_IMAGE_DESCRIPTIONS) else "No Description"
        return path, desc

    def _get_next_update_message(self):
        if not MOCK_UPDATE_MESSAGES: return None
        return random.choice(MOCK_UPDATE_MESSAGES)

    # --- Screen Handling ---
    def move_to_secondary_display(self):
        """ Attempts to move the window to the secondary display and show fullscreen. """
        screens = QApplication.screens()
        print(f"Detected {len(screens)} screen(s).") # Debug output
        if len(screens) > 1:
            secondary_screen = screens[1] # Index 1 is typically secondary
            screen_geometry = secondary_screen.geometry()
            print(f"Attempting to move to secondary screen (index 1) at {screen_geometry.topLeft()}.")
            self.move(screen_geometry.topLeft())
            self.showFullScreen() # Show fullscreen on the target screen
        else:
            print("Only one screen detected. Showing fullscreen on primary screen.")
            self.showFullScreen() # Show fullscreen on the primary screen

    # --- Event Handlers ---
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.imageDisplay:
             QTimer.singleShot(50, self.imageDisplay.scale_and_position_overlay)

    def showEvent(self, event):
        """ Called when the widget is shown. """
        # Movement logic moved to __init__ calling move_to_secondary_display
        super().showEvent(event) # Call parent showEvent
        if self.imageDisplay: # Trigger initial scaling after showing
            QTimer.singleShot(100, self.imageDisplay.scale_and_position_overlay)

# =============================================================================
# Main Execution Block
# =============================================================================

if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_window = PoliceDashboard()
    # Window is shown via move_to_secondary_display called in main_window's __init__
    sys.exit(app.exec_())

