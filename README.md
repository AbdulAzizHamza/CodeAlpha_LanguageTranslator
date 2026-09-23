# Language Translator Tool (CodeAlpha - Task 1)

A simple desktop app, built with Python, that translates text between
languages. It has a text box for input, dropdown menus to pick the
source and target language, a "Translate" button, a "Copy" button,
and a "Speak" (text-to-speech) button.

## Files

| File | What it is |
|---|---|
| `translator_app.py` | The full program. Just run this. |
| `requirements.txt` | The libraries the program needs. |

## How to run it

**1. Make sure Python is installed** (Python 3.8 or newer).

**2. Install the libraries this project needs** by opening a
terminal/command prompt in this folder and running:

```bash
pip install -r requirements.txt
```

**3. Run the program:**

```bash
python translator_app.py
```

A window should pop up. Type some text, choose your languages, and
click **Translate**.

> **Note for Linux users only:** the "Speak" (text-to-speech) button
> needs a small system program called `espeak`. If the Speak button
> doesn't produce sound, install it with:
> `sudo apt install espeak`
> On Windows and macOS, text-to-speech works out of the box - no
> extra install needed.

You also need an internet connection, because the translation itself
is done by Google Translate over the web (through the free
`deep-translator` library - no API key or account required).

## How the translation works (in short)

The app tries up to three different, unrelated ways to translate
your text: a direct request to Google (which also handles "Detect
Language" itself - Google's own detection is far more reliable than
trying to guess the language locally, especially for short text), the
`deep-translator` library reaching Google a different way, and
finally MyMemory (a translation service from a different company
altogether, unrelated to Google). All are free and need no sign-up,
no billing account, and no API key.

If you ever see a "Translation error" popup, it's almost always
Google briefly (or not-so-briefly, after a lot of testing in one
day) rate-limiting free requests from your connection - not a bug.
The app already retries automatically and tries a non-Google service
as a backup. If it still fails:
- Wait a while (this can take longer than a few minutes after heavy
  testing) and try again.
- Try from a different internet connection (like your phone's mobile
  data) to check whether it's specific to this connection.
- If you're up against a deadline and this keeps happening, the only
  fully reliable option is Google's official (paid, but with a
  generous free monthly quota) Cloud Translation API, which needs a
  Google Cloud account, billing enabled, and an API key - more setup,
  but not subject to the same shared, unofficial rate limits.

## Submitting this for your CodeAlpha internship

Based on the task PDF, when you're ready to submit:
1. Create a GitHub repository named `CodeAlpha_LanguageTranslator` and
   upload `translator_app.py`, `requirements.txt`, and this README.
2. Record a short video showing the app running and post it on
   LinkedIn, tagging @CodeAlpha and including your GitHub repo link.
3. Submit through the submission form shared in your WhatsApp group.
