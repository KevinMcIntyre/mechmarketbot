import logging
import os
import traceback

import sys


def write_pid_file():
    pid = str(os.getpid())
    f = open('bot.pid', 'w+')
    f.write(pid)
    f.close()


def log_exception():
    exc_type, exc_value, exc_traceback = sys.exc_info()
    lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
    logging.getLogger('mechbot.log').error(''.join('!! ' + line for line in lines))
