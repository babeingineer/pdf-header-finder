from typing import Union


def start_with_number(text: str) -> bool:
    return text.split(". ")[0].isdigit()


def start_with_symbol(text: str) -> str:
    if not text:
        return ""
    if not text[0].isalnum():
        return text[0]
    return ""


def end_with_symbol(text: str) -> str:
    no_symbols = ["?", ")", "."]
    if not text:
        return ""
    if not text[-1].isalnum() and text[-1] not in no_symbols:
        return text[-1]
    return ""


def split_risks(risks):
    title = risks[0]
    description = risks[1]
    subtitles = [risks[2]["text"]]

    result = {
        "title": title["text"],
        "description": description["text"],
        "body": [{"subtitle": subtitles[0], "content": []}],
    }

    is_start_number = start_with_number(subtitles[0])
    start_symbol = start_with_symbol(subtitles[0])
    end_symbol = end_with_symbol(subtitles[0])
    boldness = risks[2]["boldness"]
    font_size = risks[2]["font_size"]
    font_name = risks[2]["font_name"]

    current_subtitle = 0
    for risk in risks[3:]:
        is_subtitle = False
        if (
            (
                is_start_number
                and start_with_number(risk["text"]) == is_start_number
                or end_with_symbol(risk["text"]) == end_symbol
            )
            and start_with_symbol(risk["text"]) == start_symbol
            and risk["boldness"] == boldness
            and risk["font_name"] == font_name
        ):
            is_subtitle = True

        if is_subtitle:
            result["body"].append({"subtitle": risk["text"], "content": []})
            current_subtitle += 1
        else:
            result["body"][current_subtitle]["content"].append(risk["text"])

    return result


def split_objectives(objectives):
    title = objectives[0]

    result = {
        "title": title["text"],
        "body": [],
    }
    for objective in objectives[1:]:
        result["body"].append(objective["text"])

    return result
