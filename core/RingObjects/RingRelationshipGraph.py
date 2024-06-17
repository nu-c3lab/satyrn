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

import networkx as nx

class RingRelationshipGraph(object):

    def __init__(self, graph=None):
        # Set default values
        self.graph = graph if graph else nx.Graph()

    def get_path(self, entity_a, entity_b):
        node_path = nx.dijkstra_path(self.graph, entity_a, entity_b)
        return [self.graph[node_pair[0]][node_pair[1]]['relationship'] for node_pair in zip(node_path[:-1], node_path[1:])]