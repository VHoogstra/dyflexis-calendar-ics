import json
import re

import arrow
import tkinter as tk
import tkinter.ttk as ttk

from tatsu.util import format_if

from Modules.Constants import Constants
from Modules.Logger import Logger


class ExportReturnObject:
  newCalendarItem = []
  updateCalendarItem = []
  removeCalendarItem = []

  def __init__(self):
    self.newCalendarItem = []
    self.updateCalendarItem = []
    self.removeCalendarItem = []

  def toJson(self):
    return json.dumps(
      self,
      default=lambda o: o.__dict__,
      sort_keys=True,
      indent=2)


class EventDataList:
  assignments = 0
  agenda = 0
  events = 0
  periods = []
  list = []

  def __init__(self):
    self.assignments = 0
    self.agenda = 0
    self.events = 0
    self.periods = []
    self.list = []

  def toJson(self):
    return json.dumps(
      self,
      default=lambda o: o.__dict__,
      sort_keys=True,
      indent=2)


class Period:
  def __init__(self, period=None):
    if period is None:
      self.period = arrow.get(tzinfo=Constants.timeZone).format('YYYY-MM')
    else:
      self.period = arrow.get(period, tzinfo=Constants.timeZone).format('YYYY-MM')
    self.on = True
    self.progres = 0
    self.progressBar = None

  def getTKOn(self):
    return tk.BooleanVar(value=self.on)

  def getTkProgress(self):
    return tk.IntVar(value=self.progres)


class PeriodList:
  def __init__(self, amountOfPeriods=0):
    self.periods = []
    self._handler = []
    if amountOfPeriods != 0:
      self.generatePeriodsInFuture(amountOfPeriods)
    # mogelijk update handler er bij? dan kan ik alle schermen tegelijk updaten

  def addHandler(self, handler):
    self._handler.append(handler)

  def clearHandler(self):
    self._handler.clear()

  def callHandler(self):
    for handler in self._handler:
      handler()

  def addPeriod(self, period):
    self.periods.append(period)
    self.callHandler()

  def removePeriod(self, period):
    index = self.periods.index(period)
    Logger.getLogger(__name__).info(period.period)
    self.periods.pop(index)
    self.callHandler()

  def getPeriods(self):
    return self.periods

  def generatePeriods(self, start: str, end: str):
    pattern = re.compile(r"[0-9][0-9][0-9][0-9]-[0-9][0-9]", re.IGNORECASE)
    startRegex = pattern.fullmatch(start)
    endRegeq = pattern.fullmatch(end)
    if (startRegex is None or endRegeq is None):
      raise TypeError('start {} end {} not right'.format("notGood" if startRegex is None else "Good",
                                                         "notGood" if endRegeq is None else "Good"))
    startPeriod = arrow.get(start, tzinfo=Constants.timeZone)
    endPeriod = arrow.get(end, tzinfo=Constants.timeZone)
    ##validate input
    if (startPeriod.format('YYYY') >= endPeriod.format('YYYY') and
        startPeriod.format('MM') >= endPeriod.format('MM')):
      raise Exception('Start periode moet voor eind periode zijn')
    maxCount = 100
    while maxCount >= 1:
      createdPeriod = Period(startPeriod.format('YYYY-MM'))
      index = None
      for i, period in enumerate(self.periods):
        if period.period == createdPeriod.period:
          index = i
      if (index is not None):
        self.periods[index] = createdPeriod
      else:
        self.addPeriod(createdPeriod)
      if (startPeriod.format('YYYY') == endPeriod.format('YYYY') and
          startPeriod.format('MM') == endPeriod.format('MM')):
        break
      startPeriod = startPeriod.shift(months=1)
      maxCount -= 1
    self.periods.sort(key=self.returnKey)
    self.callHandler()

  def returnKey(self,period):
    return period.period
  def generatePeriodsInFuture(self, amount):
    today = arrow.get(tzinfo=Constants.timeZone)
    end = arrow.get(tzinfo=Constants.timeZone).shift(months=amount)
    self.generatePeriods(today.format('YYYY-MM'), end.format('YYYY-MM'))

  def clearPeriods(self):
    self.periods.clear()
    self.callHandler()
