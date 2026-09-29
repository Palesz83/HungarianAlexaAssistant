[English](README.md) | [Magyar](README.hu.md)
# HungarianAlexaAssistant

Magyar nyelvű, helyben futó hangasszisztens ébresztőszó-felismeréssel, beszédfelismeréssel, helyi LLM-integrációval és szövegfelolvasással.

A projekt Windows környezetre készült, és a Python környezet valamint a függőségek kezelésére az [`uv`](https://docs.astral.sh/uv/) eszközt használja.

## Funkciók

* Magyar nyelvű hangvezérlés
* Ébresztőszó-felismerés Sherpa-ONNX segítségével
* Beszédfelismerés OpenAI Whisper segítségével
* Helyben futó LLM Ollama segítségével
* Magyar nyelvű szövegfelolvasás (TTS)
* Időzítők és alapvető parancsok
* Egyszerű beszélgetési memória
* Játékok támogatása
* GPU-gyorsítás, ahol az adott hardver és a használt könyvtárak támogatják

A src_slow_pc mappában található verzió, egy lebutított alap funkcionalítást 
támogató egyszerű implementáció ami későbbiekben RPI-re portolás miatt kezdtem kialakítani.

---

# Követelmények

* Windows
* Python 3.11.9
* [`uv`](https://docs.astral.sh/uv/)
* [Ollama](https://ollama.com/) a helyi nyelvi modell futtatásához
* Működő mikrofon
* Hangszóró vagy fejhallgató

A projekt a Python verzióját a `.python-version` fájlban rögzíti.

---

# Telepítés

## 1. A repository klónozása

```powershell
git clone <REPOSITORY_URL>
cd HungarianAlexaAssistant
```

## 2. Python függőségek telepítése

A projekt az `uv` csomagkezelőt és környezetkezelőt használja.

A repositoryban található:

* `pyproject.toml` — a projekt közvetlen függőségei
* `uv.lock` — a rögzített függőségverziók
* `.python-version` — a használt Python verzió

A virtuális környezet létrehozásához és a függőségek telepítéséhez:

```powershell
uv sync
```

Nincs szükség a virtuális környezet manuális létrehozására vagy aktiválására.

Az alkalmazás indítása:

```powershell
uv run python src\assistant.py
```

---

# Ébresztőszó-modell

Az ébresztőszó-felismeréshez használt modell **nincs a repositoryban**.

A modell letöltése és telepítése a felhasználó feladata.

Ez azért van így, hogy a Git repository ne tartalmazzon nagy bináris modellfájlokat.

A projekt jelenleg ezt a Sherpa-ONNX modellt használja:

```text
sherpa-onnx-kws-zipformer-gigaspeech-3.3M-2024-01-01
```

## Modell letöltése

A modell letölthető a Sherpa-ONNX GitHub release oldaláról:

https://github.com/k2-fsa/sherpa-onnx/releases/download/kws-models/sherpa-onnx-kws-zipformer-gigaspeech-3.3M-2024-01-01.tar.bz2

A letöltött archívumot ki kell csomagolni ide:

```text
models/
└── wakeword/
    └── sherpa-onnx-kws-zipformer-gigaspeech-3.3M-2024-01-01/
```

A könyvtárban a szükséges Sherpa-ONNX fájloknak meg kell lenniük, többek között:

```text
encoder-*.onnx
decoder-*.onnx
joiner-*.onnx
tokens.txt
keywords.txt
```

A modellfájlokat a Git repository **nem tartalmazza**, és nem is szabad őket feltölteni.

---

# Ollama

Az asszisztens az Ollama segítségével helyben futó nyelvi modellt használ.

Telepítsd az Ollamát, majd győződj meg róla, hogy fut.

A jelenlegi konfiguráció:

```text
gemma3:4b
```

Ha a modell még nincs letöltve:

```powershell
ollama pull gemma3:4b
```

A telepített modellek ellenőrzése:

```powershell
ollama list
```

---

# Futtatás

Az asszisztens indítása:

```powershell
uv run python src\assistant.py
```
Lassabb gépen:
```powershell
uv run python src_slow_pc\assistant.py
```


Az asszisztens jelenlegi ébresztőszava:

```text
ALEXA
```

Az aktiválás után például ilyen parancsokat lehet mondani:

```text
Alexa, mennyi a pontos idő?
```

```text
Alexa, állíts időzítőt 5 percre.
```

```text
Alexa, időzítőt stop.
```

```text
Alexa, kezdjük a játékot.
```

---

# Projekt felépítése

```text
HungarianAlexaAssistant/
│
├── src/
│   ├── assistant.py
│   ├── voice_recognation.py
│   ├── command_definition.py
│   └── ...
│
├── src_slow_pc/
│   ├── assistant.py
│   ├── command_definition.py
│   ├── command_interpreter.py
│   └── ...
│
├── models/
│   └── wakeword/
│       └── sherpa-onnx-kws-zipformer-gigaspeech-3.3M-2024-01-01/
│           └── ... modellfájlok ...
│
├── resources/
│   └── activation.wav
│
├── pyproject.toml
├── uv.lock
├── .python-version
├── .gitignore
└── README.md
```

A `models/wakeword/` könyvtár tartalma felhasználói telepítés része, a modellfájlok nem kerülnek be a Git repositoryba.

---

# Függőségek kezelése

A Python függőségeket kizárólag az `uv` segítségével kezeljük.

Új függőség hozzáadása:

```powershell
uv add <csomag>
```

Függőség eltávolítása:

```powershell
uv remove <csomag>
```

A lock fájl frissítése:

```powershell
uv lock
```

A környezet szinkronizálása:

```powershell
uv sync
```

A repositoryban az alábbi fájlok tartoznak a Python környezethez:

```text
pyproject.toml
uv.lock
.python-version
```

Az `uv.lock` fájlt Gitben tároljuk.

A projektnek nincs szüksége `requirements.txt` vagy `requirements-lock.txt` fájlra.

A `pip freeze` kimenetét nem használjuk a projekt függőségeinek meghatározására.

---

# Tiszta telepítés

Egy új Windows gépen a cél az, hogy a Python környezet néhány paranccsal reprodukálható legyen:

```powershell
git clone <REPOSITORY_URL>
cd HungarianAlexaAssistant
uv sync
```

Ezután:

1. Töltsd le az ébresztőszó-modellt.
2. Csomagold ki a megfelelő `models/wakeword/` könyvtárba.
3. Telepítsd és indítsd el az Ollamát.
4. Töltsd le a szükséges Ollama modellt.

Végül:

```powershell
uv run python src\assistant.py
```
vagy ezt kell indítani, ha lassabb gépen szeretnéd kipróbálni:
```powershell
uv run python src_slow_pc\assistant.py
```
---

# Modellfájlok és nagy bináris fájlok

A nagy modellfájlokat nem tároljuk a Git repositoryban.

Különösen:

```text
models/wakeword/
```

felhasználói telepítés része.

A Python környezet reprodukálhatóságát ezzel szemben a repositoryban található:

```text
pyproject.toml
uv.lock
.python-version
```

fájlok biztosítják.
