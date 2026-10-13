import re

import requests
import sounddevice as sd
import speech_recognition as sr
import torch
from TTS.api import TTS
from num2words import num2words

import command_definition as com_def
from command_definition import engine

# from tools_call import tools_calling

OLLAMA_URL = "http://localhost:11434/api/generate"
# OLLAMA_MODEL = "llama3.2"  # <-- ide a saját modelled neve
# OLLAMA_MODEL = "gemma4:26b"
OLLAMA_MODEL = "gemma3:4b"
device = "cuda" if torch.cuda.is_available() else "cpu"

print("Avalibale device: " + device)

DEVICE_NAME = "Aleksza"
print(TTS().list_models())

tts = TTS(model_name="tts_models/hu/css10/vits").to(device)

wav = tts.tts(text=DEVICE_NAME + " vagyok, egy virtuális aszisztens.")
wait = tts.tts(text="Máris mondom ")
thinking = tts.tts(text="Ezen még gondolkodom")
need_time = tts.tts(text="Kis időt kérek még")

sd.default.samplerate = 22050
sd.play(wav, blocking=True)

conversation_history = []

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


def ask_ollama(user_text):
    system_prompt = """
                        Te  """ + DEVICE_NAME + """ vagy, egy magyar nyelvű lokális személyi asszisztens.
                        
                        Mindig magyarul válaszolj.
                        
                        a válaszodat egy text-to-speech rendszer fogja felolvasni.
                        
                        Ne használj markdown formázást.
                        Ne használj felsorolást, ha nem szükséges.
                        Ne írj hosszú magyarázatokat.
                        A felhasználóval közvetlenül beszélgetsz.
                        Minimum 2 szavas mondatokban válaszolj!
                        Az input egy speech to text modulból jön, ezért lehetnek benne "félrehallások" és tűnhet elgépelésnek, 
                        ezért a legvalószínűbb választ próbáld megadni. 
                        """

    # Az előzményekből felépítjük a promptot
    prompt = system_prompt + com_def.getSystemToolPrompt() + "\n\n"

    for message in conversation_history:
        if message["role"] == "user":
            prompt += "Felhasználó: " + message["content"] + "\n"
        elif message["role"] == "assistant":
            prompt += DEVICE_NAME + ": " + message["content"] + "\n"

    # Aktuális kérdés
    prompt += "Felhasználó: " + user_text + "\n"
    prompt += DEVICE_NAME + ":"

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "keep_alive": "1h",
        "think": False
    }

    response = requests.post(
        OLLAMA_URL,
        json=payload,
        timeout=240
    )

    response.raise_for_status()

    data = response.json()
    answer = data["response"].strip()

    # Aktuális kérdés-válasz eltárolása
    add_to_memory(user_text, answer)

    return answer


def speech_something(string_to_say):
    tts_wav = tts.tts(text=string_to_say)
    sd.default.samplerate = 22050
    sd.play(tts_wav, blocking=True)


r = sr.Recognizer()
m = sr.Microphone()
MAX_TURNS = 10


def add_to_memory(user_text, assistant_text):
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
        del conversation_history[:-max_messages]


def voice_process():
    # tool_response = engine.process_string_2("{10}{IDOZITO}")
    # if tool_response is not None:
    #     converted_str = szamokat_beture_magyarul(tool_response)
    # speech_something(converted_str)

    with sr.Microphone() as source:

        r.energy_threshold = 300
        r.dynamic_energy_threshold = False

        print("Say something!")

        audio = r.listen(
            source,
            phrase_time_limit=4,
            timeout=4
        )

        sd.default.samplerate = 22050
        sd.play(wait, blocking=True)

        print("Processing...")

    try:

        input_string = r.recognize_whisper(
            audio,
            language="hu",
            model="small"
        )

        print("You said:", input_string)

        # --------------------------------
        # OLLAMA
        # --------------------------------

        print("Sending to LLM...")

        response = ask_ollama(input_string)

        print(DEVICE_NAME + ":", response)

        tool_response = engine.process_string_2(response)

        if tool_response is not None:

            converted_str = number_to_word(tool_response)
        else:

            converted_str =number_to_word(response)

        speech_something(converted_str)


    except sr.UnknownValueError:

        print(DEVICE_NAME + " could not understand audio")

    except sr.RequestError as e:

        print(
            f"Could not request results from {DEVICE_NAME}; {e}"
        )
