"""Validate results.json against expectations."""

import json

with open("/autograder/results/results.json") as srcfile:
    results = json.load(srcfile)

print(results)
assert results["score"] == 0
assert results["tests"][2]["status"] != "passed"
assert results["tests"][3]["output"] == "This test was not run."
print("\nResults matched expectations")