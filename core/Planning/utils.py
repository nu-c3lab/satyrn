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

from typing import List

def oxfordcomma(items: List[str]) -> str:
    """
    Joins the list of items as a comma separated list with proper use of "and".
    :param items: Items to put into the statement.
    :type items: List of str
    :return: A string representing the properly formatted list.
    :rtype: str
    """
    if len(items) == 0:
        return ''
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return items[0] + ' and ' + items[1]
    return ', '.join(items[:-1]) + ', and ' + items[-1]

def capitalize_first_only(s: str) -> str:
    """
    Capitalizes the first letter of the string.
    :param s: The string to capitalize.
    :type s: str
    :return: A string with the first letter capitalized.
    :rtype: str
    """
    return s[0].upper() + s[1:]
