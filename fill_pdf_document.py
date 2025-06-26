from pdfrw import PdfReader, PdfWriter, PdfName, PdfString
from datetime import datetime
import util
import action_chain
from voice_util import say

import cv2
import re
import time
import easyocr

# ---------------------------------------------------------------------------
#   Configurations
# ---------------------------------------------------------------------------

INPUT_PDF  = "example.pdf"
OUTPUT_PDF = "filled_example.pdf"

action_chain = action_chain.ActionChain()

# ----------------------------------------------------------------------
# Collect user data for filling the PDF form
# ----------------------------------------------------------------------
def collect_pdf_user_data() -> dict[str, any]:

    say("Welcome to the Dutch wage tax form assistant. Let’s collect just a few details to fill out your pdf form.")
    data: dict[str, any] = {}

    # --- last-name (spelled) ----------------------------------
    def store_last_name(val: str):
        data["_lastname"] = val.lower().capitalize()
        print(f"[DEBUG] last name → {data['_lastname']}")

    h = action_chain.add_action()
    h.add_prompt_user("Please spell your last name.")
    h.add_get_user_input(util.INPUT_TYPE.SPELLING, store_last_name)
    h.add_confirm_user_input("Did I understand you correctly, your last name is ")

    # --- initials ---------------------------------------------
    def store_initials(val: str):
        data["_initials"] = val
        print(f"[DEBUG] initials → {data['_initials']}")

    h = action_chain.add_action()
    h.add_prompt_user("Please say your initials one by one.")
    h.add_get_user_input(util.INPUT_TYPE.INITIALS, store_initials)
    h.add_confirm_user_input("Did I understand you correctly, your initials are ")
    
    # --- BSN (voice vs. camera) --------------------------------------
    def store_bsn(val: str):
        data["1_BSN"] = val
        print(f"[DEBUG] BSN → {val}")

    def choose_bsn_method(choice: str):
        mode = choice.strip().lower()
        if mode == "camera":
            say("I am now opening the camera.")
            try:
                bsn = read_bsn_from_camera()
                if bsn is None:
                    h = action_chain.add_action()
                    h.add_get_user_input(util.INPUT_TYPE.BSN, store_bsn)
                    h.add_confirm_user_input("Did I understand you correctly, your BSN is ")
                    action_chain.run()
                else:
                    data["1_BSN"] = str(bsn)
                    print(f"[DEBUG] BSN → {bsn}")
                    return
            except Exception as e:
                say(f"Camera OCR failed: {e}. Please say your BSN instead.")

        h = action_chain.add_action()
        h.add_get_user_input(util.INPUT_TYPE.BSN, store_bsn)
        h.add_confirm_user_input("Did I understand you correctly, your BSN is ")
        action_chain.run()

    # ask which input method
    h = action_chain.add_action()
    h.add_prompt_user("Would you like to speak your BSN or show it to the camera?")
    h.add_get_user_input(util.INPUT_TYPE.VOICE_CAMERA, choose_bsn_method)
    

    # Old version using only voice input
    '''def store_bsn(val: str):
        data["1_BSN"] = val
        print(f"[DEBUG] BSN → {val}")

    h = action_chain.add_action()
    h.add_prompt_user("What are the 9-digits of your BSN number?")
    h.add_get_user_input(util.INPUT_TYPE.BSN, store_bsn)
    h.add_confirm_user_input("Did I understand you correctly, your BSN is ")'''

    # --- §2a  (loonheffings-korting) ---------------------------
    def store_q2a(val: bool):
        data["TICK_2A_JA"] = val
        print(f"[DEBUG] 2a (korting) → {val}")

    h = action_chain.add_action()
    h.add_prompt_user("Would you like this employer or benefits agency to apply the wage tax credit? Please note: you can only have this credit applied by one employer or agency at a time.")
    h.add_get_user_input(util.INPUT_TYPE.YES_NO, store_q2a)
    h.add_confirm_user_input("Did I understand you correctly, your answer is ")


    # --- §2b  (alleenst.-ouderenkorting) -----------------------
    def store_q2b(val: bool):
        data["TICK_2B_JA"] = val
        print(f"[DEBUG] 2b (alleenstaande-ouderenkorting) → {val}")

    h = action_chain.add_action()
    h.add_prompt_user("Do you want this employer or benefits agency to apply the single-parent elderly tax credit? This is only allowed if you’re entitled to it and you answered 'yes' to the previous question.")
    h.add_get_user_input(util.INPUT_TYPE.YES_NO, store_q2b)
    h.add_confirm_user_input("Did I understand you correctly, your answer is ")

    action_chain.run()

    # — Combine last name + initials into field "0" ------------------------
    full_name = f"{data['_lastname']} {data['_initials']}."
    data["0"] = full_name
    print(f"[DEBUG] Combined full name → {full_name}")

    # — Pre-fill remaining fields for now — -------------------------------
    data.update({
        "2": "Hoofdstraat 5",  # Street + house number
        "3": "1234AB",  # Postcode
        "4": "Amsterdam",  # City
        "5": "Noord-Holland",  # Region 
        "6": "Nederland",  # Country
        "d": "01",  # Birthdate day
        "m": "07",  # Birthdate month
        "y": "1997",  # Birthdate year
    })

    # — Add current date to field "date" — -------------------------------
    today = datetime.today()
    data.update({
        "d_F": f"{today.day:02d}",
        "m_F": f"{today.month:02d}",
        "y_F": f"{today.year}",
    })
    print(f"[DEBUG] Current date → {today.strftime('%d-%m-%Y')}")

    return data


# ----------------------------------------------------------------------
# Helper: tick checkbox by appearance name
# ----------------------------------------------------------------------
def _set_checkbox(annot, want_label):
    ap = annot.get("/AP")
    if not ap or "/N" not in ap:
        return False

    normal_states = ap["/N"].keys()
    label = PdfName(want_label)
    if label in normal_states:
        annot.AS = label       
        annot.V = label        
        print(f"Ticked checkbox with label: {label}")
        return True
    return False

def read_bsn_from_camera(attempts: int = 3, delay: int = 3) -> str:
    reader = easyocr.Reader(['en'], gpu=False)
    cap = cv2.VideoCapture(0)

    try:
        # Take three attempts to read the BSN from the camera
        for attempt in range(1, attempts + 1):
            say(f"Attempt {attempt} of {attempts}. Please hold your BSN document in front of the camera. You have {delay} seconds.")
            
            # Wait to let the user position the document
            for i in range(delay, 0, -1):
                say(f"{i}")
                time.sleep(1)
            say("I am capturing the image now.")
            ret, frame = cap.read()
            if not ret:
                say("Sorry, I could not capture an image from the camera. Let's try again.")
                continue

            # Take a temporary file to save the image and process it
            temp_file = "bsn_image/bsn_camera_temp.png"
            cv2.imwrite(temp_file, frame)
            result = reader.readtext(temp_file, detail=0)
            detected_text = ''.join(result).replace(' ', '')
            numbers = re.findall(r'\d{9}', detected_text)
            print(f"[DEBUG] Detected text: {numbers}")    
    
            # If 9-digit number found save it, otherwise retry
            if numbers:
                bsn = numbers[0]
                digits_spoken = " ".join(bsn) 
                say(f"Your BSN is: {digits_spoken}.")
                return bsn
            else:
                say("I could not find a 9-digit number. Let's try again.")

        cap.release()
        say("I could not detect your BSN after 3 attempts. Please say your BSN instead.")
        return None
    except Exception as e:
        say(f"An error occurred while reading the BSN from the camera: {e}")
        cap.release()
        raise e

# ---------------------------------------------------------------------------
#   MAIN PDF FILLER
# ---------------------------------------------------------------------------

def fill_pdf(data: dict[str, any]):
    say("Thank you! I've filled out your pdf document. The file is titled filled_example.pdf")
    pdf = PdfReader(INPUT_PDF)

    for page in pdf.pages:
        annots = page.Annots
        if not annots:
            continue

        for annot in annots:
            if annot.Subtype != PdfName.Widget:
                continue

            # 1) text fields (have a /T key)
            if annot.T:
                key = annot.T.to_unicode().strip("()")
                if key in data:
                    value = str(data[key])
                    print(f"Setting field '{key}' to '{value}'")
                    annot.V = PdfString.encode(value)
                    annot.AP = None

            # 2) checkbox fields – matched by appearance label
            else:
                if data["TICK_2A_JA"]:
                    _set_checkbox(annot, "Ja. Vul de datum in vanaf wanneer.")
                else:
                    _set_checkbox(annot, "Nee. Vul de datum in vanaf wanneer niet of niet meer, en ga daarna verder met vraag 3.")

                if data["TICK_2B_JA"]:
                    _set_checkbox(annot, "Ja")
                else:
                    _set_checkbox(annot, "Nee")

    PdfWriter().write(OUTPUT_PDF, pdf)
    return f"The form has been filled and saved as '{OUTPUT_PDF}'. Please remember to write the missing date next to the checkbox for question 2a on page two and sign the form."

# ---------------------------------------------------------------------------
#   MAIN
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    ########## Task 1: Filling out pdf form ###########
    user_data = collect_pdf_user_data()
    say("Thanks. I'm now filling in the PDF document.")
    result = fill_pdf(user_data)
    say(result)
    print("PDF filled and saved as 'filled_example.pdf'.")
