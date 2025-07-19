import asyncio
import numpy as np
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from aiortc.contrib.signaling import TcpSocketSignaling
from av import VideoFrame
import fractions
from datetime import datetime
import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstVideo', '1.0')
from gi.repository import Gst, GstVideo, GLib
import threading
import queue
import time

class GStreamerVideoSource:
    def __init__(self, camera_id=0, width=640, height=480, fps=30):
        Gst.init(None)
        self.camera_id = camera_id
        self.width = width
        self.height = height
        self.fps = fps
        self.frame_queue = queue.Queue(maxsize=10)  # Buffer for 10 frames
        self.running = False
        self.thread = None
        
        # Create GStreamer pipeline
        self.pipeline_str = (
            f"v4l2src device=/dev/video{camera_id} ! "
            f"video/x-raw,width={width},height={height},framerate={fps}/1 ! "
            "videoconvert ! "
            "video/x-raw,format=RGB ! "
            "appsink name=sink sync=false max-buffers=1 drop=true"
        )
        
        self.pipeline = Gst.parse_launch(self.pipeline_str)
        self.sink = self.pipeline.get_by_name("sink")
        
        # Set up callbacks
        self.sink.connect("new-sample", self.on_new_sample, None)
        
    def on_new_sample(self, sink, data):
        """Callback when new frame is available"""
        try:
            sample = sink.emit("pull-sample")
            buffer = sample.get_buffer()
            caps = sample.get_caps()
            
            # Get video info
            video_info = GstVideo.VideoInfo()
            video_info.from_caps(caps)
            
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
                ).copy()  # Make a copy to avoid memory issues
                
                # Add timestamp overlay
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                self.add_text_overlay(frame_data, timestamp, 10, 30)
                
                # Put frame in queue (non-blocking)
                try:
                    self.frame_queue.put_nowait(frame_data)
                except queue.Full:
                    # Drop oldest frame if queue is full
                    try:
                        self.frame_queue.get_nowait()
                        self.frame_queue.put_nowait(frame_data)
                    except queue.Empty:
                        pass
                        
            finally:
                buffer.unmap(map_info)
                
        except Exception as e:
            print(f"Error in on_new_sample: {e}")
            
        return Gst.FlowReturn.OK
    
    def add_text_overlay(self, frame, text, x, y):
        """Add text overlay to frame using PIL for better performance"""
        try:
            from PIL import Image, ImageDraw, ImageFont
            # Convert numpy array to PIL Image
            pil_image = Image.fromarray(frame)
            draw = ImageDraw.Draw(pil_image)
            
            # Use default font
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
            except:
                font = ImageFont.load_default()
            
            # Draw text with green color
            draw.text((x, y), text, fill=(0, 255, 0), font=font)
            
            # Convert back to numpy array
            frame[:] = np.array(pil_image)
        except ImportError:
            # Fallback to simple pixel manipulation if PIL not available
            print("PIL not available, skipping text overlay")
        except Exception as e:
            print(f"Error adding text overlay: {e}")
    
    def start(self):
        """Start the GStreamer pipeline"""
        if self.running:
            return
            
        self.running = True
        self.pipeline.set_state(Gst.State.PLAYING)
        
        # Start monitoring thread
        self.thread = threading.Thread(target=self._monitor_pipeline)
        self.thread.daemon = True
        self.thread.start()
        
        print(f"GStreamer pipeline started with camera {self.camera_id}")
    
    def stop(self):
        """Stop the GStreamer pipeline"""
        self.running = False
        if self.pipeline:
            self.pipeline.set_state(Gst.State.NULL)
        if self.thread:
            self.thread.join(timeout=1)
    
    def _monitor_pipeline(self):
        """Monitor pipeline state and handle errors"""
        loop = GLib.MainLoop()
        
        def on_bus_message(bus, message):
            msg_type = message.type
            if msg_type == Gst.MessageType.ERROR:
                err, debug = message.parse_error()
                print(f"GStreamer error: {err}, {debug}")
                loop.quit()
            elif msg_type == Gst.MessageType.EOS:
                print("GStreamer EOS")
                loop.quit()
            return True
        
        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message", on_bus_message)
        
        while self.running:
            try:
                loop.run()
                break
            except Exception as e:
                print(f"Pipeline monitoring error: {e}")
                break
    
    def get_frame(self, timeout=0.1):
        """Get the latest frame from the queue"""
        try:
            return self.frame_queue.get(timeout=timeout)
        except queue.Empty:
            return None

class GStreamerVideoStreamTrack(VideoStreamTrack):
    def __init__(self, camera_id=0, width=640, height=480, fps=30):
        super().__init__()
        self.video_source = GStreamerVideoSource(camera_id, width, height, fps)
        self.frame_count = 0
        self.video_source.start()
        
    async def recv(self):
        try:
            self.frame_count += 1
            print(f"Sending frame {self.frame_count}")
            
            # Get frame from GStreamer
            frame = self.video_source.get_frame(timeout=0.1)
            
            if frame is None:
                print("No frame available from GStreamer")
                # Return a black frame to keep the stream alive
                black_frame = np.zeros((self.video_source.height, self.video_source.width, 3), dtype=np.uint8)
                video_frame = VideoFrame.from_ndarray(black_frame, format="rgb24")
                video_frame.pts = self.frame_count
                video_frame.time_base = fractions.Fraction(1, self.video_source.fps)
                return video_frame
            
            # Create video frame
            video_frame = VideoFrame.from_ndarray(frame, format="rgb24")
            video_frame.pts = self.frame_count
            video_frame.time_base = fractions.Fraction(1, self.video_source.fps)
            return video_frame
            
        except Exception as e:
            print(f"Error in recv: {str(e)}")
            # Return a black frame to keep the stream alive
            black_frame = np.zeros((self.video_source.height, self.video_source.width, 3), dtype=np.uint8)
            video_frame = VideoFrame.from_ndarray(black_frame, format="rgb24")
            video_frame.pts = self.frame_count
            video_frame.time_base = fractions.Fraction(1, self.video_source.fps)
            return video_frame
    
    def stop(self):
        """Stop the video source"""
        self.video_source.stop()

async def setup_webrtc_and_run(ip_address, port, camera_id=0, width=640, height=480, fps=30):
    signaling = TcpSocketSignaling(ip_address, port)
    pc = RTCPeerConnection()
    video_sender = GStreamerVideoStreamTrack(camera_id, width, height, fps)
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
            elif pc.connectionState == "failed" or pc.connectionState == "closed":
                print(f"WebRTC connection {pc.connectionState}, stopping video source...")
                video_sender.stop()

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
        video_sender.stop()
        await pc.close()

async def main():
    ip_address = "10.10.1.100"  # IP Address of Remote Server/Machine
    port = 9999
    camera_id = 1  # Change this to the appropriate camera ID
    width = 640
    height = 480
    fps = 30
    
    print(f"Starting GStreamer-based WebRTC sender")
    print(f"Camera: {camera_id}, Resolution: {width}x{height}, FPS: {fps}")
    
    await setup_webrtc_and_run(ip_address, port, camera_id, width, height, fps)

if __name__ == "__main__":
    asyncio.run(main()) 