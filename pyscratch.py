import json as js
import sys
from enum import Enum

class OPCODE(Enum): # All of the scratch opcodes that are supported
    DEF_MAIN = 0
    SETVARIABLE = 1

class Block:
    def __init__(self, oc: OPCODE, inputs: dict, prnt: str, nxt: str, fields: dict):
        self.oc = oc
        self.inputs = inputs
        self.prnt = prnt
        self.nxt = nxt
        self.fields = fields
    @staticmethod
    #TODO: Modify so builtin functions are supported, meaning we pass the entire block
    def get_opcode(op: str) -> OPCODE:
        match op:
            case "event_whenflagclicked":
                return OPCODE.DEF_MAIN
            case "data_setvariableto":
                return OPCODE.SETVARIABLE
        #if block["opcode"] == "procedures_prototype":
        #    print(block["mutation"]["proccode"])

def main():
    progname, fname = handle_args(sys.argv)
    program = parse_scratch_file(fname)
    translate_program(program)

def handle_args(args: list[str]) -> (str, str):
    """
    Handles command line arguments
    Input: command line arguments: list[str]
    Output: tuple(progname, fname)
    progname: argv[0]
    fname: name of scratch project.json to be transpiled
    """
    progname = args.pop(0)
    if len(args) == 0:
        eprint("Not enough arguments. You have to at least provide a scratch JSON file")
        print_usage(progname)
        exit(1)
    fname = args.pop(0)
    if len(args) != 0:
        eprint("Argument(s) " + args + " not recognised")
        print_usage(progname)
        exit(1)
    return (progname, fname)

def parse_scratch_file(fname: str) -> dict:
    """
    Parses scratch project.json
    Input:
    fname: str - name of input file
    Output: dictionary of parsed project.json
    """
    f = open(fname, "r")
    program_string = f.read().split("],\"monitors")[0].split("{\"targets\":[")[1]
    program = js.loads(program_string)
    f.close()
    return program

def translate_program(program: dict):
    """
    Translates parsed scratch JSON file to python
    """
    output = []
    blocks = program["blocks"]
    block_dict = {}
    entry_point = ""
    for bkey in blocks:
        block = blocks[bkey]
        #if block["opcode"] == "procedures_prototype":
        #    print(block["mutation"]["proccode"])
        opcode = Block.get_opcode(block["opcode"])
        if opcode == OPCODE.DEF_MAIN:
            if entry_point == "":
                entry_point = bkey
            else:
                eprint("Only one \"when flag clicked\" block can be used, as it's used as the entry point")
                exit(1)
        if opcode != None:
            block_dict[bkey] = Block(opcode, block["inputs"], block["parent"], block["next"], block["fields"])
    if entry_point == "":
        eprint("No entry point defined. Please use a \"when flag clicked\" block to indicate the \"main function\" of your program")
        exit(1)
    variables = program_get_vars(program)

    for variable in variables:
        var_name = variable[0].replace(" ", "_")
        var_value = variable[1]
        print(var_name + " = " + variable[1])

    # TODO: Generalise functions
    print("\ndef main():")

    for variable in variables:
        var_name = variable[0].replace(" ", "_")
        print("\tglobal " + var_name)

    #### translate all the blocks ####
    current_id = block_dict[entry_point].nxt
    # TODO: indent levels/scopes
    while current_id != None:
        current_block = block_dict[current_id]
        print("\t" + translate_block(current_block))
        current_id = current_block.nxt

    print()
    print('if __name__ == "__main__":')
    print("\tmain()")

def program_get_vars(program: dict) -> list[(str, str)]:
    variables = program["variables"]
    var_list = []
    for varkey in variables:
        variable = variables[varkey]
        var_name = variable[0]
        var_val = str(variable[1])
        var_list.append((var_name, var_val))
    return var_list

def translate_block(block: Block) -> str:
    match block.oc:
        case OPCODE.SETVARIABLE:
            operand = block.fields["VARIABLE"][0].replace(" ", "_")
            new_value = str(block.inputs["VALUE"][1][1])
            return operand + " = " + new_value

def eprint(*args, **kwargs):
    print("[ERROR]: ", *args, file=sys.stderr, **kwargs)

def print_usage(name: str):
    print(name + ":", file=sys.stderr)
    print("Usage: python " + name + " [file]", file=sys.stderr)
    print("[file]: name of input scratch JSON file to be compiled", file=sys.stderr)

if __name__ == "__main__":
    main()
