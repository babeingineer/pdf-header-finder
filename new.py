import fitz  # PyMuPDF
import json
import os

output_folder = "output_directory"
if not os.path.exists(output_folder):
        os.makedirs(output_folder)

# Open the PDF
doc = fitz.open('./data/f.pdf')

def get_main_font(line):
    font_dict = {}
    for span in line["spans"]:
        if str(span["font"]) + ' ' +  str(span["size"]) in font_dict:
            font_dict[str(span["font"]) + ' ' + str(span["size"])] += len(span["text"])
        else:
            font_dict[str(span["font"]) + ' ' + str(span["size"])] = len(span["text"])
    return sorted(font_dict.items(), key=lambda item: -item[1])[0][0].split()


# Loop through every page

data = []

for i in range(len(doc)):
    page = doc[i]
    page_width = page.rect.width
    page_height = page.rect.height
    annotations = page.annots()
    highlights = []
    for annotation in annotations:
        if annotation.type[1] == 'Highlight':
            highlights.append(annotation)

    images = page.get_images(full=True)

    image_bboxes = []
    image_count = 0
    for img in images:
        image_count += 1
        base_image = doc.extract_image(img[0])
        image_bytes = base_image["image"]

        image_filename = f"image_{i + 1}_{image_count}.png"
        image_filepath = os.path.join(output_folder, image_filename)

        with open(image_filepath, "wb") as img_file:
            img_file.write(image_bytes)

        image_bbox = page.get_image_bbox(img[-3])

        image_bboxes.append([image_bbox, image_filepath])

    
    structure = page.get_text("dict") 
    for block in structure["blocks"]:
        
        prevlen = len(data)
        if "lines" in block:
            for index, line in enumerate(block["lines"]):
                is_highlighted = 0
                comment = ""
                content = []
                for annotation in highlights:
                    r = fitz.Rect(line["bbox"])
                    if r.intersects(annotation.rect):
                        is_highlighted = 1
                        comment = annotation.info["content"]
                main_font = get_main_font(line)
                for span in line["spans"]:
                    content.append(span["text"])
                paragraph = {}
                paragraph["text"] = " ".join(content)
                paragraph["font_name"] = main_font[0]
                paragraph["font_size"] = round(float(main_font[1]))
                if is_highlighted:
                    paragraph["comment"] = comment
                if "wave with an amplitude" in paragraph["text"]:
                    a = 0
                
                # if len(data) > prevlen and len(data[-1]["text"]) < 5:
                j = 0
                k = 0
                paragraph["img"] = []
                while k <= index:
                    if fitz.Rect(block["lines"][k]["bbox"]).y1 < page_height / 5 * 4:
                        break
                    k += 1
                if not (k == index + 1):
                    while j < len(image_bboxes):
                        if fitz.Rect(line["bbox"]).y1 > image_bboxes[j][0].y0:
                            paragraph["img"].append(image_bboxes[j][1])
                            image_bboxes.pop(j)
                        else:
                            j += 1
                
                if len(data) == 0:
                    data.append(paragraph)
                elif ("comment" in data[-1] and "comment" in paragraph and paragraph["comment"] == data[-1]["comment"]) or data[-1]["font_name"] == paragraph["font_name"] and data[-1]["font_size"] == paragraph["font_size"] or len(paragraph["text"]) < 5:
                    data[-1]["text"] += " " + paragraph["text"]
                    if is_highlighted:
                        data[-1]["comment"] = comment
                    if not "img" in data[-1]:
                        data[-1]["img"] = []
                    data[-1]["img"] += paragraph["img"]
                else:
                    data.append(paragraph)
    
    for j in range(len(image_bboxes)):
        if not "img" in data[-1]:
            data[-1]["img"] = []
        data[-1]["img"].append(image_bboxes[j][1])


# fonts = {}
# for i in range(0, len(data)):
#     if "bold" in data[i]["font_name"].lower():
#         key = data[i]["font_name"] + ' ' + str(data[i]["font_size"])
#         if key in fonts:
#             fonts[key] += 1
#         else:
#             fonts[key] = 1

# sorted_fonts = sorted(fonts.items(), key=lambda item: -item[1])

# maintopic_font_name, maintopic_font_size = sorted_fonts[2]
# subtopic_font_name, subtopic_font_size = sorted_fonts[1]


res = []

for i in range(0, len(data)):
    if "comment" in data[i]:
        subtopic_index = 0
        maintopic_index = 0
        for j in range(i - 1, -1, -1):
            if "bold" in data[j]["font_name"].lower() and data[j]["font_size"] >= data[i]["font_size"]:
                subtopic_index = j
                break
        for k in range(j - 1, -1, -1):
            if "bold" in data[k]["font_name"].lower() and data[k]["font_size"] > data[j]["font_size"]:
                maintopic_index = k
                break
        res.append({"following": i + 1, "text": data[i]["text"], "comment": data[i]["comment"], "img": data[i]["img"], "subtopic": data[subtopic_index]["text"], "maintopic": data[maintopic_index]["text"]})
        
print(res)

output = open("output__.json", "w", encoding="utf8")
output.write(json.dumps(data, indent=4))


import sqlite3
conn = sqlite3.connect("output.db")
cursor = conn.cursor()
create_table_paragraph_sql = """
CREATE TABLE IF NOT EXISTS paragraphs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT,
    font_name TEXT,
    font_size INTEGER,
    img TEXT,
    comment TEXT
)
""" 

create_table_highlight_sql = """
CREATE TABLE IF NOT EXISTS highlights (
    id INTEGER PRIMARY KEY,
    text TEXT,
    subtopic TEXT,
    maintopic TEXT,
    img TEXT,
    comment TEXT
)
""" 

cursor.execute(create_table_paragraph_sql)
cursor.execute(create_table_highlight_sql)

for i in range(len(data)):
    cursor.execute("""
        INSERT INTO paragraphs (id, text, font_name, font_size, img, comment)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (i, data[i]["text"], data[i]["font_name"], data[i]["font_size"], data[i]["img"][0] if len(data[i]["img"]) else "", data[i]["comment"] if "comment" in data[i] else ""))

for i in range(len(res)):
    cursor.execute("""
            INSERT INTO highlights (text, maintopic, subtopic, img, comment)
            VALUES (?, ?, ?, ?, ?)
        """, (res[i]["text"], res[i]["maintopic"], res[i]["subtopic"], res[i]["img"][0] if len(res[i]["img"]) else "", res[i]["comment"]))

conn.commit()
conn.close()