"""PineconeDocumentStore and Retriever: only original user messages."""
import hashlib
import math
import time
from uuid import uuid4
from datetime import datetime, timezone
from config import Config
from openai import OpenAI
from pinecone import Pinecone
from haystack import Document
from haystack.utils import Secret
from haystack.document_stores.types import DuplicatePolicy
from haystack_integrations.document_stores.pinecone import PineconeDocumentStore
from haystack_integrations.components.retrievers.pinecone import PineconeEmbeddingRetriever

class Memory:
    def __init__(self, config):
        self.config = config
        self.ai = OpenAI(api_key=config.api_key, base_url=config.base_url or None, timeout=60, max_retries=1)
        self.pc = Pinecone(api_key=config.pinecone_key)
        info = self.pc.describe_index(config.index)
        if info.dimension != 1536 or info.metric != "cosine" or not info.status["ready"]:
            raise ValueError("Нужен готовый индекс dimension=1536, metric=cosine.")
        self.index = self.pc.Index(host=info.host)
    def namespace(self, owner):
        if not isinstance(owner, str) or not owner.strip():
            raise ValueError("Не указан владелец памяти.")
        return self.config.prefix + "-" + hashlib.sha256(owner.encode()).hexdigest()[:32]
    def store(self, owner):
        return PineconeDocumentStore(api_key=Secret.from_token(self.config.pinecone_key),
            index=self.config.index, namespace=self.namespace(owner), dimension=1536, metric="cosine")
    def embed(self, text):
        if not isinstance(text, str) or not text.strip() or len(text) > 4000:
            raise ValueError("Нужен текст от 1 до 4000 символов.")
        v = self.ai.embeddings.create(model=self.config.embedding_model, input=text).data[0].embedding
        if len(v) != 1536 or not all(math.isfinite(x) for x in v):
            raise ValueError("Неверный эмбеддинг.")
        return v
    def search(self, owner, text):
        retriever = PineconeEmbeddingRetriever(document_store=self.store(owner), top_k=5)
        docs = retriever.run(query_embedding=self.embed(text))["documents"]
        return [{"id": d.id, "text": d.content, "score": d.score} for d in docs]
    def save_user(self, owner, text):
        # No profile, assistant answers or tool results are accepted by this method.
        d = Document(id=uuid4().hex, content=text, embedding=self.embed(text),
                     meta={"type": "user_message", "created_at": datetime.now(timezone.utc).isoformat()})
        self.store(owner).write_documents([d], policy=DuplicatePolicy.OVERWRITE)
        until = time.monotonic() + 35
        while time.monotonic() < until:
            rows = self.index.fetch(ids=[d.id], namespace=self.namespace(owner)).vectors
            hits = self.search(owner, text)
            if d.id in rows and any(x["id"] == d.id for x in hits):
                return d.id
            time.sleep(1)
        raise TimeoutError("Запись отправлена; видимость в поиске ещё не подтверждена.")
    def rows(self, owner):
        ids = [i if isinstance(i, str) else i.id
               for batch in self.index.list(namespace=self.namespace(owner)) for i in batch]
        result = []
        for start in range(0, len(ids), 100):
            vs = self.index.fetch(ids=ids[start:start+100], namespace=self.namespace(owner)).vectors
            result.extend({"id": k, "metadata": dict(v.metadata or {})} for k,v in vs.items())
        return result
    def clear(self, owner):
        if not self.rows(owner):
            return
        self.index.delete(delete_all=True, namespace=self.namespace(owner))
        until = time.monotonic() + 35
        while self.rows(owner):
            if time.monotonic() >= until:
                raise TimeoutError("Удаление отправлено, но ещё не подтверждено.")
            time.sleep(1)
