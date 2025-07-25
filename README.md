# webrtc-python
 webrtc with python for proof of concept

## Prerequisites

```sh
python -m venv venv
source venv/bin/activate
```

```sh 
sudo dnf install -y python3-pip python3-devel gcc gcc-c++ make
sudo dnf install -y qt5-devel qt5-qtbase-devel qt5-qtbase-gui
sudo dnf install -y opencv-devel ffmpeg-devel

sudo dnf install -y gstreamer1-devel gstreamer1-plugins-base-devel gstreamer1-plugins-good gstreamer1-plugins-bad-free gstreamer1-plugins-ugly-free gstreamer1-libav gstreamer1-plugins-base gstreamer1-plugins-good-extras gstreamer1-plugins-bad-free-extras gstreamer1-plugins-ugly-free-extras gstreamer1-plugins-ffmpeg v4l-utils python3-gobject python3-gobject-devel python3-pip python3-devel gcc gcc-c++ make

sudo dnf install gobject-introspection-devel cairo-devel pkg-config python3-devel

pip install gbulb

pip install aiortc opencv-python
pip install matplotlib aiortc av numpy PyQt5 opencv-python 
pip install aiortc av numpy PyGObject Pillow 
```

## Testing camera 

```sh
gst-launch-1.0 --version

gst-launch-1.0 v4l2src device=/dev/video0 ! videoconvert ! autovideosink
``` 

## How It Works

This project demonstrates real-time video streaming using WebRTC in Python, with a sender and a receiver script.

### Sender (`sender.py`)
- Captures video frames from your webcam using OpenCV (`cv2.VideoCapture`).
- Streams the video frames over a WebRTC connection using the `aiortc` library.
- The sender connects to the receiver using TCP socket signaling (IP and port must match on both sides).
- Each frame is timestamped and sent to the receiver.

### Receiver (`receiver.py`)
- Listens for a WebRTC connection from the sender using the same IP and port.
- Receives video frames via WebRTC and decodes them.
- Each received frame is saved as an image in the `imgs/` directory.
- Frames are displayed using `matplotlib` (a window will pop up for each frame). This is more compatible with headless or SSH environments than OpenCV's `imshow`.
- If you do not see a display window, ensure you have a GUI environment or X11 forwarding enabled, and that `matplotlib` is installed (`pip install matplotlib`).

### Requirements
- Python 3.7+
- OpenCV (`pip install opencv-python`)
- aiortc (`pip install aiortc`)
- av (`pip install av`)
- numpy (`pip install numpy`)
- matplotlib (`pip install matplotlib`)

### Usage
1. Start the receiver first:
   ```bash
   python receiver.py
   ```
2. Then start the sender:
   ```bash
   python sender.py
   ```
3. The sender will turn on your webcam and start sending frames. The receiver will display each frame in a matplotlib window and save them as images.

### Notes
- Make sure the IP address and port match in both scripts.
- If running both scripts on the same machine, you can use `127.0.0.1` as the IP address.
- If you want to use a different camera, change the `camera_id` in `sender.py` (default is `0`).

## Performance Comparison

### Latency Results

Based on testing on an Intel Core i5-7600K system:

- **GStreamer (software encoding)**: ~57ms average frame processing time
- **OpenCV**: ~75ms average frame processing time
- **GStreamer advantage**: 24% faster than OpenCV even without hardware acceleration

### Hardware Acceleration Status

The current implementation falls back to software encoding due to missing Intel Quick Sync and VA-API plugins. While hardware acceleration would provide additional performance benefits, the software pipeline already demonstrates superior performance compared to OpenCV.

### Performance Notes

- Both implementations achieve real-time performance (<100ms per frame)
- GStreamer's optimized pipeline architecture provides better performance even without hardware acceleration
- Frame processing includes WebRTC encoding overhead
- Performance may vary based on system specifications and network conditions

## Sources

* https://medium.com/@malieknath135/building-a-real-time-streaming-application-using-webrtc-in-python-d34694604fc4
* https://gist.github.com/velovix/8cbb9bb7fe86a08fb5aa7909b2950259

## Important Note for GStreamer Usage

When using GStreamer with Python (PyGObject), you **must** start a `GLib.MainLoop` in its own thread. This is required for GStreamer to process signals and events, such as delivering frames to your application. Without this, your pipeline may not emit frames or work correctly.

Example:

```python
import threading
from gi.repository import GLib

main_loop = GLib.MainLoop()
main_loop_thread = threading.Thread(target=main_loop.run, daemon=True)
main_loop_thread.start()
```

Make sure to start this main loop before creating and running your GStreamer pipeline.
