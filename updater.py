#!/usr/bin/env python3
import subprocess
import datetime
import platform
import os
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
            $balloon.ShowBalloonTip(10000)
            '''
            subprocess.run(['powershell', '-Command', ps_script], check=False)
        else:
            # Linux notification
            subprocess.run([
                'notify-send', 
                '-u', urgency,
                '-t', '10000',
                title, 
                message
            ], check=False)
    except Exception as e:
        print(f"Notification failed: {e}")

def run_command(cmd, use_sudo=True):
    """Run command with platform-specific handling"""
    if is_windows():
        # Remove sudo from commands on Windows
        if use_sudo and cmd[0] == 'sudo':
            cmd = cmd[1:]
        # Use PowerShell for Windows
        if cmd[0] in ['apt', 'snap']:
            return None, "Package manager not available on Windows", 1
    else:
        # Linux commands
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
    
    print(message)

def check_windows_updates():
    """Check for Windows updates"""
    log_message("🔍 Checking for Windows updates...")
    show_notification("Windows Update", "Checking for available updates...", "low")
    
    # Check for Windows updates using PowerShell
    ps_script = '''
    $UpdateSession = New-Object -ComObject Microsoft.Update.Session
    $UpdateSearcher = $UpdateSession.CreateUpdateSearcher()
    $SearchResult = $UpdateSearcher.Search("IsInstalled=0")
    
    if ($SearchResult.Updates.Count -gt 0) {
        Write-Host "UPDATES_AVAILABLE:" $SearchResult.Updates.Count
        foreach ($Update in $SearchResult.Updates) {
            Write-Host "UPDATE:" $Update.Title
        }
    } else {
        Write-Host "NO_UPDATES"
    }
    '''
    
    stdout, stderr, returncode = run_command(['powershell', '-Command', ps_script], use_sudo=False)
    
    if "UPDATES_AVAILABLE" in stdout:
        update_count = int(stdout.split("UPDATES_AVAILABLE:")[1].split()[0])
        log_message(f"📦 Found {update_count} Windows updates")
        show_notification(
            "Windows Updates Available", 
            f"Found {update_count} updates. Install them from Windows Update.",
            "normal"
        )
        return True
    elif "NO_UPDATES" in stdout:
        log_message("✅ Windows is up to date")
        show_notification("Windows Update", "System is already up to date", "low")
        return True
    else:
        log_message("⚠️ Could not check Windows updates automatically")
        show_notification("Windows Update", "Check updates manually in Settings", "normal")
        return False

def check_linux_updates():
    """Check for Linux updates"""
    log_message("🔍 Checking for Ubuntu updates...")
    show_notification("System Update", "Checking for available updates...", "low")
    
    # Update package lists
    stdout, stderr, returncode = run_command(['apt', 'update'])
    
    if returncode != 0:
        error_msg = "Failed to update package lists"
        log_message(f"❌ {error_msg}")
        show_notification("Update Error", error_msg, "critical")
        return False
    
    # Check for upgradable packages
    stdout, stderr, returncode = run_command(['apt', 'list', '--upgradable'], use_sudo=False)
    
    upgradable_packages = []
    if returncode == 0 and stdout:
        upgradable_packages = [line.split('/')[0] for line in stdout.split('\n') 
                             if line and not line.startswith('Listing')]
    
    if not upgradable_packages:
        success_msg = "System is already up to date"
        log_message(f"✅ {success_msg}")
        show_notification("System Update", success_msg, "low")
        return True
    
    # Show update available notification
    log_message(f"📦 Found {len(upgradable_packages)} packages to update")
    show_notification(
        "Updates Available", 
        f"Found {len(upgradable_packages)} packages to update. Starting upgrade...",
        "normal"
    )
    
    # Perform the upgrade
    log_message("🔄 Starting system upgrade...")
    show_notification("System Update", "Installing updates... This may take a few minutes.", "normal")
    
    stdout, stderr, returncode = run_command(['apt', 'upgrade', '-y'])
    
    if returncode == 0:
        # Clean up
        run_command(['apt', 'autoclean'])
        run_command(['apt', 'autoremove', '-y'])
        
        success_msg = f"Successfully updated {len(upgradable_packages)} packages"
        log_message(f"✅ {success_msg}")
        show_notification("Update Complete", success_msg, "normal")
        
        # Show important packages if any
        important_packages = [pkg for pkg in upgradable_packages 
                            if any(word in pkg.lower() for word in ['linux', 'firefox', 'kernel', 'security'])]
        
        if important_packages:
            important_msg = f"Important updates: {', '.join(important_packages[:3])}"
            if len(important_packages) > 3:
                important_msg += f" and {len(important_packages) - 3} more"
            show_notification("Important Updates", important_msg, "normal")
        
        return True
    else:
        error_msg = "System upgrade failed"
        log_message(f"❌ {error_msg}")
        show_notification("Update Failed", error_msg, "critical")
        return False

def check_and_update_system():
    """Check for updates based on platform"""
    if is_windows():
        return check_windows_updates()
    else:
        return check_linux_updates()

def main():
    """Main function"""
    log_message("=" * 50)
    log_message(f"🚀 Starting automated system update check on {platform.system()}")
    
    try:
        success = check_and_update_system()
        
        if success:
            log_message("✅ Update process completed successfully")
        else:
            log_message("❌ Update process encountered errors")
            
    except Exception as e:
        error_msg = f"Unexpected error: {e}"
        log_message(f"❌ {error_msg}")
        show_notification("Update Error", error_msg, "critical")
    
    log_message("=" * 50)

if __name__ == "__main__":
    main()
