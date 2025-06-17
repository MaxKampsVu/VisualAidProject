import speech_recognition as sr
from gtts import gTTS
import os
import requests
import util
import platform
import traceback

import sys

audio_player = "mpv" 
environment = "linux"

if sys.platform.startswith("linux"):
    print("Running on Linux")
elif sys.platform == "darwin":
    print("Running on macOS")
    audio_player = "afplay"
    environment = "mac"

    ### Differnt model (llama2) request
    MODEL_NAME = "llama2"
    url = "http://localhost:11434/api/generate"
    headers = {
        "Content-Type": "application/json"
    }
else:
    print(f"Running on unknown platform: {sys.platform}")

''' config for speech recognition '''
r = sr.Recognizer()
pause_threshold_spelling = 2.0 # pauses between words when spelling
pause_threshold_normal = 1.0 # pauses between words for normal sentences
timeout = 3 # wait time until user speaks
phrase_time_limit = 20 # maximum record time
duration = 5 # record time in seconds
''' config for gTTS (audio output) '''
language = 'en'
''' config for LLM '''
MODEL_NAME = "google/gemma-3-1b"
url = "http://localhost:1234/v1/chat/completions"
headers = {
   "Content-Type": "application/json",
  "Authorization": "Bearer lm-studio"
}

### Helper methods

def _make_llm_request(prompt):
    if environment == "mac":
        data = {
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": False,  # Set to True if you want streamed output
            "temperature": 0.7
        }

        response = requests.post(url, headers=headers, json=data)
        return response.json()["response"]
    else:
        data = {
            "model": f"{MODEL_NAME}",
            "messages": [
                {"role": "user", "content": f"{prompt}"},
            ],
            "temperature": 0.7
        }
        request = requests.post(url, headers=headers, json=data)
        print(request.json())
        return request.json()["choices"][0]["message"]["content"]



def _contains_word(text, word_list):
    """
    Check if text contains a word from word_list
    :param text:
    :param word_list:
    :return: a word from word_list or None
    """
    text_lower = text.lower()
    for word in word_list:
        if word.lower() in text_lower:
            return word
    return None

### Methods to get speak to the user and get input from user voice
def _record_user(input_type):
    if input_type == util.INPUT_TYPE.SPELLING:
        r.pause_threshold = pause_threshold_spelling
    else:
        r.pause_threshold = pause_threshold_normal

    with sr.Microphone() as source:
        r.adjust_for_ambient_noise(source, duration=0.25)
        print("Listening...")
        return r.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)

def say(message):
    """
    play a message as audio
    :param message:
    :return:
    """
    print("Talking... ")
    message_obj = gTTS(text=message, lang=language, slow=False)
    message_obj.save("message.mp3")
    null_device = "nul" if platform.system() == "Windows" else "/dev/null" # Redirect audio_player console printing
    os.system(f"{audio_player} message.mp3 > {null_device} 2>&1")



def get_user_input(input_type):
    """
    Get user input from voice, the input is extracted based on user_input_type
    :param input_type:
    :return:
    """
    # Record user request
    user_input = None
    r = sr.Recognizer()

    while user_input is None:
        try:
            audio_text = _record_user(input_type)

            print("Processing input...")
            spoken_text = r.recognize_google(audio_text)
            print(f"Recorded user input: {spoken_text}")

            user_input = util.extract(input_type, spoken_text)
            print(f"Extracted input: '{user_input}' for type '{input_type}'")

        except sr.WaitTimeoutError:
            print("[Timeout] No speech detected within the timeout period.")
        except sr.UnknownValueError:
            print("[Warning] Could not understand the audio.")
        except sr.RequestError as e:
            print("[Error] Could not reach the speech recognition service.")
            print(f"Details: {e}")
        except Exception as e:
            print("[Unexpected Error] while processing user input:")
            traceback.print_exc()
        if user_input is None:
            say("I didn't understand that. Please try again.")

    return user_input

def categorize_user_input(categories):
    """
    Categorize the user input from voice using LLM and a list of predefined categories.

    :param categories: list[str] - predefined category options
    :return: str - the matched category
    """
    category = None
    r = sr.Recognizer()

    while category is None:
        try:
            audio_text = _record_user(None)

            print("Processing input...")
            user_input = r.recognize_google(audio_text)
            print(f"Recorded user input: {user_input}")

            prompt = (
                f"Which category from the list {categories} fits the sentence: "
                f"'{user_input}' the best? Only reply with the matching category name."
            )
            llm_reply = _make_llm_request(prompt)
            print(f"LLM categorized the input as: {llm_reply}")

            category = _contains_word(llm_reply, categories)

        except sr.UnknownValueError:
            print("[Warning] Could not understand the audio.")
        except sr.RequestError as e:
            print("[Error] Could not reach the speech recognition service.")
            print(f"Details: {e}")
        except Exception as e:
            print("[Unexpected Error] while categorizing user input:")
            traceback.print_exc()

        if category is None:
            say("I didn't understand that. Please try again.")

    return category



try:
    # Check if LM Studio is running by sending a request
    if environment == "linux":
        response = requests.get("http://localhost:1234", timeout=2)
        print("[SUCCESS] LM studio online")
    elif environment == "mac":
        # Check for llama2 model availability
        response = requests.get("http://localhost:11434/api/models", timeout=2)
        print("[SUCCESS] Llama2 model available")

    print(response)
except requests.RequestException:
    print("[ERROR] Couldn't reach LM studio, did you start it?")








