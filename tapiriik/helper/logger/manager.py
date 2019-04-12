# Synchronization module for decathloncoach.com
# (c) 2019 Anael Jourdain, anael.jourdain.partner@decathlon.com
from tapiriik.settings import LOG_PATH
import json
import sys
import os
import io
import logging
import logging.handlers

class LoggerManager():

    _logger = logging
    _log_dir = LOG_PATH
    _log_file = "dc_log"
    _filename= "global"
    _filename_full=""
    _name = "Global"
    _formatter = None
    _handler = None

    _logger_conf = {
        'format':'%(asctime)s|%(filename)s:%(lineno)d|%(levelname)s\t|\t%(message)s',
        'datefmt': '%Y-%m-%d %H:%M:%S',
        'level': logging.INFO
    }

    _global_logger = None

    def __init__(self, name=None, filename=None):
        """logging.basicConfig(
            level=logging.INFO,
            format=self._logger_conf['format'],
            datefmt=self._logger_conf['datefmt'],
        )"""
        self.build_logger(name, filename)

    def build_logger(self, name=None, filename=None):

        if name:
            self._name = name

        if filename is not None:
            self._filename = filename

        #Define logger
        self._global_logger = logging.getLogger(self._name)

        #Define level
        self._global_logger.setLevel(self._logger_conf['level'])

        #Define format
        self._formatter = logging.Formatter(self._logger_conf['format'], self._logger_conf['datefmt'])

        #Define handler for filename
        filename_full = self._log_dir + '/' + self._log_file + '_' + self._filename + '.log'
        self._filename_full = filename_full
        self._logger = logging
        self._logger.getLogger(self._name)
        self.define_stream_handler()


    def get_logging(self):
        return self._logger

    def use_logger(self, name=None, filename=None):

        if name is not self._name:
            self.build_logger(name, filename)

    def define_stream_handler(self):

        logging_console_handler = logging.StreamHandler(io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8'))
        logging_console_handler.setLevel(self._logger_conf['level'])
        logging_console_handler.setFormatter(self._formatter)
        self._global_logger.addHandler(logging_console_handler)

    def define_rotate_handler(self, complement_name):
        self._filename = complement_name
        filename_full = self._log_dir + '/' + self._log_file + '_' + self._filename + '.log'
        self._filename_full = filename_full

        self._handler = logging.handlers.RotatingFileHandler(filename_full, maxBytes=0, backupCount=5, encoding="utf-8")
        self._handler.setFormatter(self._formatter)
        self._handler.doRollover()
        self._global_logger.addHandler(self._handler)

    def remove_handler(self):
        self._global_logger.removeHandler(self._handler)
        self._handler.flush()
        self._handler.close()
