#!/usr/bin/env python3

import sys
import os

# Set Qt platform to wayland if running on Wayland
if "WAYLAND_DISPLAY" in os.environ:
    os.environ["QT_QPA_PLATFORM"] = "wayland"

from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QPainter, QColor

class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Qt5 Test Window")
        self.setGeometry(100, 100, 400, 300)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create test label
        test_label = QLabel("Qt5 is working! This is a test window.")
        test_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        test_label.setStyleSheet("font-size: 16px; color: blue;")
        layout.addWidget(test_label)
        
        # Create a simple colored rectangle
        pixmap = QPixmap(200, 100)
        painter = QPainter(pixmap)
        painter.fillRect(0, 0, 200, 100, QColor(255, 0, 0))  # Red rectangle
        painter.end()
        
        image_label = QLabel()
        image_label.setPixmap(pixmap)
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(image_label)

def main():
    app = QApplication(sys.argv)
    
    window = TestWindow()
    window.show()
    
    print("Qt5 test window should be visible now.")
    print("If you can see a window with text and a red rectangle, Qt5 is working!")
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main() 