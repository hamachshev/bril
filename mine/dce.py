import json
import sys

from mycfg import form_blocks


def unused_vars(program):
    """
    loop until have not changed
    on each loop get all the used vars
    and then loop thru all the const statements and
    if not used, remove the const statement
    """

    while True:
        used_vars = set()
        changed = False
        # used var pass
        for func in program["functions"]:
            for instr in func["instrs"]:
                if "args" in instr:
                    for arg in instr["args"]:
                        used_vars.add(arg)

        # shake the unused vars

        for func in program["functions"]:
            new_instrs = []

            for instr in func["instrs"]:
                if "dest" in instr and instr["dest"] not in used_vars:
                    changed = True
                    continue
                new_instrs.append(instr)
            func["instrs"] = new_instrs

        if not changed:
            break


def reassigned_before_use(block):
    """
    takes a block and adds on every dest call
    to a last_assign
    if the arg of the instr is in last assign, remove it bc its used
    if we get to another of the same dest, before its removed from last assn
    then remove old instr by rewriting it in the new array and return the new array
    """
    new = []
    last_assign = {}

    for i, instr in enumerate(block):
        if "args" in instr:
            for arg in instr["args"]:
                if arg in last_assign:
                    del last_assign[arg]

        if "dest" in instr:
            if instr["dest"] in last_assign:  # ie its being reassinged
                new[last_assign[instr["dest"]]] = instr
                last_assign[instr["dest"]] = i
                continue
            last_assign[instr["dest"]] = i
        new.append(instr)
    return new


def run():
    program = json.load(sys.stdin)
    unused_vars(program)
    for func in program["functions"]:
        blocks = list(form_blocks(func["instrs"]))
        for i, block in enumerate(blocks):
            new_block = reassigned_before_use(block)
            blocks[i] = new_block
        new_instr = []
        for block in blocks:
            for instr in block:
                new_instr.append(instr)
        func["instrs"] = new_instr
    print(json.dumps(program))


if __name__ == "__main__":
    run()
