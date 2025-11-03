# MeetMinder

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Website](https://img.shields.io/badge/website-meetminder.io-blue)](https://meetminder.io/)

A real-time AI meeting assistant with system audio transcription, intelligent topic analysis, and context-aware responses. Available in two UI options: standard PyQt5 interface (~150MB) or lightweight web-based UI (~15-30MB) using native OS webviews. Features a modern overlay interface that stays at the top of your screen during meetings and calls.

## ✨ Features

- **🎙️ Real-time Audio Transcription**: Captures system audio (meetings, videos) with live transcript display
- **🤖 Multi-LLM Support**: OpenAI GPT, Azure OpenAI, Google Gemini integration
- **📊 Topic Analysis**: Intelligent conversation flow tracking and guidance
- **🖥️ Modern UI Options**:
  - Standard: Advanced PyQt5 interface with transparency effects (~150MB)
  - Lightweight: Web-based UI using native OS webviews (~15-30MB) ⭐ **RECOMMENDED**
- **⌨️ Global Hotkeys**: Instant AI assistance with customizable shortcuts
- **🔒 Privacy Focused**: Local audio processing with optional cloud AI
- **⚙️ Highly Configurable**: Extensive settings through YAML configuration or full settings dialog

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- Windows 10/11, macOS, or Linux
- Microphone and speaker access

### Installation Options

#### Option 1: Standard Version (PyQt5 - ~150MB)
For full-featured UI with advanced graphics capabilities:

1. **Clone the repository**
   ```bash
   git clone https://github.com/mojtaba217/meetminder.git
   cd meetminder
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure API Keys**

   Edit `config.yaml` and add your AI provider credentials:
   ```yaml
   ai_provider:
     type: azure_openai  # or 'openai' or 'google_gemini'
     azure_openai:
       api_key: "your-api-key-here"
       endpoint: "https://your-resource.openai.azure.com/"
       model: "gpt-4"
   ```

4. **Run the application**
   ```bash
   python main.py
   ```

#### Option 2: Lightweight Version (pywebview - ~15-30MB) ⭐ **RECOMMENDED**
For a much smaller, web-based UI with 80-90% size reduction:

1. **Install lightweight dependencies**
   ```bash
   pip install -r requirements_lightweight.txt
   ```

2. **Configure API Keys** (same as above)

3. **Run the lightweight version**
   ```bash
   python main_lightweight.py
   ```

4. **Build portable executable** (optional)
   ```bash
   python build_lightweight.py
   ```

**Key Differences:**
- **Lightweight**: Uses native OS webviews instead of PyQt5
- **Size**: 80-90% smaller (~15-30MB vs ~150MB)
- **UI**: Modern web-based interface with full settings dialog
- **Features**: All core functionality preserved
- **Performance**: Faster startup, lower memory usage

## 💻 Usage

### Interface

MeetMinder displays as a horizontal bar at the top-center of your screen:

- **🎤 Recording Button**: Start/stop audio capture
- **⏱️ Timer**: Shows recording duration  
- **🤖 Ask AI**: Trigger AI analysis
- **▼ Expand**: Show detailed transcript and analysis
- **⚙️ Settings**: Configure all options
- **✕ Close**: Exit application

### Global Hotkeys
- **Ctrl+Space**: Trigger AI assistance
- **Ctrl+B**: Toggle overlay visibility
- **Ctrl+H**: Take screenshot
- **Alt+Arrow Keys**: Move overlay position
- **Ctrl+Shift+R**: Emergency reset

### Use Cases

#### 1. Meeting Assistant
- Automatically detects meeting applications (Zoom, Teams, etc.)
- Provides real-time objection handling suggestions
- Summarizes key discussion points
- Suggests relevant questions based on your expertise

#### 2. Coding Assistant
- Detects coding environments (VS Code, PyCharm, etc.)
- Analyzes clipboard content and active files
- Provides debugging suggestions tailored to your skill level
- Recommends best practices based on your experience

#### 3. General Work Assistant
- Monitors screen context and clipboard
- Provides task-specific guidance
- Adapts suggestions to your professional background
- Offers relevant tips and next steps

## ⚙️ Configuration

### Main Configuration (`config.yaml`)
```yaml
# AI Provider
ai_provider:
  type: "azure_openai"  # or "google_gemini"

# Audio Settings
audio:
  sample_rate: 16000
  processing_interval_seconds: 1.6
  silence_threshold_seconds: 30

# UI Settings
ui:
  overlay:
    width: 350
    height: 200
    position: "top_right"
    auto_hide_seconds: 5

# Hotkeys
hotkeys:
  trigger_assistance: "ctrl+space"
  toggle_overlay: "ctrl+b"
```

### User Profile (`data/resume.md`)
- Supports markdown format
- Automatically extracts education, skills, experience
- Updates AI responses with personalized context

### Topic Graph (`data/topic_graph.txt`)
- Define topic hierarchies and relationships
- Add custom suggestions for each topic
- Format: `Parent -> Child (suggestion: "Your suggestion")`

## 🏗️ Architecture

### Core Components
- **ConfigManager**: YAML configuration with environment variable support
- **UserProfileManager**: Resume parsing and profile management
- **TopicGraphManager**: Topic matching and suggestion system
- **AIHelper**: Multi-provider AI integration with streaming
- **AudioContextualizer**: Continuous audio processing with Whisper
- **ScreenCapture**: Cross-platform screen and window analysis
- **HotkeyManager**: Global hotkey handling with async support

### UI Implementations
- **EnhancedOverlay** (`main.py`): Full-featured PyQt5 interface with advanced graphics
- **WebviewOverlay** (`main_lightweight.py`): Lightweight web-based UI using native OS webviews

### Data Flow
1. **Audio Capture** → Whisper transcription → Topic matching
2. **Screen Analysis** → Context detection → Application identification
3. **Profile Integration** → Skill matching → Personalized prompts
4. **AI Processing** → Streaming responses → Overlay display

## 🔧 Advanced Configuration

### Custom AI Providers
Extend `ai/ai_helper.py` to add new AI providers:
```python
elif self.config.type == "custom_provider":
    # Your custom implementation
```

#### OpenAI
```yaml
ai_provider:
  type: "openai"
  openai:
    api_key: "your-openai-api-key"
    model: "gpt-4"
```

#### Google Gemini
```yaml
ai_provider:
  type: "google_gemini"
  google_gemini:
    api_key: "your-gemini-api-key"
    model: "gemini-2.0-flash"
```

## 🏗️ Architecture

```
meetminder/
├── main.py              # Application entry point
├── config.yaml          # Main configuration file
├── requirements.txt     # Python dependencies
├── core/                # Core configuration management
├── ai/                  # AI provider integrations
├── audio/               # Audio processing and transcription
├── ui/                  # User interface components
├── utils/               # Utilities and hotkey management
└── data/                # User data and knowledge graphs
```

## 🎯 Use Cases

### Meeting Assistant
- Real-time transcription of meeting audio
- Topic analysis and conversation flow tracking
- AI-powered meeting insights and action items

### Content Creation
- Transcribe videos, podcasts, or live streams
- Generate summaries and key points
- Context-aware AI assistance while creating content

### Learning & Research
- Capture and analyze educational content
- Real-time Q&A assistance
- Topic-based knowledge organization

## 🛠️ Development

### Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Code Structure

- **Core Components**: Configuration, AI providers, audio processing
- **UI Components**: Modern PyQt5 interface with transparency effects
- **Audio Pipeline**: Real-time audio capture → transcription → AI analysis
- **Settings Management**: Tabbed settings dialog with live updates

## 📋 Requirements

### System Requirements
- **OS**: Windows 10/11, macOS 10.14+, Linux (Ubuntu 18.04+)
- **Python**: 3.8 or higher
- **Memory**: 4GB RAM minimum, 8GB recommended
- **Audio**: Microphone and speaker access

### Python Dependencies

#### Standard Version (`requirements.txt`)
Full-featured UI with PyQt5 (~150MB build size):
- `PyQt5` - Advanced user interface with transparency effects
- `openai-whisper` - Local speech recognition
- `openai` - OpenAI API integration
- `google-generativeai` - Google Gemini integration
- `pyaudio` - Audio capture
- `pyyaml` - Configuration management

#### Lightweight Version (`requirements_lightweight.txt`) ⭐ **RECOMMENDED**
Web-based UI with pywebview (~15-30MB build size):
- `pywebview` - Lightweight native OS webviews
- `openai-whisper` - Local speech recognition
- `openai` - OpenAI API integration
- `google-generativeai` - Google Gemini integration
- `sounddevice` - Audio capture (lighter than pyaudio)
- `pyyaml` - Configuration management

**Size Comparison**: Lightweight version is 80-90% smaller while maintaining all core functionality!

## 🔒 Privacy & Security

- **Local Processing**: Audio transcription can run entirely locally with Whisper
- **No Data Storage**: Audio is processed in real-time, not permanently stored
- **API Security**: All API keys stored in local configuration files
- **Transparency**: Full source code available for security review

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support & Issues

- **Website**: [https://meetminder.io/](https://meetminder.io/)
- **Issues**: [GitHub Issues](https://github.com/mojtaba217/meetminder/issues)
- **Discussions**: [GitHub Discussions](https://github.com/mojtaba217/meetminder/discussions)
- **Wiki**: [Documentation Wiki](https://github.com/mojtaba217/meetminder/wiki)

## 🙏 Acknowledgments

- [OpenAI Whisper](https://github.com/openai/whisper) for speech recognition
- [PyQt5](https://riverbankcomputing.com/software/pyqt/) for the user interface
- All AI providers for their APIs and services

---

**Visit [MeetMinder.io](https://meetminder.io/) for more information and updates.**

**Note**: This software requires API keys from AI providers for full functionality. Local-only operation is available with Whisper transcription only. 