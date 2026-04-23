import tkinter as tk
from tkinter import ttk, messagebox
import pyperclip
import anthropic
from dotenv import load_dotenv
import os
import threading

load_dotenv()

MODEL_NAMES = ["claude-opus-4-7", "claude-sonnet-4-6", "claude-haiku-4-5"]
DEFAULT_MODEL = "claude-haiku-4-5"
MAX_TOKENS = 2048

LANGUAGE_PROMPTS = {
    "Japanese": "Japanese",
    "English": "English",
}


class ClipboardTranslatorApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Clipboard Translator")

        self._build_ui()

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            messagebox.showerror(
                "API Key Missing",
                "Anthropic API key not found. Please set ANTHROPIC_API_KEY in your .env file.",
            )
            root.destroy()
            return
        self.client = anthropic.Anthropic(api_key=api_key)

        self._load_clipboard()

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

        # --- Translate button ---
        self.translate_btn = tk.Button(
            toolbar,
            text="Translate",
            command=self._on_translate,
            bg="#264ABF",
            fg="white",
            relief="flat",
            cursor="hand2",
            width=12,
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
        self.status_var.set("Connecting to Claude API...")
        self._set_result("")

        thread = threading.Thread(target=self._translate, args=(source,), daemon=True)
        thread.start()

    def _translate(self, source: str):
        """Call Claude API and stream the result (runs in background thread)."""
        target_lang = LANGUAGE_PROMPTS[self.lang_var.get()]
        prompt = (
            f"Translate the following text into {target_lang}. "
            f"Output only the translated text, nothing else.\n\n{source}"
        )

        try:
            with self.client.messages.stream(
                model=self.model_var.get(),
                max_tokens=MAX_TOKENS,
                messages=[{"role": "user", "content": prompt}],
            ) as stream:
                self.root.after(0, lambda: self.status_var.set("Translating..."))
                for text_chunk in stream.text_stream:
                    self.root.after(0, self._append_result, text_chunk)

            self.root.after(0, self._on_translate_done)

        except anthropic.AuthenticationError:
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
                lambda: messagebox.showerror(
                    "Error",
                    f"An error occurred while translating:\n{e}"
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

def main():
    root = tk.Tk()
    root.minsize(400, 240)
    ClipboardTranslatorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
