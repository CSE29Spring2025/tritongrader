FROM gradescope/autograder-base:ubuntu-22.04

COPY ./grader/ /autograder/source/
COPY ./grader/run_autograder /autograder/

WORKDIR /autograder
RUN apt-get update
RUN bash /autograder/source/setup.sh
RUN apt-get clean

ENTRYPOINT [ "/autograder/run_autograder" ]
