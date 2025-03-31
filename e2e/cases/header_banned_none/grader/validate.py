"""Validate results.json against expectations."""

import json

with open("/autograder/results/results.json") as srcfile:
    results = json.load(srcfile)

print(results)
assert results["score"] == 1
assert results["tests"][2]["status"] == "passed"
assert results["tests"][3]["status"] == "passed"
print("\nResults matched expectations")