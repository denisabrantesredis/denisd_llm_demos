from unstructured.partition.html import partition_html
from rag_schema import Document

def parse(url):
    print(f"--> Starting parse: {url}")
    acceptable_types = ["NarrativeText", "List", "ListItem"]
    elements = partition_html(url=url)
    output_list = Document()
    for element in elements:
        el = element.to_dict()
        el_type = el["type"]
        if el_type in acceptable_types:
            if len(el["text"]) >= 20:
                output_list.append(element.to_dict())
    print(f"--> Total Elements: {len(output_list)}")        
    return output_list
