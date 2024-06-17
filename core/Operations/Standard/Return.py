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

from core.Operations.ArgType import ArgType
from core.Operations.DataOperation import DataOperation
from core.Operations.OperationArgument import OperationArgument

class Return(DataOperation):
    def __init__(self):
        name = "return"
        input_args = [
            OperationArgument(1, 1, [ArgType.AttributeCollection]),
            OperationArgument(0, 1, [ArgType.Filter]),
            OperationArgument(0, 1, [ArgType.Sort])
        ]
        output_args = [
            OperationArgument(1, 1, [ArgType.Entity])
        ]
        super().__init__(name, input_args, output_args)
