import json
import sys
from collections import OrderedDict

TERMINATORS = "jmp", "br", "ret"


def form_blocks(body):
    block = []
    for instr in body:
        if "op" in instr:
            block.append(instr)

            if instr["op"] in TERMINATORS:  # TERMINATOR
                yield block
                block = []

        else:  # a label
            if block:
                yield block
            block = [instr]

    if block:
        yield block


def name_block(blocks):
    out = OrderedDict()
    for block in blocks:
        if "label" in block[0]:
            name = block[0]["label"]
            block = block[1:]
        else:
            name = "b{}".format(len(out))
        out[name] = block

    return out


def get_cfg(block_map):
    out = {}

    for i, (name, block) in enumerate(block_map.items()):
        last = block[-1]
        if last["op"] in ("br", "jmp"):
            succ = last["labels"]
        elif last["op"] == "ret" or i == len(block_map) - 1:
            succ = []
        else:
            succ = [list(block_map.keys())[i + 1]]

        out[name] = succ
    return out


def run():
    program = json.load(sys.stdin)

    for func in program["functions"]:
        name2block = name_block(form_blocks(func["instrs"]))
        cfg = get_cfg(name2block)

        print(cfg)


if __name__ == "__main__":
    run()
