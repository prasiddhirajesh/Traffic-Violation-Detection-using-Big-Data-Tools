from flask import Flask, render_template, jsonify, request, Response
from pymongo import MongoClient
from bson import ObjectId
import datetime
import json

app = Flask(__name__)

MONGO_URI = "mongodb://localhost:27018/"
DB_NAME = "traffic_db"
COLLECTION = "violations"


def get_collection():
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
    return client[DB_NAME][COLLECTION], client


def serialize(doc):
    """Convert MongoDB document to JSON-serializable dict."""
    doc["_id"] = str(doc["_id"])
    return doc


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/violations")
def get_violations():
    """Return all violations, newest first."""
    try:
        col, client = get_collection()
        limit = int(request.args.get("limit", 50))
        docs = list(col.find({}, {"car_snapshot_base64": 0})
                    .sort("detected_at", -1)
                    .limit(limit))
        client.close()
        return jsonify([serialize(d) for d in docs])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/violation/<vid>/image")
def get_image(vid):
    """Serve the car snapshot as a JPEG image."""
    try:
        import base64
        col, client = get_collection()
        doc = col.find_one({"_id": ObjectId(vid)}, {"car_snapshot_base64": 1})
        client.close()
        if doc and doc.get("car_snapshot_base64"):
            img_bytes = base64.b64decode(doc["car_snapshot_base64"])
            return Response(img_bytes, mimetype="image/jpeg")
        # Return a tiny grey placeholder if no image
        return Response(b"", mimetype="image/jpeg"), 204
    except Exception as e:
        return str(e), 500


@app.route("/api/violation/<vid>")
def get_violation(vid):
    """Return a single violation including its snapshot image."""
    try:
        col, client = get_collection()
        doc = col.find_one({"_id": ObjectId(vid)})
        client.close()
        if doc:
            return jsonify(serialize(doc))
        return jsonify({"error": "Not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/stats")
def get_stats():
    """Return summary statistics."""
    try:
        col, client = get_collection()
        total = col.count_documents({})
        red_light = col.count_documents({"violation_type": "Red Light Crossing"})
        wrong_dir = col.count_documents({"violation_type": "Wrong Direction"})
        cameras = col.distinct("camera_id")
        client.close()
        return jsonify({
            "total": total,
            "red_light": red_light,
            "wrong_direction": wrong_dir,
            "cameras_active": len(cameras)
        })
    except Exception as e:
        return jsonify({"error": str(e), "total": 0, "red_light": 0,
                        "wrong_direction": 0, "cameras_active": 0})


@app.route("/ticket/<vid>")
def ticket(vid):
    """Render a printable violation ticket."""
    try:
        col, client = get_collection()
        doc = col.find_one({"_id": ObjectId(vid)})
        client.close()
        if doc:
            doc["_id"] = str(doc["_id"])
            return render_template("ticket.html", v=doc)
        return "Violation not found", 404
    except Exception as e:
        return str(e), 500


if __name__ == "__main__":
    print("\n" + "="*55)
    print("  Traffic Violation Dashboard")
    print("  Open: http://localhost:5000")
    print("="*55 + "\n")
    app.run(debug=False, port=5000, host="0.0.0.0")
