import datetime
import json
import os.path
import traceback
from pprint import pprint

import arrow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from Modules.ConfigLand import ConfigLand
from Modules.Constants import Constants
from Modules.Logger import Logger


class Google:
  creds = None
  SCOPES: list[str] = ["https://www.googleapis.com/auth/calendar.app.created"]
  calendar = None
  event = None
  config = None

  def __init__(self):
    print("Google")

  def getCredentials(self):
    if self.creds is None:
      googleConfig = self.getConfigService().getKey('google')

      if 'credentials' in googleConfig and googleConfig['credentials'] is not None:
        credentials_dict = googleConfig['credentials']
        self.creds = Credentials(credentials_dict["token"],
                                 refresh_token=credentials_dict["refresh_token"],
                                 token_uri=credentials_dict["token_uri"],
                                 client_id=credentials_dict["client_id"],
                                 client_secret=credentials_dict["client_secret"],
                                 scopes=credentials_dict["scopes"])

  def validCreds(self):
    self.getCredentials()
    return self.creds and self.creds.valid

  def getConfigService(self):
    if self.config is None:
      self.config = ConfigLand()
    return self.config

  def login(self):
    googleConfig = self.getConfigService().getKey('google')

    if not self.validCreds():
      print('No valid credentials found.')
      if self.creds and self.creds.expired and self.creds.refresh_token:
        self.creds.refresh(Request())
      else:
        flow = InstalledAppFlow.from_client_secrets_file(
          "credentials.json", self.SCOPES
        )
        self.creds = flow.run_local_server(port=0)
        googleConfig['credentials'] = json.loads(self.creds.to_json())
        # Save the credentials for the next run
        self.getConfigService().storeKey('google', googleConfig)

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
      print(startAutoGenerated )
      gevent['description'] = gevent['description'][0:startAutoGenerated]
    else:
      gevent['description'] = ""
    gevent['description'] = gevent['description'] + dyflexysEvent['description'] + "\n" + dyflexysEvent['id']

    gevent['start']['dateTime'] = dyflexysEvent['start_date']
    gevent['end']['dateTime'] = dyflexysEvent['end_date']
    return gevent

  def manageEvents(self, googleCal, dyflexisEvents):
    eventService = self.getEventService(googleCal)
    events = eventService.list()
    seenEvents = []

    for shift in dyflexisEvents:
      shiftProcessed = False
      print(shift['date'])
      for gEvent in events:
        if shift['id'] in gEvent['description']:
          print('\t found!! updating')
          gEvent = self.updateEventData(gEvent, shift)
          seenEvents.append(gEvent['id'])
          eventService.update(gEvent)
          shiftProcessed = True

      if not shiftProcessed:
        print('\t not found, creating')
        gEvent = self.createEventData(shift)
        eventService.create(gEvent)

    for event in events:
      if event['id'] not in seenEvents:
        eventService.remove(event)
    '''
    remove events that no longer exist
    '''


  def manageCalendar(self):
    '''
    haal de huidige agenda op, als hij verwijderd is of onvindbaar, maak een nieuwe aan
    :return: het googleCal object
    '''
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
    googleCal = calendar.create(Constants.defaultGoogleCalName)
    config['calendarId'] = googleCal['id']
    self.getConfigService().storeKey('google', config)
    return googleCal

  def main(self):
    self.login()
    self.calendar = self.getCalendarService()
    try:
      calendar = self.calendar.create("ZT DYF")
      # build events class
      self.event = Event(self.getService(), calendar['id'])

      pprint(calendar)
      # look for calendar
      print(self.calendar.get(
        'ab7e56a19bcda7a349b4c3f8a1a0456e8c5f30df5241be601526ab8ebe364f86@group.calendar.google.com'))
    except HttpError as error:
      raise error


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

  def remove(self,calenderId):
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
