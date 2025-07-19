#!/usr/bin/env python3

import asyncio
import socket
import time

async def test_tcp_connection(host, port, timeout=5):
    """Test TCP connection to the signaling server"""
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), 
            timeout=timeout
        )
        writer.close()
        await writer.wait_closed()
        print(f"✓ TCP connection to {host}:{port} successful")
        return True
    except Exception as e:
        print(f"✗ TCP connection to {host}:{port} failed: {e}")
        return False

def test_camera_access():
    """Test if camera is accessible"""
    try:
        import cv2
        cap = cv2.VideoCapture(1)  # Try camera ID 1
        if cap.isOpened():
            ret, frame = cap.read()
            cap.release()
            if ret:
                print("✓ Camera access successful")
                return True
            else:
                print("✗ Camera opened but failed to read frame")
                return False
        else:
            print("✗ Camera not accessible")
            return False
    except Exception as e:
        print(f"✗ Camera test failed: {e}")
        return False

async def main():
    print("Testing WebRTC connection prerequisites...")
    print("=" * 50)
    
    # Test TCP connection
    tcp_ok = await test_tcp_connection("10.10.1.100", 9999)
    
    # Test camera access
    camera_ok = test_camera_access()
    
    print("=" * 50)
    if tcp_ok and camera_ok:
        print("✓ All tests passed! Ready to run WebRTC.")
    else:
        print("✗ Some tests failed. Please check:")
        if not tcp_ok:
            print("  - Network connectivity to 10.10.1.100:9999")
            print("  - Sender is running and listening")
        if not camera_ok:
            print("  - Camera is connected and accessible")
            print("  - Try different camera ID in sender.py")

if __name__ == "__main__":
    asyncio.run(main()) 