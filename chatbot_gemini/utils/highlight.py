import io
import json
import urllib
from pypdf import PdfReader, PdfWriter
from pypdf.annotations import Highlight
from pypdf.generic import ArrayObject, FloatObject, DictionaryObject, NumberObject, FloatObject, NameObject, TextStringObject,ArrayObject

def createHighlight(x1, y1, x2, y2, meta, color = [1, 0, 0]):
    newHighlight = DictionaryObject()

    newHighlight.update({
        NameObject("/F"): NumberObject(4),
        NameObject("/Type"): NameObject("/Annot"),
        NameObject("/Subtype"): NameObject("/Highlight"),

        NameObject("/T"): TextStringObject(meta["title"]),
        NameObject("/Contents"): TextStringObject(meta["contents"]),

        NameObject("/C"): ArrayObject([FloatObject(c) for c in color]),
        NameObject("/Rect"): ArrayObject([
            FloatObject(x1),
            FloatObject(y1),
            FloatObject(x2),
            FloatObject(y2)
        ]),
        NameObject("/QuadPoints"): ArrayObject([
            FloatObject(x1),
            FloatObject(y2),
            FloatObject(x2),
            FloatObject(y2),
            FloatObject(x1),
            FloatObject(y1),
            FloatObject(x2),
            FloatObject(y1)
        ]),
    })
    
    return newHighlight


def generate_annotation(filename, url, annotation_info):
    with urllib.request.urlopen(url) as f:
        memoryFile = io.BytesIO(f.read())
        reader = PdfReader(memoryFile)
        writer = PdfWriter()
        
        # Measure page size
        box = reader.pages[0].mediabox
        page_width = box.width
        page_height = box.height
        #print(f"Width: {page_width} | Height: {page_height}")
  

        for i in range(len(reader.pages)):
            page = reader.pages[i]
            writer.add_page(page)
            
            for annotation in annotation_info:    
                if i == annotation['page']:
                    
                    coords = annotation['coords']
                    #print(f"--> coords: {coords}")
                    text = annotation['text']

                    start_x = coords[0][0]
                    end_x = coords[2][0]
                    start_y = page_height - coords[0][1]
                    end_y = page_height - coords[1][1]
                    #print(f"--> start_x: {start_x}, end_x: {end_x}, start_y: {start_y}, end_y: {end_y}, page: {annotation['page']}")

                    rect = (start_x, start_y, end_x, end_y)
                    quad_points = [start_x, end_x, start_y, end_y]

                    annotation = createHighlight(start_x, start_y, end_x, end_y, {"title": "Chunk Text:", "contents": text}, [1, 1, 0])                
                    writer.add_annotation(page_number=i, annotation=annotation)
                    

        with open(filename, "wb") as fp:
            writer.write(fp)
        return filename
