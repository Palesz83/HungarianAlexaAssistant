import requests


# =========================================================
# BEÁLLÍTÁSOK
# =========================================================

WEATHER_URL = "https://api.open-meteo.com/v1/forecast"

GEOCODING_URL = (
    "https://geocoding-api.open-meteo.com/v1/search"
)

REQUEST_TIMEOUT = 15

DEFAULT_COUNTRY_CODE = "HU"


# =========================================================
# TELEPÜLÉS NÉV NORMALIZÁLÁSA
# =========================================================

def normalize_location_name(
    location_name
):
    """
    Egyszerű magyar toldalék-normalizálás.

    Példák:

        Érden -> Érd
        Budapesten -> Budapest
        Győrben -> Győr
        Szegeden -> Szeged
    """

    if not location_name:
        return ""

    name = location_name.strip()

    lower = name.lower()

    replacements = {

        "budapesten": "Budapest",

        "érden": "Érd",

        "győrben": "Győr",

        "szegeden": "Szeged",

        "debrecenben": "Debrecen",

        "pécsen": "Pécs",

        "miskolcon": "Miskolc",

        "nyíregyházán": "Nyíregyháza",

        "kecskeméten": "Kecskemét",

        "székesfehérváron": "Székesfehérvár",

        "szolnokon": "Szolnok",

        "tatabányán": "Tatabánya",

        "kaposváron": "Kaposvár",

        "sopronban": "Sopron",

        "veszprémben": "Veszprém",

        "békéscsabán": "Békéscsaba",

        "zalaegerszegen": "Zalaegerszeg"
    }

    if lower in replacements:
        return replacements[lower]

    return name


# =========================================================
# HELY KERESÉSE
# =========================================================

def find_location(
    location_name,
    country_code=DEFAULT_COUNTRY_CODE
):
    """
    Település koordinátáinak lekérése
    Open-Meteo geokódoló segítségével.

    Alapértelmezés:
        Magyarország

    Visszatérés:

        {
            "name": "...",
            "latitude": ...,
            "longitude": ...,
            "country": "...",
            "country_code": "...",
            "admin1": "...",
            "timezone": "..."
        }

    vagy None.
    """

    if not location_name:
        return None

    normalized_name = normalize_location_name(
        location_name
    )

    if not normalized_name:
        return None

    try:

        params = {
            "name": normalized_name,
            "count": 10,
            "language": "hu",
            "format": "json"
        }

        if country_code:

            params["countryCode"] = (
                country_code.upper()
            )

        response = requests.get(
            GEOCODING_URL,
            params=params,
            timeout=REQUEST_TIMEOUT
        )

        response.raise_for_status()

        data = response.json()

    except requests.exceptions.Timeout:

        print(
            "[WEATHER ERROR] "
            "A helykeresés időtúllépés miatt sikertelen."
        )

        return None

    except requests.exceptions.ConnectionError:

        print(
            "[WEATHER ERROR] "
            "Nem sikerült kapcsolódni a geokódolóhoz."
        )

        return None

    except requests.exceptions.RequestException as e:

        print(
            "[WEATHER ERROR]",
            e
        )

        return None

    except ValueError:

        print(
            "[WEATHER ERROR] "
            "Érvénytelen JSON válasz."
        )

        return None

    results = data.get(
        "results",
        []
    )

    if not results:

        print(
            f"[WEATHER] "
            f"Nem található hely: {normalized_name}"
        )

        return None

    result = choose_best_location(
        results,
        normalized_name
    )

    if not result:

        return None

    location = {

        "name": result.get(
            "name",
            normalized_name
        ),

        "latitude": result.get(
            "latitude"
        ),

        "longitude": result.get(
            "longitude"
        ),

        "country": result.get(
            "country",
            ""
        ),

        "country_code": result.get(
            "country_code",
            ""
        ),

        "admin1": result.get(
            "admin1",
            ""
        ),

        "timezone": result.get(
            "timezone",
            ""
        )
    }

    print(
        "[WEATHER] Hely:",
        location
    )

    return location


# =========================================================
# LEGJOBB HELY KIVÁLASZTÁSA
# =========================================================

def choose_best_location(
    results,
    requested_name
):
    """
    A találatok közül kiválasztja a legjobb egyezést.

    Elsődleges:
        1. pontos névegyezés
        2. részleges névegyezés
        3. népesség
    """

    if not results:
        return None

    requested_lower = (
        requested_name.strip().lower()
    )

    # -----------------------------------------------------
    # PONTOS EGYEZÉS
    # -----------------------------------------------------

    exact_matches = []

    for result in results:

        result_name = result.get(
            "name",
            ""
        )

        if (
            result_name.strip().lower()
            == requested_lower
        ):

            exact_matches.append(
                result
            )

    if exact_matches:

        exact_matches.sort(
            key=lambda item: (
                item.get(
                    "population",
                    0
                ) or 0
            ),
            reverse=True
        )

        return exact_matches[0]

    # -----------------------------------------------------
    # RÉSZLEGES EGYEZÉS
    # -----------------------------------------------------

    partial_matches = []

    for result in results:

        result_name = result.get(
            "name",
            ""
        ).strip().lower()

        if (
            requested_lower in result_name
            or result_name in requested_lower
        ):

            partial_matches.append(
                result
            )

    if partial_matches:

        partial_matches.sort(
            key=lambda item: (
                item.get(
                    "population",
                    0
                ) or 0
            ),
            reverse=True
        )

        return partial_matches[0]

    # -----------------------------------------------------
    # ELSŐ TALÁLAT
    # -----------------------------------------------------

    return results[0]


# =========================================================
# WMO IDŐJÁRÁSI KÓD -> MAGYAR SZÖVEG
# =========================================================

def weather_code_to_hungarian(
    code
):

    descriptions = {

        0: "derült",

        1: "többnyire derült",

        2: "részben felhős",

        3: "borult",

        45: "ködös",

        48: "zúzmarás köd",

        51: "enyhe szitálás",

        53: "mérsékelt szitálás",

        55: "erős szitálás",

        56: "enyhe ónos szitálás",

        57: "erős ónos szitálás",

        61: "enyhe eső",

        63: "mérsékelt eső",

        65: "erős eső",

        66: "enyhe ónos eső",

        67: "erős ónos eső",

        71: "enyhe havazás",

        73: "mérsékelt havazás",

        75: "erős havazás",

        77: "hószemcsék",

        80: "enyhe zápor",

        81: "mérsékelt zápor",

        82: "heves zápor",

        85: "enyhe hózápor",

        86: "erős hózápor",

        95: "zivatar",

        96: "zivatar jégesővel",

        99: "erős zivatar jégesővel"
    }

    return descriptions.get(
        code,
        "ismeretlen időjárás"
    )


# =========================================================
# AKTUÁLIS IDŐJÁRÁS LEKÉRÉSE
# =========================================================

def get_current_weather(
    location_name
):
    """
    Aktuális időjárás lekérése.

    Visszatérés:

        {
            "location": "...",
            "country": "...",
            "temperature": ...,
            "feels_like": ...,
            "humidity": ...,
            "wind_speed": ...,
            "weather_code": ...,
            "description": "...",
            "timezone": "...",
            "time": "..."
        }

    vagy None.
    """

    location = find_location(
        location_name
    )

    if not location:

        return None

    latitude = location.get(
        "latitude"
    )

    longitude = location.get(
        "longitude"
    )

    if latitude is None or longitude is None:

        print(
            "[WEATHER ERROR] "
            "Hiányzó koordináták."
        )

        return None

    try:

        response = requests.get(
            WEATHER_URL,
            params={

                "latitude": latitude,

                "longitude": longitude,

                "current": (
                    "temperature_2m,"
                    "relative_humidity_2m,"
                    "apparent_temperature,"
                    "weather_code,"
                    "wind_speed_10m"
                ),

                "timezone": "auto"
            },

            timeout=REQUEST_TIMEOUT
        )

        response.raise_for_status()

        data = response.json()

    except requests.exceptions.Timeout:

        print(
            "[WEATHER ERROR] "
            "Az időjárási lekérés időtúllépés miatt sikertelen."
        )

        return None

    except requests.exceptions.ConnectionError:

        print(
            "[WEATHER ERROR] "
            "Nem sikerült kapcsolódni az időjárási szolgáltatáshoz."
        )

        return None

    except requests.exceptions.RequestException as e:

        print(
            "[WEATHER ERROR]",
            e
        )

        return None

    except ValueError:

        print(
            "[WEATHER ERROR] "
            "Érvénytelen időjárási JSON."
        )

        return None

    current = data.get(
        "current"
    )

    if not current:

        print(
            "[WEATHER ERROR] "
            "Nem érkezett current adat."
        )

        return None

    weather_code = current.get(
        "weather_code"
    )

    result = {

        "location": location.get(
            "name",
            location_name
        ),

        "country": location.get(
            "country",
            ""
        ),

        "country_code": location.get(
            "country_code",
            ""
        ),

        "region": location.get(
            "admin1",
            ""
        ),

        "temperature": current.get(
            "temperature_2m"
        ),

        "feels_like": current.get(
            "apparent_temperature"
        ),

        "humidity": current.get(
            "relative_humidity_2m"
        ),

        "wind_speed": current.get(
            "wind_speed_10m"
        ),

        "weather_code": weather_code,

        "description": weather_code_to_hungarian(
            weather_code
        ),

        "timezone": data.get(
            "timezone",
            location.get(
                "timezone",
                ""
            )
        ),

        "time": current.get(
            "time",
            ""
        )
    }

    print(
        "[WEATHER] Aktuális időjárás:",
        result
    )

    return result


# =========================================================
# SZÁM FORMÁZÁSA
# =========================================================

def format_number(
    value,
    decimals=1
):
    """
    Lebegőpontos érték formázása magyar
    tizedesvesszővel.
    """

    if value is None:
        return "ismeretlen"

    try:

        number = float(value)

    except (
        ValueError,
        TypeError
    ):

        return str(value)

    if decimals == 0:

        return str(
            int(
                round(number)
            )
        )

    formatted = (
        f"{number:.{decimals}f}"
    )

    return formatted.replace(
        ".",
        ","
    )


# =========================================================
# IDŐJÁRÁS -> FELMONDHATÓ MAGYAR STRING
# =========================================================

def format_weather_response(
    weather
):
    """
    Az időjárási adatokból közvetlenül
    felolvasható magyar választ készít.

    NINCS LLM-HÍVÁS.
    """

    if not weather:

        return (
            "Sajnos nem sikerült lekérnem "
            "az időjárási adatokat."
        )

    location = weather.get(
        "location",
        "a megadott helyen"
    )

    temperature = format_number(
        weather.get(
            "temperature"
        )
    )

    feels_like = format_number(
        weather.get(
            "feels_like"
        )
    )

    humidity = format_number(
        weather.get(
            "humidity"
        ),
        decimals=0
    )

    wind_speed = format_number(
        weather.get(
            "wind_speed"
        )
    )

    description = weather.get(
        "description",
        "ismeretlen időjárás"
    )

    response = (
        f"{location} településen jelenleg "
        f"{temperature} fok van, "
        f"a hőérzet {feels_like} fok. "
        f"Az időjárás {description}, "
        f"a páratartalom {humidity} százalék, "
        f"a szélsebesség pedig "
        f"{wind_speed} kilométer per óra."
    )

    return response


# =========================================================
# EGYSZERŰ PUBLIKUS FÜGGVÉNY
# =========================================================

def get_weather(
    location_name
):
    """
    Időjárás lekérése és közvetlenül
    felolvasható szöveg visszaadása.
    """

    weather = get_current_weather(
        location_name
    )

    return format_weather_response(
        weather
    )


# =========================================================
# TESZT
# =========================================================

def test_weather():

    location = input(
        "Település: "
    ).strip()

    if not location:

        print(
            "Nem adtál meg települést."
        )

        return

    print(
        "\n[WEATHER] Lekérés indul..."
    )

    weather = get_current_weather(
        location
    )

    if not weather:

        print(
            "\nNem sikerült lekérni az időjárást."
        )

        return

    print(
        "\n" + "=" * 60
    )

    print(
        format_weather_response(
            weather
        )
    )

    print(
        "=" * 60
    )


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    test_weather()