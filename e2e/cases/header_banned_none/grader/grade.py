from tritongrader.autograder import Autograder  # noqa
from tritongrader.formatter import GradescopeResultsFormatter
from tritongrader.test_case import BasicTestCase  # noqa

if __name__ == "__main__":
    ag = Autograder(
        "Test Autograder",
        "/autograder/submission/",
        "/autograder/source/tests/",
        required_files=["submission.c"],
        source_files=["submission.c"],
        banned_includes={"string.h"},
        verbose_rubric=True,
        build_command="gcc -Wall -Werror -o submission submission.c",
    )

    ag.add_test(BasicTestCase("./submission"))

    ag.execute()

    formatter = GradescopeResultsFormatter(
        src=ag,
        message="tritongrader test",
        hidden_tests_setting="after_published",
        html_diff=True,
    )

    formatter.export()
