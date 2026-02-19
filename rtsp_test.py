import cv2
import time
import os

# usage: python rtsp_test.py

CAM_IP = "192.168.0.254"
# Try empty credentials if none were provided
USERNAME = "admin" 
PASSWORD = "admin" # Default - try also empty

def test_rtsp_connection(url):
    print(f"Testing URL: {url}")
    cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
    if cap.isOpened():
        ret, frame = cap.read()
        if ret:
            print(f"  [SUCCESS] Connected! Working URL: {url}")
            cap.release()
            return True
    cap.release()
    return False

# Common ONVIF/RTSP paths to try
paths = [
    f"rtsp://{USERNAME}:{PASSWORD}@{CAM_IP}:554/stream1",
    f"rtsp://{USERNAME}:{PASSWORD}@{CAM_IP}:554/live",
    f"rtsp://{USERNAME}:{PASSWORD}@{CAM_IP}:554/onvif1",
    f"rtsp://{USERNAME}:{PASSWORD}@{CAM_IP}/live/ch0",
    f"rtsp://{USERNAME}:{PASSWORD}@{CAM_IP}:554/h264_stream",
    f"rtsp://{USERNAME}:{PASSWORD}@{CAM_IP}:554/11",
    f"rtsp://{USERNAME}:{PASSWORD}@{CAM_IP}:554/1",
    # Try without port 554
    f"rtsp://{USERNAME}:{PASSWORD}@{CAM_IP}/stream1",
    # Try without credentials (if open)
    f"rtsp://{CAM_IP}:554/stream1",
    f"rtsp://{CAM_IP}/live",
    # Try the ONVIF service port just in case (unlikely for RTSP but possible)
     f"rtsp://{USERNAME}:{PASSWORD}@{CAM_IP}:80/live",
]

print(f"Starting Brute-Force RTSP Finder for {CAM_IP}...\n")

for url in paths:
    if test_rtsp_connection(url):
        print("\n✅ FOUND IT! Use this URL in SolCam Settings:")
        print(f"   {url}")
        break
else:
    print("\n❌ Could not find a working stream path.")
    print("Try checking if ONVIF Discovery tool gives a specific 'Media URL'.")
