import urllib.request
import urllib.error
import base64
import hashlib
import datetime
import os
import random
import re
import html
from typing import Tuple, Optional

class ONVIFClient:
    """
    Lightweight ONVIF Client (No external dependencies)
    Handles WS-Security Authentication and Stream URI retrieval
    """
    
    def __init__(self, ip: str, port: int = 80, username: str = None, password: str = None):
        self.ip = ip
        self.port = port
        self.username = username
        self.password = password
        self.device_url = f"http://{ip}:{port}/onvif/device_service"
        self.media_url = None
        self.profiles = []
        
    def _create_auth_header(self) -> str:
        """Create WS-Security Header"""
        if not self.username:
            return ""
            
        # Generate nonce
        nonce_bytes = os.urandom(16)
        nonce_b64 = base64.b64encode(nonce_bytes).decode('utf-8')
        
        # Get timestamp
        timestamp = datetime.datetime.utcnow().isoformat() + "Z"
        
        # Create digest: Base64(SHA1(nonce + created + password))
        digest = hashlib.sha1(
            nonce_bytes + 
            timestamp.encode('utf-8') + 
            self.password.encode('utf-8')
        ).digest()
        password_digest = base64.b64encode(digest).decode('utf-8')
        
        return f"""
        <s:Header>
            <Security s:mustUnderstand="1" xmlns="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd">
                <UsernameToken>
                    <Username>{self.username}</Username>
                    <Password Type="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0#PasswordDigest">{password_digest}</Password>
                    <Nonce EncodingType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0#Base64Binary">{nonce_b64}</Nonce>
                    <Created xmlns="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">{timestamp}</Created>
                </UsernameToken>
            </Security>
        </s:Header>
        """

    def _send_soap_request(self, url: str, body: str, action: str = None) -> str:
        """Send SOAP request"""
        header = self._create_auth_header()
        
        envelope = f"""<?xml version="1.0" encoding="utf-8"?>
        <s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope">
            {header}
            <s:Body xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
                {body}
            </s:Body>
        </s:Envelope>"""
        
        req = urllib.request.Request(url, data=envelope.encode('utf-8'), method='POST')
        req.add_header('Content-Type', 'application/soap+xml; charset=utf-8')
        if action:
            req.add_header('SOAPAction', action)
            
        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                return response.read().decode('utf-8')
        except urllib.error.HTTPError as e:
            raise Exception(f"HTTP Error {e.code}: {e.reason}")
        except urllib.error.URLError as e:
            raise Exception(f"Network Error: {e.reason}")

    def get_media_service(self) -> str:
        """Get Media Service URL"""
        body = '<GetCapabilities xmlns="http://www.onvif.org/ver10/device/wsdl"><Category>Media</Category></GetCapabilities>'
        try:
            response = self._send_soap_request(self.device_url, body)
            
            # Simple regex to find XAddr
            # Pattern matches <tt:XAddr>http://...</tt:XAddr> inside Media element
            # Note: Namespace prefixes (tt:) might vary, so we look for XAddr tag
            match = re.search(r'Media>.*?<[^:]*:XAddr>(.*?)</[^:]*:XAddr>', response, re.DOTALL)
            if match:
                self.media_url = match.group(1).strip()
                return self.media_url
            
            # Fallback regex if structure is slightly different
            match = re.search(r'<[^:]*:XAddr>(.*?)</[^:]*:XAddr>', response)
            if match:
                self.media_url = match.group(1).strip()
                return self.media_url
                
            raise Exception("Media Service URL not found in capabilities")
            
        except Exception as e:
            raise Exception(f"Failed to get capabilities: {e}")

    def get_profiles(self) -> list:
        """Get Media Profiles to find a token"""
        if not self.media_url:
            self.get_media_service()
            
        body = '<GetProfiles xmlns="http://www.onvif.org/ver10/media/wsdl"/>'
        try:
            response = self._send_soap_request(self.media_url, body)
            
            # Find all profile tokens
            # <trt:Profiles token="Profile1" fixed="true">
            tokens = re.findall(r'Profiles[^>]*?token="([^"]+)"', response)
            self.profiles = tokens
            return tokens
            
        except Exception as e:
            raise Exception(f"Failed to get profiles: {e}")

    def get_stream_uri(self, profile_token: str = None) -> str:
        """Get RTSP Stream URI for a profile"""
        if not self.profiles and not profile_token:
            self.get_profiles()
            
        if not profile_token:
            if not self.profiles:
                raise Exception("No media profiles found")
            profile_token = self.profiles[0] # Use first profile
            
        body = f"""
        <GetStreamUri xmlns="http://www.onvif.org/ver10/media/wsdl">
            <StreamSetup>
                <Stream xmlns="http://www.onvif.org/ver10/schema">RTP-Unicast</Stream>
                <Transport xmlns="http://www.onvif.org/ver10/schema">
                    <Protocol>RTSP</Protocol>
                </Transport>
            </StreamSetup>
            <ProfileToken>{profile_token}</ProfileToken>
        </GetStreamUri>
        """
        
        try:
            response = self._send_soap_request(self.media_url, body)
            
            # Extract URI
            # <trt:Uri>rtsp://...</trt:Uri>
            match = re.search(r'<[^:]*:Uri>(.*?)</[^:]*:Uri>', response)
            if match:
                uri = html.unescape(match.group(1).strip())
                # Ensure credentials are in the URI if not present
                if self.username and self.password and '@' not in uri:
                    scheme, rest = uri.split('://', 1)
                    return f"{scheme}://{self.username}:{self.password}@{rest}"
                return uri
                
            raise Exception("Stream URI not found in response")
            
        except Exception as e:
            raise Exception(f"Failed to get stream URI: {e}")

if __name__ == "__main__":
    # Test
    client = ONVIFClient("192.168.0.254", 80, "admin", "admin")
    try:
        print("Getting Media Service...")
        media = client.get_media_service()
        print(f"Media Service: {media}")
        
        print("Getting Profiles...")
        profiles = client.get_profiles()
        print(f"Profiles: {profiles}")
        
        if profiles:
            print("Getting Stream URI...")
            uri = client.get_stream_uri(profiles[0])
            print(f"Stream URI: {uri}")
    except Exception as e:
        print(f"Error: {e}")
