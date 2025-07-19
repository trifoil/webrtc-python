import asyncio
# Remove cv2 import
# import cv2
import numpy as np
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from aiortc.contrib.signaling import TcpSocketSignaling
from av import VideoFrame
import fractions
from datetime import datetime
import time

import gi

# Set GStreamer version and import Gst, GLib at the top level for linter
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib

# Ensure GStreamer is available at runtime
try:
    Gst.init(None)
except Exception as e:
    raise RuntimeError("GStreamer could not be initialized. Ensure GStreamer is installed on your system.") from e

# Start GLib MainLoop in a background thread for GStreamer event processing
import threading
main_loop = GLib.MainLoop()
main_loop_thread = threading.Thread(target=main_loop.run, daemon=True)
main_loop_thread.start()

class CustomVideoStreamTrack(VideoStreamTrack):
    def __init__(self, camera_id):
        super().__init__()
        self.frame_count = 0
        self.sample = None
        self.loop = asyncio.get_event_loop()
        self.total_processing_time = 0
        self.frame_times = []
        
        # Try Intel hardware acceleration first, fallback to software if not available
        try:
            # Test if qsvh264enc is available
            test_pipeline = Gst.parse_launch("fakesrc ! qsvh264enc ! fakesink")
            test_pipeline.set_state(Gst.State.NULL)
            del test_pipeline
            
            # Use Intel Quick Sync hardware acceleration
            self.pipeline = Gst.parse_launch(
                f"v4l2src device=/dev/video{camera_id} ! "
                f"video/x-raw,format=NV12,width=640,height=480,framerate=30/1 ! "
                f"qsvh264enc bitrate=1000 ! "  # Intel hardware H.264 encoding
                f"appsink name=sink emit-signals=true max-buffers=1 drop=true"
            )
            print("Using Intel Quick Sync hardware acceleration")
        except Exception as e:
            print(f"Intel Quick Sync not available: {e}")
            try:
                # Try VA-API hardware acceleration
                test_pipeline = Gst.parse_launch("fakesrc ! vaapih264enc ! fakesink")
                test_pipeline.set_state(Gst.State.NULL)
                del test_pipeline
                
                self.pipeline = Gst.parse_launch(
                    f"v4l2src device=/dev/video{camera_id} ! "
                    f"videoconvert ! "
                    f"vaapipostproc ! "  # VA-API post-processing
                    f"vaapih264enc ! "   # VA-API H.264 encoding
                    f"appsink name=sink emit-signals=true max-buffers=1 drop=true"
                )
                print("Using VA-API hardware acceleration")
            except Exception as e2:
                print(f"VA-API not available: {e2}")
                # Fallback to software encoding
                self.pipeline = Gst.parse_launch(
                    f"v4l2src device=/dev/video{camera_id} ! "
                    f"videoconvert ! "
                    f"video/x-raw,format=RGB,width=640,height=480,framerate=30/1 ! "
                    f"appsink name=sink emit-signals=true max-buffers=1 drop=true"
                )
                print("Using software encoding (no hardware acceleration)")
        
        self.appsink = self.pipeline.get_by_name('sink')
        self.appsink.connect('new-sample', self.on_new_sample)
        self.latest_frame = None
        # Add bus message handler for errors and state changes
        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect('message', self.on_bus_message)
        self.pipeline.set_state(Gst.State.PLAYING)

    def on_bus_message(self, bus, message):
        t = message.type
        if t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            print(f"GStreamer ERROR: {err}, debug info: {debug}")
        elif t == Gst.MessageType.STATE_CHANGED:
            old, new, pending = message.parse_state_changed()
            if message.src == self.pipeline:
                print(f"GStreamer pipeline state changed from {old.value_nick} to {new.value_nick}")
        elif t == Gst.MessageType.EOS:
            print("GStreamer End-Of-Stream reached")

    def on_new_sample(self, sink):
        sample = sink.emit('pull-sample')
        buf = sample.get_buffer()
        caps = sample.get_caps()
        arr = self.gst_buffer_to_ndarray(buf, caps)
        self.latest_frame = arr
        return Gst.FlowReturn.OK

    def gst_buffer_to_ndarray(self, buf, caps):
        # Get video info
        structure = caps.get_structure(0)
        width = structure.get_value('width')
        height = structure.get_value('height')
        # Map buffer and convert to numpy array
        success, map_info = buf.map(Gst.MapFlags.READ)
        if not success:
            return None
        try:
            array = np.frombuffer(map_info.data, dtype=np.uint8)
            array = array.reshape((height, width, 3))
            return array
        finally:
            buf.unmap(map_info)

    async def recv(self):
        start_time = time.time()
        try:
            self.frame_count += 1
            print(f"Sending frame {self.frame_count}")
            # Wait for a new frame
            for _ in range(10):
                if self.latest_frame is not None:
                    frame = self.latest_frame.copy()
                    self.latest_frame = None
                    break
                await asyncio.sleep(0.01)
            else:
                print("Failed to get frame from GStreamer, sending black frame")
                frame = np.zeros((480, 640, 3), dtype=np.uint8)

            # Add timestamp to the frame
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            # Use numpy for text if OpenCV is not available, or skip text
            # (GStreamer does not provide text overlay in numpy directly)
            # If you want text overlay, you can add 'textoverlay' element in the pipeline

            # Ensure frame is uint8
            frame = frame.astype(np.uint8)

            # Create video frame
            video_frame = VideoFrame.from_ndarray(frame, format="rgb24")
            video_frame.pts = self.frame_count
            video_frame.time_base = fractions.Fraction(1, 30)
            
            # Calculate and store timing
            processing_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            self.frame_times.append(processing_time)
            self.total_processing_time += processing_time
            
            # Print performance stats every 30 frames
            if self.frame_count % 30 == 0:
                avg_time = self.total_processing_time / self.frame_count
                recent_avg = sum(self.frame_times[-30:]) / min(30, len(self.frame_times))
                print(f"Performance: Avg={avg_time:.2f}ms, Recent={recent_avg:.2f}ms, Current={processing_time:.2f}ms")
            
            return video_frame
        except Exception as e:
            print(f"Error in recv: {str(e)}")
            black_frame = np.zeros((480, 640, 3), dtype=np.uint8)
            video_frame = VideoFrame.from_ndarray(black_frame, format="rgb24")
            video_frame.pts = self.frame_count
            video_frame.time_base = fractions.Fraction(1, 30)
            return video_frame

async def setup_webrtc_and_run(ip_address, port, camera_id):
    signaling = TcpSocketSignaling(ip_address, port)
    pc = RTCPeerConnection()
    video_sender = CustomVideoStreamTrack(camera_id)
    pc.addTrack(video_sender)

    try:
        await signaling.connect()

        @pc.on("datachannel")
        def on_datachannel(channel):
            print(f"Data channel established: {channel.label}")

        @pc.on("connectionstatechange")
        async def on_connectionstatechange():
            print(f"Connection state is {pc.connectionState}")
            if pc.connectionState == "connected":
                print("WebRTC connection established successfully")

        offer = await pc.createOffer()
        await pc.setLocalDescription(offer)
        await signaling.send(pc.localDescription)

        while True:
            obj = await signaling.receive()
            if isinstance(obj, RTCSessionDescription):
                await pc.setRemoteDescription(obj)
                print("Remote description set")
            elif obj is None:
                print("Signaling ended")
                break
        print("Closing connection")
    finally:
        await pc.close()

async def main():
    ip_address = "10.10.1.100" # Ip Address of Remote Server/Machine
    port = 9999
    camera_id = 0  # Change this to the appropriate camera ID
    await setup_webrtc_and_run(ip_address, port, camera_id)

if __name__ == "__main__":
    asyncio.run(main())