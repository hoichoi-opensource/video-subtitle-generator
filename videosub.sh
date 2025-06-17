#!/bin/bash
# videosub.sh - Master shell script for Video Subtitle Generation System

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# Function to print colored text
print_color() {
    local color=$1
    local text=$2
    echo -e "${color}${text}${NC}"
}

# Function to print banner
print_banner() {
    clear
    print_color $CYAN "╔════════════════════════════════════════════════════════════╗"
    print_color $CYAN "║                                                            ║"
    print_color $CYAN "║${BOLD}           VIDEO SUBTITLE GENERATION SYSTEM                 ${NC}${CYAN}║"
    print_color $CYAN "║                                                            ║"
    print_color $CYAN "║          Powered by Vertex AI & Google Cloud               ║"
    print_color $CYAN "║                                                            ║"
    print_color $CYAN "╚════════════════════════════════════════════════════════════╝"
    echo
}

# Function to show main menu
show_main_menu() {
    print_banner
    print_color $BOLD "Main Menu:"
    echo
    print_color $GREEN "  1) 🎬 Process Video      - Process a single video file"
    print_color $GREEN "  2) 📁 Batch Process      - Process multiple videos"
    print_color $GREEN "  3) 📊 Check Status       - View job status"
    print_color $GREEN "  4) 🧹 Cleanup           - Clean temporary files"
    print_color $GREEN "  5) 📈 Statistics        - View processing statistics"
    print_color $GREEN "  6) ⚙️  Settings         - Configure options"
    print_color $GREEN "  7) 🔐 Auth Setup        - Google Cloud authentication"
    print_color $GREEN "  8) 🧪 Test Connection   - Test system connectivity"
    print_color $GREEN "  9) 📚 Help             - Show help information"
    print_color $RED "  0) ❌ Exit"
    echo
    print_color $YELLOW "Enter your choice [0-9]: "
}

# Function to check prerequisites
check_prerequisites() {
    local all_good=true
    
    print_color $BLUE "Checking prerequisites..."
    echo
    
    # Check Python
    if command -v python3 &> /dev/null; then
        print_color $GREEN "✅ Python3: $(python3 --version)"
    else
        print_color $RED "❌ Python3: Not found"
        all_good=false
    fi
    
    # Check FFmpeg
    if command -v ffmpeg &> /dev/null; then
        print_color $GREEN "✅ FFmpeg: $(ffmpeg -version 2>&1 | head -n1)"
    else
        print_color $RED "❌ FFmpeg: Not found"
        all_good=false
    fi
    
    # Check virtual environment
    if [ -d "venv" ]; then
        print_color $GREEN "✅ Virtual environment: Found"
    else
        print_color $YELLOW "⚠️  Virtual environment: Not found (run install first)"
        all_good=false
    fi
    
    # Check config file
    if [ -f "config/config.yaml" ]; then
        print_color $GREEN "✅ Configuration: Found"
    else
        print_color $YELLOW "⚠️  Configuration: Not found (using example)"
    fi
    
    # Check Google credentials
    if [ -f "credentials/service-account.json" ] || [ ! -z "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
        print_color $GREEN "✅ Google credentials: Found"
    else
        print_color $YELLOW "⚠️  Google credentials: Not configured"
    fi
    
    echo
    
    if [ "$all_good" = false ]; then
        print_color $RED "Some prerequisites are missing. Please run install.sh first."
        return 1
    fi
    
    return 0
}

# Function to process single video
process_video() {
    print_banner
    print_color $BOLD "Process Single Video"
    echo
    
    # List videos in input directory
    print_color $BLUE "Available videos in input directory:"
    echo
    
    videos=($(find input -name "*.mp4" -o -name "*.avi" -o -name "*.mkv" -o -name "*.mov" 2>/dev/null))
    
    if [ ${#videos[@]} -eq 0 ]; then
        print_color $YELLOW "No videos found in input directory."
        print_color $YELLOW "Please place your video files in the 'input' directory."
        echo
        read -p "Press Enter to continue..."
        return
    fi
    
    # Display videos
    for i in "${!videos[@]}"; do
        print_color $CYAN "  $((i+1))) ${videos[$i]}"
    done
    
    echo
    print_color $YELLOW "Enter video number (or full path): "
    read video_choice
    
    # Determine video path
    if [[ "$video_choice" =~ ^[0-9]+$ ]] && [ "$video_choice" -ge 1 ] && [ "$video_choice" -le "${#videos[@]}" ]; then
        video_path="${videos[$((video_choice-1))]}"
    else
        video_path="$video_choice"
    fi
    
    # Check if file exists
    if [ ! -f "$video_path" ]; then
        print_color $RED "Error: Video file not found: $video_path"
        read -p "Press Enter to continue..."
        return
    fi
    
    # Select language
    echo
    print_color $BOLD "Select Language:"
    print_color $GREEN "  1) 🇬🇧 English"
    print_color $GREEN "  2) 🇮🇳 Hindi"
    print_color $GREEN "  3) 🇧🇩 Bengali"
    echo
    print_color $YELLOW "Enter language choice [1-3]: "
    read lang_choice
    
    case $lang_choice in
        1) language="en" ;;
        2) language="hi" ;;
        3) language="bn" ;;
        *) language="en" ;;
    esac
    
    # Confirm processing
    echo
    print_color $BOLD "Processing Summary:"
    print_color $CYAN "  Video: $video_path"
    print_color $CYAN "  Language: $language"
    echo
    print_color $YELLOW "Proceed with processing? [y/N]: "
    read confirm
    
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        print_color $YELLOW "Processing cancelled."
        read -p "Press Enter to continue..."
        return
    fi
    
    # Activate virtual environment and run
    echo
    print_color $BLUE "Starting processing..."
    echo
    
    source venv/bin/activate
    python -m scripts.main process "$video_path" --language "$language"
    deactivate
    
    echo
    read -p "Press Enter to continue..."
}

# Function for batch processing
batch_process() {
    print_banner
    print_color $BOLD "Batch Process Videos"
    echo
    
    print_color $YELLOW "Enter directory path (or press Enter for 'input'): "
    read dir_path
    
    if [ -z "$dir_path" ]; then
        dir_path="input"
    fi
    
    if [ ! -d "$dir_path" ]; then
        print_color $RED "Error: Directory not found: $dir_path"
        read -p "Press Enter to continue..."
        return
    fi
    
    # Select language
    echo
    print_color $BOLD "Select Language for all videos:"
    print_color $GREEN "  1) 🇬🇧 English"
    print_color $GREEN "  2) 🇮🇳 Hindi"
    print_color $GREEN "  3) 🇧🇩 Bengali"
    echo
    print_color $YELLOW "Enter language choice [1-3]: "
    read lang_choice
    
    case $lang_choice in
        1) language="en" ;;
        2) language="hi" ;;
        3) language="bn" ;;
        *) language="en" ;;
    esac
    
    # Start batch processing
    echo
    print_color $BLUE "Starting batch processing..."
    echo
    
    source venv/bin/activate
    python -m scripts.main batch "$dir_path" --language "$language"
    deactivate
    
    echo
    read -p "Press Enter to continue..."
}

# Function to check status
check_status() {
    print_banner
    print_color $BOLD "Check Job Status"
    echo
    
    print_color $YELLOW "Enter Job ID (or 'list' to see recent jobs): "
    read job_id
    
    if [ "$job_id" = "list" ]; then
        # List recent jobs
        print_color $BLUE "Recent jobs:"
        echo
        # Find metadata files
        find output -name "*_metadata.json" -type f -printf "%T@ %p\n" 2>/dev/null | sort -rn | head -10 | while read -r timestamp file; do
            job_info=$(basename "$file" _metadata.json)
            print_color $CYAN "  - $job_info"
        done
        echo
        print_color $YELLOW "Enter Job ID: "
        read job_id
    fi
    
    if [ -z "$job_id" ]; then
        return
    fi
    
    echo
    source venv/bin/activate
    python -m scripts.main status "$job_id"
    deactivate
    
    echo
    read -p "Press Enter to continue..."
}

# Function for cleanup
cleanup_files() {
    print_banner
    print_color $BOLD "Cleanup Temporary Files"
    echo
    
    print_color $YELLOW "Clean files older than how many days? [7]: "
    read days
    
    if [ -z "$days" ]; then
        days=7
    fi
    
    echo
    print_color $YELLOW "This will clean files older than $days days. Continue? [y/N]: "
    read confirm
    
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        return
    fi
    
    echo
    source venv/bin/activate
    python -m scripts.main cleanup --days "$days"
    deactivate
    
    echo
    read -p "Press Enter to continue..."
}

# Function to show statistics
show_statistics() {
    print_banner
    print_color $BOLD "Processing Statistics"
    echo
    
    # Count completed jobs
    completed=$(find output -name "*_metadata.json" -type f 2>/dev/null | xargs grep -l '"status": "COMPLETED"' 2>/dev/null | wc -l)
    failed=$(find output -name "*_metadata.json" -type f 2>/dev/null | xargs grep -l '"status": "FAILED"' 2>/dev/null | wc -l)
    total=$((completed + failed))
    
    print_color $CYAN "📊 Overall Statistics:"
    print_color $GREEN "  ✅ Completed: $completed"
    print_color $RED "  ❌ Failed: $failed"
    print_color $BLUE "  📁 Total: $total"
    echo
    
    # Disk usage
    if [ -d "output" ]; then
        output_size=$(du -sh output 2>/dev/null | cut -f1)
        print_color $CYAN "💾 Storage Usage:"
        print_color $BLUE "  Output directory: $output_size"
    fi
    
    if [ -d "temp" ]; then
        temp_size=$(du -sh temp 2>/dev/null | cut -f1)
        print_color $BLUE "  Temp directory: $temp_size"
    fi
    
    echo
    read -p "Press Enter to continue..."
}

# Function for settings
show_settings() {
    print_banner
    print_color $BOLD "Settings"
    echo
    
    if [ -f "config/config.yaml" ]; then
        print_color $GREEN "Current configuration:"
        echo
        # Show key settings
        print_color $CYAN "Model: $(grep "model:" config/config.yaml | head -1 | cut -d'"' -f2)"
        print_color $CYAN "Chunk duration: $(grep "chunk_duration:" config/config.yaml | awk '{print $2}')s"
        print_color $CYAN "Output formats: $(grep "subtitle_formats:" config/config.yaml -A2 | tail -2 | xargs)"
    else
        print_color $YELLOW "No configuration file found. Using defaults."
    fi
    
    echo
    print_color $YELLOW "To edit settings, modify config/config.yaml"
    echo
    read -p "Press Enter to continue..."
}

# Function for auth setup
setup_auth() {
    print_banner
    print_color $BOLD "Google Cloud Authentication Setup"
    echo
    
    print_color $BLUE "Current status:"
    
    if [ -f "credentials/service-account.json" ]; then
        print_color $GREEN "✅ Service account file found"
    else
        print_color $YELLOW "⚠️  Service account file not found"
    fi
    
    if [ ! -z "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
        print_color $GREEN "✅ GOOGLE_APPLICATION_CREDENTIALS set"
    else
        print_color $YELLOW "⚠️  GOOGLE_APPLICATION_CREDENTIALS not set"
    fi
    
    echo
    print_color $CYAN "To set up authentication:"
    print_color $WHITE "1. Go to Google Cloud Console"
    print_color $WHITE "2. Create a service account with Vertex AI and Storage permissions"
    print_color $WHITE "3. Download the JSON key file"
    print_color $WHITE "4. Save it as: credentials/service-account.json"
    echo
    print_color $YELLOW "Do you have a service account JSON file to configure? [y/N]: "
    read has_file
    
    if [[ "$has_file" =~ ^[Yy]$ ]]; then
        print_color $YELLOW "Enter the path to your JSON file: "
        read json_path
        
        if [ -f "$json_path" ]; then
            mkdir -p credentials
            cp "$json_path" credentials/service-account.json
            print_color $GREEN "✅ Service account file configured successfully!"
        else
            print_color $RED "❌ File not found: $json_path"
        fi
    fi
    
    echo
    read -p "Press Enter to continue..."
}

# Function to test connection
test_connection() {
    print_banner
    print_color $BOLD "Test System Connection"
    echo
    
    print_color $BLUE "Testing connections..."
    echo
    
    # Create a simple test script
    cat > test_connection.py << 'EOF'
import sys
sys.path.append('.')

try:
    from scripts.config import get_config
    from scripts.gcs_manager import GCSManager
    from scripts.subtitle_generator import SubtitleGenerator
    
    print("1. Testing configuration...")
    config = get_config()
    print("   ✅ Configuration loaded")
    
    print("\n2. Testing Google Cloud Storage...")
    try:
        gcs = GCSManager()
        is_connected, message = gcs.test_connection()
        if is_connected:
            print(f"   ✅ {message}")
        else:
            print(f"   ❌ {message}")
    except Exception as e:
        print(f"   ❌ GCS Error: {str(e)}")
    
    print("\n3. Testing Vertex AI...")
    try:
        subtitle_gen = SubtitleGenerator()
        print(f"   ✅ Vertex AI initialized with model: {config.vertex_ai['model']}")
    except Exception as e:
        print(f"   ❌ Vertex AI Error: {str(e)}")
    
except Exception as e:
    print(f"❌ Error: {str(e)}")
EOF
    
    source venv/bin/activate
    python test_connection.py
    deactivate
    
    rm -f test_connection.py
    
    echo
    read -p "Press Enter to continue..."
}

# Function to show help
show_help() {
    print_banner
    print_color $BOLD "Help Information"
    echo
    
    print_color $CYAN "Video Subtitle Generation System"
    print_color $WHITE "This system generates subtitles for videos using Google's Vertex AI."
    echo
    
    print_color $YELLOW "Quick Start:"
    print_color $WHITE "1. Run install.sh to set up the environment"
    print_color $WHITE "2. Configure Google Cloud credentials"
    print_color $WHITE "3. Place video files in the 'input' directory"
    print_color $WHITE "4. Select 'Process Video' from the main menu"
    echo
    
    print_color $YELLOW "Supported Languages:"
    print_color $WHITE "- English (en)"
    print_color $WHITE "- Hindi (hi)"
    print_color $WHITE "- Bengali (bn)"
    echo
    
    print_color $YELLOW "Supported Video Formats:"
    print_color $WHITE "MP4, AVI, MKV, MOV, WMV, FLV, WEBM"
    echo
    
    print_color $YELLOW "For more information:"
    print_color $WHITE "- See README.md for detailed documentation"
    print_color $WHITE "- Check TROUBLESHOOTING.md for common issues"
    echo
    
    read -p "Press Enter to continue..."
}

# Main loop
main() {
    # Check if running from correct directory
    if [ ! -f "videosub.sh" ]; then
        print_color $RED "Error: Please run this script from the project root directory"
        exit 1
    fi
    
    # Initial prerequisite check
    if ! check_prerequisites; then
        print_color $YELLOW "Would you like to run the installer? [y/N]: "
        read install_choice
        if [[ "$install_choice" =~ ^[Yy]$ ]]; then
            if [ -f "install.sh" ]; then
                bash install.sh
            else
                print_color $RED "install.sh not found!"
                exit 1
            fi
        fi
    fi
    
    # Main menu loop
    while true; do
        show_main_menu
        read -n 1 choice
        echo
        
        case $choice in
            1) process_video ;;
            2) batch_process ;;
            3) check_status ;;
            4) cleanup_files ;;
            5) show_statistics ;;
            6) show_settings ;;
            7) setup_auth ;;
            8) test_connection ;;
            9) show_help ;;
            0) 
                print_color $GREEN "Thank you for using Video Subtitle Generation System!"
                exit 0
                ;;
            *)
                print_color $RED "Invalid choice. Please try again."
                sleep 1
                ;;
        esac
    done
}

# Run main function
main