import io
import json
import logging
from pprint import pprint

from Modules.Constants import Constants
from Modules.Logger import Logger
import os.path


class ConfigLand:

  def __init__(self, useConfigFile=1):
    logger = logging.getLogger(__name__)

    self.useConfigFile = useConfigFile
    self.fileName = Constants.resource_path("config.json")
    self.Config = {
      "dyflexis": {"username": "", "password": ""},
      "ics": {"url": ""},
      "google": {"calendarId": None,'credentials':None},
      "autoPopulateConfig": False,
    }

    self.defaultConfig = {
      "dyflexis": {"username": "", "password": ""},
      "ics": {"url": ""},
      "google": {"calendarId": None,'credentials':None},
      "autoPopulateConfig": False,
    }
    self.loadConfig()

  def getKey(self, key):
    if key in self.Config:
      print(type(self.Config[key]))
      return self.Config[key]
    else:
      return self.defaultConfig[key]

  def storeKey(self, key, value):
    self.Config[key] = value
    pprint(value)
    pprint(type(value))
    self.saveConfig()

  def saveConfig(self, localConfig=None):
    # alleen als we de config gebruiken save ik de waarden. anders draaien we in memory
    if (localConfig != None):
      self.Config = localConfig
    with open(self.fileName, 'w') as fp:
      fp.write(json.dumps(self.Config,indent=2))
      fp.close()

  def loadConfig(self):
    if os.path.isfile(self.fileName):
      try:
        with open(self.fileName, 'r') as fp:
          superValue = fp.read()
          self.Config = json.loads(superValue)
          fp.close()
      except:
        Logger().log('config.json is niet json')
        self.saveConfig()
    else:
      self.saveConfig(self.defaultConfig)
      Logger().log('geen config.json gevonden, we maken dit aan')
    return self.Config
