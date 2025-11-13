import os
import fitz
from dotenv import load_dotenv
from Logging.logger import logger
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_astradb import AstraDBVectorStore
from langchain_core.documents import Document
from langchain_community.embeddings import SentenceTransformerEmbeddings
import nest_asyncio
nest_asyncio.apply()

load_dotenv()

PDF_DIR = "data/raw/pdfs/new"
COLLECTION_NAME = "Mospi_data"

embedding_model = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")

vectorstore = AstraDBVectorStore(
    embedding=embedding_model,
    collection_name=COLLECTION_NAME,
    api_endpoint=os.getenv("ASTRA_DB_ENDPOINT_2"),
    token=os.getenv("ASTRA_DB_TOKEN_2"),
)


def extract_text_from_pdf(filepath):
    """Extracts text from a PDF file using fitz (PyMuPDF)."""
    try:
        if not hasattr(fitz, 'open'):
            raise ImportError("fitz.open not found. Check PyMuPDF installation.")

        logger.debug(f"Loading PDF with fitz: {filepath}")
        with fitz.open(filepath) as doc:
            full_text = "\n".join(page.get_text() for page in doc)
        logger.debug(f"Extracted {len(full_text)} characters from {filepath}")
        return full_text
    except Exception as e:
        logger.error(f"Error reading {filepath} with fitz: {e}", exc_info=True)
        return ""


def extract_text_from_txt(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error reading {filepath}: {e}")
        return ""


def chunk_text(text, metadata):
    """Chunks text and returns LangChain Document objects with metadata."""
    splitter = RecursiveCharacterTextSplitter(chunk_size=700, chunk_overlap=100)
    chunks = splitter.split_text(text)
    return [
        Document(
            page_content=chunk,
            metadata={**metadata, "chunk_index": i}
        )
        for i, chunk in enumerate(chunks)
    ]


def ingest_all():
    """Finds PDFs in PDF_DIR, chunks them, and adds them to the vector store."""
    if not os.path.isdir(PDF_DIR):
        logger.error(f"PDF directory not found: {os.path.abspath(PDF_DIR)}")
        return

    all_pdf_paths = [
        os.path.join(PDF_DIR, fname)
        for fname in os.listdir(PDF_DIR)
        if fname.lower().endswith(".pdf")
    ]

    logger.info(f"Found {len(all_pdf_paths)} PDF files to process in '{PDF_DIR}': {all_pdf_paths}")

    processed_chunks_count = 0

    for pdf_path in all_pdf_paths:
        doc_id = os.path.splitext(os.path.basename(pdf_path))[0]
        logger.info(f"\nProcessing document: {doc_id}")

        text = extract_text_from_pdf(pdf_path)
        if not text.strip():
            logger.warning(f"No text extracted for document '{doc_id}', skipping.")
            continue

        metadata = {
            "id": doc_id,
            "source_file": os.path.abspath(pdf_path),
            "original_filename": os.path.basename(pdf_path),
            "source": "DGFT"
        }

        documents = chunk_text(text, metadata)
        logger.info(f"  - Split text into {len(documents)} chunks.")

        if not documents:
            logger.warning(f"  - No chunks generated for '{doc_id}', skipping.")
            continue

        try:
            vectorstore.add_documents(documents)

            logger.info(
                f"  - Successfully ADDED {len(documents)} chunks for '{doc_id}' "
                f"to collection '{COLLECTION_NAME}'."
            )
            processed_chunks_count += len(documents)

        except Exception as e:
            logger.error(f"  - Failed to insert chunks for '{doc_id}': {e}", exc_info=True)

    logger.info(f"\nIngestion finished. Total new chunks added: {processed_chunks_count}")


if __name__ == "__main__":
    logger.info(f"Starting ingestion process for collection '{COLLECTION_NAME}'...")
    ingest_all()
    logger.info("Ingestion process complete.")
