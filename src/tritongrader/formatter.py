import json
import logging
import subprocess
from typing import Dict, Callable, List, Union, Iterable
from difflib import HtmlDiff
from tritongrader import Autograder

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

        if test.result.output_correct:
            lines += ["", test.expected_stdout]
        else:
            diff_proc = subprocess.Popen([
                "icdiff", "--head=1000", "-W", "--cols=120", "--color-map=line-numbers:cyan",
                "-L", "Your output (stdout)", "-L", "Expected output (stdout)",
                test.runner.stdout_tf, test.exp_stdout_path,
            ], stdout=subprocess.PIPE, shell=False)

            diff_proc_2 = subprocess.Popen([
                "icdiff", "--head=1000", "-W", "--cols=120", "--color-map=line-numbers:cyan",
                "-L", "Your output (stderr)", "-L", "Expected output (stderr)",
                test.runner.stderr_tf, test.exp_stderr_path,
            ], stdout=subprocess.PIPE, shell=False)

            try:
                diff_proc.wait(timeout=2)
            except Exception as e:
                print("icdiff crashed!")
                print(e)
                return self.basic_io_output(test)
            lines += [diff_proc.stdout.read().decode()]

            try:
                diff_proc_2.wait(timeout=2)
            except Exception as e:
                print("icdiff crashed!")
                print(e)
                return self.basic_io_output(test)
            lines += [diff_proc_2.stdout.read().decode()]

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
