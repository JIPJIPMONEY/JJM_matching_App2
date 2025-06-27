# Customer Loan Management App v1.0 🏦

**Professional Docker-ready application for managing customer loan records with keyword validation.**

## 🚀 Quick Start

### 1. Prerequisites
- **Docker Desktop** installed on your system
  - Windows: [Download Docker Desktop](https://docs.docker.com/desktop/windows/)
  - Mac: [Download Docker Desktop](https://docs.docker.com/desktop/mac/)
  - Linux: [Install Docker Engine](https://docs.docker.com/engine/install/)

### 2. Setup Your Data
1. Place your Excel file named `Customer_Loan_2025_06_07.xlsx` in this directory
2. **Brand keywords are already included!** The `BRAND_KEYWORDS` folder contains sample brand files (CHANEL, LOUIS_VUITTON)
3. (Optional) Add more brand keyword JSON files to the `BRAND_KEYWORDS` folder if needed

### 3. Run the Application

**Option A: Main Deployment Script (Recommended)**
```bash
# Windows - double-click or run in command prompt
deploy.bat
```

**Option B: Simple Deployment**
```bash
# Windows - if you prefer the minimal version
simple_deploy.bat
```

**Option C: Docker Compose (Advanced)**
```bash
docker-compose up --build
```

### 4. Access the App
- The app will automatically open in your browser after ~30 seconds
- Or manually go to: **http://localhost:8501**

## 🛠️ Troubleshooting

### Quick System Check:
```batch
# Run this first if you have issues
quick_check.bat

# For detailed system diagnostics
check_system.bat
```

### Common Issues:

**❌ "Docker is not installed"**
- Install Docker Desktop from the official website
- Make sure Docker Desktop is running (check system tray)
- Restart your computer after installation

**❌ "Port 8501 already in use"**
- Stop any other Streamlit apps: `Ctrl+C` in their terminals
- Kill the process: `taskkill /f /im streamlit.exe` (Windows)

**❌ "Excel file not found"**
- Make sure `Customer_Loan_2025_06_07.xlsx` is in the same directory as the scripts
- Check the filename matches exactly (case-sensitive)

**❌ Build fails**
- Restart Docker Desktop
- Free up disk space (Docker needs ~2GB for this app)
- Run as Administrator (Windows)

## ✨ Features

### 📊 **Status Filtering**
- **All Records**: View complete dataset
- **✅ Fixed**: View completed records  
- **❌ Unfixed**: View pending records

### 🔍 **Advanced Filtering**
- Filter by Contract Number (All/Empty/Not Empty)
- Filter by Type, Brand, Sub-Model
- Dependent dropdown filtering

### ✏️ **Smart Record Editing**
- Single-row selection for editing
- Dependent dropdown validation
- Hierarchical Brand → Model → Sub-Model → Size/Material
- Independent Color and Hardware selection
- Auto-save to Excel file

### 📈 **Progress Tracking**
- Real-time progress dashboard
- Persistent status tracking in Excel
- Export functionality for completed records

### 🖼️ **Image Preview**
- View product images directly in the app
- Automatic image loading from URLs

## 📁 File Structure

Your project folder should look like this:
```
your-project-folder/
├── Customer_Loan_2025_06_07.xlsx    # Required: Your main Excel file
├── BRAND_KEYWORDS/                   # ✅ Included: Brand keyword files
│   ├── brands_list.txt              # List of available brands
│   ├── CHANEL/
│   │   └── chanel_keywords.json     # ✅ Sample CHANEL keywords
│   └── LOUIS_VUITTON/
│       └── louis_vuitton_keywords.json # ✅ Sample LOUIS VUITTON keywords
├── Dockerfile                       # Docker configuration
├── docker-compose.yml               # Docker Compose config
├── deploy.bat                       # Windows deployment script
├── deploy.sh                        # Linux/Mac deployment script
└── README.md                        # This file
```

## 🔧 Configuration

### Excel File Requirements
- Must be named: `Customer_Loan_2025_06_07.xlsx`
- Required columns: `Form_ids`, `Transaction_dates`, `Contract_Numbers`, `Types`, `Brands`, `Models`, `Sub-Models`, `Sizes`, `Colors`, `Hardwares`, `Materials`, `Estimate_prices`, `Picture_url`
- Status column will be auto-created if missing

### Brand Keywords (Optional)
Brand keyword files should be JSON format:
```json
{
  "models": {
    "ModelName": {
      "sub_models": {
        "SubModelName": {
          "sizes": ["Small", "Medium", "Large"],
          "materials": ["Leather", "Canvas"]
        }
      }
    }
  },
  "colors": ["Black", "Brown", "Red"],
  "hardwares": ["Gold", "Silver", "Bronze"]
}
```

## 🛠️ Troubleshooting

### Docker Issues
- **Docker not found**: Install Docker Desktop from the official website
- **Permission denied**: On Linux/Mac, run with `sudo` or add user to docker group
- **Port 8501 in use**: Stop other applications using port 8501 or change port in docker-compose.yml

### Data Issues
- **Excel file not found**: Ensure file is named exactly `Customer_Loan_2025_06_07.xlsx`
- **No data loading**: Check Excel file format and column names
- **Keywords not loading**: Verify JSON file format and directory structure

### Application Issues
- **App won't start**: Check Docker logs with `docker-compose logs`
- **Can't save changes**: Ensure Docker has write permissions to mounted directory
- **Images not loading**: Check image URLs and internet connection

## 🔄 Updates and Maintenance

### Stopping the Application
```bash
# With Docker Compose
docker-compose down

# With Docker
docker stop <container-name>
```

### Updating Data
- Replace Excel file and restart the container
- Add new brand keywords and restart the container

### Backup Data
- Export updated records using the app's export feature
- Copy the updated Excel file from your project directory

## 📞 Support

### Common Solutions
1. **Restart Docker Desktop** if the app won't start
2. **Check file permissions** if data won't save
3. **Verify Excel file format** if data won't load
4. **Update Docker** if you encounter compatibility issues

### System Requirements
- **RAM**: 2GB minimum, 4GB recommended
- **Storage**: 1GB free space
- **Network**: Internet connection for image loading
- **OS**: Windows 10+, macOS 10.14+, or modern Linux

---

**Version**: 1.0  
**Release Date**: June 2025  
**Docker**: Ready for deployment  
**Status**: Production Ready ✅
