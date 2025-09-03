# SCALE System v2.0 - Installation Guide

**Professional Weighbridge Management System**  
**Author:** MiniMax Agent  
**Version:** 2.0.0 - Phase 1  
**Date:** 2025-08-23

---

## Prerequisites

### System Requirements
- **Operating System:** Windows 10/11, Linux, macOS
- **Python:** Version 3.8 or higher (3.12+ recommended)
- **Memory:** Minimum 512MB RAM
- **Storage:** 100MB free disk space
- **Hardware:** Serial port (COM/USB) for weight indicator connection

### Weight Indicator Compatibility
- **Toledo** - Native protocol support
- **Avery** - Built-in protocol parser
- **Generic** - CSV format with configurable patterns
- **Custom** - User-definable protocol support

---

## Installation Steps

### 1. Download and Extract

```bash
# Download the SCALE System files
# Extract to desired directory, e.g.:
C:\SCALE_System\    (Windows)
/opt/scale_system/   (Linux)
/Applications/SCALE_System/  (macOS)
```

### 2. Install Python Dependencies

```bash
# Navigate to installation directory
cd scale_system

# Install required packages
pip install pyserial==3.5 qrcode[pil]==8.2 Pillow

# Or use requirements file
pip install -r requirements.txt
```

### 3. Initialize Database

```bash
# Run the main application to initialize database
python main.py
```

This will create:
- `data/scale_system.db` - Main database
- `config/` - Configuration directory
- `logs/` - Application logs
- `backups/` - Database backups

### 4. Configure Hardware

#### 4.1 Identify Serial Port
```bash
# Run hardware test to see available ports
python test_hardware.py
```

#### 4.2 Configure Weight Indicator
1. Connect weight indicator to serial port
2. Note the communication parameters:
   - **Port:** COM1, COM2, etc. (Windows) or /dev/ttyUSB0 (Linux)
   - **Baud Rate:** Usually 9600
   - **Data Bits:** Usually 8
   - **Parity:** Usually None
   - **Stop Bits:** Usually 1

#### 4.3 Select Protocol Profile
The system includes pre-configured profiles:
- **Generic** - Standard CSV format
- **Toledo** - Toledo weight indicators  
- **Avery** - Avery weight indicators

---

## Configuration

### Database Configuration

The database is automatically configured with:
- **Default Admin User:** `admin` (no PIN required initially)
- **Default Settings:** Optimized for most weighbridge operations
- **Sample Data:** None (clean installation)

### Hardware Configuration

Edit `config/hardware_profiles.json` to customize:

```json
{
  "Custom Profile": {
    "name": "Custom Profile",
    "port": "COM1",
    "baud_rate": 9600,
    "data_bits": 8,
    "parity": "N",
    "stop_bits": 1,
    "protocol": "generic",
    "stable_indicator": "ST",
    "weight_pattern": "([+-]?\\d+\.?\\d*)"
  }
}
```

### Application Settings

Settings are stored in the database and can be modified:

```python
# Example: Change serial port
dal = DataAccessLayer("data/scale_system.db")
dal.set_setting('serial_port', 'COM2', operator_id)
```

Key settings:
- `serial_port` - Weight indicator serial port
- `weight_decimal_places` - Number of decimal places (default: 2)
- `stable_weight_threshold` - Stability threshold in kg (default: 0.5)
- `ticket_prefix` - Ticket number prefix (default: 'SC')

---

## Testing Installation

### 1. Database Test
```bash
# Run Phase 1 demo
python demo_phase1.py
```

Expected output:
```
✅ Database Schema & Operations
✅ Hardware Abstraction Layer  
✅ Serial Communication Framework
✅ Diagnostic Tools
✅ Utility Functions
✅ Configuration Management
```

### 2. Hardware Test
```bash
# Test hardware abstraction layer
python test_hardware.py
```

Expected output:
```
✅ Protocol Parsing
✅ Diagnostic Console
✅ Hardware Profiles
✅ Weight Reading Simulation
```

### 3. Manual Database Check
```bash
# Check database creation
ls -la data/scale_system.db    # Linux/macOS
dir data\scale_system.db       # Windows
```

---

## Troubleshooting

### Common Issues

#### 1. Python Not Found
**Error:** `python: command not found`

**Solution:**
- Install Python from https://python.org
- Ensure Python is in system PATH
- Try `python3` instead of `python` on Linux/macOS

#### 2. Permission Denied (Linux/macOS)
**Error:** `Permission denied: '/dev/ttyUSB0'`

**Solution:**
```bash
# Add user to dialout group
sudo usermod -a -G dialout $USER
# Logout and login again
```

#### 3. Serial Port Not Available
**Error:** `SerialException: could not open port 'COM1'`

**Solutions:**
- Check if port exists: `python test_hardware.py`
- Verify weight indicator is connected
- Close other applications using the port
- Try different port (COM2, COM3, etc.)

#### 4. Database Initialization Failed
**Error:** `sqlite3.OperationalError`

**Solutions:**
- Check write permissions in data directory
- Ensure sufficient disk space
- Delete existing database and reinitialize

#### 5. Import Errors
**Error:** `ModuleNotFoundError: No module named 'serial'`

**Solution:**
```bash
pip install pyserial qrcode[pil] Pillow
```

### Log Files

Check log files for detailed error information:
- `logs/scale_system.log` - Application logs
- `logs/serial_communication.log` - Hardware communication
- `data/diagnostic_log.txt` - Console output

### Support Commands

```bash
# Check Python version
python --version

# Check installed packages
pip list

# Test database connection
python -c "import sqlite3; print('SQLite OK')"

# Test serial library
python -c "import serial; print('PySerial OK')"

# List serial ports
python -c "import serial.tools.list_ports; print([p.device for p in serial.tools.list_ports.comports()])"
```

---

## File Structure After Installation

```
scale_system/
├── main.py                    # Main application
├── demo_phase1.py            # Demo application
├── test_hardware.py          # Hardware tests
├── requirements.txt          # Dependencies
│
├── data/
│   ├── scale_system.db       # Main database (auto-created)
│   └── *.csv, *.json        # Export files
│
├── config/
│   └── hardware_profiles.json # Hardware configurations
│
├── logs/                     # Log files (auto-created)
├── backups/                  # Database backups
├── reports/                  # Generated reports
├── templates/                # Report templates
│
└── [source modules]          # Python source code
```

---

## Security Considerations

### Default Security
- Default admin user has **no PIN** (set PIN after installation)
- Database is **not encrypted** (suitable for local installation)
- Serial communication is **unencrypted** (standard for weight indicators)

### Recommended Security Steps
1. **Set Admin PIN** after installation
2. **Create Operator Users** with limited privileges
3. **Regular Backups** to secure location
4. **File System Permissions** - Restrict database access
5. **Network Security** - If running on networked system

---

## Performance Optimization

### Database Performance
- Database uses **WAL mode** for better concurrency
- **Automatic VACUUM** keeps database optimized
- **Indexed queries** for fast data retrieval

### Serial Communication
- **Background threading** prevents UI blocking
- **Message queue** handles high-frequency data
- **Automatic reconnection** for reliable operation

### Memory Usage
- **Minimal memory footprint** (~50MB typical)
- **Efficient data structures** for large datasets
- **Garbage collection** for long-running operation

---

## Backup and Recovery

### Automatic Backups
The system can create automatic backups:
```python
# Enable automatic backup
dal.set_setting('auto_backup_enabled', True, operator_id)
dal.set_setting('backup_retention_days', 30, operator_id)
```

### Manual Backup
```bash
# Create backup
python -c "
from database.data_access import DataAccessLayer
dal = DataAccessLayer('data/scale_system.db')
dal.create_backup('backups/manual_backup.db')
print('Backup created')
"
```

### Recovery
```bash
# Restore from backup
python -c "
from database.data_access import DataAccessLayer
dal = DataAccessLayer('data/scale_system.db')
dal.restore_backup('backups/manual_backup.db')
print('Database restored')
"
```

---

## Getting Started

After successful installation:

1. **Run Initial Test**
   ```bash
   python demo_phase1.py
   ```

2. **Configure Hardware**
   - Connect weight indicator
   - Test communication
   - Adjust protocol settings

3. **Set Up Users**
   - Create operator accounts
   - Set PINs for security
   - Assign appropriate roles

4. **Ready for Phase 2**
   - Core foundation is complete
   - Ready for GUI implementation
   - Authentication system prepared

**Installation Complete! 🎉**

---

*For technical support or questions, refer to the Phase 1 Implementation Report for detailed technical information.*
