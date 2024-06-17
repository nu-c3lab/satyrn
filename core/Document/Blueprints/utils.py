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

def build_metric_name(metric_aggregation: str,
                      metric_entity_name: str,
                      metric_attribute_name: str) -> str:
    return f"{metric_aggregation}_{metric_entity_name}_{metric_attribute_name}" if metric_aggregation else metric_attribute_name
