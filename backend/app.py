from flask import Flask, render_template, Response, jsonify, request, send_file
import json
import cv2
import numpy as np
from ultralytics import YOLO
from datetime import datetime
import winsound
import threading
import time
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max file size

# Create upload directory if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Load configuration
def load_config():
    try:
        with open('config.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        # Default configuration if file not found
        return {
            "camera_settings": {"camera_index": 1, "width": 640, "height": 480},
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
video_processing_active = False
uploaded_video_path = None

def initialize_camera():
    """Initialize the camera with proper settings and start monitoring"""
    global cap, is_streaming, camera_active
    cam_settings = config["camera_settings"]
    
    # Try camera index 0 first, then 1
    camera_indices = [0, 1]
    
    for camera_index in camera_indices:
        print(f"🔍 Trying camera index {camera_index}...")
        cap = cv2.VideoCapture(camera_index)
        
        if cap.isOpened():
            # Set camera properties
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            
            # Test if camera can read frames
            ret, test_frame = cap.read()
            if ret and test_frame is not None:
                print(f"✅ Camera {camera_index} is working!")
                camera_active = True
                is_streaming = True
                print(f"✅ Camera {camera_index} initialized and monitoring started")
                return True
            else:
                print(f"❌ Camera {camera_index} opened but cannot read frames")
                cap.release()
        else:
            print(f"❌ Camera {camera_index} could not be opened")
    
    print("❌ Error: Could not open webcam.")
    camera_active = False
    cap = None
    return False

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
        print("⚠️ Camera not active or not opened")
        return None, None
    
    try:
        success, frame = cap.read()
        if not success or frame is None:
            print("⚠️ Failed to read frame from camera")
            return None, None

        if frame.size == 0:
            print("⚠️ Empty frame received")
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
        
    except Exception as e:
        print(f"❌ Error processing frame: {str(e)}")
        return None, None

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

@app.route('/video-upload')
def video_upload():
    """Video upload page"""
    return render_template('video_upload.html')

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
        "alerted_zones": list(alerted_zones),
        "video_processing_active": video_processing_active
    })

@app.route('/api/upload-video', methods=['POST'])
def upload_video():
    """Handle video file upload"""
    if 'video' not in request.files:
        return jsonify({"status": "error", "message": "No video file provided"}), 400
    
    file = request.files['video']
    if file.filename == '':
        return jsonify({"status": "error", "message": "No file selected"}), 400
    
    if file:
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_")
        filename = timestamp + filename
        
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        try:
            file.save(filepath)
            
            global uploaded_video_path
            uploaded_video_path = filepath
            
            return jsonify({
                "status": "success", 
                "message": "Video uploaded successfully",
                "filename": filename,
                "filepath": filepath
            })
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f"Failed to save video file: {str(e)}"
            }), 500

def process_video_frame(frame):
    """Process a single video frame and return detection data"""
    global current_zone_data
    
    # Run YOLOv8 inference
    results = model(frame)

    # Set up grid
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

    # Show total count
    cv2.putText(frame, f"Total People: {total_count}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

    return frame, frame_data

@app.route('/api/process-video', methods=['POST'])
def process_video():
    """Process uploaded video file"""
    global video_processing_active, uploaded_video_path
    
    # Check if video path is provided in request
    request_data = request.get_json()
    if request_data and 'video_path' in request_data:
        video_path = request_data['video_path']
    else:
        video_path = uploaded_video_path
    
    if not video_path or not os.path.exists(video_path):
        return jsonify({"status": "error", "message": "No video file to process"}), 400
    
    try:
        video_processing_active = True
        cap_video = cv2.VideoCapture(video_path)
        
        if not cap_video.isOpened():
            return jsonify({"status": "error", "message": "Could not open video file"}), 400
        
        # Get video properties
        fps = cap_video.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap_video.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count / fps if fps > 0 else 0
        
        # Process first frame to get initial data
        ret, frame = cap_video.read()
        if ret:
            processed_frame, zone_data = process_video_frame(frame)
        
        cap_video.release()
        video_processing_active = False
        
        return jsonify({
            "status": "success",
            "message": "Video processed successfully",
            "video_info": {
                "fps": fps,
                "frame_count": frame_count,
                "duration": duration
            }
        })
        
    except Exception as e:
        video_processing_active = False
        return jsonify({"status": "error", "message": f"Error processing video: {str(e)}"}), 500

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
