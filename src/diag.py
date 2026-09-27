import sys
import platform
import importlib.util
import subprocess


def section(title):
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


def package_version(package_name):
    try:
        from importlib.metadata import version
        return version(package_name)
    except Exception:
        return "NOT INSTALLED"


section("SYSTEM")

print("Python:")
print(" ", sys.version)

print("Platform:")
print(" ", platform.platform())

print("Machine:")
print(" ", platform.machine())

print("Processor:")
print(" ", platform.processor())


section("PYTORCH")

try:
    import torch

    print("PyTorch:")
    print(" ", torch.__version__)

    print("torch.cuda.is_available():")
    print(" ", torch.cuda.is_available())

    print("torch.cuda.device_count():")
    print(" ", torch.cuda.device_count())

    if torch.cuda.is_available():
        for i in range(torch.cuda.device_count()):
            print(f"CUDA device {i}:")
            print(" ", torch.cuda.get_device_name(i))

    print("Torch backends:")

    if hasattr(torch.backends, "mps"):
        print(" MPS:", torch.backends.mps.is_available())

except Exception as e:
    print("PyTorch ERROR:")
    print(" ", type(e).__name__, e)


section("DIRECTML")

try:
    import torch_directml

    print("torch-directml:")
    print(" ", package_version("torch-directml"))

    dml = torch_directml.device()

    print("DirectML device:")
    print(" ", dml)

    # Teszt: tényleges tensor létrehozás DirectML-en
    import torch

    x = torch.tensor([1, 2, 3], device=dml)

    print("DirectML tensor:")
    print(" ", x)

    print("Tensor device:")
    print(" ", x.device)

except Exception as e:
    print("DirectML ERROR:")
    print(" ", type(e).__name__, e)


section("COQUI TTS")

try:
    import TTS

    print("TTS:")
    print(" ", package_version("TTS"))
    print("TTS module:")
    print(" ", TTS.__file__)

except Exception as e:
    print("TTS ERROR:")
    print(" ", type(e).__name__, e)


section("WHISPER")

try:
    import whisper

    print("openai-whisper:")
    print(" ", package_version("openai-whisper"))

    print("Whisper module:")
    print(" ", whisper.__file__)

    print("Whisper device selection:")

    model = whisper.load_model("tiny")

    print(" model.device:")
    print(" ", model.device)

except Exception as e:
    print("Whisper ERROR:")
    print(" ", type(e).__name__, e)


section("SHERPA-ONNX")

try:
    import sherpa_onnx

    print("sherpa-onnx:")
    print(" ", package_version("sherpa-onnx"))

    print("sherpa_onnx module:")
    print(" ", sherpa_onnx.__file__)

except Exception as e:
    print("Sherpa ERROR:")
    print(" ", type(e).__name__, e)


section("ONNX RUNTIME")

try:
    import onnxruntime

    print("onnxruntime:")
    print(" ", onnxruntime.__version__)

    print("Execution providers:")
    for provider in onnxruntime.get_available_providers():
        print(" ", provider)

except Exception as e:
    print("ONNX Runtime:")
    print(" ", type(e).__name__, e)


section("INSTALLED RELEVANT PACKAGES")

packages = [
    "torch",
    "torchaudio",
    "torchvision",
    "torch-directml",
    "coqui-tts",
    "openai-whisper",
    "sherpa-onnx",
    "sherpa-onnx-core",
    "onnxruntime",
    "transformers",
    "sounddevice",
    "soundfile",
    "SpeechRecognition",
]

for package in packages:
    print(f"{package:25} {package_version(package)}")


section("WINDOWS GPU")

try:
    result = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            "Get-CimInstance Win32_VideoController | "
            "Select-Object Name,DriverVersion,AdapterRAM | "
            "Format-List"
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )

    print(result.stdout)

except Exception as e:
    print("GPU information ERROR:")
    print(" ", type(e).__name__, e)


section("CURRENT APPLICATION DEVICE LOGIC")

try:
    import torch

    device = "cuda" if torch.cuda.is_available() else "cpu"

    print("Current voice_recognation.py style:")
    print(" device =", device)

except Exception as e:
    print("ERROR:")
    print(" ", type(e).__name__, e)


section("DONE")

print()
print("Diagnostics completed.")