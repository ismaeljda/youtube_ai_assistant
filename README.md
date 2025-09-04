# YouTube AI Assistant 🤖

An intelligent AI assistant that helps you understand YouTube video content in real-time. Ask questions about what you're watching and get contextualized answers based on the video transcript.

## ✨ Features

- **🎯 Contextual Questions**: Ask questions about the precise moment you're watching
- **🧠 Memory System**: The assistant remembers your previous conversations
- **🤖 Smart Multi-Agent System**: Advanced question analysis system with LangChain
- **⚡ Intuitive Interface**: Chrome extension integrated directly into YouTube
- **🔄 Real-time Analysis**: Analysis based on your current position in the video

## 🏗️ Project Architecture

```
youtube-ai-assistant/
├── app.py                              # Main Flask server
├── contextual_transcript_processor.py   # Transcript processing
├── memory_system.py                    # Conversational memory system
├── multi_agents.py                     # Multi-agent system with LangChain
├── requirements.txt                    # Python dependencies
├── .env                               # Environment variables (create this)
└── transcript_extension/              # Chrome extension
    ├── manifest.json                  # Extension manifest
    ├── content.js                     # Main extension script
    └── styles.css                     # Extension styling
```

## 🚀 Installation & Setup

### 1. Clone the Repository

```bash
git clone git@github.com:ismaeljda/youtube_ai_assistant.git
cd youtube-ai-assistant
```

### 2. Python Backend Setup

**Install Dependencies:**
```bash
pip install -r requirements.txt
```

**Create Environment File:**
Create a `.env` file in the root directory:

```env
OPENAI_API_KEY=your_openai_api_key_here
```

> ⚠️ **Important**: You must obtain an OpenAI API key from [OpenAI Platform](https://platform.openai.com/api-keys) and add it to your `.env` file.

**Start the Backend Server:**
```bash
python app.py
```

The server will start on `http://localhost:5000`

### 3. Chrome Extension Setup

**Load the Extension:**
1. Open Chrome and navigate to `chrome://extensions/`
2. Enable "Developer mode" (toggle in the top right)
3. Click "Load unpacked"
4. Select the `transcript_extension` folder
5. The extension should now appear in your extensions list

**Verify Installation:**
- Navigate to any YouTube video
- You should see a blue "🤖 Ask AI" button on the right side of the screen

## 📖 How to Use

1. **Open a YouTube Video**: Navigate to any YouTube video with available captions/transcript (only english video)
2. **Click the AI Button**: Click the blue "🤖 Ask AI" button that appears on the page
3. **Ask Questions**: Type questions about what you're currently watching
4. **Get Smart Answers**: The AI analyzes the video content and provides contextual responses

### Example Questions:
- "What is machine learning?" (when the video is discussing ML)
- "Can you explain what was just said about algorithms?"
- "Summarize the last 2 minutes"
- "What are the key points mentioned so far?"

## 🧠 System Components

### Backend Components

**1. Contextual Transcript Processor** (`contextual_transcript_processor.py`)
- Fetches YouTube video transcripts
- Creates contextual windows around the current playback time
- Provides prioritized context for better AI responses

**2. Memory System** (`memory_system.py`)
- Maintains conversation history per video session
- 30-minute session timeout
- Maximum 10 messages per session
- Automatic cleanup of expired sessions

**3. Multi-Agent System** (`multi_agents.py`)
- **Agent 1**: Question Analyzer - Analyzes the type and intent of user questions
- **Agent 2**: Response Generator - Creates optimized responses based on analysis
- Uses LangChain for advanced prompt engineering

**4. Flask API** (`app.py`)
- `/ask` - Main endpoint with memory (recommended)
- `/ask/simple` - Simple endpoint without memory
- `/conversation/clear/<video_id>` - Clear conversation history
- `/memory/stats` - Memory system statistics
- `/health` - System health check

### Frontend Component

**Chrome Extension** (`transcript_extension/`)
- Injects AI button into YouTube interface
- Provides chat interface for questions
- Handles video ID detection and current time tracking
- Communicates with backend API

## 🔧 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/ask` | POST | Ask question with memory |
| `/ask/simple` | POST | Ask question without memory |
| `/conversation/clear/<video_id>` | POST | Clear conversation history |
| `/conversation/history/<video_id>` | GET | Get conversation history |
| `/memory/stats` | GET | Memory system statistics |
| `/transcript/<video_id>` | GET | Get transcript information |
| `/health` | GET | System health status |

### Request Format for `/ask`:
```json
{
  "video_id": "SmZmBKc7Lrs",
  "current_time": 120.5,
  "question": "What is an algorithm?",
  "user_id": "browser_session"
}
```

## ⚙️ Configuration

### Environment Variables (.env)
```env
# Required
OPENAI_API_KEY=your_openai_api_key_here

# Optional (with defaults)
FLASK_ENV=development
FLASK_PORT=5000
```

### Memory System Settings
- **Session Timeout**: 30 minutes
- **Max Messages per Session**: 10
- **Auto-cleanup**: Expired sessions are automatically removed

## 🧪 Testing

### Test Backend System:
```bash
# Test basic transcript processing
python contextual_transcript_processor.py

# Test memory system
python memory_system.py

# Test multi-agent system
python multi_agents.py
```

### Test Extension:
1. Load the extension in Chrome
2. Navigate to a YouTube video
3. Check browser console for any errors
4. Test the AI button and chat interface

## 🐛 Troubleshooting

### Common Issues:

**1. "OPENAI_API_KEY not found"**
- Ensure you've created the `.env` file with your API key
- Restart the Flask server after adding the API key

**2. "Cannot fetch transcript"**
- Some videos don't have available transcripts
- Try with a different video that has captions

**3. Extension button not appearing**
- Refresh the YouTube page
- Check if the extension is properly loaded in `chrome://extensions/`
- Check browser console for JavaScript errors

**4. CORS errors**
- The Flask server includes CORS headers
- Ensure the backend is running on `localhost:5000`

## 📊 System Statistics

The system provides detailed statistics via the `/memory/stats` endpoint:
- Active conversation sessions
- Total messages processed
- Memory usage information
- Session cleanup reports

## 🔮 Future Enhancements

- Support for multiple languages
- Video summarization features
- Export conversation history
- Advanced analytics dashboard
- Integration with other video platforms

## 📝 Requirements

- **Python 3.8+**
- **OpenAI API Key** (paid account recommended for better rate limits)
- **Chrome Browser** (for extension)
- **Internet Connection** (for API calls)

**Need Help?** Check the troubleshooting section or open an issue in the repository.
