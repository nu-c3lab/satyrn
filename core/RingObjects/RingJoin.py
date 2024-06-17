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

from .RingObject import RingObject

class RingJoin(RingObject):

    def __init__(self):

        # Set default values
        self.bidirectional = False

        # Initialize other properties
        self.name = None
        self.from_ = None
        self.to = None
        self.path = None

        self.error_set = set()

    def parse(self,
              join_config: dict) -> None:
        self.name = join_config.get('name')
        self.from_ = join_config.get('from')
        self.to = join_config.get('to')
        self.path = join_config.get('path')
        self.bidirectional = join_config.get('bidirectional')

    def construct(self):
        join = {}
        self.safe_insert('name', self.name, join)
        self.safe_insert('from', self.from_, join)
        self.safe_insert('to', self.to, join)
        self.safe_insert('path', self.path, join)
        self.safe_insert('bidirectional', self.bidirectional, join)
        return join

    def is_valid(self):
        if self.name == None:
            self.error_set.add("Ring Join 'name' is missing.")
        if self.from_ == None:
            self.error_set.add("Ring Join 'from_' is missing.")
        if self.to == None:
            self.error_set.add("Ring Join 'to' is missing.")
        if self.path == None:
             self.error_set.add("Ring Join 'path' is missing.")

        if len(self.error_set) == 0:
            return (True, {})
        else:
            ## will return a string of errors
            errorString = ' '.join(self.error_set)
            return (False, errorString)
