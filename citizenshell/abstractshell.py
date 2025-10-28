from .shellerror import ShellError
from uuid import uuid4
from logging import getLogger, StreamHandler, Formatter, INFO, DEBUG, ERROR, CRITICAL
from sys import stdout, stderr
from termcolor import colored
from os import chmod, stat


class AbstractShell(dict):

    # TODO: allow to pass logger or log handlers from outside
    def __init__(self, check_xc: bool = False, check_err: bool = False, wait: bool = True, log_level: int = CRITICAL, **kwargs):
        dict.__init__(self, kwargs)
        self._local_env = {}
        self._check_xc = check_xc
        self._check_err = check_err
        self._wait = wait
        self._id = uuid4().hex[:16].upper()
        self._in_logger = self._build_logger("%s.in" % str(self), stdout, prefix="$ ", color="cyan")
        self._out_logger = self._build_logger("%s.out" % str(self), stdout, attrs=[])
        self._err_logger = self._build_logger("%s.err" % str(self), stderr, color="red")
        self._oob_logger = self._build_logger("%s.oob" % str(self), stdout, prefix="> ", color="yellow")
        self._spy_read_logger = self._build_logger("%s.spy.read" % str(self), stdout, prefix="<<< ", color="magenta")
        self._spy_write_logger = self._build_logger("%s.spy.write" % str(self), stdout, prefix=">>> ", color="green")
        self.set_log_level(log_level)
        self._available_commands = {}
        self._os_type = None  # Detected lazily on first use

    def id(self):
        return self._id

    def __repr__(self):
        return "%s(id=%s)" % (self.__class__.__name__, self._id)

    # TODO: cwd could be of type Path (check how it works with remote paths)
    def __call__(self, cmd: str, check_xc: bool | None = None, check_err: bool | None = None, wait: bool | None = None, cwd: str | None = None, timeout: float | None = None, **kwargs):
        check_xc = check_xc if check_xc is not None else self._check_xc
        check_err = check_err if check_err is not None else self._check_err
        wait = wait if wait is not None else self._wait

        env = dict(self)
        env.update(kwargs)
        self._result = self.execute_command(command=cmd, env=env, wait=wait, check_err=check_err, cwd=cwd, timeout=timeout)

        if check_xc and self._result.exit_code() != 0:
            raise ShellError(cmd, "exit code '%s'" % str(self._result.exit_code()))
        return self._result

    def wait(self):
        self._result.wait()

    def execute_command(self, command: str, env: dict = {}, wait: bool = True, check_err: bool = False, cwd: str | None = None, timeout: float | None = None):
        raise NotImplementedError("this method must be implemented by the subclass")

    @staticmethod
    def _build_logger(name, stream, prefix="", color=None, attrs=["bold"]):
        logger = getLogger(name)
        logger.setLevel(CRITICAL)
        handler = StreamHandler(stream)
        formatter = Formatter(colored(prefix, attrs=attrs) + colored('%(message)s', color=color, attrs=attrs))
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger

    def set_log_level(self, level):
        self._log_level = level
        self._in_logger.setLevel(level)
        self._out_logger.setLevel(level)
        self._err_logger.setLevel(level)
        self._oob_logger.setLevel(level)
        self._spy_read_logger.setLevel(level)
        self._spy_write_logger.setLevel(level)

    def log_stdin(self, text):
        self._in_logger.info(text)

    def log_stdout(self, text):
        self._out_logger.info(text)

    def log_stderr(self, text):
        self._err_logger.error(text)

    def log_oob(self, text):
        self._oob_logger.info(text)

    def log_spy_read(self, text):
        self._spy_read_logger.debug(repr(text))

    def log_spy_write(self, text):
        self._spy_write_logger.debug(repr(text))

    def detect_command(self, *alternatives, **kwargs):
        for alternative in alternatives:
            if self.execute_command("command -v %s" % alternative):
                return alternative
        if kwargs.get("mandatory", True):
            raise RuntimeError("could find command '%s', tried any of the the following: %s" % (alternatives[0], alternatives))
        return None
        
    def get_command(self, *alternatives, **kwargs):
        command = alternatives[0]
        if command not in self._available_commands:
            detected = self.detect_command(*alternatives, **kwargs)
            self._available_commands[command] = detected
            return detected
        return self._available_commands[command]

    def md5(self, path, mandatory=False):
        command = self.get_command("md5sum", "md5", mandatory=mandatory)
        result = self.execute_command("%s '%s'" % (command, path))
        return str(result).split()[0].strip() if result else None

    def hexdump(self, path, mandatory=True):
        command = self.get_command("hexdump", "od", mandatory=mandatory)
        if command == "hexdump":
            result = self.execute_command("hexdump -C %s | cut -c 10-60" % path)
        elif command == "od":
            result = self.execute_command("od -t x1 -An %s" % path)
        return str(result).replace(" ", "").rstrip("\r\n")
        
    def _detect_os(self):
        """
        Detect the operating system running on the shell.
        Returns 'linux', 'darwin' (macOS), or 'unknown'.
        Result is cached after first detection.
        """
        if self._os_type is not None:
            return self._os_type
        
        try:
            result = self.execute_command("uname -s")
            if result and result.exit_code() == 0:
                os_name = str(result).strip().lower()
                if 'linux' in os_name:
                    self._os_type = 'linux'
                elif 'darwin' in os_name:
                    self._os_type = 'darwin'
                else:
                    self._os_type = 'unknown'
            else:
                self._os_type = 'unknown'
        except Exception:
            self._os_type = 'unknown'
        
        return self._os_type

    def get_permissions(self, path):
        """
        Get file permissions as an octal integer (e.g., 0o755).
        
        Returns:
            int: Permission bits (e.g., 0o755)
        """
        os_type = self._detect_os()
        
        if os_type == 'linux':
            stat_cmd = f"stat -c '%%a' '{path}'"
        elif os_type == 'darwin':
            stat_cmd = f"stat -f '%%A' '{path}'"
        else:
            raise RuntimeError("Unsupported OS type for permission detection")
        
        try:
            # TODO: raise exception if stat command fails (e.g., file does not exist)
            result = self.execute_command(stat_cmd)
            if result and result.exit_code() == 0:
                output = str(result).strip()
                if output.isdigit():
                    return int(output, 8)
        except Exception as e:
            raise RuntimeError(f"Failed to get permissions for '{path}': {str(e)}")

    def set_permissions(self, path, permissions):
        chmod = self.get_command("chmod", mandatory=True)
        self("%s %o '%s'" % (chmod, permissions, path))

    def do_pull(self, local_path, remote_path):
        raise NotImplementedError("this method must be implemented by the subclass")

    def do_push(self, local_path, remote_path):
        raise NotImplementedError("this method must be implemented by the subclass")

    def pull(self, local_path, remote_path):
        self.log_oob("'%s' <- '%s'" % (local_path, remote_path))
        self.do_pull(local_path, remote_path)
        chmod(local_path, self.get_permissions(remote_path))

    def push(self, local_path, remote_path):
        self.log_oob("'%s' -> '%s'" % (local_path, remote_path))
        self.do_push(local_path, remote_path)
        self.set_permissions(remote_path, (stat(local_path).st_mode & 0o777))


