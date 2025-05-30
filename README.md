# MeetMinder

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Website](https://img.shields.io/badge/website-meetminder.io-blue)](https://meetminder.io/)

A real-time AI meeting assistant with system audio transcription, intelligent topic analysis, and context-aware responses. Features a modern horizontal UI bar that stays at the top of your screen during meetings and calls.

## ✨ Features

- **🎙️ Real-time Audio Transcription**: Captures system audio (meetings, videos) with live transcript display
- **🤖 Multi-LLM Support**: OpenAI GPT, Azure OpenAI, Google Gemini integration
- **📊 Topic Analysis**: Intelligent conversation flow tracking and guidance
- **🖥️ Modern UI**: Horizontal bar interface with expandable content areas
- **⌨️ Global Hotkeys**: Instant AI assistance with customizable shortcuts
- **🔒 Privacy Focused**: Local audio processing with optional cloud AI
- **⚙️ Highly Configurable**: Extensive settings through YAML configuration

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- Windows 10/11, macOS, or Linux
- Microphone and speaker access

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/meetminder.git
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

- `Ctrl+Space` - Trigger AI assistance
- `Ctrl+B` - Toggle overlay visibility
- `Ctrl+H` - Take screenshot
- `Ctrl+Shift+R` - Emergency reset

### Settings

Access comprehensive settings through the ⚙️ button:

- **Audio Settings**: Configure transcription and recording
- **AI Settings**: Choose provider, model, and behavior
- **UI Settings**: Customize appearance and layout
- **Hotkeys**: Modify keyboard shortcuts
- **Prompts**: Edit AI behavior instructions
- **Knowledge Graph**: Manage topic understanding

## 🔧 Configuration

### Main Configuration File

All settings are managed through `config.yaml`:

```yaml
# AI Provider Configuration
ai_provider:
  type: "azure_openai"
  azure_openai:
    api_key: "your-key"
    endpoint: "your-endpoint"
    model: "gpt-4"

# Audio Processing
audio:
  mode: "dual_stream"  # microphone + system audio
  buffer_duration_minutes: 5
  processing_interval_seconds: 1.6

# User Interface
ui:
  overlay:
    size_multiplier: 1.0
    show_transcript: true
    auto_hide_seconds: 5

# Hotkeys
hotkeys:
  trigger_assistance: "ctrl+space"
  toggle_overlay: "ctrl+b"
```

### AI Providers

#### Azure OpenAI
```yaml
ai_provider:
  type: "azure_openai"
  azure_openai:
    api_key: "your-azure-openai-key"
    endpoint: "https://your-resource.openai.azure.com/"
    api_version: "2024-02-01"
    model: "gpt-4"
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
See `requirements.txt` for full list. Key dependencies:
- `PyQt5` - User interface
- `openai-whisper` - Local speech recognition
- `openai` - OpenAI API integration
- `google-generativeai` - Google Gemini integration
- `pyaudio` - Audio capture
- `pyyaml` - Configuration management

## 🔒 Privacy & Security

- **Local Processing**: Audio transcription can run entirely locally with Whisper
- **No Data Storage**: Audio is processed in real-time, not permanently stored
- **API Security**: All API keys stored in local configuration files
- **Transparency**: Full source code available for security review

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support & Issues

- **Website**: [https://meetminder.io/](https://meetminder.io/)
- **Issues**: [GitHub Issues](https://github.com/yourusername/meetminder/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/meetminder/discussions)
- **Wiki**: [Documentation Wiki](https://github.com/yourusername/meetminder/wiki)

## 🙏 Acknowledgments

- [OpenAI Whisper](https://github.com/openai/whisper) for speech recognition
- [PyQt5](https://riverbankcomputing.com/software/pyqt/) for the user interface
- All AI providers for their APIs and services

---

**Visit [MeetMinder.io](https://meetminder.io/) for more information and updates.**

**Note**: This software requires API keys from AI providers for full functionality. Local-only operation is available with Whisper transcription only. 