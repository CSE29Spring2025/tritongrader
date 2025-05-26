import json
import logging
import os
import shlex
import subprocess
from typing import Dict, Callable, List, Optional, Union, Iterable
from difflib import HtmlDiff
from tritongrader import Autograder

from tritongrader.runner import CommandRunner
from tritongrader.test_case import TestCaseBase
from tritongrader.test_case import IOTestCase
from tritongrader.test_case import BasicTestCase
from tritongrader.test_case import CustomTestCase
from tritongrader.test_case.static_analysis_test_case import HeaderCheckTestCase, StaticAnalysisTestCase

logger = logging.getLogger("tritongrader.formatter")


class ResultsFormatterBase:
    def __init__(self, src: Union[Autograder, Iterable[Autograder]]):
        self.formatters: Dict[TestCaseBase, Callable[[TestCaseBase], None]] = {
            IOTestCase: self.format_io_test,
            BasicTestCase: self.format_basic_test,
            StaticAnalysisTestCase: self.format_static_analysis,
            HeaderCheckTestCase: self.format_static_analysis,  # TODO make more specific
            CustomTestCase: self.format_custom_test,
        }
        self.test_cases: List[TestCaseBase] = []
        ags = [src] if isinstance(src, Autograder) else src
        for autograder in ags:
            self.test_cases.extend(autograder.test_cases)

    def format_io_test(self, test: IOTestCase):
        raise NotImplementedError()

    def format_basic_test(self, test: BasicTestCase):
        raise NotImplementedError()

    def format_static_analysis(self, test: StaticAnalysisTestCase):
        raise NotImplementedError()

    def format_custom_test(self, test: CustomTestCase):
        raise NotImplementedError()

    def format_test(self, test: TestCaseBase):
        return self.formatters[type(test)](test)

    def execute(self):
        raise NotImplementedError


class AnsiDiff:
    """A helpful and robust display of file diffs using ANSI colors.
    
    Features:
    - display of whitespace differences
    - handling large files
    - handling invalid UTF-8
    """

    def __init__(self, expected_path: str, actual_path: str):
        self.stdout_truncated = self._truncate_if_needed(actual_path)
        self.whitespace_shown = False
        if self._should_visualize_whitespace(expected_path, actual_path):
            self.whitespace_shown = True
            self._visualize_whitespace(expected_path)
            self._visualize_whitespace(actual_path)
        self.expected = expected_path
        self.actual = actual_path

    def _truncate_if_needed(self, filepath: str) -> bool:
        """Truncate an output file as needed to ensure
        that the file fits in memory."""
        num_bytes = os.path.getsize(filepath)
        if num_bytes > 80000:
            logger.info("The output file %s is too big (%d bytes). It will be truncated.",
                        filepath, num_bytes)
            with open(filepath, 'rb') as read_fp:
                content = read_fp.read(80000)
            with open(filepath, 'wb') as write_fp:
                write_fp.write(content)
            del content
            return True
        return False

    def _should_visualize_whitespace(self,
                                    expected_path: str,
                                    actual_path: str) -> bool:
        """Determine if two files only differ in whitespace (or non-printable characters)."""
        contract = lambda line: "".join(
            ch for ch in line if ch.isprintable() and not ch.isspace()
        )
        with open(expected_path, 'rb') as exp:
            with open(actual_path, 'rb') as actual:
                diffs_found = False
                while True:
                    exp_line = exp.readline().decode(errors="ignore")
                    act_line = actual.readline().decode(errors="ignore")
                    if not exp_line and not act_line:
                        # reached EOF both sides
                        return diffs_found
                    exp_line_shown = contract(exp_line)
                    act_line_shown = contract(act_line)
                    if exp_line_shown != act_line_shown:
                        return False
                    if exp_line != act_line:
                        diffs_found = True

    def _visualize_whitespace(self, fp: str):
        path = shlex.quote(fp)
        altpath = shlex.quote(fp + ".tmp")
        os.system(f"batcat -A {path} > {altpath}")
        os.system(f"mv {altpath} {path}")

    def render_diff(self, label: str = "stdout") -> str:
        messages = []
        if self.whitespace_shown:
            messages.append("whitespace and non-printable characters have been visualized in this output to highlight their differences.")
        if self.stdout_truncated:
            messages.append("stdout is truncated because it is too large. You may have an infinite loop.")

        if self.stdout_truncated:
            # infinite loop should be evident from the actual output. No need to diff.
            # (icdiff takes too long for big files)
            pr_proc = subprocess.Popen([
                "pr", "-m", "-t", self.actual, self.expected
            ], stdout=subprocess.PIPE)
            try:
                pr_proc.wait(timeout=20)
            except Exception as e:
                print(e)
                raise e
            diff_output = ""
            for i in range(1000):
                b = pr_proc.stdout.readline()
                if len(b) == 0:
                    break
                diff_output += b.decode(errors="ignore")
        else:
            diff_proc = subprocess.Popen([
                "icdiff", "--head=1000", "-W", "--cols=120",
                "-L", f"Your output ({label})", "-L", f"Expected output ({label})",
                self.actual, self.expected,
            ], stdout=subprocess.PIPE, shell=False)
            try:
                diff_proc.wait(timeout=30)
            except Exception as e:
                print(e)
                raise e
            diff_output = diff_proc.stdout.read().decode(errors="ignore")

        if messages:
            return "\n".join("⚠️ " + msg for msg in messages) + "\n\n" + diff_output
        return diff_output

class GradescopeResultsFormatter(ResultsFormatterBase):
    def __init__(
        self,
        src: Union[Autograder, Iterable[Autograder]],
        message: str = "",
        visibility: str = "visible",
        stdout_visibility: str = "hidden",
        hidden_tests_setting: str = "hidden",
        hide_points: bool = False,
        max_output_bytes: int = 5000,
        verbose: bool = True,
        diff_format: str = "plain", # or "color" or "html"
    ):
        super().__init__(src)
        self.message = message
        self.visibility: str = visibility
        self.stdout_visibility: str = stdout_visibility
        self.hidden_tests_setting: str = hidden_tests_setting
        self.hide_points: bool = hide_points
        self.max_output_bytes: int = max_output_bytes
        self.verbose: bool = verbose
        self.diff_format = diff_format
        self.results: dict = None

    def html_diff_make_table(
        self,
        fromtext: str,
        totext: str,
        fromdesc: str = "",
        todesc: str = "",
    ):
        return HtmlDiff(tabsize=2, wrapcolumn=80).make_table(
            fromlines=fromtext.split("\n"),
            tolines=totext.split("\n"),
            fromdesc=fromdesc,
            todesc=todesc,
            context=False,
        ) + """<style>tbody > tr:nth-child(n+2) > .diff_next:has(a) ~ td ~ td {
            font-weight: 800;
            background-color: #cfcfcf;
        }
        .diff_header {
            padding-right: 4px;
            color: #444444 !important;
            border-right: 1px solid #444444 !important;
        }
        .diff tr td:nth-child(3n) {
            padding-left: 4px;
        }</style>"""

    def generate_html_diff(self, test: IOTestCase):
        if not test.result.has_run or not test.runner:
            return "<i>This test was not run.</i>"
        elif test.result.timed_out:
            return f"<i>Test case timed out with limit = {test.timeout}.</i>"

        stdout_diff = self.html_diff_make_table(
            fromtext=test.actual_stdout or "",
            totext=test.expected_stdout or "",
            fromdesc="Your stdout",
            todesc="Expected stdout",
        )
        stderr_diff = self.html_diff_make_table(
            fromtext=test.actual_stderr or "",
            totext=test.expected_stderr or "",
            fromdesc="Your stderr",
            todesc="Expected stderr",
        )
        valgrind_html = ""
        if test.result.valparse_out:
            val = test.result.valparse_out
            errors = val.errs + val.leaks
            if errors:
                valgrind_html += "<h2>valgrind errors/leaks</h2><ul>"
                for err in errors:
                    valgrind_html += f"<li><pre>{str(err)}</pre></li>"
                valgrind_html += "</ul>"

        html = "".join(
            [
                "<div>",
                "<h2>exit status</h2>",
                str(test.runner.exit_status),
                "<hr>",
                "<h2>stdout</h2>",
                stdout_diff,
                "<hr>",
                "<h2>stderr</h2>",
                stderr_diff,
                valgrind_html,
                "</div>",
            ]
        )
        return html

    def generate_ansi_diff(self, test: IOTestCase):
        lines = []
        if not test.result.has_run or not test.runner:
            return "This test was not run."
        elif test.result.timed_out:
            lines.append("Test case timed out with limit = {test.timeout}.")
            lines.append("")
        
        lines.append("Test status: " + self._test_status(test))
        lines.append("")

        if test.test_input is not None:
            lines.extend(["=== TEST INPUT ===", test.test_input, ""])

        if test.result.output_correct:
            lines += ["", "=== TEST OUTPUT ===", test.expected_stdout]
        else:
            stdout_diff = AnsiDiff(test.exp_stdout_path, test.runner.stdout_tf)
            stderr_diff = AnsiDiff(test.exp_stderr_path, test.runner.stderr_tf)
            try:
                lines.append(stdout_diff.render_diff(label="stdout"))
                lines.append(stderr_diff.render_diff(label="stderr"))
            except Exception as e:
                return self.basic_io_output(test)

        if test.exp_exit_status != test.exit_status:
             lines.append("")
             lines.append(f"Expected exit status of {test.exp_exit_status}, "
                          f"but your exit status was {test.exit_status}.")

        if test.result.valparse_out:
            lines.append("")
            lines.append("=== VALGRIND ===")
            lines.append("valgrind errors:")
            lines.extend(map(str, test.result.valparse_out.errs))
            lines.append("valgrind leaks:")
            lines.extend(map(str, test.result.valparse_out.leaks))
            if test.result.valparse_out.hasFatalSignal():
                lines.append("valgrind fatal signal:")
                lines.append(str(test.result.valparse_out.signal))

        return "\n".join(lines)

    def _test_status(self, test: IOTestCase) -> str:
        """Summarize the status of the test (passed? failed? passed with memory errors?)"""
        if test.result.valparse_out is None:
            return "PASSED" if test.result.passed else "FAILED"
        elif not test.result.output_correct:
            return "FAILED"
        elif test.result.valparse_out.hasErrors() or\
              test.result.valparse_out.hasLeaks() or\
              test.result.valparse_out.hasFatalSignal():
            return "FAILED (output correct, but memory errors detected)"
        else:
            return "PASSED"

    def basic_io_output(self, test: IOTestCase):
        if not test.result.has_run or not test.runner:
            return "This test was not run."

        if test.result.error:
            return "\n".join(
                [
                    "=== Unexpected autograder runtime error!  Please notify your instructors. ===",
                    "=== stdout ===",
                    test.actual_stdout,
                    "=== stderr ===",
                    test.actual_stderr,
                ]
            )
        if test.result.timed_out:
            return "\n".join(
                [
                    f"Test case timed out with limit = {test.timeout}.",
                    "== stdout ==",
                    test.actual_stdout,
                    "== stderr ==",
                    test.actual_stderr,
                ]
            )

        status_str = self._test_status(test)

        summary = []
        summary.append(f"{status_str} in {test.runner.running_time:.2f} ms.")

        if self.verbose:
            summary.extend(["=== test command ===", test.command_path])

            if test.test_input is not None:
                summary.extend(["=== test input ===", test.test_input])
            summary.extend(
                [
                    "=== expected stdout ===",
                    test.expected_stdout,
                    "=== expected stderr ===",
                    test.expected_stderr,
                    "=== expected exit status ===",
                    str(test.exp_exit_status),
                ]
            )
            if not test.result.passed:
                summary.extend(
                    [
                        "=== your stdout ===",
                        test.actual_stdout,
                        "=== your stderr ===",
                        test.actual_stderr,
                        "=== your exit status ===",
                        str(test.exit_status),
                    ]
                )
                if test.result.valparse_out:
                    summary.append("=== valgrind ===")
                    summary.append("valgrind errors:")
                    summary.extend(map(str, test.result.valparse_out.errs))
                    summary.append("valgrind leaks:")
                    summary.extend(map(str, test.result.valparse_out.leaks))
                    if test.result.valparse_out.hasFatalSignal():
                        summary.append("valgrind fatal signal:")
                        summary.append(str(test.result.valparse_out.signal))

        return "\n".join(summary)

    def format_io_test(self, test: IOTestCase):
        if self.diff_format == "plain":
            generated = self.basic_io_output(test)
        elif self.diff_format == "ansi":
            generated = self.generate_ansi_diff(test)
        elif self.diff_format == "html":
            generated = self.generate_html_diff(test)

        output_format = {
            "plain": "simple_format",
            "ansi": "ansi",
            "html": "html",
        }

        return {
            "output_format": output_format[self.diff_format],
            "output": generated
        }

    def format_basic_test(self, test: BasicTestCase):
        if not test.runner:
            return {
                "output": "This test was not run."
            }
        summary = []
        summary.extend(
            [
                "=== test command ===",
                test.command,
                "=== exit status ===",
                str(test.runner.exit_status),
            ]
        )
        if self.verbose:
            summary.extend(
                [
                    "=== stdout ===",
                    test.runner.stdout,
                    "=== stderr ===",
                    test.runner.stderr,
                ]
            )
        return {
            "output": "\n".join(summary)
        }

    def format_static_analysis(self, test: StaticAnalysisTestCase):
        if not test.result.has_run:
            return {
                "output": "This test was not run."
            }
        summary = []
        if test.result.passed:
            summary.append("Test passed!")
        elif test.result.error:
            summary.extend([
                "Test ERRORED",
                "=== stderr ===",
                test.result.stderr,
                "",
                f"Return code: {test.result.retcode}",
            ])
        else:
            summary.extend([
                "Test FAILED",
                test.result.evaluation_error.args[0]
                    if test.result.evaluation_error else test.result.stderr,
            ])
        return {
            "output": "\n".join(summary)
        }

    def format_custom_test(self, test: CustomTestCase):
        if not test.result.has_run:
            output = "This test was not run."
        else:
            output = test.result.output

        return {
            "output": output
        }

    def format_test(self, test: TestCaseBase):
        item = {
            "name": test.name,
            "visibility": "visible" if not test.hidden else self.hidden_tests_setting,
        }
        if not self.hide_points:
            item["score"] = test.result.score
        if test.point_value is not None:
            item["max_score"] = test.point_value
        if test.result.passed is not None:
            item["status"] = "passed" if test.result.passed else "failed"

        item.update(super().format_test(test))
        return item

    def get_total_score(self):
        return sum(i.result.score for i in self.test_cases)

    def execute(self):
        logger.info("Formatter running...")
        self.results = {
            "output": self.message,
            "visibility": self.visibility,
            "stdout_visibility": self.stdout_visibility,
            "score": self.get_total_score(),
            "tests": [self.format_test(i) for i in self.test_cases],
        }

        if self.hide_points:
            self.results["score"] = 0
        logger.info("Formatter execution completed.")
        return self.results

    def export(self, path="/autograder/results/results.json"):
        with open(path, "w+") as fp:
            json.dump(self.execute(), fp)


if __name__ == "__main__":
    formatter = GradescopeResultsFormatter()
    formatter.formatters[IOTestCase](None)
