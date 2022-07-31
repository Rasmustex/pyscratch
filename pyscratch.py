import json as js
import sys
from enum import Enum

class OPCODE(Enum): # All of the scratch opcodes that are supported
    DEF_MAIN = 0
    DEF_PROC = 1
    CALL_PROC = 2
    SETVARIABLE = 3

class Block: # maybe do some of the value processing in the initialiser
    def __init__(self, oc: OPCODE, inputs: dict, prnt: str, nxt: str, fields: dict, scope_level: int):
        self.oc = oc
        self.inputs = inputs
        self.prnt = prnt
        self.nxt = nxt
        self.fields = fields
        self.scope_level = scope_level
    @staticmethod
    #TODO: Modify so builtin functions are supported, meaning we pass the entire block
    def get_opcode(op: str) -> OPCODE:
        match op:
            case "event_whenflagclicked":
                return OPCODE.DEF_MAIN
            case "data_setvariableto":
                return OPCODE.SETVARIABLE
            case "procedures_definition":
                return OPCODE.DEF_PROC
            case "procedures_call":
                return OPCODE.CALL_PROC
            case opcode:
                return None
                assert False,f'opcode {opcode} not implemented yet'

class ProcCall(Block): # include procedure name and stuff
    def __init__(self, oc: OPCODE, inputs: dict, prnt: str, nxt: str, fields: dict, scope_level: int, proccode: str):
        super().__init__(oc, inputs, prnt, nxt, fields, scope_level)
        self.proccode = proccode

class ProcProt(Block): # include procedure name and stuff
    def __init__(self, oc: OPCODE, inputs: dict, prnt: str, nxt: str, fields: dict, scope_level: int, argnames: list[str]):
        super().__init__(oc, inputs, prnt, nxt, fields, scope_level)
        self.argnames = argnames

def main():
    progname, fname = handle_args(sys.argv)
    program = parse_scratch_json(fname)
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

def parse_scratch_json(fname: str) -> dict:
    """
    Parses scratch project.json
    Input:
    fname: str - name of input file
    Output: dictionary of parsed project.json
    """
    f = open(fname, "r")
    program_string = f.read().split("],\"monitors")[0].split("{\"targets\":[")[1] # ew
    program = js.loads(program_string)
    f.close()
    return program

def translate_program(program: dict):
    """
    Translates parsed scratch JSON file to python
    """
    blocks = program["blocks"]
    procs = program_parse_blocks(blocks)
    variables = program_get_vars(program)

    for variable in variables:
        var_name = variable[0].replace(" ", "_") # maybe move replace to program_get_vars
        var_value = variable[1]
        print(var_name + " = " + variable[1])
    print()

    for proc_id in procs:
        proc = procs[proc_id]
        proc_name, entry_point = proc_id.split(" ")
        if proc_name != "main":
            argnames = proc[entry_point].argnames
            print("def " + proc_name + "(" + ''.join(c for c in argnames if c not in "[]\"") + "):") # TODO: prettier, check multiple function arguments
        else:
            print("def " + proc_name + "():") # TODO: function arguments

        for variable in variables:
            var_name = variable[0].replace(" ", "_")
            print("\tglobal " + var_name)

        print()
        current_id = proc[entry_point].nxt
        while current_id != None:
            current_block = proc[current_id]
            print(current_block.scope_level * "\t" + translate_block(blocks, current_block))
            current_id = current_block.nxt
        print()

    print()
    print('if __name__ == "__main__":')
    print("\tmain()")

def program_parse_blocks(blocks: dict) -> dict[dict]:
    proc_dict = {}
    main_defined = False

    for bkey in blocks:
        block = blocks[bkey]
        # get all root blocks
        if block["parent"] == None:
            opcode = Block.get_opcode(block["opcode"])
            # put together main function
            if opcode == OPCODE.DEF_MAIN:
                if main_defined:
                    eprint("Only one \"when flag clicked\" block can be used, as it's used as the entry point")
                else:
                    main, entry_point = assemble_proc(bkey, blocks, main = True)
                    identifier = "main " + entry_point
                    proc_dict[identifier] = main
                    main_defined = True
            # maybe procs are called by ID... in that case, we might have issues
            elif opcode == OPCODE.DEF_PROC:
                name = blocks[block["inputs"]["custom_block"][1]]["mutation"]["proccode"].split(" %")[0] # yikes. Gets procedure name
                if name.startswith("BUILTIN: "):
                    continue
                else:
                    proc, entry_point = assemble_proc(bkey, blocks)
                    identifier = name + " " + entry_point
                    proc_dict[identifier] = proc

    if not main_defined:
        eprint("No entry point defined. Please use a \"when flag clicked\" block to indicate the \"main function\" of your program")
        exit(1)
    else:
        return proc_dict

# maybe change so builtin gets an empty dict entry
def assemble_proc(bkey: str, blocks: dict, main: bool = False) -> (dict, str): # todo: procedure arguments
    proc = {}
    block = blocks[bkey]
    opcode = Block.get_opcode(block["opcode"])
    if not main:
        proc[bkey] = ProcProt(opcode, block["inputs"], block["parent"], block["next"], block["fields"], 1, blocks[block["inputs"]["custom_block"][1]]["mutation"]["argumentnames"])
    else:
        proc[bkey] = Block(None, None, None, block["next"], None, 0)

    entry_point = bkey
    ckey = block["next"]
    while ckey != None:
        cblock = blocks[ckey]
        copcode = Block.get_opcode(cblock["opcode"])

        match copcode:
            case OPCODE.CALL_PROC:
                proc[ckey] = ProcCall(copcode, cblock["inputs"], cblock["parent"], cblock["next"], cblock["fields"], 1, cblock["mutation"]["proccode"])
            case _:
                proc[ckey] = Block(copcode, cblock["inputs"], cblock["parent"], cblock["next"], cblock["fields"], 1)

        ckey = cblock["next"]

    return (proc, entry_point)

def program_get_vars(program: dict) -> list[(str, str)]:
    variables = program["variables"]
    var_list = []
    for varkey in variables:
        variable = variables[varkey]
        var_name = variable[0]
        var_val = str(variable[1])
        var_list.append((var_name, var_val))
    return var_list

# Should be changed to something more general, argument-wise, once more cases have been covered
def translate_block(blocks: dict, block: Block) -> str:
    match block.oc:
        case OPCODE.SETVARIABLE:
            operand = block.fields["VARIABLE"][0].replace(" ", "_")
            # Should be a smarter way to do this
            # Checks if value is provided by an arg_reporter block (as in value is passed through function)
            if len(block.inputs["VALUE"]) == 2:
                arg = str(block.inputs["VALUE"][-1][-1])
            else:
                # arg reporter sits here in the input field
                arg_reporter = blocks[block.inputs["VALUE"][1]]
                # arg reporter tells setvalue which variable it should be set to
                arg = arg_reporter["fields"]["VALUE"][0]
            return operand + " = " + arg
        case OPCODE.CALL_PROC:
            # get function name
            num_args = block.proccode.count("%")
            if num_args > 0:
                arg = block.inputs[list(block.inputs.keys())[0]][1][1]
            else:
                arg = ""
            if block.proccode.startswith("BUILTIN: "):
                name = block.proccode.split(" %")[0].split("BUILTIN: ")[1]
            else:
                name = block.proccode.split(" %")[0]
            return f"{name}({arg})"
        case opcode:
            assert False,f"opcode {opcode} not translatable (yet)"

def eprint(*args, **kwargs):
    print("[ERROR]: ", *args, file=sys.stderr, **kwargs)

def print_usage(name: str):
    print(name + ":", file=sys.stderr)
    print("Usage: python " + name + " [file]", file=sys.stderr)
    print("[file]: name of input scratch JSON file to be compiled", file=sys.stderr)

if __name__ == "__main__":
    main()
