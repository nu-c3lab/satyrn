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
from typing import List, Any
from sqlalchemy import func, asc, desc, nullslast
from sqlalchemy.sql.elements import Label

from core.Operations.ArgType import ArgType
from core.Operations.DataOperation import DataOperation
from core.Operations.OperationArgument import OperationArgument

class RowNum(DataOperation):
    def __init__(self):
        name = "rownum"
        input_args = [
            OperationArgument(1, 1, [ArgType.Sort])
        ]
        output_args = [
            OperationArgument(1, 1, [ArgType.RowNum])
        ]

        super().__init__(name, input_args, output_args)
        self.template = "rank when {0}"

    def sqlalchemy_op(self,
                      operation_input: List[Any],
                      db_type: str) -> None:
        args_list = []
        for sort_column, sort_direction in zip(operation_input[0::2], operation_input[1::2]):
            args_list.append(nullslast(eval(sort_direction)(sort_column)))
        return func.row_number().over(order_by=args_list)
