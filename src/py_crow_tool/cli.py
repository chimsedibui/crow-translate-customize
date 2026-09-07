from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from py_crow_tool.bootstrap import build_services
from py_crow_tool.core.models import TranslationException, TranslationRequest
from py_crow_tool.services.ocr import OcrService


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="py-crow", description="Translate text with Google Cloud Translation")
    result.add_argument("text", nargs="*", help="Text to translate")
    result.add_argument("--file", type=Path, help="Read source text from a UTF-8 file")
    result.add_argument("--stdin", action="store_true", help="Read source text from stdin")
    result.add_argument("--ocr", type=Path, help="Recognize text from an image before translating")
    result.add_argument("--ocr-language", default=None, help="Language hint for OCR (e.g. vi, en); defaults to the configured OCR language")
    result.add_argument("--ocr-engine", choices=["tesseract", "openai-vision"], default=None, help="Override the configured OCR engine")
    result.add_argument("-s", "--source", default="auto", help="Source language code")
    result.add_argument("-t", "--target", default="en", help="Target language code")
    result.add_argument("-p", "--provider", help="Override automatic provider selection (e.g. google-v2, or a plugin's provider id)")
    result.add_argument("--detect", action="store_true", help="Only detect the source language")
    result.add_argument("--json", action="store_true", help="Print structured JSON")
    return result


async def run(args: argparse.Namespace) -> int:
    _, settings, manager = build_services()
    ocr_service = OcrService(settings) if args.ocr else None
    try:
        if args.ocr:
            text = await ocr_service.recognize_file(str(args.ocr), language=args.ocr_language, engine=args.ocr_engine)
        elif args.file:
            text = args.file.read_text(encoding="utf-8")
        elif args.stdin:
            text = sys.stdin.read()
        else:
            text = " ".join(args.text)
        if not text.strip():
            raise ValueError("No source text supplied")
        if args.detect:
            detected = await manager.detect_language(text, args.provider)
            output = {"language": detected.language, "confidence": detected.confidence}
        else:
            output = (await manager.translate(TranslationRequest(text, args.target, args.source, args.provider))).to_dict()
        print(json.dumps(output, ensure_ascii=False) if args.json else output.get("translated_text", output["language"]))
        return 0
    except (TranslationException, OSError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2
    finally:
        await manager.close()
        if ocr_service is not None:
            await ocr_service.close()


def main() -> int:
    return asyncio.run(run(parser().parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())

