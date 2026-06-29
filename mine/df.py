import json
import sys
from collections import deque

from mycfg import form_blocks, get_cfg, name_block


def kill(ins, block):
    """
    return a set of all the var killed.
    takes in the incoming vars, and the block
    """
    out = set()
    for instr in block:
        if "dest" in instr:
            if instr["dest"] in ins:
                out.add(instr["dest"])
    return out


def gen(ins, block):
    """
    returns only new vars generated in the block
    """
    out = set()
    for instr in block:
        if "dest" in instr:
            if instr["dest"] not in ins:
                out.add(instr["dest"])
    return out


def run():
    program = json.load(sys.stdin)

    for func in program["functions"]:
        blocks = name_block(form_blocks(func["instrs"]))
        ins = {name: set() for name in blocks}
        outs = {name: set() for name in blocks}
        cfg = get_cfg(blocks)
        workbench = deque(list(blocks))

        while workbench:
            name = workbench.popleft()
            block = blocks[name]
            in_block = ins[name]
            out = gen(in_block, block) | (in_block - kill(in_block, block))
            outs[name] = out

            for succ in cfg[name]:
                old = ins[succ]
                ins[succ] = old | out
                if ins[succ] != old:
                    workbench.append(succ)
        print("ins", ins)
        print("outs", outs)


if __name__ == "__main__":
    run()
