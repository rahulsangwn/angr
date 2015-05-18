from .tablespecs import StringTableSpec

import logging
l = logging.getLogger('angr.states')

class StateGenerator(object):
    def __init__(self, project):
        self._project = project
        self._arch = project.arch
        self._simos = project.simos
        self._ld = project.ld

    def blank_state(self, mode=None, address=None, initial_prefix=None,
                    options=None, add_options=None, remove_options=None):

        if address is None:
            address = self._project.entry
        if mode is None:
            mode = self._project.default_analysis_mode

        memory_backer = self._ld.memory

        state = self._simos.make_state(memory_backer=memory_backer,
                                       mode=mode, options=options,
                                       initial_prefix=initial_prefix,
                                       add_options=add_options,
                                       remove_options=remove_options)

        state.regs.ip = address

        return state


    def entry_point(self, args=None, env=None, sargc=None, **kwargs):
        '''
        entry_point     Returns a state reflecting the processor when execution
                        reaches the binary's entry point.

        @param args     Argv for the program as a python list. Optional.
        @param env      The program's environment as a python dict. Optional.
        @param sargc    If true, argc will be fully unconstrained even if you supply argv. Be very afraid.

        Any further params will be directly re-passed to StateGenerator.blank_state.
        '''

        state = self.blank_state(**kwargs)

        if args is not None:
            # Handle default values
            if env is None:
                env = {}

            # Prepare argc
            argc = state.BVV(len(args), state.arch.bits)
            if sargc is not None:
                argc = state.se.Unconstrained("argc", state.arch.bits)

            # Make string table for args/env/auxv
            table = StringTableSpec()

            # Add args to string table
            for arg in args:
                table.add_string(arg)
            table.add_null()

            # Add environment to string table
            for k, v in env.iteritems():
                table.add_string(k + '=' + v)
            table.add_null()

            # Prepare the auxiliary vector and add it to the end of the string table
            # TODO: Actually construct a real auxiliary vector
            aux = []
            for a, b in aux:
                table.add_pointer(a)
                table.add_pointer(b)
            table.add_null()
            table.add_null()

            # Dump the table onto the stack, calculate pointers to args, env, and auxv
            argv = table.dump(state, state.sp_expr())
            envp = argv + ((len(args) + 1) * state.arch.bytes)
            auxv = argv + ((len(args) + len(env) + 2) * state.arch.bytes)

            # Put argc on stack and fix the stack pointer
            newsp = argv - state.arch.bytes
            state.store_mem(newsp, argc, endness=state.arch.memory_endness)
            state.regs.sp = newsp

            if state.arch.name in ('PPC32',):
                state.stack_push(state.BVV(0, 32))
                state.stack_push(state.BVV(0, 32))
                state.stack_push(state.BVV(0, 32))
                state.stack_push(state.BVV(0, 32))
        else:
            state.stack_push(state.BVV(0, state.arch.bits))
            newsp = state.sp_expr()
            state.store_mem(newsp, state.BVV(0, state.arch.bits), endness=state.arch.memory_endness)
            argv = newsp + state.arch.bytes
            argc = 0
            envp = argv
            auxv = argv

        # store argc argv envp in the posix plugin
        state.posix.argv = argv
        state.posix.argc = argc
        state.posix.environ = envp

        # drop in all the register values at the entry point
        for reg, val in self._arch.entry_register_values.iteritems():
            if isinstance(val, (int, long)):
                state.store_reg(reg, val, length=state.arch.bytes)
            elif isinstance(val, (str,)):
                if val == 'argc':
                    state.store_reg(reg, argc, length=state.arch.bytes)
                elif val == 'argv':
                    state.store_reg(reg, argv)
                elif val == 'envp':
                    state.store_reg(reg, envp)
                elif val == 'auxv':
                    state.store_reg(reg, auxv)
                elif val == 'ld_destructor':
                    # a pointer to the dynamic linker's destructor routine, to be called at exit
                    # or NULL. We like NULL. It makes things easier.
                    state.store_reg(reg, state.BVV(0, state.arch.bits))
                elif val == 'toc':
                    if self._ld.main_bin.ppc64_initial_rtoc is not None:
                        state.store_reg(reg, self._ld.main_bin.ppc64_initial_rtoc)
                        state.libc.ppc64_abiv = 'ppc64_1'
                else:
                    l.warning('Unknown entry point register value indicator "%s"', val)
            else:
                l.error('What the ass kind of default value is %s?', val)

        return state
