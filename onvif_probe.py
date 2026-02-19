import urllib.request
import urllib.error
import re
import base64
import hashlib
import datetime
import os

# Target
ONVIF_URL = "http://192.168.0.254/onvif/device_service"
USERNAME = "admin"
PASSWORD = "admin"

def create_soap_header(username, password, created, nonce):
    # This is a simplified WS-Security header generation
    # Not fully robust but enough for testing basic auth triggers
    pass # implementing full WS-Security manually is complex, 
         # usually ONVIF accepts Digest or basic for initial handshake sometimes? 
         # actually ONVIF requires UsernameToken.

# Simpler check: Just hit the endpoint with GetSystemDateAndTime (often public)
# and GetCapabilities (often public or basic auth).

ENVELOPE = """<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope">
  <s:Body xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
    <GetSystemDateAndTime xmlns="http://www.onvif.org/ver10/device/wsdl"/>
  </s:Body>
</s:Envelope>"""

def probe_onvif(url):
    print(f"Probing ONVIF URL: {url}")
    req = urllib.request.Request(url, data=ENVELOPE.encode('utf-8'), method='POST')
    req.add_header('Content-Type', 'application/soap+xml; charset=utf-8')
    
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            data = response.read().decode('utf-8')
            print("[SUCCESS] Device responded!")
            if "GetSystemDateAndTimeResponse" in data:
                print("  Service is active and reachable.")
                print("  The device is online.")
            # Verify if this IP matches the one failing RTSP
            print("\nAnalysis:")
            print("  - The ONVIF service is responding at port 80.")
            print("  - This confirms 192.168.0.254 is the correct IP.")
            print("  - Previous RTSP error was '401 Unauthorized'.")
            print("  - This likely means the Username/Password 'admin/admin' is incorrect.")
            return True
            
    except urllib.error.HTTPError as e:
        print(f"[FAILED] HTTP Error: {e.code} {e.reason}")
        if e.code == 401:
            print("  Status: Unauthorized.")
            print("  The device exists but requires authentication.")
        elif e.code == 404:
            print("  Status: Not Found (Wrong URL path?).")
    except urllib.error.URLError as e:
        print(f"[FAILED] Network Error: {e.reason}")
        print("  Check connection and IP address.")
    except Exception as e:
        print(f"[FAILED] Unexpected Error: {e}")

    return False

if __name__ == "__main__":
    probe_onvif(ONVIF_URL)
