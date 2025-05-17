from PyQt5.QtCore import QObject, pyqtSignal
import threading
import cv2
import numpy as np
import requests
from PyQt5.QtGui import QImage, QPixmap
from ultralytics import YOLO
import torch
import os
from datetime import datetime

class CameraView(QObject):
    frame_updated = pyqtSignal(QPixmap)
    objects_detected = pyqtSignal(dict) 

    def __init__(self):
        super().__init__()
        self.running = False
        self.recording = False
        self.video_writer = None
        self.frame_rate = 10
        self.frame_size = (1600, 1200)

        # Check for GPU availability
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Using {device} for processing")

        # Load all three models
        self.models = {
            "coco": YOLO("yolov8s.pt").to(device),
            "rescue": YOLO("rescue.pt").to(device),
            "emergency": YOLO("amb_fire.pt").to(device)
        }

        # Define relevant class indices for each model
        self.class_names = {
            "coco": {
                0: "person", 2: "car", 5: "bus", 7: "truck",
                9: "traffic light", 10: "fire hydrant", 67: "cell phone"
            },
            "rescue": {
                2: "gloves", 3: "helmet", 4: "vest"
            },
            "emergency": {
                0: "Ambulance", 3: "Fire", 4: "Fire-truck",
                5: "Hazmat-Sign", 6: "License-plate",
                8: "Police-car", 11: "Smoke"
            }
        }

        # Define colors for each class using HEX converted to BGR
        self.class_colors = {
            "person": (0, 0, 255),  # Red
            "car": (0, 255, 0),  # Green
            "bus": (255, 165, 0),  # Orange
            "truck": (255, 0, 0),  # Blue
            "traffic light": (255, 255, 0),  # Cyan
            "fire hydrant": (255, 0, 255),  # Magenta
            "cell phone": (0, 255, 255),  # Yellow
            "gloves": (128, 0, 128),  # Purple
            "helmet": (255, 215, 0),  # Gold
            "vest": (165, 42, 42),  # Brown
            "Ambulance": (255, 0, 0),  # Red
            "Fire": (255, 69, 0),  # Orange-Red
            "Fire-truck": (139, 0, 0),  # Dark Red
            "Hazmat-Sign": (255, 223, 0),  # Gold-Yellow
            "License-plate": (128, 128, 128),  # Gray
            "Police-car": (0, 0, 255),  # Blue
            "Smoke": (105, 105, 105)  # Dim Gray
        }

        # ESP32-CAM stream URL
        self.ip = "http://192.168.4.1"  # Change this to your ESP32-CAM's IP address
        self.url = self.ip + "/"  # Root path for video streaming
        self.stream = None
        self.frame = None
        self.frame_lock = threading.Lock()

    def start(self):
        """Start video processing thread."""
        if self.running:
            return
        self.running = True

        # Start the ESP32-CAM stream
        self.stream = requests.get(self.url, stream=True)

        # Start the thread to fetch frames from the ESP32-CAM
        self.fetch_thread = threading.Thread(target=self.fetch_frames, daemon=True)
        self.fetch_thread.start()

        # Start the thread to process frames
        self.process_thread = threading.Thread(target=self.run)
        self.process_thread.start()

    def fetch_frames(self):
        """Fetch frames from the ESP32-CAM stream."""
        bytes_data = b''
        for chunk in self.stream.iter_content(chunk_size=1024):
            if not self.running:
                break

            # Append the incoming chunk to our bytes_data buffer
            bytes_data += chunk

            # Look for a complete JPEG frame in the buffer
            a = bytes_data.find(b'\xff\xd8')  # Start of JPEG
            b = bytes_data.find(b'\xff\xd9')  # End of JPEG

            if a != -1 and b != -1:
                jpg = bytes_data[a:b+2]  # Get the complete JPEG frame

                # Decode the JPEG into an image
                img = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)

                # Use a lock to safely update the global frame
                with self.frame_lock:
                    self.frame = img

                # Remove the processed frame from the buffer
                bytes_data = bytes_data[b+2:]

    def run(self):
        """Process frames from the ESP32-CAM stream."""
        while self.running:
            with self.frame_lock:
                if self.frame is None:
                    continue

                frame = self.frame.copy()

            # Flip the frame horizontally for a mirror effect
            frame = cv2.flip(frame, 1)
            detected_counts = {}  # Dictionary to store detected objects and their counts

            threads = []
            results_list = []

            def process_model(model_key):
                """Process the frame using the specified model."""
                results = self.models[model_key](frame)  # Run inference on the frame
                results_list.append((model_key, results))

            # Start threads for each model
            for key in self.models.keys():
                t = threading.Thread(target=process_model, args=(key,))
                threads.append(t)
                t.start()

            # Wait for all threads to finish
            for t in threads:
                t.join()

            # Process results from all models
            for model_key, results in results_list:
                valid_classes = self.class_names[model_key]  # Get valid classes for the model

                for result in results:
                    boxes = result.boxes.xyxy.cpu().numpy()  # Get bounding boxes
                    clss = result.boxes.cls.cpu().numpy()  # Get class indices
                    confs = result.boxes.conf.cpu().numpy()  # Get confidence scores

                    h, w, _ = frame.shape  # Get frame dimensions

                    for box, cls, conf in zip(boxes, clss, confs):
                        if conf < 0.45:  # Skip low-confidence detections
                            continue

                        cls_idx = int(cls)
                        if cls_idx not in valid_classes:  # Skip irrelevant classes
                            continue

                        class_name = valid_classes[cls_idx]  # Get class name
                        color = self.class_colors.get(class_name, (0, 255, 0))  # Get color for the class

                        # Update detected_counts dictionary
                        detected_counts[class_name] = detected_counts.get(class_name, 0) + 1

                        # Draw bounding box and label
                        x1, y1, x2, y2 = map(int, box)
                        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

                        # Add label text
                        label_text = f"{class_name} {conf:.2f}"
                        text_size = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
                        text_x, text_y = x1, y1 - 5

                        # Adjust text position if it goes out of frame
                        if text_y < 10:  # Prevent text from going above the frame
                            text_y = y1 + text_size[1] + 5

                        if text_x + text_size[0] > w:  # Prevent text from going off the right edge
                            text_x = w - text_size[0] - 10

                        if text_x < 0:  # Prevent text from going off the left edge
                            text_x = 10

                        # Draw background for text
                        cv2.rectangle(frame, (text_x - 2, text_y - text_size[1] - 2),
                                    (text_x + text_size[0] + 2, text_y + 2), color, -1)

                        # Draw text
                        cv2.putText(frame, label_text, (text_x, text_y),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

            # Emit the detected_counts dictionary
            self.objects_detected.emit(detected_counts)

            # Convert the frame to RGB for display in the GUI
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_frame.shape
            bytes_per_line = ch * w
            qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
            qt_pixmap = QPixmap.fromImage(qt_image)

            # Emit the updated frame
            self.frame_updated.emit(qt_pixmap)

           # If recording, write the frame to the video file
            if self.recording:
                if self.video_writer is None:
                    # Create the output folder if it doesn't exist
                    if not os.path.exists("output"):
                        os.makedirs("output")

                    # Generate a timestamp for the filename
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    output_filename = os.path.join("output", f"recording_{timestamp}.avi")

                    # Initialize the video writer
                    fourcc = cv2.VideoWriter_fourcc(*'XVID')
                    self.video_writer = cv2.VideoWriter(output_filename, fourcc, self.frame_rate, self.frame_size)

                # Write the frame to the video file
                self.video_writer.write(frame)

    def stop(self):
        """Stop video processing."""
        self.running = False
        if hasattr(self, "process_thread"):
            self.process_thread.join()
        if hasattr(self, "fetch_thread"):
            self.fetch_thread.join()
        if self.video_writer is not None:
            self.video_writer.release()
            self.video_writer = None

    def toggle_recording(self):
        """Toggle video recording."""
        self.recording = not self.recording
        if not self.recording and self.video_writer is not None:
            self.video_writer.release()
            self.video_writer = None