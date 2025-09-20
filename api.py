# api_server.py

from flask import Flask, request, jsonify

app = Flask(__name__)
tasks = []

@app.route("/xuz/", methods=["GET"])
def get_tasks():
    if tasks:
        return jsonify({"success": True, "added": tasks.pop(0)})
    return jsonify({"success": False, "added": None})

@app.route("/xuz/Mroffline/", methods=["GET"])
def add_task():
    ip = request.args.get("ip")
    port = request.args.get("port")
    time_val = request.args.get("time")
    if ip and port and time_val:
        tasks.append({"ip": ip, "port": port, "time": time_val})
        return jsonify({"success": True, "task": tasks[-1]})
    return jsonify({"success": False, "error": "Missing ip, port or time"}), 400

@app.route("/xuz/done", methods=["GET"])
def mark_done():
    ip = request.args.get("ip")
    port = request.args.get("port")
    time_val = request.args.get("time")
    # remove matching task(s)
    global tasks
    tasks = [t for t in tasks if not (t["ip"] == ip and str(t["port"]) == str(port) and str(t["time"]) == str(time_val))]
    return jsonify({"success": True})

if __name__ == "__main__":
    # Use port 8080 so no root needed
    app.run(host="0.0.0.0", port=8080)
