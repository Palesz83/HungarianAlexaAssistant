import sys
import threading

import sherpa_onnx
import sounddevice as sd
import soundfile as sf

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import QApplication

from alexa_face_3d import AlekszaFace
import voice_recognation


MODEL_DIR = (
    "../models/wakeword/"
    "sherpa-onnx-kws-zipformer-gigaspeech-3.3M-2024-01-01"
)

TOKENS = f"{MODEL_DIR}/tokens.txt"
ENCODER = f"{MODEL_DIR}/encoder-epoch-12-avg-2-chunk-16-left-64.int8.onnx"
DECODER = f"{MODEL_DIR}/decoder-epoch-12-avg-2-chunk-16-left-64.int8.onnx"
JOINER = f"{MODEL_DIR}/joiner-epoch-12-avg-2-chunk-16-left-64.int8.onnx"
KEYWORDS = f"{MODEL_DIR}/keywords.txt"

SAMPLE_RATE = 16000
CHANNELS = 1
BLOCK_SIZE = 1600


# ============================================================
# HÁTTÉRBEN FUTÓ HANGFELDOLGOZÁS
# ============================================================

class VoiceWorker(QThread):

    thinking_changed = Signal(bool)
    error_occurred = Signal(str)
    wake_detected = Signal(str)
    audio_monitoring_changed = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def run(self):
        try:
            wavefile, _ = sf.read(
                "../src/resources/activation.wav"
            )

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

            stream = kws.create_stream()

            def audio_callback(
                indata, frames, time_info, status
            ):
                if status:
                    print(status)

                if not self._stop_event.is_set():
                    stream.accept_waveform(
                        SAMPLE_RATE,
                        indata[:, 0].copy(),
                    )

            with sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype="float32",
                blocksize=BLOCK_SIZE,
                callback=audio_callback,
            ):
                while not self._stop_event.is_set():

                    if not kws.is_ready(stream):
                        self.msleep(5)
                        continue

                    kws.decode_stream(stream)
                    result = kws.get_result(stream)

                    if not result:
                        continue

                    print("WAKE WORD:", repr(result))

                    # Az arc gondolkodni kezd.
                    self.thinking_changed.emit(True)

                    try:
                        # A hang lejátszása nem blokkolja a GUI-t.
                        sd.play(
                            wavefile,
                            samplerate=SAMPLE_RATE,
                            blocking=True,
                        )

                        if self._stop_event.is_set():
                            break

                        # A meglévő feldolgozó meghívása.
                        self.audio_monitoring_changed.emit(True)
                        try:
                            voice_recognation.voice_process()
                        finally:
                            self.audio_monitoring_changed.emit(False)

                    except Exception as exc:
                        self.error_occurred.emit(str(exc))

                    finally:
                        # Visszaállás nyugalmi állapotba.
                        self.thinking_changed.emit(False)

                        sd.stop()
                        kws.reset_stream(stream)

        except Exception as exc:
            self.error_occurred.emit(str(exc))


# ============================================================
# KÖZPONTI ASSISTANT
# ============================================================

class Assistant:

    def __init__(self):
        self.app = QApplication.instance()

        if self.app is None:
            self.app = QApplication(sys.argv)

        self.face = AlekszaFace(monitor_audio=False)
        self.worker = VoiceWorker()
        self.worker.audio_monitoring_changed.connect(
            self.face.set_audio_monitoring
        )
        # self.worker = VoiceWorker()

        # A háttérszál jelzései a grafikus felületnek.
        self.worker.thinking_changed.connect(
            self.face.set_thinking
        )

        self.worker.error_occurred.connect(
            self.handle_error
        )

        self.worker.wake_detected.connect(
            self.handle_wake_word
        )

        self.app.aboutToQuit.connect(
            self.shutdown
        )

    def handle_wake_word(self, text):
        print(f"Wake word felismerve: {text}")

    def handle_error(self, message):
        print(f"[Assistant hiba] {message}")

    def start(self):
        self.face.show()
        self.worker.start()

        return self.app.exec()

    def shutdown(self):
        self.worker.stop()

        # Megvárjuk a háttérszál befejezését.
        if self.worker.isRunning():
            self.worker.wait()


# ============================================================
# BELÉPÉSI PONT
# ============================================================

if __name__ == "__main__":
    assistant = Assistant()
    sys.exit(assistant.start())
