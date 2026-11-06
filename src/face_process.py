import json
import sys
import threading

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

from alexa_face_3d import AlekszaFace

IPC_PREFIX = "[FACE IPC] "


class FaceCommands(QObject):
    received = Signal(str)
    disconnected = Signal()

    def read_commands(self):
        for line in sys.stdin:
            self.received.emit(line)
        self.disconnected.emit()


def main():
    app = QApplication(sys.argv)
    face = AlekszaFace(monitor_audio=False)
    commands = FaceCommands()

    def receive_command(line):
        try:
            message = json.loads(line)
        except json.JSONDecodeError as exc:
            print(f"[FACE ERROR] Invalid command: {exc}", file=sys.stderr, flush=True)
            app.exit(1)
            return

        if not isinstance(message, dict) or type(message.get("enabled")) is not bool:
            print("[FACE ERROR] Invalid command fields.", file=sys.stderr, flush=True)
            app.exit(1)
            return

        if message.get("command") == "thinking":
            face.set_thinking(message["enabled"])
        elif message.get("command") == "audio_monitoring":
            face.set_audio_monitoring(message["enabled"])
        else:
            print("[FACE ERROR] Unknown command.", file=sys.stderr, flush=True)
            app.exit(1)

    commands.received.connect(receive_command)
    commands.disconnected.connect(app.quit)
    app.aboutToQuit.connect(lambda: face.set_audio_monitoring(False))
    reader = threading.Thread(target=commands.read_commands, daemon=True)
    reader.start()
    face.show()
    print(IPC_PREFIX + json.dumps({"event": "ready"}), flush=True)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
