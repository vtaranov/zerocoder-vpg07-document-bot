"""Two real Haystack Pipeline graphs with connected component sockets."""
from haystack import Pipeline
from haystack.utils import Secret
from haystack.components.embedders import OpenAIDocumentEmbedder, OpenAITextEmbedder
from haystack_integrations.components.retrievers.pinecone import PineconeEmbeddingRetriever
from components.documents import ConvertDocument, SaveDocuments, Summarize, Answer

def ingestion_pipeline(config, documents, owner):
    p = Pipeline()
    p.add_component("convert", ConvertDocument())
    p.add_component("embed", OpenAIDocumentEmbedder(api_key=Secret.from_token(config.api_key),
        api_base_url=config.base_url or None, model=config.embedding_model, progress_bar=False))
    p.add_component("save", SaveDocuments(documents, owner))
    p.add_component("summarize", Summarize(documents.ai, config.model))
    p.connect("convert.documents", "embed.documents")
    p.connect("embed.documents", "save.documents")
    p.connect("save.documents", "summarize.documents")
    return p

def generation_pipeline(config, documents, assistant, owner):
    p = Pipeline()
    p.add_component("embed", OpenAITextEmbedder(api_key=Secret.from_token(config.api_key),
        api_base_url=config.base_url or None, model=config.embedding_model))
    p.add_component("retrieve", PineconeEmbeddingRetriever(document_store=documents.store(owner), top_k=5))
    p.add_component("answer", Answer(assistant, owner))
    p.connect("embed.embedding", "retrieve.query_embedding")
    p.connect("retrieve.documents", "answer.documents")
    return p
