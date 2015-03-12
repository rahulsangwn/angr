from .base import SimIRExpr
from ...s_helpers import size_bytes, size_bits
from ... import s_options as o
from ...s_action import SimActionData
from ...s_action_object import SimActionObject

class SimIRExpr_Load(SimIRExpr):
	def _execute(self):
		# size of the load
		size = size_bytes(self._expr.type)
		self.type = self._expr.type

		# get the address expression and track stuff
		addr = self._translate_expr(self._expr.addr)

		# if we got a symbolic address and we're not in symbolic mode, just return a symbolic value to deal with later
		if o.DO_LOADS not in self.state.options:
			self.expr = self.state.se.Unconstrained("load_expr_0x%x_%d" % (self.imark.addr, self.stmt_idx), size*8)
		else:

			# load from memory and fix endianness
			self.expr = self.state.mem_expr(addr.expr, size, endness=self._expr.endness)

		# finish it and save the mem read
		self._post_process()
		if o.MEMORY_REFS in self.state.options:
			addr_ao = SimActionObject(addr.expr, reg_deps=addr.reg_deps(), tmp_deps=addr.tmp_deps())
			r = SimActionData(self.state, self.state.memory.id, SimActionData.READ, addr=addr_ao, size=size_bits(self._expr.type), data=self.expr)
			self.actions.append(r)
