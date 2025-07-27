# 🚀 Docker Quick Start - Video Subtitle Generator

**Run everything in Docker - No local setup required!**

## 🎯 5-Minute Setup

### 1️⃣ Prerequisites
- Docker Desktop installed ([Windows](https://docs.docker.com/desktop/windows/install/) | [Mac](https://docs.docker.com/desktop/mac/install/) | [Linux](https://docs.docker.com/engine/install/))
- Google Cloud service account JSON file

### 2️⃣ Quick Setup
```bash
# Clone repository
git clone <repository-url>
cd Video-subtitle-Generator

# Create data folders
mkdir -p data/{input,output,config,logs,temp,jobs}

# Copy your Google Cloud credentials
cp /path/to/your-service-account.json data/config/

# Make scripts executable (Linux/Mac)
chmod +x docker-run.sh docker-entrypoint.sh
```

### 3️⃣ Run It!

**All Platforms:**
```bash
# Using modern docker compose
docker compose run --rm subtitle-generator

# Or use convenience scripts:
./docker-run.sh              # Linux/Mac
docker-run.bat               # Windows
```

That's it! The application will build and start in interactive mode.

## 📹 Process Your First Video

### Method 1: Interactive Mode (Easiest)
```bash
# Copy video to input folder
cp my-video.mp4 data/input/

# Run interactive mode
./docker-run.sh              # Linux/Mac
docker-run.bat               # Windows

# Select option 1 and follow prompts
```

### Method 2: Command Line
```bash
# Modern docker compose syntax
docker compose run --rm subtitle-generator python main.py --video /data/input/my-video.mp4 --languages eng,hin,ben

# Or using convenience scripts
./docker-run.sh --video /data/input/my-video.mp4 --languages eng,hin,ben,tel
./docker-run.sh --batch /data/input
```

## 🎮 Common Commands

| What you want | Command |
|--------------|---------|
| **Interactive menu** | `./docker-run.sh` |
| **Process video** | `./docker-run.sh --video /data/input/video.mp4` |
| **Batch process** | `./docker-run.sh --batch /data/input` |
| **Get help** | `./docker-run.sh --help` |
| **Shell access** | `./docker-run.sh shell` |
| **Health check** | `./docker-run.sh health` |
| **View logs** | `./docker-run.sh logs` |
| **Run as service** | `./docker-run.sh daemon` |
| **Stop service** | `./docker-run.sh stop` |

## 📁 Where Files Go

```
Video-subtitle-Generator/
├── data/
│   ├── input/      ← Put videos here
│   ├── output/     ← Find subtitles here
│   ├── config/     ← Put service-account.json here
│   └── logs/       ← Check logs here
```

## 🔧 Configuration (Optional)

### Custom Settings
Create `data/config/config.yaml`:
```yaml
vertex_ai:
  temperature: 0.2
  max_output_tokens: 8192

processing:
  chunk_duration: 60
  parallel_workers: 4
```

### Environment Variables
Edit `docker-compose.yml` (or use override file):
```yaml
environment:
  - LOG_LEVEL=DEBUG
  - ENV=development
```

## 🚨 Troubleshooting

### "No service account found"
→ Copy your Google Cloud JSON to `data/config/service-account.json`

### "Permission denied"
→ **Linux/Mac**: `sudo chown -R $USER:$USER data/`
→ **Windows**: Run as Administrator

### "Out of memory"
→ Increase Docker memory: Docker Desktop → Settings → Resources → Memory: 8GB

### "Cannot connect to Docker"
→ Make sure Docker Desktop is running

## 🎯 Complete Examples

### Example 1: Process Hindi Video to Multiple Indian Languages
```bash
# Put video in input
cp hindi-movie.mp4 data/input/

# Process to core + regional languages
./docker-run.sh process --video /data/input/hindi-movie.mp4 --languages eng,hin,ben,tel,tam,mar
```

### Example 2: Process English Video to Indian Languages
```bash
# Copy English video
cp english-documentary.mp4 data/input/

# Process to major Indian languages
./docker-run.sh process --video /data/input/english-documentary.mp4 --languages eng,hin,ben,tel,tam,guj,kan,mal
```

### Example 3: Run as Background Service
```bash
# Start service
./docker-run.sh daemon

# Monitor logs
./docker-run.sh logs

# Stop when done
./docker-run.sh stop
```

## 📊 Monitor Progress

### Real-time Logs
```bash
docker compose logs -f subtitle-generator
```

### Check Health
```bash
./docker-run.sh health
# Or directly:
docker compose exec subtitle-generator python -c "from src.health_checker import quick_health_check; print(quick_health_check())"
```

### Resource Usage
```bash
docker stats subtitle-generator
```

## 🆘 Get Help

### Application Help
```bash
./docker-run.sh --help
```

### Shell Access (Advanced)
```bash
# Get shell inside container
./docker-run.sh shell

# Test components
python -c "from src.health_checker import quick_health_check; print(quick_health_check())"
```

## ✅ Success Checklist

- [ ] Docker Desktop running
- [ ] `data/config/service-account.json` exists
- [ ] Video files in `data/input/`
- [ ] Run `./docker-run.sh`
- [ ] Check `data/output/` for subtitles!

---

**That's all! Everything runs inside Docker - no Python, no dependencies, works everywhere!** 🎉