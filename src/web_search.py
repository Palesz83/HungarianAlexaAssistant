import requests


FREE_SERP_URL = "https://freeserp.ai/api.php"

DEFAULT_RESULTS = 5
REQUEST_TIMEOUT = 15


def search_web(query, max_results=DEFAULT_RESULTS):
    """
    Webes keresés FreeSerp segítségével.

    Paraméterek:
        query: keresési kifejezés
        max_results: visszaadandó találatok száma

    Visszatérés:
        Lista:
        [
            {
                "title": "...",
                "url": "...",
                "snippet": "...",
                "domain": "...",
                "language": "...",
                "published": "..."
            }
        ]
    """

    if not query:
        return []

    query = query.strip()

    if not query:
        return []

    try:
        response = requests.get(
            FREE_SERP_URL,
            params={
                "index": "web",
                "q": query,
                "size": max_results
            },
            timeout=REQUEST_TIMEOUT
        )

        response.raise_for_status()

        data = response.json()

    except requests.exceptions.Timeout:
        print("[WEB ERROR] A keresés időtúllépés miatt sikertelen.")
        return []

    except requests.exceptions.ConnectionError:
        print("[WEB ERROR] Nem sikerült kapcsolódni a FreeSerphez.")
        return []

    except requests.exceptions.RequestException as e:
        print("[WEB ERROR]", e)
        return []

    except ValueError:
        print("[WEB ERROR] A FreeSerp nem érvényes JSON választ adott.")
        return []

    if not isinstance(data, dict):
        print("[WEB ERROR] Ismeretlen válaszformátum.")
        return []

    if not data.get("ok", True):
        print("[WEB ERROR] A FreeSerp hibát jelzett.")
        return []

    results = data.get("results", [])

    if not isinstance(results, list):
        print("[WEB ERROR] A results mező nem lista.")
        return []

    cleaned_results = []

    for result in results:

        if not isinstance(result, dict):
            continue

        title = result.get("title", "")
        url = result.get("url", "")
        snippet = result.get("snippet", "")

        domain = result.get("domain", "")
        language = result.get("language", "")
        published = result.get("published", "")

        # Egyes FreeSerp válaszokban más mezőnevek is
        # előfordulhatnak, ezért ezeket is ellenőrizzük.
        if not snippet:
            snippet = result.get("description", "")

        if not published:
            published = result.get("publication_date", "")

        cleaned_results.append({
            "title": title,
            "url": url,
            "snippet": snippet,
            "domain": domain,
            "language": language,
            "published": published
        })

    print(
        f"[WEB] Keresés: {query} "
        f"-> {len(cleaned_results)} találat"
    )

    return cleaned_results


def search_web_detailed(query, max_results=DEFAULT_RESULTS):
    """
    Részletesebb keresés.

    A normál search_web() megtisztítja a találatokat.
    Ez a függvény megtartja a FreeSerp teljes válaszát.

    Hibánál None értéket ad vissza.
    """

    if not query:
        return None

    query = query.strip()

    if not query:
        return None

    try:
        response = requests.get(
            FREE_SERP_URL,
            params={
                "index": "web",
                "q": query,
                "size": max_results
            },
            timeout=REQUEST_TIMEOUT
        )

        response.raise_for_status()

        return response.json()

    except requests.exceptions.Timeout:
        print("[WEB ERROR] A keresés időtúllépés miatt sikertelen.")
        return None

    except requests.exceptions.ConnectionError:
        print("[WEB ERROR] Nem sikerült kapcsolódni a FreeSerphez.")
        return None

    except requests.exceptions.RequestException as e:
        print("[WEB ERROR]", e)
        return None

    except ValueError:
        print("[WEB ERROR] Érvénytelen JSON válasz.")
        return None


def format_results_for_llm(results, max_chars_per_result=1000):
    """
    A keresési találatokat olyan szöveggé alakítja,
    amit később közvetlenül odaadhatunk az Ollamának.

    Példa:

    [1]
    Title: ...
    URL: ...
    Snippet: ...

    [2]
    ...
    """

    if not results:
        return "Nem találtam releváns webes találatot."

    formatted = []

    for index, result in enumerate(results, start=1):

        title = result.get("title", "").strip()
        url = result.get("url", "").strip()
        snippet = result.get("snippet", "").strip()
        domain = result.get("domain", "").strip()
        published = result.get("published", "").strip()

        if len(snippet) > max_chars_per_result:
            snippet = snippet[:max_chars_per_result] + "..."

        block = [
            f"[{index}]",
            f"Title: {title}",
            f"URL: {url}",
        ]

        if domain:
            block.append(f"Domain: {domain}")

        if published:
            block.append(f"Published: {published}")

        if snippet:
            block.append(f"Snippet: {snippet}")

        formatted.append("\n".join(block))

    return "\n\n".join(formatted)


def test_search():
    """
    Egyszerű teszt a fájl önálló ellenőrzéséhez.
    """

    query = input("Keresés: ").strip()

    if not query:
        print("Nem adtál meg keresést.")
        return

    print("\n[WEB] Keresés indul...\n")

    results = search_web(
        query,
        max_results=5
    )

    if not results:
        print("Nem érkezett találat.")
        return

    print("=" * 60)

    for index, result in enumerate(results, start=1):

        print(f"\n[{index}] {result['title']}")
        print(f"URL: {result['url']}")

        if result["domain"]:
            print(f"Domain: {result['domain']}")

        if result["published"]:
            print(f"Published: {result['published']}")

        print(f"Snippet: {result['snippet']}")

    print("\n" + "=" * 60)

    print("\n[LLM FORMÁTUM]\n")
    print(
        format_results_for_llm(results)
    )


if __name__ == "__main__":
    test_search()