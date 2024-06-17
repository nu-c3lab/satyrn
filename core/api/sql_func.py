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

# SQL functions to be able to work in postres and sqlite

from typing import List
from sqlalchemy import func, Date, cast
from functools import reduce
from sqlalchemy.sql.expression import case, Case

def sql_right(field, db_type: str, char_n: int=2):
    # Given a sqlalchemy string field, return the last char_n chars
    if db_type == "sqlite":
        return func.substr(field, -2, 2)
    elif db_type == "postgres":
        return func.right(field, 2)

def sql_concat(field_lst: List[Case], db_type: str):
    # concatenating strings together
    if len(field_lst) == 1:
        return field_lst[0]

    if db_type == "sqlite":
        return reduce(lambda a, b: a + b, field_lst, "")

    elif db_type == "postgres":
        return reduce(lambda a, b: a + b, field_lst, "")
        # return func.concatenate(field_lst)

def sql_median(field, db_type):
    # Given a sqlalchemy string field, return the last char_n chars
    if db_type == "sqlite":
        return func.median(field)
    elif db_type == "postgres":
        return func.percentile_disc(0.5).within_group(field.asc())

def nan_cast(field, cast_val):
    # Casts a field in case it is a null value
    return case([(field == None, cast_val)], else_=field)

def date_cast(field, db_type):
    if db_type == "sqlite":
        return func.DATE(field)
    elif db_type == "postgres":
        return cast(field, Date)
