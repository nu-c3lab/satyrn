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

from sqlalchemy import func
from typing import List, Any

from core.Operations.ArgType import ArgType
from core.Operations.SQLAInterface import SQLAInterface
from core.Operations.PandasInterface import  PandasInterface
from core.Operations.OperationArgument import OperationArgument
from core.Operations.AggregationOperation import AggregationOperation

class StdDev(AggregationOperation, SQLAInterface, PandasInterface):
    def __init__(self):
        name = 'stddev'
        input_args = [
            OperationArgument(1, 1, [ArgType.Arithmetic, ArgType.Metric]),
            OperationArgument(0, 1, [ArgType.Group])
        ]
        output_args = [
            OperationArgument(1, 1, [ArgType.Arithmetic, ArgType.Metric])
        ]
        template = "standard deviation of {target}"
        super().__init__(name, input_args, output_args, template)

    def sqlalchemy_op(self,
                      operation_input: List[Any],
                      db_type: str) -> None:
        if db_type == 'sqlite':
            return func.stdev(operation_input[0])
        else:
            return func.stddev(operation_input[0])

