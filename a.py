import json

input = open("merged_paragraphs.json", encoding="utf8")
output = open("output_.json", "w", encoding="utf8")

input_data = json.loads(input.read())

merge_data = []
for i in range(len(input_data)):
    if len(merge_data) == 0:
        merge_data.append(input_data[i])
        continue
    last = merge_data[len(merge_data) - 1]
    if input_data[i]["font_name"] == last["font_name"] and input_data[i]["font_size"] == last["font_size"] and input_data[i]["boldness"] == last["boldness"]:
        last["text"] += input_data[i]["text"]
    else:
        merge_data.append(input_data[i])

header = {}
content = {}

for block in merge_data:
    temp = block.copy()
    temp.pop("text")
    temp = json.dumps(temp)
    if block["boldness"] == True:
        if temp in header:
            header[temp] += 1
        else:
            header[temp] = 1
    else:
        if temp in content:
            content[temp] += 1
        else:
            content[temp] = 1



header = dict(sorted(header.items(), key=lambda item: (-item[1], -json.loads(item[0])["font_size"])))
content = dict(sorted(content.items(), key=lambda item: (-item[1])))
print(header)
print(json.loads(list(content.keys())[0]))

subtopic_font = json.loads(list(header.keys())[1])
maintopic_font = json.loads(list(header.keys())[2])

print(subtopic_font)
print(maintopic_font)

result = []
for block in merge_data:
    # Check if the block is bold
    if block["boldness"]:
        # Check if result is not empty
        if block["font_size"] == maintopic_font["font_size"] and block["font_name"] == maintopic_font["font_name"]:
            result.append({"title": block, "subtopic": [], "content": []})
            continue

        if not result:
            continue
        last_topic = result[-1]

        # Check if the block is a subtopic
        if block["font_size"] == subtopic_font["font_size"] and block["font_name"] == subtopic_font["font_name"]:
            last_topic["subtopic"].append({"title": block, "content": []})
            continue

    # Check if result is not empty
    if not result:
        continue

    last_topic = result[-1]

    # Check if there are any subtopics
    if not last_topic["subtopic"]:
        last_topic["content"].append(block)
        continue

    last_subtopic = last_topic["subtopic"][-1]

    # Append the block to the content of the last subtopic
    last_subtopic["content"].append(block)


output.write(json.dumps(result, indent=4))