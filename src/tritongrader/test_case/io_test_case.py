import os
import shutil
import logging
import subprocess

import traceback
from typing import Optional

from tritongrader.test_case.test_case_base import TestCaseBase, TestResultBase
from tritongrader.runner import CommandRunner
from tritongrader.valparse import valparse

logger = logging.getLogger("tritongrader.test_case.io_test_case")


class IOTestResult(TestResultBase):
    def __init__(self):
        super().__init__()
        self.exit_status: Optional[int] = None
        self.stderr: str = ""
        self.stdout: str = ""
        self.valparse_out: Optional[valparse.Parser] = None
        self.output_correct: bool = False


class IOTestCase(TestCaseBase):
    def __init__(
        self,
        command_path: str,
        input_path: str,
        exp_stdout_path: str,
        exp_stderr_path: str,
        exp_exit_status: Optional[int],
        name: str = "Test Case",
        point_value: float = 1,
        valgrind_point_value: float = 0,
        timeout: float = TestCaseBase.DEFAULT_TIMEOUT,
        student: bool = True,
        binary_io: bool = False,
        hidden: bool = False,
    ):
        """
        :param float timeout: Timeout in seconds.
        :param float valgrind_point_value: Points given in addition to `point_value`
            for having no memory problems. If set to 0, don't run Valgrind.
        """
        super().__init__(name, point_value + valgrind_point_value, timeout, hidden)

        self.student: bool = student
        self.binary_io: bool = binary_io

        self.command_path: str = command_path
        self.input_path: str = input_path if os.path.exists(input_path) else None
        self.exp_stdout_path: str = exp_stdout_path
        self.exp_stderr_path: str = exp_stderr_path
        self.exp_exit_status: Optional[int] = exp_exit_status

        self.point_value_correct_out = point_value
        self.point_value_valgrind = valgrind_point_value

        self.result: IOTestResult = IOTestResult()
        self.runner: CommandRunner = None

    def __str__(self):
        return (
            f"{self.name} student={self.student} cmd={self.command_path} " +
            f"input_path={self.input_path} exp_stdout_path={self.exp_stdout_path} exp_stderr_path={self.exp_stderr_path}"
        )

    @property
    def open_mode(self):
        return "r" if not self.binary_io else "rb"

    @property
    def expected_stdout(self):
        if not self.exp_stdout_path:
            return None
        with open(self.exp_stdout_path, self.open_mode) as fp:
            return fp.read()

    @property
    def expected_stderr(self):
        if not self.exp_stderr_path:
            return None
        with open(self.exp_stderr_path, self.open_mode) as fp:
            return fp.read()

    @property
    def actual_stdout(self) -> str:
        if not self.runner:
            raise Exception("no runner initialized")
        return self.runner.stdout

    @property
    def actual_stderr(self) -> str:
        if not self.runner:
            raise Exception("no runner initialized")
        return self.runner.stderr

    @property
    def test_input(self):
        if not self.input_path:
            return None

        # test input is passed in via command line ('<'), which
        # should always be text, so we don't use open_mode() here.
        with open(self.input_path, "r") as fp:
            return fp.read()

    def get_execute_command(self):
        logger.info(f"Running {str(self)}")
        exe = self.command_path
        with open(exe, "r") as script_file:
            exe = script_file.read().strip()

        if self.input_path:
            exe += f" < {self.input_path}"
        if self.point_value_valgrind > 0:
            exe = "valgrind --leak-check=full -s --track-origins=yes --xml=yes --xml-file=ValgrindResult.xml " + exe
        return exe

    def execute(self):
        # reset states
        self.result = IOTestResult()

        # run test case
        self.result.has_run = True
        try:
            self.runner = CommandRunner(
                command=self.get_execute_command(),
                capture_output=True,
                text=(not self.binary_io),
                timeout=self.timeout,
                print_command=True,
                student=self.student,
            )
            self.runner.run()

            stdout_check = self.runner.check_stdout(self.exp_stdout_path)
            stderr_check = self.runner.check_stderr(self.exp_stderr_path)
            valgrind_check = True if self.point_value_valgrind == 0 else self.check_valgrind_result()
            status = True
            if self.exp_exit_status is not None:
                status = self.exp_exit_status == self.runner.exit_status
            self.exit_status: int = self.runner.exit_status
            self.result.exit_status = self.exit_status
            self.result.output_correct = stdout_check and stderr_check and status
            self.result.passed = self.result.output_correct and valgrind_check
            self.result.score = 0
            if self.result.output_correct:
                self.result.score += self.point_value_correct_out
            if self.result.passed:
                self.result.score += self.point_value_valgrind

            print(
                f"stdout check: {stdout_check}; stderr check: {stderr_check}; status: {status}; " +
                (f"valgrind check: {valgrind_check}" if self.point_value_valgrind else "")
            )
        except subprocess.TimeoutExpired:
            logger.info(f"{self.name} timed out (limit={self.timeout}s)!")
            self.result.timed_out = True
            self.exit_status = None
        except OSError as err:
            logger.info(f"{self.name} caused OSError: {err}")
            self.result.crash = err
            self.exit_status = None
        except:
            traceback.print_exc()
            self.result.error = True
            self.exit_status = None

    def check_valgrind_result(self):
        try:
            self.result.valparse_out = valparse.Parser("ValgrindResult.xml")
            return not (self.result.valparse_out.hasErrors() or\
                    self.result.valparse_out.hasLeaks() or\
                    self.result.valparse_out.hasFatalSignal())
        except Exception as e:
            self.result.error = True
            print(e)
            return False


class IOTestCaseBulkLoader:
    def __init__(
        self,
        autograder,
        commands_path: Optional[str],
        test_input_path: Optional[str],
        expected_stdout_path: Optional[str],
        expected_stderr_path: Optional[str],
        expected_exit_status_path: Optional[str],
        commands_prefix: Optional[str] = "cmd-",
        test_input_prefix: Optional[str] = "in-",
        expected_stdout_prefix: Optional[str] = "out-",
        expected_stderr_prefix: Optional[str] = "err-",
        expected_exit_status_prefix: Optional[str] = "status-",
        prefix: str = "",
        default_timeout: float = 500,
        binary_io: bool = False,
    ):
        """
        - default_timeout: timeout in seconds.
        """
        self.autograder = autograder
        self.commands_path = commands_path
        self.test_input_path = test_input_path
        self.expected_stdout_path = expected_stdout_path
        self.expected_stderr_path = expected_stderr_path
        self.expected_exit_status_path: Optional[str] = expected_exit_status_path
        self.commands_prefix = commands_prefix
        self.test_input_prefix = test_input_prefix
        self.expected_stdout_prefix = expected_stdout_prefix
        self.expected_stderr_prefix = expected_stderr_prefix
        self.expected_exit_status_prefix: Optional[str] = expected_exit_status_prefix
        self.prefix = prefix
        self.default_timeout = default_timeout
        self.binary_io = binary_io

    def add(
        self,
        name: str,
        point_value: float = 1,
        valgrind_point_value: float = 0,
        hidden: bool = False,
        timeout: float = None,
        binary_io: bool = False,
        prefix: str = "",
        no_prefix: bool = False,
    ) -> "IOTestCaseBulkLoader":
        """
        - timeout: timeout in seconds.
        """
        if timeout is None:
            timeout = self.default_timeout

        cmd = os.path.join(self.commands_path, self.commands_prefix + name)
        stdin = os.path.join(self.test_input_path, self.test_input_prefix + name)
        stdout = os.path.join(
            self.expected_stdout_path, self.expected_stdout_prefix + name
        )
        stderr = os.path.join(
            self.expected_stderr_path, self.expected_stderr_prefix + name
        )
        if self.expected_exit_status_path is not None and self.expected_exit_status_prefix is not None:
            file = os.path.join(
                self.expected_exit_status_path, self.expected_exit_status_prefix + name
            )
            with open(file, "r") as fin:
                exit_status = int(fin.read().strip())
        else:
            exit_status = None

        test_name = name if no_prefix else self.prefix + prefix + name
        test_case = IOTestCase(
            name=f"{test_name}",
            point_value=point_value,
            valgrind_point_value=valgrind_point_value,
            command_path=cmd,
            input_path=stdin,
            exp_stdout_path=stdout,
            exp_stderr_path=stderr,
            exp_exit_status=exit_status,
            timeout=timeout,
            binary_io=binary_io,
            hidden=hidden,
            student=True,  # Bulk IO test cases always run as the student
        )

        self.autograder.add_test(test_case)

        return self

    def add_list(
        self,
        test_list: list[tuple[str, float] | tuple[str, float, float]],
        prefix: str = "",
        hidden: bool = False,
        timeout: float = None,
        binary_io: bool = False,
    ):
        for test in test_list:
            if len(test) == 2:
                self.add(test[0], test[1], 0, hidden, timeout, binary_io, prefix=prefix)
            elif len(test) == 3:
                self.add(test[0], test[1], test[2], hidden, timeout, binary_io, prefix=prefix)
            else:
                raise ValueError(test)

        return self
