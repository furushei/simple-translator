# Simple Translator

Simple translator using the Claude and OpenAI APIs. This application allows you to translate text entered manually, pasted from the clipboard, or loaded from the clipboard at startup, then copy the translated text back to the clipboard.

## Requirements

- Python 3.11+ (uses the standard-library `tomllib` module)
- Tkinter
- Anthropic and/or OpenAI API key (at least one)

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

3. Create a `.env` file and set your API key(s). Only the key matching the
   models you use is required.
   ```
   ANTHROPIC_API_KEY=your_anthropic_api_key_here
   OPENAI_API_KEY=your_openai_api_key_here
   ```

## Configuration

The available models, default model, max-token options, and target languages
are defined in [`config.toml`](config.toml). Edit this file to change the
options shown in the app without modifying the source code:

```toml
default_model = "claude-haiku-4-5"
models = [
    "claude-opus-4-8",
    "claude-sonnet-4-6",
    "claude-haiku-4-5",
    "gpt-5.6",
    "gpt-5.6-terra",
    "gpt-5.6-luna",
]
max_tokens = 2048
max_tokens_options = [512, 1024, 2048, 4096, 8192]

[languages]
Japanese = "Japanese"
English = "English"
```

The API provider is inferred from the model id prefix: `claude-*` models use
the Anthropic API (`ANTHROPIC_API_KEY`) and `gpt-*` models use the OpenAI API
(`OPENAI_API_KEY`). `gpt-5.6` is an alias for `gpt-5.6-sol`.

Note: for GPT-5.6 models, the max-tokens budget also covers the model's
internal reasoning tokens, so a small value can leave no room for visible
output. A Max Tokens value of 2048 or higher is recommended for GPT models.

If `config.toml` is missing or invalid, the app falls back to its built-in
defaults. If you have customized `models` in an existing `config.toml`, add
the GPT model ids to your list to see them in the dropdown.

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
