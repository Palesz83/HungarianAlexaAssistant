import argparse
import json
import signal
import sys
import threading
from pathlib import Path

import sherpa_onnx
import sounddevice as sd
import soundfile as sf

from PySide6.QtCore import (
    QCoreApplication, QProcess, QProcessEnvironment, QThread, QTimer, Signal,
)

import voice_recognation
#from local_llm import generate, get_finetuned_model, make_prompt

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

    def __init__(self, show_face=True):
        self.app = QCoreApplication.instance()

        if self.app is None:
            self.app = QCoreApplication(sys.argv)

        self.face = None
        self._shutting_down = False
        self._face_ready = False
        self.face_startup_timer = QTimer()
        self.face_startup_timer.setSingleShot(True)
        self.face_startup_timer.timeout.connect(self.handle_face_startup_timeout)
        self.worker = VoiceWorker()
        if show_face:
            self.face = QProcess()
            environment = QProcessEnvironment.systemEnvironment()
            environment.insert("PYTHONIOENCODING", "utf-8")
            self.face.setProcessEnvironment(environment)
            self.face.setProgram(sys.executable)
            self.face.setArguments([
                "-u", str(Path(__file__).resolve().with_name("face_process.py"))
            ])
            self.face.readyReadStandardOutput.connect(self.read_face_output)
            self.face.readyReadStandardError.connect(self.read_face_errors)
            self.face.errorOccurred.connect(self.handle_face_error)
            self.face.finished.connect(self.handle_face_finished)
            self.worker.audio_monitoring_changed.connect(
                lambda enabled: self.send_face_command("audio_monitoring", enabled)
            )
            self.worker.thinking_changed.connect(
                lambda enabled: self.send_face_command("thinking", enabled)
            )
        self.worker.finished.connect(self.app.quit)

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

    def send_face_command(self, command, enabled):
        if self._shutting_down:
            return
        message = json.dumps({"command": command, "enabled": enabled}) + "\n"
        if self.face.write(message.encode("utf-8")) == -1:
            self.handle_error("Nem sikerült állapotot küldeni a 3D fejnek.")
            self.app.exit(1)

    def read_face_output(self):
        while self.face.canReadLine():
            line = bytes(self.face.readLine()).decode("utf-8").strip()
            if line == '[FACE IPC] {"event": "ready"}':
                if not self._face_ready and not self._shutting_down:
                    self._face_ready = True
                    self.face_startup_timer.stop()
                    print("[STARTUP] 3D fej külön folyamatban készen áll.")
                    self.worker.start()
            elif line:
                print(line)

    def read_face_errors(self):
        output = bytes(self.face.readAllStandardError()).decode("utf-8")
        if output:
            print(output, file=sys.stderr, end="")

    def handle_face_error(self, error):
        if not self._shutting_down:
            self.handle_error(f"3D fej folyamathiba: {self.face.errorString()}")
            self.app.exit(1)

    def handle_face_startup_timeout(self):
        self.handle_error("A 3D fej nem jelezte időben, hogy készen áll.")
        self.app.exit(1)

    def handle_face_finished(self, exit_code, exit_status):
        if not self._shutting_down:
            failed = exit_code != 0 or exit_status == QProcess.ExitStatus.CrashExit
            if failed:
                self.handle_error(f"A 3D fej folyamata leállt: {exit_code}")
            self.app.exit(1 if failed else 0)

    def start(self):
        if self.face is not None:
            self.face.start()
            if not self.face.waitForStarted(10000):
                self.shutdown()
                return 1
            self.face_startup_timer.start(30000)
        else:
            print("[STARTUP] 3D fej kikapcsolva.")
            self.worker.start()

        print("[STARTUP] Kilépés: Ctrl+C vagy a 3D ablak bezárása.")
        # Let Python handle Ctrl+C while the Qt event loop is idle.
        timer = QTimer()
        timer.timeout.connect(lambda: None)
        timer.start(100)
        previous_handler = signal.signal(
            signal.SIGINT, lambda signum, frame: self.app.quit()
        )
        try:
            return self.app.exec()
        finally:
            timer.stop()
            signal.signal(signal.SIGINT, previous_handler)
            self.shutdown()

    def shutdown(self):
        if self._shutting_down:
            return
        self._shutting_down = True
        self.face_startup_timer.stop()
        self.worker.stop()

        if self.face is not None and self.face.state() != QProcess.ProcessState.NotRunning:
            self.face.closeWriteChannel()
            if not self.face.waitForFinished(3000):
                print("[Assistant] A 3D fej leállítása időtúllépés miatt.")
                self.face.terminate()
                if not self.face.waitForFinished(1000):
                    self.face.kill()
                    self.face.waitForFinished()

        # Megvárjuk a háttérszál befejezését.
        if self.worker.isRunning():
            self.worker.wait()


# ============================================================
# BELÉPÉSI PONT
# ============================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--no-face",
        action="store_true",
        help="Run without the animated 3D face.",
    )
    args = parser.parse_args()
    assistant = Assistant(show_face=not args.no_face)
    sys.exit(assistant.start())
