# Quick Start Guide

## 🚀 Get Started in 3 Steps

### 1. Install
```bash
git clone <repository-url>
cd video-subtitle-generator
chmod +x install.sh
./install.sh
```

### 2. Setup Google Cloud Credentials
```bash
# Download service account JSON from Google Cloud Console
cp ~/Downloads/your-service-account.json ./service-account.json
```

### 3. Run
```bash
./subtitle-gen
```

That's it! No need to manually activate virtual environments or manage dependencies.

## 🎯 What Happens Automatically

When you run `./subtitle-gen`, the script automatically:

✅ **Activates Virtual Environment** - No manual `source venv/bin/activate` needed  
✅ **Checks Dependencies** - Verifies all packages are installed  
✅ **Creates Directories** - Sets up input/output folders  
✅ **Starts Application** - Launches the interactive menu  

## 📁 Quick Usage

**Place your videos in the `input/` folder and run:**
```bash
./subtitle-gen
```

**Or process a specific video:**
```bash
./subtitle-gen --video /path/to/video.mp4
```

## 🆘 Troubleshooting

**If you see "Virtual environment not found":**
```bash
./install.sh
```

**If you see SSL errors:**
```bash
./fix_ssl.sh
```

**If you see permission errors:**
```bash
chmod +x subtitle-gen run.sh
```

## 📝 Alternative Commands

```bash
./run.sh              # Same as ./subtitle-gen
./subtitle-gen --help # Show all options
```

**No virtual environment activation required for any of these commands!** 🎉