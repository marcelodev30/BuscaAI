


from typing import Any

try:
    from docling.document_converter import DocumentConverter
    from docling_core.types import DoclingDocument
except ImportError as exc:
    raise ImportError(
                "Docling não está instalado. Instale com `uv sync --extra docling` "
                "para carregar PDF/DOCX."
            ) from exc



class DoclingLoader:
        

    def load_to_document(self, file:str)-> DoclingDocument:
        converter = DocumentConverter()
        result = converter.convert(file)
        return result.document


    def convert_docling_to_markdown(self, doc: DoclingDocument):
        return doc.export_to_markdown()

    def save_as_json(self, doc: DoclingDocument, path:str):
        doc.save_as_json(path)

    def load_json_to_docling_document(self, file:str)-> DoclingDocument:
        doc_recarregado = DoclingDocument.load_from_json(file)
        return doc_recarregado

    