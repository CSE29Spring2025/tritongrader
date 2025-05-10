from tritongrader.autograder import Autograder  # noqa
from tritongrader.formatter import GradescopeResultsFormatter
from tritongrader.test_case.io_test_case import IOTestCase  # noqa

if __name__ == "__main__":
    ag = Autograder(
        "Valgrind Autograder Test",
        "/autograder/submission/",
        "/autograder/source/tests/",
        required_files=["submission.c"],
        source_files=["submission.c"],
        verbose_rubric=True,
        build_command="gcc -Wall -o submission submission.c",
    )

    ag.add_test(IOTestCase(
        "./submission",
        "/autograder/source/sample.in",
        "/autograder/source/sample.out",
        "/autograder/source/sample.err",
        0,
        valgrind_point_value=2,
    ))

    ag.execute()

    formatter = GradescopeResultsFormatter(
        src=ag,
        message="tritongrader valgrind test",
        hidden_tests_setting="after_published",
        diff_format="html",
    )

    formatter.export()
