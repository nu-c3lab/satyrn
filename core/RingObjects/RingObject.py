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

class RingObject(object):
    """
    Contains utility functions for the other RingX classes. It serves as the superclass for concrete ring classes.
    """

    def safe_extract_list(self,
                          key,
                          dictionary: dict) -> list:
        """
        Extract value if list, if not extract and wrap in list.
        :param key: A key in the dictionary.
        :type key:
        :param dictionary: The dictionary to check.
        :type dictionary: dict
        :return: Ensures that the dictionary value at the key is returned as a list.
        :rtype: list
        """
        if key in dictionary and dictionary[key]:
            value = dictionary[key]
            if type(value) is list:
                return value
            else:
                return [value]
        return None

    def safe_insert(self,
                    key,
                    value,
                    dictionary: dict) -> None:
        """
        If the value evaluates to True, it is inserted into the dictionary at the specified key.
        :param key: A key in the dictionary.
        :type key:
        :param value: The value to update/insert into the dictionary.
        :type value: Any
        :param dictionary: The dictionary in which the value is inserted.
        :type dictionary: dict
        :return: None
        :rtype: None
        """
        if value or type(value) is bool:
            dictionary[key] = value
        else:
            dictionary[key] = None
        return None

    def is_valid(self):
        """
        Determines if the object is valid.
        :return: Returns true/false along with the error message (if any).
        :rtype: tuple(boolean, dict)
        """

        return (False, {"initialization set to false."})
