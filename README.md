# Clipboard Translator

Simple clipboard translator using the Anthropic API. This application allows you to translate text from the clipboard or manual input into a selected language and copy the translated text back to the clipboard.

## Requirements

- Windows (Linux/macOS are not supported)
- Python 3
- Anthropic API key

## Installation

1. Create and activate a virtual environment (recommended).
   Windows:
   ```
   python -m venv venv
   venv\Scripts\activate
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

2. Load text from the clipboard or enter it manually.

3. Select the target language for translation.

4. Click the "Translate" button.

5. Copy the translated result to the clipboard.

## Supported Languages

- Japanese
- English

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
