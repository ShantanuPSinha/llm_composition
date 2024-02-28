import json, sys, os, re
from openai import OpenAI
from collections import Counter


file_path = "/home/shantanu/duality/Xtractor/temp/rfixer_output/.temp_sols.ndjson"
dir_path = "/home/shantanu/duality/Xtractor/temp/rfixer_output"

# Extract all text files in dir_path
def get_files_in_dir(dir_path):
    files = []
    try:
        for file in os.listdir(dir_path):
            if file.endswith(".txt"):
                files.append(file)
    except FileNotFoundError:
        print(f"Error: Directory not found - {dir_path}")
    except Exception as e:
        print(f"Error: {e}")
    return files

# Filter files based on file_id in data_dict
def filter_files(data_dict, files):
    filtered_files = []
    for file in files:
        file_id = int(file.split(".")[0])
        if file_id in data_dict and data_dict[file_id] not in ["TIMEOUT", "NO_SOL"]:
            filtered_files.append(file)
    return filtered_files

def load_ndjson_as_dict(file_path):
    data_dict = {}
    try:
        with open(file_path, 'r') as file:
            for line in file:
                try:
                    json_obj = json.loads(line)
                    file_id = json_obj.get("file_id")
                    solution = json_obj.get("solution", "NO_SOL")
                    data_dict[file_id] = solution
                except json.JSONDecodeError:
                    print(f"Warning: Could not parse line as JSON: {line}")
                except KeyError:
                    print(f"Warning: Key not found in line: {line}")
    except FileNotFoundError:
        print(f"Error: File not found - {file_path}")
    except Exception as e:
        print(f"Error: {e}")
    return data_dict

def parse_file(file_path):
    with open(file_path, 'r') as file:
        input_text = file.read()

    parts = input_text.split('---')
    positive_part = parts[0].split('+++')[1] if '+++' in parts[0] else ''
    negative_part = parts[1] if len(parts) > 1 else ''

    positive_examples = positive_part.strip().split('\n')
    negative_examples = negative_part.strip().split('\n')

    return positive_examples, negative_examples

def generate_prompt(file):
    file_path = os.path.join(dir_path, file)
    positive_examples, negative_examples = parse_file(file_path)

    if len(positive_examples) > 100 or len(negative_examples) > 100:
        return None

    prompt = f"Act as a Software Engineer. Create a regular expression in Python that matches strings with a pattern similar to the examples: {positive_examples}. The regular expression should exclude strings with a pattern similar to the examples: {negative_examples}. I need to parse your response with a program, so please include your final solution regex with these tags -> ##<Regex>##. Make the regular expression generalizable to similar strings. Use Python to test that the Regex matches the positive examples and does not match the negative examples."
    return prompt

def query_gpt(prompt):
    client = OpenAI(
        api_key=os.environ.get("OPENAI_API_KEY"),
    )

    completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        model="gpt-4-turbo-preview",
    )

    return completion.choices[0].message.content


def begin_query ():
    existing_file_ids = set()
    if os.path.exists("gpt_output.ndjson"):
        with open("gpt_output.ndjson", "r") as infile:
            for line in infile:
                data = json.loads(line)
                existing_file_ids.add(data["file_id"])

    data_dict = load_ndjson_as_dict(file_path)
    files = get_files_in_dir(dir_path)
    filtered_files = filter_files(data_dict, files)

    skip_count = 0

    with open("gpt_output.ndjson", "a") as ofile:
        for file_name in filtered_files:
            file_id = int(file_name.split(".")[0])

            if file_id in existing_file_ids:
                continue

            prompt = generate_prompt(file_name)

            if prompt is None:
                skip_count += 1
                continue

            print(f"Processing file: {file_id:05}")
            
            try:
                response = query_gpt(prompt)
                ofile.write(json.dumps({"file_id": file_id, "GPT-response": response, "RFixer_Sol": data_dict.get(file_id, "NO_SOL")}) + "\n")
            except Exception as e:
                print (f"Error: {e}")

def filter_unique_strings(input_list):
    counts = Counter(input_list)
    unique_strings = [item for item in input_list if counts[item] == 1]
    return unique_strings


def remove_python_code_blocks(text):
    pattern = r"```python.*?```"
    
    cleaned_text = re.sub(pattern, '', text, flags=re.DOTALL)
    return cleaned_text


def extract_between_tags(text):
    text = remove_python_code_blocks(text)
    pattern_closed = r"##<Regex>##(.*?)##</Regex>##"
    matches_closed = re.findall(pattern_closed, text, re.DOTALL)    
    
    if len(matches_closed) > 0:
        return filter_unique_strings(matches_closed)

    pattern_open = r"(?:##<REGEX>##)(.*?)(?=##<REGEX>##)"
    matches_open = re.findall(pattern_open, text, re.DOTALL)
    
    return filter_unique_strings(matches_open)


def clean_query():
    gpt_output = []
    cnt = 0
    with open("gpt_output.ndjson", "r") as infile:
        for line in infile:
            data = json.loads(line)
            file_id = data["file_id"]
            gpt_response = extract_between_tags(data["GPT-response"])

            if len (gpt_response) == 1:
                gpt_response = gpt_response[0]
            elif len (gpt_response) == 0:
                gpt_response = None
                cnt += 1
            else:

                print (f"Error: Multiple regex found for file_id: {file_id}, GPT Response: {gpt_response}")

            gpt_output.append({"file_id": file_id, "GPT-response": gpt_response})

    with open("gpt_output_clean.ndjson", "w") as ofile:
        for data in gpt_output:
            ofile.write(json.dumps(data) + "\n")

    print (f"Total files with no solution: {cnt}")

    

    

if __name__ == "__main__":
    #begin_query()
    clean_query()