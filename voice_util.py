import speech_recognition as sr
from gtts import gTTS
import os
import requests
import util

audio_player = "mpv" #TODO: Specify the cmd audio player for your operating system
''' config for speech recognition '''
r = sr.Recognizer()
duration = 5 # record time in seconds
''' config for gTTS (audio output) '''
language = 'en'
''' config for LLM '''
MODEL_NAME = "gemma-3-1b"
url = "http://localhost:1234/v1/chat/completions"
headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer lm-studio"
}

### Helper methods

def _make_llm_request(prompt):
    data = {
        "model": f"{MODEL_NAME}",
        "messages": [
            {"role": "user", "content": f"{prompt}"},
        ],
        "temperature": 0.7
    }
    request = requests.post(url, headers=headers, json=data)
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

def say(message):
    """
    play a message as audio
    :param message:
    :return:
    """
    message_obj = gTTS(text=message, lang=language, slow=False)
    message_obj.save("message.mp3")
    os.system(f"{audio_player} message.mp3")

def get_user_input(input_type):
    """
    Get user input from voice, the input is extracted based on user_input_type
    :param input_type:
    :return:
    """
    # Record user request
    user_input = None
    while user_input is None:
        with sr.Microphone() as source:
            r.adjust_for_ambient_noise(source, duration=0.25)
            print("Listening...")
            audio_text = r.record(source, duration=duration)
            print("Time over")
            try:
                user_input = r.recognize_google(audio_text)
                user_input = util.extract(input_type, user_input)
                break
            except:
                # TODO: Here it would be nice if we can prompt the user if they need help with the question
                # TODO: maybe passing the help string to the function in action_chain
                say("I didn't get that, please repeat")
    return user_input

# TODO: remove categorize_user_input?
# Categorize user input essentially does the same as get_user_input. It just gives a bit more control by allowing
# us to specify a category list. Should we remove this function?
def categorize_user_input(categories):
    """
    Categorize the user input from voice based on
    :param categories: a string list of categories
    :return:
    """
    # Record user request
    category = None
    while category is None:
        with sr.Microphone() as source:
            r.adjust_for_ambient_noise(source, duration=0.25)
            print("Listening...")
            audio_text = r.record(source, duration=duration)
            print("Time over")

        try:
            user_request = r.recognize_google(audio_text)
            print(f"Recorded user request: {user_request}")
            llm_reply = _make_llm_request(f"Which category from {categories} fits the sentence: '{user_request}' the best? Answer only with the category that matches")
            print(f"LLM categorized the user request as: {llm_reply}")
            category = _contains_word(llm_reply, categories)
        except:
            print("Couldn't tts or categorize user request")

        if category is None:
            say("I didn't get that, please repeat")
    return category








