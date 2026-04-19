import base64
import time
import cv2
import sys

def main():
    print("Opening video...")
    cap = cv2.VideoCapture(r"c:\Users\HP\OneDrive\Desktop\Big Data Project\Traffic-Rules-Violation-Detection\videos\video7.mp4")
    if not cap.isOpened():
        print("Failed to open video")
        return
        
    ret, frame = cap.read()
    if not ret:
        print("Failed to read frame")
        return
        
    frame = cv2.resize(frame, (640, 480))
    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
    base64_frame = base64.b64encode(buffer).decode('utf-8')
    
    print("Importing process_frame...")
    from core.detector import process_frame
    
    print("Calling process_frame...")
    try:
        res = process_frame('cam_01', base64_frame, time.time())
        print("Result length:", len(res))
    except Exception as e:
        import traceback
        traceback.print_exc()
        
    print("Finished successfully without Segfault!")

if __name__ == "__main__":
    main()
