import pandas as pd
import sqlite3, json

gpt_responses_path = '/home/shantanu/duality/llm_composition/GPT_Responses_Tested.ndjson'
secondary_database_path = '/home/shantanu/duality/Xtractor/temp/rfixer_solutions.ndjson'
updated_database_path = './db.ndjson'
sqlite_db_path = './composition_regexes.db'

def read_ndjson_file(file_path):
    """
    Reads an NDJSON file and returns a list of dictionaries.

    :param file_path: Path to the NDJSON file.
    :return: A list of dictionaries, where each dictionary represents a JSON object from the file.
    """
    data = []
    with open(file_path, 'r') as file:
        for line in file:
            try:
                json_object = json.loads(line)
                data.append(json_object)
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON: {e}")
    return data

def read_and_update_ndjson_file(file_path, updated_file_path):
    """
    Reads an NDJSON file, ensures that every entry has 'RFixer-Solution' and 'GPT-response' fields,
    and writes the updated entries to a new NDJSON file.

    :param file_path: Path to the original NDJSON file.
    :param updated_file_path: Path to the updated NDJSON file with default values added.
    """
    updated_data = []
    with open(file_path, 'r') as file:
        for line in file:
            try:
                entry = json.loads(line)
                # Ensure 'RFixer-Solution' and 'GPT-response' exist in the entry, add them with None as default if missing
                if 'RFixer-Solution' not in entry:
                    entry['RFixer-Solution'] = None
                if 'GPT-response' not in entry:
                    entry['GPT-response'] = None
                updated_data.append(entry)
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON: {e}")

    # Write the updated entries to a new NDJSON file
    with open(updated_file_path, 'w') as file:
        for entry in updated_data:
            json_line = json.dumps(entry)
            file.write(f"{json_line}\n")


def update_secondary_database(gpt_responses_path, secondary_database_path, updated_database_path):
    # Read both NDJSON files
    gpt_responses = read_ndjson_file(gpt_responses_path)
    secondary_database = read_ndjson_file(secondary_database_path)

    # Convert secondary database to a dict for easier access by id
    secondary_dict = {entry['id']: entry for entry in secondary_database}

    # Update secondary database entries with GPT response where pass = true
    for response in gpt_responses:
        if response['pass'] and response['file_id'] in secondary_dict:
            # Append GPT response to the matching secondary database entry
            secondary_dict[response['file_id']]['GPT-response'] = response['GPT-response']

    # Convert the updated dict back to a list
    updated_secondary_database = list(secondary_dict.values())

    # Write the updated list back to an NDJSON file
    with open(updated_database_path, 'w') as file:
        for entry in updated_secondary_database:
            json_line = json.dumps(entry)
            file.write(f"{json_line}\n")





update_secondary_database(gpt_responses_path, secondary_database_path, updated_database_path)
read_and_update_ndjson_file(updated_database_path, updated_database_path)



# Connect to your SQLite database
conn = sqlite3.connect(sqlite_db_path)
cursor = conn.cursor()

# Create the table
cursor.execute('''
CREATE TABLE IF NOT EXISTS regex_data (
    id INTEGER PRIMARY KEY,
    regex TEXT,
    positive_inputs TEXT,  -- Storing lists as JSON strings
    negative_inputs TEXT,  -- Storing lists as JSON strings
    file_path TEXT,
    RFixer_Solution TEXT,
    GPT_response TEXT
)
''')

# Function to read and insert NDJSON data into the SQLite table
def insert_data_from_ndjson(file_path):
    with open(file_path, 'r') as file:
        for line in file:
            data = json.loads(line)
            # Convert lists to JSON strings
            positive_inputs_str = json.dumps(data.get('positive_inputs', []))
            negative_inputs_str = json.dumps(data.get('negative_inputs', []))
            # Insert data into the table
            cursor.execute('''
            INSERT INTO regex_data (id, regex, positive_inputs, negative_inputs, file_path, RFixer_Solution, GPT_response)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                data['id'],
                data['regex'],
                positive_inputs_str,
                negative_inputs_str,
                data['file_path'],
                data.get('RFixer-Solution'),  # Use .get() to handle possible None values
                data.get('GPT-response')      # Use .get() to handle possible None values
            ))

insert_data_from_ndjson(updated_database_path)

conn.commit()
conn.close()
