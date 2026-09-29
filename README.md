[English](README.md) | [Magyar](README.hu.md)
# HungarianAlexaAssistant

Hungarian voice assistant with wake-word detection, speech recognition, LLM integration and text-to-speech.

The project is designed to run locally on Windows and uses [`uv`](https://docs.astral.sh/uv/) for Python environment and dependency management.

## Features

* Hungarian voice interaction
* Wake-word detection using Sherpa-ONNX
* Speech recognition using OpenAI Whisper
* Local LLM integration through Ollama
* Hungarian text-to-speech
* Timers and basic commands
* Simple conversational memory
* Game interaction support
* GPU acceleration where supported

The version found in the `src_slow_pc` folder is a simple implementation supporting only basic,
stripped-down functionality. I began developing it with the intention of later porting it to the Raspberry Pi.

---

# Requirements

* Windows
* Python 3.11.9
* [`uv`](https://docs.astral.sh/uv/)
* [Ollama](https://ollama.com/) for the local LLM
* A working microphone
* Speakers/headphones

The Python version is pinned through `.python-version`.

---

# Installation

## 1. Clone the repository

```powershell
git clone <REPOSITORY_URL>
cd HungarianAlexaAssistant
```

## 2. Install Python dependencies

This project uses `uv`.

The repository contains:

* `pyproject.toml` — project dependencies
* `uv.lock` — locked dependency versions
* `.python-version` — required Python version

Create the virtual environment and install the locked dependencies with:

```powershell
uv sync
```

You do not need to create or activate a virtual environment manually.

To run the application:

```powershell
uv run python src\assistant.py
```

Slower PC:
```powershell
uv run python src_slow_pc\assistant.py
```


---

# Wake-word model

The wake-word model is **not included in this repository**.

This keeps the Git repository small and makes the model an explicit user-side dependency.

The application currently uses:

```text
sherpa-onnx-kws-zipformer-gigaspeech-3.3M-2024-01-01
```

Download the model archive from the Sherpa-ONNX project:

https://github.com/k2-fsa/sherpa-onnx/releases/download/kws-models/sherpa-onnx-kws-zipformer-gigaspeech-3.3M-2024-01-01.tar.bz2

After downloading, extract it into:

```text
models/
└── wakeword/
    └── sherpa-onnx-kws-zipformer-gigaspeech-3.3M-2024-01-01/
```

The directory should contain the required Sherpa-ONNX model files, including:

```text
encoder-*.onnx
decoder-*.onnx
joiner-*.onnx
tokens.txt
keywords.txt
```

The model files are intentionally excluded from Git.

---

# Ollama

The assistant uses Ollama for local language-model processing.

Install Ollama and make sure it is running before starting the assistant.

The current application configuration uses:

```text
gemma3:4b
```

If the model is not installed yet:

```powershell
ollama pull gemma3:4b
```

Verify that Ollama is available:

```powershell
ollama list
```

---

# Running

Start the assistant with:

```powershell
uv run python src\assistant.py
```

or on a slower computer:

```powershell
uv run python src_slow_pc\assistant.py
```

The assistant listens for the wake word:

```text
ALEXA
```

After activation, you can use commands such as:

```text
Alexa, mennyi a pontos idő?
```

```text
Alexa, állíts időzítőt 5 percre
```

```text
Alexa, időzítőt stop
```

```text
Alexa, kezdjük a játékot
```

---

# Project structure

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
│           └── ... model files ...
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

The wake-word model directory is user-provided and must not be committed to the repository.

---

# Dependency management

Dependencies are managed exclusively through `uv`.

To add a dependency:

```powershell
uv add <package>
```

To remove a dependency:

```powershell
uv remove <package>
```

To update the lock file:

```powershell
uv lock
```

To synchronize the environment with the lock file:

```powershell
uv sync
```

The `uv.lock` file should be committed to Git.

Do not use `pip freeze` as the project's dependency definition.

---

# Reproducible installation

A clean installation on another Windows machine should be possible with:

```powershell
git clone <REPOSITORY_URL>
cd HungarianAlexaAssistant
uv sync
```

Then download and extract the wake-word model as described above and install/configure Ollama.

Finally:

```powershell
uv run python src\assistant.py
```

---

# Models and generated files

Large model files and downloaded model data should not be committed to Git.

In particular, the following are user-side files:

```text
models/wakeword/
```

The Python dependency lock is kept in Git through:

```text
pyproject.toml
uv.lock
.python-version
```

This separates the reproducible Python environment from large model files.
