"""Validate results.json against expectations."""

import json

with open("/autograder/results/results.json") as srcfile:
    results = json.load(srcfile)

print(results)
assert results["score"] == 1
assert results["tests"][2]["status"] == "failed"
assert results["tests"][2]["score"] == 1
assert results["tests"][2]["max_score"] == 3
assert "4 bytes in 1 blocks are definitely lost" in results["tests"][2]["output"]
print("\nResults matched expectations")