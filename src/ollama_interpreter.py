import json
import requests
# from local_llm import generate, get_finetuned_model, make_prompt
from local_llm import make_prompt, get_system_prompt, get_large_system_prompt

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
#
# Load the finetuned model to ollama service.
# Rrun in CMD:
# ollama create qwen2.5_pago:0.5b -f qwen_finetuned_modelFile

OLLAMA_URL = "http://localhost:11434/api/generate"

#OLLAMA_MODEL = "qwen2.5_pago:0.5b"
OLLAMA_MODEL = "gemma3:4b"
# OLLAMA_MODEL = "gemma4:26b"
# OLLAMA_MODEL = "qwen2.5:1.5b"

REQUEST_TIMEOUT = 240
# =========================================================
# NORMÁL BESZÉLGETÉSI ELŐZMÉNY
# =========================================================

conversation_history = []

MAX_HISTORY_MESSAGES = 12

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

def call_local_model(
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
                f"- User request: {content}"
            )

        elif role == "assistant":

            lines.append(
                f"- Aleksza: {content}"
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

    return make_prompt(user_text, history)


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

    if not isinstance(result, dict):
        print("[INTERPRETER ERROR] A modell válasza nem JSON objektum.")
        return None

    if set(result) != set(ACTION_SCHEMA["required"]):
        print("[INTERPRETER ERROR] Hiányzó vagy ismeretlen JSON mezők.")
        return None

    json_types = {
        "string": str,
        "integer": int,
        "object": dict,
        "null": type(None),
    }
    for field, rules in ACTION_SCHEMA["properties"].items():
        allowed_types = rules["type"]
        if isinstance(allowed_types, str):
            allowed_types = [allowed_types]
        if type(result[field]) not in [json_types[name] for name in allowed_types]:
            print(f"[INTERPRETER ERROR] Érvénytelen mezőtípus: {field}")
            return None

    action = result.get(
        "action"
    )

    if action not in ACTION_SCHEMA["properties"]["action"]["enum"]:
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

    user_prompt = build_interpretation_prompt(
        user_text
    )

    #system_prompt = get_system_prompt()
    system_prompt = get_large_system_prompt()

    print(
        "system prompt:",
        system_prompt
    )

    print(
        "Prompt:",
        user_prompt
    )
    result = call_local_model(system_prompt, user_prompt, ACTION_SCHEMA)

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
