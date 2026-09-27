import html
import re

import requests


# =========================================================
# BEÁLLÍTÁSOK
# =========================================================

WIKIPEDIA_SEARCH_URL = (
    "https://hu.wikipedia.org/w/rest.php/v1/search/page"
)

WIKIPEDIA_SUMMARY_URL = (
    "https://hu.wikipedia.org/api/rest_v1/page/summary/"
)

REQUEST_TIMEOUT = 15

DEFAULT_RESULTS = 5

USER_AGENT = (
    "Aleksza/1.0 "
    "(local Hungarian voice assistant)"
)


# =========================================================
# HTTP FEJ
# =========================================================

HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/json"
}


# =========================================================
# HTML / SZÖVEG TISZTÍTÁS
# =========================================================

def clean_text(text):

    if not text:
        return ""

    text = html.unescape(text)

    text = re.sub(
        r"<[^>]+>",
        "",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# =========================================================
# WIKIPÉDIA KERESÉS
# =========================================================

def search_wikipedia(
    query,
    max_results=DEFAULT_RESULTS
):

    if not query:
        return []

    query = query.strip()

    if not query:
        return []

    try:

        response = requests.get(
            WIKIPEDIA_SEARCH_URL,
            headers=HEADERS,
            params={
                "q": query,
                "limit": max_results
            },
            timeout=REQUEST_TIMEOUT
        )

        response.raise_for_status()

        data = response.json()

    except requests.exceptions.Timeout:

        print(
            "[WIKI ERROR] "
            "A Wikipédia keresés időtúllépés miatt sikertelen."
        )

        return []

    except requests.exceptions.ConnectionError:

        print(
            "[WIKI ERROR] "
            "Nem sikerült kapcsolódni a Wikipédiához."
        )

        return []

    except requests.exceptions.RequestException as e:

        print(
            "[WIKI ERROR]",
            e
        )

        return []

    except ValueError:

        print(
            "[WIKI ERROR] "
            "Érvénytelen JSON válasz érkezett."
        )

        return []

    if not isinstance(data, dict):

        print(
            "[WIKI ERROR] "
            "Ismeretlen válaszformátum."
        )

        return []

    pages = data.get(
        "pages",
        []
    )

    if not isinstance(pages, list):

        print(
            "[WIKI ERROR] "
            "A pages mező nem lista."
        )

        return []

    results = []

    for page in pages:

        if not isinstance(page, dict):
            continue

        title = page.get(
            "title",
            ""
        )

        key = page.get(
            "key",
            ""
        )

        description = clean_text(
            page.get(
                "description",
                ""
            )
        )

        excerpt = clean_text(
            page.get(
                "excerpt",
                ""
            )
        )

        page_id = page.get(
            "id"
        )

        if not title:
            continue

        results.append({

            "id": page_id,

            "title": title,

            "key": key,

            "description": description,

            "excerpt": excerpt
        })

    print(
        f"[WIKI] Keresés: {query} "
        f"-> {len(results)} találat"
    )

    return results


# =========================================================
# WIKIPÉDIA LAP ÖSSZEFOGLALÓ
# =========================================================

def get_wikipedia_summary(
    title
):

    if not title:
        return None

    try:

        response = requests.get(
            WIKIPEDIA_SUMMARY_URL
            + requests.utils.quote(
                title,
                safe=""
            ),
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT
        )

        response.raise_for_status()

        data = response.json()

    except requests.exceptions.Timeout:

        print(
            "[WIKI ERROR] "
            "Az oldal lekérése időtúllépés miatt sikertelen."
        )

        return None

    except requests.exceptions.ConnectionError:

        print(
            "[WIKI ERROR] "
            "Nem sikerült lekérni a Wikipédia oldalt."
        )

        return None

    except requests.exceptions.RequestException as e:

        print(
            "[WIKI ERROR]",
            e
        )

        return None

    except ValueError:

        print(
            "[WIKI ERROR] "
            "Érvénytelen JSON válasz."
        )

        return None

    if not isinstance(data, dict):
        return None

    return data


# =========================================================
# TALÁLAT KIVÁLASZTÁSA
# =========================================================

def choose_best_result(
    query,
    results
):

    if not results:
        return None

    query_clean = (
        query
        .strip()
        .lower()
    )

    # -----------------------------------------------------
    # 1. Pontos cím egyezés
    # -----------------------------------------------------

    for result in results:

        title = (
            result.get(
                "title",
                ""
            )
            .strip()
            .lower()
        )

        if title == query_clean:

            return result

    # -----------------------------------------------------
    # 2. A keresés szerepel a címben
    # -----------------------------------------------------

    for result in results:

        title = (
            result.get(
                "title",
                ""
            )
            .strip()
            .lower()
        )

        if (
            query_clean
            and query_clean in title
        ):

            return result

    # -----------------------------------------------------
    # 3. Első releváns találat
    # -----------------------------------------------------

    return results[0]


# =========================================================
# ÖSSZEFOGLALÓ SZÖVEG KINYERÉSE
# =========================================================

def extract_summary_text(
    summary
):

    if not summary:
        return ""

    extract = clean_text(
        summary.get(
            "extract",
            ""
        )
    )

    if extract:
        return extract

    description = clean_text(
        summary.get(
            "description",
            ""
        )
    )

    return description


# =========================================================
# SZÖVEG RÖVIDÍTÉSE
# =========================================================

def limit_text(
    text,
    max_chars=900
):

    if not text:
        return ""

    text = text.strip()

    if len(text) <= max_chars:
        return text

    shortened = text[:max_chars]

    # Próbáljunk mondathatáron vágni.

    last_sentence = max(
        shortened.rfind("."),
        shortened.rfind("!"),
        shortened.rfind("?")
    )

    if last_sentence >= 300:

        return shortened[
            :last_sentence + 1
        ].strip()

    # Ha nincs megfelelő mondathatár,
    # szóhatáron vágunk.

    last_space = shortened.rfind(" ")

    if last_space > 0:

        shortened = shortened[
            :last_space
        ]

    return (
        shortened.rstrip(
            " ,;:-"
        )
        + "..."
    )


# =========================================================
# WIKI VÁLASZ FORMÁZÁSA
# =========================================================

def format_wiki_response(
    result,
    summary=None
):

    if not result:
        return (
            "Nem találtam megfelelő Wikipédia-szócikket."
        )

    title = result.get(
        "title",
        ""
    ).strip()

    if not title:
        title = "A keresett témáról"

    text = extract_summary_text(
        summary
    )

    # -----------------------------------------------------
    # Ha sikerült teljes Wikipédia-összefoglalót kérni
    # -----------------------------------------------------

    if text:

        text = limit_text(
            text,
            max_chars=900
        )

        return (
            f"{title}. "
            f"{text}"
        )

    # -----------------------------------------------------
    # Ha az összefoglaló API nem volt elérhető,
    # használjuk a keresési találat kivonatát.
    # -----------------------------------------------------

    description = clean_text(
        result.get(
            "description",
            ""
        )
    )

    excerpt = clean_text(
        result.get(
            "excerpt",
            ""
        )
    )

    if description and excerpt:

        return (
            f"{title}. "
            f"{description}. "
            f"{limit_text(excerpt, 700)}"
        )

    if excerpt:

        return (
            f"{title}. "
            f"{limit_text(excerpt, 900)}"
        )

    if description:

        return (
            f"{title}. "
            f"{description}."
        )

    return (
        f"Találtam egy Wikipédia-szócikket "
        f"{title} címmel, de annak tartalmát "
        f"most nem sikerült lekérnem."
    )


# =========================================================
# TELJES WIKI KERESÉS
# =========================================================

def get_wiki_answer(
    query
):

    if not query:

        return (
            "Nem tudom, miről keressek "
            "információt a Wikipédián."
        )

    query = query.strip()

    if not query:

        return (
            "Nem tudom, miről keressek "
            "információt a Wikipédián."
        )

    print(
        "\n[WIKI QUERY]",
        query
    )

    results = search_wikipedia(
        query,
        max_results=DEFAULT_RESULTS
    )

    if not results:

        return (
            f"Nem találtam Wikipédia-szócikket "
            f"erre: {query}."
        )

    print(
        "\n[WIKI RESULTS]"
    )

    for index, result in enumerate(
        results,
        start=1
    ):

        print(
            f"[{index}] "
            f"{result.get('title', '')}"
        )

        if result.get(
            "description"
        ):

            print(
                "    ",
                result.get(
                    "description"
                )
            )

    best_result = choose_best_result(
        query,
        results
    )

    if not best_result:

        return (
            f"Nem találtam megfelelő "
            f"Wikipédia-szócikket erre: {query}."
        )

    print(
        "\n[WIKI SELECTED]",
        best_result.get(
            "title"
        )
    )

    summary = get_wikipedia_summary(
        best_result.get(
            "title"
        )
    )

    if summary:

        print(
            "\n[WIKI SUMMARY]"
        )

        print(
            summary.get(
                "title",
                ""
            )
        )

    final_response = format_wiki_response(
        best_result,
        summary
    )

    print(
        "\n[WIKI RESPONSE]"
    )

    print(
        final_response
    )

    return final_response


# =========================================================
# RÉSZLETES KERESÉS
# =========================================================

def search_wikipedia_detailed(
    query,
    max_results=DEFAULT_RESULTS
):

    results = search_wikipedia(
        query,
        max_results=max_results
    )

    if not results:
        return None

    return results


# =========================================================
# TESZT
# =========================================================

def test_wiki():

    query = input(
        "Wikipédia keresés: "
    ).strip()

    if not query:

        print(
            "Nem adtál meg keresést."
        )

        return

    print(
        "\n[WIKI] Keresés indul...\n"
    )

    answer = get_wiki_answer(
        query
    )

    print(
        "\n"
        + "=" * 60
    )

    print(
        "\n[ALEKSZA VÁLASZA]\n"
    )

    print(
        answer
    )

    print(
        "\n"
        + "=" * 60
    )


# =========================================================
# FŐPROGRAM
# =========================================================

if __name__ == "__main__":

    test_wiki()