import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
from config import Config
from components.documents import ConvertDocument
from components.memory import Memory
from bot.telegram_bot import build_bot

class DocumentsTest(unittest.TestCase):
    def test_docling_markdown_stable_ids_and_limits(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"sample.md"
            p.write_text("# Test policy\n\n"+"The warranty lasts 19 days. "*150)
            converter=ConvertDocument()
            first=converter.run(str(p),p.name)["documents"]
            second=converter.run(str(p),p.name)["documents"]
            self.assertEqual([d.id for d in first],[d.id for d in second])
            self.assertTrue(all(0<len(d.content)<=1800 for d in first))
            self.assertTrue(all(d.meta["filename"]==p.name for d in first))
            self.assertGreater(len(first),1)
    def test_unsupported_and_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"bad.exe";p.write_bytes(b"x")
            with self.assertRaises(ValueError):ConvertDocument().run(str(p),p.name)
            p=Path(tmp)/"empty.md";p.write_bytes(b"")
            with self.assertRaises(ValueError):ConvertDocument().run(str(p),p.name)
    def test_pinecone_listing_accepts_sdk_objects(self):
        from types import SimpleNamespace
        m=object.__new__(Memory);m.config=Config("x","y","z",prefix="vpg07-documents")
        m.index=Mock();m.index.list.return_value=[[SimpleNamespace(id="a"),"b"]]
        m.index.fetch.return_value=SimpleNamespace(vectors={"a":SimpleNamespace(metadata={}),"b":SimpleNamespace(metadata={})})
        self.assertEqual(len(m.rows("owner")),2)
        self.assertEqual(m.index.fetch.call_args.kwargs["ids"],["a","b"])
    def test_namespaces(self):
        m=object.__new__(Memory); m.config=Config("x","y","z",prefix="vpg07-documents")
        self.assertNotEqual(m.namespace("user:a"),m.namespace("user:b"))
        with self.assertRaises(ValueError):m.namespace("")
    def test_unauthorized_file_is_not_downloaded(self):
        bot=Mock(); decorators={}
        def register(**kw):
            def decorate(fn):decorators[kw["content_types"][0]]=fn;return fn
            return decorate
        bot.message_handler.side_effect=register
        c=Config("x","y","z",allowed_users=(42,))
        service=Mock();build_bot(c,service,bot)
        message=Mock();message.from_user.id=99;message.chat.type="private"
        decorators["document"](message)
        bot.get_file.assert_not_called();service.ingest.assert_not_called()

if __name__=="__main__":unittest.main()
