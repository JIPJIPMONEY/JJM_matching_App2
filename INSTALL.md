# Quick Installation Guide 🚀

## Step 1: Download & Extract
1. Download the `RELEASE_v1.0` folder
2. Extract it to your desired location

## Step 2: Add Your Data
1. Copy your `Customer_Loan_2025_06_07.xlsx` file into the `RELEASE_v1.0` folder
2. **Brand keywords are already included!** (CHANEL and LOUIS_VUITTON samples)
3. (Optional) Add more brand keyword files to `BRAND_KEYWORDS/` folder if needed

## Step 3: Install Docker
- **Windows**: [Download Docker Desktop](https://docs.docker.com/desktop/windows/)
- **Mac**: [Download Docker Desktop](https://docs.docker.com/desktop/mac/)
- **Linux**: [Install Docker Engine](https://docs.docker.com/engine/install/)

## Step 4: Run the App

### Windows Users:
1. Double-click `deploy.bat`
2. Wait for the app to start
3. Open http://localhost:8501

### Mac/Linux Users:
1. Open Terminal in the app folder
2. Run: `chmod +x deploy.sh && ./deploy.sh`
3. Open http://localhost:8501

### Alternative (All Platforms):
1. Open command prompt/terminal in the app folder
2. Run: `docker-compose up --build`
3. Open http://localhost:8501

## That's it! 🎉

Your Customer Loan Management app is now running at:
**http://localhost:8501**

## Need Help?
- Check the full `README.md` for detailed instructions
- Ensure your Excel file is in the same folder as the Docker files
- Make sure Docker Desktop is running before starting the app
