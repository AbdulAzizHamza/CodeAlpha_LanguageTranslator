"""
==================================================
 LANGUAGE TRANSLATION TOOL
 CodeAlpha AI Internship - Task 1
==================================================

WHAT THIS PROGRAM DOES:
1. Shows a window (a "GUI" - Graphical User Interface) with a box
   where you can type text.
2. Lets you pick a "source" language (the language you're typing in)
   and a "target" language (the language you want it translated to).
3. Sends your text to Google Translate (through a free Python library
   called deep-translator) and shows the translated result.
4. Has a "Copy" button to copy the translation, and a "Speak" button
   that reads the translation out loud.

HOW TO RUN THIS FILE:
1. Install the required libraries (only needs to be done once):
       pip install -r requirements.txt
2. Run the program:
       python translator_app.py
"""

# ------------------------------------------------------------------
# STEP 1: IMPORTS
# "Importing" means bringing in ready-made code that other people
# wrote, so we don't have to build everything from scratch.
# ------------------------------------------------------------------

import tkinter as tk
# tkinter is Python's built-in library for building windows, buttons,
# text boxes, etc. We give it the short nickname "tk" so we can type
# less code later (tk.Something instead of tkinter.Something).

from tkinter import ttk, messagebox
# ttk = "themed tkinter" - gives us nicer-looking, modern versions of
#       buttons, dropdown menus, etc.
# messagebox = lets us pop up small alert/info windows (e.g. errors).

from deep_translator import GoogleTranslator
# One way we can reach Google Translate (a BACKUP method - see the
# "translation engine" section below for why).

from deep_translator.exceptions import TooManyRequests as DeepTranslatorRateLimited
# deep-translator raises its OWN "too many requests" error (a
# different class from the one we define below for our direct
# request). We need to recognize both kinds as "this was a rate
# limit" - see translate_text below.

import requests
# Lets Python make direct web requests. We use this to call a second,
# more reliable free Google Translate endpoint (see below).

import pyttsx3
# This library converts written text into spoken audio (text-to-speech)
# and plays it through your computer's speakers. It works offline.

import subprocess
# Lets us start a brand new, separate Python process. We use this for
# the "speak" feature - see the TEXT-TO-SPEECH section below for why.

import sys
# sys.executable tells us the exact path to the Python program that
# is currently running US. We need that to launch the new process
# above using the SAME Python (and the same installed libraries).

import langdetect
# Offline language detector (no internet needed). Used as a backup
# when Google's own detection is unreachable, so the MyMemory
# fallback can still translate when Google has rate-limited us.
from langdetect import detect as _local_detect
from langdetect.lang_detect_exception import LangDetectException

# langdetect is non-deterministic by default (same text can detect
# differently each run). Seeding it makes results repeatable.
langdetect.DetectorFactory.seed = 0

# ------------------------------------------------------------------
# STEP 2: DATA - the list of languages the user can choose from
# ------------------------------------------------------------------
# A "dictionary" in Python is a way to store pairs of information.
# Here, each language NAME (what the user sees) is paired with the
# short CODE that Google Translate actually needs (e.g. "en" for
# English). This is exactly the kind of list you would use to fill
# a dropdown menu in the interface.

LANGUAGES = {
    "Detect Language (auto)": "auto",
    "Arabic": "ar",
    "English": "en",
    "French": "fr",
    "Spanish": "es",
    "German": "de",
    "Italian": "it",
    "Portuguese": "pt",
    "Russian": "ru",
    "Turkish": "tr",
    "Hindi": "hi",
    "Urdu": "ur",
    "Chinese (Simplified)": "zh-CN",
    "Japanese": "ja",
    "Korean": "ko",
    "Dutch": "nl",
    "Greek": "el",
    "Hebrew": "iw",
    "Polish": "pl",
    "Swedish": "sv",
    "Indonesian": "id",
    "Persian (Farsi)": "fa",
    "Vietnamese": "vi",
    "Thai": "th",
    "Swahili": "sw",
}
# NOTE: "Detect Language" is ONLY valid as a SOURCE language (it
# tells Google "figure out the language yourself"). It can never be
# a TARGET language, because you must tell Google what to translate
# INTO. We'll make sure the target dropdown never offers that option.

# Flips our LANGUAGES dictionary so we can show a friendly name for
# a code Google detected (e.g. "it" -> "Italian"). Lowercased keys so
# "zh-CN" matches Google's "zh-CN". Codes we don't list (e.g. "cs"
# for Czech) simply fall back to showing the raw code.
CODE_TO_LANGUAGE = {
    code.lower(): name
    for name, code in LANGUAGES.items()
    if code != "auto"
}


# ------------------------------------------------------------------
# STEP 3: TEXT-TO-SPEECH
# ------------------------------------------------------------------
# We do a quick "can this computer speak at all?" check once, when
# the program opens, and remember the answer in TTS_AVAILABLE. We
# wrap it in a try/except block because on some computers (mostly
# Linux without extra system software installed) starting the speech
# engine can fail - and we don't want the WHOLE app to crash just
# because the "speak" feature can't start.
#
# NOTE ON WHY EACH CLICK STARTS A WHOLE NEW PROCESS:
# pyttsx3 quietly keeps a cached copy of the speech engine inside
# your program - so even code that LOOKS like it's making a fresh
# engine each time can secretly get handed back the same broken one,
# which is why the button worked once and then went silent. The only
# fully reliable fix is to hand each click its own brand new Python
# process (subprocess.Popen below): a new process always starts with
# a completely clean slate, no matter what pyttsx3 is caching
# internally, and it doesn't freeze the window while it talks either.

try:
    _startup_engine = pyttsx3.init()
    _startup_engine.stop()
    TTS_AVAILABLE = True
except Exception:
    TTS_AVAILABLE = False

# This tiny script is what actually runs inside that new process. It
# just initializes its own speech engine and speaks whatever text it
# was given as a command-line argument (sys.argv[1]).
_SPEAK_SCRIPT = (
    "import pyttsx3, sys\n"
    "engine = pyttsx3.init()\n"
    "engine.say(sys.argv[1])\n"
    "engine.runAndWait()\n"
)


def speak_text(text):
    """Speaks the given text by launching a fresh helper process."""
    if not TTS_AVAILABLE:
        messagebox.showinfo(
            "Not available",
            "Text-to-speech isn't available on this computer."
        )
        return
    if not text.strip():
        # .strip() removes empty spaces from the start/end of text.
        # If there's nothing to speak, say so instead of doing nothing
        # silently (that's what made it look "broken" before).
        messagebox.showinfo(
            "Nothing to speak",
            "Translate some text first, then press Speak."
        )
        return
    try:
        # sys.executable = "use the same Python that's running this
        # app" (so the new process can find pyttsx3 too). Popen starts
        # it and immediately moves on - we don't wait around for it
        # to finish talking, so the window never freezes.
        subprocess.Popen([sys.executable, "-c", _SPEAK_SCRIPT, text])
    except Exception as error:
        messagebox.showerror("Speech error", str(error))


import time
# Lets us briefly pause between retries when Google is rate-limiting
# us (see RateLimited / translate_text below).

# ------------------------------------------------------------------
# STEP 3.5: THE TRANSLATION ENGINE
# ------------------------------------------------------------------
# Google Translate's free "web page" endpoint (the one the
# deep-translator library uses by default) sometimes answers with
# "HTTP 429 - Too Many Requests", even on your very first try. That's
# Google rate-limiting that specific page, not a bug in our code.
#
# The fix: we talk directly to the same endpoint Google's own
# translation widgets use ("translate_a/single"). It isn't rate-
# limited the same way, and - unlike some other free endpoints -
# it properly supports "auto" as a source language, so Detect
# Language actually works.
#
# Every free Google Translate route shares the SAME underlying
# limit: about 5 requests per second, ~200k per day, per internet
# connection. If you've been clicking Translate a lot in a short
# time (e.g. while testing), you can genuinely run into that limit -
# it's Google, not a bug. So if we get rate-limited, we wait a
# couple of seconds and try once more before giving up, and only
# fall back to deep-translator for problems that AREN'T a rate
# limit (retrying a rate limit on a different route rarely helps,
# since it's usually the same underlying limit).

GOOGLE_TRANSLATE_URL = "https://translate.googleapis.com/translate_a/single"
BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)


class RateLimited(Exception):
    """Raised when Google is temporarily rate-limiting our requests."""
    pass


def _extract_translated_text(payload):
    """
    Parse the JSON that Google's translate_a/single endpoint returns.
    It looks like: [[["Hola","Hello",None,None,1], [...]], ...]
    Google sometimes splits long text into several of those inner
    [translated, original, ...] groups (one per sentence), so we
    join all of them together to get the FULL translation back.
    """
    try:
        sentence_groups = payload[0]
        return "".join(group[0] for group in sentence_groups if group and group[0])
    except (TypeError, IndexError, KeyError):
        raise ValueError("Unexpected translation response from Google.")


def google_web_translate(text, source_code, target_code):
    """
    Translate text by calling Google Translate's own endpoint directly.

    Returns a tuple: (translated_text, detected_code). The detected
    code (e.g. "it") is only filled in when we asked Google to detect
    the language (source_code == "auto"); otherwise it is None.
    """
    params = {
        "client": "gtx",   # the same client id Google's own translate widget uses
        "sl": source_code,  # source language - "auto" is fully supported here
        "tl": target_code,
        "dt": "t",          # "dt=t" means "give me the translated text"
        "q": text,
    }
    headers = {
        "User-Agent": BROWSER_USER_AGENT,
        "Accept": "*/*",
    }
    response = requests.get(
        GOOGLE_TRANSLATE_URL,
        params=params,
        headers=headers,
        timeout=20,
    )
    if response.status_code == 429:
        raise RateLimited("Google is temporarily rate-limiting requests.")
    if response.status_code != 200:
        raise RuntimeError(f"Google Translate returned HTTP {response.status_code}.")
    payload = response.json()
    translated = _extract_translated_text(payload)

    # When we asked Google to detect (sl=auto), the code it picked
    # (e.g. "it") is the third item of the response.
    detected_code = None
    if source_code == "auto" and len(payload) > 2:
        detected_code = payload[2]

    return translated, detected_code


def detect_language_code(text, target_code):
    """
    Ask Google to detect the language of `text` and return its code
    (e.g. "it"). Uses the same endpoint as google_web_translate: with
    sl=auto, the JSON response's item [2] is the detected code.
    Only called when we need a concrete code for MyMemory, so the
    normal Google path costs no extra request.
    """
    params = {
        "client": "gtx",
        "sl": "auto",       # ask Google to detect
        "tl": target_code,
        "dt": "t",
        "q": text,
    }
    headers = {"User-Agent": BROWSER_USER_AGENT, "Accept": "*/*"}
    response = requests.get(
        GOOGLE_TRANSLATE_URL, params=params, headers=headers, timeout=20
    )
    if response.status_code == 429:
        raise RateLimited("Google is temporarily rate-limiting requests.")
    if response.status_code != 200:
        raise RuntimeError(f"Google Translate returned HTTP {response.status_code}.")
    payload = response.json()
    # The detected code is the third element of the top-level array.
    if len(payload) <= 2 or not isinstance(payload[2], str) or not payload[2]:
        raise ValueError("Google did not return a detected language.")
    return payload[2]

def get_detected_code(text, target_code):
    """
    Figure out the language of `text` with a concrete code, trying
    Google's detection first and an OFFLINE detector second - so
    language detection (and therefore the MyMemory fallback) keeps
    working even when Google has rate-limited this connection.
    """
    try:
        return detect_language_code(text, target_code)
    except Exception:
        try:
            return _local_detect(text).lower()
        except LangDetectException:
            raise RuntimeError("Could not detect the source language.")

# Google still uses a few old ISO codes that MyMemory rejects,
# so we map them to the modern ones before sending langpair.
MYMEMORY_ALIASES = {
    "iw": "he",      # Hebrew (old code)
    "in": "id",      # Indonesian (old code)
    "ji": "yi",      # Yiddish (old code)
    "zh-cn": "zh-CN",  # langdetect lowercase -> MyMemory regional style
    "zh-tw": "zh-TW",
}


def normalize_mymemory_code(code):
    return MYMEMORY_ALIASES.get(code.lower(), code)


def mymemory_translate(text, source_code, target_code):
    """
    Translate text using MyMemory's own API directly (NOT through
    deep-translator's MyMemoryTranslator wrapper - that wrapper
    insists on region-tagged codes like "en-US" instead of plain
    "en", and rejects almost every plain code we use in this app
    before it even sends a request. MyMemory's actual API is happy
    with plain codes like "en|fr", so we just call it ourselves.

    NOTE: MyMemory does NOT support "auto" as a source language, and
    it reports errors as HTTP 200 with an error message INSIDE the
    JSON body (responseStatus != "200") - so we must check that body,
    or an error like "'AUTO' IS AN INVALID SOURCE LANGUAGE" would be
    mistaken for a translation. The caller handles auto-detection by
    passing a concrete code from detect_language_code() instead.
    """
    params = {
        "q": text,
        "langpair": f"{normalize_mymemory_code(source_code)}|{normalize_mymemory_code(target_code)}",
    }
    response = requests.get(
        "https://api.mymemory.translated.net/get",
        params=params,
        timeout=20,
    )
    if response.status_code == 429:
        raise RateLimited("MyMemory is temporarily rate-limiting requests.")
    if response.status_code != 200:
        raise RuntimeError(f"MyMemory returned HTTP {response.status_code}.")
    data = response.json()

    # MyMemory reports errors as HTTP 200 with responseStatus != 200
    # in the JSON body (e.g. an invalid langpair like auto|it).
    if str(data.get("responseStatus")) != "200":
        raise RuntimeError(
            data.get("responseDetails") or "MyMemory rejected the request."
        )

    translated = data.get("responseData", {}).get("translatedText")
    if not translated:
        raise ValueError("Unexpected response from MyMemory.")
    return translated


def translate_text(text, source_code, target_code):
    """
    Tries up to three different ways to translate the text, in order,
    and returns whichever one works first as a tuple:
        (translated_text, detected_code)
    where detected_code is the source language Google detected (only
    filled in when the user picked "Detect Language"; None otherwise):
      1. A direct request to Google Translate (fast, usually works;
         retried once if Google briefly rate-limits us).
      2. The deep-translator library reaching Google a different way,
         in case only the first route is having trouble.
      3. MyMemory - a translation service from a completely different
         company, unrelated to Google. MyMemory can't detect languages
         itself, so when the source is "auto" we first ask Google for
         the detected code, then hand MyMemory that concrete language.
         This is what saves the day if Google itself is temporarily
         blocking this internet connection: every Google route fails
         together in that case, but MyMemory is a different company
         entirely, so it keeps working.
    """
    last_error = None
    hit_rate_limit = False   # tracks whether ANY attempt was a rate limit,
                              # even if a later, different-shaped error
                              # ends up being the very last one we saw

    # --- Google, direct request (with one retry if rate-limited) ---
    for attempt in range(2):
        try:
            return google_web_translate(text, source_code, target_code)
        except RateLimited as error:
            last_error = error
            hit_rate_limit = True
            if attempt == 0:
                time.sleep(2)   # brief pause, then try again
                continue
        except Exception as error:
            last_error = error
            break   # not a rate limit - no point retrying the same way

    # --- Google, via deep-translator (a different route to Google) ---
    try:
        translated = GoogleTranslator(source=source_code, target=target_code).translate(text)
        detected_code = None
        if source_code == "auto":
            try:
                detected_code = get_detected_code(text, target_code)
            except Exception:
                pass   # translation worked; detection is just a bonus
        return translated, detected_code
    except DeepTranslatorRateLimited as error:
        last_error = error
        hit_rate_limit = True
    except Exception as error:
        last_error = error

    # --- MyMemory (not Google at all - our last resort) ---
    mymemory_source = source_code

    if source_code == "auto":
        # MyMemory has no auto-detect, so get a concrete code from
        # Google first. If even detection fails, Google is the problem
        # and MyMemory can't help - report the original error.
        try:
            mymemory_source = get_detected_code(text, target_code)
        except Exception:
            if hit_rate_limit:
                raise RuntimeError(
                    "Google is limiting how many free translations can be "
                    "made from this internet connection right now - try "
                    "again later."
                )
            raise last_error

    try:
        translated = mymemory_translate(text, mymemory_source, target_code)
        return translated, (mymemory_source if source_code == "auto" else None)
    except Exception:
        pass   # we'll report the more useful error captured above

    if hit_rate_limit:
        # Give a clear, friendly explanation instead of a scary
        # wall of text - Google can keep blocking a connection for a
        # while after a lot of testing, well beyond a minute or two.
        raise RuntimeError(
            "Google is limiting how many free translations can be made "
            "from this internet connection right now. This can last "
            "longer than a few minutes after heavy testing - try again "
            "later, or from a different connection (like your phone's "
            "mobile data) to check."
        )
    raise last_error


# ------------------------------------------------------------------
# STEP 4: THE MAIN LOGIC - what happens when you click "Translate"
# ------------------------------------------------------------------

def do_translate():
    """Reads the input box, translates it, and shows the result."""

    # .get("1.0", tk.END) reads ALL the text inside a Text box,
    # starting from line 1, character 0, to the very end.
    user_text = input_box.get("1.0", tk.END).strip()

    if user_text == "":
        messagebox.showwarning("Nothing to translate", "Please type some text first.")
        return

    # source_combo.get() returns the LANGUAGE NAME currently selected
    # in the dropdown (e.g. "Arabic"). We use our LANGUAGES dictionary
    # to convert that into the short CODE Google needs (e.g. "ar").
    # If "Detect Language (auto)" is selected, this becomes "auto" -
    # Google's own translate endpoint (see google_web_translate below)
    # understands "auto" directly and detects the language itself,
    # far more reliably than we could guess it ourselves from a short
    # bit of text.
    source_code = LANGUAGES[source_combo.get()]
    target_code = LANGUAGES[target_combo.get()]

    status_label.config(text="Translating...", foreground="blue")
    root.update_idletasks()  # forces the label above to redraw right now

    try:
        translated, detected_code = translate_text(user_text, source_code, target_code)
    except Exception as error:
        # If anything goes wrong (e.g. no internet connection), we
        # show a friendly error message instead of crashing.
        status_label.config(text="Translation failed.", foreground="red")
        messagebox.showerror("Translation error", str(error))
        return

    # The output box is normally "disabled" (read-only) so the user
    # can't accidentally type in it. We briefly turn it back on so we
    # can update the text, then disable it again.
    output_box.config(state="normal")
    output_box.delete("1.0", tk.END)      # clear whatever was there before
    output_box.insert(tk.END, translated)  # insert the new translated text
    output_box.config(state="disabled")

    # If we asked Google to detect the language, show which one it
    # picked, using a friendly name from our list when we have one
    # (e.g. "it" -> "Italian"; an unknown code just shows as-is).
    if source_code == "auto" and detected_code:
        language_name = CODE_TO_LANGUAGE.get(detected_code.lower(), detected_code)
        status_label.config(
            text=f"Done! Detected: {language_name}", foreground="green"
        )
    else:
        status_label.config(text="Done!", foreground="green")


def copy_translation():
    """Copies the translated text in the output box to the clipboard."""
    text = output_box.get("1.0", tk.END).strip()
    if text == "":
        return
    root.clipboard_clear()     # empty whatever was previously copied
    root.clipboard_append(text)  # put our translated text there instead
    status_label.config(text="Copied to clipboard!", foreground="green")


def speak_translation():
    """Speaks the translated text out loud."""
    text = output_box.get("1.0", tk.END).strip()
    speak_text(text)


def swap_languages():
    """Swaps the source and target language selections."""
    source_name = source_combo.get()
    target_name = target_combo.get()

    # "Detect Language" is not a valid target, so we only swap if the
    # target is not currently set to that (it never should be, but we
    # play it safe).
    if source_name == "Detect Language (auto)":
        messagebox.showinfo(
            "Can't swap",
            "Pick a specific source language first (not 'Detect Language')."
        )
        return

    source_combo.set(target_name)
    target_combo.set(source_name)


# ------------------------------------------------------------------
# STEP 5: BUILD THE WINDOW (the actual visual interface)
# ------------------------------------------------------------------

root = tk.Tk()                       # create the main application window
root.title("Language Translator")    # text shown in the window's title bar
root.geometry("640x560")             # starting size: 640 pixels wide, 560 tall
root.minsize(560, 500)               # don't let the window get too small

# A "Frame" is just an invisible container used to group and organize
# other widgets (like a box that holds other boxes). Using frames with
# some padding makes the layout look neat instead of everything being
# jammed against the window edges.
main_frame = ttk.Frame(root, padding=15)
main_frame.pack(fill="both", expand=True)

# ---- Title text at the top ----
title_label = ttk.Label(
    main_frame, text="🌍 Language Translator", font=("Segoe UI", 18, "bold")
)
title_label.pack(pady=(0, 10))

# ---- Input text box ----
ttk.Label(main_frame, text="Enter text:", font=("Segoe UI", 10, "bold")).pack(anchor="w")

input_frame = ttk.Frame(main_frame)
input_frame.pack(fill="both", expand=True, pady=(2, 10))

input_box = tk.Text(input_frame, height=6, wrap="word", font=("Segoe UI", 11))
input_scroll = ttk.Scrollbar(input_frame, command=input_box.yview)
input_box.configure(yscrollcommand=input_scroll.set)
input_box.pack(side="left", fill="both", expand=True)
input_scroll.pack(side="right", fill="y")

# ---- Language selection row (source -> swap -> target) ----
lang_frame = ttk.Frame(main_frame)
lang_frame.pack(fill="x", pady=5)

ttk.Label(lang_frame, text="From:").grid(row=0, column=0, padx=(0, 5))
source_combo = ttk.Combobox(
    lang_frame, values=list(LANGUAGES.keys()), state="readonly", width=22
)
source_combo.set("Detect Language (auto)")   # default starting value
source_combo.grid(row=0, column=1, padx=5)

swap_button = ttk.Button(lang_frame, text="⇄", width=3, command=swap_languages)
swap_button.grid(row=0, column=2, padx=5)

ttk.Label(lang_frame, text="To:").grid(row=0, column=3, padx=(10, 5))
target_combo = ttk.Combobox(
    lang_frame,
    values=[name for name in LANGUAGES if name != "Detect Language (auto)"],
    state="readonly",
    width=22,
)
target_combo.set("English")   # default starting value
target_combo.grid(row=0, column=4, padx=5)

# ---- Translate button ----
translate_button = ttk.Button(main_frame, text="Translate", command=do_translate)
translate_button.pack(pady=10)

# ---- Output text box ----
ttk.Label(main_frame, text="Translation:", font=("Segoe UI", 10, "bold")).pack(anchor="w")

output_frame = ttk.Frame(main_frame)
output_frame.pack(fill="both", expand=True, pady=(2, 10))

output_box = tk.Text(
    output_frame, height=6, wrap="word", font=("Segoe UI", 11), state="disabled"
)
output_scroll = ttk.Scrollbar(output_frame, command=output_box.yview)
output_box.configure(yscrollcommand=output_scroll.set)
output_box.pack(side="left", fill="both", expand=True)
output_scroll.pack(side="right", fill="y")

# ---- Copy & Speak buttons ----
action_frame = ttk.Frame(main_frame)
action_frame.pack(fill="x")

copy_button = ttk.Button(action_frame, text="📋 Copy", command=copy_translation)
copy_button.pack(side="left", padx=(0, 5))

speak_button = ttk.Button(action_frame, text="🔊 Speak", command=speak_translation)
speak_button.pack(side="left")

# ---- Status label (shows "Translating...", "Done!", errors, etc.) ----
status_label = ttk.Label(main_frame, text="", font=("Segoe UI", 9))
status_label.pack(anchor="w", pady=(8, 0))


# ------------------------------------------------------------------
# STEP 6: START THE PROGRAM
# ------------------------------------------------------------------
# This line tells tkinter "now actually show the window and keep it
# open, watching for clicks and key presses". Nothing after this line
# will run until the window is closed - so it always goes LAST.
root.mainloop()
