import argparse
import tkinter as tk
from tkinter import ttk, messagebox
import pyperclip
import anthropic
import openai
from dotenv import load_dotenv
import os
import sys
import threading
import tomllib

load_dotenv()

# Path to the TOML configuration file, resolved relative to this script so the
# app works regardless of the current working directory.
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.toml")

# Built-in defaults used when config.toml is missing, invalid, or incomplete.
DEFAULT_CONFIG = {
    "models": [
        "claude-opus-4-8",
        "claude-sonnet-4-6",
        "claude-haiku-4-5",
        "gpt-5.6",
        "gpt-5.6-terra",
        "gpt-5.6-luna",
    ],
    "default_model": "claude-haiku-4-5",
    "max_tokens": 2048,
    "max_tokens_options": [512, 1024, 2048, 4096, 8192],
    "languages": {
        "Japanese": "Japanese",
        "English": "English",
    },
}


def load_config(path: str = CONFIG_PATH) -> dict:
    """Load configuration from a TOML file, falling back to DEFAULT_CONFIG.

    Missing files or parse errors are reported to stderr and the built-in
    defaults are used instead. Any keys absent from the file are filled in from
    DEFAULT_CONFIG so callers always get a complete config.
    """
    config = {**DEFAULT_CONFIG}
    try:
        with open(path, "rb") as f:
            loaded = tomllib.load(f)
        config.update({k: v for k, v in loaded.items() if v})
    except FileNotFoundError:
        print(
            f"Config file not found at {path}; using default settings.",
            file=sys.stderr,
        )
    except tomllib.TOMLDecodeError as e:
        print(
            f"Failed to parse config file {path}: {e}; using default settings.",
            file=sys.stderr,
        )
    return config


_config = load_config()

MODEL_NAMES = _config["models"]
DEFAULT_MODEL = _config["default_model"]
MAX_TOKENS = _config["max_tokens"]
MAX_TOKENS_OPTIONS = _config["max_tokens_options"]
LANGUAGE_PROMPTS = _config["languages"]

# Environment variable holding the API key for each supported provider.
PROVIDER_KEY_ENV = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
}


def infer_provider(model_id: str) -> str:
    """Map a model id to its API provider by prefix.

    Unknown prefixes default to Anthropic so that custom model ids typed into
    the (editable) model combobox behave as they did before OpenAI support.
    """
    if model_id.startswith("gpt-"):
        return "openai"
    return "anthropic"


class MissingAPIKeyError(Exception):
    """Raised when translating with a model whose provider key is not set."""


class SimpleTranslatorApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Simple Translator")

        self._build_ui()

        # Provider name -> SDK client, created lazily on first use so the app
        # runs with only one of the provider keys configured.
        self._clients = {}
        if not any(os.getenv(env) for env in PROVIDER_KEY_ENV.values()):
            messagebox.showerror(
                "API Key Missing",
                "No API key found. Please set ANTHROPIC_API_KEY and/or "
                "OPENAI_API_KEY in your .env file.",
            )
            root.destroy()
            return

    def _get_client(self, provider: str):
        """Return (and lazily create) the SDK client for a provider."""
        if provider not in self._clients:
            env_var = PROVIDER_KEY_ENV[provider]
            api_key = os.getenv(env_var)
            if not api_key:
                raise MissingAPIKeyError(
                    f"{env_var} is not set. "
                    "Add it to your .env file to use this model."
                )
            if provider == "openai":
                self._clients[provider] = openai.OpenAI(api_key=api_key)
            else:
                self._clients[provider] = anthropic.Anthropic(api_key=api_key)
        return self._clients[provider]

    def _build_ui(self):
        top_frame = tk.Frame(self.root)
        top_frame.pack(fill="both", expand=True, padx=16, pady=8)

        # --- Toolbar ---
        toolbar = tk.Frame(top_frame)
        toolbar.pack(fill="x")

        # --- Language selector ---
        tk.Label(
            toolbar,
            text="Translate to:",
        ).pack(
            side="left",
        )
        default_lang = next(iter(LANGUAGE_PROMPTS.keys()))
        self.lang_var = tk.StringVar(value=default_lang)
        lang_menu = ttk.Combobox(
            toolbar,
            textvariable=self.lang_var,
            values=list(LANGUAGE_PROMPTS.keys()),
            state="readonly",
            width=12,
        )
        lang_menu.pack(side="left", padx=(4, 0))

        # --- Model selector ---
        tk.Label(
            toolbar,
            text="Model:",
        ).pack(
            side="left",
            padx=(4, 0),
        )
        self.model_var = tk.StringVar(value=DEFAULT_MODEL)
        model_menu = ttk.Combobox(
            toolbar,
            textvariable=self.model_var,
            values=MODEL_NAMES
        )
        model_menu.pack(side="left", padx=(4, 0))

        # --- Max tokens selector ---
        tk.Label(
            toolbar,
            text="Max Tokens:",
        ).pack(
            side="left",
            padx=(4, 0),
        )
        self.max_tokens_var = tk.IntVar(value=MAX_TOKENS)
        max_tokens_menu = ttk.Combobox(
            toolbar,
            textvariable=self.max_tokens_var,
            values=MAX_TOKENS_OPTIONS,
            width=8,
        )
        max_tokens_menu.pack(side="left", padx=(4, 0))

        # --- Translate button ---
        self.translate_btn = tk.Button(
            toolbar,
            text="Translate",
            command=self._on_translate,
            bg="#264ABF",
            fg="white",
            relief="flat",
            cursor="hand2",
            width=8,
        )
        self.translate_btn.pack(side="right")

        # --- Paned window ---
        pane = tk.PanedWindow(
            top_frame,
            orient='horizontal',
            sashwidth=4
        )
        pane.pack(fill="both", expand=True, pady=(8, 0))
        pane.bind(
            "<Configure>",
            lambda event: pane.sash_place(0, event.width // 2, 0),
        )

        # --- Source pane ---
        source_frame = tk.Frame(pane)
        source_header = tk.Frame(source_frame)
        source_header.pack(fill="x")
        tk.Label(
            source_header,
            text="Source Text",
        ).pack(
            side="left",
        )
        tk.Button(
            source_header,
            text="📋 Paste",
            command=self._load_clipboard,
            anchor="w",
        ).pack(
            side="right",
        )
        self.source_text = tk.Text(
            source_frame,
            wrap="word",
            width=40,
            height=6,
        )
        self.source_text.pack(
            fill="both",
            expand=True,
            pady=(8, 0),
        )
        pane.add(source_frame)

        # --- Result pane ---
        result_frame = tk.Frame(pane)
        result_header = tk.Frame(result_frame)
        result_header.pack(fill="x")
        tk.Label(
            result_header,
            text="Translation Result",
            anchor="w"
        ).pack(
            side="left",
        )
        tk.Button(
            result_header,
            text="📋 Copy",
            command=self._copy_result,
        ).pack(
            side="right",
        )
        self.result_text = tk.Text(
            result_frame,
            wrap="word",
            state="disabled",
            bg="#f5f5f5",
            width=40,
            height=6,
        )
        self.result_text.pack(
            fill="both",
            expand=True,
            pady=(8, 0),
        )
        pane.add(result_frame)

        # --- Status bar ---
        status_bar = tk.Frame(self.root, height=24)
        status_bar.pack(fill="x", side="bottom")
        status_bar.pack_propagate(False)
        self.status_var = tk.StringVar(value="Ready")
        tk.Label(
            status_bar,
            textvariable=self.status_var,
            anchor="w",
            fg="gray",
            font=("", 9),
        ).pack(fill="both", padx=16)

    def _load_clipboard(self):
        """Load text from clipboard into the source text area."""
        try:
            text = pyperclip.paste()
            self.source_text.delete("1.0", tk.END)
            self.source_text.insert("1.0", text)
            self.status_var.set("Loaded from clipboard")
        except Exception as e:
            self.status_var.set(f"Error loading clipboard: {e}")

    def _on_translate(self):
        """Start translation in a background thread."""
        source = self.source_text.get("1.0", tk.END).strip()
        if not source:
            messagebox.showwarning("Input Required", "No text to translate.")
            return

        self.translate_btn.config(state="disabled", text="Translating...")
        self.status_var.set("Connecting to API...")
        self._set_result("")

        thread = threading.Thread(target=self._translate, args=(source,), daemon=True)
        thread.start()

    def _stream_anthropic(self, client, model: str, max_tokens: int, prompt: str):
        """Yield text chunks from the Anthropic Messages streaming API."""
        with client.messages.stream(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            yield from stream.text_stream

    def _stream_openai(self, client, model: str, max_tokens: int, prompt: str):
        """Yield text chunks from the OpenAI Chat Completions streaming API."""
        stream = client.chat.completions.create(
            model=model,
            # GPT-5+ reasoning models reject the deprecated max_tokens param.
            max_completion_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
            stream=True,
        )
        for chunk in stream:
            # Skip role-only deltas, empty-choices chunks, and the final
            # chunk whose delta.content is None.
            if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def _translate(self, source: str):
        """Call the translation API and stream the result (runs in background thread)."""
        target_lang = LANGUAGE_PROMPTS[self.lang_var.get()]
        prompt = (
            f"Translate the following text into {target_lang}. "
            f"Output only the translated text, nothing else.\n\n{source}"
        )
        model = self.model_var.get()
        provider = infer_provider(model)

        try:
            client = self._get_client(provider)
            if provider == "openai":
                stream_fn = self._stream_openai
            else:
                stream_fn = self._stream_anthropic
            self.root.after(0, lambda: self.status_var.set("Translating..."))
            for text_chunk in stream_fn(
                client, model, self.max_tokens_var.get(), prompt
            ):
                self.root.after(0, self._append_result, text_chunk)

            self.root.after(0, self._on_translate_done)

        except MissingAPIKeyError as e:
            self.root.after(
                0,
                lambda msg=str(e): messagebox.showerror("API Key Missing", msg),
            )
            self.root.after(0, self._on_translate_done)
        except (anthropic.AuthenticationError, openai.AuthenticationError):
            self.root.after(
                0,
                lambda: messagebox.showerror(
                    "Authentication Error",
                    "API key is invalid. Please check your .env file."
                ),
            )
            self.root.after(0, self._on_translate_done)
        except Exception as e:
            self.root.after(
                0,
                lambda msg=str(e): messagebox.showerror(
                    "Error",
                    f"An error occurred while translating:\n{msg}"
                )
            )
            self.root.after(0, self._on_translate_done)

    def _set_result(self, text: str):
        self.result_text.config(state="normal")
        self.result_text.delete("1.0", tk.END)
        self.result_text.insert("1.0", text)
        self.result_text.config(state="disabled")

    def _append_result(self, chunk: str):
        self.result_text.config(state="normal")
        self.result_text.insert(tk.END, chunk)
        self.result_text.see(tk.END)
        self.result_text.config(state="disabled")

    def _on_translate_done(self):
        self.translate_btn.config(state="normal", text="Translate")
        self.status_var.set("Translation complete")

    def _copy_result(self):
        result = self.result_text.get("1.0", tk.END).strip()
        if not result:
            messagebox.showinfo("Copy", "No translation result available.")
            return
        pyperclip.copy(result)
        self.status_var.set("Result copied to clipboard")


def parse_args():
    parser = argparse.ArgumentParser(description="Simple Translator App")
    parser.add_argument(
        "--load-clipboard",
        action="store_true",
        help="Load text from clipboard on startup",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    root = tk.Tk()
    root.minsize(640, 240)
    app = SimpleTranslatorApp(root)
    if args.load_clipboard:
        app._load_clipboard()
    root.mainloop()


if __name__ == "__main__":
    main()
