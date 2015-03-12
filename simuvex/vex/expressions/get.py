from .base import SimIRExpr
from ...s_helpers import size_bytes
from ... import s_options as o
from ...s_action import SimActionData

class SimIRExpr_Get(SimIRExpr):
	def _execute(self):
		size = size_bytes(self._expr.type)
		self.type = self._expr.type

		# get it!
		self.expr = self.state.reg_expr(self._expr.offset, size)

		# finish it and save the register references
		self._post_process()
		if o.REGISTER_REFS in self.state.options:
			r = SimActionData(self.state, self.state.registers.id, SimActionData.READ, offset=self._expr.offset, size=size, data=self.expr)
			self.actions.append(r)
