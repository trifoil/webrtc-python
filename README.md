# webrtc-python
 wertc with python for proof of concept

```sh
python -m venv venv
source venv/bin/activate
```

```sh 
pip install aiortc opencv-python
pip install matplotlib
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

