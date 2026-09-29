import datetime
import threading
import time

import sounddevice as sd
import soundfile as sf

import command_interpreter as CommandEngine

# Importáljuk az engine-t (például ha külön fájlban vannak)
# from engine import CommandEngine
# from command_interpreter import CommandEngine

# Létrehozzuk az engine példányát, ami a regisztrációt vezérli
engine = CommandEngine.CommandEngine()
running_timers = []
wavefile, fs = sf.read('../src/resources/alert.wav')
sd.default.samplerate = 40000
alarm_active = False


#gyengébb LLM esetén trigger idozitore: "Az időzítőt állítsd öt percere":
SYSTEM_TOOLS_PROMPT = (


    "Felsoroltak alapján válaszolj a kérdésekere a következő értékekkel ***FONTOS*** A FOMRÁTUMRA FIGYELJ!:"
    "-Aktuális időpontra vontakozhat a kérdés a válasz legyen ez: '{IDO}'"
    "-Hogya vagy, vagy erre vonatkozó kérdés esetén a válasz legyen ez :'{HOGYVAGY}'"
    "-Köszönés, üdvözlés esetén a válasz: '{SZIA}'"
    "-Ha időzítés, időzítő beállítás esetén a válaszban szerepeljen az érték megfelelő számmal például: '{10}' legyen benne ez: '{IDOZITO}' például 50 perc esetén a válasz:'{50}{IDOZITO}' Ha nem tudod ezt a választ adni ne válaszolj!"
    "   Example: 'You said: Az időzítőt állítsd öt percere. Response: {5}{IDOZITO}'"
    "-Az időzítő leállítása esetén a válasz: '{STOP_IDOZITO}'"
)

def getSystemToolPrompt():
    return SYSTEM_TOOLS_PROMPT


def _play_alert_loop():
    """Ez a függvény most már egy ciklusban fut, amíg az alarm_active True."""
    global alarm_active
    print("\n\n[ALARM] 🔔 Idő lejárt! A csengő aktív! (Leállítást várok...)")

    # Amíg a stop parancs nem érkezik, addig loopolunk
    while alarm_active:
        sd.default.samplerate = 40000
        sd.play(wavefile, blocking=True)

        time.sleep(5)
        # A blocking=True azért jó, mert megvárja, amíg lejátszódik az egyik kör,
        # majd a következő kör előtt ellenőrzi a while feltételt.

    alarm_active = False
    print("\n[ALARM] 🛑 A csengő leállt.")


# ---------------------------------------------------------
# ITT LEHETŐ A PARANCSOK BEFORDÍTÁSA (A "TANKHENGÉR")
# ---------------------------------------------------------

@engine.register("{HOGYVAGY}")
def handle_hogy_vagy(parameter=None):
    return "Jól köszönöm!"


@engine.register("{IDO}")
def handle_time(parameter=None):
    now = datetime.datetime.now()
    return f"Az idő: {now.hour} óra, {now.minute} perc."


@engine.register("{SZIA}")
def handle_szia(parameter=None):
    return "Szia, én Aleksza vagyok az asszisztens!"


@engine.register("{IDOZITO}")
def handle_timer(time=None):
    global alarm_active
    if time is None:
        return "Nem értettem az időt."

    # Itt az idő módosítása percre (ahogy a kódodban volt: time * 60)
    seconds = int(time) *60 # Teszteléshez 60 helyett 6-ot tettem, hogy ne várj túl sokáig

    t = threading.Timer(seconds, _play_alert_loop)
    alarm_active = True
    # 2. MEZMÉMODIFIKÁCIÓ: Mentjük az időzítőt a listába!
    global running_timers
    running_timers.append(t)
    t.start()
    return "Rendben van! " + str(time) + " perc múlva szólok."


@engine.register("{STOP_IDOZITO}")
def handle_stop_timer(parameter=None):
    global running_timers
    global alarm_active

    # 1. MOST A LÉNYEG: Ha a csengő (alarm_active) fut, azt is leállítjuk!
    if alarm_active:
        alarm_active = False  # Ez kilépi a _play_alert_loop ciklusát
        msg = "A csengőt leállítottam!"
    else:
        # 2. Először leállítjuk a futó countdown (időző) folyamatokat
        if running_timers:
            for t in running_timers:
                t.cancel()
            running_timers.clear()
            msg = "Az időzítőket leállítottam. "
        else:
            msg = "Nincs futó időzítő vagy csengő."

    return msg

# Itt bármilyen új, bonyolultabb függvényt hozzáadhatsz könnyedén.
