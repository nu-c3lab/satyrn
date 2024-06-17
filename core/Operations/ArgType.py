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

from enum import Enum
from typing import List

class ArgType(Enum):
    Arithmetic = 1
    Categorical = 2
    Document = 3
    Datetime = 4
    Metric = 5
    Identifier = 6

    Entity = 7
    Attribute = 8
    Group = 9
    Filter = 10
    Sort = 11
    Limit = 12
    RowNum = 13
    AttributeCollection = 14

    String = 15

    # DiagnosticMetric = 16
    # ComparativeMetric = 17

    StartDate = 18
    EndDate = 19

    Quantity = 21

    RelatedIdentifier = 22

    @staticmethod
    def from_str(label: str) -> 'ArgType':
        label = label.lower()
        if label == 'arithmetic':
            return ArgType.Arithmetic
        elif label == 'categorical':
            return ArgType.Categorical
        elif label == 'document':
            return ArgType.Document
        elif label == 'datetime':
            return ArgType.Datetime
        elif label == 'metric':
            return ArgType.Metric
        # elif label == 'diagnosticmetric':
        #     return ArgType.DiagnosticMetric
        # elif label == 'comparativemetric':
        #     return ArgType.ComparativeMetric
        elif label == 'identifier':
            return ArgType.Identifier
        elif label == 'relatedidentifier':
            return ArgType.RelatedIdentifier
        elif label == 'entity':
            return ArgType.Entity
        elif label == 'attribute':
            return ArgType.Attribute
        elif label == 'group':
            return ArgType.Group
        elif label == 'string':
            return ArgType.String
        elif label == 'startdate':
            return ArgType.StartDate
        elif label == 'enddate':
            return ArgType.EndDate
        elif label == 'quantity':
            return  ArgType.Quantity
        else:
            raise NotImplementedError
    @staticmethod
    def get_all() -> List['ArgType']:
        return [ArgType.Arithmetic, ArgType.Categorical, ArgType.Document, ArgType.Datetime, ArgType.StartDate, ArgType.EndDate, ArgType.Metric, ArgType.Quantity, ArgType.Identifier, ArgType.RelatedIdentifier, ArgType.Entity, ArgType.Attribute, ArgType.Group, ArgType.Filter, ArgType.AttributeCollection, ArgType.String]
