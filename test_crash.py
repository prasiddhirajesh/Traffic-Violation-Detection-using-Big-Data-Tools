import os
import sys

# Force run from root directory
sys.path.append(os.path.abspath('.'))

import cv2
import numpy as np
from core.detector import encode_frame, process_frame

print("Generating synthetic frame...")
frame = np.zeros((480, 640, 3), dtype=np.uint8)
base64_frame = encode_frame(frame)

print("Testing cam_01 processor...")
res1 = process_frame("cam_01", base64_frame, "2023-01-01 12:00:00")
print("cam_01 result:", res1)

print("Testing cam_04 processor...")
try:
    res4 = process_frame("cam_04", base64_frame, "2023-01-01 12:00:00")
    print("cam_04 result:", res4)
except Exception as e:
    print("cam_04 failed:", e)

print("Done! No Segfault.")
