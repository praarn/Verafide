import io
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

import fitz  # PyMuPDF — rasterizes pages with no external binary needed
import pytesseract
from PIL import Image
from pypdf import PdfReader

from app.config import settings

if settings.TESSERACT_CMD:
    pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD

MIN_CHUNK_WORDS = 25
MAX_CHUNK_WORDS = 400  # keep TF-IDF inference fast and each "article" digestible
OCR_DPI = 150  # good balance of OCR accuracy vs. speed for newspaper-density text
MIN_ALPHA_RATIO = 0.4  # fraction of characters that must be real a-z letters
MAX_OCR_PAGES = 40  # bounds worst-case request time on very long scanned documents
OCR_WORKERS = min(8, (os.cpu_count() or 4))  # pytesseract shells out to the tesseract
# binary per call, releasing the GIL while it runs — so a thread pool gives real
# wall-clock speedup here despite Python's GIL, unlike pure-Python CPU work.


class PDFExtractError(Exception):
    pass


def _has_real_text(text: str) -> bool:
    """Raw word-count alone isn't enough: many PDFs (common with Indian
    newspaper e-papers built from custom/embedded fonts with broken text
    encoding) extract plenty of "words" that are actually garbage Unicode
    codepoints — visually the page looks like normal English text, but the
    underlying character data isn't real letters at all. Those pages would
    otherwise silently pass this check, then get stripped to nothing during
    classification and vanish with no explanation. Checking the fraction of
    real a-z letters (not just whitespace-separated token count) catches
    this and correctly routes those pages to OCR instead, since OCR reads
    the actual rendered pixels rather than the broken text layer."""
    words = text.split()
    if len(words) < MIN_CHUNK_WORDS:
        return False
    letters = sum(1 for ch in text if ch.isalpha() and ch.isascii())
    return (letters / max(len(text), 1)) >= MIN_ALPHA_RATIO


def _split_long_page(page_text: str) -> list[str]:
    """Prefer real paragraph breaks (blank lines) when the PDF preserves
    them — this cleanly separates distinct articles on a page. Many PDFs
    don't preserve any blank lines at all, since PDF text extraction is
    fundamentally position-based, not semantic — in that case, fall back to
    fixed-size word windows so one verdict never silently has to cover an
    entire page's worth of mixed, unrelated content."""
    blocks = [b.strip() for b in re.split(r"\n\s*\n", page_text) if b.strip()]

    if len(blocks) <= 1:
        words = page_text.split()
        if len(words) <= MAX_CHUNK_WORDS:
            return [page_text.strip()] if page_text.strip() else []
        return [
            " ".join(words[i : i + MAX_CHUNK_WORDS])
            for i in range(0, len(words), MAX_CHUNK_WORDS)
        ]

    chunks = []
    buffer = ""
    for block in blocks:
        candidate = f"{buffer} {block}".strip() if buffer else block
        if len(candidate.split()) >= MAX_CHUNK_WORDS:
            if buffer:
                chunks.append(buffer)
            buffer = block
        else:
            buffer = candidate
    if buffer:
        chunks.append(buffer)
    return chunks


def _tesseract_available() -> bool:
    try:
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def _ocr_page(file_bytes: bytes, page_index: int) -> str:
    """Rasterizes a single PDF page to an image and runs OCR on it.

    Opens its own fitz.Document per call (rather than sharing one document
    across threads) — PyMuPDF documents aren't guaranteed safe to render
    from multiple threads concurrently, and file_bytes is already in memory
    so re-opening it per page is cheap relative to the OCR pass itself.
    """
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    try:
        page = doc[page_index]
        pix = page.get_pixmap(dpi=OCR_DPI)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        try:
            return pytesseract.image_to_string(img)
        except Exception:
            return ""
    finally:
        doc.close()


def extract_chunks_from_pdf(file_bytes: bytes, max_chunks: int = 200) -> dict:
    """Returns {"chunks": [{"text":..., "source_ref":"page N"}, ...], "summary": {...}}.

    Two passes for speed:
      1. Sequential, fast native-text extraction across all pages, checking
         whether each page's text is actually readable (not just present —
         see _has_real_text). This identifies which pages need OCR.
      2. OCR only those pages, **concurrently** across a thread pool. OCR is
         the slow part (each page can take a couple of seconds), so for a
         multi-page scanned or broken-encoding document, doing this one
         page at a time made large uploads feel like they'd hung — running
         them in parallel cuts wall-clock time roughly by the worker count.

    A hard cap (MAX_OCR_PAGES) bounds worst-case request time on very long
    scanned documents; anything beyond the cap is reported as skipped
    rather than silently making the request run indefinitely.
    """
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
    except Exception as exc:
        raise PDFExtractError(f"Could not read that PDF: {exc}") from exc

    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except Exception:
            raise PDFExtractError("This PDF is password-protected and can't be read.")

    total_pages = len(reader.pages)

    # --- Pass 1: fast native text extraction ---
    page_texts: dict[int, str] = {}
    needs_ocr: list[int] = []  # 0-based page indices

    for page_num, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        text = re.sub(r"[ \t]+", " ", text)
        if _has_real_text(text):
            page_texts[page_num] = text
        else:
            needs_ocr.append(page_num - 1)

    # --- Pass 2: OCR only the pages that need it, in parallel ---
    tesseract_ok = _tesseract_available() if needs_ocr else True
    ocr_capped = len(needs_ocr) > MAX_OCR_PAGES
    ocr_targets = needs_ocr[:MAX_OCR_PAGES]
    ocr_page_count = 0
    failed_page_count = len(needs_ocr) - len(ocr_targets)  # pages skipped due to the cap

    if ocr_targets and tesseract_ok:
        with ThreadPoolExecutor(max_workers=OCR_WORKERS) as pool:
            future_to_page = {
                pool.submit(_ocr_page, file_bytes, idx): idx for idx in ocr_targets
            }
            for future in as_completed(future_to_page):
                idx = future_to_page[future]
                page_num = idx + 1
                try:
                    text = re.sub(r"[ \t]+", " ", future.result())
                except Exception:
                    text = ""
                if _has_real_text(text):
                    page_texts[page_num] = text
                    ocr_page_count += 1
                else:
                    failed_page_count += 1
    elif ocr_targets and not tesseract_ok:
        failed_page_count += len(ocr_targets)

    text_page_count = len(page_texts) - ocr_page_count

    # --- Assemble chunks in original page order ---
    results = []
    for page_num in sorted(page_texts):
        for chunk in _split_long_page(page_texts[page_num]):
            if len(chunk.split()) >= MIN_CHUNK_WORDS:
                results.append({"text": chunk, "source_ref": f"page {page_num}"})
            if len(results) >= max_chunks:
                break
        if len(results) >= max_chunks:
            break

    summary = {
        "total_pages": total_pages,
        "text_pages": text_page_count,
        "ocr_pages": ocr_page_count,
        "failed_pages": failed_page_count,
        "ocr_available": bool(tesseract_ok),
        "ocr_capped": ocr_capped,
    }

    if not results:
        if not tesseract_ok and needs_ocr:
            raise PDFExtractError(
                f"Could not find embedded text on any of this PDF's {total_pages} page(s), "
                "and Tesseract OCR isn't installed on this server, so scanned/image pages "
                "can't be read. Install Tesseract OCR (see README) and try again."
            )
        raise PDFExtractError(
            f"Could not find enough readable text in this PDF, even after attempting OCR "
            f"on {len(ocr_targets)} of {total_pages} page(s). The scan quality may be too low to read."
        )

    return {"chunks": results, "summary": summary}
