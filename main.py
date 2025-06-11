import speech_recognition as sr
from gtts import gTTS
import os
import requests

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

def make_llm_request(prompt):
    data = {
        "model": f"{MODEL_NAME}",
        "messages": [
            {"role": "user", "content": f"{prompt}"},
        ],
        "temperature": 0.7
    }
    request = requests.post(url, headers=headers, json=data)
    return request.json()["choices"][0]["message"]["content"]

def contains_word(text, word_list):
    text_lower = text.lower()
    for word in word_list:
        if word.lower() in text_lower:
            return word
    return None

### Methods to get speak to the user and get input from user voice

def say(message):
    message_obj = gTTS(text=message, lang=language, slow=False)
    message_obj.save("message.mp3")
    os.system(f"{audio_player} message.mp3")

def get_user_input():
    # Record user request
    with sr.Microphone() as source:
        r.adjust_for_ambient_noise(source, duration=1)
        print("Listening...")
        audio_text = r.record(source, duration=duration)
        print("Time over")
        try:
            return r.recognize_google(audio_text)
        except:
            return ""

def categorize_user_request(categories):
    # Record user request
    with sr.Microphone() as source:
        category = None
        while category is None:
            r.adjust_for_ambient_noise(source, duration=1)
            print("Listening...")
            audio_text = r.record(source, duration=duration)
            print("Time over")

            try:
                user_request = r.recognize_google(audio_text)
                print(f"Recorded user request: {user_request}")
                llm_reply = make_llm_request(f"Which category from {categories} fits the sentence: '{user_request}' the best? Answer only with the category that matches")
                print(f"LLM categorized the user request as: {llm_reply}")
                category = contains_word(llm_reply, categories)
                print(category)
            except:
                print("Couldn't tts or categorize user request")

            if category is None:
                say("I didn't get that, please repeat")
        return category

if __name__ == '__main__':
    ### Let user choose an action
    say("I can help you with digital government services such as filling out a tax form, setting up a bank account or renewing an identification card. What do you want to do?")
    user_confirmed = "false"
    user_request_category = None

    while user_confirmed == "false":
        user_request_category = categorize_user_request(["Tax form", "Bank account", "Renew ID card"])
        say(f"Did I understand you correctly, you want to proceed with action {user_request_category}?")
        user_confirmed = categorize_user_request(["true", "false"])

        if user_confirmed == "false":
            say(f"Sorry, what do you want to do instead?")

    say(f"I will guide you through the steps to {user_request_category}")

    #... continue process








