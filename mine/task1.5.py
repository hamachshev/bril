import json
import sys


def run():
    program = json.load(sys.stdin)

    for func in range(len(program["functions"])):
        new_instrs = []
        function = program["functions"][func]
        for instr in function["instrs"].copy():
            if "op" in instr and instr["op"] == "jmp":
                new_instrs.append({"op": "print", "args": ["about to jmp!"]})
            new_instrs.append(instr)
        function["instrs"] = new_instrs

    for instr in program["functions"][0]["instrs"]:
        print(instr)


if __name__ == "__main__":
    run()
