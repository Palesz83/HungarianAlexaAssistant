import re
import requests
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

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "gemma3:4b"

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
# NORMÁL CHAT HISTORY
# =========================================================

conversation_history = []

MAX_TURNS = 10


def add_to_memory(
    user_text,
    assistant_text
):
    """
    Csak a normál beszélgetést tároljuk itt.

    A játék saját history-val rendelkezik.
    """

    conversation_history.append({
        "role": "user",
        "content": user_text
    })

    conversation_history.append({
        "role": "assistant",
        "content": assistant_text
    })

    max_messages = MAX_TURNS * 2

    if len(conversation_history) > max_messages:

        del conversation_history[
            :-max_messages
        ]


# =========================================================
# SZÁM -> MAGYAR SZÖVEG
# =========================================================

def szamokat_beture_magyarul(szoveg):

    if not szoveg:
        return ""

    pattern = r"\d+"

    def replacer(match):

        number = int(
            match.group(0)
        )

        return num2words(
            number,
            lang="hu"
        )

    return re.sub(
        pattern,
        replacer,
        szoveg
    )


# =========================================================
# TTS
# =========================================================

def speech_something(
    string_to_say
):

    if not string_to_say:
        return

    tts_wav = tts.tts(
        text=string_to_say
    )

    # sd.default.samplerate = 22050

    sd.play(
        tts_wav,
        blocking=True
    )


# =========================================================
# NORMÁL CHAT HISTORY KEZELÉSE
# =========================================================

def save_chat_turn(
    user_text,
    assistant_text
):

    if not assistant_text:
        return

    add_to_memory(
        user_text,
        assistant_text
    )


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
        "response"
    )

    print("\n[ACTION]", action)

    # =====================================================
    # CHAT
    # =====================================================

    if action == "chat":

        if response:

            save_chat_turn(
                user_text,
                response
            )

            converted = (
                szamokat_beture_magyarul(
                    response
                )
            )

            speech_something(
                converted
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

        engine.start_game(
            game_name
        )

        if response:

            # A kezdő üzenetet is eltesszük
            # a játék előzményébe.
            save_game_turn(
                user_text,
                response
            )

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

            save_game_turn(
                user_text,
                response
            )

            speech_something(
                response
            )

        return

    # =====================================================
    # GAME END
    # =====================================================

    if action == "game_end":

        if response:

            save_game_turn(
                user_text,
                response
            )

            speech_something(
                response
            )

        engine.stop_game()

        return

    # =====================================================
    # NORMÁL COMMAND
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

            converted = (
                szamokat_beture_magyarul(
                    tool_response
                )
            )

            speech_something(
                converted
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

        print("\n🎤 Mondj valamit!")

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

        # sd.default.samplerate = 22050

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

        result = interpret(

            user_text=input_string,

            conversation_history=(
                conversation_history
            ),

            game_context=(
                engine.get_game_context()
            )
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