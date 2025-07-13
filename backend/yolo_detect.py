import json
import cv2
import numpy as np
from ultralytics import YOLO
from datetime import datetime
import winsound

# Load YOLOv8 model
model = YOLO("yolov8s.pt")  # You can change to 'yolov8n.pt' or 'yolov8m.pt' if needed

# Open webcam
#cap = cv2.VideoCapture(1)  # 0 = default webcam
cap = cv2.VideoCapture("../data/videos/crowd.mp4")
# Adjust path as needed

# 🛠 Optional: Fix black screen issue by setting resolution
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
#1280x720 is also a common resolution, adjust as needed

# Check if webcam opened
if not cap.isOpened():
    print("❌ Error: Could not open webcam.")
    exit()

alerted_zones = set()

while cap.isOpened():
    success, frame = cap.read()
    if not success:
        print("❌ Failed to read frame from webcam.")
        break

    # Run YOLOv8 inference
    results = model(frame)

    # Set up 3x3 grid
    rows, cols = 3, 3
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

            if zone_count <= 3:
                level = "Low"
            elif zone_count <= 6:
                level = "Medium"
            elif zone_count <= 10:
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

                # Beep
                winsound.Beep(1000, 500)

                # Log to file
                alert_message = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ALERT: {zone_id} is in CRITICAL state with {zone_count} people\n"
                with open("alerts_log.txt", "a") as log_file:
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

    # Save zone info as JSON
    with open("zone_data.json", "w") as f:
        json.dump(frame_data, f)

    # Show total count
    cv2.putText(frame, f"Total People: {total_count}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

    # Show the output
    cv2.imshow("YOLOv8 Zone-Based Crowd Detection", frame)
    cv2.namedWindow("YOLOv8 Zone-Based Crowd Detection", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("YOLOv8 Zone-Based Crowd Detection", 1920, 1080)
    #1280x720 is also a common resolution, adjust as needed 
    
    
    if cv2.waitKey(1) == ord('q'):
        break

# Cleanup
cap.release()
cv2.destroyAllWindows()
