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

from typing import List, Any
from functools import reduce

from core.Operations.ArgType import ArgType
from core.Operations.SQLAInterface import SQLAInterface
from core.Operations.PandasInterface import  PandasInterface
from core.Operations.OperationArgument import OperationArgument
from core.Operations.ArithmeticOperation import ArithmeticOperation

class Percentage(ArithmeticOperation, SQLAInterface, PandasInterface):
    def __init__(self):
        name = 'percentage'
        input_args = [
            OperationArgument(1, 1, [ArgType.Quantity]),
            OperationArgument(1, 1, [ArgType.Quantity]),
        ]
        output_args = [
            OperationArgument(1, 1, [ArgType.Metric])
        ]
        template = "percentage of {0} in {1}"
        super().__init__(name, input_args, output_args, template)

    def sqlalchemy_op(self,
                      operation_input: List[Any],
                      db_type: str) -> None:
        return reduce(lambda a, arg: a / arg, operation_input)

