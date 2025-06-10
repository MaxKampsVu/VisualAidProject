from pyexpat.errors import messages

import speech_recognition as sr
from gtts import gTTS
import os

#
audio_player = "mpv" #TODO: Specify the cmd audio player for your operating system

# config for speech recognition
r = sr.Recognizer()
timeout = 5 # maximum number of seconds that listen() will wait for a phrase to start
phrase_time_limit = 20 # maximum number of seconds that listen() will allow a phrase to continue after it has started
# config for gTTS (audio output )
language = 'en'

def say(message):
    message_obj = gTTS(text=message, lang=language, slow=False)
    message_obj.save("message.mp3")
    os.system(f"{audio_player} mpv message.mp3")

def get_user_request(message):
    # Speak to the user
    say(message)
    # Record user request
    with sr.Microphone() as source:
        print("Talk")
        audio_text = r.listen(source, timeout=timeout, phrase_time_limit = phrase_time_limit)
        print("Time over")
        try:
            return r.recognize_google(audio_text)
        except:
            return ""


if __name__ == '__main__':
    user_request = get_user_request("How can I help you today?")

    while user_request == "":
        user_request = get_user_request("I didn't get that, please repeat")

    say("I will help you with" + user_request)






