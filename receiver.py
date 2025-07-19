import asyncio
import numpy as np
import os
from aiortc import RTCPeerConnection, RTCSessionDescription, MediaStreamTrack
from aiortc.contrib.signaling import TcpSocketSignaling
from av import VideoFrame
from datetime import datetime, timedelta
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget
from PyQt5.QtCore import QTimer, QThread, pyqtSignal, Qt
from PyQt5.QtGui import QImage, QPixmap
import threading

class VideoDisplayThread(QThread):
    frame_received = pyqtSignal(np.ndarray)
    
    def __init__(self):
        super().__init__()
        self.frame_queue = asyncio.Queue()
        self.running = True
    
    def add_frame(self, frame):
        self.frame_received.emit(frame)
    
    def stop(self):
        self.running = False

class VideoWindow(QMainWindow):
    frame_update_signal = pyqtSignal(np.ndarray)
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("WebRTC Video Receiver")
        self.setGeometry(100, 100, 800, 600)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create video display label
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setMinimumSize(640, 480)
        self.video_label.setStyleSheet("border: 2px solid gray; background-color: black;")
        layout.addWidget(self.video_label)
        
        # Create status label
        self.status_label = QLabel("Waiting for video stream...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        self.frame_count = 0
        
        # Connect signal to slot
        self.frame_update_signal.connect(self.update_frame_slot)
    
    def update_frame_slot(self, frame):
        """Update the video display with a new frame (called from main thread)"""
        try:
            # Convert BGR to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Get frame dimensions
            height, width, channel = rgb_frame.shape
            bytes_per_line = 3 * width
            
            # Create QImage from numpy array
            q_image = QImage(rgb_frame.data, width, height, bytes_per_line, QImage.Format_RGB888)
            
            # Scale image to fit the label while maintaining aspect ratio
            pixmap = QPixmap.fromImage(q_image)
            scaled_pixmap = pixmap.scaled(self.video_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            
            # Update the label
            self.video_label.setPixmap(scaled_pixmap)
            
            self.frame_count += 1
            self.status_label.setText(f"Frame {self.frame_count} - {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
            
        except Exception as e:
            print(f"Error updating frame: {str(e)}")
    
    def update_frame(self, frame):
        """Emit signal to update frame from any thread"""
        self.frame_update_signal.emit(frame)

class VideoReceiver:
    def __init__(self, video_window):
        self.track = None
        self.video_window = video_window
        self.running = True
    
    def stop(self):
        """Stop the video receiver"""
        self.running = False
        if self.track:
            self.track.stop()

    async def handle_track(self, track):
        print("Inside handle track")
        self.track = track
        frame_count = 0
        consecutive_errors = 0
        max_consecutive_errors = 10
        
        while self.running:
            try:
                print("Waiting for frame...")
                frame = await asyncio.wait_for(track.recv(), timeout=5.0)
                
                if frame is None:
                    print("Received None frame, continuing...")
                    consecutive_errors += 1
                    if consecutive_errors >= max_consecutive_errors:
                        print("Too many consecutive None frames, exiting...")
                        break
                    continue
                
                frame_count += 1
                consecutive_errors = 0  # Reset error counter on successful frame
                print(f"Received frame {frame_count}")
                
                if isinstance(frame, VideoFrame):
                    print(f"Frame type: VideoFrame, pts: {frame.pts}, time_base: {frame.time_base}")
                    frame = frame.to_ndarray(format="bgr24")
                elif isinstance(frame, np.ndarray):
                    print(f"Frame type: numpy array")
                else:
                    print(f"Unexpected frame type: {type(frame)}")
                    consecutive_errors += 1
                    if consecutive_errors >= max_consecutive_errors:
                        print("Too many unexpected frame types, exiting...")
                        break
                    continue
              
                # Add timestamp to the frame
                current_time = datetime.now()
                new_time = current_time - timedelta(seconds=55)
                timestamp = new_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                cv2.putText(frame, timestamp, (10, frame.shape[0] - 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)
                
                # Save frame to file
                cv2.imwrite(f"imgs/received_frame_{frame_count}.jpg", frame)
                print(f"Saved frame {frame_count} to file")
                
                # Update Qt window with new frame
                self.video_window.update_frame(frame)
    
            except asyncio.TimeoutError:
                print("Timeout waiting for frame, continuing...")
                consecutive_errors += 1
                if consecutive_errors >= max_consecutive_errors:
                    print("Too many timeouts, exiting...")
                    break
            except ConnectionError as e:
                print(f"Connection error in handle_track: {str(e)}")
                break
            except Exception as e:
                print(f"Error in handle_track: {str(e)}")
                consecutive_errors += 1
                if consecutive_errors >= max_consecutive_errors:
                    print("Too many consecutive errors, exiting...")
                    break
                if "Connection" in str(e) or "closed" in str(e).lower():
                    print("Connection appears to be closed, exiting...")
                    break
        print("Exiting handle_track")

async def run(pc, signaling, video_window):
    await signaling.connect()

    @pc.on("track")
    def on_track(track):
        if isinstance(track, MediaStreamTrack):
            print(f"Receiving {track.kind} track")
            asyncio.ensure_future(video_receiver.handle_track(track))

    @pc.on("datachannel")
    def on_datachannel(channel):
        print(f"Data channel established: {channel.label}")

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        print(f"Connection state is {pc.connectionState}")
        if pc.connectionState == "connected":
            print("WebRTC connection established successfully")
        elif pc.connectionState == "failed" or pc.connectionState == "closed":
            print(f"WebRTC connection {pc.connectionState}, stopping receiver...")
            # Signal to stop the video receiver
            if hasattr(video_receiver, 'track') and video_receiver.track:
                video_receiver.track.stop()

    print("Waiting for offer from sender...")
    offer = await signaling.receive()
    print("Offer received")
    await pc.setRemoteDescription(offer)
    print("Remote description set")

    answer = await pc.createAnswer()
    print("Answer created")
    await pc.setLocalDescription(answer)
    print("Local description set")

    await signaling.send(pc.localDescription)
    print("Answer sent to sender")

    print("Waiting for connection to be established...")
    while pc.connectionState != "connected":
        await asyncio.sleep(0.1)

    print("Connection established, waiting for frames...")
    
    # Wait for connection to end or timeout
    try:
        while pc.connectionState == "connected":
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("Received keyboard interrupt, shutting down...")
    finally:
        print("Closing connection")

def run_webrtc_async(video_window):
    """Run the WebRTC receiver in a separate thread"""
    async def async_main():
        signaling = TcpSocketSignaling("10.10.1.100", 9999)
        pc = RTCPeerConnection()
        
        global video_receiver
        video_receiver = VideoReceiver(video_window)

        try:
            await run(pc, signaling, video_window)
        except Exception as e:
            print(f"Error in main: {str(e)}")
        finally:
            print("Closing peer connection")
            await pc.close()
    
    asyncio.run(async_main())

async def main():
    # Set Qt platform to wayland if running on Wayland
    if "WAYLAND_DISPLAY" in os.environ:
        os.environ["QT_QPA_PLATFORM"] = "wayland"
    
    # Create Qt application
    app = QApplication(sys.argv)
    
    # Create video window
    video_window = VideoWindow()
    video_window.show()
    
    # Start WebRTC receiver in a separate thread
    webrtc_thread = threading.Thread(target=run_webrtc_async, args=(video_window,))
    webrtc_thread.daemon = True
    webrtc_thread.start()
    
    # Start Qt event loop
    sys.exit(app.exec_())

if __name__ == "__main__":
    # Import cv2 here since we still need it for timestamp overlay
    import cv2
    
    asyncio.run(main())