from unstructured.chunking.title import chunk_by_title
from unstructured.staging.base import convert_to_dict, dict_to_elements

def chunk_docs_unstruct(elements):
    chunking_settings = {
        "combine_text_under_n_chars": 50,
        "max_characters": 750,
        "new_after_n_chars": 500
    }
    chunked_raw = chunk_by_title(elements=elements, **chunking_settings)
    results = convert_to_dict(chunked_raw)
    return results


def chunk(input_data):
    print(f"--> Generating Chunks")
    elements_raw = dict_to_elements(input_data)
    elements = chunk_docs_unstruct(elements_raw)
    print(f"--> Generated {len(elements)} chunks")
    return elements
