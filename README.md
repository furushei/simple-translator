# Simple Translator

Simple translator using the Claude API. This application allows you to translate text entered manually, pasted from the clipboard, or loaded from the clipboard at startup, then copy the translated text back to the clipboard.

## Requirements

- Python 3.11+ (uses the standard-library `tomllib` module)
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

## Configuration

The available models, default model, max-token options, and target languages
are defined in [`config.toml`](config.toml). Edit this file to change the
options shown in the app without modifying the source code:

```toml
default_model = "claude-haiku-4-5"
models = ["claude-opus-4-8", "claude-sonnet-4-6", "claude-haiku-4-5"]
max_tokens = 2048
max_tokens_options = [512, 1024, 2048, 4096, 8192]

[languages]
Japanese = "Japanese"
English = "English"
```

If `config.toml` is missing or invalid, the app falls back to its built-in
defaults.

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
