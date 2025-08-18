import os
import json
import fitz
from dotenv import load_dotenv
from Logging.logger import logger
from sentence_transformers import SentenceTransformer
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_astradb import AstraDBVectorStore
from langchain_core.documents import Document

load_dotenv()

PDF_DIR = "data/Policy"
#TXT_DIR = "data/raw/webpages"
COLLECTION_NAME = "Investor_policies"

# Embedding model (LangChain wrapper)
embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

# Vector Store setup
vectorstore = AstraDBVectorStore(
    embedding=embedding_model,
    collection_name=COLLECTION_NAME,
    api_endpoint=os.getenv("ASTRA_DB_ENDPOINT"),
    token=os.getenv("ASTRA_DB_TOKEN"),
)

def extract_text_from_pdf(filepath):
    try:
        doc = fitz.open(filepath)
        return "\n".join(page.get_text() for page in doc)
    except Exception as e:
        logger.error(f"Error reading {filepath}: {e}")
        return ""

def extract_text_from_txt(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error reading {filepath}: {e}")
        return ""

def chunk_text(text, metadata):
    splitter = RecursiveCharacterTextSplitter(chunk_size=700, chunk_overlap=100)
    chunks = splitter.split_text(text)

    documents = []
    for i, chunk in enumerate(chunks):
        doc = Document(
            page_content=chunk,
            metadata={
                **metadata,
                "chunk_index": i
            }
        )
        documents.append(doc)
    return documents

def ingest_all():
    groups = {}

    for root, _, files in os.walk(PDF_DIR):
        for fname in files:
            if fname.endswith(".pdf"):
                key = os.path.splitext(fname)[0]
                pdf_path = os.path.join(root, fname)
                groups.setdefault(key, {}).setdefault("pdfs", []).append(pdf_path)

    #for fname in os.listdir(TXT_DIR):
        #if fname.endswith(".txt"):
            #key = os.path.splitext(fname)[0]
            #groups.setdefault(key, {})["txt"] = os.path.join(TXT_DIR, fname)

    for doc_id, files in groups.items():
        logger.info(f"\nProcessing document group: {doc_id}")
        text = ""

        if "txt" in files:
            text += extract_text_from_txt(files["txt"])

        for pdf_path in files.get("pdfs", []):
            text += "\n" + extract_text_from_pdf(pdf_path)

        if not text.strip():
            logger.warning(f"No text found for group {doc_id}, skipping.")
            continue

        metadata = {
            "id": doc_id,
            "source_files": list(files.values()),
            "scheme_name": doc_id.replace("_", " ").title()
        }

        documents = chunk_text(text, metadata)
        try:
            vectorstore.add_documents(documents)
            logger.info(f"Inserted {len(documents)} chunks for {doc_id}")
        except Exception as e:
            logger.error(f"Failed to insert chunks for {doc_id}: {e}")

if __name__ == "__main__":
    ingest_all()
