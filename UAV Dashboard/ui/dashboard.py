import sys
import os
import cv2
import time
import numpy as np
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QMenuBar, QMenu, QAction, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QPixmap, QImage, QFont
from camera.camera_view import CameraView
from ping3 import ping  
from fpdf import FPDF
from PIL import Image

class DroneDashboard(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

        self.photos = []  # To store paths of captured photos
        self.videos = []  # To store paths of recorded videos

        self.camera = CameraView()
        self.camera.frame_updated.connect(self.update_camera_view)
        self.camera.objects_detected.connect(self.update_live_reporting)

        self.camera_running = False
        self.is_recording = False

        # Ping-related attributes
        self.ping_ip = "192.168.4.1"  # ESP32-CAM IP address
        self.ping_timer = QTimer(self)
        self.ping_timer.timeout.connect(self.update_ping_status)
        self.ping_timer.start(1000)  # Ping every 1 second

        # Stream reconnection attributes
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 5  # Delay in seconds between reconnection attempts

        # Timer for live reporting updates
        self.report_timer = QTimer(self)
        self.report_timer.timeout.connect(self.update_live_reporting)  # No arguments passed here
        self.report_timer.start(5000)  # Update every 5 seconds

    def init_ui(self):
        # Window properties
        self.setWindowTitle("UAV Dashboard")
        self.setMinimumSize(1000, 800)

        # Main layout
        self.main_layout = QVBoxLayout(self)

        # Menu Bar
        self.menu_bar = QMenuBar(self)

        # Menu (File-like menu)
        menu_menu = QMenu("Menu", self)
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        menu_menu.addAction(exit_action)

        # Help Menu
        help_menu = QMenu("Help", self)
        about_action = QAction("About", self)
        examples_action = QAction("Examples", self)
        help_menu.addAction(about_action)
        help_menu.addAction(examples_action)

        # Add menus to the menu bar
        self.menu_bar.addMenu(menu_menu)
        self.menu_bar.addMenu(help_menu)
        self.main_layout.setMenuBar(self.menu_bar)

        # Connect actions
        about_action.triggered.connect(self.show_about)
        examples_action.triggered.connect(self.show_examples)

        # Top Button Layout
        top_layout = QHBoxLayout()
        self.camera_toggle_btn = QPushButton("Start Camera")
        self.camera_toggle_btn.clicked.connect(self.toggle_camera)

        self.take_photo_btn = QPushButton("Take Photo")
        self.take_photo_btn.clicked.connect(self.take_photo)

        self.record_btn = QPushButton("Record")
        self.record_btn.clicked.connect(self.toggle_recording)

        self.generate_report_btn = QPushButton("Generate Report")
        self.generate_report_btn.clicked.connect(self.generate_report)

        top_layout.addWidget(self.camera_toggle_btn)
        top_layout.addWidget(self.take_photo_btn)
        top_layout.addWidget(self.record_btn)
        top_layout.addWidget(self.generate_report_btn)

        self.main_layout.addLayout(top_layout)

        # Middle Layout
        middle_layout = QHBoxLayout()
        self.camera_view = QLabel("Camera View")
        self.camera_view.setStyleSheet("background-color: lightgray;")
        self.camera_view.setAlignment(Qt.AlignCenter)

        self.live_reporting = QTextEdit()
        self.live_reporting.setReadOnly(True)
        self.live_reporting.setStyleSheet("background-color: #f0f0f0; font-size: 12px;")
        self.live_reporting.setText("<span style='color: blue; text-align:center'>Live Reporting</span><br>")

        middle_layout.addWidget(self.camera_view, 3)
        middle_layout.addWidget(self.live_reporting, 1)
        self.main_layout.addLayout(middle_layout)

        # Alerts Layout
        alerts_layout = QVBoxLayout()
        self.object_count_label = QLabel("Objects detected: 0")
        self.fire_alert_label = QLabel("Fire detected: No")
        self.disaster_alert_label = QLabel("Other disasters: None")
        self.survivors_alert_label = QLabel("Survivors detected: 0")
        self.emergency_teams_alert_label = QLabel("Emergency teams: Not required")

        alerts_layout.addWidget(self.object_count_label)
        alerts_layout.addWidget(self.fire_alert_label)
        alerts_layout.addWidget(self.disaster_alert_label)
        alerts_layout.addWidget(self.survivors_alert_label)
        alerts_layout.addWidget(self.emergency_teams_alert_label)
        self.main_layout.addLayout(alerts_layout)

        # Ping Status Label
        self.ping_status_label = QLabel("Ping: N/A")
        self.ping_status_label.setStyleSheet("font-weight: bold;")
        self.main_layout.addWidget(self.ping_status_label)

        # Bottom Layout
        bottom_layout = QHBoxLayout()
        self.camera_status = QLabel("Camera Status: <span style='color: red;'>Offline</span>")
        bottom_layout.addWidget(self.camera_status)
        self.main_layout.addLayout(bottom_layout)


    def update_ping_status(self):
        """Ping the ESP32-CAM and update the ping status label."""
        try:
            latency = ping(self.ping_ip, timeout=1)  # Ping with a timeout of 1 second
            if latency is not None:
                latency_ms = int(latency * 1000)  # Convert to milliseconds
                self.ping_status_label.setText(f"Ping: {latency_ms} ms")
                if latency_ms > 100:  # High latency
                    self.ping_status_label.setStyleSheet("color: red; font-weight: bold;")
                else:  # Low latency
                    self.ping_status_label.setStyleSheet("color: green; font-weight: bold;")
            else:
                self.ping_status_label.setText("Ping: Timeout")
                self.ping_status_label.setStyleSheet("color: orange; font-weight: bold;")
        except Exception as e:
            self.ping_status_label.setText(f"Ping: Error ({str(e)})")
            self.ping_status_label.setStyleSheet("color: red; font-weight: bold;")

    def resizeEvent(self, event):
        self.camera_view.setFixedHeight(self.height() // 2)
        self.camera_view.setFixedWidth(int(self.width() * 0.7))
        self.live_reporting.setFixedWidth(int(self.width() * 0.3))
        super().resizeEvent(event)

    def toggle_camera(self):
        if self.camera_running:
            # Stop the camera
            self.camera.stop()
            self.live_reporting.append("<span style='color: red;'>Camera Stopped.</span>")
            self.camera_status.setText("Camera Status: <span style='color: red;'>Offline</span>")
            self.camera_toggle_btn.setText("Start Camera")

            # Stop the live reporting timer
            self.report_timer.stop()
        else:
            # Start the camera
            self.camera.start()
            self.live_reporting.append("<span style='color: green;'>Camera Started.</span>")
            self.camera_status.setText("Camera Status: <span style='color: green;'>Online</span>")
            self.camera_toggle_btn.setText("Stop Camera")

            # Start the live reporting timer
            self.report_timer.start(5000)  # Update every 5 seconds

        self.camera_running = not self.camera_running

    def update_camera_view(self, pixmap):
        """Update the camera view with the latest frame."""
        try:
            self.camera_view.setPixmap(pixmap.scaled(
                self.camera_view.width(),
                self.camera_view.height(),
                Qt.KeepAspectRatio
            ))
        except Exception as e:
            self.handle_stream_error(e)

    def handle_stream_error(self, error):
        """Handle stream errors and attempt to reconnect."""
        error_message = str(error)
        self.live_reporting.append(f"<span style='color: red;'>Stream Error: {error_message}</span>")

        if self.reconnect_attempts < self.max_reconnect_attempts:
            self.reconnect_attempts += 1
            self.live_reporting.append(f"<span style='color: orange;'>Reconnecting in {self.reconnect_delay} seconds (Attempt {self.reconnect_attempts}/{self.max_reconnect_attempts})...</span>")

            # Stop the camera and attempt to reconnect after a delay
            self.camera.stop()
            QTimer.singleShot(self.reconnect_delay * 1000, self.reconnect_camera)
        else:
            self.live_reporting.append("<span style='color: red;'>Max reconnection attempts reached. Please check the ESP32-CAM.</span>")
            self.camera_running = False
            self.camera_toggle_btn.setText("Start Camera")
            self.camera_status.setText("Camera Status: <span style='color: red;'>Offline</span>")

    def reconnect_camera(self):
        """Reconnect to the ESP32-CAM stream."""
        try:
            self.camera.start()
            self.live_reporting.append("<span style='color: green;'>Reconnection successful.</span>")
            self.camera_running = True
            self.camera_toggle_btn.setText("Stop Camera")
            self.camera_status.setText("Camera Status: <span style='color: green;'>Online</span>")
            self.reconnect_attempts = 0  # Reset reconnection attempts
        except Exception as e:
            self.handle_stream_error(e)

    def update_live_reporting(self, detected_objects=None):
        """Update the live reporting section with detected objects and counts."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.live_reporting.append(f"<br><span style='color: blue;'>Live Update at {timestamp}:</span>")

        # If no detected_objects are provided, initialize an empty dictionary
        if detected_objects is None:
            detected_objects = {}

        # Count total objects
        total_count = sum(detected_objects.values())

        # Check for fire and other disasters
        fire_detected = False
        fire_count = 0
        other_disasters = []
        survivors_count = 0

        # List to store detected objects and their counts
        detected_objects_list = []

        for obj_name, obj_count in detected_objects.items():
            # Add object name and count to the list
            detected_objects_list.append(f"{obj_name}: {obj_count}")

            # Check for specific objects
            if obj_name.lower() == 'fire':
                fire_detected = True
                fire_count += obj_count
            elif obj_name.lower() in ['smoke', 'flood', 'earthquake']:
                other_disasters.append(f"{obj_name} {obj_count}")
            elif obj_name.lower() == 'person':
                survivors_count += obj_count

        # Append total objects detected
        self.live_reporting.append(f"<b>Total Objects Detected:</b> {total_count}")

        # Append list of detected objects with their counts
        if detected_objects_list:
            self.live_reporting.append("<b>Detected Objects:</b>")
            for obj in detected_objects_list:
                self.live_reporting.append(f"- {obj}")
        else:
            self.live_reporting.append("<b>Detected Objects:</b> None")

        # Append fire detection status
        self.live_reporting.append(f"<b>Fire Detected:</b> {'Yes' if fire_detected else 'No'}")

        # Append other disasters
        disaster_text = ', '.join(other_disasters) if other_disasters else 'None'
        self.live_reporting.append(f"<b>Other Disasters:</b> {disaster_text}")

        # Append survivors detected
        self.live_reporting.append(f"<b>Survivors Detected:</b> {survivors_count}")

        # Update labels
        self.object_count_label.setText(f"Objects detected: {total_count}")
        self.fire_alert_label.setText(f"Fire detected: {'Yes' if fire_detected else 'No'}")
        self.disaster_alert_label.setText(f"Other disasters: {disaster_text}")
        self.survivors_alert_label.setText(f"Survivors detected: {survivors_count}")

        # Emergency teams alert
        if fire_count > 5:
            self.disaster_alert_label.setText("Disaster type: Fire disaster")
            self.emergency_teams_alert_label.setText("<span style='color: blue;'>Alerts: Fire truck and other emergency teams required</span>")
        else:
            self.disaster_alert_label.setText("Disaster type: Other disaster")
            self.emergency_teams_alert_label.setText("Emergency teams: Not required")

        if survivors_count > 0:
            self.emergency_teams_alert_label.setText("<span style='color: red;'>Alerts: Survivors detected, send emergency teams</span>")

    def toggle_recording(self):
        """Toggle video recording."""
        self.camera.toggle_recording()
        self.is_recording = not self.is_recording
        if self.is_recording:
            self.record_btn.setText("Stop Recording")
            self.live_reporting.append("<span style='color: green;'>Recording started.</span>")
        else:
            self.record_btn.setText("Record")
            self.live_reporting.append("<span style='color: green;'>Recording stopped.</span>")

    def take_photo(self):
        if self.camera_running:
            pixmap = self.camera_view.pixmap()
            if pixmap:
                if not os.path.exists("output"):
                    os.makedirs("output")
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = os.path.join("output", f"photo_{timestamp}.jpg")
                pixmap.save(filename, "JPEG")
                self.photos.append(filename)  # Add the photo path to the list
                self.live_reporting.append(f"<span style='color: green;'>Photo saved to {filename}</span>")
    
    def generate_report(self):
        

        if not os.path.exists("output"):
            os.makedirs("output")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = os.path.join("output", f"report_{timestamp}.pdf")

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)

        # Report Title
        pdf.cell(200, 10, txt="UAV Search and Rescue Report", ln=1, align='C')
        pdf.cell(200, 10, txt=f"Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=1, align='L')
        pdf.ln(10)

        # Alerts Summary
        pdf.cell(200, 10, txt="Alerts Summary:", ln=1, align='L')
        alerts = [
            self.object_count_label.text(),
            self.fire_alert_label.text(),
            self.disaster_alert_label.text(),
            self.survivors_alert_label.text(),
            self.emergency_teams_alert_label.text()
        ]
        for alert in alerts:
            pdf.cell(200, 10, txt=alert, ln=1, align='L')
        pdf.ln(10)

        # Live Reporting Logs
        pdf.cell(200, 10, txt="Live Reporting Logs:", ln=1, align='L')
        live_text = self.live_reporting.toPlainText().split('\n')
        for line in live_text:
            pdf.multi_cell(0, 7, txt=line)
        pdf.ln(10)

        # Captured Photos
        if self.photos:  # Check if there are any photos
            pdf.cell(200, 10, txt="Captured Photos:", ln=1, align='L')
            for photo in self.photos:
                try:
                    pdf.cell(200, 7, txt=photo, ln=1, align='L')
                    img = Image.open(photo)
                    img.thumbnail((160, 120))  # Resize for fitting
                    img_path = os.path.join("output", f"temp_{os.path.basename(photo)}")
                    img.save(img_path, format="JPEG")
                    pdf.image(img_path, x=10, w=60)
                    pdf.ln(5)
                except Exception as e:
                    pdf.cell(200, 7, txt=f"Error loading image: {e}", ln=1, align='L')
            pdf.ln(10)

        # Recorded Videos
        if self.videos:  # Check if there are any videos
            pdf.cell(200, 10, txt="Recorded Videos:", ln=1, align='L')
            for video in self.videos:
                pdf.multi_cell(0, 7, txt=video)

        # Save PDF
        pdf.output(report_filename)
        self.live_reporting.append(f"<span style='color: green;'>Report saved to {report_filename}</span>")
    
    def show_about(self):
        QMessageBox.information(self, "About", "UAV Camera Application\nVersion 1.0\nDeveloped by [CSE-AIML 16] (2021-2025)\nGuide:[Mr. Ravindra Naick]\nTeam Members:\n1. Aanand Pandit\n2. G. Hareesh\n3. K. Kavitha\n4. S. Rajesh\nSree Vidyanikethan Engineering College")

    def show_examples(self):
        QMessageBox.information(self, "Examples", "Example scenarios:\n1. Fire detection\n2. Object counting\n3. Disaster monitoring\n4. Emergency response\n5. Live reporting\n6. Photo and video capture\n7. Alert system")
