"""Same application service for Telegram and CLI."""
from dataclasses import replace
from config import load_config
from components.memory import Memory
from components.assistant import Assistant
from pipelines.builders import ingestion_pipeline, generation_pipeline

class DocumentBot:
    def __init__(self, config=None):
        self.config = config or load_config()
        self.assistant = Assistant(self.config)
        self.memory = self.assistant.memory
        self.documents = Memory(replace(self.config, prefix="vpg07-documents"))
    def ingest(self, owner, path, filename=None):
        from pathlib import Path
        pipeline = ingestion_pipeline(self.config, self.documents, owner)
        output = pipeline.run({"convert":{"path":str(path), "filename":filename or Path(path).name}},
            include_outputs_from={"save"})
        return {"summary": output["summarize"]["summary"],
                "chunks": output["save"]["documents_written"]}
    def handle(self, owner, text):
        if not text.strip() or len(text)>4000 or text.startswith("/"):
            raise ValueError("Нужен вопрос от 1 до 4000 символов.")
        return generation_pipeline(self.config, self.documents, self.assistant, owner).run(
            {"embed":{"text":text}, "answer":{"question":text}})["answer"]["result"]
    def clear(self, owner):
        self.documents.clear(owner)
        self.memory.clear(owner)
