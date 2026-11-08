"""CLI uses the same pipelines as Telegram; uploads only your selected local files."""
import argparse
import json
from service import DocumentBot

def main():
    p = argparse.ArgumentParser()
    p.add_argument("action", choices=["ingest", "ask"])
    p.add_argument("value", help="Local path or question")
    p.add_argument("--owner", default="cli:demo")
    a=p.parse_args()
    service=DocumentBot()
    result=service.ingest(a.owner,a.value) if a.action=="ingest" else service.handle(a.owner,a.value)
    print(json.dumps({k:v for k,v in result.items() if k in {"summary","chunks","answer","sources","calls"}}, ensure_ascii=False,indent=2))
if __name__ == "__main__":
    main()
