# ICT for the Global North - Spoken feedback for the visually impaired (Group 20)
## 📝 About
This project is a voice-based assistant designed to help visually impaired users access Dutch governmental services. It enables users to navigate websites and complete PDF forms using only their voice, removing the need for visual interaction.

## 🎮 Demos

We have provided three different demos, each focused on a specific task:

- **Applying for Tax Benefits — `fill_pdf_document.py`**  
  You are guided through the process of completing a Dutch tax form. The system fills out a PDF form that you can submit to the authorities:  
  [Model opgaaf gegevens voor de loonheffingen (LH0082Z)](https://download.belastingdienst.nl/belastingdienst/docs/model_opgaaf_gegevens_loonheffingen_lh0082z11fol.pdf)<br>
  🎥 [Watch the improved demo video](demo_videos/fill_pdf_document.mp4)

- **Eligibility for Benefits — `toeslagen.py`**  
  You are guided through the Dutch government's official **"Proefberekening Toeslagen"** (benefits eligibility calculator):  
  [Proefberekening Toeslagen](https://www.belastingdienst.nl/wps/wcm/connect/nl/toeslagen/content/hulpmiddel-proefberekening-toeslagen)  
  The assistant collects the necessary personal information and makes a request on your behalf to the website to check your eligibility for healthcare, rental, or child benefits.<br>
  🎥 [Watch the improved demo video](demo_videos/toeslagen.mp4)

- **Garbage Disposal Directions — `afval.py`**  
  This demo helps you find the nearest garbage disposal containers in Amsterdam using the city's official map:  
  [Afvalcontainers Kaart Amsterdam](https://kaart.amsterdam.nl/afvalcontainers)<br>
  🎥 [Watch the improved demo video](demo_videos/afval.mp4)


> ⚠️ **Note:** As this is a prototype, the full user interaction is not implemented. Some input values are currently hardcoded to demonstrate the system’s functionality.

> ⚠️ **Note:** Voice recognition may not work for certain inputs. When prompted by the system, you can try interacting with the system using personal details like your own **name**, **date of birth**, etc. If your queries are not understood, please fall back on the **example sentences** provided as comments in the demo files.

> ⚠️ **Note:** When prompted to confirm an input (e.g. when asked: "Did I understand you correctly?"), please say "yes you did" or "no you did not". Other answers are not reliably recognized 

### 🎥 Can't run the code?

If you're unable to set up or run the project locally, don't worry!  
We've included demonstration videos for all three tasks in the [`demo_videos`](demo_videos) folder.  
These videos show exactly how the system is intended to work.

## ⚙️ Installation

### Browser
Some features require a browser to run. The supported browsers are Chrome and Chromium.

### LM Studio (for ML model execution)
LM Studio allows you to run a machine learning model locally:  
<https://lmstudio.ai/>

- Download Google's smallest model: `gemma-3-1b`.  
  This can be done via the top bar in LM Studio.
- Ensure LM Studio has a local endpoint by opening the developer settings and setting the application status to "running".

> ⚠️ **Note:** LM Studio is **not compatible with Intel Macs**. It currently supports only Apple Silicon (M1/M2) and Windows/Linux systems

### Python Packages
The project has various dependencies which need to be installed.

#### Virtual Environment (Optional)
First create a virtual environment. This is optional, but recommended.
```bash
  python -m venv venv
  source venv/bin/activate
```
#### Installing Packages
Make sure all the packages in requirements.txt are installed successfully.
```bash
  pip install -r requirements.txt
```

### Model for spaCy
spaCy is a library for word recognition in sentences. You need to download an ML model for it with:
```bash
  python -m spacy download en_core_web_sm
```

### Tesseract OCR (System Dependency)
The "Read BSN from camera" feature requires [Tesseract OCR](https://github.com/tesseract-ocr/tesseract).  
Install it using the instructions below, depending on your operating system:

- **Ubuntu/Debian:** `sudo apt-get install tesseract-ocr`
- **macOS (with Homebrew):** `brew install tesseract`
- **Windows:** Download and install from [here](https://github.com/tesseract-ocr/tesseract)

## 💻 Operating System Requirements

### Linux
#### Audio Player
You need to install the audio player **mpv**:  
<https://mpv.io/>

### Intel Mac

#### Alternative to LM Studio
As an alternative to LM Studio, you need to install and run **llama2** locally:
<https://ollama.com/library/llama3>