"""Validate results.json against expectations."""

import json

with open("/autograder/results/results.json") as srcfile:
    results = json.load(srcfile)

print(results)
assert results["score"] == 2
assert results["tests"][2]["status"] == "passed"
assert results["tests"][2]["score"] == 2
assert results["tests"][2]["max_score"] == 2
assert "valgrind errors" not in results["tests"][2]["output"]
print("\nResults matched expectations")