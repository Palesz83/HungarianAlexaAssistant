import time
import sys
import platform
import soundfile as sf

MODEL_DIR = "../models/wakeword/sherpa-onnx-kws-zipformer-gigaspeech-3.3M-2024-01-01"
WAV_FILE =  f"{MODEL_DIR}/test_wavs/5.wav"

print("=" * 70)
print("AI BENCHMARK")
print("=" * 70)

print("Python:", sys.version.split()[0])
print("Platform:", platform.platform())

# ---------------------------------------------------------
# PYTORCH
# ---------------------------------------------------------

print("\n" + "=" * 70)
print("PYTORCH")
print("=" * 70)

import torch

print("Torch:", torch.__version__)
print("CUDA available:", torch.cuda.is_available())

# ---------------------------------------------------------
# WHISPER
# ---------------------------------------------------------

print("\n" + "=" * 70)
print("WHISPER")
print("=" * 70)

import whisper

print("Whisper version:", end=" ")

try:
    from importlib.metadata import version
    print(version("openai-whisper"))
except Exception:
    print("unknown")

MODEL_NAME = "small"
# WAV_FILE = "test_wavs/5.wav"

print("Model:", MODEL_NAME)
print("Audio:", WAV_FILE)

print("\nLoading Whisper model...")

start = time.perf_counter()

whisper_model = whisper.load_model(MODEL_NAME)

load_time = time.perf_counter() - start

print(f"Model load time: {load_time:.3f} sec")
print("Model device:", whisper_model.device)

print("\nRunning Whisper...")

start = time.perf_counter()
audio, sample_rate = sf.read(WAV_FILE, dtype="float32")

if audio.ndim > 1:
    audio = audio.mean(axis=1)

print("Audio sample rate:", sample_rate)
print("Audio samples:", len(audio))
print("Audio duration:", len(audio) / sample_rate, "sec")

start = time.perf_counter()

result = whisper_model.transcribe(
    audio,
    language="hu",
    fp16=False,
)

whisper_time = time.perf_counter() - start
text = result.get("text", "").strip()

print(f"Whisper time: {whisper_time:.3f} sec")
print("Result:")
print(" ", text)


whisper_time = time.perf_counter() - start

text = result.get("text", "").strip()

print(f"Whisper time: {whisper_time:.3f} sec")
print("Result:")
print(" ", text)

# ---------------------------------------------------------
# TTS
# ---------------------------------------------------------

print("\n" + "=" * 70)
print("TTS")
print("=" * 70)

try:
    from TTS.api import TTS

    print("Loading TTS...")

    start = time.perf_counter()

    tts = TTS(
        model_name="tts_models/hu/css10/vits"
    )

    tts_load_time = time.perf_counter() - start

    print(f"TTS model load time: {tts_load_time:.3f} sec")

    test_text = "Ez egy sebességteszt."

    print("\nRunning TTS...")

    start = time.perf_counter()

    wav = tts.tts(text=test_text)

    tts_time = time.perf_counter() - start

    print(f"TTS generation time: {tts_time:.3f} sec")

    print("Generated samples:", len(wav))

except Exception as e:
    tts_load_time = None
    tts_time = None

    print("TTS benchmark FAILED")
    print(type(e).__name__, e)

# ---------------------------------------------------------
# SUMMARY
# ---------------------------------------------------------

print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)

print(f"Whisper model load : {load_time:.3f} sec")
print(f"Whisper inference  : {whisper_time:.3f} sec")

if tts_load_time is not None:
    print(f"TTS model load     : {tts_load_time:.3f} sec")
    print(f"TTS generation     : {tts_time:.3f} sec")

print("=" * 70)