# import fitz  # PyMuPDF
# import os

# def extract_text_and_image_positions(pdf_path):
#     doc = fitz.open(pdf_path)
#     results = []

#     for page_num in range(len(doc)):
#         page = doc.load_page(page_num)
#         text_blocks = page.get_text("dict", flags=11)["blocks"]  # flags=11 for more detailed info
#         image_blocks = page.get_images(full=True)

#         # Process images
#         for img in image_blocks:
#             xref = img[-3]
#             img_bbox = page.get_image_bbox(xref)
#             if img_bbox:  # Check if image is not null
#                 # Determine image position relative to text blocks
#                 before_text = ""
#                 after_text = ""
#                 for block in text_blocks:
#                     if block["type"] == 0:  # text block
#                         block_bbox = fitz.Rect(block["bbox"])
#                         block_text = block.get("text", "")
#                         if block_bbox.y1 < img_bbox.y0:  # Text block is before image
#                             before_text = block_text
#                         elif block_bbox.y0 > img_bbox.y1 and after_text == "":  # Text block is after image
#                             after_text = block_text
#                             break  # Only need the first text block after the image

#                 results.append({
#                     "page": page_num + 1,
#                     "image_xref": xref,
#                     "before_text": before_text,
#                     "after_text": after_text
#                 })

#     doc.close()
#     return results

# # Example Usage
# pdf_file = './data/c.pdf'
# image_positions = extract_text_and_image_positions(pdf_file)

# # Output the results
# for item in image_positions:
#     print(f"Page {item['page']}, Image XREF: {item['image_xref']}")
#     print(f"Before Text: {item['before_text']}")
#     print(f"After Text: {item['after_text']}\n")

import fitz  # Import PyMuPDF
import os

def extract_images(pdf_path, output_folder):
    doc = fitz.open(pdf_path)
    image_count = 0

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    for page_num in range(len(doc)):
        page = doc[page_num]
        images = page.get_images(full=True)
        for img in images:
            xref = img[0]  # xref number
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]

            image_filename = f"image_{page_num + 1}_{image_count + 1}.png"
            image_filepath = os.path.join(output_folder, image_filename)

            with open(image_filepath, "wb") as img_file:
                img_file.write(image_bytes)

            image_count += 1


            image_bbox = page.get_image_bbox(img[-3])
            print(image_bbox, image_filepath)

    doc.close()
    return image_count

# Example Usage
pdf_file = './data/c.pdf'
output_dir = 'output_directory'
num_images = extract_images(pdf_file, output_dir)
print(f"Extracted {num_images} images.")
