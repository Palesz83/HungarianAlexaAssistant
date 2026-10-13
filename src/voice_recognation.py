import re

import sounddevice as sd
import speech_recognition as sr
import torch

from TTS.api import TTS
from num2words import num2words

from command_definition import engine
from ollama_interpreter import interpret


# =========================================================
# BEÁLLÍTÁSOK
# =========================================================

DEVICE_NAME = "Aleksza"

device = "cuda" if torch.cuda.is_available() else "cpu"

print("Available device:", device)


# =========================================================
# TTS
# =========================================================

tts = TTS(
    model_name="tts_models/hu/css10/vits"
).to(device)


sd.default.samplerate = 22050


# =========================================================
# INDULÓ HANGOK
# =========================================================

wav = tts.tts(
    text=DEVICE_NAME +
    " vagyok, egy virtuális asszisztens."
)

wait = tts.tts(
    text="Máris mondom"
)


# =========================================================
# INDULÁS
# =========================================================

sd.play(
    wav,
    blocking=True
)


# =========================================================
# SZÁM -> MAGYAR SZÖVEG
# =========================================================

def number_to_word(input_string):
    if not input_string:
        return ""

    # Új regex: keresünk számjegyeket, amik után opcionálisan követhet egy
    # pont vagy vessző, és újabb számjegyek.
    # \d+ : egy vagy több számjegy
    # (?:[.,]\d+)? : egy nem-csoportos csoport, ami opcionális (?),
    #                és tartalmaz egy pontot/vesszőt [.,] és számjegyeket \d+
    pattern = r"\d+(?:[.,]\d+)?"

    def replacer(match):
        full_number = match.group(0)

        # Megnézzük, van-e a számban tizedes elválasztó
        if '.' in full_number or ',' in full_number:
            # Szétválasztjuk a tizedes részt az elválasztótól (pont vagy vessző)
            # re.split használata, hogy mindkét karaktert kezelje
            parts = reerca_split_parts(full_number)

            whole_part = int(parts[0])
            fractional_part = int(parts[1])

            return f"{num2words(whole_part, lang='hu')} egész {num2words(fractional_part, lang='hu')}"
        else:
            # Ha sima egész szám
            return num2words(int(full_number), lang="hu")

    # Segédfüggvény a részek szétválasztására
    def reerca_split_parts(s):
        # A pontot vagy vesszőt replaced-eljük, hogy könnyebb legyen splitelni
        return re.split(r'[.,]', s)

    return re.sub(
        pattern,
        replacer,
        input_string
    )


# =========================================================
# TTS
# =========================================================

def speech_something(
    string_to_say
):

    if not string_to_say:
        return

    converted = (
        number_to_word(
            string_to_say
        )
    )

    tts_wav = tts.tts(
        text=converted
    )

    sd.play(
        tts_wav,
        blocking=True
    )


# =========================================================
# CHAT HISTORY
# =========================================================

def save_chat_turn(
    user_text,
    assistant_text
):

    """
    A normál beszélgetési előzményt az
    ollama_interpreter.py kezeli.

    Itt nincs külön history lista,
    hogy ne legyen két külön memória.
    """

    return


# =========================================================
# JÁTÉK HISTORY
# =========================================================

def save_game_turn(
    user_text,
    assistant_text
):

    if not engine.game_active:
        return

    engine.add_game_turn(
        user_text,
        assistant_text
    )


# =========================================================
# PARANCS FELDOLGOZÁS
# =========================================================

def handle_result(
    user_text,
    result
):

    if not result:

        speech_something(
            "Nem sikerült értelmeznem."
        )

        return

    action = result.get(
        "action"
    )

    response = result.get(
        "response",
        ""
    )

    print(
        "\n[ACTION]",
        action
    )

    # =====================================================
    # CHAT
    # =====================================================

    if action == "chat":

        if response:

            speech_something(
                response
            )

        return

    # =====================================================
    # WEB SEARCH
    # =====================================================

    if action == "web_search":

        if response:

            speech_something(
                response
            )

        return

    # =====================================================
    # GAME START
    # =====================================================

    if action == "game_start":

        game_name = result.get(
            "game"
        )

        if not game_name:

            speech_something(
                "Nem tudom, melyik játékot szeretnéd."
            )

            return

        # Az interpreter normál esetben már
        # elindította a játékot.
        #
        # Biztonsági ellenőrzésként csak akkor
        # indítjuk el, ha még nincs aktív játék.

        if not engine.game_active:

            engine.start_game(
                game_name
            )

        if response:

            speech_something(
                response
            )

        return

    # =====================================================
    # GAME TURN
    # =====================================================

    if action == "game_turn":

        if not engine.game_active:

            speech_something(
                "Jelenleg nincs aktív játék."
            )

            return

        if response:

            speech_something(
                response
            )

        return

    # =====================================================
    # GAME END
    # =====================================================

    if action == "game_end":

        if response:

            speech_something(
                response
            )

        if engine.game_active:

            engine.stop_game()

        return

    # =====================================================
    # TIMER / COMMAND
    # =====================================================

    if action in [
        "set_timer",
        "stop_timer",
        "play",
        "get_time"
    ]:

        tool_response = (
            engine.process_command(
                result
            )
        )

        if tool_response:

            speech_something(
                tool_response
            )

        return

    # =====================================================
    # ISMERETLEN
    # =====================================================

    speech_something(
        "Ezt most nem értettem."
    )


# =========================================================
# VOICE PROCESS
# =========================================================

r = sr.Recognizer()


def voice_process():

    with sr.Microphone() as source:

        r.energy_threshold = 300

        r.dynamic_energy_threshold = False

        print(
            "\n🎤 Mondj valamit!"
        )

        try:

            audio = r.listen(
                source,
                phrase_time_limit=4,
                timeout=4
            )

        except sr.WaitTimeoutError:

            print(
                "[VOICE] Nem érkezett beszéd."
            )

            return

        sd.play(
            wait,
            blocking=True
        )

        print(
            "Processing..."
        )

    try:

        # =================================================
        # WHISPER
        # =================================================

        input_string = r.recognize_whisper(
            audio,
            language="hu",
            model="small"
        )

        input_string = input_string.strip()

        print(
            "\nYou said:",
            input_string
        )

        if not input_string:

            return

        # =================================================
        # OLLAMA
        # =================================================

        print(
            "\nSending to Ollama..."
        )

        # Az új interpret() csak user_text-et vár.
        #
        # A beszélgetési history-t és az aktív játék
        # állapotát már az ollama_interpreter.py kezeli.

        result = interpret(
            input_string
        )

        # =================================================
        # RESULT
        # =================================================

        handle_result(
            input_string,
            result
        )

    except sr.UnknownValueError:

        print(
            DEVICE_NAME +
            " could not understand audio"
        )

    except sr.RequestError as e:

        print(
            "Speech recognition error:",
            e
        )

    except Exception as e:

        print(
            "[VOICE ERROR]",
            type(e).__name__,
            e
        )