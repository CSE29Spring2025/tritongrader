from tritongrader.autograder import Autograder  # noqa
from tritongrader.formatter import GradescopeResultsFormatter
from tritongrader.test_case.io_test_case import IOTestCaseBulkLoader # noqa

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

    
    ag.io_tests_bulk_loader().add_list([("1", 2)])
    ag.execute()

    formatter = GradescopeResultsFormatter(
        src=ag,
        message="tritongrader valgrind test",
        hidden_tests_setting="after_published",
        html_diff=True,
    )

    formatter.export()
