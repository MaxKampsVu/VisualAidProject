import re
import time
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
import util

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

# ---------------------------------------------------------------------------
#   New *ask* helper using action-chain + parsing
# ---------------------------------------------------------------------------
def ask(question: str, input_type: util.INPUT_TYPE) -> Any:
    handle = action_chain.add_action()
    handle.add_prompt_user(question)
    answer = handle.add_get_user_input(input_type, print)
    handle.add_confirm_user_input(str(answer))
    return answer

# ------------------------------------------------------------
#   Collect all answers we need *before* opening the browser.
# ------------------------------------------------------------
def collect_user_data() -> dict[str, any]:
    say("Welcome to the Dutch tax benefit estimation tool. Let’s collect just a few details to run the calculation.")
    data: dict[str, any] = {}

    #TODO: Include the voice parts for the demo

    data.update({
         # generic
        "year": 2025,
        "has_partner": False,          
        # applicant personal
        "birth_day":   15,
        "birth_month": 4,
        "birth_year":  1990,
        "country": "Nederland",        
        # income / rent
        "annual_income": 35000,
        "monthly_rent":   850,
        # children 
        "has_children": False,
        # housemates
        "has_housemates": False,
        # room rental
        "lives_in_room": False,
        # group housing
        "lives_in_group_housing": False,
        # disability
        "disability_adjusted_home": False,
        # rent & service costs
        "basic_rent": 750.95,
        "pays_service_costs": True,    
        "service_energy":     25.00,
        "service_cleaning":   15.00,
        "service_janitor":    10.00,
        "service_recreation":  5.00,
        # savings
        "high_savings": False,
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

    # 1) Partner? ----------------------------------------------------------
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
            wait_click(wait, (By.ID, f"V6-13-{idx}_pbt_0"))  # own address
            wait_click(wait, (By.ID, f"V6-14-{idx}_pbt_False"))  # no income
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




######## Full version of the user data collection function:

# def collect_user_data_full() -> Dict[str, str | int | bool]:
#     data: Dict[str, str | int | bool] = {}
#
#     # ---- generic questions -------------------------------------------------
#     data["year"] = ask("Which year (2021-2025) should the calculation be for?", util.INPUT_TYPE.NUMBER)
#     
#     data["has_partner"] = ask("Do you have a toeslagpartner? Please answer with yes or no.", util.INPUT_TYPE.YES_NO)
#
#     # ---- applicant personal data ------------------------------------------
#     day, month, year = ask("What is your birthdate?", util.INPUT_TYPE.BIRTHDATE)
#     data["birth_day"], data["birth_month"], data["birth_year"] = day, month, year
#
#     data["country"] = ask("In which country do you live? (as on the site)", util.INPUT_TYPE.COUNTRY)
#
#     # ---- income / rent -----------------------------------------------------
#     data["annual_income"] = ask("What is your own annual income in euros?", util.INPUT_TYPE.AMOUNT)
#
#     data["monthly_rent"]  = ask("What is your monthly rent in euros?", util.INPUT_TYPE.AMOUNT)
#
#     # ---- partner specific --------------------------------------------------
#     if data["has_partner"]:
#         day, month, year = ask("What is your partner's birthdate?", util.INPUT_TYPE.BIRTHDATE)
#         data["partner_birth_day"], data["partner_birth_month"], data["partner_birth_year"] = day, month, year
#
#         data["same_address"] = ask("Do you and your partner live at the same address? Please answer with yes or no.", util.INPUT_TYPE.YES_NO)
#
#         if not data["same_address"]:
#             data["partner_country"] = ask("In which country does your partner live?", util.INPUT_TYPE.COUNTRY)
#
#         data["partner_income"] = ask("What is your partner's annual income in euros?", util.INPUT_TYPE.AMOUNT)
#
#     # ---- children ----------------------------------------------------------
#     data["has_children"] = ask("Do you have any children living with you?", util.INPUT_TYPE.YES_NO)
#
#     if data["has_children"]:
#         num_children = ask("How many children live with you? (1-8)", util.INPUT_TYPE.NUMBER)
#         num_children = max(1, min(num_children, 8))
#         data["num_children"] = num_children
#
#         data["co_parent"] = ask("Are you (or your partner) a co‑parent?", util.INPUT_TYPE.YES_NO)
#
#         children_birthdays = []
#         for i in range(1, num_children + 1):
#             bd = ask(f"What is your {i} child's birthdate?", util.INPUT_TYPE.BIRTHDATE)
#             children_birthdays.append(bd)
#         data["children_birthdays"] = children_birthdays
#
#     # ---- housemates --------------------------------------------------------
#     data["has_housemates"] = ask("Do other people live in your house?", util.INPUT_TYPE.YES_NO)
#
#     if data["has_housemates"]:
#         num_housemates = ask("How many housemates live with you? (1-5)", util.INPUT_TYPE.NUMBER)
#         num_housemates = max(1, min(num_housemates, 5))
#         data["num_housemates"] = num_housemates
#
#         housemate_birthdays = []
#         housemate_incomes = []
#         for i in range(1, num_children + 1):
#             bd = ask(f"What is your {i} child's birthdate?", util.INPUT_TYPE.BIRTHDATE)
#             housemate_birthdays.append(bd)
#
#             income = ask(f"What is your {i} housemate's income in euros?", util.INPUT_TYPE.AMOUNT)
#             housemate_incomes.append(income)
#
#         data["housemate_birthdays"] = housemate_birthdays
#         data["housemate_incomes"] = housemate_incomes
#
#     # ---- room rental (“op kamers”) ------------------------------------------
#     data["lives_in_room"] = ask("Do you live in a rented room or group housing?", util.INPUT_TYPE.YES_NO)
#
#     if data["lives_in_room"]:
#         rent_allowance_possible = ask("Can you receive rent allowance for your room or shared housing?", util.INPUT_TYPE.YES_NO)
#         data["room_eligible_for_rent_allowance"] = rent_allowance_possible
#
#     # ---- group housing for elderly / begeleid wonen ------------------------
#     data["lives_in_group_housing"] = ask("Do you live in group housing for the elderly?", util.INPUT_TYPE.YES_NO)
#
#     # ---- disability-related housing modifications --------------------------
#     data["disability_adjusted_home"] = ask("Is your rental home adapted because someone in the household has a disability?", util.INPUT_TYPE.YES_NO)
#
#     # ---- rent amount -------------------------------------------------------
#     data["basic_rent"] = ask("How much basic rent (\"kale huur\") do you pay per month in euros?", util.INPUT_TYPE.AMOUNT)
#
#     # ---- service costs -----------------------------------------------------
#     data["pays_service_costs"] = ask("Do you pay service costs?", util.INPUT_TYPE.YES_NO)
#
#     if data["pays_service_costs"]:
#         data["service_energy"]      = ask("What is your monthly energy costs for shared spaces?", util.INPUT_TYPE.AMOUNT)
#         data["service_cleaning"]    = ask("What is your monthly cleaning costs for shared spaces?", util.INPUT_TYPE.AMOUNT)
#         data["service_janitor"]     = ask("What is your monthly janitor costs?", util.INPUT_TYPE.AMOUNT)
#         data["service_recreation"]  = ask("What is your monthly costs for service/recreation areas?", util.INPUT_TYPE.AMOUNT)
#
#     # ---- savings check -----------------------------------------------------
#     data["high_savings"] = ask("Do you have more than €37,395 in savings on January 1st, 2025?", util.INPUT_TYPE.YES_NO)
#
#     return data