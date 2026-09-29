import re


class CommandEngine:
    def __init__(self):
        # Itt tárolódnak a regisztrált függvények
        self._commands = {}

    def register(self, keyword):
        """
        Ez a 'dekorátor' függvény.
        Segít regisztrálni a függvényt egy kulcsszóhoz.
        """

        def decorator(func):
            # A kulcsszót nagybetűssé tesszük az egyértelműség miatt
            self._commands[keyword.upper()] = func
            return func

        return decorator

    def process_string(self, input_string):
        if not input_string:
            return None

        found_tokens = re.findall(r"\{.*?\}", input_string)
        results = []

        for token in found_tokens:
            # A keresésnél a tokenet nagybetűssé konvertáljuk
            action = self._commands.get(token.upper())

            if action:
                results.append(action())
            else:
                print(f"Ismeretlen kulcsszó: {token}")

        return "\n".join(results) if results else None

    def process_string_2(self, input_string):
        if not input_string:
            return None

        results = []

        # Ez a Regex egyszerűen kinyeri mindent, ami {} között van
        # Például: "{10}{IDOZITO}{HOGYVAGY}" -> ['10', 'IDOZITO', 'HOGYVAGY']
        pattern = r"\{([^}]+)\}"
        tokens = re.findall(pattern, input_string)

        current_param = None  # Ez a "memória" a számok tárolására

        for token in tokens:
            # Megvizsgáljuk, hogy a token egy szám vagy egy kulcsszó
            if token.isdigit():
                # Ha szám (pl. "10"), csak elmentjük a memóriába
                current_param = int(token)
            else:
                # Ha szöveg (pl. "IDOZITO"), keresjük a parancsot
                lookup_key = "{" + token + "}"
                action = self._commands.get(lookup_key)

                if action:
                    # Ha találtunk parancsot, átadjuk neki a megjegyzött paramétert
                    # Ha nem volt paraméter, a None (vagy 0) megérkezik
                    results.append(action(current_param))

                    # A parancs futtatása után töröljük a paramétert,
                    # hogy ne maradjon meg a következő parancsnál is!
                    current_param = None
                else:
                    print(f"Ismeretlen kulcsszó: {lookup_key}")

        return "\n".join(results) if results else None

# Helper to handle the None group from regex
def ast_none_to_str(val):
    return val
