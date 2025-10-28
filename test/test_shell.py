from os import environ
from citizenshell import SecureShell, Shell, LocalShell, ShellError
from pytest import mark, raises
try:
    from urllib.parse import quote_plus
except:
    from urllib import quote_plus

###################################################################################################

def test_localshell_by_uri():
    shell = Shell()
    assert isinstance(shell, LocalShell)
    assert shell("echo Hello World") == "Hello World"

def test_localshell_by_uri_with_env():
    shell = Shell(FOO="foo")
    assert isinstance(shell, LocalShell)
    assert shell("echo $FOO") == "foo"

def test_localshell_by_uri_with_check_xc():
    shell = Shell(check_xc=True)
    assert isinstance(shell, LocalShell)
    with raises(ShellError):
        shell("exit 44")


###################################################################################################

TEST_SSH_HOST_NOT_AVAILABLE = environ.get("TEST_SSH_HOST", None) is None

def get_secureshell_by_uri(**kwargs):
    hostname = environ.get("TEST_SSH_HOST")
    username = environ.get("TEST_SSH_USER")
    password = environ.get("TEST_SSH_PASS", None)
    port = int(environ.get("TEST_SSH_PORT", 22))
    if (hostname and username and password and port):
        shell = Shell("ssh://%s:%s@%s:%d" % (username, quote_plus(password), hostname, port), **kwargs)
    elif (hostname and username and port):
        shell = Shell("ssh://%s@%s:%d" % (username, hostname, port), **kwargs)
    else:
        assert False, "missing username and or hostname"
    assert isinstance(shell, SecureShell)
    return shell

@mark.skipif(TEST_SSH_HOST_NOT_AVAILABLE, reason="test host not available")
def test_secureshell_by_uri():
    shell = get_secureshell_by_uri()
    assert shell("echo Hello World") == "Hello World"

@mark.skipif(TEST_SSH_HOST_NOT_AVAILABLE, reason="test host not available")
def test_secureshell_by_uri_with_check_xc():
    shell = get_secureshell_by_uri(check_xc=True)
    with raises(ShellError):
        shell("exit 14")

###################################################################################################

TEST_SERIAL_PORT_AVAILABLE = environ.get("TEST_SERIAL_PORT", None) is None

def get_serialshell_by_uri(**kwargs):
    port = environ.get("TEST_SERIAL_PORT")
    username = environ.get("TEST_SERIAL_USER", None)
    password = environ.get("TEST_SERIAL_PASS", None)
    baudrate = int(environ.get("TEST_SERIAL_BAUDRATE", "115200"))   
    if username and password:
        return Shell("serial://%s:%s@%d?baudrate=%d" % (username, password, port, baudrate), **kwargs)
    else:
        return Shell("serial://%s?baudrate=%d" % (port, baudrate), **kwargs)

@mark.skipif(TEST_SERIAL_PORT_AVAILABLE, reason="test host not available")
def test_serialshell_by_uri():
    shell = get_serialshell_by_uri()
    assert shell("echo Hello World") == "Hello World"

@mark.skipif(TEST_SERIAL_PORT_AVAILABLE, reason="test host not available")
def test_serialshell_by_uri_with_env():
    shell = get_serialshell_by_uri(FOO="foo")
    assert shell("echo $FOO World") == "foo World"

@mark.skipif(TEST_SERIAL_PORT_AVAILABLE, reason="test host not available")
def test_serialshell_by_uri_with_check_xc():
    shell = get_serialshell_by_uri(check_xc=True)
    with raises(ShellError):
        shell("exit 46")
