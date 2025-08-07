from flask import Flask, render_template, Response, jsonify
import json
import cv2
import numpy as np
from ultralytics import YOLO
from datetime import datetime
import winsound
import threading
import time
import os

app = Flask(__name__)

# Load configuration
def load_config():
    try:
        with open('config.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        # Default configuration if file not found
        return {
            "camera_settings": {"camera_index": 1, "width": 1920, "height": 1080},
            "detection_settings": {"model_path": "yolov8s.pt", "grid_size": {"rows": 3, "cols": 3}},
            "zone_thresholds": {"low": 3, "medium": 6, "high": 10},
            "alert_settings": {"enable_sound": True, "log_file": "alerts_log.txt"}
        }

config = load_config()

# Global variables
model = YOLO(config["detection_settings"]["model_path"])
cap = None
current_zone_data = {"total": 0, "zones": []}
alerted_zones = set()
is_streaming = False
camera_active = False

def initialize_camera():
    """Initialize the camera with proper settings and start monitoring"""
    global cap, is_streaming, camera_active
    cam_settings = config["camera_settings"]
    cap = cv2.VideoCapture(cam_settings["camera_index"])
    
    # Optional: Fix black screen issue by setting resolution
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, cam_settings["width"])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cam_settings["height"])
    
    if not cap.isOpened():
        print("❌ Error: Could not open webcam.")
        camera_active = False
        return False
    
    # Camera opened successfully, start monitoring automatically
    camera_active = True
    is_streaming = True
    print("✅ Camera initialized and monitoring started")
    return True

def stop_camera():
    """Stop camera and monitoring"""
    global cap, is_streaming, camera_active
    is_streaming = False
    camera_active = False
    if cap is not None:
        cap.release()
        cap = None
    print("🛑 Camera stopped and monitoring ended")

def process_frame():
    """Process a single frame and return detection data"""
    global current_zone_data, alerted_zones
    
    if not camera_active or cap is None or not cap.isOpened():
        return None, None
    
    success, frame = cap.read()
    if not success:
        return None, None

    # Run YOLOv8 inference
    results = model(frame)

    # Set up 3x3 grid
    grid_size = config["detection_settings"]["grid_size"]
    rows, cols = grid_size["rows"], grid_size["cols"]
    height, width = frame.shape[:2]
    zone_h, zone_w = height // rows, width // cols
    zone_counts = np.zeros((rows, cols), dtype=int)

    total_count = 0

    for r in results:
        for box in r.boxes:
            cls = int(box.cls[0])
            if cls == 0:  # Person class
                total_count += 1
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

                row = min(cy // zone_h, rows - 1)
                col = min(cx // zone_w, cols - 1)
                zone_counts[row][col] += 1

                # Draw bounding box around person
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

    # Prepare zone data
    frame_data = {
        "total": int(total_count),
        "zones": []
    }

    for row in range(rows):
        for col in range(cols):
            zone_id = f"Z{row * cols + col + 1}"
            zone_count = int(zone_counts[row][col])

            thresholds = config["zone_thresholds"]
            if zone_count <= thresholds["low"]:
                level = "Low"
            elif zone_count <= thresholds["medium"]:
                level = "Medium"
            elif zone_count <= thresholds["high"]:
                level = "High"
            else:
                level = "Critical"

            frame_data["zones"].append({
                "id": zone_id,
                "count": zone_count,
                "level": level
            })

            # Draw zone and label
            x_start = col * zone_w
            y_start = row * zone_h
            x_end = x_start + zone_w
            y_end = y_start + zone_h

            # Handle alerts and logging
            if level == "Critical" and zone_id not in alerted_zones:
                print(f"🚨 ALERT: {zone_id} is in CRITICAL state with {zone_count} people!")
                alerted_zones.add(zone_id)

                # Beep (if enabled)
                alert_settings = config["alert_settings"]
                if alert_settings["enable_sound"]:
                    try:
                        winsound.Beep(alert_settings.get("beep_frequency", 1000), 
                                    alert_settings.get("beep_duration", 500))
                    except:
                        pass  # Ignore beep errors in web environment

                # Log to file
                alert_message = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ALERT: {zone_id} is in CRITICAL state with {zone_count} people\n"
                with open(alert_settings["log_file"], "a") as log_file:
                    log_file.write(alert_message)

            elif level != "Critical" and zone_id in alerted_zones:
                alerted_zones.remove(zone_id)

            # Set zone color
            if level == "Low":
                color = (0, 255, 0)
            elif level == "Medium":
                color = (0, 255, 255)
            elif level == "High":
                color = (0, 165, 255)
            else:
                color = (0, 0, 255)

            # Draw zone rectangle and label
            cv2.rectangle(frame, (x_start, y_start), (x_end, y_end), color, 2)
            cv2.putText(frame, f"{level} ({zone_count})", (x_start + 5, y_start + 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    # Update global zone data
    current_zone_data = frame_data

    # Save zone info as JSON
    with open("zone_data.json", "w") as f:
        json.dump(frame_data, f)

    # Show total count
    cv2.putText(frame, f"Total People: {total_count}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

    return frame, frame_data

def generate_frames():
    """Generate frames for video streaming - only runs when camera is active"""
    global is_streaming
    
    while is_streaming and camera_active:
        frame, zone_data = process_frame()
        if frame is not None:
            # Encode frame to JPEG
            ret, buffer = cv2.imencode('.jpg', frame)
            if ret:
                frame_bytes = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        time.sleep(0.1)  # Control frame rate

@app.route('/')
def index():
    """Main page with video stream"""
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    """Video streaming route - only works when camera is active"""
    if not camera_active:
        return "Camera not started. Please start the camera first.", 404
    
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/zones')
def get_zones():
    """API endpoint to get current zone data"""
    return jsonify(current_zone_data)

@app.route('/api/start')
def start_camera_api():
    """Start the camera and begin monitoring"""
    if camera_active:
        return jsonify({"status": "already_active", "message": "Camera is already active and monitoring"})
    
    if initialize_camera():
        return jsonify({"status": "started", "message": "Camera started and monitoring began successfully"})
    else:
        return jsonify({"status": "error", "message": "Failed to initialize camera"}), 500

@app.route('/api/stop')
def stop_camera_api():
    """Stop the camera and end monitoring"""
    if not camera_active:
        return jsonify({"status": "already_stopped", "message": "Camera is already stopped"})
    
    stop_camera()
    return jsonify({"status": "stopped", "message": "Camera stopped and monitoring ended"})

@app.route('/api/alerts')
def get_alerts():
    """Get recent alerts from log file"""
    try:
        log_file = config["alert_settings"]["log_file"]
        with open(log_file, "r") as f:
            alerts = f.readlines()[-10:]  # Get last 10 alerts
        return jsonify({"alerts": [alert.strip() for alert in alerts]})
    except FileNotFoundError:
        return jsonify({"alerts": []})

@app.route('/api/config')
def get_config():
    """Get current configuration"""
    return jsonify(config)

@app.route('/api/status')
def get_status():
    """Get system status"""
    return jsonify({
        "camera_active": camera_active,
        "is_streaming": is_streaming,
        "camera_initialized": cap is not None and cap.isOpened(),
        "total_zones": len(current_zone_data.get("zones", [])),
        "alerted_zones": list(alerted_zones)
    })

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    import os
    os.makedirs('templates', exist_ok=True)
    
    try:
        app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)
    finally:
        # Cleanup on exit
        if cap is not None:
            cap.release()
            print("🧹 Camera resources cleaned up")
