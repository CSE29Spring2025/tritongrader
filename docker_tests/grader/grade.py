import pprint
from tritongrader.autograder import Autograder  # noqa
from tritongrader.formatter import GradescopeResultsFormatter
from tritongrader.test_case import BasicTestCase  # noqa

if __name__ == "__main__":
    ag = Autograder(
        "Test Autograder",
        "/autograder/submission/",
        "/autograder/source/tests/",
        required_files=["submission.c"],
        verbose_rubric=True,
        build_command="gcc -Wall -Werror -o submission submission.c",
        compile_points=1,
    )
    
    failure_test = BasicTestCase(
        "./submission",
        name="Submission failure test",
        point_value=5,
        student=True,
    )
    ag.add_test(failure_test)
    ag.execute()
    
    formatter = GradescopeResultsFormatter(
        src=ag,
        message="tritongrader test",
        hidden_tests_setting="after_published",
        html_diff=True,
    )

    pprint.pprint(formatter.execute())

    assert failure_test.result.passed, (
        failure_test.result.stdout,
        failure_test.result.stderr
    )
