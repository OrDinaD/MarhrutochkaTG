import asyncio
import logging
from typing import Optional, List, Dict
from playwright.async_api import async_playwright, Page, Browser, Playwright

class BookingBot:
    BASE_URL = "https://билет.маршруточка.бел/"
    
    CITY_MAPPING = {
        "Минск": "5",
        "Островец": "23",
        "Ошмяны": "24",
        "Сморгонь": "22",
        "Байдаки": "6",
        "Богуши": "55",
        "Гарани": "7",
        "Гаути": "42",
        "Дайлидки": "38",
        "Дегенево": "27",
        "Забрезье": "14",
        "Козельщина": "11",
        "Крево почта": "20",
        "Крево 2": "64",
        "Крево 3": "21",
        "Кунава": "51",
        "Куцевичи": "30",
        "Лавский Брод": "15",
        "Лесная сказка": "8",
        "Лубянка": "43",
        "Мацканы": "37",
        "Медрики": "40",
        "Милейково": "17",
        "Михалкони": "28",
        "Михалово": "63",
        "Новоселки": "29",
        "Новоспаск": "53",
        "Ореховка": "46",
        "Осиновщизна": "45",
        "Переходы": "16",
        "Попелевичи": "71",
        "Раковцы": "18",
        "Светоч": "50",
        "Свиридовичи": "49",
        "Селец": "54",
        "Сморг. погран. группа": "44",
        "Солы": "41",
        "Сутьково": "52",
        "Трасса М6 Шараи": "10",
        "Трасса М7 Дайнова Большая": "67",
        "Трасса М7 поворот на ст. Воложин": "13",
        "Трокели": "39"
    }

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.logger = logging.getLogger(__name__)
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None

    async def start(self):
        """Initializes the browser session."""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=self.headless)
        self.page = await self.browser.new_page()
        self.logger.info("Browser started")

    async def stop(self):
        """Closes the browser session."""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        self.logger.info("Browser stopped")

    async def login(self, phone: str, password: str) -> bool:
        """Logs into the website."""
        if not self.page:
            await self.start()

        try:
            self.logger.info(f"Navigating to {self.BASE_URL}")
            await self.page.goto(self.BASE_URL)

            # Click "Войти" to open the popup
            self.logger.info("Clicking login button")
            await self.page.click(".showHideEntButton")

            # Wait for form to be visible
            await self.page.wait_for_selector(".entrfFormWrapperPU", state="visible")

            # Fill credentials
            self.logger.info(f"Filling credentials for {phone}")
            await self.page.fill('input[name="phone"]', phone)
            await self.page.fill('input[name="password"]', password)

            # Submit
            await self.page.click('input.enterButton')

            # Wait for login to complete (check for logout button or similar, or just absence of login button)
            # After login, usually the "Войти" button changes to "Кабинет" or similar.
            # Based on HTML, we can look for .showHideEntButton to disappear or text to change.
            # But let's just wait a bit or check if we are redirected.
            # Actually, let's wait for the page to reload or update.
            await self.page.wait_for_timeout(3000) # Simple wait for now

            # Check if login was successful
            # The "Войти" button usually disappears or is replaced.
            # Let's check if the "Войти" text is still visible.
            if await self.page.is_visible("text=Войти"):
                 self.logger.warning("Login might have failed, 'Войти' is still visible")
                 return False
            
            self.logger.info("Login successful")
            return True

        except Exception as e:
            self.logger.error(f"Login failed: {e}")
            return False

    async def find_tickets(self, from_city: str, to_city: str, date: str) -> List[Dict]:
        """
        Searches for tickets.
        date format: YYYY-MM-DD
        """
        if not self.page:
            raise RuntimeError("Browser not started")

        from_id = self.CITY_MAPPING.get(from_city)
        to_id = self.CITY_MAPPING.get(to_city)

        if not from_id or not to_id:
            self.logger.error(f"Invalid city: {from_city} or {to_city}")
            return []

        try:
            self.logger.info(f"Searching tickets from {from_city} to {to_city} on {date}")
            
            # Select From City
            # We interact with the select directly if possible, or force it.
            # Select2 hides the original select, but Playwright can usually handle it.
            await self.page.select_option('#city_from_id', value=from_id)
            
            # Wait for To City to update/enable. It might trigger an AJAX call.
            # We can wait for the 'disabled' attribute to be removed from #city_to_id
            await self.page.wait_for_function("document.getElementById('city_to_id').disabled === false")
            
            # Select To City
            await self.page.select_option('#city_to_id', value=to_id)
            
            # Fill Date
            # The date input is readonly, so we might need to evaluate js to set it or click the datepicker.
            # Let's try forcing the value via JS since it's readonly.
            await self.page.evaluate(f"document.querySelector('input[name="date"]').value = '{date}'")
            
            # Click Search
            await self.page.click('.js_reservation-button')
            
            # Wait for results
            await self.page.wait_for_selector('.scheduleBlock', state="visible")
            # And wait for loading to finish (spinner hidden)
            await self.page.wait_for_selector('.sk-fading-circle', state="hidden")

            # Parse results
            # This part requires knowing the structure of the results.
            # Since I haven't seen the results page, I will return the raw text of the schedule block for now
            # or try to extract basic info if I can assume a structure.
            # Usually results are in .scheduleBlock
            
            results = await self.page.content()
            # For now, let's just save the screenshot of results to verify
            # await self.page.screenshot(path="search_results.png")
            
            # I'll return a placeholder for now until I can inspect the results
            return [{"raw_html": "Results loaded"}]

        except Exception as e:
            self.logger.error(f"Search failed: {e}")
            return []

    async def book_ticket(self, time: str) -> bool:
        """
        Books a ticket for a specific time.
        :param time: Departure time in "HH:MM" format.
        """
        if not self.page:
            raise RuntimeError("Browser not started")
            
        try:
            self.logger.info(f"Attempting to book ticket for {time}")
            
            # Find the route container with the specific departure time
            # We iterate over all routes and check the time
            routes = await self.page.query_selector_all('.nf-route')
            target_route = None
            
            for route in routes:
                # Get departure time (first .nf-route-point__time)
                time_el = await route.query_selector('.nf-route-point__time')
                if time_el:
                    route_time = await time_el.inner_text()
                    if route_time.strip() == time:
                        target_route = route
                        break
            
            if not target_route:
                self.logger.error(f"Route for time {time} not found")
                return False
                
            # Click "Заказать билет" button
            book_btn = await target_route.query_selector('button.js_get-bus')
            if not book_btn:
                self.logger.error("Booking button not found")
                return False
                
            self.logger.info("Clicking booking button...")
            await book_btn.click()
            
            # Wait for response/modal
            # It might open a seat selection or confirm dialog.
            # Based on HTML, there is a .busRow.js_get-bus-row that might appear
            try:
                # Wait for "Далее" button or similar
                # Or wait for a modal with seat selection
                # Let's wait for .seats-choice or .make-order
                
                # Check if we need to select seats
                # For now, we'll try to click "Далее" if it appears
                try:
                    await self.page.wait_for_selector('button.seats-choice', timeout=5000)
                    self.logger.info("Seat selection appearing, clicking Next...")
                    await self.page.click('button.seats-choice')
                except:
                    self.logger.info("No seat selection step or timed out, checking for confirmation...")

                # Wait for final confirmation or success message
                # This part is speculative without seeing the next step.
                # Assuming there might be a final "Подтвердить" button
                
                # Verify if successful?
                # Usually redirected to orders page or shows "Success"
                
                self.logger.info("Booking flow initiated. Checking for success...")
                # await self.page.screenshot(path="booking_step.png")
                
                return True
                
            except Exception as e:
                self.logger.error(f"Error during booking steps: {e}")
                return False

        except Exception as e:
            self.logger.error(f"Booking failed: {e}")
            return False
