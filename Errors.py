import Dir

class Error(Exception):
    pass

class MicrocontrollerNotFound(Error):
    pass

class LedsLessThanMinimum(Error):
    pass

class NoAudioFound(Error):
    pass

class PortAccessDenied(Error):
    pass

class LedCountNotSet(Error):
    pass

class LedCountLessThanMinimum(Error):
    pass

class InvalidConfig(Error):
    pass

class InvalidInstrument(Error):
    pass

class InvalidFillType(Error):
    pass



