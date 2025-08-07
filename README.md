# Crowd Density Monitoring Flask App

A comprehensive real-time crowd density monitoring system using YOLOv8 and Flask, featuring both live camera monitoring and video file analysis.

## Features

- 🎥 **Real-time Camera Monitoring**: Live camera feed with crowd detection
- � **Video Upload & Analysis**: Upload and analyze pre-recorded videos
- �📊 **Zone-based Analysis**: 3x3 grid zone monitoring with density levels
- 🚨 **Alert System**: Critical zone alerts with sound notifications and logging
- 🌐 **Modern Web Interface**: Responsive, mobile-friendly dashboard
- 📱 **API Endpoints**: RESTful API for integration with other systems
- ⚙️ **Configurable**: Easy configuration through JSON file
- 📱 **Responsive Design**: Works perfectly on desktop, tablet, and mobile devices

## Installation

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Ensure YOLOv8 Model**:
   Make sure `yolov8s.pt` is in the `backend` directory. If not, it will be downloaded automatically on first run.

## Running the Application

### Method 1: Using the startup script (Recommended)
```bash
cd backend
python run_flask.py
```

### Method 2: Direct Flask run
```bash
cd backend
python app.py
```

### Method 3: Using Flask command
```bash
cd backend
set FLASK_APP=app.py
flask run --host=0.0.0.0 --port=5000
```

## Accessing the Application

1. **Main Dashboard**: Open your browser and go to `http://localhost:5000`
   - Live camera monitoring
   - Real-time zone analysis
   - Alert management

2. **Video Upload Page**: Go to `http://localhost:5000/video-upload`
   - Upload video files for analysis
   - Drag & drop interface
   - Supported formats: MP4, AVI, MOV, MKV

3. **API Endpoints**: Available at `http://localhost:5000/api/`

## Web Interface

### 🏠 Live Camera Dashboard
The main dashboard provides:
- Live video feed with person detection and zone overlays
- Real-time zone status grid with color-coded density levels
- Total person count and active zone statistics
- Recent alerts panel with timestamps
- Control buttons to start/stop camera

### 📁 Video Upload Dashboard
The video upload page offers:
- Drag & drop video file upload
- Video player with analysis controls
- Real-time processing progress
- Zone analysis during video playback
- Support for multiple video formats

### Zone Density Levels
- 🟢 **Low** (0-3 people): Safe density
- 🟡 **Medium** (4-6 people): Moderate density
- 🟠 **High** (7-10 people): High density
- 🔴 **Critical** (11+ people): Dangerous density with alerts

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Main live camera dashboard |
| `/video-upload` | GET | Video upload page |
| `/video_feed` | GET | Live video stream endpoint |
| `/api/zones` | GET | Current zone data (JSON) |
| `/api/alerts` | GET | Recent alerts list |
| `/api/start` | GET | Start camera and monitoring |
| `/api/stop` | GET | Stop camera and monitoring |
| `/api/config` | GET | Current configuration |
| `/api/status` | GET | System status |
| `/api/upload-video` | POST | Upload video file |
| `/api/process-video` | POST | Process uploaded video |

## Configuration

Edit `config.json` to customize:

```json
{
    "camera_settings": {
        "camera_index": 1,          // Camera device index
        "width": 1920,              // Camera resolution width
        "height": 1080              // Camera resolution height
    },
    "detection_settings": {
        "model_path": "yolov8s.pt", // YOLOv8 model file
        "grid_size": {
            "rows": 3,              // Grid rows
            "cols": 3               // Grid columns
        }
    },
    "zone_thresholds": {
        "low": 3,                   // Low density threshold
        "medium": 6,                // Medium density threshold
        "high": 10                  // High density threshold
    },
    "alert_settings": {
        "enable_sound": true,       // Enable sound alerts
        "log_file": "alerts_log.txt", // Alert log file
        "beep_frequency": 1000,     // Beep frequency (Hz)
        "beep_duration": 500        // Beep duration (ms)
    }
}
```

## Troubleshooting

### Camera Issues
- **Camera not found**: Change `camera_index` in config.json (try 0, 1, 2...)
- **Black screen**: Adjust resolution in camera_settings
- **Permission denied**: Ensure camera isn't being used by another application

### Performance Issues
- Use a smaller YOLO model: Change to `yolov8n.pt` for faster processing
- Reduce camera resolution in config.json
- Lower frame rate by increasing sleep time in `generate_frames()`

### Network Issues
- **Can't access from other devices**: Ensure firewall allows port 5000
- **Slow response**: Check network connection and server performance

## Files Structure

```
backend/
├── app.py                 # Main Flask application
├── run_flask.py          # Startup script
├── config.json           # Configuration file
├── templates/
│   ├── index.html        # Live camera dashboard
│   └── video_upload.html # Video upload page
├── uploads/              # Uploaded video files directory
├── yolov8s.pt           # YOLOv8 model (auto-downloaded)
├── alerts_log.txt       # Alert logs (created automatically)
└── zone_data.json       # Current zone data (created automatically)
```

## Differences from Original Script

### Improvements:
- ✅ Web-based interface instead of OpenCV window
- ✅ RESTful API for external integration
- ✅ Configuration file for easy customization
- ✅ Better error handling and logging
- ✅ Responsive design for mobile devices
- ✅ Start/stop controls without restarting application

### Changes:
- Video display moved from OpenCV window to web browser
- Camera initialization on-demand instead of at startup
- Thread-safe frame processing for web streaming
- JSON-based configuration instead of hardcoded values

## Development

To modify the application:

1. **Frontend Changes**: Edit `templates/index.html`
2. **Backend Logic**: Modify `app.py`
3. **Configuration**: Update `config.json`
4. **Styling**: Add CSS to the HTML template

## Production Deployment

For production use:

1. Set `debug: false` in config.json
2. Use a production WSGI server like Gunicorn:
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5000 app:app
   ```
3. Consider using nginx as a reverse proxy
4. Implement proper authentication and security measures
