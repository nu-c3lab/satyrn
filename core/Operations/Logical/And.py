'''
This file is part of Satyrn.
Satyrn is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software Foundation,
either version 3 of the License, or (at your option) any later version.
Satyrn is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
See the GNU General Public License for more details.
You should have received a copy of the GNU General Public License along with Satyrn.
If not, see <https://www.gnu.org/licenses/>.
'''

import math
from typing import Any, List
from sqlalchemy import and_

from core.Operations.ArgType import ArgType
from core.Operations.OperationArgument import OperationArgument
from core.Operations.BooleanOperation import BooleanOperation

class And(BooleanOperation):
    def __init__(self):
        name = "and"
        input_args = [
            OperationArgument(1, math.inf, [ArgType.Filter])
        ]
        output_args = [
            OperationArgument(1, 1, [ArgType.Filter])
        ]
        super().__init__(name, input_args, output_args)

    def sqlalchemy_op(self,
                      operation_input: List[Any],
                      db_type: str) -> None:
        return and_(*operation_input)
