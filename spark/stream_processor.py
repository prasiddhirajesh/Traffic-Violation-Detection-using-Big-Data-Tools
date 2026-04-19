import sys
import os

# Add parent directory to sys.path so 'core' module can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Force Spark workers to use the exact same Python binary as this script (the venv)
os.environ['PYSPARK_PYTHON'] = sys.executable
os.environ['PYSPARK_DRIVER_PYTHON'] = sys.executable

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json
from pyspark.sql.types import StructType, StructField, StringType, DoubleType

def create_spark_session():
    return SparkSession.builder \
        .appName("BigDataTrafficDetection") \
        .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0") \
        .config("spark.sql.shuffle.partitions", "2") \
        .getOrCreate()


def process_batch(batch_df, batch_id):
    """
    Process each micro-batch entirely inside pure Python.
    This avoids the PySpark Python UDF IPC socket entirely, 
    which is what was crashing on Windows.
    """
    # Lazy imports so they only happen in the driver process
    from core.detector import process_frame

    rows = batch_df.collect()
    if not rows:
        return

    all_violations = []
    for row in rows:
        cam_id = row["camera_id"]
        frame_data = row["frame_data"]
        timestamp = row["timestamp"]
        light = row["light"] if row["light"] else "Green"  # Default to Green if missing

        try:
            # Apply traffic light state to the per-camera processor
            # (This replaces pressing 'R' in the original GUI)
            from core.detector import processor_cache, process_frame
            from processor.MainProcessor import MainProcessor
            
            if cam_id not in processor_cache:
                processor_cache[cam_id] = MainProcessor(cam_id)
            processor_cache[cam_id].setLight(light)
            
            violations = process_frame(cam_id, frame_data, timestamp)
            all_violations.extend(violations)
        except Exception as e:
            print(f"[ERROR] Failed to process frame for cam {cam_id}: {e}")

    if all_violations:
        print(f"\n{'='*60}")
        print(f"  Batch {batch_id} — {len(all_violations)} VIOLATION(S) DETECTED!")
        print(f"{'='*60}")
        for v in all_violations:
            plate = v.get('license_plate') or 'N/A'
            print(f"  Camera : {v['camera_id']}")
            print(f"  Time   : {v['timestamp']}")
            print(f"  Type   : {v['violation_type']}")
            print(f"  Plate  : {plate}")
            print(f"  Snapshot: [base64 image, length={len(v.get('car_snapshot_base64', ''))}]")
            print(f"  {'-'*56}")

        # --- Save to MongoDB (optional) ---
        # Wrapped in its own try-except so MongoDB being down NEVER crashes the stream.
        try:
            from pymongo import MongoClient
            import datetime

            client = MongoClient("mongodb://localhost:27018/", serverSelectionTimeoutMS=2000)
            db = client["traffic_db"]
            collection = db["violations"]

            docs = []
            for v in all_violations:
                docs.append({
                    "camera_id":      v["camera_id"],
                    "violation_type": v["violation_type"],
                    "timestamp":      v["timestamp"],
                    "detected_at":    datetime.datetime.utcnow().isoformat(),
                    "snapshot_size":  len(v.get("car_snapshot_base64", "")),
                    "car_snapshot_base64": v.get("car_snapshot_base64", ""),
                    "license_plate":  v.get("license_plate"),
                })
            collection.insert_many(docs)
            print(f"  [MongoDB] Saved {len(docs)} violation(s) to traffic_db.violations ✓")
            client.close()
        except Exception as mongo_err:
            # MongoDB not running or pymongo not installed — just skip silently
            print(f"  [MongoDB] Skipped (not available): {mongo_err}")
    else:
        print(f"[Batch {batch_id}] Processed {len(rows)} frame(s) — no violations detected.")


def run_stream():
    spark = create_spark_session()
    spark.sparkContext.setLogLevel("ERROR")

    # 1. Define JSON schema (now includes optional 'light' field)
    schema = StructType([
        StructField("camera_id", StringType(), True),
        StructField("timestamp", DoubleType(), True),
        StructField("frame_data", StringType(), True),
        StructField("light", StringType(), True)
    ])

    print("\n" + "="*60)
    print("  Connecting to Kafka topic 'traffic-stream'...")
    print("="*60 + "\n")

    # 2. Read Stream from Kafka with a limited batch size
    df = spark \
        .readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", "localhost:9092") \
        .option("subscribe", "traffic-stream") \
        .option("startingOffsets", "latest") \
        .option("maxOffsetsPerTrigger", 10) \
        .load()

    # 3. Parse JSON
    parsed_df = df.selectExpr("CAST(value AS STRING)") \
        .select(from_json(col("value"), schema).alias("data")) \
        .select("data.*")

    print("="*60)
    print("  Spark Structured Streaming started!")
    print("  Start your video producer in another terminal.")
    print("  Results will appear below as violations are detected.")
    print("="*60 + "\n")

    # 4. Use foreachBatch — runs pure Python, NO JVM-Python UDF IPC socket
    query = parsed_df.writeStream \
        .foreachBatch(process_batch) \
        .outputMode("append") \
        .option("checkpointLocation", os.path.join(
            r"c:\Users\HP\OneDrive\Desktop\Big Data Project\Traffic-Rules-Violation-Detection",
            "spark_checkpoints",
            str(int(os.environ.get('SPARK_RUN_ID', __import__('time').time())))
        )) \
        .start()

    query.awaitTermination()


if __name__ == "__main__":
    run_stream()
