import base64
import cv2
import numpy as np
from processor.MainProcessor import MainProcessor
from core.plate_reader import extract_plate

# Prevent OpenCV from spawning UI threads or competing with Spark for CPUs
cv2.setNumThreads(0)

# Memory cache for stateful processors per Spark Partition
processor_cache = {}

def decode_frame(base64_string):
    img_data = base64.b64decode(base64_string)
    np_arr = np.frombuffer(img_data, np.uint8)
    return cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

def encode_frame(frame):
    _, buffer = cv2.imencode('.jpg', frame)
    return base64.b64encode(buffer).decode('utf-8')

def process_frame(cam_id, base64_frame, timestamp):
    """
    Headless violation detection logic meant to be run inside Spark Executors.
    """
    import os
    trace_file = os.path.join(r"c:\Users\HP\OneDrive\Desktop\Big Data Project\Traffic-Rules-Violation-Detection", "pyspark_trace.txt")
    
    def trace(msg):
        with open(trace_file, 'a') as f:
            f.write(msg + '\n')
            
    try:
        trace(f"--- INIT FRAME for {cam_id} ---")
        if cam_id not in processor_cache:
            trace(f"Cache miss. Creating MainProcessor for {cam_id}...")
            processor_cache[cam_id] = MainProcessor(cam_id)
            trace(f"Created MainProcessor for {cam_id}.")
            
        trace("Decoding frame...")
        frame = decode_frame(base64_frame)
        trace("Frame decoded.")
        
        if frame is None or frame.size == 0:
            trace("Frame is None or empty. Returning []")
            return []
            
        processor = processor_cache[cam_id]
    
        trace("Running OpenCV logic...")
        results = processor.getProcessedImage(frame)
        trace("OpenCV logic done.")
        
        violations = []
        if len(results['list_of_cars']) > 0:
            for car_img in results['list_of_cars']:
                if car_img is None or car_img.size == 0 or len(car_img.shape) < 2 or car_img.shape[0] == 0 or car_img.shape[1] == 0:
                    continue
                    
                car_encoded = encode_frame(car_img)
                
                # Attempt license plate extraction from the cropped vehicle image
                plate_text = extract_plate(car_img)
                trace(f"Plate OCR result: {plate_text}")
                
                violations.append({
                    "camera_id": cam_id,
                    "timestamp": float(timestamp),
                    "violation_type": "Wrong Direction" if cam_id == "cam_04" else "Red Light Crossing",
                    "car_snapshot_base64": car_encoded,
                    "license_plate": plate_text
                })
                
        trace(f"Returning {len(violations)} violations.")
        return violations
    except Exception as e:
        import traceback
        trace(f"Worker Error for {cam_id}: {str(e)}\n{traceback.format_exc()}")
        return []
