# System Updater Tool 🔄

A cross-platform system update checker and notifier with automated scheduling options.

## Features
- ✅ **Windows Support**: Checks for Windows updates using PowerShell
- ✅ **Linux Support**: Checks for APT package updates (Ubuntu/Debian)
- ✅ **Safe Check & Notify**: Only checks for updates, never auto-installs
- ✅ **Desktop Notifications**: Shows detailed update status on both platforms
- ✅ **Security Update Highlighting**: Prioritizes security and kernel updates
- ✅ **Automation Ready**: Built-in scheduling and integration options
- ✅ **Comprehensive Logging**: Detailed log files with timestamps

## Components

### Python Update Checker (`src/updater.py`)
- Cross-platform update detection
- Interactive and auto modes
- Detailed update categorization
- Desktop notifications

### Bash Automation Script (`scripts/update-apps.sh`) 
- Snap application updates
- Integrated system update checks
- Cron job ready
- Comprehensive logging

## Installation

### Quick Start
```bash
# Clone the repository
git clone https://github.com/accentvic/system-updater-tool.git
cd system-updater-tool

# Make scripts executable
chmod +x scripts/update-apps.sh
