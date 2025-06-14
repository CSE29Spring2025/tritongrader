import logging
import subprocess
import traceback

from tritongrader.test_case.test_case_base import TestCaseBase, TestResultBase
from tritongrader.runner import CommandRunner

logger = logging.getLogger("tritongrader.test_case.basic_test_case")


class BasicTestResult(TestResultBase):
    def __init__(self):
        super().__init__()
        self.retcode: int = None
        self.stderr: str = ""
        self.stdout: str = ""


class BasicTestCase(TestCaseBase):
    """
    A basic test case executes a command and evaluates pass/fail
    based on the return value (retcode).
    """
    def __init__(
        self,
        command: str,
        name: str = "Test Case",
        point_value: float = 1,
        expected_retcode: int = 0,
        timeout: float = TestCaseBase.DEFAULT_TIMEOUT,
        student: bool = True,
        binary_io: bool = False,
        hidden: bool = False,
    ):
        """Create a basic test case.
        
        :param student: Whether the test should run as the "student" user.
        """
        super().__init__(name, point_value, timeout, hidden)

        self.student: bool = student
        self.binary_io: bool = binary_io

        self.command: str = command
        self.expected_retcode: int = expected_retcode

        self.result: BasicTestResult = BasicTestResult()
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
        self.result.passed = self.runner.exit_status == self.expected_retcode
        self.result.score = self.point_value if self.result.passed else 0

    def execute(self):
        self.result = BasicTestResult()

        try:
            self._execute()
        except subprocess.TimeoutExpired:
            logger.info(f"{self.name} timed out (limit={self.timeout}s)!")
            self.result.timed_out = True
        except OSError as err:
            logger.info(f"{self.name} caused OSError: {err}")
            self.result.crash = err
            self.exit_status = None
        except:
            traceback.print_exc()
            self.result.error = True
            self.exit_status = None