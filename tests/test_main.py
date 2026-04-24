"""Unit tests for main.py (SimpleTranslatorApp)."""

import sys
import unittest
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Mock GUI / external dependencies before importing main so that the module
# can be loaded in a headless / CI environment without a real display.
# ---------------------------------------------------------------------------

# tkinter – replaced with a MagicMock so every attribute access returns a
# further MagicMock (tk.END, tk.Tk, tk.Frame, …).
_tk_mock = MagicMock()
sys.modules["tkinter"] = _tk_mock
sys.modules["tkinter.ttk"] = MagicMock()
# "from tkinter import messagebox" resolves to sys.modules["tkinter.messagebox"]
_messagebox_mock = MagicMock()
sys.modules["tkinter.messagebox"] = _messagebox_mock

# pyperclip
_pyperclip_mock = MagicMock()
sys.modules["pyperclip"] = _pyperclip_mock

# anthropic – we need AuthenticationError to be a *real* exception class so
# that the `except anthropic.AuthenticationError:` clause in main.py works.
_anthropic_mock = MagicMock()
_anthropic_mock.AuthenticationError = type("AuthenticationError", (Exception,), {})
sys.modules["anthropic"] = _anthropic_mock

# python-dotenv (load_dotenv is called at module level)
sys.modules["dotenv"] = MagicMock()

# ---------------------------------------------------------------------------
# Now it is safe to import main
# ---------------------------------------------------------------------------
import main  # noqa: E402
from main import SimpleTranslatorApp, LANGUAGE_PROMPTS, DEFAULT_MODEL, MAX_TOKENS  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_app(api_key="test-api-key"):
    """Instantiate SimpleTranslatorApp with all side-effects mocked out.

    Returns ``(app, root_mock)``.  After construction the helper attaches
    MagicMock widgets to the instance so that method tests can exercise widget
    interactions without a real Tk hierarchy.
    """
    root = MagicMock()
    with (
        patch.object(SimpleTranslatorApp, "_build_ui"),
        patch.object(SimpleTranslatorApp, "_load_clipboard"),
        patch("os.getenv", return_value=api_key),
    ):
        app = SimpleTranslatorApp(root)

    # Attach mock widgets that methods under test interact with
    app.source_text = MagicMock()
    app.result_text = MagicMock()
    app.status_var = MagicMock()
    app.translate_btn = MagicMock()
    app.lang_var = MagicMock()
    app.lang_var.get.return_value = "Japanese"
    app.model_var = MagicMock()
    app.model_var.get.return_value = DEFAULT_MODEL
    app.client = MagicMock()
    return app, root


# ---------------------------------------------------------------------------
# Tests: module-level constants
# ---------------------------------------------------------------------------

class TestConstants(unittest.TestCase):
    def test_default_model(self):
        self.assertEqual(DEFAULT_MODEL, "claude-haiku-4-5")

    def test_max_tokens(self):
        self.assertEqual(MAX_TOKENS, 2048)

    def test_language_prompts_contains_japanese(self):
        self.assertIn("Japanese", LANGUAGE_PROMPTS)

    def test_language_prompts_contains_english(self):
        self.assertIn("English", LANGUAGE_PROMPTS)

    def test_language_prompts_values_are_non_empty_strings(self):
        for key, value in LANGUAGE_PROMPTS.items():
            with self.subTest(key=key):
                self.assertIsInstance(value, str)
                self.assertTrue(value)


# ---------------------------------------------------------------------------
# Tests: SimpleTranslatorApp
# ---------------------------------------------------------------------------

class TestInit(unittest.TestCase):
    def test_root_is_stored(self):
        app, root = _make_app()
        self.assertIs(app.root, root)

    def test_window_title_is_set(self):
        root = MagicMock()
        with (
            patch.object(SimpleTranslatorApp, "_build_ui"),
            patch.object(SimpleTranslatorApp, "_load_clipboard"),
            patch("os.getenv", return_value="key"),
        ):
            SimpleTranslatorApp(root)
        root.title.assert_called_once_with("Simple Translator")

    def test_missing_api_key_shows_error_and_destroys_root(self):
        root = MagicMock()
        with (
            patch.object(SimpleTranslatorApp, "_build_ui"),
            patch("os.getenv", return_value=None),
            patch.object(main, "messagebox") as mock_mb,
        ):
            SimpleTranslatorApp(root)
        mock_mb.showerror.assert_called_once()
        root.destroy.assert_called_once()

    def test_missing_api_key_does_not_create_client(self):
        root = MagicMock()
        with (
            patch.object(SimpleTranslatorApp, "_build_ui"),
            patch("os.getenv", return_value=None),
            patch.object(main, "messagebox"),
        ):
            app = SimpleTranslatorApp(root)
        self.assertFalse(hasattr(app, "client"))


class TestLoadClipboard(unittest.TestCase):
    def test_pastes_text_into_source_widget(self):
        app, _ = _make_app()
        with patch("main.pyperclip.paste", return_value="Hello World"):
            app._load_clipboard()
        app.source_text.delete.assert_called_with("1.0", main.tk.END)
        app.source_text.insert.assert_called_with("1.0", "Hello World")

    def test_updates_status_on_success(self):
        app, _ = _make_app()
        with patch("main.pyperclip.paste", return_value="text"):
            app._load_clipboard()
        app.status_var.set.assert_called_with("Loaded from clipboard")

    def test_updates_status_on_exception(self):
        app, _ = _make_app()
        with patch("main.pyperclip.paste", side_effect=Exception("no clipboard")):
            app._load_clipboard()
        app.status_var.set.assert_called_with("Error loading clipboard: no clipboard")


class TestOnTranslate(unittest.TestCase):
    def test_shows_warning_when_source_is_empty(self):
        app, _ = _make_app()
        app.source_text.get.return_value = "   "
        with patch.object(main, "messagebox") as mock_mb:
            app._on_translate()
        mock_mb.showwarning.assert_called_once()

    def test_does_not_start_thread_when_source_is_empty(self):
        app, _ = _make_app()
        app.source_text.get.return_value = ""
        with (
            patch.object(main, "messagebox"),
            patch("main.threading.Thread") as mock_thread,
        ):
            app._on_translate()
        mock_thread.assert_not_called()

    def test_disables_translate_button(self):
        app, _ = _make_app()
        app.source_text.get.return_value = "Bonjour"
        with patch("main.threading.Thread"):
            app._on_translate()
        app.translate_btn.config.assert_called_with(state="disabled", text="Translating...")

    def test_starts_daemon_thread(self):
        app, _ = _make_app()
        app.source_text.get.return_value = "Bonjour"
        with patch("main.threading.Thread") as mock_thread:
            instance = MagicMock()
            mock_thread.return_value = instance
            app._on_translate()
        _, kwargs = mock_thread.call_args
        self.assertTrue(kwargs.get("daemon"))
        instance.start.assert_called_once()


class TestTranslate(unittest.TestCase):
    def _stream_ctx(self, chunks):
        """Build a mock context-manager whose text_stream yields *chunks*."""
        ctx = MagicMock()
        ctx.__enter__ = MagicMock(return_value=ctx)
        ctx.__exit__ = MagicMock(return_value=False)
        ctx.text_stream = chunks
        return ctx

    def test_calls_api_with_correct_model_and_tokens(self):
        app, _ = _make_app()
        app.client.messages.stream.return_value = self._stream_ctx([])
        app._translate("hi")
        _, kwargs = app.client.messages.stream.call_args
        self.assertEqual(kwargs["model"], DEFAULT_MODEL)
        self.assertEqual(kwargs["max_tokens"], MAX_TOKENS)

    def test_prompt_contains_target_language_and_source(self):
        app, _ = _make_app()
        app.client.messages.stream.return_value = self._stream_ctx([])
        app._translate("Bonjour")
        _, kwargs = app.client.messages.stream.call_args
        content = kwargs["messages"][0]["content"]
        self.assertIn("Japanese", content)
        self.assertIn("Bonjour", content)

    def test_success_schedules_on_translate_done(self):
        app, root = _make_app()
        app.client.messages.stream.return_value = self._stream_ctx(["Hello", " World"])
        app._translate("Bonjour")
        scheduled_callbacks = [call.args[1] for call in root.after.call_args_list if len(call.args) > 1]
        self.assertIn(app._on_translate_done, scheduled_callbacks)

    def test_success_schedules_append_result_for_each_chunk(self):
        app, root = _make_app()
        chunks = ["chunk1", "chunk2", "chunk3"]
        app.client.messages.stream.return_value = self._stream_ctx(chunks)
        app._translate("text")
        append_calls = [
            call for call in root.after.call_args_list
            if len(call.args) > 1 and call.args[1] == app._append_result
        ]
        self.assertEqual(len(append_calls), len(chunks))

    def test_auth_error_schedules_on_translate_done(self):
        app, root = _make_app()
        app.client.messages.stream.side_effect = main.anthropic.AuthenticationError()
        app._translate("hi")
        scheduled_callbacks = [call.args[1] for call in root.after.call_args_list if len(call.args) > 1]
        self.assertIn(app._on_translate_done, scheduled_callbacks)

    def test_generic_error_schedules_on_translate_done(self):
        app, root = _make_app()
        app.client.messages.stream.side_effect = Exception("network failure")
        app._translate("hi")
        scheduled_callbacks = [call.args[1] for call in root.after.call_args_list if len(call.args) > 1]
        self.assertIn(app._on_translate_done, scheduled_callbacks)


class TestSetResult(unittest.TestCase):
    def test_enables_then_disables_widget(self):
        app, _ = _make_app()
        app._set_result("translated")
        calls = [str(c) for c in app.result_text.config.call_args_list]
        self.assertTrue(any("normal" in c for c in calls))
        self.assertTrue(any("disabled" in c for c in calls))

    def test_deletes_previous_content(self):
        app, _ = _make_app()
        app._set_result("new text")
        app.result_text.delete.assert_called_with("1.0", main.tk.END)

    def test_inserts_provided_text(self):
        app, _ = _make_app()
        app._set_result("translated text")
        app.result_text.insert.assert_called_with("1.0", "translated text")


class TestAppendResult(unittest.TestCase):
    def test_enables_then_disables_widget(self):
        app, _ = _make_app()
        app._append_result("chunk")
        calls = [str(c) for c in app.result_text.config.call_args_list]
        self.assertTrue(any("normal" in c for c in calls))
        self.assertTrue(any("disabled" in c for c in calls))

    def test_inserts_chunk_at_end(self):
        app, _ = _make_app()
        app._append_result("chunk")
        app.result_text.insert.assert_called_with(main.tk.END, "chunk")

    def test_scrolls_to_end(self):
        app, _ = _make_app()
        app._append_result("chunk")
        app.result_text.see.assert_called_with(main.tk.END)


class TestOnTranslateDone(unittest.TestCase):
    def test_re_enables_button_with_original_label(self):
        app, _ = _make_app()
        app._on_translate_done()
        app.translate_btn.config.assert_called_with(state="normal", text="Translate")

    def test_updates_status_to_complete(self):
        app, _ = _make_app()
        app._on_translate_done()
        app.status_var.set.assert_called_with("Translation complete")


class TestCopyResult(unittest.TestCase):
    def test_copies_result_to_clipboard(self):
        app, _ = _make_app()
        app.result_text.get.return_value = "Translated text"
        with patch("main.pyperclip.copy") as mock_copy:
            app._copy_result()
        mock_copy.assert_called_once_with("Translated text")

    def test_updates_status_after_copy(self):
        app, _ = _make_app()
        app.result_text.get.return_value = "Translated text"
        with patch("main.pyperclip.copy"):
            app._copy_result()
        app.status_var.set.assert_called_with("Result copied to clipboard")

    def test_shows_info_when_result_is_empty(self):
        app, _ = _make_app()
        app.result_text.get.return_value = "   "
        with patch.object(main, "messagebox") as mock_mb:
            app._copy_result()
        mock_mb.showinfo.assert_called_once()

    def test_does_not_copy_when_result_is_empty(self):
        app, _ = _make_app()
        app.result_text.get.return_value = ""
        with (
            patch.object(main, "messagebox"),
            patch("main.pyperclip.copy") as mock_copy,
        ):
            app._copy_result()
        mock_copy.assert_not_called()


class TestCliBehavior(unittest.TestCase):
    def test_parse_args_enables_startup_clipboard_loading(self):
        with patch.object(sys, "argv", ["main.py", "--load-clipboard"]):
            args = main.parse_args()
        self.assertTrue(args.load_clipboard)

    def test_main_loads_clipboard_when_flag_is_present(self):
        mock_app = MagicMock()
        with (
            patch.object(main, "parse_args", return_value=MagicMock(load_clipboard=True)),
            patch.object(main.tk, "Tk", return_value=MagicMock()) as mock_tk,
            patch.object(main, "SimpleTranslatorApp", return_value=mock_app),
        ):
            main.main()
        mock_tk.return_value.minsize.assert_called_once_with(400, 240)
        mock_app._load_clipboard.assert_called_once()
        mock_tk.return_value.mainloop.assert_called_once()

    def test_main_skips_clipboard_loading_without_flag(self):
        mock_app = MagicMock()
        with (
            patch.object(main, "parse_args", return_value=MagicMock(load_clipboard=False)),
            patch.object(main.tk, "Tk", return_value=MagicMock()) as mock_tk,
            patch.object(main, "SimpleTranslatorApp", return_value=mock_app),
        ):
            main.main()
        mock_app._load_clipboard.assert_not_called()
        mock_tk.return_value.mainloop.assert_called_once()


