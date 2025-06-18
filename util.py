from nameparser import HumanName
import spacy
from enum import Enum
import re

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
    INITIALS = 10
    BSN = 11
    CONTAINER = 12

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
        case INPUT_TYPE.INITIALS:
            return extract_initials(text)
        case INPUT_TYPE.BSN:
            return extract_bsn(text)
        case INPUT_TYPE.CONTAINER:
            return extract_container(text)
    return None


if __name__ == '__main__':
    s = "My name is Sarah Connor and I live in Los Angeles."
    print(extract_firstname(s))
    print(extract_surname(s))
    print(extract_place(s))
