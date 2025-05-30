import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import os
import sys
import asyncio
import threading
import time

import main
from include.discord_oauth import DISCORD_TOKEN
import logging

class AppServerSvc (win32serviceutil.ServiceFramework):
    _svc_name_ = "ArchipelagoRelay"
    _svc_display_name_ = "ArchipelagoRelay Discord Bot"

    _continue = True

    def __init__(self,args):
        if sys.platform == "win32" and sys.version_info >= (3, 8, 0):
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        win32serviceutil.ServiceFramework.__init__(self,args)
        os.chdir(os.path.dirname(__file__))
        self.hWaitStop = win32event.CreateEvent(None,0,0,None)
        socket.setdefaulttimeout(60)

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
        self._continue = False

    def SvcDoRun(self):
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                              servicemanager.PYS_SERVICE_STARTED,
                              (self._svc_name_,''))
        self.main()

    def main(self):
        threading.Thread(target=main.main_bot.run, kwargs={'token': DISCORD_TOKEN, 'log_level': logging.WARN}).start()
        while (self._continue):
            time.sleep(1)


if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(AppServerSvc)