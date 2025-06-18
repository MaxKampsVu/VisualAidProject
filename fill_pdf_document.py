from pdfrw import PdfReader, PdfWriter, PdfName, PdfString
from datetime import datetime
import util
import action_chain
from voice_util import say

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


    # --- BSN ---------------------------------------------------
    def store_bsn(val: str):
        data["1_BSN"] = val
        print(f"[DEBUG] BSN → {val}")

    h = action_chain.add_action()
    h.add_prompt_user("What is your BSN number?")
    h.add_get_user_input(util.INPUT_TYPE.BSN, store_bsn)
    h.add_confirm_user_input("Did I understand you correctly, your BSN is ")


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


# ---------------------------------------------------------------------------
#   MAIN PDF FILLER
# ---------------------------------------------------------------------------

def fill_pdf(data: dict[str, any]):
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
    user_data = collect_pdf_user_data()
    fill_pdf(user_data)