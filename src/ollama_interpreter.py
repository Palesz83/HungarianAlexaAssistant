import json
import requests

from wiki_search import (
    get_wiki_answer
)

from weather import (
    get_current_weather,
    format_weather_response
)

# =========================================================
# BEÁLLÍTÁSOK
# =========================================================

OLLAMA_URL = "http://localhost:11434/api/generate"

OLLAMA_MODEL = "gemma3:4b"
# OLLAMA_MODEL = "qwen2.5:1.5b"

REQUEST_TIMEOUT = 240

# =========================================================
# NORMÁL BESZÉLGETÉSI ELŐZMÉNY
# =========================================================

conversation_history = []

MAX_HISTORY_MESSAGES = 12

# =========================================================
# ELSŐ LLM PROMPT
# =========================================================

SYSTEM_PROMPT = """
You are the intent and action controller of a Hungarian voice assistant
called Aleksza.

The user speaks Hungarian.

IMPORTANT:
The speech recognition system may produce:
- missing accents
- spelling mistakes
- wrong words
- phonetic errors
- incomplete sentences

You must infer the user's intended meaning from context.

Your job is to classify the user's request into exactly ONE action.

Allowed actions:

- chat
- set_timer
- stop_timer
- play
- get_time
- wiki_search
- weather
- game_start
- game_turn
- game_end


ACTION RULES
------------

SPEECH INPUT SAFETY RULE:
The user input comes from Whisper speech recognition.
Whisper can make transcription mistakes, especially with names, numbers,
commands, and similar-sounding words.

IMPORTANT:
Never guess an action when the user's intention is unclear.

Use the conversation context to understand small speech-recognition errors,
but only when the intended meaning is obvious.

If the input can reasonably mean two or more different things, do NOT choose
an action based on guessing.

chat:
Normal conversation, greetings, casual requests, opinions, explanations,
or questions that do not require a special action.

Use chat for general knowledge questions when a Wikipedia search
would not be useful or necessary.

set_timer:
The user wants to start or set a countdown timer.

duration_minutes must contain the requested duration in whole minutes.

stop_timer:
The user wants to stop or cancel the timer or alarm.

play:
The user wants to start music or playback.

get_time:
The user asks for the current time.

wiki_search:
Use this when the user asks for factual information about a person,
place, historical event, scientific concept, animal, object, organization,
or other topic that can reasonably be answered from a Wikipedia article.

Examples:
- "Ki volt Albert Einstein?"
- "Mesélj Petőfi Sándorról."
- "Mi az a fekete lyuk?"
- "Mi volt a Római Birodalom?"
- "Hol található a Balaton?"
- "Mi az a fotoszintézis?"
- "Ki volt Mátyás király?"

For wiki_search:
response MUST contain a concise Wikipedia search query.

The query should contain the main subject of the request,
not the entire user sentence.

Examples:

User:
"Ki volt Albert Einstein?"

Query:
"Albert Einstein"

User:
"Mesélj a Római Birodalomról."

Query:
"Római Birodalom"

User:
"Mi az a fotoszintézis?"

Query:
"Fotoszintézis"

Do not include phrases such as:
"keress rá"
"wikipédia"
"mi az"
"mesélj"
"ki volt"

Only return the subject to search for.

weather:
Use this for weather-related requests.

Examples:
- "Milyen idő van Budapesten?"
- "Hány fok van Érden?"
- "Esik most?"
- "Milyen idő van Győrben?"
- "Mi az időjárás Budapesten?"

For weather:
location MUST contain the requested location.

IMPORTANT:
Do NOT use wiki_search for normal weather requests.
Do NOT use web search for weather.

If the user clearly names a Hungarian city, use its normal
Hungarian name.

Examples:
"Érd"
"Budapest"
"Győr"
"Szeged"

Do not translate Hungarian city names into another language.

If the user asks about weather but does not specify a location,
use location = null.

game_start:
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


game:
Contain the game name.

game_turn:
The user is making a move or continuing an active game.

game_end:
The user wants to stop or end the current game or if the animal has been successfully guessed.


RESPONSE RULE
------------

For chat:
response must contain the natural Hungarian response.

For set_timer, stop_timer, play and get_time:
response may contain a short Hungarian response.

For wiki_search:
response MUST contain ONLY the concise search query.

The Python application will perform the Wikipedia search
and generate the final spoken answer.

Do not generate a Wikipedia answer yourself.

For weather:
location MUST contain the location.
response can be empty or contain a short acknowledgement.

The Python application will retrieve the weather data
and generate the final spoken answer.

Do not generate weather information yourself.

For game actions:
response should contain the natural Hungarian response.

Always return valid JSON matching the supplied schema.
Do not output markdown.
Do not output explanations outside JSON.
"""

# =========================================================
# ELSŐ LLM SCHEMA
# =========================================================

ACTION_SCHEMA = {

    "type": "object",

    "properties": {

        "action": {
            "type": "string",

            "enum": [
                "chat",
                "set_timer",
                "stop_timer",
                "play",
                "get_time",
                "wiki_search",
                "weather",
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

        "location": {
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
        "location",
        "response",
        "game_data"
    ],

    "additionalProperties": False
}


# =========================================================
# OLLAMA HÍVÁS
# =========================================================

def call_ollama(
        system_prompt,
        user_prompt,
        schema
):
    payload = {

        "model": OLLAMA_MODEL,

        "prompt": user_prompt,

        "system": system_prompt,

        "stream": False,

        "format": schema,

        "options": {
            "temperature": 0.1
        }
    }

    try:

        response = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=REQUEST_TIMEOUT
        )

        response.raise_for_status()

        data = response.json()

    except requests.exceptions.Timeout:

        print(
            "[OLLAMA ERROR] "
            "A kérés időtúllépés miatt sikertelen."
        )

        return None

    except requests.exceptions.ConnectionError:

        print(
            "[OLLAMA ERROR] "
            "Nem sikerült kapcsolódni az Ollamához."
        )

        return None

    except requests.exceptions.RequestException as e:

        print(
            "[OLLAMA ERROR]",
            e
        )

        return None

    except ValueError:

        print(
            "[OLLAMA ERROR] "
            "Érvénytelen JSON válasz az Ollamától."
        )

        return None

    raw_response = data.get(
        "response",
        ""
    )

    if not raw_response:
        print(
            "[OLLAMA ERROR] "
            "Üres válasz érkezett."
        )

        return None

    print(
        "\n[OLLAMA RAW]"
    )

    print(
        raw_response
    )

    try:

        parsed = json.loads(
            raw_response
        )

    except json.JSONDecodeError as e:

        print(
            "[OLLAMA JSON ERROR]",
            e
        )

        return None

    print(
        "\n[OLLAMA JSON]"
    )

    print(
        json.dumps(
            parsed,
            ensure_ascii=False,
            indent=2
        )
    )

    return parsed


# =========================================================
# CHAT HISTORY
# =========================================================

def add_conversation_turn(
        user_text,
        assistant_text
):
    conversation_history.append({

        "role": "user",

        "content": user_text
    })

    conversation_history.append({

        "role": "assistant",

        "content": assistant_text
    })

    if len(
            conversation_history
    ) > MAX_HISTORY_MESSAGES:
        del conversation_history[
            :-MAX_HISTORY_MESSAGES
        ]


# =========================================================
# HISTORY FORMÁZÁSA
# =========================================================

def format_conversation_history():
    if not conversation_history:
        return (
            "Nincs korábbi beszélgetési előzmény."
        )

    lines = []

    for message in conversation_history:

        role = message.get(
            "role",
            ""
        )

        content = message.get(
            "content",
            ""
        )

        if role == "user":

            lines.append(
                f"Felhasználó: {content}"
            )

        elif role == "assistant":

            lines.append(
                f"Aleksza: {content}"
            )

    return "\n".join(
        lines
    )


# =========================================================
# ELSŐ PROMPT ÖSSZEÁLLÍTÁSA
# =========================================================

def build_interpretation_prompt(
        user_text
):
    history = (
        format_conversation_history()
    )

    prompt = f"""
Korábbi beszélgetés:

{history}

Mostani felhasználói üzenet:

{user_text}

Osztályozd a felhasználó kérését a megadott szabályok szerint.

Különösen figyelj arra, hogy:

- időjárási kérdés esetén weather actiont használj
- Wikipédia-szerű tényszerű kérdés esetén wiki_search actiont használj
- normál beszélgetés esetén chat actiont használj

Wikipédia-keresésnél a response mezőbe csak a keresendő témát írd.
"""

    return prompt


# =========================================================
# WIKIPÉDIA
# =========================================================

def perform_wiki_search(
        user_text,
        search_query
):
    print(
        "\n[WIKI QUERY]",
        search_query
    )

    if not search_query:
        return {

            "action": "chat",

            "duration_minutes": None,

            "game": None,

            "location": None,

            "response": (
                "Nem sikerült meghatároznom, "
                "miről keressek információt."
            ),

            "game_data": None
        }

    final_response = get_wiki_answer(
        search_query
    )

    if not final_response:
        final_response = (
            "Sajnos most nem sikerült "
            "információt találnom."
        )
    # -----------------------------------------------------
    # WIKI KÉRÉS + WIKI VÁLASZ A CHAT HISTORYBA
    # -----------------------------------------------------

    add_conversation_turn(
        user_text,
        final_response
    )
    return {

        "action": "chat",

        "duration_minutes": None,

        "game": None,

        "location": None,

        "response": final_response.strip(),

        "game_data": None
    }


# =========================================================
# WEATHER
# =========================================================

def perform_weather(
        user_text,
        location
):
    print(
        "\n[WEATHER LOCATION]",
        location
    )

    if not location:
        return {

            "action": "chat",

            "duration_minutes": None,

            "game": None,

            "location": None,

            "response": (
                "Nem tudom, melyik település "
                "időjárására vagy kíváncsi."
            ),

            "game_data": None
        }

    weather = get_current_weather(
        location
    )

    if not weather:
        return {

            "action": "chat",

            "duration_minutes": None,

            "game": None,

            "location": location,

            "response": (
                f"Nem sikerült lekérnem "
                f"{location} aktuális időjárását."
            ),

            "game_data": None
        }

    print(
        "\n[WEATHER DATA]"
    )

    print(
        weather
    )

    final_response = format_weather_response(
        weather
    )

    print(
        "\n[WEATHER RESPONSE]"
    )

    print(
        final_response
    )

    return {

        "action": "chat",

        "duration_minutes": None,

        "game": None,

        "location": weather.get(
            "location",
            location
        ),

        "response": final_response,

        "game_data": None
    }


# =========================================================
# EREDMÉNY NORMALIZÁLÁSA
# =========================================================

def normalize_result(
        result
):
    if not result:
        return None

    action = result.get(
        "action"
    )

    if action not in [

        "chat",
        "set_timer",
        "stop_timer",
        "play",
        "get_time",
        "wiki_search",
        "weather",
        "game_start",
        "game_turn",
        "game_end"
    ]:
        print(
            "[INTERPRETER ERROR] "
            "Ismeretlen action:",
            action
        )

        return None

    return {

        "action": action,

        "duration_minutes": result.get(
            "duration_minutes"
        ),

        "game": result.get(
            "game"
        ),

        "location": result.get(
            "location"
        ),

        "response": result.get(
            "response"
        ),

        "game_data": result.get(
            "game_data"
        )
    }


# =========================================================
# FŐ INTERPRETER
# =========================================================

def interpret(
        user_text
):
    if not user_text:
        return None

    user_text = user_text.strip()

    if not user_text:
        return None

    print(
        "\n[INTERPRETER]"
    )

    print(
        "User:",
        user_text
    )

    prompt = build_interpretation_prompt(
        user_text
    )

    result = call_ollama(
        SYSTEM_PROMPT,
        prompt,
        ACTION_SCHEMA
    )

    result = normalize_result(
        result
    )

    if not result:
        return None

    action = result.get(
        "action"
    )

    print(
        "\n[ACTION]",
        action
    )

    # -----------------------------------------------------
    # WEATHER
    # -----------------------------------------------------

    if action == "weather":
        return perform_weather(
            user_text,
            result.get(
                "location"
            )
        )

    # -----------------------------------------------------
    # WIKIPÉDIA
    # -----------------------------------------------------

    if action == "wiki_search":
        search_query = result.get(
            "response"
        )

        return perform_wiki_search(
            user_text,
            search_query
        )

    # -----------------------------------------------------
    # NORMÁL CHAT
    # -----------------------------------------------------

    if action == "chat":

        response = result.get(
            "response",
            ""
        )

        if response:
            add_conversation_turn(
                user_text,
                response
            )

        return result

    # -----------------------------------------------------
    # JÁTÉK
    # -----------------------------------------------------

    if action == "game_start":
        return result

    if action == "game_turn":
        return result

    if action == "game_end":
        return result

    # -----------------------------------------------------
    # EGYÉB AKCIÓK
    # -----------------------------------------------------

    return result
