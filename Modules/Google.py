import json
import traceback

import arrow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from Modules.ConfigLand import ConfigLand
from Modules.Constants import Constants
from Modules.Dyflexis import Dyflexis
from Modules.Logger import Logger
from Modules.dataClasses import ExportReturnObject


class Google:
  creds = None
  SCOPES: list[str] = ["https://www.googleapis.com/auth/calendar.app.created"]
  calendar = None
  event = None
  config = None

  def __init__(self):
    Logger.getLogger(__name__).info("Google init")

  def get_credentials(self):
    if self.creds is None:
      google_config = self.getConfigService().getKey('google')

      if 'credentials' in google_config and google_config['credentials'] is not None:
        credentials_dict = google_config['credentials']
        self.creds = Credentials.from_authorized_user_info(credentials_dict, scopes=self.SCOPES)
    return self.creds

  def valid_creds(self):
    self.get_credentials()
    Logger.getLogger(__name__).info(
      'validCreds response {} here self.creds is: {} and valid: {}'.format(self.creds and self.creds.valid,
                                                                           self.creds is not None, self.creds.valid))
    return self.creds is not None and self.creds.valid

  def getConfigService(self):
    if self.config is None:
      self.config = ConfigLand()
    return self.config

  def login(self):
    googleConfig = self.getConfigService().getKey('google')
    Logger.getLogger(__name__).debug('google creds')
    if not self.valid_creds():
      Logger.getLogger(__name__).warning('No valid credentials found.')
      if self.creds and self.creds.expired and self.creds.refresh_token:
        Logger.getLogger(__name__).info('refreshing credentials')
        self.creds.refresh(Request())
      else:
        Logger.getLogger(__name__).info('asking for new user approval')
        flow = InstalledAppFlow.from_client_secrets_file(
          "credentials.json", self.SCOPES
        )
        self.creds = flow.run_local_server(port=0)
        googleConfig['credentials'] = json.loads(self.creds.to_json())
        # Save the credentials for the next run
        self.getConfigService().setKey('google', googleConfig)

  def forceLogin(self):
    flow = InstalledAppFlow.from_client_secrets_file(
      "credentials.json", self.SCOPES
    )
    self.creds = flow.run_local_server(port=0)
    googleConfig = self.getConfigService().getKey('google')
    googleConfig['credentials'] = json.loads(self.creds.to_json())
    self.getConfigService().setKey('google', googleConfig)

  def getService(self):
    return build('calendar', 'v3', credentials=self.creds)

  def getCalendarService(self):
    if self.calendar is None:
      self.calendar = Calendar(self.getService())
    return self.calendar

  def getEventService(self, calendar):
    '''
    setup the Event class
    :param calendar: the google Calendar object
    :return: Event class
    '''
    if self.event is None:
      self.event = Event(self.getService(), calendar['id'])
    return self.event

  def createEventData(self, dyflexysEvent):
    print('creating new Calendar event from ' + dyflexysEvent['date'])
    event = {
      "summary": None,
      "description": None,

      "start": {
        "dateTime": None,
        "timeZone": Constants.timeZone
      },
      "end": {
        "dateTime": None,
        "timeZone": Constants.timeZone
      },
    }
    return self.updateEventData(event, dyflexysEvent)

  def updateEventData(self, gevent, dyflexysEvent):
    print('update new Calendar event from ' + dyflexysEvent['date'])
    gevent['summary'] = dyflexysEvent['title']

    # nieuwe events hebben geen description
    if 'description' in gevent and gevent['description'] != None:
      # index where autogen starts
      print('new description')
      startAutoGenerated = gevent['description'].find(Constants.DESCRIPTION_PREFIX)
      print(startAutoGenerated)
      gevent['description'] = gevent['description'][0:startAutoGenerated]
    else:
      gevent['description'] = ""
    gevent['description'] = gevent['description'] + dyflexysEvent['description'] + "\n" + dyflexysEvent['id']

    gevent['start']['dateTime'] = dyflexysEvent['start_date']
    gevent['end']['dateTime'] = dyflexysEvent['end_date']
    return gevent

  def parseEventsToGoogle(self, googleCal, dyflexisEvents, periods=None):
    eventService = self.getEventService(googleCal)
    google_events = eventService.list()
    returnObject = ExportReturnObject()

    for shift in dyflexisEvents:
      shiftProcessed = False
      Logger.getLogger(__name__).info(shift['date'])
      for gEvent in google_events:
        if 'description' in gEvent and shift['id'] in gEvent['description']:
          Logger.getLogger(__name__).info('\t found!! updating')
          gEvent = self.updateEventData(gEvent, shift)
          returnObject.updateCalendarItem.append(gEvent)
          shiftProcessed = True

      if not shiftProcessed:
        print('\t not found, creating')
        gEvent = self.createEventData(shift)
        returnObject.newCalendarItem.append(gEvent)
    self.sortRemoval(returnObject, google_events, periods)
    return returnObject

  def sortRemoval(self, returnObject: ExportReturnObject, google_events, periods):
    # if we dont know the period, we won't remove anything
    if periods is None or len(periods) == 0:
      return

    for gEvent in google_events:
      # check if found event is in fact in the scanned month
      periodBreak = True
      for period in periods:
        periodMont = arrow.get(period, tzinfo=Constants.timeZone).month
        if 'start' in gEvent and 'dateTime' in gEvent['start']:
          start = arrow.get(gEvent['start']['dateTime'], tzinfo=Constants.timeZone).month
          end = arrow.get(gEvent['end']['dateTime'], tzinfo=Constants.timeZone).month
          if (start == periodMont or end == periodMont):
            periodBreak = False
      if periodBreak:
        continue
      # check if its my event or a random event
      if 'description' in gEvent and gEvent['description'] != None and Dyflexis.DESCRIPTION_PREFIX not in gEvent[
        'description']:
        continue

      if gEvent in [obj['id'] for obj in returnObject.newCalendarItem] or gEvent['id'] in [obj['id'] for obj in
                                                                                           returnObject.updateCalendarItem]:
        continue

      returnObject.removeCalendarItem.append(gEvent)
    return returnObject

  def manageCalendar(self):
    """
         haal de huidige agenda op, als hij verwijderd is of onvindbaar, maak een nieuwe aan
         :return: het googleCal object
    """
    calendar = self.getCalendarService()
    config = self.getConfigService().getKey('google')
    if 'calendarId' in config and config['calendarId'] is not None:
      try:
        googleCal = calendar.get(config['calendarId'])
        return googleCal
      except HttpError as e:
        Message = ('Google cal niet gevonden?: ')
        Logger().log(str(type(e)))
        if hasattr(e, 'message'):
          Message = Message + e.message
          Logger().log((e.message))
        else:
          Message = Message + str(e)
        Logger().log((traceback.format_exc()))

    # geen googleCal gevonden, maak nieuwe aan
    googleCal = calendar.create(Constants.getGoogleCalName())
    config['calendarId'] = googleCal['id']
    self.getConfigService().setKey('google', config)
    return googleCal

  """
  process the returnObject Data
  """

  def processData(self, googleCal, returnObject: ExportReturnObject):
    eventService = self.getEventService(googleCal)
    # update googleCal info

    googleCal['description'] = "Generated by {} \nlast updated at {}".format(Constants.appname, arrow.get(
      tzinfo=Constants.timeZone).format('YYYY-MM-DD HH:mm'))
    self.getCalendarService().update(googleCal)

    for newItem in returnObject.newCalendarItem:
      eventService.create(newItem)

    for updateItem in returnObject.updateCalendarItem:
      eventService.update(updateItem)

    for removable in returnObject.removeCalendarItem:
      eventService.remove(removable)


class Calendar:
  def __init__(self, service):
    self.service = service
    if service is None:
      raise Exception("Service cannot be None")

  def get(self, calendarId):
    '''
    get one calendar by its id
    :param calendarId:
    :return:
    '''
    return self.service.calendars().get(calendarId=calendarId).execute()

  def list(self):
    '''
    list all calendars (if scope allows)
    :return:
    '''
    calendars = []
    page_token = None
    while True:
      calendar_list = self.service.calendarList().list(pageToken=page_token).execute()
      for calendar_list_entry in calendar_list['items']:
        calendars.append((calendar_list_entry['summary'], calendar_list_entry['id']))
      page_token = calendar_list.get('nextPageToken')
      if not page_token:
        break
    return calendars

  def update(self, calendar):
    '''
    update an existing calendar as is
    :param calendar: a google calendar
    :return:
    '''
    return self.service.calendars().update(calendarId=calendar['id'], body=calendar).execute()

  def create(self, name):
    """
    create a new calendar in google
    :param name: the name of the calendar
    :return: a calendar object
    """
    calendar = {
      'summary': name,
      'timeZone': Constants.timeZone
    }
    return self.service.calendars().insert(body=calendar).execute()

  def remove(self, calenderId):
    """
    remove a calendar by its id
    :param calenderId:
    :return:
    """
    return self.service.calendars().delete(calendarId=calenderId).execute()


class Event:
  def __init__(self, service, calendarId):
    if service is None:
      raise Exception("Service cannot be None")
    self.service = service
    self.calendarId = calendarId

  def list(self):
    beforeDate = arrow.get(tzinfo=Constants.timeZone).shift(days=-1)
    page_token = None
    returnEvents = []
    while True:
      events = self.service.events().list(
        orderBy="startTime",
        singleEvents=True,
        timeMin=beforeDate,
        calendarId=self.calendarId,
        pageToken=page_token
      ).execute()
      for event in events['items']:
        returnEvents.append(event)
      page_token = events.get('nextPageToken')
      if not page_token:
        break
    return returnEvents

  def get(self):
    return self.service.events().get(calendarId='primary', eventId='eventId').execute()

  def update(self, event):
    return self.service.events().update(calendarId=self.calendarId, eventId=event['id'], body=event).execute()

  def remove(self, event):
    '''
    Remove event from the calendar
    :param event: google event object
    :return: none
    '''
    self.service.events().delete(calendarId=self.calendarId, eventId=event['id']).execute()

  def create(self, event):
    return self.service.events().insert(calendarId=self.calendarId, body=event).execute()
