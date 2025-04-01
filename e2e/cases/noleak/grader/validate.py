"""Validate results.json against expectations."""

import json

with open("/autograder/results/results.json") as srcfile:
    results = json.load(srcfile)

print(results)
assert results["score"] == 3
assert results["tests"][2]["status"] == "passed"
assert results["tests"][2]["score"] == 3
assert results["tests"][2]["max_score"] == 3
assert "valgrind errors" not in results["tests"][2]["output"]
print("\nResults matched expectations")