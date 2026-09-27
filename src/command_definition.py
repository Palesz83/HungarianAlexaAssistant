import datetime
import threading

import sounddevice as sd
import soundfile as sf


class CommandEngine:

    def __init__(self):

        # ============================================
        # TIMER
        # ============================================

        self.running_timers = []

        # ============================================
        # ALARM
        # ============================================

        self.alarm_active = False

        self.alarm_thread = None

        self.alarm_stop_event = threading.Event()

        # WAV betöltése
        self.wavefile, self.fs = sf.read(
            "resources/alert.wav",
            dtype="float32"
        )

        print(
            f"[ALARM] WAV betöltve: "
            f"{self.fs} Hz, "
            f"{len(self.wavefile)} sample"
        )

        # ============================================
        # JÁTÉK
        # ============================================

        self.game_active = False
        self.current_game = None
        self.game_history = []

        # ============================================
        # AUDIO LOCK
        # ============================================

        self.audio_lock = threading.Lock()

    # ==================================================
    # ALARM
    # ==================================================

    def _alarm_worker(self):

        print(
            "\n\n[ALARM] 🔔 Idő lejárt! "
            "A csengő aktív!"
        )

        try:

            while not self.alarm_stop_event.is_set():

                print(
                    "[ALARM] WAV lejátszás..."
                )

                # A WAV saját mintavételi frekvenciáját használjuk.
                # Nem módosítjuk az sd.default.samplerate értékét.

                with self.audio_lock:

                    sd.play(
                        self.wavefile,
                        self.fs,
                        blocking=True
                    )

                print(
                    "[ALARM] WAV lejátszás kész."
                )

                # 5 másodperc várakozás.
                # Az Event miatt a várakozás megszakítható.

                self.alarm_stop_event.wait(
                    timeout=5
                )

        except Exception as e:

            print(
                "[ALARM ERROR]",
                type(e).__name__,
                e
            )

        finally:

            try:
                sd.stop()
            except Exception:
                pass

            self.alarm_active = False

            print(
                "[ALARM] 🛑 A csengő leállt."
            )

    def _start_alarm(self):

        # Ha már szól az alarm,
        # ne indítsunk újabb alarm szálat.

        if self.alarm_active:
            return

        self.alarm_active = True

        self.alarm_stop_event.clear()

        self.alarm_thread = threading.Thread(
            target=self._alarm_worker,
            daemon=True,
            name="AlarmThread"
        )

        self.alarm_thread.start()

    def _stop_alarm(self):

        self.alarm_stop_event.set()

        try:
            sd.stop()
        except Exception:
            pass

        self.alarm_active = False

    # ==================================================
    # TIMER LEJÁRT
    # ==================================================

    def _timer_finished(self):

        current_timer = threading.current_thread()

        self.running_timers = [
            timer
            for timer in self.running_timers
            if timer is not current_timer
        ]

        print(
            "[TIMER] Idő lejárt."
        )

        self._start_alarm()

    # ==================================================
    # TIMER BEÁLLÍTÁS
    # ==================================================

    def handle_timer(
        self,
        duration_minutes
    ):

        if duration_minutes is None:

            return (
                "Nem értettem, mennyi időre "
                "állítsam az időzítőt."
            )

        try:

            duration_minutes = int(
                duration_minutes
            )

        except (
            ValueError,
            TypeError
        ):

            return "Nem értettem az időt."

        if duration_minutes <= 0:

            return (
                "Az időzítőnek legalább "
                "egy percesnek kell lennie."
            )

        # --------------------------------------------
        # Korábbi timerek törlése
        # --------------------------------------------

        for timer in self.running_timers:

            timer.cancel()

        self.running_timers.clear()

        # --------------------------------------------
        # Ha éppen szól az alarm,
        # azt is állítsuk le.
        # --------------------------------------------

        if self.alarm_active:

            self._stop_alarm()

        # --------------------------------------------
        # Új timer
        # --------------------------------------------

        seconds = duration_minutes * 60

        timer = threading.Timer(
            seconds,
            self._timer_finished
        )

        self.running_timers.append(
            timer
        )

        timer.start()

        print(
            f"[TIMER] "
            f"{duration_minutes} perc"
        )

        return (
            f"Rendben, "
            f"{duration_minutes} perc múlva szólok."
        )

    # ==================================================
    # TIMER / ALARM LEÁLLÍTÁS
    # ==================================================

    def handle_stop_timer(self):

        # --------------------------------------------
        # Alarm leállítása
        # --------------------------------------------

        if self.alarm_active:

            self._stop_alarm()

            for timer in self.running_timers:

                timer.cancel()

            self.running_timers.clear()

            return (
                "A csengőt leállítottam."
            )

        # --------------------------------------------
        # Timer leállítása
        # --------------------------------------------

        if self.running_timers:

            for timer in self.running_timers:

                timer.cancel()

            self.running_timers.clear()

            return (
                "Az időzítőt leállítottam."
            )

        return (
            "Nincs futó időzítő."
        )

    # ==================================================
    # PLAY
    # ==================================================

    def handle_play(self):

        print(
            "[PLAYER] ▶ Play"
        )

        return (
            "Elindítom a lejátszást."
        )

    # ==================================================
    # TIME
    # ==================================================

    def handle_time(self):

        now = datetime.datetime.now()

        return (
            f"Az idő "
            f"{now.hour} óra "
            f"{now.minute} perc."
        )

    # ==================================================
    # GAME
    # ==================================================

    def start_game(
        self,
        game_name
    ):

        self.game_active = True

        self.current_game = game_name

        self.game_history = []

        print(
            f"[GAME] Játék indítása: "
            f"{game_name}"
        )

    def add_game_turn(
        self,
        user_text,
        assistant_text
    ):

        self.game_history.append({
            "role": "user",
            "content": user_text
        })

        self.game_history.append({
            "role": "assistant",
            "content": assistant_text
        })

    def stop_game(self):

        print(
            "[GAME] Játék vége."
        )

        self.game_active = False

        self.current_game = None

        self.game_history.clear()

    def get_game_context(self):

        return {
            "active": self.game_active,
            "game": self.current_game,
            "history": self.game_history
        }

    # ==================================================
    # WEB SEARCH
    # ==================================================

    def handle_web_search(
        self,
        response
    ):

        """
        A web_search action tényleges végrehajtását
        az ollama_interpreter.py végzi.

        Ez a függvény csak akkor hasznos,
        ha valamilyen más komponens közvetlenül
        a CommandEngine-en keresztül szeretné kezelni.

        Normál esetben ide nem jut el a web_search,
        mert az ollama_interpreter.py már feldolgozza.
        """

        return response

    # ==================================================
    # COMMAND PROCESSOR
    # ==================================================

    def process_command(
        self,
        command
    ):

        if not command:
            return None

        action = command.get(
            "action"
        )

        print(
            "[COMMAND ENGINE]",
            command
        )

        # ============================================
        # TIMER
        # ============================================

        if action == "set_timer":

            return self.handle_timer(
                command.get(
                    "duration_minutes"
                )
            )

        # ============================================
        # TIMER STOP
        # ============================================

        elif action == "stop_timer":

            return self.handle_stop_timer()

        # ============================================
        # PLAY
        # ============================================

        elif action == "play":

            return self.handle_play()

        # ============================================
        # TIME
        # ============================================

        elif action == "get_time":

            return self.handle_time()

        # ============================================
        # WEB SEARCH
        # ============================================

        elif action == "web_search":

            return self.handle_web_search(
                command.get(
                    "response",
                    ""
                )
            )

        # ============================================
        # GAME START
        # ============================================

        elif action == "game_start":

            game_name = command.get(
                "game"
            )

            self.start_game(
                game_name
            )

            return command.get(
                "response"
            )

        # ============================================
        # GAME END
        # ============================================

        elif action == "game_end":

            response = command.get(
                "response"
            )

            self.stop_game()

            return response

        # ============================================
        # CHAT
        # ============================================

        elif action == "chat":

            return command.get(
                "response"
            )

        return None


engine = CommandEngine()