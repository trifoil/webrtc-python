#!/usr/bin/env python3

import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstVideo', '1.0')
from gi.repository import Gst, GstVideo, GLib
import numpy as np
import time
import threading
import queue

class GStreamerTest:
    def __init__(self, camera_id=1, width=640, height=480, fps=30):
        Gst.init(None)
        self.camera_id = camera_id
        self.width = width
        self.height = height
        self.fps = fps
        self.frame_count = 0
        self.running = False
        
        # Create simple pipeline for testing
        self.pipeline_str = (
            f"v4l2src device=/dev/video{camera_id} ! "
            f"video/x-raw,width={width},height={height},framerate={fps}/1 ! "
            "videoconvert ! "
            "video/x-raw,format=RGB ! "
            "appsink name=sink sync=false max-buffers=1 drop=true"
        )
        
        print(f"Testing pipeline: {self.pipeline_str}")
        
        try:
            self.pipeline = Gst.parse_launch(self.pipeline_str)
            self.sink = self.pipeline.get_by_name("sink")
            self.sink.connect("new-sample", self.on_new_sample, None)
            print("✓ Pipeline created successfully")
        except Exception as e:
            print(f"✗ Failed to create pipeline: {e}")
            return
    
    def on_new_sample(self, sink, data):
        """Callback when new frame is available"""
        try:
            sample = sink.emit("pull-sample")
            buffer = sample.get_buffer()
            
            # Map buffer to memory
            success, map_info = buffer.map(Gst.MapFlags.READ)
            if not success:
                return Gst.FlowReturn.ERROR
            
            try:
                # Create numpy array from buffer
                frame_data = np.ndarray(
                    shape=(self.height, self.width, 3),
                    dtype=np.uint8,
                    buffer=map_info.data
                )
                
                self.frame_count += 1
                print(f"✓ Received frame {self.frame_count} - Shape: {frame_data.shape}, Type: {frame_data.dtype}")
                
                # Stop after 5 frames for testing
                if self.frame_count >= 5:
                    self.stop()
                    
            finally:
                buffer.unmap(map_info)
                
        except Exception as e:
            print(f"✗ Error in on_new_sample: {e}")
            
        return Gst.FlowReturn.OK
    
    def start(self):
        """Start the GStreamer pipeline"""
        if self.running:
            return
            
        try:
            self.running = True
            self.pipeline.set_state(Gst.State.PLAYING)
            print(f"✓ GStreamer pipeline started with camera {self.camera_id}")
            
            # Monitor for 10 seconds
            time.sleep(10)
            self.stop()
            
        except Exception as e:
            print(f"✗ Failed to start pipeline: {e}")
    
    def stop(self):
        """Stop the GStreamer pipeline"""
        self.running = False
        if hasattr(self, 'pipeline') and self.pipeline:
            self.pipeline.set_state(Gst.State.NULL)
        print("✓ Pipeline stopped")

def test_camera_devices():
    """Test available camera devices"""
    import os
    
    print("Available camera devices:")
    for i in range(4):  # Check first 4 devices
        device_path = f"/dev/video{i}"
        if os.path.exists(device_path):
            print(f"  ✓ {device_path}")
        else:
            print(f"  ✗ {device_path} (not found)")

def main():
    print("GStreamer Camera Test")
    print("=" * 40)
    
    # Test available devices
    test_camera_devices()
    print()
    
    # Test GStreamer pipeline
    camera_id = 1  # Change this if needed
    test = GStreamerTest(camera_id)
    test.start()
    
    print("\nTest completed!")

if __name__ == "__main__":
    main() 