#!/usr/bin/env python3
import logging
import sys
import traceback

from Modules.Constants import Constants
from Modules.GUI import Gui
from Modules.Google import Google
from Modules.Logger import Logger


#https://tkdocs.com/shipman/index-2.html
######## Main #########
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s -\t %(message)s',
                    filename=Constants.logPrefix+"console_"+Constants.logFileName,
                    filemode='a')
# logger = logging.getLogger(__name__)
# # todo https://docs.python.org/3/library/logging.html dit uitzoeken
# logger.info('info')
# logger.warning('warn')
# logger.error('error')
# logger.critical('critical')
# logger.exception('exception')

Logger.getLogger(__name__).info(' ###\t\t\tapplication start\t\t\t###')



Constants.cleanLogFolder()
# print(sys.argv)
# for arg in sys.argv:
#     if "--headless" in arg:
#         print("Headless mode")

try:
    app = Gui()
    app.mainloop()

except Exception as e:
    Message = ('Er ging iets mis in de mainloop: ')
    Logger().log(str(type(e)))
    if hasattr(e, 'message'):
        Message = Message + e.message
    else:
        Message = Message + str(e)
    Logger.getLogger(__name__).error('Er ging wat mis bij bij Mainloop', exc_info=True)
    #todo bug scherm openen?
    raise e

sys.exit(0)

