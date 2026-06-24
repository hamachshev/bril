import json
import sys


def run():
    program = json.load(sys.stdin)
    for function in program["functions"]:
        print(function["name"])


if __name__ == "__main__":
    run()
