# HungarianAlexaAssistant
Hungarian voice assistant capable of running on a GPU.

# Wakeup detection

project/<br>
└── models/<br>
&nbsp;&nbsp;&nbsp;&nbsp;└── wakeword/<br>

    
sherpa-onnx-kws-zipformer-gigaspeech-3.3M-2024-01-01 <br>
You need to download: kws-model.tar.bz2<br>
    
[https://k2-fsa.github.io/sherpa/onnx/](https://github.com/k2-fsa/sherpa-onnx/releases/download/kws-models/sherpa-onnx-kws-zipformer-gigaspeech-3.3M-2024-01-01.tar.bz2)<br>

# Installation

- python verison 3.9.13<br>

- Creating virtual environment<br>
py -3.9 -m venv .venv<br>


- Write-Host "Activating virtual environment..."<br>
& .\.venv\Scripts\Activate.ps1<br>

- Installing locked dependencies...<br>
python -m pip install -r requirements-lock.txt<br>

- Running the script.<br>
python.exe assistant.py<br>

- After you can say 
  - "Alexa, mennyi a pontos idő?"
  - "Alexa, állíts időzítőt 5 percre"
  - "Alexa, időzítőt stop"
  - "Alexa, Kezdjük a játékot"
    








