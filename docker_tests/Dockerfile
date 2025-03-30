FROM gradescope/autograder-base:ubuntu-22.04

COPY ./grader/ /autograder/source/
COPY ./grader/run_autograder /autograder/

WORKDIR /autograder
RUN sh /autograder/source/setup.sh

ENTRYPOINT [ "/autograder/run_autograder" ]
