import json
import random
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


def last_writes(block):
    """
    returns a array the length of the block of booleans indicating
    if the instr is the last storage in the var, bc if so keep the
    name and if not then create a new var name for the cannonical home
    and add the old one for now into the env
    """
    out = [False] * len(block)
    _set = set()
    for i, instr in reversed(list(enumerate(block))):
        if "dest" in instr and instr["dest"] not in _set:
            out[i] = True
            _set.add(instr["dest"])
    return out


def get_random_register():
    """return random register letter"""
    abc = "abcdefghijklmnopqrstuvwxyz".split("")
    return random.choice(abc)


def fold(env, instr):
    """
    accepts expression with args (subbed with Values (key) when possible) and
    returns folded const if possible and
    if not None
    """
    if len(instr["args"]) != 2:
        return None
    args = instr["args"]

    for arg in args:
        if (
            arg not in env or env[arg].op != "const"
        ):  # dont really need to check for const - bc const has one arg but...
            return None

    # the value of the constand is in the key
    # of the variable in the env
    # bc the key is a Value(op="const", args[]) and the first arg is the value

    lhs, rhs = env[args[0]].args[0], env[args[1]].args[0]

    if instr["op"] == "add":
        value = lhs + rhs
    elif instr["op"] == "sub":
        value = lhs - rhs
    elif instr["op"] == "mul":
        value = lhs * rhs
    elif instr["op"] == "div":
        value = lhs // rhs
    else:
        value = "shouldnt happen"  # should not happen
    return value


def lvn(block):
    """
    apply lvn to a block.
    this includes constant folding
    subexpression elimination
    """
    env = {}  # mapping of vars to keys (of values) in lvn table
    lvn_table = (
        {}
    )  # table with cannonical home and key (tuple) for the value so key -> cannonical home

    for last_write, (i, instr) in zip(last_writes(block), enumerate(block)):
        new_args = []
        if "args" in instr:
            for arg in instr["args"]:
                if arg not in env:
                    new_args.append(arg)
                else:
                    key = env[arg]
                    canonical = lvn_table[key]
                    new_args.append(canonical)

        elif "value" in instr:  # if this is a const instr
            new_args.append(instr["value"])

        instr["args"] = new_args

        folded = fold(env, instr)
        if folded:
            block[i] = {
                "op": "const",
                "value": folded,
                "dest": instr["dest"],
                "type": instr["type"],
            }
            continue

        #  if this is not an action instr and ignore calls
        # if not assigning to var then we are not adding ti to the table or replacing it
        if "dest" in instr and instr["op"] != "call":
            key = canonicalize(Value(instr["op"], tuple(new_args)))

            # if seen value already and has cannonical home
            if key in lvn_table:
                env[instr["dest"]] = key  # add variable to env

                # i dont think we need the id instr at all no?
                # bc were just going to point to the cannonical ?
                # and then garbage collect these lines bc the dest
                # does not point to anything
                block[i] = {
                    "op": "id",
                    "args": [lvn_table[key]],
                    "dest": instr["dest"],
                }
                continue
            # otherwise, it is a new value, so add var to env
            # and value to lvn_table -> cannonical home

            # if this is the last write to this dest, then it is the cannonical home
            if last_write:
                dest = instr["dest"]
            else:
                # otherwise need to create new variable to store it in
                while new_dest in env:
                    new_dest = get_random_register()
                dest = new_dest

            lvn_table[key] = dest

            env[instr["dest"]] = key


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
