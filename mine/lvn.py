import json
import sys
from collections import namedtuple

import dce
from mycfg import form_blocks

Value = namedtuple("Value", ["op", "args"])


def canonicalize(value):
    """
    cannonicalize mult and add instr to same key
    """
    if value.op in ("mult", "add"):
        value = Value(value.op, tuple(sorted(value.args)))
    return value


def lvn(block):
    env = {}  # mapping of vars to keys (of values) in lvn table
    lvn_table = (
        {}
    )  # table with cannonical home and key (tuple) for the value so key -> cannonical home

    for i, instr in enumerate(block):
        new_args = []
        if "args" in instr:
            const_expr = True
            for arg in instr["args"]:
                if arg not in env:
                    const_expr = False
                    new_args.append(arg)
                    continue
                key = env[arg]
                canonical = lvn_table[key]
                new_args.append(canonical)

            if (
                "dest" in instr and const_expr
            ):  # if all args are consts, then calc result
                # the value of the constand is in the key
                # of the variable in the env
                # bc the key is a Value(op="const", args[]) and the first arg is the value

                if instr["op"] == "add":
                    value = env[new_args[0]].args[0] + env[new_args[1]].args[0]
                elif instr["op"] == "sub":
                    value = env[new_args[0]].args[0] - env[new_args[1]].args[0]
                elif instr["op"] == "mul":
                    value = env[new_args[0]].args[0] * env[new_args[1]].args[0]
                elif instr["op"] == "div":
                    value = env[new_args[0]].args[0] / env[new_args[1]].args[0]
                else:
                    value = "shouldnt happen"  # should not happen

                block[i] = {
                    "op": "const",
                    "value": value,
                    "dest": instr["dest"],
                    "type": instr["type"],
                }
                continue

        elif "value" in instr:  # if this is a const instr
            new_args.append(instr["value"])

        if (
            "dest" in instr and instr["op"] != "call"
        ):  # ie if this is not an action instr and ignore calls
            # if not assigning to var then we are not adding ti to the table or replacing it

            key = canonicalize(Value(instr["op"], tuple(new_args)))

            # if seen value already and has cannonical home
            if key in lvn_table:
                env[instr["dest"]] = key  # add variable to env
                block[i] = {
                    "op": "id",
                    "args": [lvn_table[key]],
                    "dest": instr["dest"],
                }  # i dont think we need the id instr at all no bc were just going to point to the cannonical ?

                continue
            lvn_table[key] = instr["dest"]
            env[instr["dest"]] = key

        if "args" in instr:
            # rewrite using args in the table
            instr["args"] = new_args
            block[i] = instr


def run():
    program = json.load(sys.stdin)
    new_blocks = []

    for func in program["functions"]:
        for block in form_blocks(func["instrs"]):
            lvn(block)
            new_blocks.append(block)
        func["instrs"] = [line for block in new_blocks for line in block]
    dce.unused_vars(program)
    print(json.dumps(program))


if __name__ == "__main__":
    run()
