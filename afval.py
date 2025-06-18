#afafvalcontainers.py

import re
import time
from typing import Dict, Optional, Tuple, Any

import action_chain
import util
from voice_util import say

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC

from googletrans import Translator

# ------------------------------------------------------------------
#   Config & globals
# ------------------------------------------------------------------
AFVAL_URL = (
    "https://kaart.amsterdam.nl/afvalcontainers"
)

residual, glass, paper, textile, textile_collection, organic, bread  = (1, 2, 3, 5, 13698, 6, 7)

CHROME_HEADLESS = False
DEFAULT_TIMEOUT = 15

translator = Translator()
action_chain = action_chain.ActionChain()

# ------------------------------------------------------------------
#   Action-chain “ask” helper
# ------------------------------------------------------------------
def ask(question: str, input_type: util.INPUT_TYPE) -> Any:
    handle = action_chain.add_action()
    handle.add_prompt_user(question)
    answer = handle.add_get_user_input(input_type, lambda x: None)
    handle.add_confirm_user_input(f"Did I understand you correctly? {question}")
    return answer

# ------------------------------------------------------------------
#   collect_user_data: demo prompts + hard-coded defaults
# ------------------------------------------------------------------
def collect_user_data() -> Dict[str, Any]:
    say("Welcome to the Dutch Waste container map. Let’s collect just a few details to run the calculation.")
    data: dict[str, any] = {}

    # — Ask for Address — ----------------------------------------------------
    address: int | None = None
    def store_address(v):
        nonlocal address
        address = v
        data["address"] = address
        print(f"[DEBUG] Stored street: {address}")

    h = action_chain.add_action()
    h.add_prompt_user("Please spell the name of your street?")
    h.add_get_user_input(util.INPUT_TYPE.SPELLING, store_address)
    h.add_confirm_user_input("Did I understand you correctly, the name of your street is ")
    
    stNumber: int | None = None
    def store_stNumber(v):
        nonlocal stNumber
        stNumber = v
        data["address"] = data.get("address", "") + f" {stNumber}"
        print(f"[DEBUG] Stored house number: {stNumber}")

    h = action_chain.add_action()
    h.add_prompt_user("What is your house number?")
    h.add_get_user_input(util.INPUT_TYPE.NUMBER, store_stNumber)
    h.add_confirm_user_input("Did I understand you correctly, your house number is ")

     # — Ask for container type — ----------------------------------------------------
    container: int | None = None
    def store_container(v):
        nonlocal container
        container = v
        data["container"] = int("1249" + str(container)) if container in {1, 2, 3, 5, 6, 7} else 13698
        print(f"[DEBUG] Stored container type: {container}")

    h = action_chain.add_action()
    h.add_prompt_user("What is the container type you want to find? Say 1 for residual waste, 2 for glass, 3 for paper, 4 for textile collection, 5 for textile containers, 6 for organic waste, or 7 for bread and pastry waste.")
    h.add_get_user_input(util.INPUT_TYPE.NUMBER, store_container)
    h.add_confirm_user_input("Did I understand you correctly, the container type you want to find is ")

    # fill dummy data for testing
    data["container"] = residual  # Default to residual waste
    say(f"Thanks. I will now search for the nearest waste container for {data['container']} at {data['address']}.")

    action_chain.run()

    return data

# ------------------------------------------------------------------
#   Browser-automation helpers
# ------------------------------------------------------------------
def wait_click(wait: WebDriverWait, locator: Tuple[str, str]):
    el = wait.until(EC.element_to_be_clickable(locator))
    el.click()
    return el

# ------------------------------------------------------------------
#   Main form-filler
# ------------------------------------------------------------------
def find_bin(driver: webdriver.Chrome, data: Dict[str, Any]) -> str:
    wait = WebDriverWait(driver, DEFAULT_TIMEOUT)

    # 1) Wait for the map to load
    wait.until(EC.presence_of_element_located((By.ID, "map")))

    # 2) Click the "Find container" button
    wait_click(wait, (By.CLASS_NAME, "legend__search"))

    # 3) Fill in the address and press enter
    address = data.get("address", "")
    if not address:
        raise ValueError("Address is required to find a bin.")
    
    address_input = wait.until(EC.presence_of_element_located((By.ID, "search-input")))
    address_input.send_keys(address)
    # Wait for the listings to load then find the first listing in the dropdown with class search-result search-result--selected and click it
    wait.until(EC.presence_of_element_located((By.CLASS_NAME, "search-result")))
    first_listing = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "search-result--selected")))
    first_listing.click()
    # Wait for the map to update with the new location
    wait.until(EC.presence_of_element_located((By.CLASS_NAME, "leaflet-marker-icon")))

    # 4) Find the ul with class categories and click on all the checkboxes inside it except for the one with value "1249 + str(data['container'])"
    # Using their xpaths
    container_type_value = int("1249" + str(data["container"]))
    categories_ul = wait.until(EC.presence_of_element_located((By.XPATH, "//ul[@class='categories']")))
    checkboxes = categories_ul.find_elements(By.CLASS_NAME, "form-checkbox__label")
    for checkbox in [12491, 12492, 12493, 12495, 13698, 12496, 12497]:
        if checkbox != container_type_value:
            label = wait.until(EC.element_to_be_clickable((By.XPATH, f"//label[@for='category_{checkbox}_checkbox']")))
            label.click()
    
    time.sleep(2)

    # 4) Zoom in to reduce containers shown. Focus on the closest ones.
    zoom_button = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "leaflet-control-zoom-in")))
    # Click the zoom button until its class changes to "disabled"
    while "leaflet-disabled" not in zoom_button.get_attribute("class"):
        zoom_button.click()
        time.sleep(0.5)

        
    time.sleep(2)

    markers = wait.until(EC.presence_of_all_elements_located((By.XPATH, "//div[contains(@class, 'leaflet-marker-icon')]")))
    poi_markers = [marker for marker in markers if "marker-poi-wrapper" in marker.get_attribute("class")]        
    clusters = [marker for marker in markers if "marker-cluster-wrapper" in marker.get_attribute("class")]

    # Zoom out until a cluster or marker is found
    zoom_button = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "leaflet-control-zoom-out")))
    while not poi_markers and not clusters:
        zoom_button.click()
        time.sleep(0.5)
        markers = wait.until(EC.presence_of_all_elements_located((By.XPATH, "//div[contains(@class, 'leaflet-marker-icon')]")))
        poi_markers = [marker for marker in markers if "marker-poi-wrapper" in marker.get_attribute("class")]        
        clusters = [marker for marker in markers if "marker-cluster-wrapper" in marker.get_attribute("class")]

    print(f"[DEBUG] Found {len(poi_markers)} POI markers and {len(clusters)} clusters.")

    while not poi_markers:
        first_cluster = clusters[0]
        print("[DEBUG] Clicking on the first cluster found.")
        first_cluster.click()
        time.sleep(2)
        markers = wait.until(EC.presence_of_all_elements_located((By.XPATH, "//div[contains(@class, 'leaflet-marker-icon')]")))
        poi_markers = [marker for marker in markers if "marker-poi-wrapper" in marker.get_attribute("class")]
        clusters = [marker for marker in markers if "marker-cluster-wrapper" in marker.get_attribute("class")]

    first_marker = poi_markers[0]
    first_marker.click()

    feature_div = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "feature-digital-item__link")))
    href = feature_div.get_attribute("href")
    
    driver.get(href)
    WebDriverWait(driver, DEFAULT_TIMEOUT).until(
            EC.presence_of_element_located((By.ID, "yDmH0d"))
    )
    
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

    time.sleep(2)

    third_button = wait.until(EC.element_to_be_clickable((By.XPATH, "(//button)[3]")))
    third_button.click()

    time.sleep(2)

    address_element = wait.until(EC.presence_of_element_located((By.XPATH, "(//input[@class='tactile-searchbox-input'])[2]")))
    address_text = address_element.get_attribute("aria-label")
    address_text = address_text.replace("Bestemming", "").strip()
    return f"The nearest waste container for {data['container']} is located at {address_text}."
# ------------------------------------------------------------------
#   Translate & run
# ------------------------------------------------------------------
def translate_to_english(text: str) -> str:
    return translator.translate(text, src="nl", dest="en").text

def run_calculation(data: Dict[str, Any]) -> str:
    opts = Options()
    if CHROME_HEADLESS:
        opts.add_argument("--headless=new")

    service = Service(ChromeDriverManager().install())
    driver  = webdriver.Chrome(service=service, options=opts)
    driver.maximize_window() # Needed to get most information on screen

    try:
        driver.get(AFVAL_URL)
        WebDriverWait(driver, DEFAULT_TIMEOUT).until(
            EC.presence_of_element_located((By.ID, "map"))
        )
        result = find_bin(driver, data)
        return result
    finally:
        time.sleep(3)
        driver.quit()