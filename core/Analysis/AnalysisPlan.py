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

import json
import networkx as nx
import matplotlib.pyplot as plt
from typing import Dict, List

from core.Analysis.AnalysisStep import AnalysisStep
from core.Analysis.AnalysisSubplan import AnalysisSubplan

class AnalysisPlan:
    def __init__(self,
                 plan_steps: Dict[str, AnalysisStep],
                 plan_graph: nx.DiGraph,
                 subplans: Dict[str, AnalysisSubplan]):
        self.plan_steps = plan_steps
        self.plan_graph = plan_graph
        self.subplans = subplans


    def display_graph(self) -> None:
        for layer, nodes in enumerate(nx.topological_generations(self.plan_graph)):
            # `multipartite_layout` expects the layer as a node attribute, so add the
            # numeric layer value as a node attribute
            for node in nodes:
                self.plan_graph.nodes[node]["layer"] = layer

        # Compute the multipartite_layout using the "layer" node attribute
        pos = nx.multipartite_layout(self.plan_graph, subset_key="layer")
        nx.draw_networkx(self.plan_graph, pos=pos, node_size=500, node_color='red', font_color='white')
        plt.show()
        return None

    def __repr__(self):
        return json.dumps({step_num : step.__repr__() for step_num, step in self.plan_steps.items()})

    def __str__(self):
        return self.__repr__()

    def to_json(self):
        return {step_num : step.__repr__() for step_num, step in self.plan_steps.items()}

    def get_leaves(self) -> List[str]:
        """
        Get the leaf nodes of the plan graph.
        :return: A list of step references (e.g. ['|7|']).
        :rtype: list of str
        """
        return [node for node in self.plan_graph.nodes if self.plan_graph.out_degree(node) == 0]
