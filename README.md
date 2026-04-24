# Simple Translator

Simple translator using the Claude API. This application allows you to translate text entered manually, pasted from the clipboard, or loaded from the clipboard at startup, then copy the translated text back to the clipboard.

## Requirements

- Python 3
- Tkinter
- Claude API key

## Installation

1. Create and activate a virtual environment (recommended).
   Windows:
   ```
   python -m venv venv
   venv\Scripts\activate
   ```

   macOS/Linux:
   ```
   python3 -m venv venv
   source venv/bin/activate
   ```

2. Install the dependencies.
   ```
   pip install -r requirements.txt
   ```

3. Create a `.env` file and set the Anthropic API key.
   ```
   ANTHROPIC_API_KEY=your_api_key_here
   ```

## Usage

1. Launch the application.
   ```
   python main.py
   ```

   To load text from the clipboard at startup, launch it with:
   ```
   python main.py --load-clipboard
   ```

2. Load text from the clipboard with the "Paste" button or enter it manually.

3. Select the target language for translation.

4. Click the "Translate" button.

5. Copy the translated result to the clipboard.

## Supported Languages

- Japanese
- English

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
