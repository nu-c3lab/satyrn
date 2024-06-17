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

from typing import Set, List, Dict
from sqlalchemy.sql.expression import Label
from sqlalchemy.sql.elements import BinaryExpression

class QueryArguments:
    def __init__(self,
                 query_fields: List[Label],
                 tables: Set[str],
                 sqrfields: Dict[str, dict],
                 joins_todo: set,
                 select: list,
                 group_bys: list,
                 sort_attributes: List[dict],
                 filter: List[BinaryExpression] = None,
                 having: List[BinaryExpression] = None,
                 froms: list = None):
        self.query_fields = query_fields
        self.tables = tables
        self.sqrfields = sqrfields
        self.joins_todo = joins_todo
        self.select = select
        self.filter = filter
        self.having = having
        self.group_bys = group_bys
        self.sort_attributes = sort_attributes
        self.limit = None
        self.froms = froms
