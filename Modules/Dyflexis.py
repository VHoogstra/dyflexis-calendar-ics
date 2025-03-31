from pprint import pprint

from selenium.common import TimeoutException
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import time
import arrow

from selenium.webdriver.chrome.options import Options
from selenium import webdriver

from Exceptions.BadLoginException import BadLoginException
from Modules.Logger import Logger


class Dyflexis:
    tz = "Europe/Amsterdam"
    DESCRIPTION_PREFIX = "=== CODE GENERATED BELOW ==="
    driver = None

    def __init__(self, config, width, height, minChromeWidth):
        self.config = config
        self.width = width
        self.height = height
        self.minChromeWidth = minChromeWidth

    def __str__(self):
        return 'Dyflexis'

    def openChrome(self):
        if self.driver == None:
            ws = self.width / 3
            if ws < self.minChromeWidth:
                ws = self.minChromeWidth
            hs = self.height
            options = Options()
            # options.add_argument("--headless")
            options.add_argument('window-size=%d,%d' % (ws, hs))
            self.driver = webdriver.Chrome(options=options)

    def login(self, _progressbarCallback=None):
        startProgress = 0
        endProgress = 5
        # progressbar 0 through 10
        config = self.config.Config
        self.driver.get(config["routes"]["loginUrl"])
        WebDriverWait(self.driver, 20).until(EC.presence_of_element_located((By.ID, "username")))

        if _progressbarCallback:
            _progressbarCallback(startProgress)
        # wait for page load
        if (config["dyflexis"]["username"] == ""):
            raise BadLoginException('no username')
        # gebruikersnaam invullen
        self.driver.find_element(by=By.ID, value="username").send_keys(config["dyflexis"]["username"])

        if (config["dyflexis"]["password"] == ""):
            raise BadLoginException('no password')
        # wachtwoord invullen
        self.driver.find_element(by=By.ID, value="password").send_keys(config["dyflexis"]["password"])
        if _progressbarCallback:
            _progressbarCallback(endProgress / 2)
        # knop indrukken en inloggen
        self.driver.find_element(by=By.ID, value="do-login").click()

        try:
            WebDriverWait(self.driver, 6).until(EC.invisibility_of_element_located((By.ID, "username")))
        except TimeoutException as e:
            # de inlog ging niet goed bij dyflexis
            raise BadLoginException("De login bij dyflexis was niet succesvol")

        if _progressbarCallback:
            _progressbarCallback(endProgress)
        if (self.driver.current_url == config["routes"]["loginUrl"]):
            # inlog mis gegaan, fout geven
            print('er is iets mis gegaan bij het inloggen, zie het scherm')
            return False
        if (self.driver.current_url == config["routes"]["homepageAfterLogin"]):
            print('login succesvol')
            return True

    def run(self, _progressbarCallback=None):
        try:
            self.openChrome()
            logger = Logger()
            # progressbar 0 through 5
            self.login(_progressbarCallback)
            # progressbar 5 through 50
            thisMonth = arrow.now().format('YYYY-MM')
            nextMonth = arrow.now().shift(months=1).format('YYYY-MM')
            data = self.getRooster(_progressbarCallback, period=thisMonth)
            data = self.getRooster(_progressbarCallback, period=nextMonth, baseData=data)
            # progressbar 75 through 100
            eventData = self.elementArrayToIcs(data, _progressbarCallback)
        except Exception as e:
            self.driver.quit()
            self.driver = None
            raise e

        logger.toFile(location='icsData.json', variable=eventData)
        self.driver.quit()
        self.driver = None
        return eventData

    def getRooster(self, _progressbarCallback=None, period=None, baseData=None):

        # todo get rooster today en next month
        # print(calendarNextMonthButton[1].get_attribute('href'))
        # self.driver.get(calendarNextMonthButton[1].get_attribute('href'))
        config = self.config.Config
        startProgress = 5
        endProgress = 75

        if _progressbarCallback:
            _progressbarCallback(startProgress)
        route = config['routes']['roosterUrl']
        if period != None:
            route = route + '?periode=' + period
        else:
            period = arrow.get(tzinfo=self.tz).format('YYYY-MM')
        self.driver.get(route)
        WebDriverWait(self.driver, 20).until(EC.presence_of_element_located((By.CLASS_NAME, "main-bar-inner")))
        calendar = self.driver.find_element(by=By.CLASS_NAME, value='calender')

        print('de maand word uitgelezen')
        if _progressbarCallback:
            _progressbarCallback(6)
        if (baseData != None):
            returnArray = baseData
        else:
            returnArray = {
                "assignments": 0,
                "agenda": 0,
                "events": 0,
                "list": []
            }

        body = calendar.find_element(by=By.TAG_NAME, value='tbody')
        rows = body.find_elements(by=By.TAG_NAME, value='tr')

        progressRowCount = (endProgress - startProgress) / len(rows)

        for row in rows:
            print('regel word uitgelezen')
            columns = row.find_elements(by=By.TAG_NAME, value='td')
            for column in columns:
                print('\tkolom word uitgelezen\t' + column.text[0:2])

                # als de datum in het verleden ligt lezen we hem niet uit
                startOfMonth = arrow.get(period, tzinfo=self.tz).replace(day=1, hour=0, minute=0, second=0)
                endOfMonth = arrow.get(period, tzinfo=self.tz).shift(months=1, minutes=-1)
                eventDate = arrow.get(column.get_attribute('title'), tzinfo=self.tz)
                pprint((" start vs event" ,startOfMonth > eventDate ,"end vs date ",endOfMonth < eventDate))
                pprint((startOfMonth , eventDate, endOfMonth))
                if startOfMonth > eventDate or endOfMonth < eventDate:
                    print('\t\t skipped: wrong month')
                    continue

                if not (arrow.get(column.get_attribute('title'), tzinfo=self.tz) >
                        arrow.now().replace(hour=0, minute=0).shift(days=-1)):
                    print('\t\t skipped: before today')
                    continue
                ## find events aka shows
                events = column.find_elements(by=By.CLASS_NAME, value='evt')
                eventList = []
                if len(events) != 0:
                    for event in events:
                        # click event to open info
                        event.click()
                        WebDriverWait(self.driver, 20).until(
                            EC.visibility_of_element_located((By.CSS_SELECTOR, "div.c-rooster2.a-info")))

                        popup = self.driver.find_element(by=By.CSS_SELECTOR, value="div.c-rooster2.a-info")
                        divWithInfo = popup.find_elements(by=By.TAG_NAME, value='div')[2]

                        eventList.append(
                            {"id": event.get_attribute('uo'), "text": event.text, 'description': divWithInfo.text})
                        self.driver.find_element(by=By.CLASS_NAME, value='close-flux').click()
                        WebDriverWait(self.driver, 20).until(
                            EC.invisibility_of_element_located((By.CSS_SELECTOR, "div.c-rooster2.a-info")))

                ## find assignments, aka diensten
                assignments = column.find_elements(by=By.CLASS_NAME, value='ass')
                assList = []
                if len(assignments) != 0:
                    for assignment in assignments:
                        assignmentInnerDiv = assignment.find_element(by=By.TAG_NAME, value='div')
                        tijd = assignment.find_element(by=By.TAG_NAME, value='b')

                        assList.append({
                            "id": assignment.get_attribute('uo'),
                            "tijd": tijd.text,
                            "text": assignmentInnerDiv.text
                        })

                ## find agenda aka gewerkte uren
                agendas = column.find_elements(by=By.CLASS_NAME, value='agen')
                aggList = []
                if len(agendas) != 0:
                    for agenda in agendas:
                        aggList.append({"id": agenda.get_attribute('uo'), "text": agenda.text})

                returnArray['list'].append(
                    {
                        "date": column.get_attribute('title'),
                        "text": column.text,
                        "events": eventList,
                        'assignments': assList,
                        'agenda': aggList,
                    })
                returnArray['events'] =returnArray['events'] + len(eventList)
                returnArray['assignments'] = returnArray['assignments']+ len(assList)
                returnArray['agenda'] = returnArray['agenda']+ len(aggList)
                ##progress for column
                if _progressbarCallback:
                    # gedeeld door 7 omdat er 7 dagen in de week zijn
                    startProgress = startProgress + (progressRowCount / 7)
                    _progressbarCallback(startProgress)
            # progress for row
            if _progressbarCallback:
                startProgress = startProgress + progressRowCount
                _progressbarCallback(startProgress)

        print('done')
        if _progressbarCallback:
            _progressbarCallback(50)

        return returnArray

    def elementArrayToIcs(self, elementArray, _progressbarCallback=None):
        # 75 ->100
        startProgress = 75
        endProgress = 100

        if _progressbarCallback:
            _progressbarCallback(startProgress)
        print('elementArrayToIcs')
        shift = []
        tz = "Europe/Amsterdam"
        progressRowCount = (endProgress - startProgress) / len(elementArray['list'])

        for dates in elementArray['list']:

            startDate = arrow.get(dates['date'], tzinfo=tz)
            stopDate = arrow.get(dates['date'], tzinfo=tz)
            print(dates['date'])
            if (dates['text'] == ""):
                continue
            for assignments in dates['assignments']:
                description = self.DESCRIPTION_PREFIX + "\n"

                ## start date and time
                start_time = assignments['tijd'][0:5]
                print('\twith date ' + start_time + " and times " + start_time[0:2] + " and sec " + start_time[3:5])

                startDate = startDate.replace(hour=int(start_time[0:2]), minute=int(start_time[3:5]))
                print("\t" + startDate.format('YYYY-MM-DDTHH:mm:ss'))
                # stop date and time
                stop_time = assignments['tijd'][8:13]
                stopDate = stopDate.replace(hour=int(stop_time[0:2]), minute=int(stop_time[3:5]))
                # create name depending on what is in text
                print(" \t" + assignments['text'])
                if "Kleine Zaal".upper() in assignments['text'].upper():
                    name = ""
                    for event in dates['events']:
                        if "kz".upper() in event['text'].upper():
                            name = name + event['text']
                            description = description + event['description']
                elif "Grote Zaal".upper() in assignments['text'].upper():
                    name = ""
                    for event in dates['events']:
                        if "ah".upper() in event['text'].upper():
                            name = name + event['text']
                            description = description + event['description']

                else:
                    name = assignments['text'][33:]
                shift.append({
                    'date': startDate.format('YYYY-MM-DD'),
                    "start_date": startDate.format('YYYY-MM-DDTHH:mm:ssZZ'),  # 20250321T090000Z
                    "end_date": stopDate.format('YYYY-MM-DDTHH:mm:ssZZ'),  # 20250321T170000Z
                    'title': name,
                    'description': description,
                    'id': assignments['id']
                })

            if _progressbarCallback:
                startProgress = startProgress + progressRowCount
                _progressbarCallback(startProgress)
        elementArray["shift"] = shift
        return elementArray

    def test(self):
        config = self.config.Config
        self.driver.get(config["routes"]["roosterUrl"])
        WebDriverWait(self.driver, 20).until(EC.presence_of_element_located((By.CLASS_NAME, "main-bar-inner")))
        event = self.driver.find_element(by=By.CSS_SELECTOR, value="div[uo='event://1698']")
        event.click()
        time.sleep(1)
        popup = self.driver.find_element(by=By.CSS_SELECTOR, value="div.c-rooster2.a-info")
        divWithInfo = popup.find_elements(by=By.TAG_NAME, value='div')[2]
        pprint(divWithInfo.text)
        # todo, click op event en dan daar de tekst uit slepen
