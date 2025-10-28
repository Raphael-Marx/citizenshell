class ShellError(RuntimeError):

    def __init__(self, command: str, problem: str):
        self._command = command        
        self._problem = problem
        super().__init__(f"'{command}' terminated with {problem}")

    def command(self):
        return self._command

    def exit_code(self):
        return self._problem
