# PCOR - Screenshot OCR Tool

A simple Windows desktop application for capturing screenshots and extracting text using AI vision models via Ollama.

## What It Does

PCOR lets you:
1. Select any area of your screen with a crosshair cursor
2. Automatically extract all text from that screenshot using AI
3. Copy the extracted text to your clipboard

Perfect for quickly grabbing text from images, PDFs, videos, or any on-screen content.

## Demo

1. Click the **+** button
2. Drag to select text on your screen  
3. Release - text is extracted automatically
4. Click "Copy Text" to copy to clipboard

## Features

- ✨ **Easy Screenshot Selection** - Crosshair cursor with click-and-drag
- 🤖 **AI-Powered OCR** - Uses MiniCPM-V vision model for accurate text extraction
- 📸 **Multi-Screenshot Mode** - Capture up to 3 screenshots before processing
- 📋 **One-Click Copy** - Instant clipboard copying
- 🎨 **Clean UI** - Simple, intuitive interface
- 💾 **No File Clutter** - Screenshots processed in memory only
- 🔄 **System Tray** - Minimize to tray for quick access

## Quick Start

### 1. Prerequisites

- **Windows 10+**
- **Python 3.7+** - [Download](https://python.org)
- **Ollama** - [Download](https://ollama.ai)

### 2. Install

```bash
# Clone this repo
git clone https://github.com/yourusername/pcor.git
cd pcor

# Run setup (creates venv, installs dependencies, pulls AI model)
setup.bat
```

### 3. Run

```bash
run.bat
```

## Usage

### Basic OCR
1. Click the green **+** button
2. Your screen will dim and cursor becomes a crosshair
3. Click and drag to select the text area
4. Release to capture
5. Text appears in the window automatically
6. Click "Copy Text" to copy

### Multi-Screenshot Mode
1. Enable "Multi Mode" checkbox
2. Capture up to 3 screenshots
3. Click "Send to OCR" to process all at once
4. Each screenshot's text is separated with dividers

### Keyboard Shortcuts
- **ESC** - Cancel screenshot selection
- **Ctrl+C** - Copy selected text from results

## How It Works

PCOR uses:
- **tkinter** for the GUI
- **Pillow** for image handling
- **Ollama** to run the MiniCPM-V vision model locally
- **pyperclip** for clipboard operations

The MiniCPM-V model is specifically trained for OCR tasks on:
- Text-heavy images (invoices, receipts, documents)
- Low contrast and handwritten text
- Multiple languages (English, Chinese, Japanese)

All processing happens **locally** on your machine - no cloud uploads.

## Configuration

Edit `config.json` to customize:

```json
{
  "model": {
    "name": "minicpm-v",
    "alternatives": ["minicpm-v:latest"]
  },
  "ocr": {
    "prompt": "Your custom OCR instructions"
  }
}
```

## Development

Built with Python and love. Contributions welcome!

### Project Structure
```
pcor/
├── pcor.py           # Main application
├── config.json       # Configuration
├── setup.bat         # One-time setup
├── run.bat          # Application launcher
└── requirements.txt  # Python dependencies
```

### Tech Stack
- **GUI**: tkinter (Python standard library)
- **OCR**: MiniCPM-V via Ollama
- **Image Processing**: Pillow
- **System Tray**: pystray

## Troubleshooting

### "Ollama not running"
Make sure Ollama is installed and running. It should auto-start.

### "Model not found"
Run: `ollama pull minicpm-v`

### Poor OCR accuracy?
- Capture larger screenshots
- Ensure good contrast between text and background
- Use clear, non-rotated text when possible

## Why MiniCPM-V?

Unlike general vision models that describe images, MiniCPM-V is optimized for OCR:
- Trained specifically on text-heavy documents
- Handles low contrast and handwriting
- Supports multiple languages and scripts
- Preserves text layout and formatting

## License

MIT License - Feel free to use and modify!

## Credits

Built by [Your Name]

Uses:
- [MiniCPM-V](https://github.com/OpenBMB/MiniCPM-V) for OCR
- [Ollama](https://ollama.ai) for running local AI models

## Support

Found a bug? Have a feature request? Open an issue!

---

Made with ❤️ for easy text extraction
