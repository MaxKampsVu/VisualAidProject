from nameparser import HumanName
import spacy
from enum import Enum
import re
from dateutil.parser import parse as _parse_date
import pycountry
from word2number import w2n
from voice_util import _make_llm_request
from rapidfuzz import process, fuzz

# TODO: download small English language model: python -m spacy download en_core_web_sm
nlp = spacy.load("en_core_web_sm")

'''
Other categories spacey recognizes: 
PERSON	    People, including fictional
NORP	    Nationalities, religious groups, political groups
FAC	        Facilities (buildings, airports, highways, bridges)
ORG	        Organizations (companies, institutions, agencies)
GPE	        Geopolitical entities (countries, cities, states)
LOC	        Non-GPE locations (mountains, bodies of water)
PRODUCT	    Objects, vehicles, foods, etc. (not services)
EVENT	    Named events (e.g., "World War II", "Olympics")
WORK_OF_ART	Titles of books, songs, films, artworks
LAW	Named   legal documents (e.g., "Constitution", "Treaty of Versailles")
LANGUAGE	Any named language (e.g., "English", "Mandarin")
DATE	    Absolute or relative dates (e.g., "July 4th", "two weeks ago")
TIME	    Specific times (e.g., "2 PM", "three hours")
PERCENT	    Percentage values (e.g., "50%")
MONEY	    Monetary values (e.g., "$100", "€1 million")
QUANTITY	Generic quantities (e.g., "10 kg", "dozen")
ORDINAL	    position in a sequence (e.g., "first", "second")
CARDINAL	Numerical values not part of another category (e.g., "one", "2,000")    
'''

class INPUT_TYPE(Enum):
    FIRSTNAME = 0
    SURNAME = 1
    PLACE = 2
    SPELLING = 3
    BIRTHDATE = 4
    COUNTRY = 5
    AMOUNT = 6
    NUMBER = 8
    YES_NO = 9
    CONTAINER = 10

def extract_firstname(text):
    doc = nlp(text)
    person = next((ent.text for ent in doc.ents if ent.label_ == "PERSON"), None)
    if person is None:
        print("[Warning] Spacey did not recognize answer.")
        return None
    name = HumanName(person)
    return name.first

def extract_surname(text):
    doc = nlp(text)
    person = next((ent.text for ent in doc.ents if ent.label_ == "PERSON"), None)
    if person is None:
        print("[Warning] Spacey did not recognize answer.")
        return None
    name = HumanName(person)
    return name.surnames

def extract_place(text):
    doc = nlp(text)
    place = next((ent.text for ent in doc.ents if ent.label_ == "GPE"), None)
    if place is None:
        print("[Warning] Spacey did not recognize answer.")
    return place

def extract_spelling(text):
    match = re.search(r'\b(?:[A-Za-z]\s+){1,}[A-Za-z]\b', text)
    if match:
        letters = match.group().split()
        return ''.join(letters).lower()
    return None

def extract_container(text):
    types = [
        "residual waste",
        "glass",
        "paper",
        "textile collection",
        "textile containers",
        "organic waste",
        "bread and pastry waste"
    ]

    text_lower = text.lower()

    # First, try exact match
    for t in types:
        if t in text_lower:
            return t

     # Fuzzy match against the full types list
    result = process.extractOne(
        text_lower,  # input string
        types,  # list of valid types
        scorer=fuzz.partial_ratio,
        score_cutoff=80  # adjust threshold for strictness
    )

    return result[0] if result else None

def extract_birthdate(text: str) -> tuple[int, int, int] | None:
    """Return (day, month, year) as ints, or None if not recognized."""
    doc = nlp(text)
    date_ent = next((ent.text for ent in doc.ents if ent.label_ == "DATE"), None)
    if not date_ent:
        print("[Warning] SpaCy did not recognize a date.")
        return None

    try:
        dt = _parse_date(date_ent, dayfirst=True, fuzzy=True)
        return dt.day, dt.month, dt.year
    except Exception as e:
        print(f"[Warning] Could not parse date “{date_ent}”: {e}")
        return None


def extract_country(text: str) -> str | None:
    doc = nlp(text)
    # look for any geopolitical entity
    ent = next((ent.text for ent in doc.ents if ent.label_ == "GPE"), None)
    if not ent:
        print("[Warning] SpaCy did not recognize a country.")
        return None
    try:
        country = pycountry.countries.search_fuzzy(ent)[0]
        return country.name
    except LookupError:
        # fallback: return the raw text
        print(f"[Warning] Could not map “{ent}” to a known country.")
        return ent

def extract_amount(text: str) -> float | None:
    # first try SpaCy MONEY
    doc = nlp(text)
    money_ent = next((ent.text for ent in doc.ents if ent.label_ == "MONEY"), None)
    raw = money_ent or text
    # strip currency symbols/words and commas
    cleaned = re.sub(r'[^\d\.]', '', raw.replace(',', ''))
    try:
        return float(cleaned)
    except ValueError:
        print(f"[Warning] Could not parse amount from “{raw}”.")
        return None

def extract_number(text: str) -> int | None:
    doc = nlp(text)
    ent = next((ent.text for ent in doc.ents if ent.label_ in ("CARDINAL","QUANTITY")), None)
    if ent:
        # try digits first
        m = re.search(r'\d+', ent.replace(',', ''))
        if m:
            return int(m.group())
        # try spelled-out
        try:
            return w2n.word_to_num(ent)
        except Exception:
            pass

    # fallback
    m = re.search(r'\d+', text.replace(',', ''))
    if m:
        return int(m.group())

    print("[Warning] Could not extract a number.")
    return None

def extract_yes_no(text: str) -> bool | None:
    categories = ["yes", "no"]
    prompt = (
        f"Which category from the list {categories} fits the sentence "
        f"'{text}' best? Only reply with the matching category name."
    )

    # make the LLM request
    llm_reply = _make_llm_request(prompt)
    print(f"LLM categorized the input as: {llm_reply!r}")

    # find which keyword appeared
    choice = next((c for c in categories if c in llm_reply.lower()), None)
    if choice == "yes":
        return True
    if choice == "no":
        return False

    print(f"[Warning] Could not interpret yes/no from LLM reply: {llm_reply!r}")
    return None

def extract(input_type, text):
    match input_type:
        case INPUT_TYPE.FIRSTNAME:
            return extract_firstname(text)
        case INPUT_TYPE.SURNAME:
            return extract_surname(text)
        case INPUT_TYPE.PLACE:
            return extract_place(text)
        case INPUT_TYPE.SPELLING:
            return extract_spelling(text)
        case INPUT_TYPE.BIRTHDATE: 
            return extract_birthdate(text)
        case INPUT_TYPE.COUNTRY:   
            return extract_country(text)
        case INPUT_TYPE.AMOUNT:    
            return extract_amount(text)
        case INPUT_TYPE.NUMBER:    
            return extract_number(text)
        case INPUT_TYPE.YES_NO:    
            return extract_yes_no(text)
        case INPUT_TYPE.CONTAINER:
            return extract_container(text)
    return None


if __name__ == '__main__':
    s = "My name is Sarah Connor and I live in Los Angeles."
    print(extract_firstname(s))
    print(extract_surname(s))
    print(extract_place(s))