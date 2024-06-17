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
import requests

class Mixtral8x7BInterface:
    def __init__(self,
                 url: str):

        self.url = url

        self.headers = {
            'Content-Type': 'application/json'
        }
        self.data = {
            "max_tokens": 4096,
            "temperature": 0.2,
            "top_p": 0.1,
            "seed": -1
        }

    def generate(self,
                 prompt: str) -> str:

        self.data["prompt"] = f"[INST] {prompt}[/INST]"

        # Making the POST request
        response = requests.post(self.url, headers=self.headers, data=json.dumps(self.data))

        # Checking if the request was successful
        if response.status_code == 200:
            # Printing the response content
            result = response.json()["choices"][0]['text']
            return result
        else:
            return ""