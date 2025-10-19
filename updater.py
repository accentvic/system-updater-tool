#!/usr/bin/env python3
import subprocess
import datetime
import platform
import os
import sys
from pathlib import Path

def is_windows():
    """Check if running on Windows"""
    return platform.system() == "Windows"

def show_notification(title, message, urgency="normal"):
    """Show desktop notification (cross-platform)"""
    try:
        if is_windows():
            # Windows notification using powershell
            ps_script = f'''
            Add-Type -AssemblyName System.Windows.Forms
            $global:balloon = New-Object System.Windows.Forms.NotifyIcon
            $balloon.Icon = [System.Drawing.SystemIcons]::Information
            $balloon.BalloonTipIcon = "Info"
            $balloon.BalloonTipText = "{message}"
            $balloon.BalloonTipTitle = "{title}"
            $balloon.Visible = $true
            $balloon.ShowBalloonTip(30000)
            '''
            subprocess.run(['powershell', '-Command', ps_script], check=False)
        else:
            # Linux notification
            subprocess.run([
                'notify-send', 
                '-u', urgency,
                '-t', '30000',  # 30 seconds
                title, 
                message
            ], check=False)
    except Exception as e:
        print(f"Notification failed: {e}")

def get_user_input(prompt):
    """Get user input safely"""
    try:
        return input(prompt).strip().lower()
    except (KeyboardInterrupt, EOFError):
        print("\nOperation cancelled by user.")
        sys.exit(0)

def run_command(cmd, use_sudo=False):
    """Run command with platform-specific handling"""
    if is_windows():
        # Remove sudo from commands on Windows
        if use_sudo and cmd[0] == 'sudo':
            cmd = cmd[1:]
        # Use PowerShell for Windows commands
        if cmd[0] in ['apt', 'snap']:
            return None, "Package manager not available on Windows", 1
    else:
        # Linux commands - don't auto-sudo for safety
        if use_sudo and os.geteuid() != 0 and cmd[0] != 'sudo':
            cmd = ['sudo'] + cmd
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        return result.stdout, result.stderr, result.returncode
    except Exception as e:
        return None, str(e), 1

def log_message(message):
    """Save messages to a log file"""
    log_dir = Path.home() / "scripts" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / "updater.log"
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    with open(log_file, "a", encoding='utf-8') as f:
        f.write(f"[{timestamp}] {message}\n")
    
    print(f"📝 {message}")

def check_windows_updates():
    """Check for Windows updates and notify user"""
    log_message("🔍 Checking for Windows updates...")
    show_notification("Windows Update", "Checking for available updates...", "low")
    
    # Check for Windows updates using PowerShell
    ps_script = '''
    $UpdateSession = New-Object -ComObject Microsoft.Update.Session
    $UpdateSearcher = $UpdateSession.CreateUpdateSearcher()
    
    try {
        $SearchResult = $UpdateSearcher.Search("IsInstalled=0")
        
        if ($SearchResult.Updates.Count -gt 0) {
            Write-Host "UPDATES_AVAILABLE:" $SearchResult.Updates.Count
            foreach ($Update in $SearchResult.Updates) {
                Write-Host "UPDATE:" $Update.Title
                Write-Host "SIZE:" ([math]::Round($Update.MaxDownloadSize/1MB, 2)) "MB"
                if ($Update.IsMandatory) { Write-Host "MANDATORY:true" }
            }
        } else {
            Write-Host "NO_UPDATES"
        }
    }
    catch {
        Write-Host "ERROR:" $_.Exception.Message
    }
    '''
    
    stdout, stderr, returncode = run_command(['powershell', '-Command', ps_script], use_sudo=False)
    
    if "UPDATES_AVAILABLE" in stdout:
        lines = stdout.strip().split('\n')
        update_count = int(lines[0].split("UPDATES_AVAILABLE:")[1].strip())
        
        # Parse update details
        updates = []
        current_update = {}
        for line in lines[1:]:
            if line.startswith("UPDATE:"):
                if current_update:
                    updates.append(current_update)
                current_update = {"title": line.replace("UPDATE:", "").strip()}
            elif line.startswith("SIZE:"):
                current_update["size"] = line.replace("SIZE:", "").strip()
            elif line.startswith("MANDATORY:"):
                current_update["mandatory"] = True
        
        if current_update:
            updates.append(current_update)
        
        log_message(f"📦 Found {update_count} Windows updates available")
        
        # Show detailed notification
        update_list = "\n".join([f"• {u['title'][:60]}..." for u in updates[:3]])
        if len(updates) > 3:
            update_list += f"\n• ... and {len(updates) - 3} more updates"
        
        message = f"{update_count} updates available!\n\n{update_list}\n\nOpen Windows Update to install."
        show_notification("📢 Updates Available", message, "critical")
        
        # Ask if user wants to open Windows Update
        print(f"\n🎯 Found {update_count} Windows updates!")
        for i, update in enumerate(updates[:5], 1):
            size_info = f" ({update.get('size', 'size unknown')})" if 'size' in update else ""
            mandatory = " 🔴 MANDATORY" if update.get('mandatory') else ""
            print(f"   {i}. {update['title'][:80]}...{size_info}{mandatory}")
        
        choice = get_user_input("\n🚀 Open Windows Update settings? (y/n): ")
        if choice in ['y', 'yes']:
            subprocess.run(['start', 'ms-settings:windowsupdate'], shell=True)
            log_message("✅ Opened Windows Update settings")
        
        return True
        
    elif "NO_UPDATES" in stdout:
        log_message("✅ Windows is up to date")
        show_notification("✅ System Updated", "Your system is already up to date!", "low")
        return True
    else:
        log_message("⚠️ Could not check Windows updates automatically")
        show_notification("⚠️ Update Check", "Could not check updates automatically. Check manually in Settings.", "normal")
        return False

def check_linux_updates():
    """Check for Linux updates and notify user"""
    log_message("🔍 Checking for Ubuntu updates...")
    show_notification("System Update", "Checking for available updates...", "low")
    
    # Update package lists (no sudo for safety)
    stdout, stderr, returncode = run_command(['apt', 'update'], use_sudo=False)
    
    if returncode != 0:
        error_msg = "Failed to update package lists - need sudo access"
        log_message(f"❌ {error_msg}")
        show_notification("Update Error", error_msg, "critical")
        return False
    
    # Check for upgradable packages
    stdout, stderr, returncode = run_command(['apt', 'list', '--upgradable'], use_sudo=False)
    
    upgradable_packages = []
    if returncode == 0 and stdout:
        for line in stdout.split('\n'):
            if line and not line.startswith('Listing'):
                parts = line.split('/')
                if len(parts) > 0:
                    upgradable_packages.append(parts[0])
    
    if not upgradable_packages:
        success_msg = "System is already up to date"
        log_message(f"✅ {success_msg}")
        show_notification("✅ System Updated", success_msg, "low")
        return True
    
    # Show updates available
    log_message(f"📦 Found {len(upgradable_packages)} packages to update")
    
    # Categorize updates
    security_updates = [pkg for pkg in upgradable_packages if any(word in pkg.lower() for word in ['security', 'linux', 'kernel'])]
    other_updates = [pkg for pkg in upgradable_packages if pkg not in security_updates]
    
    # Create notification message
    message = f"{len(upgradable_packages)} updates available!\n"
    if security_updates:
        message += f"🔴 {len(security_updates)} security updates\n"
    if other_updates:
        message += f"🔵 {len(other_updates)} other updates\n"
    message += f"\nRun 'sudo apt upgrade' to install."
    
    show_notification("📢 Updates Available", message, "critical")
    
    # Show details to user
    print(f"\n🎯 Found {len(upgradable_packages)} updates available:")
    
    if security_updates:
        print(f"\n🔴 SECURITY UPDATES ({len(security_updates)}):")
        for pkg in security_updates[:5]:
            print(f"   • {pkg}")
        if len(security_updates) > 5:
            print(f"   • ... and {len(security_updates) - 5} more")
    
    if other_updates:
        print(f"\n🔵 OTHER UPDATES ({len(other_updates)}):")
        for pkg in other_updates[:3]:
            print(f"   • {pkg}")
        if len(other_updates) > 3:
            print(f"   • ... and {len(other_updates) - 3} more")
    
    # Ask user if they want to install
    print(f"\n💡 To install these updates, run:")
    print(f"   sudo apt upgrade")
    
    choice = get_user_input("\n🚀 Show the exact command to run? (y/n): ")
    if choice in ['y', 'yes']:
        print(f"\n💻 Run this command in terminal:")
        print(f"   sudo apt upgrade")
        print(f"\n🔍 Or to see what will be updated:")
        print(f"   apt list --upgradable")
    
    return True

def check_and_update_system():
    """Check for updates based on platform (NOTIFY ONLY)"""
    if is_windows():
        return check_windows_updates()
    else:
        return check_linux_updates()

def setup_automation():
    """Offer to set up automatic checks"""
    if is_windows():
        log_message("💡 For Windows: Use Task Scheduler to run this script daily")
        return
    
    print("\n🕒 Would you like to schedule automatic update checks?")
    print("1. Daily at 2 PM (recommended)")
    print("2. Weekly on Sunday at 10 AM") 
    print("3. Manual only (default)")
    
    choice = get_user_input("\nChoose option (1/2/3): ")
    
    if choice == '1':
        # Add to crontab for daily at 2 PM
        script_path = os.path.abspath(__file__)
        cron_cmd = f"0 14 * * * cd {os.path.dirname(script_path)} && python3 {os.path.basename(script_path)} --auto"
        subprocess.run(f'(crontab -l 2>/dev/null; echo "{cron_cmd}") | crontab -', shell=True)
        log_message("✅ Scheduled daily update checks at 2 PM")
        show_notification("Automation Set", "Daily update checks scheduled at 2 PM", "normal")
    
    elif choice == '2':
        # Add to crontab for weekly
        script_path = os.path.abspath(__file__)
        cron_cmd = f"0 10 * * 0 cd {os.path.dirname(script_path)} && python3 {os.path.basename(script_path)} --auto"
        subprocess.run(f'(crontab -l 2>/dev/null; echo "{cron_cmd}") | crontab -', shell=True)
        log_message("✅ Scheduled weekly update checks on Sundays at 10 AM")
        show_notification("Automation Set", "Weekly update checks scheduled", "normal")

def integrate_with_existing_system():
    """Integrate with existing update-apps.sh system"""
    if is_windows():
        return
    
    print("\n🔗 Integrate with existing auto-updater system?")
    print("This will add update checks to your daily app updates at 2 PM")
    
    choice = get_user_input("Integrate with app-updater.sh? (y/n): ")
    if choice in ['y', 'yes']:
        # Add to update-apps.sh
        script_path = os.path.abspath(__file__)
        integration_cmd = f'\n# System update check (added by automation)\necho "=== Running System Update Check ===" | tee -a $LOG_FILE\npython3 {script_path} --auto >> $LOG_FILE 2>&1'
        
        apps_script = Path.home() / "update-apps.sh"
        if apps_script.exists():
            with open(apps_script, 'a') as f:
                f.write(integration_cmd)
            log_message("✅ Integrated with update-apps.sh")
            show_notification("Integration Complete", "Update checks added to daily app updates", "normal")
        else:
            log_message("❌ update-apps.sh not found")

def main():
    """Main function"""
    auto_mode = '--auto' in sys.argv
    integrate_mode = '--integrate' in sys.argv
    
    if not auto_mode and not integrate_mode:
        log_message("=" * 50)
        log_message(f"🚀 Starting system update check on {platform.system()}")
        log_message(f"💡 Mode: Check & Notify (safe mode)")
    
    try:
        if integrate_mode:
            integrate_with_existing_system()
        else:
            success = check_and_update_system()
            
            if success and not auto_mode:
                log_message("✅ Update check completed successfully")
                
                # Offer automation options
                if not auto_mode:
                    print("\n" + "="*40)
                    print("🎯 AUTOMATION OPTIONS")
                    print("="*40)
                    
                    choice = get_user_input("Set up automatic checks? (y/n): ")
                    if choice in ['y', 'yes']:
                        setup_automation()
                        
    except Exception as e:
        error_msg = f"Unexpected error: {e}"
        log_message(f"❌ {error_msg}")
        if not auto_mode:  # Only show notification for manual runs
            show_notification("Update Error", error_msg, "critical")
    
    if not auto_mode and not integrate_mode:
        log_message("=" * 50)

if __name__ == "__main__":
    main()
