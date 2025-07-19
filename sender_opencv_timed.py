import asyncio
import cv2
import numpy as np
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from aiortc.contrib.signaling import TcpSocketSignaling
from av import VideoFrame
import fractions
from datetime import datetime
import time

class CustomVideoStreamTrack(VideoStreamTrack):
    def __init__(self, camera_id):
        super().__init__()
        self.cap = cv2.VideoCapture(camera_id)
        self.frame_count = 0
        self.total_processing_time = 0
        self.frame_times = []

    async def recv(self):
        start_time = time.time()
        try:
            self.frame_count += 1
            print(f"Sending frame {self.frame_count}")
            ret, frame = self.cap.read()
            if not ret:
                print("Failed to read frame from camera")
                # Return a black frame instead of None to keep the stream alive
                black_frame = np.zeros((480, 640, 3), dtype=np.uint8)
                video_frame = VideoFrame.from_ndarray(black_frame, format="rgb24")
                video_frame.pts = self.frame_count
                video_frame.time_base = fractions.Fraction(1, 30)
                return video_frame
            
            # Convert BGR to RGB
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Add timestamp to the frame
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            cv2.putText(frame, timestamp, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)
            
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
                print(f"OpenCV Performance: Avg={avg_time:.2f}ms, Recent={recent_avg:.2f}ms, Current={processing_time:.2f}ms")
            
            return video_frame
            
        except Exception as e:
            print(f"Error in recv: {str(e)}")
            # Return a black frame to keep the stream alive
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