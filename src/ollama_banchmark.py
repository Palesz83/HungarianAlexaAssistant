import json
import time
import urllib.request

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "gemma3:4b"

PROMPT = """Válaszolj röviden magyarul.
Mi a különbség a CPU és a GPU között egy mesterséges intelligencia modell futtatásakor?
Legfeljebb 5 mondatban válaszolj."""


def run_test(test_name):
    payload = {
        "model": MODEL,
        "prompt": PROMPT,
        "stream": False,
    }

    data = json.dumps(payload).encode("utf-8")

    print()
    print("=" * 70)
    print(test_name)
    print("=" * 70)
    print("Model:", MODEL)
    print("Prompt:", PROMPT.replace("\n", " "))

    start = time.perf_counter()

    request = urllib.request.Request(
        OLLAMA_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(request) as response:
        result = json.loads(response.read().decode("utf-8"))

    total_time = time.perf_counter() - start

    print()
    print("Response:")
    print(result.get("response", "").strip())

    print()
    print("-" * 70)
    print(f"Total wall time       : {total_time:.3f} sec")

    if "load_duration" in result:
        print(
            f"Model load duration   : "
            f"{result['load_duration'] / 1e9:.3f} sec"
        )

    if "prompt_eval_duration" in result:
        print(
            f"Prompt eval duration  : "
            f"{result['prompt_eval_duration'] / 1e9:.3f} sec"
        )

    if "eval_duration" in result:
        eval_time = result["eval_duration"] / 1e9
        print(f"Response eval duration: {eval_time:.3f} sec")

        if result.get("eval_count"):
            tokens_per_sec = result["eval_count"] / eval_time
            print(f"Generation speed      : {tokens_per_sec:.2f} tok/s")

    print(f"Prompt tokens         : {result.get('prompt_eval_count', '?')}")
    print(f"Response tokens       : {result.get('eval_count', '?')}")
    print(f"Response characters   : {len(result.get('response', ''))}")

    return total_time


print("=" * 70)
print("OLLAMA BENCHMARK")
print("=" * 70)

print("Ollama:", OLLAMA_URL)
print("Model:", MODEL)

# Első futás
cold_time = run_test("TEST 1 - FIRST REQUEST")

# Második futás
warm_time = run_test("TEST 2 - SECOND REQUEST")

print()
print("=" * 70)
print("SUMMARY")
print("=" * 70)
print(f"First request  : {cold_time:.3f} sec")
print(f"Second request : {warm_time:.3f} sec")
print("=" * 70)