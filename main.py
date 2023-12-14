import pdfplumber
import json
import math
import re
from thefuzz import fuzz
import os
from split import split_risks, split_objectives
import requests

offset = 3


def is_primarily_chinese(text: str) -> bool:
    chinese_characters = len(re.findall(r"[\u4e00-\u9fff]", text))
    return chinese_characters > 0


class PDFTextExtractor:
    def __init__(self, file_path, delta=10):
        self.file_path = file_path
        self.delta = delta
        self.pdf = pdfplumber.open(file_path)

    def extract_font_name(self, s: str) -> str:
        match = re.search(r"[a-zA-Z0-9-]+$", s)
        if match:
            return match.group(0)
        return ""

    def detect_header_footer_height(self):
        pdf = self.pdf
        if len(pdf.pages) <= 2:
            print("There is no enough pages!")
            return

        all_page_words = []
        even_page_words = []
        min_even_page_words_count = math.inf
        min_words_count = math.inf
        page_height = 0
        for i, page in enumerate(pdf.pages):
            page_height = page.height
            words = page.extract_words(
                x_tolerance=1,
                keep_blank_chars=False,
                use_text_flow=True,
                extra_attrs=["fontname", "size"],
            )
            if i % 2 == 1:
                even_page_words.append(words)
                if len(words) < min_even_page_words_count:
                    min_even_page_words_count = len(words)
            all_page_words.append(words)
            if len(words) < min_words_count:
                min_words_count = len(words)
        all_page_words = all_page_words[1:]
        even_page_words = all_page_words

        header_height = 0
        footer_height = 0
        max_header_height = page.height / 2
        max_footer_height = page.height / 2
        # print("trying with even pages...")
        if len(even_page_words) <= 1:
            print("There is no enough even pages! Skiping...")
        else:
            # Check header
            finish = False
            for i in range(min_even_page_words_count):
                candidate_word = even_page_words[0][i]
                odd_count = 0
                if candidate_word["top"] > max_header_height:
                    is_footer = True
                else:
                    is_footer = False
                for page in even_page_words[1:]:
                    current_word = page[i]
                    if (
                        current_word["text"] != candidate_word["text"]
                        and current_word["fontname"] == candidate_word["fontname"]
                    ):
                        if (
                            current_word["text"].isdigit()
                            and candidate_word["text"].isdigit()
                            and (
                                (
                                    int(current_word["text"])
                                    - int(candidate_word["text"])
                                )
                                % 2
                                == 0
                            )
                        ):
                            continue
                    if (
                        re.sub(r"\d+", "", current_word["text"])
                        != re.sub(r"\d+", "", candidate_word["text"])
                        or current_word["fontname"] != candidate_word["fontname"]
                        or abs(candidate_word["top"] - current_word["top"]) > offset
                    ):
                        finish = True
                        break
                if finish:
                    break
                if candidate_word["bottom"] > header_height and not is_footer:
                    header_height = candidate_word["bottom"]
                elif page_height - candidate_word["top"] > footer_height and is_footer:
                    footer_height = page_height - candidate_word["top"]

            # Check footer
            finish = False
            for i in range(1, min_even_page_words_count + 1):
                candidate_word = even_page_words[0][-i]
                if candidate_word["top"] < max_footer_height:
                    is_header = True
                else:
                    is_header = False
                for page in even_page_words[1:]:
                    current_word = page[-i]
                    if (
                        current_word["text"] != candidate_word["text"]
                        and current_word["fontname"] == candidate_word["fontname"]
                    ):
                        if (
                            current_word["text"].isdigit()
                            and candidate_word["text"].isdigit()
                            and (
                                (
                                    int(current_word["text"])
                                    - int(candidate_word["text"])
                                )
                                % 2
                                == 0
                            )
                        ):
                            continue
                    if (
                        re.sub(r"\d+", "", current_word["text"])
                        != re.sub(r"\d+", "", candidate_word["text"])
                        or current_word["fontname"] != candidate_word["fontname"]
                        or abs(candidate_word["top"] - current_word["top"]) > offset
                    ):
                        finish = True
                        break
                if finish:
                    break
                if (
                    page_height - candidate_word["top"] > footer_height
                    and not is_header
                ):
                    footer_height = page_height - candidate_word["top"]
                elif candidate_word["bottom"] > header_height and is_header:
                    header_height = candidate_word["bottom"]

        return header_height, footer_height

    def extract_text(self):
        default_offset = 8
        min_offset = 5
        max_w_offset = 20
        words = self.extract_body_words()
        paragraphs = []
        current_paragraph = [words[0]["text"]]
        font_size = words[0]["size"]
        font_name = self.extract_font_name(words[0]["fontname"])
        boldness = (
            "Bol" in words[0]["fontname"]
            or "bold" in words[0]["fontname"]
            or words[0]["ncs"] == "DeviceRGB"
            or words[0]["stroking_color"] is not None
            and 0.486 in words[0]["stroking_color"]
        )

        for i in range(1, len(words)):
            is_same_stroke = True
            if (
                words[i]["stroking_color"] is not None
                and words[i - 1]["stroking_color"] is not None
            ):
                if len(words[i]["stroking_color"]) != len(
                    words[i - 1]["stroking_color"]
                ):
                    is_same_stroke = False
                for idx, color in enumerate(words[i]["stroking_color"]):
                    if len(words[i - 1]["stroking_color"]) <= idx:
                        break
                    if color != words[i - 1]["stroking_color"][idx]:
                        is_same_stroke = False
                        break
            if (
                (
                    abs(words[i]["bottom"] - words[i - 1]["bottom"]) < min_offset
                    or (
                        default_offset
                        > abs(words[i]["bottom"] - words[i - 1]["bottom"])
                        > min_offset
                        and (
                            abs(words[i]["x1"] - words[i - 1]["x1"]) < max_w_offset
                            or words[i - 1]["x1"] > words[i]["x1"]
                        )
                        and words[i - 1]["size"] == words[i]["size"]
                    )
                )
                and self.extract_font_name(words[i]["fontname"])
                == self.extract_font_name(words[i - 1]["fontname"])
                and words[i]["ncs"] == words[i - 1]["ncs"]
                or words[i]["x0"] - words[i - 1]["x1"] < 4
                and abs(words[i]["bottom"] - words[i - 1]["bottom"]) < min_offset
                and not (
                    not is_primarily_chinese(current_paragraph[0])
                    and is_primarily_chinese(words[i]["text"])
                )
                and is_same_stroke
            ):
                current_paragraph.append(words[i]["text"])
            else:
                paragraphs.append(
                    {
                        "font_name": font_name,
                        "font_size": font_size,
                        "boldness": boldness,
                        "text": " ".join(current_paragraph),
                    }
                )
                current_paragraph = [words[i]["text"]]
                font_size = words[i]["size"]
                font_name = self.extract_font_name(words[i]["fontname"])
                boldness = (
                    "Bol" in words[i]["fontname"]
                    or "bold" in words[i]["fontname"]
                    or words[i]["ncs"] == "DeviceRGB"
                    or words[i]["stroking_color"] is not None
                    and 0.486 in words[i]["stroking_color"]
                )

        if current_paragraph:
            paragraphs.append(
                {
                    "font_name": font_name,
                    "font_size": font_size,
                    "boldness": boldness,
                    "text": " ".join(current_paragraph),
                }
            )
        self.pdf.close()
        return paragraphs

    def extract_body_words(self):
        header_height, footer_height = self.detect_header_footer_height()
        header_height = header_height + 10
        print(header_height, footer_height)
        result_words = []
        for page in self.pdf.pages:
            words = page.extract_words(
                x_tolerance=3,
                keep_blank_chars=False,
                use_text_flow=True,
                extra_attrs=["fontname", "size", "ncs", "stroking_color"],
            )

            for word in words:
                if (word["top"] + word["bottom"]) / 2 > header_height and word[
                    "bottom"
                ] < page.height - footer_height:
                    result_words.append(word)
        return result_words


class ParagraphMerger:
    @staticmethod
    def merge_paragraphs(paragraphs):
        leading_words = ["▪", "❖", "≤", "“", "WAL", "WAM", "(", "", "•", "-", "*"]
        following_words = ["”", "WAM"]
        merged_paragraphs = []
        if not paragraphs:
            return merged_paragraphs
        merged_paragraphs.append(paragraphs[0])
        for i in range(1, len(paragraphs)):
            if (
                not merged_paragraphs[-1]["text"].endswith((".", "?"))
                and paragraphs[i]["text"][0].islower()
                and merged_paragraphs[-1]["font_name"] == paragraphs[i]["font_name"]
            ):
                merged_paragraphs[-1]["text"] += " " + paragraphs[i]["text"]
                merged_paragraphs[-1]["font_name"] = paragraphs[i]["font_name"]
                merged_paragraphs[-1]["font_size"] = paragraphs[i]["font_size"]
            elif any(
                merged_paragraphs[-1]["text"].endswith(word) for word in leading_words
            ):
                merged_paragraphs[-1]["text"] += paragraphs[i]["text"]
                merged_paragraphs[-1]["font_name"] = paragraphs[i]["font_name"]
                merged_paragraphs[-1]["font_size"] = paragraphs[i]["font_size"]
            elif any(
                paragraphs[i]["text"].startswith(word) for word in following_words
            ):
                merged_paragraphs[-1]["text"] += paragraphs[i]["text"]
                merged_paragraphs[-1]["font_name"] = paragraphs[i]["font_name"]
                merged_paragraphs[-1]["font_size"] = paragraphs[i]["font_size"]
            elif merged_paragraphs[-1]["text"] == "n":
                merged_paragraphs[-1]["text"] = "•" + paragraphs[i]["text"]
                merged_paragraphs[-1]["font_name"] = paragraphs[i]["font_name"]
                merged_paragraphs[-1]["font_size"] = paragraphs[i]["font_size"]
            else:
                merged_paragraphs.append(paragraphs[i])
        return merged_paragraphs


class JSONExporter:
    @staticmethod
    def export_to_json(data, file_name):
        with open(file_name, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)


def main(path: str):
    keywords = {
        "objectives": {
            "start": [
                "Objective and Investment Strategy",
                "Investment Objective and Strategy",
                "Investment Objective and Policy",
                "Objectives and Investment Policy",
                "Investment Objectives",
                "Objectives",
            ],
            "end": [
                "Use of Financial Derivative Instruments (“FDI”) / investment in FDI",
                "Use of financial derivative instruments",
                "Use of derivatives / investment in derivatives",
                "Use of Derivatives",
                "Use of derivatives",
                "What are the key risks?",
            ],
        },
        "risks": {
            "start": [
                "What are the key risks?",
                "What are the key features and risks?",
            ],
            "end": ["How has the Fund performed?", "How has the Sub-Fund performed?"],
        },
    }

    extractor = PDFTextExtractor(path)
    result_paragraphs = extractor.extract_text()
    merged_paragraphs = ParagraphMerger.merge_paragraphs(result_paragraphs)

    objectives = []
    risks = []
    status = {"objectives": "pending", "risks": "pending"}
    for paragraph in merged_paragraphs:
        if paragraph["boldness"]:
            if status["objectives"] == "pending":
                max_ratio = 0
                for text in keywords["objectives"]["start"]:
                    ratio = fuzz.ratio(paragraph["text"].lower(), text.lower())
                    if ratio > max_ratio:
                        max_ratio = ratio
                if max_ratio > 80:
                    status["objectives"] = "start"
            elif status["objectives"] == "start":
                max_ratio = 0
                for text in keywords["objectives"]["end"]:
                    ratio = fuzz.ratio(paragraph["text"].lower(), text.lower())
                    if ratio > max_ratio:
                        max_ratio = ratio
                if max_ratio > 80:
                    status["objectives"] = "end"

        if status["objectives"] == "start":
            if not is_primarily_chinese(paragraph["text"]):
                objectives.append(paragraph)
            continue

        if paragraph["boldness"]:
            if status["risks"] == "pending":
                max_ratio = 0
                for text in keywords["risks"]["start"]:
                    ratio = fuzz.ratio(paragraph["text"].lower(), text.lower())
                    if ratio > max_ratio:
                        max_ratio = ratio
                if max_ratio > 80:
                    status["risks"] = "start"
            elif status["risks"] == "start":
                max_ratio = 0
                for text in keywords["risks"]["end"]:
                    ratio = fuzz.ratio(paragraph["text"].lower(), text.lower())
                    if ratio > max_ratio:
                        max_ratio = ratio
                if max_ratio > 80:
                    status["risks"] = "end"

        if status["risks"] == "start":
            if not is_primarily_chinese(paragraph["text"]):
                risks.append(paragraph)

    JSONExporter.export_to_json(merged_paragraphs, f"merged_paragraphs.json")

    risks = split_risks(risks)
    objectives = split_objectives(objectives)

    file_name = os.path.splitext(os.path.basename(path))[0]

    JSONExporter.export_to_json(objectives, f"output/{file_name}_objectives.json")
    JSONExporter.export_to_json(risks, f"output/{file_name}_risks.json")


def download_file(url, local_filename):
    with requests.get(url, stream=True) as r:
        if r.status_code == 200:
            with open(local_filename, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        else:
            print(f"Failed to download the file. Status code: {r.status_code}")
            return False
    return True


if __name__ == "__main__":
    for filename in os.listdir("./data"):
        if filename.lower().endswith(".pdf"):
            filepath = os.path.join("data", filename)
            try:
                main(filepath)
                print("Success")
            except Exception as err:
                print("Fail")
