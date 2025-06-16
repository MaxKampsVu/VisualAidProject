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
    h.add_confirm_user_input("Did I understand you correctly, your savings answer is ")

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
    safe_select_by_value(Select(wait.until(EC.presence_of_element_located((By.ID, "V1-1_pbt")))), data["year"])

    # only Huurtoeslag checked
    huur = driver.find_element(By.ID, "V1-3_pbt_1")
    if not huur.is_selected():
        huur.click()

    # 1) Partner ----------------------------------------------------------
    click_yes_no(wait, "V2-1_pbt", data["has_partner"])

    # 2) Applicant birthday & country ------------------------------------
    fill_date(driver, "V2-3_pbt", (data["birth_day"], data["birth_month"], data["birth_year"]))
    safe_select_by_value(Select(driver.find_element(By.ID, "V2-11_pbt")), data["country"])

    # 3) Applicant income --------------------------------------------------
    driver.find_element(By.ID, "V3-10_pbt").send_keys(data["annual_income"])

    # 4) Partner section ---------------------------------------------------
    if data["has_partner"]:
        fill_date(driver, "V4-2_pbt", (data["partner_birth_day"], data["partner_birth_month"], data["partner_birth_year"]))
        click_yes_no(wait, "V4-3_pbt", data["same_address"])
        if data["same_address"]:
            driver.find_element(By.ID, "V4-25_pbt").send_keys(data["partner_income"])
        else:
            safe_select_by_value(Select(driver.find_element(By.ID, "V4-4_pbt")), data["partner_country"])

    # 5) Children ----------------------------------------------------------
    click_yes_no(wait, "V6-1_pbt", data["has_children"])
    if data["has_children"]:
        click_yes_no(wait, "V6-3_pbt", data["co_parent"])
        Select(driver.find_element(By.ID, "V6-4_pbt")).select_by_value(str(data["num_children"]))
        for idx, bday in enumerate(data["children_birthdays"], start=1):
            fill_date(driver, f"V6-5-{idx}_pbt", bday)
            wait_click(wait, (By.ID, f"V6-13-{idx}_pbt_0"))  
            wait_click(wait, (By.ID, f"V6-14-{idx}_pbt_False"))  
            driver.find_element(By.ID, f"V6-15-{idx}_pbt").send_keys("0")

    # 6) Housemates --------------------------------------------------------
    click_yes_no(wait, "V9-1_pbt", data["has_housemates"])
    if data["has_housemates"]:
        Select(driver.find_element(By.ID, "V9-2_pbt")).select_by_value(str(data["num_housemates"]))
        for idx, (bday, inc) in enumerate(zip(data["housemate_birthdays"], data["housemate_incomes"]), start=1):
            fill_date(driver, f"V9-3-{idx}_pbt", bday)
            driver.find_element(By.ID, f"V9-4-{idx}_pbt").send_keys(inc)

    # 7) Room / shared housing -------------------------------------------
    click_yes_no(wait, "V10-1_pbt", data["lives_in_room"])
    if data["lives_in_room"]:
        click_yes_no(wait, "V10-3_pbt", data["room_eligible_for_rent_allowance"])
    
    # 8) Group housing for elderly / begeleid wonen -------------------
    click_yes_no(wait, "V10-2_pbt", data["lives_in_group_housing"])

    # 9) Handicap modifications ------------------------------------------
    click_yes_no(wait, "V10-5_pbt", data["disability_adjusted_home"])

    # 10) Rent & Service costs --------------------------------------------
    rent_str = f"{data['basic_rent']:.2f}".replace('.', ',')
    driver.find_element(By.ID, "V10-10_pbt").send_keys(rent_str)

    click_yes_no(wait, "V10-11_pbt", data["pays_service_costs"])
    if data["pays_service_costs"]:
        energy_str = f"{data['service_energy']:.2f}".replace('.', ',')
        driver.find_element(By.ID, "V10-12-1_pbt").send_keys(energy_str)
        
        cleaning_str = f"{data['service_cleaning']:.2f}".replace('.', ',')
        driver.find_element(By.ID, "V10-12-2_pbt").send_keys(cleaning_str)
        
        janitor_str = f"{data['service_janitor']:.2f}".replace('.', ',')
        driver.find_element(By.ID, "V10-12-3_pbt").send_keys(janitor_str)

        recreation_str = f"{data['service_recreation']:.2f}".replace('.', ',')
        driver.find_element(By.ID, "V10-12-4_pbt").send_keys(recreation_str)

    # 11) Savings ---------------------------------------------------------
    click_yes_no(wait, "V11-3_pbt", data["high_savings"])

    # 12) Results ---------------------------------------------------------
    wait_click(wait, (By.ID, "butResults_pbt"))
    result_el = wait.until(EC.visibility_of_element_located((By.ID, "divResultTxt_pbt")))

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