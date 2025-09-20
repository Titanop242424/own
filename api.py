# api_server.py
from flask import Flask, request, jsonify
from waitress import serve

app = Flask(__name__)
tasks = []

@app.route("/xuz/", methods=["GET"])
def get_tasks():
    if tasks:
        return jsonify({"success": True, "added": tasks.pop(0)})
    return jsonify({"success": False})

@app.route("/xuz/Mroffline/", methods=["GET"])
def add_task():
    ip = request.args.get("ip")
    port = request.args.get("port")
    time = request.args.get("time")
    if ip and port and time:
        tasks.append({"ip": ip, "port": port, "time": time})
        return jsonify({"success": True})
    return jsonify({"success": False})

@app.route("/xuz/done", methods=["GET"])
def mark_done():
    return jsonify({"success": True})

if __name__ == "__main__":
    serve(app, host="0.0.0.0", port=80)
