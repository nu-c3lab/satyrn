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
from pathlib import Path
from typing import Dict, List, Tuple

from core.RingObjects.Ring import Ring
from core.Document.Blueprints.utils import build_metric_name

class ComparativeBenchmarkBlueprint():
    """
    Produces a set of information requirements for a single entity instance.
    """
    def __init__(self,
                 entity_name: str,
                 entity_instance_identifier_attribute_name: str,
                 entity_instance_identifier_value: str,
                 entity_reference: str,
                 metric_entity_name: str,
                 metric_attribute_name: str,
                 metric_aggregation: str,
                 comparison_set_filter: Dict[str, str],
                 metric_sort_direction: str,
                 metric_preference_direction: str,
                 benchmark_target: float,
                 ring: Ring):
        super().__init__()
        self.entity_name = entity_name
        self.entity_instance_identifier_attribute_name = entity_instance_identifier_attribute_name
        self.entity_instance_identifier_value = entity_instance_identifier_value
        self.entity_reference = entity_reference
        self.metric_entity_name = metric_entity_name
        self.metric_attribute_name = metric_attribute_name
        self.metric_aggregation = metric_aggregation

        self.comparison_set_filter = comparison_set_filter

        self.metric_sort_direction = metric_sort_direction
        self.metric_preference_direction = metric_preference_direction
        self.benchmark_target = benchmark_target

        self.ring = ring

        # Read in the JSON file of info_requirements.json
        p = Path(__file__).with_name('base_plan_templates.json')
        with p.open('r') as f:
            self.base_plan_templates = json.load(f)

        # Generate / retrieve some useful information about the entity and metric
        self.metric_name = build_metric_name(self.metric_aggregation, self.metric_entity_name, self.metric_attribute_name)
        self.metric_access_plan, self.metric_nicename = self.get_metric_access_plan_and_nicename(self.metric_name)
        self.entity_access_plan = self.get_entity_access_plan()
        self.instance_filter = self.get_instance_filter()
        self.not_instance_filter = self.get_not_instance_filter()

        self.requirements = {}

    def get_plan_composition_specs(self) -> List[Dict]:
        """

        :return: A list of dictionaries, each of which contains keys for "base_plan", "access_plan", "access_plan_filters", and "slot_fillers".
        :rtype: List of dictionaries
        """

        composition_specs = []

        # Get the metric value for the entity instance
        composition_specs.append(self.get_metric_value_for_entity_instance())

        # Figure out if the entity instance's value is greater than the target benchmark value
        composition_specs.append(self.is_instance_metric_greater_than_benchmark_target())

        # Compute the min, max, average, median, and standard deviation the specified metric for all entities being compared
        composition_specs.append(self.get_aggregated_value_of_metric('min'))
        composition_specs.append(self.get_aggregated_value_of_metric('max'))

        composition_specs.append(self.get_aggregated_value_of_metric('median'))
        composition_specs.append(self.get_is_instance_metric_greater_than_aggregated_metric_for_others('median'))

        composition_specs.append(self.get_aggregated_value_of_metric('average'))
        composition_specs.append(self.get_is_instance_metric_greater_than_aggregated_metric_for_others('average'))

        composition_specs.append(self.get_aggregated_value_of_metric('stddev'))

        return composition_specs

    def get_entity_access_plan(self) -> Dict:
        # Get the ring entity
        ring_entity = [ent for ent in self.ring.entities if ent.name == self.entity_name][0]

        # Get the attribute from the ring
        ring_attribute = ring_entity.attributes[self.metric_name]

        # Return the access plan for that attribute
        return ring_attribute.access_plan

    def get_metric_access_plan_and_nicename(self,
                                            metric_name: str) -> Tuple[Dict, str]:
        # Get the ring entity
        ring_entity = [ent for ent in self.ring.entities if ent.name == self.entity_name][0]

        # Get the attribute from the ring
        ring_attribute = ring_entity.attributes[metric_name]

        # Get the nicename for the metric
        metric_nicename = ring_attribute.nicename[0]

        # Return the access plan for that attribute
        return ring_attribute.access_plan, metric_nicename

    def get_instance_filter(self) -> Dict:
        return {
            "|1|": f"(retrieve_entity {self.entity_name})",
            "|2|": f"(retrieve_attribute |1| {self.entity_instance_identifier_attribute_name})",
            "|3|": f"(exact |2| \"{self.entity_instance_identifier_value}\")",
        }

    def get_not_instance_filter(self) -> Dict:
        return {
            "|1|": f"(retrieve_entity {self.entity_name})",
            "|2|": f"(retrieve_attribute |1| {self.entity_instance_identifier_attribute_name})",
            "|3|": f"(exact |2| \"{self.entity_instance_identifier_value}\")",
            "|4|": f"(not |3|)"
        }

    def get_metric_value_for_entity_instance(self) -> Dict:
        """

        :return:
        :rtype:
        """
        return {
            "plan_name": "InstanceMetricValue",
            "base_plan": self.base_plan_templates["InstanceMetricValue"],
            "access_plans": {
                "|A|": {
                    "access_plan": self.metric_access_plan,
                    "access_plan_filters": {
                        "filters": [self.comparison_set_filter],
                        "filter_joiner": None
                    }
                }
            },
            "slot_fillers": {
                "String:0": self.entity_instance_identifier_value,
                "EntityReference:0": self.entity_reference,
                "Filter:0": ""
            }
        }

    def is_instance_metric_greater_than_benchmark_target(self) -> Dict:
        """

        :return:
        :rtype:
        """
        plan = "InstanceGreaterThanQuantity" if self.get_target_range() == '+inf' else "InstanceLessThanQuantity"
        return {
            "plan_name": plan,
            "base_plan": self.base_plan_templates[plan],
            "access_plans": {
                "|A|": {
                    "access_plan": self.metric_access_plan,
                    "access_plan_filters": {
                        "filters": [self.comparison_set_filter],
                        "filter_joiner": None
                    }
                }
            },
            "slot_fillers": {
                "String:0": self.entity_instance_identifier_value,
                "EntityReference:0": self.entity_reference,
                "Quantity:0": self.benchmark_target
            }
        }

    def get_aggregated_value_of_metric(self,
                                       aggregation: str) -> Dict:
        """

        :return:
        :rtype:
        """
        return {
            "plan_name": "AggregateMetric",
            "base_plan": self.base_plan_templates["AggregateMetric"],
            "access_plans": {
                "|A|": {
                    "access_plan": self.metric_access_plan,
                    "access_plan_filters": {
                        "filters": [self.comparison_set_filter, self.not_instance_filter],
                        "filter_joiner": "and"
                    }
                }
            },
            "slot_fillers": {
                "Analysis:0": aggregation,
                "Filter:0": ""
            }
        }

    def get_is_instance_metric_greater_than_aggregated_metric_for_others(self,
                                                                         aggregation: str) -> Dict:
        """

        :return:
        :rtype:
        """
        plan = "InstanceGreaterThanAggregatedMetric" if self.get_target_range() == '+inf' else "InstanceLessThanAggregatedMetric"
        return {
            "plan_name": plan,
            "base_plan": self.base_plan_templates[plan],
            "access_plans": {
                "|A|": {
                    "access_plan": self.metric_access_plan,
                    "access_plan_filters": {
                        "filters": [self.comparison_set_filter, self.not_instance_filter],
                        "filter_joiner": "and"
                    }
                },
                "|B|": {
                    "access_plan": self.metric_access_plan,
                    "access_plan_filters": {
                        "filters": [self.comparison_set_filter],
                        "filter_joiner": "and"
                    }
                }
            },
            "slot_fillers": {
                "Analysis:0": aggregation,
                "String:0": self.entity_instance_identifier_value,
                "EntityReference:0": self.entity_reference
            }
        }

    @staticmethod
    def parse(utterance, feature_extractor):
        return feature_extractor.extract_entity_instance(utterance)

    def get_target_range(self):
        return self.metric_preference_direction or self.ring.get_entity_by_name(self.metric_entity_name).metrics[self.metric_attribute_name][0]

    def build_baseline_prompt(self,
                              entity_reference: str,
                              filter_statement: str) -> str:
        prompt = f"Generate a report for {entity_reference} comparing it to the target benchmark for {self.metric_nicename}{' ' + filter_statement if filter_statement else ''}. " \
                 f"The target benchmark value is {self.benchmark_target}. " \
                 f"It is better to be {'higher' if self.metric_preference_direction == '+inf' else 'lower'} than the target benchmark value."
        return prompt

    def build_prompting_instructions(self) -> str:
        return f"The audience is educated, but may not understand technical terms. " \
               f"Please use natural sounding language and try to find more natural terms for the groups that are mentioned."

    def build_baseline_prompt_with_facts(self,
                                         entity_reference: str,
                                         filter_statement: str,
                                         factual_statements: List[str]) -> str:
        prompt = "Context:\n{}".format('\n'.join(factual_statements))
        prompt += "\n\n" + self.build_baseline_prompt(entity_reference, filter_statement)
        prompt += " Use only the facts provided in the context. "
        prompt += self.build_prompting_instructions()
        return prompt

    def build_baseline_prompt_with_info_reqs(self,
                                             entity_reference: str,
                                             filter_statement: str) -> str:
        prompt = self.build_baseline_prompt(entity_reference, filter_statement)
        prompt += f" The metric is {self.metric_nicename}. " \
                  f"In the report, include information about the value of the metric for {entity_reference}, " \
                  f"whether or not the metric value for {entity_reference} is greater than the target benchmark value, " \
                  f"what the minimum value of the metric is, "\
                  f"what the maximum value of the metric is, " \
                  f"what the median value of the metric is, " \
                  f"whether or not the metric value for {entity_reference} is greater than the median value of the metric, " \
                  f"what the average value of the metric is, " \
                  f"whether or not the metric value for {entity_reference} is greater than the average value of the metric, " \
                  f"and what the standard deviation is for the metric."
        prompt += "\n\n" + self.build_prompting_instructions()
        return prompt
