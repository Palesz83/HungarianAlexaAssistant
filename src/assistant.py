import sherpa_onnx
import sounddevice as sd
import soundfile as sf

import voice_recognation

MODEL_DIR = "../models/wakeword/sherpa-onnx-kws-zipformer-gigaspeech-3.3M-2024-01-01"

TOKENS = f"{MODEL_DIR}/tokens.txt"
ENCODER = f"{MODEL_DIR}/encoder-epoch-12-avg-2-chunk-16-left-64.int8.onnx"
DECODER = f"{MODEL_DIR}/decoder-epoch-12-avg-2-chunk-16-left-64.int8.onnx"
JOINER = f"{MODEL_DIR}/joiner-epoch-12-avg-2-chunk-16-left-64.int8.onnx"
KEYWORDS = f"{MODEL_DIR}/keywords.txt"

SAMPLE_RATE = 16000
CHANNELS = 1
BLOCK_SIZE = 1600  # 100 ms

wavefile, fs = sf.read('resources/activation.wav')

# ============================================================
# KWS
# ============================================================

print("Wake-word modell betöltése...")

kws = sherpa_onnx.KeywordSpotter(
    tokens=TOKENS,
    encoder=ENCODER,
    decoder=DECODER,
    joiner=JOINER,
    keywords_file=KEYWORDS,

    num_threads=4,
    sample_rate=SAMPLE_RATE,

    provider="cpu",

    keywords_score=0.85,
    keywords_threshold=0.10,
)

print("Load model")

# ============================================================
# STREAM
# ============================================================

stream = kws.create_stream()


# ============================================================
# CALLBACK
# ============================================================

def audio_callback(indata, frames, time, status):
    if status:
        print(status)

    # sounddevice -> numpy
    audio = indata[:, 0].copy()

    stream.accept_waveform(
        SAMPLE_RATE,
        audio,
    )


# ============================================================
# MICROPHONE
# ============================================================

print()
print("======================================")
print(" ALEXA WAKE WORD DETECTOR")
print("======================================")
print()
print("Say: ALEXA")
print()


def playWav(wave):
    # sd.default.samplerate = 16000
    sd.play(wave, blocking=True)


with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="float32",
        blocksize=BLOCK_SIZE,
        callback=audio_callback,
):
    while True:

        while kws.is_ready(stream):

            kws.decode_stream(stream)

            result = kws.get_result(stream)

            if result:

                print()
                print("=" * 50)
                print("WAKE WORD:", repr(result))
                playWav(wavefile)
                try:
                    voice_recognation.voice_process()
                except:
                    print("Voice Processing Error")

                print("=" * 50)
                print()

                kws.reset_stream(stream)
