import json
from pprint import pprint

import requests
import arrow
from ics import Calendar, Event


# https://icspy.readthedocs.io/en/stable/index.html
# https://arrow.readthedocs.io/en/latest/
class ICS:
    calendar = None

    def connectToICS(self, url=None, file=None):
        content = None
        if (url is not None):
            content = requests.get(url).text

        if (file is not None):
            with open(file, 'r') as fp:
                content = fp.read()

        if content == None:
            return;

        self.calendar = Calendar(content)

        print("calendar connectToICS event lengths " + str(len(self.calendar.events)))
        # c.events # lijst met evenementen in de dingus, kan ik met een map/foreach op filteren? indexen?
        # eventondate = self.isEventOnDate('2025-03-23')
        tz = "Europe/Amsterdam"

        test = self.calendar.timeline.on(arrow.get("2025-03-20", tzinfo=tz))
        pprint(test)
        for bla in test:
            pprint(bla)

            # self.calendar.events.add(bla)
        # with open('my.ics', 'w') as fp:
        #     fp.writelines( self.calendar.serialize_iter())
        #     fp.close()

    def createNewEvent(self, dyflexysEvent):
        print('creating new Calendar event from ' + dyflexysEvent['date'])
        event = Event()
        event.name = dyflexysEvent['title']
        event.description = dyflexysEvent['description'] + "\n\n\n " + dyflexysEvent['id']
        event.begin = dyflexysEvent['start_date']
        event.end = dyflexysEvent['end_date']
        return event

    def updateEvent(self,event, dyflexysEvent):
        print('creating new Calendar event from ' + dyflexysEvent['date'])
        event.name = dyflexysEvent['title']
        event.description = dyflexysEvent['description'] + "\n\n\n " + dyflexysEvent['id']
        event.begin = dyflexysEvent['start_date']
        event.end = dyflexysEvent['end_date']
        return event

    def isEventOnDate(self, date):
        eventOnDate = self.calendar.timeline.on(arrow.get(date))

        for event in eventOnDate:
            # print(event)
            print(event.name)
            if "id" in event.description:
                print('id is in description ')

    def generateToICS(self, events):
        if self.calendar is None:
            self.calendar = Calendar()

        print('calendar created')
        tz = "Europe/Amsterdam"

        for event in events:
            updated = False
            if arrow.get(event['date']).is_between(arrow.now(tz).shift(years=-1), arrow.now(tz)):
                continue
            print('\tcreating event ' + event['start_date'])
            test = self.calendar.timeline.on(arrow.get(event['start_date'], tzinfo=tz))
            pprint(test)
            for bla in test:
                pprint(bla)
                if event['id'] in bla.description:
                    self.updateEvent(bla,event)
                    updated = True
            if not updated:
                self.calendar.events.add(self.createNewEvent(event))

        with open('my.ics', 'w') as fp:
            fp.writelines(self.calendar.serialize_iter())
            fp.close()
