import cv2
import json
import base64
import time
import argparse
import sys
from kafka import KafkaProducer

def get_producer(bootstrap_servers):
    try:
        return KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None
        )
    except Exception as e:
        print(f"Failed to connect to Kafka: {e}")
        sys.exit(1)

def stream_camera(cam_id, video_source, broker, light='green'):
    print(f"  Traffic light set to: {light.upper()} — {'violations ENABLED' if light == 'red' else 'no violations'}")
    print(f"Starting stream for {cam_id} using source: {video_source}")
    producer = get_producer(broker)
    cap = cv2.VideoCapture(video_source)
    
    if not cap.isOpened():
        print(f"Error: Could not open video source {video_source}")
        return

    frame_count = 0
    try:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                # Loop video for demonstration purposes
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue
                
            # Resize to save bandwidth (640x480 is sufficient for detection)
            frame = cv2.resize(frame, (640, 480))
            
            # Encode frame to JPEG, then Base64
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            base64_frame = base64.b64encode(buffer).decode('utf-8')
            
            payload = {
                "camera_id": cam_id,
                "timestamp": time.time(),
                "frame_data": base64_frame,
                "light": light.capitalize()  # "Green" or "Red"
            }
            
            # Key guarantees frames from same camera go to same partition
            producer.send('traffic-stream', key=cam_id, value=payload)
            
            frame_count += 1
            if frame_count % 30 == 0:
                print(f"[{cam_id}] Sent {frame_count} frames to Kafka...")
                
            # Simulate real-time FPS
            time.sleep(0.04)
            
    except KeyboardInterrupt:
        print("\nStopping stream...")
    finally:
        cap.release()
        producer.flush()
        producer.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Traffic Camera Kafka Producer')
    parser.add_argument('--cam', required=True, help='Camera ID (e.g., cam_01)')
    parser.add_argument('--video', required=True, help='Path to video file or RTSP stream')
    parser.add_argument('--broker', default='localhost:9092', help='Kafka bootstrap server')
    parser.add_argument('--light', default='green', choices=['green', 'red'],
                        help='Traffic light: green (no violations) or red (triggers violations)')
    
    args = parser.parse_args()
    stream_camera(args.cam, args.video, [args.broker], args.light)
