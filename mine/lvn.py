import json
import random
import sys
from collections import namedtuple

import dce
from mycfg import form_blocks

Value = namedtuple("Value", ["op", "args"])


def add_nonlocal(block, lvn_table, env):
    """
    we need if we use a non local var, like an arg,
    basically a var that has no decl in this block
    to be added to the lvn table and env
    so
    """

    seen = set()
    for instr in block:
        if "args" in instr:
            for arg in instr["args"]:
                if arg not in seen:
                    value = Value("id", (arg))
                    lvn_table[value] = arg
                    env[arg] = value
                    seen.add(arg)
        if "dest" in instr:
            seen.add(instr["dest"])


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
    abc = list("abcdefghijklmnopqrstuvwxyz")
    return "lvn.{}".format(random.choice(abc))


def fold(env, instr):
    """
    accepts expression with args (subbed with Values (key) when possible) and
    returns folded const if possible and
    if not None
    """

    BINARY_OPS = {
        "add": lambda a, b: a + b,
        "sub": lambda a, b: a - b,
        "mul": lambda a, b: a * b,
        "div": lambda a, b: a // b,
        # comparison operators
        "eq": lambda a, b: a == b,
        "lt": lambda a, b: a < b,
        "gt": lambda a, b: a > b,
        "le": lambda a, b: a <= b,
        "ge": lambda a, b: a >= b,
        # logical operators
        "and": lambda a, b: a and b,
        "or": lambda a, b: a or b,
    }

    UNARY_OPS = {
        "not": lambda a: not a,
    }
    args = instr["args"]

    if (
        "op" not in instr
        or (instr["op"] not in BINARY_OPS and instr["op"] not in UNARY_OPS)
        or len(args) not in (1, 2)
    ):
        return None

    for arg in args:
        if arg not in env or env[arg].op != "const":
            return None

    # the value of the constand is in the key
    # of the variable in the env
    # bc the key is a Value(op="const", args[]) and the first arg is the value

    if len(args) == 2:
        lhs, rhs = int(env[args[0]].args[0]), int(env[args[1]].args[0])

        value = BINARY_OPS[instr["op"]](lhs, rhs)
    else:
        operand = int(env[args[0]].args[0])
        value = UNARY_OPS[instr["op"]](operand)

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

    add_nonlocal(block, lvn_table, env)

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

        elif "value" in instr:  # if this is a const instr to add to key later
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

        # if not assigning to var (ie no dest)
        # then we are not adding ti to the table or replacing it
        if "dest" in instr:
            # we are rewriting this so must del old one in env
            # - import for call inst where we dont explicitly rewrite the env with new val
            # ie if d: int = call x
            # so we dont want to save call x in table, but
            # we also dont want d to point to whatever it was pointing to before
            # after this point
            if instr["dest"] in env:
                # if any saved key used this variable that is being reassigned,
                # must remove that key from the table so dont cache old value
                # based on old value of the variable argument
                # ie if  c-> mult a b
                # and were reassigning b, and later
                # there is f -> mult a b if we dont do this we will do f -> id c
                # but thats wrong bc c is using b from before and now b is updated
                del env[instr["dest"]]
                for key in list(lvn_table.keys()):
                    if instr["dest"] in key.args:
                        if lvn_table[key] in env:
                            del env[lvn_table[key]]
                            del lvn_table[key]

            # either save as canon or retrieve cannon
            if instr["op"] != "call":
                key = canonicalize(
                    Value(
                        instr["op"],
                        tuple(
                            str(a) if type(a) is bool else a for a in new_args
                        ),  # was converting True -> 1
                    )
                )

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
                        "type": instr["type"],
                    }
                    continue
                # otherwise, it is a new value, so add var to env
                # and value to lvn_table -> cannonical home

                # if this is the last write to this dest, then it is the cannonical home
                if last_write:
                    dest = instr["dest"]
                else:
                    # otherwise need to create new variable to store it in
                    new_dest = get_random_register()
                    while new_dest in env:
                        new_dest = get_random_register()
                    dest = new_dest
                    env[instr["dest"]] = key
                    instr["dest"] = dest

                # if instr["op"] == "id":
                #     # then cannonical home is id, ie we dont want this to be a canonical
                #     # home of id <x>, just in case x gets updated
                #     lvn_table[key] = instr["args"][0]
                # else:
                lvn_table[key] = dest

                env[instr["dest"]] = key
    return block


def run():
    program = json.load(sys.stdin)

    for func in program["functions"]:
        blocks = list(form_blocks(func["instrs"]))
        for block in blocks:
            lvn(block)
        func["instrs"] = [line for block in blocks for line in block]
    dce.unused_vars(program)
    print(json.dumps(program))


if __name__ == "__main__":
    run()
