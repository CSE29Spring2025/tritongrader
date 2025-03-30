from tritongrader.autograder import Autograder  # noqa
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
        arm=False,
    )
    
    failure_test = BasicTestCase(
        "./submission",
        name="Submission failure test",
        point_value=5,
        arm=False
    )
    ag.add_test(failure_test)
    ag.execute()

    assert failure_test.result.passed, (
        failure_test.result.stdout,
        failure_test.result.stderr
    )
