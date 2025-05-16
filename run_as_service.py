import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import os
import sys
import asyncio

from include.discord_oauth import DISCORD_TOKEN
import logging

import main

class AppServerSvc (win32serviceutil.ServiceFramework):
    _svc_name_ = "JimmieBot"
    _svc_display_name_ = "JimmieBot Discord Bot"

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
        main.main_bot.run(DISCORD_TOKEN, log_level=logging.WARN)
        while (self._continue):
            pass

if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(AppServerSvc)