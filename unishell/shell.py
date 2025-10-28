from .parseduri import ParsedUri
from .localshell import LocalShell
from .secureshell import SecureShell
from .serialshell import SerialShell
from logging import CRITICAL

def Shell(uri: ParsedUri | None = None, check_xc: bool = False, check_err: bool = False, wait: bool = True, log_level: int = CRITICAL, **kwargs):
    parsed_uri = ParsedUri(uri, check_xc=check_xc, check_err=check_err, wait=wait, 
                           log_level=log_level, **kwargs)
    if parsed_uri.scheme == "local":
        return LocalShell(**parsed_uri.kwargs)
    elif parsed_uri.scheme == "ssh":
        return SecureShell(hostname=parsed_uri.hostname, username=parsed_uri.username, 
                           password=parsed_uri.password, port=parsed_uri.port, **parsed_uri.kwargs)
    elif parsed_uri.scheme == "serial":
        return SerialShell(port=parsed_uri.port, username=parsed_uri.username, 
                           password=parsed_uri.password, baudrate=parsed_uri.baudrate, **parsed_uri.kwargs)
            
    raise RuntimeError("unknown scheme '%s'" % parsed_uri.scheme)
