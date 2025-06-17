import time
import util
from typing import Dict, Optional, Tuple, Any
import action_chain
from voice_util import say

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from googletrans import Translator


# ---------------------------------------------------------------------------
#   URL / Selenium config
# ---------------------------------------------------------------------------

TOESLAGEN_URL = (
    "https://www.belastingdienst.nl/wps/wcm/connect/nl/toeslagen/"
    "content/hulpmiddel-proefberekening-toeslagen"
)

CHROME_HEADLESS = False
aDEFAULT_TIMEOUT = 15

action_chain = action_chain.ActionChain()


# ------------------------------------------------------------
#   Collect all answers we need *before* opening the browser.
# ------------------------------------------------------------
def collect_user_data() -> dict[str, any]:
    say("Welcome to the Dutch benefit estimation tool. Let’s collect just a few details to run the calculation.")
    data: dict[str, any] = {}

    # — Ask for year — ----------------------------------------------------
    year_val: int | None = None
    def store_year(v):
        nonlocal year_val
        year_val = v
        data["year"] = year_val if year_val in {2021, 2022, 2023, 2024, 2025} else 2025
        print(f"[DEBUG] Stored year: {year_val}")

    h = action_chain.add_action()
    h.add_prompt_user("Which year from 2021 to 2025 should we calculate for?")
    h.add_get_user_input(util.INPUT_TYPE.NUMBER, store_year)
    h.add_confirm_user_input("Did I understand you correctly, the year is ")

    # — Ask for birth-date — ---------------------------------------------
    birthdate: tuple[int, int, int] | None = None

    def store_birthdate(value: tuple[int, int, int]):
        nonlocal birthdate
        if isinstance(value, tuple) and len(value) == 3:
            birthdate = value
            day, month, year = value
            data["birth_day"], data["birth_month"], data["birth_year"] = day, month, year
            print(f"[DEBUG] Stored birthdate: {day}-{month}-{year}")
        else:
            say("Sorry, the date format was unclear. We'll use a default for now.")
            data["birth_day"], data["birth_month"], data["birth_year"] = 1, 1, 1990
            print("[DEBUG] Used fallback birthdate: 1-1-1990")

    h = action_chain.add_action()
    h.add_prompt_user("What is your birth-date?")
    h.add_get_user_input(util.INPUT_TYPE.BIRTHDATE, store_birthdate)
    h.add_confirm_user_input("Did I understand you correctly, your birth-date is ")
    
    # — Ask for country — -------------------------------------------------
    country_val: str | None = None
    def store_country(val):
        nonlocal country_val
        try:
            translated = translator.translate(val, src='en', dest='nl').text
            country_val = translated
            data["country"] = country_val or "Nederland"
        except Exception:
            country_val = val
            data["country"] = country_val or "Nederland"
        print(f"[DEBUG] Final country value stored: {country_val}")

    h = action_chain.add_action()
    h.add_prompt_user("Where do you live?")
    h.add_get_user_input(util.INPUT_TYPE.PLACE, store_country)
    h.add_confirm_user_input("Did I understand you correctly, you live in ")

    # — Ask for basic rent — ---------------------------------------------
    rent_val: int | None = None
    def store_rent(v):
        nonlocal rent_val
        rent_val = v
        data["basic_rent"] = rent_val or 0
        print(f"[DEBUG] Stored basic rent: €{rent_val}")

    h = action_chain.add_action()
    h.add_prompt_user('How much basic rent do you pay per month in euros?')
    h.add_get_user_input(util.INPUT_TYPE.AMOUNT, store_rent)
    h.add_confirm_user_input("Did I understand you correctly, your basic rent is ")

    # — Ask for savings flag — -------------------------------------------
    savings_flag: bool | None = None
    def store_savings(v):
        nonlocal savings_flag
        savings_flag = bool(v)
        data["high_savings"] = savings_flag
        print(f"[DEBUG] Stored savings flag: {'Yes' if v else 'No'}")

    h = action_chain.add_action()
    h.add_prompt_user("Do you have more than €37,395 in savings on the 1st of January in that year?")
    h.add_get_user_input(util.INPUT_TYPE.YES_NO, store_savings)
    h.add_confirm_user_input("Did I understand you correctly, your answer to this question is ")

    action_chain.run()

    # — Pre-fill remaining fields for now — -------------------------------
    data.update({
        "has_partner": False,
        "annual_income": 5000,
        "monthly_rent": 850,
        "has_children": False,
        "has_housemates": False,
        "lives_in_room": False,
        "lives_in_group_housing": False,
        "disability_adjusted_home": False,
        "pays_service_costs": False,
    })

    return data



# ---------------------------------------------------------------------------
#   BROWSER‑AUTOMATION HELPERS
# ---------------------------------------------------------------------------

def wait_click(wait: WebDriverWait, locator: Tuple[str, str]):
    el = wait.until(EC.element_to_be_clickable(locator))
    el.click()
    return el


def safe_select_by_value(sel: Select, value: Any):
    val = str(value)
    try:
        sel.select_by_value(val)
    except Exception:
        sel.select_by_visible_text(val)


def fill_date(driver, prefix_id: str, date_tuple: Tuple[str, str, str]):
    day, month, year = date_tuple
    driver.find_element(By.ID, f"{prefix_id}-1").send_keys(day)
    driver.find_element(By.ID, f"{prefix_id}-2").send_keys(month)
    driver.find_element(By.ID, f"{prefix_id}-3").send_keys(year)

def click_yes_no(wait: WebDriverWait, field_name: str,flag: bool):
    suffix   = "True" if flag else "False"           
    label_for = f"{field_name}_{suffix}"             
    locator  = (By.XPATH, f"//label[@for='{label_for}']")
    lbl      = wait.until(EC.element_to_be_clickable(locator))
    lbl.click()

# ---------------------------------------------------------------------------
#   MAIN FORM FILLER
# ---------------------------------------------------------------------------

def fill_form(driver: webdriver.Chrome, data: Dict[str, Any]):
    wait = WebDriverWait(driver, aDEFAULT_TIMEOUT)

    # 0) Year --------------------------------------------------------------
    try: 
        safe_select_by_value(Select(wait.until(EC.presence_of_element_located((By.ID, "V1-1_pbt")))), data["year"])
    except Exception as e:
        print(f"[WARN] Year selection failed: {e}")

    # only Huurtoeslag checked
    try: 
        huur = driver.find_element(By.ID, "V1-3_pbt_1")
        if not huur.is_selected():
            huur.click()
    except Exception as e:
        print(f"[WARN] Huurtoeslag checkbox selection failed: {e}")

    # 1) Partner ----------------------------------------------------------
    try:
        click_yes_no(wait, "V2-1_pbt", data["has_partner"])
    except Exception as e:
        print(f"[WARN] Partner selection failed: {e}")

    # 2) Applicant birthday & country ------------------------------------
    try:
        fill_date(driver, "V2-3_pbt", (data["birth_day"], data["birth_month"], data["birth_year"]))
    except Exception as e:
        print(f"[WARN] Applicant birthday selection failed: {e}")

    try:
        safe_select_by_value(Select(driver.find_element(By.ID, "V2-11_pbt")), data["country"])
    except Exception as e:
        print(f"[WARN] Applicant country selection failed: {e}")

    # 3) Applicant income --------------------------------------------------
    try:
        driver.find_element(By.ID, "V3-10_pbt").send_keys(data["annual_income"])
    except Exception as e:
        print(f"[WARN] Applicant income entry failed: {e}")

    # 4) Partner section ---------------------------------------------------
    if data["has_partner"]:
        try:
            fill_date(driver, "V4-2_pbt", (data["partner_birth_day"], data["partner_birth_month"], data["partner_birth_year"]))
        except Exception as e:
            print(f"[WARN] Partner birthday selection failed: {e}")
        try:
            click_yes_no(wait, "V4-3_pbt", data["same_address"])
        except Exception as e:
            print(f"[WARN] Partner same address selection failed: {e}")
        
        if data["same_address"]:
            try:
                driver.find_element(By.ID, "V4-25_pbt").send_keys(data["partner_income"])
            except Exception as e:
                print(f"[WARN] Partner income entry failed: {e}")
        else:
            try:
                safe_select_by_value(Select(driver.find_element(By.ID, "V4-4_pbt")), data["partner_country"])
            except Exception as e:
                print(f"[WARN] Partner country selection failed: {e}")

    # 5) Children ----------------------------------------------------------
    try:
        click_yes_no(wait, "V6-1_pbt", data["has_children"])
    except Exception as e:
        print(f"[WARN] Children selection failed: {e}")
    
    if data["has_children"]:
        try:
            click_yes_no(wait, "V6-3_pbt", data["co_parent"])
        except Exception as e:
            print(f"[WARN] Co-parent selection failed: {e}")
        try:
            Select(driver.find_element(By.ID, "V6-4_pbt")).select_by_value(str(data["num_children"]))
        except Exception as e:
            print(f"[WARN] Children number selection failed: {e}")

        for idx, bday in enumerate(data["children_birthdays"], start=1):
            try:
                fill_date(driver, f"V6-5-{idx}_pbt", bday)
            except Exception as e:
                print(f"[WARN] Child birthday selection failed: {e}")
            try:
                wait_click(wait, (By.ID, f"V6-13-{idx}_pbt_0"))
            except Exception as e:
                print(f"[WARN] Child co-parent selection failed: {e}")
            try:
                wait_click(wait, (By.ID, f"V6-14-{idx}_pbt_False"))
            except Exception as e:
                print(f"[WARN] Child living situation selection failed: {e}")
            try:
                driver.find_element(By.ID, f"V6-15-{idx}_pbt").send_keys("0")
            except Exception as e:
                print(f"[WARN] Child income entry failed: {e}")

    # 6) Housemates --------------------------------------------------------
    try:
        click_yes_no(wait, "V9-1_pbt", data["has_housemates"])
    except Exception as e:
        print(f"[WARN] Housemates selection failed: {e}")
    
    if data["has_housemates"]:
        try:
            Select(driver.find_element(By.ID, "V9-2_pbt")).select_by_value(str(data["num_housemates"]))
        except Exception as e:
            print(f"[WARN] Housemates number selection failed: {e}")
        
        for idx, (bday, inc) in enumerate(zip(data["housemate_birthdays"], data["housemate_incomes"]), start=1):
            try:
                fill_date(driver, f"V9-3-{idx}_pbt", bday)
            except Exception as e:
                print(f"[WARN] Housemate birthday selection failed: {e}")
            try:
                driver.find_element(By.ID, f"V9-4-{idx}_pbt").send_keys(inc)
            except Exception as e:
                print(f"[WARN] Housemate income entry failed: {e}")

    # 7) Room / shared housing -------------------------------------------
    try:
        click_yes_no(wait, "V10-1_pbt", data["lives_in_room"])
    except Exception as e:
        print(f"[WARN] Room living situation selection failed: {e}")
    
    if data["lives_in_room"]:
        try:
            click_yes_no(wait, "V10-3_pbt", data["room_eligible_for_rent_allowance"])
        except Exception as e:
            print(f"[WARN] Room rent allowance eligibility selection failed: {e}")
    
    # 8) Group housing for elderly / begeleid wonen -------------------
    try:
        click_yes_no(wait, "V10-2_pbt", data["lives_in_group_housing"])
    except Exception as e:
        print(f"[WARN] Group housing selection failed: {e}")

    # 9) Handicap modifications ------------------------------------------
    try:
        click_yes_no(wait, "V10-5_pbt", data["disability_adjusted_home"])
    except Exception as e:
        print(f"[WARN] Handicap modifications selection failed: {e}")

    # 10) Rent & Service costs --------------------------------------------
    try:
        rent_str = f"{data['basic_rent']:.2f}".replace('.', ',')
        driver.find_element(By.ID, "V10-10_pbt").send_keys(rent_str)
    except Exception as e:
        print(f"[WARN] Basic rent entry failed: {e}")

    try:
        click_yes_no(wait, "V10-11_pbt", data["pays_service_costs"])
    except Exception as e:
        print(f"[WARN] Service costs selection failed: {e}")

    if data["pays_service_costs"]:
        try:
            energy_str = f"{data['service_energy']:.2f}".replace('.', ',')
            driver.find_element(By.ID, "V10-12-1_pbt").send_keys(energy_str)
        except Exception as e:
            print(f"[WARN] Service energy entry failed: {e}")
        
        try:
            cleaning_str = f"{data['service_cleaning']:.2f}".replace('.', ',')
            driver.find_element(By.ID, "V10-12-2_pbt").send_keys(cleaning_str)
        except Exception as e:
            print(f"[WARN] Service cleaning entry failed: {e}")

        try:
            janitor_str = f"{data['service_janitor']:.2f}".replace('.', ',')
            driver.find_element(By.ID, "V10-12-3_pbt").send_keys(janitor_str)
        except Exception as e:
            print(f"[WARN] Service janitor entry failed: {e}")

        try:
            recreation_str = f"{data['service_recreation']:.2f}".replace('.', ',')
            driver.find_element(By.ID, "V10-12-4_pbt").send_keys(recreation_str)
        except Exception as e:
            print(f"[WARN] Service recreation entry failed: {e}")

    # 11) Savings ---------------------------------------------------------
    try:
        click_yes_no(wait, "V11-3_pbt", data["high_savings"])
    except Exception as e:
        print(f"[WARN] Savings selection failed: {e}")

    # 12) Results ---------------------------------------------------------
    try:
        wait_click(wait, (By.ID, "butResults_pbt"))
        result_el = wait.until(EC.visibility_of_element_located((By.ID, "divResultTxt_pbt")))
    except Exception as e:
        print(f"[ERROR] Result calculation failed: {e}")
        return "An error occurred while calculating result. Please try again later."

    return result_el.text.strip()

# ---------------------------------------------------------------------------
#   LAUNCH DRIVER + SCRIPT + TRANSLATE
# ---------------------------------------------------------------------------

translator = Translator()

def translate_to_english(text: str) -> str:
    return translator.translate(text, src="nl", dest="en").text


def run_calculation(data: Dict[str, Any]):
    opts = Options()
    if CHROME_HEADLESS:
        opts.add_argument("--headless=new")
    
    service = Service(ChromeDriverManager().install())
    driver  = webdriver.Chrome(service=service, options=opts)
    driver.set_window_size(1280, 1200)

    result: Optional[str] = None
    try:
        driver.get(TOESLAGEN_URL)
        WebDriverWait(driver, aDEFAULT_TIMEOUT).until(
            EC.presence_of_element_located((By.ID, "V1-1_pbt"))
        )
        result = fill_form(driver, data)
        result = translate_to_english(result)
    finally:
        time.sleep(3)
        driver.quit()

    return result or "No result found. Please try again."

# ---------------------------------------------------------------------------
#   MAIN
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    user_data = collect_user_data()
    run_calculation(user_data)