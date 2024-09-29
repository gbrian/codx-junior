import os
from langchain.schema.document import Document

class QASplitter:
    def __init__(self):
        pass

    def load(self, file_path):
        with open(file_path, 'r') as file:
            lines = file.readlines()
        chunks = []
        chunk_data = None
        
        def appen_chunk(chunk_data):
            documents.append(Document(page_content="\n".join(chunk_data), metadata={'source': os.path.abspath(file_path)}))

        for line in lines:
            if line.startswith('Q:'):
                if chunk_data:
                    appen_chunk(chunk_data)
                chunk_data.append(line)

        if chunk_data:
            appen_chunk(chunk_data)
        return chunks