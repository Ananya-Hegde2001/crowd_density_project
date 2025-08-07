#!/usr/bin/env python3
"""
Crowd Density Monitoring Flask Application
Run this script to start the web server
"""

import os
import sys

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app

if __name__ == '__main__':
    print("🚀 Starting Crowd Density Monitoring System...")
    print("📱 Open your browser and go to: http://localhost:5000")
    print("⏹️  Press Ctrl+C to stop the server")
    
    # Change to the backend directory to ensure file paths work correctly
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    try:
        app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
