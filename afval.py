#afafvalcontainers.py

import re
import time
from typing import Dict, Optional, Tuple, Any
import sys

import action_chain
import util
from voice_util import say

import selenium
import googlemaps
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC

# Fix for macOS
if sys.platform == 'darwin':
    from webdriver_manager.chrome import ChromeDriverManager

# ------------------------------------------------------------------
#   Config & globals
# ------------------------------------------------------------------
AFVAL_URL = (
    "https://kaart.amsterdam.nl/afvalcontainers"
)

residual, glass, paper, textile, textile_collection, organic, bread  = (1, 2, 3, 5, 13698, 6, 7)

CHROME_HEADLESS = False
DEFAULT_TIMEOUT = 15

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
    say("Welcome to the Dutch Waste container map service. Let’s collect just a few details and find a container near you for your waste.")
    data: dict[str, any] = {}
    
    # — Ask for Address — ----------------------------------------------------
    address: str | None = None
    def store_address(v):
        nonlocal address
        address = v
        data["address"] = address
        print(f"[DEBUG] Stored street: {address}")

    h = action_chain.add_action()
    h.add_prompt_user("Please spell the name of your street?")
    h.add_get_user_input(util.INPUT_TYPE.SPELLING, store_address)
    h.add_confirm_user_input("Did I understand you correctly, the name of your street is ")
    data["address"] = "Hectorstraat 28"
    
    stNumber: int | None = None
    def store_stNumber(v):
        nonlocal stNumber
        stNumber = v
        data["address"] = data.get("address") + f" {str(stNumber)}"
        print(f"[DEBUG] Stored house number: {str(stNumber)}")

    h = action_chain.add_action()
    h.add_prompt_user("What is your house number?")
    h.add_get_user_input(util.INPUT_TYPE.NUMBER, store_stNumber)
    h.add_confirm_user_input("Did I understand you correctly, your house number is ")

     # — Ask for container type — ----------------------------------------------------
    container: int | None = None
    type_mapping = {
        "residual waste": 1,
        "glass": 2,
        "paper": 3,
        "textile containers": 5,
        "organic waste": 6,
        "bread and pastry waste" : 7
    }
    def store_container(v):
        nonlocal container
        container = v
        data["container"] = 13698 if container == "textile collection" else int("1249" + str(type_mapping[v]))
        print(f"[DEBUG] Stored container type: {container}")

    h = action_chain.add_action()
    h.add_prompt_user("What is the container type you want to find? Residual waste or glass or paper or textile collection, or textile containers, or organic waste, or bread and pastry waste.")
    h.add_get_user_input(util.INPUT_TYPE.CONTAINER, store_container)
    h.add_confirm_user_input("Did I understand you correctly, the container type you want to find is ")

    # fill dummy data for testing
    #data["container"] = residual  # Default to residual waste
    #say(f"Thanks. I will now search for the nearest waste container for {data.get('container')} at {data.get('address')}.")

    action_chain.run()

    return data

# ------------------------------------------------------------------
#   Browser-automation helpers & utilities
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
    container_type_value = data["container"]
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
    while True:
        try:
            first_marker.click()
            break
        except selenium.common.exceptions.ElementClickInterceptedException:
            # zoom out a bit
            zoom_button = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "leaflet-control-zoom-out")))
            zoom_button.click()
            time.sleep(0.5)


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

    # Get the distance and duration from the waste container to the user's address
    distance, duration = get_route_info(driver, data["address"], address_text)
    address_text_short = ','.join(address_text.split(',')[:2]).strip()

    result = f"I found a container at {address_text_short}, which is {distance} away. It takes about {duration} by foot)."
    say(result)
    print("[DEBUG] Result:", result)

    # Open Google Maps with the route to the waste container
    say("I will now start the route to this waste container for you on Google Maps.")
    maps_url = build_maps_url(data["address"], address_text)
    driver.get(maps_url)

# ------------------------------------------------------------------
#  Build a Google Maps directions URL
# ------------------------------------------------------------------
def build_maps_url(origin: str, destination: str) -> str:
    from urllib.parse import quote_plus
    o = quote_plus(origin)
    d = quote_plus(destination)
    return f"https://www.google.com/maps/dir/?api=1&origin={o}&destination={d}&travelmode=walking"

# ------------------------------------------------------------------
#  Scrape distance & duration from Google Maps page
# ------------------------------------------------------------------
def get_route_info(driver: webdriver.Chrome, origin: str, destination: str) -> Tuple[str, str]:
    wait = WebDriverWait(driver, DEFAULT_TIMEOUT)
    # navigate to Maps directions
    maps_url = build_maps_url(origin, destination)
    driver.get(maps_url)

    # wait for the first route card
    card = wait.until(EC.visibility_of_element_located((
        By.XPATH,
        "//div[starts-with(@id,'section-directions-trip-0')]"
    )))

    route_div = card.find_element(By.CSS_SELECTOR, "div.XdKEzd")
    info_divs = route_div.find_elements(By.TAG_NAME, "div")
    if len(info_divs) < 2:
        raise RuntimeError(f"Unexpected structure under XdKEzd: only {len(info_divs)} divs found")

    # 4) first div is duration, second is distance
    duration = card.find_element(By.CSS_SELECTOR, "div.XdKEzd > div.Fk3sm").text       
    distance = card.find_element(By.CSS_SELECTOR, "div.XdKEzd > div.ivN21e").text

    return distance, duration
# ------------------------------------------------------------------
#   Run
# ------------------------------------------------------------------
def run_calculation(data: Dict[str, Any]) -> str:
    opts = Options()
    opts.add_experimental_option("detach", True)
    if CHROME_HEADLESS:
        opts.add_argument("--headless=new")

    # macOS fix again
    if sys.platform == 'darwin':
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=opts)
    else:
        driver = webdriver.Chrome(options=opts)

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

if __name__ == '__main__':
    ########## Task 3: Finding nearest bin ###########
    user_data = collect_user_data()
    run_calculation(user_data)
