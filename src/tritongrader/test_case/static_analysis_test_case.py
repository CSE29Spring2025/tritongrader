import logging
import subprocess
from typing import Callable, Optional

from tritongrader.test_case.test_case_base import TestCaseBase, TestResultBase
from tritongrader.runner import CommandRunner

logger = logging.getLogger("tritongrader.test_case.static_analysis_test_case")


class StaticAnalysisTestResult(TestResultBase):
    def __init__(self):
        super().__init__()
        self.retcode: int = None
        self.stderr: str = ""
        self.stdout: str = ""
        self.evaluation_error: Optional[Exception] = None


class StaticAnalysisTestCase(TestCaseBase):
    """
    A static analysis test case executes a command (that runs a static analysis tool)
    and passes the stdout output through a custom function to determine if the
    test case has passed.
    """
    def __init__(
        self,
        command: str,
        evaluator: Callable[[str], None],
        name: str = "Code Analysis",
        point_value: float = 0,
        timeout: float = TestCaseBase.DEFAULT_TIMEOUT,
        student: bool = True,
        hidden: bool = False,
    ):
        """Create a static analysis test case.
        
        :param evaluator: A function that evaluates the stdout output of the
            command. If the test has failed, it should raise an exception.
        :param student: Whether the test should run as the "student" user.
        """
        super().__init__(name, point_value, timeout, hidden)

        self.student: bool = student
        self.command: str = command

        self.result: StaticAnalysisTestResult = StaticAnalysisTestResult()
        self.evaluator = evaluator
        self.runner: CommandRunner = None

    def _execute(self):
        self.result.has_run = True
        self.runner = CommandRunner(
            command=self.command,
            capture_output=True,
            timeout=self.timeout,
            student=self.student,
        )
        self.runner.run()
        if self.runner.exit_status != 0:
            self.result.passed = False
            self.result.error = True
        self.result.retcode = self.runner.exit_status
        self.result.running_time = self.runner.running_time
        self.result.stderr = self.runner.stderr
        try:
            self.evaluator(self.result.stdout)
            self.result.passed = True
            self.result.error = False
        except Exception as failure:
            self.result.passed = False
            self.result.stderr = str(failure.args)

    def execute(self):
        self.result = StaticAnalysisTestResult()

        try:
            self._execute()
        except subprocess.TimeoutExpired:
            logger.info(f"{self.name} timed out (limit={self.timeout}s)!")
            self.result.timed_out = True

class HeaderCheckTestCase(StaticAnalysisTestCase):
    """A specialization of a static analysis test case that checks whether
    disallowed headers have been included.
    """
    LIST_DEPS_PREFIX = "gcc -M "

    def __init__(self, source_files: list[str], prohibited_headers: set[str]):
        assert source_files, "HeaderCheck is checking no files!"
        self.prohibited_headers = prohibited_headers

        super().__init__(
            f"{HeaderCheckTestCase.LIST_DEPS_PREFIX} {' '.join(source_files)}",
            self._evaluate,
            name="Check included headers",
            point_value=0,
            hidden=False
        )

    def _evaluate(self, gcc_stdout: str):
        for header in self.prohibited_headers:
            if f"/usr/include/{header}" in gcc_stdout:
                raise ValueError(f"You have included {header}, which is not allowed for this assignment.")