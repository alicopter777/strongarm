# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
from __future__ import print_function

from typing import Text, List, Optional, Dict, Tuple
from enum import Enum

from capstone.arm64 import ARM64_OP_REG, ARM64_OP_IMM, ARM64_OP_MEM
from capstone import CsInsn

from strongarm.debug_util import DebugUtil
from strongarm.macho import MachoBinary
from .objc_instruction import ObjcInstruction, ObjcBranchInstruction
from .objc_query import \
    CodeSearch, \
    CodeSearchTermInstructionMnemonic, \
    CodeSearchTermInstructionOperand, \
    CodeSearchTermInstructionIndex


class RegisterContentsType(Enum):
    FUNCTION_ARG = 0
    IMMEDIATE = 1


class RegisterContents(object):
    def __init__(self, value_type, value):
        self.type = value_type
        self.value = value


class ObjcFunctionAnalyzer(object):
    """Provides utility functions for introspecting on a set of instructions which represent a function body.
    As Objective-C is a strict superset of C, ObjcFunctionAnalyzer can also be used on pure C functions.
    """

    def __init__(self, binary, instructions):
        # type: (MachoBinary, List[CsInsn]) -> None
        from strongarm.macho import MachoAnalyzer
        try:
            self.start_address = instructions[0].address
            last_instruction = instructions[len(instructions) - 1]
            self.end_address = last_instruction.address
        except IndexError as e:
            # this method must have just been a stub with no real instructions!
            self.start_address = 0
            self.end_address = 0
            pass

        self.binary = binary
        self.macho_analyzer = MachoAnalyzer.get_analyzer(binary)
        self.instructions = instructions

        self._call_targets = None

    def debug_print(self, idx, output):
        # type: (int, Text) -> None
        """Helper function to pretty-print debug logs

        Args:
            idx: instruction offset within function the message references
            output: string to output to debug log
        """
        if not len(self.instructions):
            DebugUtil.log(self, 'func(stub) {}'.format(
                output
            ))
        else:
            func_base = self.start_address
            # each instruction is 4 bytes
            instruction_size = 4
            instruction_address = func_base + (idx * instruction_size)
            DebugUtil.log(self, 'func({}) {}'.format(
                hex(int(instruction_address)),
                output
            ))

    @classmethod
    def get_function_analyzer(cls, binary, start_address):
        # type: (MachoBinary, int) -> ObjcFunctionAnalyzer
        """Get the shared analyzer for the function at start_address in the binary.

        This method uses a cached MachoAnalyzer if available, which is more efficient than analyzing the
        same binary over and over. Therefore, this method should be used when an ObjcFunctionAnalyzer is needed,
        instead of constructing it yourself.

        Args:
            binary: The MachoBinary containing a function at start_address
            start_address: The entry point address for the function to be analyzed

        Returns:
            An ObjcFunctionAnalyzer suitable for introspecting a block of code.
        """
        from strongarm.macho.macho_analyzer import MachoAnalyzer
        analyzer = MachoAnalyzer.get_analyzer(binary)
        instructions = analyzer.get_function_instructions(start_address)
        return ObjcFunctionAnalyzer(binary, instructions)

    @property
    def call_targets(self):
        # type: () -> List[ObjcBranchInstruction]
        """Find a List of all branch destinations reachable from the source function

        Returns:
            A list of objects encapsulating info about the branch destinations from self.instructions
        """
        # use cached list if available
        if self._call_targets is not None:
            return self._call_targets

        targets = []
        # keep track of the index of the last branch destination we saw
        last_branch_idx = 0

        while True:
            # grab the next branch in front of the last one we visited
            # TODO(PT): this should use a mnemonic and instruction index search predicate
            next_branch = self.next_branch_after_instruction_index(last_branch_idx)
            if not next_branch:
                # parsed every branch in this function
                break

            targets.append(next_branch)
            # record that we checked this branch
            last_branch_idx = self.instructions.index(next_branch.raw_instr)
            # add 1 to last branch so on the next loop iteration,
            # we start searching for branches following this instruction which is known to have a branch
            last_branch_idx += 1

        self._call_targets = targets
        return targets

    def search_code(self, code_search):
        # type: (CodeSearch) -> List[CodeSearchResult]
        """Given a CodeSearch object describing rules for matching code, return a List of CodeSearchResult's
        encapsulating instructions which match the described set of conditions.
        """
        from .objc_query import CodeSearch, CodeSearchResult
        minimum_index = 0
        maximum_index = len(self.instructions)
        step = 1

        search_results = []
        for instruction in self.instructions[minimum_index:maximum_index:step]:
            has_any_condition_failed = False
            for search_term in code_search.required_matches:
                if isinstance(search_term, CodeSearchTermInstructionIndex):
                    # this term is where minimum_index, maximum_index, step, comes from, along w/ search_backwards flag
                    raise NotImplementedError()

                if search_term.satisfied(self, instruction):
                    if not code_search.requires_all_terms_matched:
                        # matched a single term which is sufficient for storing a result
                        wrapped_instruction = ObjcInstruction.parse_instruction(self, instruction)
                        result = CodeSearchResult(search_term, self, wrapped_instruction)
                        search_results.append(result)
                else:
                    has_any_condition_failed = True
                    if code_search.requires_all_terms_matched:
                        break
            if code_search.requires_all_terms_matched and not has_any_condition_failed:
                # matched all terms
                wrapped_instruction = ObjcInstruction.parse_instruction(self, instruction)
                result = CodeSearchResult(code_search.required_matches, self, wrapped_instruction)
                search_results.append(result)
        return search_results

    def get_local_branches(self):
        # type: () -> List[ObjcBranchInstruction]
        """Return all instructions in the analyzed function representing a branch to a destination within the function
        """
        local_branches = []
        for target in self.call_targets:
            # find the address of this branch instruction within the function
            if self.is_local_branch(target):
                local_branches.append(target)
        return local_branches

    def can_execute_call(self, call_address):
        # type: (int) -> bool
        """Determine whether the function starting at call_address is reachable from any code path from source function.

        Args:
            call_address: address of the entry point of function to search for

        Returns:
            True if any of the code paths originating from the source function invoke the function at call_address.
            False if no code paths call that function.
        """
        self.debug_print(0, 'recursively searching for invocation of {}'.format(hex(int(call_address))))

        for target in self.call_targets:
            # find the address of this branch instruction within the function
            instr_idx = self.instructions.index(target.raw_instr)

            # is this a direct call?
            if target.destination_address == call_address:
                self.debug_print(instr_idx, 'found call to {} at {}'.format(
                    hex(int(call_address)),
                    hex(int(target.address))
                ))
                return True

            # don't try to follow this path if it's an external symbol and not an objc_msgSend call
            if target.is_external_c_call and not target.is_msgSend_call:
                self.debug_print(instr_idx, '{}(...)'.format(
                    target.symbol
                ))
                continue
            # don't try to follow path if it's an internal branch (i.e. control flow within this function)
            # any internal branching will eventually be covered by call_targets,
            # so there's no need to follow twice
            if self.is_local_branch(target):
                self.debug_print(instr_idx, 'local goto -> {}'.format(hex(int(target.destination_address))))
                continue

            # might be objc_msgSend to object of class defined outside binary
            if target.is_external_objc_call:
                if target.selref:
                    self.debug_print(instr_idx, 'objc_msgSend(...) to external class, selector {}'.format(
                        target.selref.selector_literal
                    ))
                else:
                    self.debug_print(instr_idx, 'objc_msgSend(...) to external class, unknown selref')
                continue

            # in debug log, print whether this is a function call or objc_msgSend call
            call_convention = 'objc_msgSend(id, ' if target.is_msgSend_call else 'func('
            self.debug_print(instr_idx, '{}{})'.format(
                call_convention,
                hex(int(target.destination_address)),
            ))

            # recursively check if this destination can call target address
            child_analyzer = ObjcFunctionAnalyzer.get_function_analyzer(self.binary, target.destination_address)
            if child_analyzer.can_execute_call(call_address):
                self.debug_print(instr_idx, 'found call to {} in child code path'.format(
                    hex(int(call_address))
                ))
                return True
        # no code paths reach desired call
        self.debug_print(len(self.instructions), 'no code paths reach {}'.format(
            hex(int(call_address))
        ))
        return False

    @classmethod
    def format_instruction(cls, instr):
        # type: (CsInsn) -> Text
        """Stringify a CsInsn for printing
        Args:
            instr: Instruction to create formatted string representation for
        Returns:
            Formatted string representing instruction
        """
        return "{addr}:\t{mnemonic}\t{ops}".format(addr=hex(int(instr.address)),
                                                   mnemonic=instr.mnemonic,
                                                   ops=instr.op_str)

    def track_reg(self, reg):
        # type: (Text) -> List[Text]
        """
        Track the flow of data starting in a register through a list of instructions
        Args:
            reg: Register containing initial location of data
        Returns:
            List containing all registers which contain data originally in reg
        """
        # list containing all registers which hold the same value as initial argument reg
        regs_holding_value = [reg]
        for instr in self.instructions:
            # TODO(pt) track other versions of move w/ suffix e.g. movz
            # do instructions like movz only operate on literals? we only care about reg to reg
            if instr.mnemonic == 'mov':
                if len(instr.operands) != 2:
                    raise RuntimeError('Encountered mov with more than 2 operands! {}'.format(
                        self.format_instruction(instr)
                    ))
                # in mov instruction, operands[0] is dst and operands[1] is src
                src = instr.reg_name(instr.operands[1].value.reg)
                dst = instr.reg_name(instr.operands[0].value.reg)

                # check if we're copying tracked value to another register
                if src in regs_holding_value and dst not in regs_holding_value:
                    # add destination register to list of registers containing value to track
                    regs_holding_value.append(dst)
                # check if we're copying something new into a register previously containing tracked value
                elif dst in regs_holding_value and src not in regs_holding_value:
                    # register being overwrote -- no longer contains tracked value, so remove from list
                    regs_holding_value.remove(dst)
        return regs_holding_value

    # TODO(PT): this should return the branch and the instruction index for caller convenience
    def next_branch_after_instruction_index(self, start_index):
        # type: (int) -> Optional[ObjcBranchInstruction]

        for idx, instr in enumerate(self.instructions[start_index::]):
            if ObjcBranchInstruction.is_branch_instruction(instr):
                # found next branch!
                # wrap in ObjcBranchInstruction object
                branch_instr = ObjcBranchInstruction.parse_instruction(self, instr)

                # were we able to resolve the destination of this call?
                # some objc_msgSend calls are too difficult to be parsed, for example if they depend on addresses
                # in the stack. detect this fail case
                if branch_instr.is_msgSend_call and not branch_instr.destination_address:
                    instr_idx = start_index + idx
                    self.debug_print(instr_idx, 'bl <objc_msgSend> target cannot be determined statically')

                return ObjcBranchInstruction.parse_instruction(self, instr)
        return None

    def is_local_branch(self, branch_instruction):
        # if there's no destination address, the destination is outside the binary, and it couldn't possible be local
        if not branch_instruction.destination_address:
            return False
        return self.start_address <= branch_instruction.destination_address <= self.end_address

    def get_selref_ptr(self, msgsend_instr):
        # type: (CsInsn) -> int
        """Retrieve contents of x1 register when control is at provided instruction

        Args:
              msgsend_instr: Instruction at which data in x1 should be found

        Returns:
              Data stored in x1 at execution of msgsend_instr

        """
        # just as a sanity check, ensure the passed instruction is at least a branch
        # TODO(PT): we could also check the branch destination to ensure it's really an objc_msgSend call
        if msgsend_instr.mnemonic != 'bl':
            raise ValueError('asked to find selref of non-branch instruction')

        msgsend_index = self.instructions.index(msgsend_instr)
        wrapped_instr = ObjcInstruction.parse_instruction(msgsend_instr)
        # retrieve whatever data is in x1 at the index of this msgSend call
        contents = self.get_register_contents_at_instruction('x1', wrapped_instr)
        if contents.type != RegisterContentsType.IMMEDIATE:
            raise RuntimeError('couldn\'t determine selref ptr, origates in function arg')
        return contents.value

    def _trimmed_reg_name(self, reg_name):
        # type: (Text) -> Text
        """Remove 'x' or 'w' from general purpose register name
        This is so the register strings 'x22' and 'w22', which are two slices of the same register,
        map to the same register.

        Will return non-GP registers, such as 'sp', as-is.

        Args:
              reg_name: Full register name to trim

        Returns:
              Register name with trimmed size prefix, or unmodified name if not a GP register

        """
        if reg_name[0] in ['x', 'w']:
            return reg_name[1::]
        return reg_name

    def get_register_contents_at_instruction(self, register, instruction):
        # type: (Text, ObjcInstruction) -> RegisterContents
        """Analyze instructions backwards from start_index to find data in reg
        This function will read all instructions until it gathers all data and assignments necessary to determine
        value of desired_reg.

        For example, if we have a function like the following:
        15  | adrp x8, #0x1011bc000
        16  | ldr x22, [x8, #0x378]
        ... | ...
        130 | mov x1, x22
        131 | bl objc_msgSend <-- ObjcDataFlowAnalyzer.find_reg_value('x1', 131) = 0x1011bc378

        Args:
            desired_reg: string containing name of register whose data should be determined
            instruction: the instruction marking the execution point where the register value should be determined

        Returns:
            A RegisterContents instance encapsulating information about the contents of the specified register at the
            specified point of execution
        """
        desired_reg = register
        start_index = self.instructions.index(instruction.raw_instr)

        bytes_in_instruction = 4
        target_addr = self.start_address + (start_index * bytes_in_instruction)
        DebugUtil.log(self, 'analyzing data flow to determine data in {} at {}'.format(
            desired_reg,
            hex(int(target_addr))
        ))

        # TODO(PT): write CsInsn instructions by hand to make this function easy to test w/ different scenarios
        # List of registers whose values we need to find
        # initially, we need to find the value of whatever the user requested
        unknown_regs = [self._trimmed_reg_name(desired_reg)]
        # map of name -> value for registers whose values have been resolved to an immediate
        determined_values = {}
        # map of name -> (name, value). key is register needing to be resolved,
        # value is tuple containing (register containing source value, signed offset from source register)
        needed_links = {}

        # find data starting backwards from start_index
        # TODO(PT): instead of blindly going through instructions backwards,
        # only follow possible code paths split into basic blocks from ObjcBasicBlock
        for instr in self.instructions[start_index::-1]:
            # still looking for anything?
            if len(unknown_regs) == 0:
                # found everything we need
                break

            # we only care about instructions that could be moving data between registers
            # therefore, the minimum number of operands an instruction we're interested in could have is 2
            if len(instr.operands) < 2:
                continue
            # some instructions will have the same format as register transformations,
            # but are actually unrelated to what we're looking for
            # for example, str x1, [sp, #0x38] would be identified by this function as moving something from sp into
            # x1, but with that particular instruction it's the other way around: x1 is being stored somewhere offset
            # from sp.
            # to avoid this bug, we need to exclude some instructions from being looked at by this method.
            excluded_instructions = [
                'str',
            ]
            if instr.mnemonic in excluded_instructions:
                continue

            dst = instr.operands[0]
            src = instr.operands[1]

            # we're only interested in instructions whose destination is a register
            if dst.type != ARM64_OP_REG:
                continue
            dst_reg_name = self._trimmed_reg_name(instr.reg_name(dst.value.reg))
            # is this register needed for us to determine the value of the requested register?
            if dst_reg_name not in unknown_regs:
                continue

            # src might not actually be the first operand
            # this could be an instruction like 'orr', whose invocation might look like this:
            # orr x1, wzr, #0x2
            # here, wzr is used as a 'trick' and the real source is the third operand
            # try to detect this pattern
            # zr indicates zero-register
            if len(instr.operands) > 2:
                if src.type == ARM64_OP_REG:
                    if self._trimmed_reg_name(instr.reg_name(src.value.reg)) == 'zr':
                        src = instr.operands[2]

            if src.type == ARM64_OP_IMM:
                # we now know the immediate value in dst_reg_name
                # remove it from unknown list
                unknown_regs.remove(dst_reg_name)
                # add it to known list, along with its value
                determined_values[dst_reg_name] = src.value.imm
            elif src.type == ARM64_OP_REG:
                # we now need the value of src before dst can be determined
                # move dst from list of unknown registers to list of registers waiting for another value
                unknown_regs.remove(dst_reg_name)
                src_reg_name = self._trimmed_reg_name(instr.reg_name(src.value.reg))

                # do we already know the exact value of the source?
                if src_reg_name in determined_values:
                    # value of dst will just be whatever src contains
                    dst_value = determined_values[src_reg_name]
                    determined_values[dst_reg_name] = dst_value
                else:
                    # we'll need to resolve src before we can know dst,
                    # add dst -> src to links list
                    needed_links[dst_reg_name] = src_reg_name, 0
                    # and add src to registers to search for
                    unknown_regs.append(src_reg_name)
            elif src.type == ARM64_OP_MEM:
                # an instruction with an operand of type ARM64_OP_MEM might look like:
                # ldr x1, [x3, #0x1000]
                # here, the bracketed portion is accessible through src.mem, which has a reg base and imm disp property
                src_reg_name = self._trimmed_reg_name(instr.reg_name(src.mem.base))
                # dst is being assigned to the value of another register, plus a signed offset
                unknown_regs.remove(dst_reg_name)
                if src_reg_name in determined_values:
                    # we know dst value is value in src plus an offset,
                    # and we know what's in source
                    # we now know the value of dst
                    dst_value = determined_values[src_reg_name] + src.mem.disp
                    determined_values[dst_reg_name] = dst_value
                else:
                    # we must find src's value to resolve dst
                    unknown_regs.append(src_reg_name)
                    # add dst -> src + offset to links list
                    needed_links[dst_reg_name] = src_reg_name, src.mem.disp

        # if any of the data dependencies for our desired register uses the stack pointer,
        # there's no way we can resolve the value.
        stack_pointer_reg = 'sp'
        if stack_pointer_reg in needed_links:
            raise RuntimeError('{} contents depends on stack, cannot determine statically'.format(desired_reg))

        # once we've broken out of the above loop, we should have all the values we need to compute the
        # final value of the desired register.

        # if we broke out of the above loop and there is still content in unknown_regs,
        # the desired value must have been an argument to the function
        if len(unknown_regs):
            # if the above assumption is correct, there should only be 1 reg in unknown_regs
            if len(unknown_regs) > 1:
                DebugUtil.log(self, 'Exited loop with unknown list! instr 0 {} idx {} unknown {} links {} known {}'.format(
                    hex(int(self.start_address)),
                    start_index,
                    unknown_regs,
                    needed_links,
                    determined_values,
                ))
                raise RuntimeError('Data-flow loop exited before all unknowns were marked {}'.format(unknown_regs))

            arg_index = int(unknown_regs[0])
            return RegisterContents(RegisterContentsType.FUNCTION_ARG, arg_index)

        # for every register in the waiting list,
        # cross reference all its dependent variables to calculate the final value
        final_register_value = self._resolve_register_value_from_data_links(
            desired_reg,
            needed_links,
            determined_values
        )
        return RegisterContents(RegisterContentsType.IMMEDIATE, final_register_value)

    def _resolve_register_value_from_data_links(self, desired_reg, links, resolved_registers):
        # type: (Text, Dict[Text, Tuple[Text, int]], Dict[Text, int]) -> int
        """Resolve data dependencies for each register to find final value of desired_reg
        This method will throw an Exception if the arguments cannot be resolved.

        Args:
              desired_reg: string containing name of register whose value should be determined
              links: mapping of register data dependencies. For example, x1's value might be x22's value plus an
              offset of 0x300, so links['x1'] = ('x22', 0x300)
              resolved_registers: mapping of registers whose final value is already known

        Returns:
            The final value contained in desired_reg after resolving all data dependencies
        """

        if len(resolved_registers) == 0:
            raise RuntimeError('need at least one known value to resolve data dependencies')

        desired_reg = self._trimmed_reg_name(desired_reg)
        if desired_reg not in links and desired_reg not in resolved_registers:
            raise RuntimeError('invalid data set? desired_reg {} can\'t be determined from '
                               'links {}, resolved_registers {}'.format(
                desired_reg,
                links,
                resolved_registers,
            ))

        # do we know the value of this register?
        if desired_reg in resolved_registers:
            DebugUtil.log(self, 'x{} is a known immediate: {}'.format(
                desired_reg,
                hex(int(resolved_registers[desired_reg]))
            ))
            return resolved_registers[desired_reg]

        # to determine value in desired_reg,
        # we must find the value of source_reg, and then apply any offset
        source_reg, offset = links[desired_reg]
        DebugUtil.log(self, 'x{} has data dependency: [x{}, #{}]'.format(
            desired_reg,
            source_reg,
            hex(int(offset))
        ))

        # resolve source reg value, then add offset
        source_reg_val = self._resolve_register_value_from_data_links(source_reg, links, resolved_registers)
        desired_reg_val = source_reg_val + offset

        # this link has been resolved! remove from links list
        links.pop(desired_reg)
        # add to list of known values
        resolved_registers[desired_reg] = desired_reg_val

        DebugUtil.log(self, 'x{} resolved to {}'.format(
            desired_reg,
            hex(int(desired_reg_val))
        ))
        return desired_reg_val


class ObjcBlockAnalyzer(ObjcFunctionAnalyzer):
    def __init__(self, binary, instructions, initial_block_reg):
        ObjcFunctionAnalyzer.__init__(self, binary, instructions)

        self.initial_block_reg = initial_block_reg
        self.block_arg_index = int(self._trimmed_reg_name(self.initial_block_reg))
        self.invoke_instruction, self.invocation_instruction_index = self.find_block_invoke()

    def find_block_invoke(self):
        # type: () -> (CsInsn, int)
        """Find instruction where the targeted Block->invoke is loaded into

        Returns:
             Tuple of register containing target Block->invoke, and the index this instruction was found at
        """
        block_invoke_search = CodeSearch(
            required_matches=[
                CodeSearchTermInstructionMnemonic(self.binary, allow_mnemonics=['blr']),
                CodeSearchTermInstructionOperand(self.binary, operand_index=0, operand_type=ARM64_OP_REG)
            ],
            requires_all_terms_matched=True
        )
        for search_result in self.search_code(block_invoke_search):
            # in the past, find_block_invoke would find a block load from an instruction like:
            # ldr x8, [<block containing reg>, 0x10]
            # then, we look for a block invoke instruction:
            # blr x8
            # Now, we just look for a blr to a register that has a dependency on the data originally in the register
            # containing the block pointer.
            # this is very likely to work more or less all the time.
            # TODO(PT): CodeSearchTermDataDependency?
            found_branch_instruction = search_result.found_instruction
            instruction_index = self.instructions.index(found_branch_instruction)
            reg, is_func_arg = self.determine_register_contents(self.initial_block_reg, instruction_index)

            trimmed_block_argument_reg = int(self._trimmed_reg_name(self.initial_block_reg))
            if not is_func_arg or reg != trimmed_block_argument_reg:
                # not the instruction we're looking for
                continue
            return found_branch_instruction, instruction_index
        raise RuntimeError('never found block invoke')
