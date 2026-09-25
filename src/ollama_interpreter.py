import json
import requests


OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "gemma3:4b"


COMMAND_SYSTEM_PROMPT = """
Te Aleksza vagy, egy magyar nyelvű lokális személyi asszisztens.

A bemenet egy Whisper beszédfelismerő rendszerből érkező magyar szöveg.

A feladatod:

1. Értsd meg a felhasználó szándékát.
2. Válaszd ki a megfelelő action értéket.
3. Ha szükséges, töltsd ki a hozzá tartozó adatokat.
4. Chat esetén írd meg közvetlenül a választ a response mezőben.
5. Játék esetén kezeld a játék beszélgetését a megadott játékállapot alapján.

A JSON-on kívül SEMMIT ne írj.

--------------------------------------------------
POSSIBLE ACTIONS
--------------------------------------------------

set_timer
stop_timer
play
get_time
chat
game_start
game_turn
game_end

--------------------------------------------------
SET_TIMER
--------------------------------------------------

Ha a felhasználó időzítőt szeretne.

Példák:

"állíts be tíz perces időzítőt"

=> action: set_timer
=> duration_minutes: 10

"állíts be fél órás időzítőt"

=> duration_minutes: 30

"állíts be másfél órás időzítőt"

=> duration_minutes: 90

"állíts be két órás időzítőt"

=> duration_minutes: 120

Minden időt percben adj vissza.

--------------------------------------------------
STOP_TIMER
--------------------------------------------------

Példák:

"állítsd le az időzítőt"

"kapcsold ki az időzítőt"

"állítsd le"

--------------------------------------------------
PLAY
--------------------------------------------------

Példák:

"indítsd el"

"indítsd el a zenét"

"játssz zenét"

--------------------------------------------------
GET_TIME
--------------------------------------------------

Példák:

"mennyi az idő?"

"hány óra van?"

"most mennyi az idő?"

--------------------------------------------------
CHAT
--------------------------------------------------

Ha a felhasználó nem akar speciális műveletet,
hanem egyszerűen beszélgetni szeretne veled,
az action legyen:

chat

Ebben az esetben a response mezőbe írd a természetes magyar választ.
Legalább három szavas mondatokban válaszolj.

Példa:

chat_request:"Mi magyarország fővárosa?"
respons=>"Magyarország fővárosa budapest"

chat_request:"Mennyi egy töketlen fecske végsebessége?"
respons=>"Attól függ, európai vagy afrikai fecske"

Felhasználó:
"Hogy vagy?"

JSON:

{
    "action": "chat",
    "duration_minutes": null,
    "game": null,
    "response": "Jól vagyok, köszönöm! Miben segíthetek?",
    "game_data": null
}

--------------------------------------------------
GAME
--------------------------------------------------

Támogatott játék:

animal_guess

Ez egy olyan játék, amelyben a FELHASZNÁLÓ gondol egy állatra,
Aleksza pedig igen/nem kérdéseket tesz fel.

Ha a felhasználó játékot akar indítani:

action = game_start

game = animal_guess

response = egy rövid magyar mondat,
amely arra kéri a felhasználót,
hogy gondoljon egy állatra.

Példa:

{
    "action": "game_start",
    "duration_minutes": null,
    "game": "animal_guess",
    "response": "Gondolj egy állatra, de ne áruld el! Ha megvan, kezdjük.",
    "game_data": null
}

A játék közben:

action = game_turn

A response legyen a KÖVETKEZŐ kérdés.

A kérdés lehetőleg igen/nem kérdés legyen.

Példák:

"Az állatod emlős?"

"Az állatod tud repülni?"

"Az állatod nagyobb egy macskánál?"

"Az állatod vízben él?"

A kérdések legyenek változatosak és segítsék az állat leszűkítését.

A game_data mezőbe röviden írd le,
hogy milyen információt próbálsz megtudni.

Ha úgy gondolod, hogy már elég információd van
az állat kitalálásához,
használj game_end actiont.

Példa:

{
    "action": "game_end",
    "duration_minutes": null,
    "game": "animal_guess",
    "response": "Arra gondoltál, hogy egy delfin?",
    "game_data": {
        "guess": "delfin"
    }
}

--------------------------------------------------
FONTOS
--------------------------------------------------

A bemenet magyar.

A JSON mezőnevek és action értékek angolul legyenek.

A felhasználó beszédfelismerésből érkező szöveget ad,
ezért kisebb Whisper hibákat javíts ki fejben. 


Mindig csak érvényes JSON-t adj vissza.

Ne használj Markdownot.

Ne írj magyarázatot JSON-on kívül.
"""


COMMAND_SCHEMA = {
    "type": "object",

    "properties": {

        "action": {
            "type": "string",
            "enum": [
                "set_timer",
                "stop_timer",
                "play",
                "get_time",
                "chat",
                "game_start",
                "game_turn",
                "game_end"
            ]
        },

        "duration_minutes": {
            "type": [
                "integer",
                "null"
            ]
        },

        "game": {
            "type": [
                "string",
                "null"
            ]
        },

        "response": {
            "type": [
                "string",
                "null"
            ]
        },

        "game_data": {
            "type": [
                "object",
                "null"
            ]
        }
    },

    "required": [
        "action",
        "duration_minutes",
        "game",
        "response",
        "game_data"
    ],

    "additionalProperties": False
}


def interpret(user_text, conversation_history=None, game_context=None):
    """
    Egyetlen Ollama hívás.

    user_text:
        Az aktuális Whisper szöveg.

    conversation_history:
        Normál beszélgetés előzménye.

    game_context:
        Aktív játék állapota és előzménye.
    """

    if not user_text:
        return None

    conversation_history = conversation_history or []

    game_context = game_context or {
        "active": False,
        "game": None,
        "history": []
    }

    # ---------------------------------------------------------
    # KONVERZÁCIÓS KONTEXTUS
    # ---------------------------------------------------------

    context_text = ""

    if conversation_history:
        context_text += "\n\nNORMÁL BESZÉLGETÉS ELŐZMÉNYEI:\n"

        for message in conversation_history:
            role = message["role"]
            content = message["content"]

            if role == "user":
                context_text += f"Felhasználó: {content}\n"

            elif role == "assistant":
                context_text += f"Aleksza: {content}\n"

    # ---------------------------------------------------------
    # JÁTÉK KONTEXTUS
    # ---------------------------------------------------------

    if game_context.get("active"):

        context_text += "\n\nAKTÍV JÁTÉK:\n"

        context_text += (
            f"Játék: {game_context.get('game')}\n"
        )

        context_text += "\nJÁTÉK ELŐZMÉNYEI:\n"

        for message in game_context.get("history", []):

            role = message["role"]
            content = message["content"]

            if role == "user":
                context_text += f"Felhasználó: {content}\n"

            elif role == "assistant":
                context_text += f"Aleksza: {content}\n"

    # ---------------------------------------------------------
    # AKTUÁLIS INPUT
    # ---------------------------------------------------------

    prompt = (
        context_text
        + "\n\nAKTUÁLIS FELHASZNÁLÓI ÜZENET:\n"
        + user_text
    )

    payload = {
        "model": OLLAMA_MODEL,

        "system": COMMAND_SYSTEM_PROMPT,

        "prompt": prompt,

        "stream": False,

        "keep_alive": "1h",

        "think": False,

        "format": COMMAND_SCHEMA,

        "options": {
            "temperature": 0.2,
            "num_predict": 180,
            "num_ctx": 4096
        }
    }

    try:

        response = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=240
        )

        response.raise_for_status()

        data = response.json()

        raw = data.get("response", "").strip()

        print("\n[OLLAMA RAW]")
        print(raw)

        if not raw:
            return None

        command = json.loads(raw)

        print("\n[OLLAMA JSON]")
        print(json.dumps(
            command,
            ensure_ascii=False,
            indent=2
        ))

        return command

    except requests.RequestException as e:

        print("[OLLAMA ERROR]", e)

        return None

    except json.JSONDecodeError as e:

        print("[OLLAMA JSON ERROR]", e)

        return None