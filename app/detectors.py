import io
import zipfile
from typing import Optional

PDF_MAGIC = b"%PDF"
ZIP_MAGIC = b"PK\x03\x04"


def detect_file_type(data: bytes) -> Optional[str]:
    """Sniff the actual file type from content, ignoring any claimed filename."""
    if data.startswith(PDF_MAGIC):
        return "pdf"
    if data.startswith(ZIP_MAGIC):
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                if "word/document.xml" in zf.namelist():
                    return "docx"
        except zipfile.BadZipFile:
            return None
    return None
