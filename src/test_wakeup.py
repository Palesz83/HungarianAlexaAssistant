import numpy as np
import soundfile as sf
import sherpa_onnx


# ============================================================
# BEÁLLÍTÁSOK
# ============================================================

MODEL_DIR = "../models/wakeword/sherpa-onnx-kws-zipformer-gigaspeech-3.3M-2024-01-01"

TOKENS = f"{MODEL_DIR}/tokens.txt"
ENCODER = f"{MODEL_DIR}/encoder-epoch-12-avg-2-chunk-16-left-64.int8.onnx"
DECODER = f"{MODEL_DIR}/decoder-epoch-12-avg-2-chunk-16-left-64.int8.onnx"
JOINER = f"{MODEL_DIR}/joiner-epoch-12-avg-2-chunk-16-left-64.int8.onnx"
KEYWORDS = f"{MODEL_DIR}/keywords.txt"

WAV_FILE =  f"{MODEL_DIR}/test_wavs/5.wav"


# ============================================================
# KEYWORD SPOTTER
# ============================================================

print("Wake-word modell betöltése...")

kws = sherpa_onnx.KeywordSpotter(
    tokens=TOKENS,
    encoder=ENCODER,
    decoder=DECODER,
    joiner=JOINER,
    keywords_file=KEYWORDS,

    num_threads=2,
    sample_rate=16000,

    # CPU használata
    provider="cpu",

    # Érzékenység
    keywords_score=0.95,
    keywords_threshold=0.25,
)


print("Modell betöltve.")


# ============================================================
# AUDIO BETÖLTÉSE
# ============================================================

print(f"Audio betöltése: {WAV_FILE}")

audio, sample_rate = sf.read(
    WAV_FILE,
    dtype="float32",
)


# Ha stereo lenne, alakítsuk mono-ra
if len(audio.shape) > 1:
    audio = audio.mean(axis=1)


print(f"Sample rate: {sample_rate}")
print(f"Audio hossz: {len(audio) / sample_rate:.2f} sec")


# ============================================================
# STREAM
# ============================================================

stream = kws.create_stream()

stream.accept_waveform(
    sample_rate,
    audio,
)


# A végére egy kis padding kell,
# hogy a modellnek legyen ideje lezárni a felismerést.
tail_padding = np.zeros(
    int(0.66 * sample_rate),
    dtype=np.float32,
)

stream.accept_waveform(
    sample_rate,
    tail_padding,
)

stream.input_finished()


# ============================================================
# DECODE
# ============================================================

print()
print("Wake-word keresése...")
print("--------------------------------")

detected = False

while kws.is_ready(stream):

    kws.decode_stream(stream)

    result = kws.get_result(stream)
    if result:
        print()
        print("=" * 50)
        print("DETECTED:", repr(result))
        print("=" * 50)


    if result != "":
        print()
        print("================================")
        print(" WAKE WORD DETECTED!")
        print(f" Keyword: {result}")
        print("================================")
        print()



        detected = True

        # Nagyon fontos:
        # felismerés után reseteljük a streamet
        kws.reset_stream(stream)


# ============================================================
# EREDMÉNY
# ============================================================

if not detected:
    print("Nem található wake-word.")

print()
print("Teszt vége.")

