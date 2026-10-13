
import sys
import math
import random
import threading
import time

import numpy as np
import soundcard as sc

from PySide6.QtCore import Qt, QTimer, QThread, Signal, QPointF
from PySide6.QtGui import (
    QPainter, QColor, QPen, QBrush,
    QLinearGradient, QPolygonF,
)
from PySide6.QtWidgets import QApplication, QWidget


# ============================================================
# RENDSZERHANG FIGYELÉSE
# ============================================================

class AudioMonitor(QThread):
    audio_level = Signal(float)
    monitor_error = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def run(self):
        try:
            speaker = sc.default_speaker()

            if speaker is None:
                self.monitor_error.emit(
                    "Nem található alapértelmezett hangeszköz."
                )
                return

            loopback = sc.get_microphone(
                id=str(speaker.name),
                include_loopback=True,
            )

            with loopback.recorder(samplerate=22050) as recorder:
                while not self._stop_event.is_set():
                    audio = recorder.record(numframes=1024)

                    if audio is None or len(audio) == 0:
                        self.audio_level.emit(0.0)
                        continue

                    rms = float(np.sqrt(np.mean(np.square(audio))))
                    self.audio_level.emit(rms)

        except Exception as exc:
            if not self._stop_event.is_set():
                self.monitor_error.emit(str(exc))


# ============================================================
# ALEKSZA — LOW-POLY 3D ROBOTARC
# ============================================================

class AlekszaFace(QWidget):
    """
    Kódból generált, sokszögű, stilizált 3D robotarc.

    Kompatibilis metódusok:
        face.start_thinking()
        face.stop_thinking()
        face.set_thinking(True)
        face.set_thinking(False)

    A 3D-geometria háromdimenziós pontokból készül,
    amelyeket perspektivikusan vetítünk a PySide6 ablakra.
    Nem szükséges hozzá külön 3D-modell.
    """

    def __init__(self, monitor_audio=False, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Aleksza — 3D")
        self.resize(560, 700)
        self.setMinimumSize(360, 460)

        self.thinking = False
        self.animation_time = 0.0

        # Hang és száj
        self.audio_level = 0.0
        self.smoothed_audio = 0.0
        self.mouth_open = 0.0

        # Pislogás
        self.eye_open = 1.0
        self.blink_start = None
        self.blink_duration = 170.0
        self.next_blink = time.monotonic() + random.uniform(2, 5)

        # Fejmozgás beállításai
        self.head_yaw = 0.0
        self.head_pitch = 0.0

        # Hangfigyelő
        self.audio_monitor = None

        # Animáció
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_animation)
        self.timer.start(16)

        if monitor_audio:
            self.set_audio_monitoring(True)

    # --------------------------------------------------------
    # KÜLSŐ VEZÉRLÉS — kompatibilis az Assistant osztállyal
    # --------------------------------------------------------

    def start_thinking(self):
        self.thinking = True
        self.update()

    def stop_thinking(self):
        self.thinking = False
        self.update()

    def set_thinking(self, enabled):
        self.thinking = bool(enabled)
        self.update()

    # --------------------------------------------------------
    # HANGKEZELÉS
    # --------------------------------------------------------

    def receive_audio_level(self, level):
        self.audio_level = max(0.0, float(level))

    def handle_audio_error(self, message):
        print(f"[Aleksza hangfigyelés] {message}")

    # --------------------------------------------------------
    # ANIMÁCIÓ
    # --------------------------------------------------------

    @staticmethod
    def smoothstep(value):
        value = max(0.0, min(1.0, value))
        return value * value * (3.0 - 2.0 * value)

    def update_animation(self):
        self.animation_time += 0.016

        # Finom, simított hangszint.
        self.smoothed_audio += (
            self.audio_level - self.smoothed_audio
        ) * 0.35

        target = min(
            1.0,
            max(0.0, (self.smoothed_audio - 0.008) * 24.0),
        )

        self.mouth_open += (
            target - self.mouth_open
        ) * 0.45

        # A fej lassan mozog, gondolkodás közben élénkebben.
        speed = 1.15 if self.thinking else 0.7
        yaw_amount = 0.22 if self.thinking else 0.12

        self.head_yaw = (
            math.sin(self.animation_time * speed) * yaw_amount
        )
        self.head_pitch = (
            math.sin(self.animation_time * 0.65) * 0.045
        )

        # Pislogás.
        now = time.monotonic()

        if self.blink_start is None and now >= self.next_blink:
            self.blink_start = now
            self.blink_duration = random.uniform(130, 210)

        if self.blink_start is not None:
            progress = (
                (now - self.blink_start) * 1000
                / self.blink_duration
            )

            if progress >= 1:
                self.eye_open = 1.0
                self.blink_start = None
                self.next_blink = now + random.uniform(2, 5.5)

            elif progress < 0.45:
                self.eye_open = 1.0 - self.smoothstep(
                    progress / 0.45
                )

            else:
                self.eye_open = self.smoothstep(
                    (progress - 0.45) / 0.55
                )

        else:
            self.eye_open = 1.0

        self.update()

    # --------------------------------------------------------
    # 3D TRANSZFORMÁCIÓ ÉS PERSPEKTIVIKUS VETÍTÉS
    # --------------------------------------------------------

    def transform_point(self, point):
        x, y, z = point

        # Y tengely: fejfordítás.
        yaw = self.head_yaw
        x, z = (
            x * math.cos(yaw) + z * math.sin(yaw),
            -x * math.sin(yaw) + z * math.cos(yaw),
        )

        # X tengely: enyhe fel-le billentés.
        pitch = self.head_pitch
        y, z = (
            y * math.cos(pitch) - z * math.sin(pitch),
            y * math.sin(pitch) + z * math.cos(pitch),
        )

        # Finom lebegés.
        y += math.sin(self.animation_time * 1.3) * 3.0

        return x, y, z

    def project(self, point):
        x, y, z = self.transform_point(point)

        scale = min(
            self.width() / 560.0,
            self.height() / 700.0,
        )

        # Perspektivikus méretezés.
        camera_distance = 560.0
        perspective = camera_distance / max(
            300.0, camera_distance - z
        )

        screen_x = self.width() / 2 + x * scale * perspective
        screen_y = self.height() * 0.46 + y * scale * perspective

        return screen_x, screen_y, z

    def polygon3d(
        self, painter, points, fill,
        outline=None, line_width=1.0
    ):
        projected = [self.project(p) for p in points]

        polygon = QPolygonF([
            QPointF(x, y) for x, y, _ in projected
        ])

        if fill is None:
            painter.setBrush(Qt.BrushStyle.NoBrush)
        else:
            painter.setBrush(QBrush(QColor(fill)))

        if outline:
            painter.setPen(QPen(QColor(outline), line_width))
        else:
            painter.setPen(Qt.PenStyle.NoPen)

        painter.drawPolygon(polygon)

    def line3d(self, painter, points, color, width=1.0):
        projected = [self.project(p) for p in points]

        polygon = QPolygonF([
            QPointF(x, y) for x, y, _ in projected
        ])

        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(
            QColor(color),
            width,
            Qt.PenStyle.SolidLine,
            Qt.PenCapStyle.RoundCap,
            Qt.PenJoinStyle.RoundJoin,
        ))
        painter.drawPolyline(polygon)

    # --------------------------------------------------------
    # HÁTTÉR
    # --------------------------------------------------------

    def draw_background(self, painter):
        gradient = QLinearGradient(
            0, 0, self.width(), self.height()
        )
        gradient.setColorAt(0, QColor("#07111f"))
        gradient.setColorAt(0.5, QColor("#102337"))
        gradient.setColorAt(1, QColor("#040811"))

        painter.fillRect(
            self.rect(), QBrush(gradient)
        )

        cx = self.width() / 2
        cy = self.height() * 0.46

        pulse = (math.sin(self.animation_time * 3) + 1) / 2

        painter.setBrush(Qt.BrushStyle.NoBrush)

        for i in range(3):
            radius = (155 + i * 20) * min(
                self.width() / 560,
                self.height() / 700,
            )

            alpha = int(
                (18 + pulse * 22) if self.thinking else 12
            )

            painter.setPen(QPen(
                QColor(36, 184, 231, alpha - i * 3),
                1.2,
            ))

            painter.drawEllipse(
                QPointF(cx, cy),
                radius,
                radius * 1.12,
            )

        # Háttérpontok.
        painter.setPen(Qt.PenStyle.NoPen)

        for i in range(40):
            x = (i * 83 + 17) % max(1, self.width())
            y = (i * 137 + 29) % max(1, self.height())

            painter.setBrush(QColor(115, 190, 235, 35))
            painter.drawEllipse(x, y, 2, 2)

    # --------------------------------------------------------
    # LOW-POLY FEJGEOMETRIA
    # --------------------------------------------------------

    def draw_head(self, painter):
        # Lágyabb, nőiesebb fejforma, változatlan 10 pontos
        # low-poly gyűrűkkel.
        rings = [
            (-145, 48, 35),
            (-120, 70, 49),
            (-82, 88, 61),
            (-35, 94, 67),
            (10, 87, 63),
            (49, 73, 53),
            (81, 55, 40),
            (105, 32, 25),
            (116, 12, 10),
        ]

        segment_count = 10
        mesh = []

        for y, rx, rz in rings:
            ring = []

            for i in range(segment_count):
                angle = 2 * math.pi * i / segment_count

                ring.append((
                    math.sin(angle) * rx,
                    y,
                    math.cos(angle) * rz,
                ))

            mesh.append(ring)

        # Fülek a fej mögött: a belső fejforma részben eltakarja őket.
        for side in (-1, 1):
            x = side * 82

            # Külső, lekerekített low-poly fül.
            self.polygon3d(
                painter,
                [
                    (x, -24, 5),
                    (x + side * 13, -31, 10),
                    (x + side * 23, -17, 15),
                    (x + side * 24, 10, 17),
                    (x + side * 17, 31, 15),
                    (x + side * 5, 36, 10),
                    (x - side * 4, 19, 8),
                    (x - side * 5, -5, 8),
                ],
                "#34465f",
                "#8d9dbb",
                1.0,
            )

            # Finom belső fülív.
            self.polygon3d(
                painter,
                [
                    (x + side * 5, -15, 17),
                    (x + side * 14, -8, 20),
                    (x + side * 15, 10, 21),
                    (x + side * 8, 22, 19),
                    (x + side * 3, 12, 20),
                    (x + side * 3, -2, 20),
                ],
                "#26364d",
                "#758bab",
                0.7,
            )

            # Apró, meleg fényű fülrészlet.
            self.polygon3d(
                painter,
                [
                    (x + side * 7, 2, 21),
                    (x + side * 11, 5, 22),
                    (x + side * 9, 12, 21),
                    (x + side * 5, 9, 21),
                ],
                "#c58bb9",
                None,
            )

        # A fej sokszögű hálója.
        faces = []

        for r in range(len(mesh) - 1):
            for i in range(segment_count):
                j = (i + 1) % segment_count

                face = [
                    mesh[r][i],
                    mesh[r][j],
                    mesh[r + 1][j],
                    mesh[r + 1][i],
                ]

                average_z = sum(p[2] for p in face) / len(face)
                faces.append((average_z, face))

        faces.sort(key=lambda item: item[0])

        for average_z, face in faces:
            shade = int(max(0, min(18, (average_z + 65) * 0.12)))

            base = QColor("#30495f")
            color = QColor(
                min(255, base.red() + shade),
                min(255, base.green() + shade),
                min(255, base.blue() + shade),
            )

            self.polygon3d(
                painter,
                face,
                color.name(),
                "#526d87",
                0.65,
            )

        # Homlok: elegáns, enyhén ívelt páncél.
        self.polygon3d(
            painter,
            [
                (-68, -111, 35),
                (-48, -139, 38),
                (-17, -151, 39),
                (19, -150, 39),
                (49, -134, 36),
                (69, -108, 32),
                (47, -94, 50),
                (0, -87, 59),
                (-47, -94, 50),
            ],
            "#39465f",
            "#7786a6",
            0.9,
        )

        # Felső hajtömeg: sötétlila, lekerekített hatású low-poly forma.
        self.polygon3d(
            painter,
            [
                (-88, -76, 8),
                (-83, -119, 8),
                (-59, -153, 10),
                (-25, -173, 12),
                (16, -176, 12),
                (53, -157, 10),
                (81, -124, 8),
                (88, -82, 8),
                (61, -103, 34),
                (34, -119, 45),
                (0, -124, 49),
                (-35, -117, 43),
                (-62, -99, 30),
            ],
            "#211d38",
            "#665782",
            1.0,
        )

        # Fény a haj felső részén.
        self.polygon3d(
            painter,
            [
                (-56, -139, 19),
                (-31, -159, 19),
                (3, -164, 19),
                (31, -151, 18),
                (13, -143, 34),
                (-20, -141, 35),
            ],
            "#3d315d",
            "#8b70aa",
            0.7,
        )

        # Aszimmetrikus frufru: oldalra omló, lágyabb sziluett.
        self.polygon3d(
            painter,
            [
                (-65, -111, 39),
                (-49, -137, 43),
                (-20, -146, 46),
                (7, -140, 49),
                (35, -121, 47),
                (49, -96, 41),
                (22, -104, 54),
                (-2, -99, 59),
                (-29, -103, 55),
            ],
            "#292440",
            "#786492",
            0.8,
        )


        # Vékony, visszafogott fény a frufrun.
        self.line3d(
            painter,
            [
                (-43, -132, 46),
                (-19, -140, 49),
                (5, -137, 51),
            ],
            "#a18ac5",
            1.0,
        )

    # --------------------------------------------------------
    # SZEMEK
    # --------------------------------------------------------

    def draw_eye(self, painter, cx, cy):
        openness = max(0.06, self.eye_open)
        w = 30
        h = 12 * openness

        # Szemkeret.
        self.polygon3d(
            painter,
            [
                (cx - w, cy, 55),
                (cx - w * 0.65, cy - h, 61),
                (cx + w * 0.55, cy - h, 61),
                (cx + w, cy, 55),
                (cx + w * 0.55, cy + h * 0.55, 59),
                (cx - w * 0.6, cy + h * 0.55, 59),
            ],
            "#071522",
            "#547b92",
            1.0,
        )

        if self.eye_open <= 0.13:
            return

        # Az írisz enyhén elmozdul, hogy ne legyen teljesen statikus.
        ix = cx + math.sin(self.animation_time * 0.7) * 2.5

        self.polygon3d(
            painter,
            [
                (ix - 10, cy, 63),
                (ix - 5, cy - 8 * openness, 65),
                (ix + 4, cy - 8 * openness, 65),
                (ix + 10, cy, 63),
                (ix + 4, cy + 7 * openness, 65),
                (ix - 5, cy + 7 * openness, 65),
            ],
            "#20cce9",
            "#8af4ff",
            0.8,
        )

        # Pupilla.
        self.polygon3d(
            painter,
            [
                (ix - 3.5, cy - 5 * openness, 66),
                (ix + 3.5, cy - 5 * openness, 66),
                (ix + 3.5, cy + 5 * openness, 66),
                (ix - 3.5, cy + 5 * openness, 66),
            ],
            "#06101a",
        )

        # Fényes szemcsillanás.
        self.polygon3d(
            painter,
            [
                (ix - 5, cy - 6 * openness, 67),
                (ix - 1, cy - 6 * openness, 67),
                (ix - 1, cy - 2 * openness, 67),
            ],
            "#ffffff",
        )

    # --------------------------------------------------------
    # ROBOTARC RÉSZLETEI
    # --------------------------------------------------------

    def draw_face_details(self, painter):
        # Lágyabb szemöldökpanelek.
        for side in (-1, 1):
            self.polygon3d(
                painter,
                [
                    (side * 78, -39, 49),
                    (side * 52, -48, 56),
                    (side * 27, -43, 61),
                    (side * 18, -35, 62),
                    (side * 49, -34, 59),
                    (side * 69, -31, 52),
                ],
                "#29394f",
                "#7587a5",
                0.7,
            )

        # A meglévő animált szemek megtartása.
        self.draw_eye(painter, -43, -18)
        self.draw_eye(painter, 43, -18)

        # Finom orrhíd.
        self.polygon3d(
            painter,
            [
                (-7, -1, 62),
                (0, -10, 67),
                (7, -1, 62),
                (6, 17, 65),
                (0, 25, 68),
                (-6, 17, 65),
            ],
            "#405c73",
            "#829bb4",
            0.6,
        )

        # Visszafogott orrhegy.
        self.polygon3d(
            painter,
            [
                (-8, 22, 63),
                (0, 19, 68),
                (8, 22, 63),
                (4, 28, 65),
                (-4, 28, 65),
            ],
            "#52647c",
            "#91a1bb",
            0.5,
        )

        # Beszéd közben nyíló, enyhén mosolygós száj.
        opening = max(0.0, min(0.5, self.mouth_open))
        mouth_w = 22 + opening * 5
        mouth_h = 1.5 + opening * 15

        self.polygon3d(
            painter,
            [
                (-mouth_w, 58, 58),
                (-mouth_w * 0.65, 55, 62),
                (-mouth_w * 0.30, 57 - mouth_h, 65),
                (0, 56 - mouth_h * 0.85, 66),
                (mouth_w * 0.30, 57 - mouth_h, 65),
                (mouth_w * 0.65, 55, 62),
                (mouth_w, 58, 58),
                (mouth_w * 0.58, 61 + mouth_h * 0.35, 62),
                (0, 62 + mouth_h, 64),
                (-mouth_w * 0.58, 61 + mouth_h * 0.35, 62),
            ],
            "#100f20",
            "#8a80ad",
            0.9,
        )


        # Beszéd közben halványan látható belső szájrész.
        if opening > 0.25:
            self.polygon3d(
                painter,
                [
                    (-mouth_w * 0.42, 57, 66),
                    (mouth_w * 0.42, 57, 66),
                    (mouth_w * 0.30, 59 + min(6, opening * 8), 67),
                    (-mouth_w * 0.30, 59 + min(6, opening * 8), 67),
                ],
                "#d49acb",
                None,
            )



    # --------------------------------------------------------
    # ÁLLAPOTKIJELZÉS
    # --------------------------------------------------------

    def draw_status(self, painter):
        if self.thinking:
            status = "FELDOLGOZÁS..."
            color = QColor("#61d5ff")
        elif self.smoothed_audio > 0.02:
            status = "BESZÉL"
            color = QColor("#78f0c5")
        else:
            status = "ALEXA ONLINE"
            color = QColor("#90abc6")

        painter.setPen(color)

        font = painter.font()
        font.setFamily("Segoe UI")
        font.setPointSize(20)
        font.setBold(True)
        painter.setFont(font)

        painter.drawText(
            self.rect().adjusted(0, 0, 0, -24),
            Qt.AlignmentFlag.AlignHCenter
            | Qt.AlignmentFlag.AlignBottom,
            status,
        )

        pulse = (math.sin(self.animation_time * 3) + 1) / 2
        alpha = int(150 + pulse * 105)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(
            color.red(), color.green(), color.blue(), alpha
        ))

        cx = self.width() / 2
        painter.drawEllipse(
            int(cx - 3), self.height() - 38 -100, 20, 20
        )

    # --------------------------------------------------------
    # KIRAJZOLÁS
    # --------------------------------------------------------

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing, True
        )

        self.draw_background(painter)
        self.draw_head(painter)
        self.draw_face_details(painter)
        self.draw_status(painter)

        painter.end()

    # --------------------------------------------------------
    # LEÁLLÍTÁS
    # --------------------------------------------------------

    def closeEvent(self, event):
        if self.audio_monitor is not None:
            self.audio_monitor.stop()

            if not self.audio_monitor.wait(1500):
                print(
                    "[Aleksza] A hangfigyelő még leállás alatt van."
                )

        super().closeEvent(event)


    def set_audio_monitoring(self, enabled: bool):
        """A rendszerhang figyelésének külső vezérlése."""
        enabled = bool(enabled)

        if enabled:
            if self.audio_monitor is not None and self.audio_monitor.isRunning():
                return

            self.audio_monitor = AudioMonitor(self)

            # A hangszintet átadjuk az arc animációjának.
            self.audio_monitor.audio_level.connect(
                self.receive_audio_level
            )

            # A hangfigyelési hibákat is jelezzük.
            self.audio_monitor.monitor_error.connect(
                self.handle_audio_error
            )

            self.audio_monitor.start()
            print("[Aleksza] Hangfigyelés bekapcsolva.")

        else:
            if self.audio_monitor is not None:
                monitor = self.audio_monitor
                monitor.stop()
                monitor.wait()
                self.audio_monitor = None

            self.audio_level = 0.0
            self.smoothed_audio = 0.0
            self.mouth_open = 0.0
            self.update()

            print("[Aleksza] Hangfigyelés kikapcsolva.")

# ============================================================
# ÖNÁLLÓ TESZT
# ============================================================

if __name__ == "__main__":
    app = QApplication.instance()

    if app is None:
        app = QApplication(sys.argv)

    face = AlekszaFace(monitor_audio=True)
    face.show()

    sys.exit(app.exec())