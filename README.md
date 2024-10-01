# Satyrn API

This is the core codebase for the Satyrn API. Satyrn is developed by [anonymous]. Details about this work are pending publication.

### License

This file is part of Satyrn.
Satyrn is free software: you can redistribute it and/or modify it under 
the terms of the GNU General Public License as published by the Free Software Foundation, 
either version 3 of the License, or (at your option) any later version.
Satyrn is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; 
without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. 
See the GNU General Public License for more details.
You should have received a copy of the GNU General Public License along with Satyrn. 
If not, see <https://www.gnu.org/licenses/>.

-----------

# Satyrn API: Getting Set Up
## Prerequisites
1. Install [Conda](https://conda.io/projects/conda/en/latest/user-guide/install/index.html).

2. Clone this repo to a place of your choosing.


## Setting up the app environment + Running the App
1. cd into the repo directory, create a Conda virtual environment, and load it up. Something like:
```bash
cd satyrn-api
conda create --name satyrn python=3.8
conda activate satyrn
```

2. Pip install the requirements.txt file into that virtual env
```bash
pip install -r requirements.txt
```
If you receive an error while attempting to install `psycopg2`, install it using `conda install psycopg2`, then re-run the requirements installation command above.

3. Follow the instructions in the [env-example.txt](env-example.txt) and get those in your env however you see fit (~/.profile or something context based -- for Mac/Linux users, this rules: [direnv.net](https://direnv.net)).

IMPORTANT: These environment variables must be loaded into your terminal/env whenever you run the Satyrn API. If you do not set up an automated method for loading these environment variables, you'll need to manually add them each time start a new terminal session.

4. To ensure that Satyrn has data to query and analyze, you'll need to make sure it has access to a ring. There are a variety of rings available in the [satyrn-rings](satyrn-rings/) repo.
To set up the ring, you'll need to make sure the `connectionString` variable is set to the full qualified path to the database. For a local, SQLite database, this will simply be the absolute path to the database on your computer. For remote databases, this will be the connection string with any required credentials.

5. Add the absolute path of one or more rings to the `rings` list in `site.json`.

6. Now start the server. From the top level directory of satyrn-api, run:
```bash
python wsgi.py
```
If you receive an error while loading SQLIte extensions, you may need to comment out `dbapi_conn.load_extension(file_name)` (line 61 of core/RingObjects/RingDataSource.py). This error typically occurs on Macs with M-series chips.

7. To test your setup, you'll need [Postman](https://www.postman.com/downloads/) or equivalent to send requests. Assuming you have the air-quality ring loaded, you can send a `GET` request to `http://127.0.0.1:5000/api/generate_report/Toxic-3418-r4hu-4289-38jd93k29s/1/` with the following JSON body:
```json
{
    "entity_name": "State",
    "entity_instance_identifier_attribute_name": "name",
    "entity_instance_identifier_value": "Oregon",

    "metric_entity_name": "Wildfire",
    "metric_attribute_name": "fire_size",
    "metric_aggregation": "median",
    "metric_preference_direction": "-inf",
    "metric_sort_direction": "desc",
    "metric_set_filter": {
        "|1|": "(retrieve_entity Wildfire)",
        "|2|": "(retrieve_attribute |1| fire_size)",
        "|3|": "(greaterthan_eq |2| 50)"
    },

    "time_attribute_name": "year",
    "time_zero": 2003,
    "time_one": 2008,
    "report_type": "TimeOverTimeBlueprint",

    "statement_generation_method": "template",
    "prompt_type": "baseline_with_facts",
    "llm": "gpt4"
}
```

If you see results, then the Satyrn API is set up!

## API Spec

The API currently supports the following primary views:

1. __/api/__

This is just a basic health check to see if the API is running.

2. __/api/rings/__

This call will return the rings (and the versions) loaded into memory at the current api instance. It should closely mirror the rings that are listed in the `site.json` file that the site utilizes.

3. __/api/sqr_analysis/<ring_id>/1/__

This endpoint takes SQR plans in the body of the request (as JSON) and executes them with the analytics engine.

### SQR Plans and Running Analysis
As part of our platform, we are developing an intermediate representation between language and queries in order to make 
this process easier called the Structured Question Representation (SQR, pronounced seeker). The purpose of this representation
is to be a data and execution agnostic meaning representation for complex, analytic questions. It is a 
graph-based representation that specifies an ordered series of steps to carry out in pursuit of an answer to a 
user’s question. Each node of the graph represents an operation whose output is fed to later steps which require the 
results. In this way, arbitrarily complex plans can be composed to satisfy any information needs of a user. 
This representation can also be easily converted to statements which describe the plan in plain language.
Our platform currently makes use of this representation when generating queries against relational databases, but 
it is possible to use this as a base representation for building SPARQL queries against knowledge graphs as well.

Here is an example of this representation for a question asking "What was the average wildfire size of each state in 2020?":

```json
{
    "|1|": "(retrieve_entity State)",
    "|2|": "(retrieve_entity Wildfire)",
    "|3|": "(retrieve_attribute |1| name)",
    "|4|": "(retrieve_attribute |2| fire_size)",
    "|5|": "(groupby |3|)",
    "|6|": "(average |4| |5|)",
    "|7|": "(retrieve_attribute |2| year)",
    "|8|": "(exact |7| 2020)",
    "|9|": "(collect |3| |6|)",
    "|10|": "(return |9| |8|)"
}
```

## Datasets
The datasets used for testing Satyrn are publicly available and can be accessed [here](https://drive.google.com/file/d/1uDVRPzF1oDa-AqUmr4Trc3KNXhthrlL6/view?usp=share_link).

## Citation
If you found this work useful, please consider citing us:
```bibtex
@article{sterbentz2024satyrn,
  title={Satyrn: A Platform for Analytics Augmented Generation},
  author={Sterbentz, Marko and Barrie, Cameron and Shahi, Shubham and Dutta, Abhratanu and Hooshmand, Donna and Pack, Harper and Hammond, Kristian J},
  journal={arXiv preprint arXiv:2406.12069},
  year={2024}
}
```
