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

from typing import Dict

from core.Operations.Operation import Operation

from core.Operations.Standard.Sort import Sort
from core.Operations.Standard.Limit import Limit
from core.Operations.Standard.RowNum import RowNum
from core.Operations.Standard.Collect import Collect
from core.Operations.Standard.Return import Return
from core.Operations.Logical.Exact import Exact
from core.Operations.Logical.Contains import Contains
from core.Operations.Logical.LessThan import LessThan
from core.Operations.Logical.GreaterThan import GreaterThan
from core.Operations.Logical.LessThanEq import LessThanEq
from core.Operations.Logical.GreaterThanEq import GreaterThanEq
from core.Operations.Logical.And import And
from core.Operations.Logical.Or import Or
from core.Operations.Logical.Not import Not
from core.Operations.Standard.Groupby import Groupby
from core.Operations.Standard.RetrieveEntity import RetrieveEntity
from core.Operations.Standard.RetrieveAttribute import RetrieveAttribute

from core.Operations.Aggregation.Average import Average
from core.Operations.Aggregation.Count import Count
from core.Operations.Aggregation.CountUnique import CountUnique
from core.Operations.Aggregation.Max import Max
from core.Operations.Aggregation.Median import Median
from core.Operations.Aggregation.Min import Min
from core.Operations.Aggregation.Sum import Sum
from core.Operations.Aggregation.StdDev import StdDev
from core.Operations.Aggregation.StringAgg import StringAgg
from core.Operations.Aggregation.GetOne import GetOne
from core.Operations.Aggregation.Correlation import Correlation

from core.Operations.Math.Add import Add
from core.Operations.Math.Subtract import Subtract
from core.Operations.Math.Multiply import Multiply
from core.Operations.Math.Divide import Divide
from core.Operations.Math.Sqrt import Sqrt
from core.Operations.Math.Abs import Abs
from core.Operations.Math.PercentChange import PercentChange
from core.Operations.Math.Duration import Duration
from core.Operations.Math.Percentage import Percentage

class OperationOntology:
    def __init__(self):
        self.retrieval_operations = self.load_retrieval_operations()
        self.aggregation_operations = self.load_aggregation_operations()
        self.boolean_operations = self.load_boolean_operations()
        self.collect_operations = self.load_collect_operations()
        self.return_operations = self.load_return_operations()
        self.sort_operations = self.load_sort_operations()
        self.limit_operations = self.load_limit_operations()
        self.rownum_operations = self.load_rownum_operations()
        self.analysis_operations = self.load_analysis_operations()
        self.arithmetic_operations = self.load_arithmetic_operations()

    def load_retrieval_operations(self) -> Dict[str, Operation]:
        ret_ent = RetrieveEntity()
        ret_attr = RetrieveAttribute()
        return {
            ret_ent.name: ret_ent,
            ret_attr.name: ret_attr
        }

    def load_aggregation_operations(self) -> Dict[str, Operation]:
        groupby_op = Groupby()
        return {
            groupby_op.name: groupby_op
        }

    def load_boolean_operations(self) -> Dict[str, Operation]:
        boolean_ops = [Exact, Contains, LessThan, GreaterThan, LessThanEq, GreaterThanEq, And, Or, Not]
        return {op().name: op() for op in boolean_ops}

    def load_arithmetic_operations(self) -> Dict[str, Operation]:
        arithmetic_ops = [Add, Subtract, Multiply, Divide, Sqrt, Abs, PercentChange, Duration, Percentage]
        # also load and, or, and not operations here
        return {op().name: op() for op in arithmetic_ops}

    def load_collect_operations(self) -> Dict[str, Operation]:
        collect_op = Collect()
        return {
            collect_op.name: collect_op
        }

    def load_return_operations(self) -> Dict[str, Operation]:
        return_op = Return()
        return {
            return_op.name: return_op
        }

    def load_sort_operations(self) -> Dict[str, Operation]:
        sort_op = Sort()
        return {
            sort_op.name: sort_op
        }

    def load_limit_operations(self) -> Dict[str, Operation]:
        limit_op = Limit()
        return {
            limit_op.name: limit_op
        }

    def load_rownum_operations(self) -> Dict[str, Operation]:
        rownum_op = RowNum()
        return {
            rownum_op.name: rownum_op
        }

    def load_analysis_operations(self) -> Dict[str, Operation]:
        # Get a list of the analysis operation classes
        analysis_ops = [Average, Count, CountUnique, Max, Median, Min, Sum, StdDev, StringAgg, GetOne, Correlation]

        # Create the dictionary with the analysis operations instantiated
        analysis_ops_dict = {op().name: op() for op in analysis_ops}

        return analysis_ops_dict

    def load_plugin_operations(self) -> Dict[str, Operation]:
        plugin_ops = [Duration, Percentage]
        return {op().name: op() for op in plugin_ops}

    def is_retrieval_operation(self,
                               operation_name: str) -> bool:
        return operation_name in self.retrieval_operations

    def is_analysis_operation(self,
                              operation_name: str) -> bool:
        return operation_name in self.analysis_operations

    def is_collect_operation(self,
                            operation_name: str) -> bool:
        return operation_name in self.collect_operations

    def is_return_operation(self,
                          operation_name: str) -> bool:
        return operation_name in self.return_operations

    def is_sort_operation(self,
                          operation_name: str) -> bool:
        return operation_name in self.sort_operations

    def is_limit_operation(self,
                          operation_name: str) -> bool:
        return operation_name in self.limit_operations

    def is_rownum_operation(self,
                           operation_name: str) -> bool:
        return operation_name in self.rownum_operations

    def is_boolean_operation(self,
                             operation_name: str) -> bool:
        return operation_name in self.boolean_operations

    def is_aggregation_operation(self,
                                 operation_name: str) -> bool:
        return operation_name in self.aggregation_operations

    def is_arithmetic_operation(self,
                                operation_name: str) -> bool:
        return operation_name in self.arithmetic_operations

    def resolve_operation(self,
                          operation_name: str) -> Operation:
        if operation_name in self.analysis_operations:
            return self.analysis_operations[operation_name]
        elif operation_name in self.retrieval_operations:
            return self.retrieval_operations[operation_name]
        elif operation_name in self.aggregation_operations:
            return self.aggregation_operations[operation_name]
        elif operation_name in self.boolean_operations:
            return self.boolean_operations[operation_name]
        elif operation_name in self.collect_operations:
            return self.collect_operations[operation_name]
        elif operation_name in self.return_operations:
            return self.return_operations[operation_name]
        elif operation_name in self.sort_operations:
            return self.sort_operations[operation_name]
        elif operation_name in self.limit_operations:
            return self.limit_operations[operation_name]
        elif operation_name in self.arithmetic_operations:
            return self.arithmetic_operations[operation_name]
        elif operation_name in self.rownum_operations:
            return self.rownum_operations[operation_name]
        else:
            raise ValueError("Unable to resolve the operation name to operation object.")
