"""
Multi-format data ingestion and dataset governance for AnalystOS.

Provides a unified DatasetArtifact abstraction supporting CSV, Excel (XLSX, XLS),
JSON, Parquet, TSV, TXT, and PDF documents with automated schema normalization,
table extraction, and integrity validation.
"""

from __future__ import annotations
import io
import os
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
import pandas as pd

from tools.data_tools import normalize_dataset_columns, inspect_schema, read_csv_with_encoding_fallbacks
from tools.validation_tools import validate_dataset_integrity
from data.data_generator import generate_ecommerce_dataset


@dataclass
class DatasetArtifact:
    """
    Unified representation of ingested analytical data or business documents.
    """
    source_id: str
    filename: str
    source_type: str  # 'csv','excel','json','parquet','tsv','txt','pdf','synthetic'
    dataframe: Optional[pd.DataFrame] = None
    extracted_text: Optional[str] = None  # for PDFs / text documents
    tables: List[pd.DataFrame] = field(default_factory=list)  # PDF / multi-sheet tables
    schema: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    validation_report: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    sheet_names: List[str] = field(default_factory=list)  # for Excel
    selected_sheet: Optional[str] = None
    page_count: Optional[int] = None  # for PDF
    is_scanned_pdf: bool = False


def _populate_df_metadata(artifact: DatasetArtifact) -> DatasetArtifact:
    """Helper to inspect schema, normalize columns, and validate integrity for DataFrame artifacts."""
    if artifact.dataframe is None:
        return artifact

    try:
        norm_df, mapping = normalize_dataset_columns(artifact.dataframe)
        artifact.dataframe = norm_df
        if mapping:
            artifact.metadata["column_mapping"] = mapping
    except Exception as ex:
        artifact.warnings.append(f"Column normalization warning: {str(ex)}")

    try:
        artifact.schema = inspect_schema(artifact.dataframe)
    except Exception as ex:
        artifact.warnings.append(f"Schema inspection warning: {str(ex)}")

    try:
        val_rep = validate_dataset_integrity(artifact.dataframe)
        artifact.validation_report = val_rep
        if val_rep.get("warnings"):
            artifact.warnings.extend(val_rep["warnings"])
        if val_rep.get("critical_errors"):
            artifact.errors.extend(val_rep["critical_errors"])
    except Exception as ex:
        artifact.warnings.append(f"Integrity audit warning: {str(ex)}")

    return artifact


def load_csv_artifact(
    file_or_buffer: Union[str, io.BytesIO, io.StringIO, Any],
    filename: str = "data.csv"
) -> DatasetArtifact:
    """Load a CSV file into a unified DatasetArtifact with multi-encoding fallback."""
    source_id = str(uuid.uuid4())
    artifact = DatasetArtifact(
        source_id=source_id,
        filename=filename,
        source_type="csv"
    )

    try:
        df, used_enc = read_csv_with_encoding_fallbacks(file_or_buffer)
        if df.empty:
            artifact.errors.append("CSV file contains no rows or data.")
            return artifact

        # Strip whitespace from columns
        df.columns = [str(c).strip() for c in df.columns]
        artifact.dataframe = df
        artifact.metadata["encoding"] = used_enc
        return _populate_df_metadata(artifact)
    except Exception as e:
        artifact.errors.append(f"Failed to read CSV: {str(e)}")
        return artifact


def load_tsv_artifact(
    file_or_buffer: Union[str, io.BytesIO, io.StringIO, Any],
    filename: str = "data.tsv"
) -> DatasetArtifact:
    """Load a TSV (tab-separated) file into a unified DatasetArtifact with multi-encoding fallback."""
    source_id = str(uuid.uuid4())
    artifact = DatasetArtifact(
        source_id=source_id,
        filename=filename,
        source_type="tsv"
    )

    try:
        df, used_enc = read_csv_with_encoding_fallbacks(file_or_buffer, default_sep="\t")
        if df.empty:
            artifact.errors.append("TSV file contains no rows or data.")
            return artifact

        df.columns = [str(c).strip() for c in df.columns]
        artifact.dataframe = df
        artifact.metadata["encoding"] = used_enc
        return _populate_df_metadata(artifact)
    except Exception as e:
        artifact.errors.append(f"Failed to read TSV: {str(e)}")
        return artifact


def load_excel_artifact(
    file_or_buffer: Union[str, io.BytesIO, bytes, Any],
    filename: str = "data.xlsx",
    sheet_name: Optional[Union[str, int]] = None
) -> DatasetArtifact:
    """
    Load an Excel workbook (XLSX, XLS), inspect sheet names, and load the specified sheet.
    """
    source_id = str(uuid.uuid4())
    artifact = DatasetArtifact(
        source_id=source_id,
        filename=filename,
        source_type="excel"
    )

    try:
        # Read sheet names first
        excel_file = pd.ExcelFile(file_or_buffer)
        sheet_names = excel_file.sheet_names
        artifact.sheet_names = sheet_names

        # Select target sheet
        target_sheet = sheet_name if sheet_name in sheet_names else (sheet_names[0] if sheet_names else 0)
        artifact.selected_sheet = str(target_sheet)

        df = excel_file.parse(sheet_name=target_sheet)
        if df.empty:
            artifact.warnings.append(f"Selected sheet '{target_sheet}' is empty.")
        else:
            df.columns = [str(c).strip() for c in df.columns]

        artifact.dataframe = df
        return _populate_df_metadata(artifact)
    except ImportError:
        artifact.errors.append("Missing dependency 'openpyxl' or 'xlrd' to read Excel files. Please install via pip.")
        return artifact
    except Exception as e:
        artifact.errors.append(f"Failed to read Excel workbook: {str(e)}")
        return artifact


def load_json_artifact(
    file_or_buffer: Union[str, io.BytesIO, io.StringIO, Any],
    filename: str = "data.json"
) -> DatasetArtifact:
    """
    Load JSON transaction data into a DatasetArtifact.
    """
    source_id = str(uuid.uuid4())
    artifact = DatasetArtifact(
        source_id=source_id,
        filename=filename,
        source_type="json"
    )

    try:
        if isinstance(file_or_buffer, (io.BytesIO, io.StringIO)):
            content = file_or_buffer.getvalue()
            if isinstance(content, bytes):
                content = content.decode("utf-8", errors="replace")
            buffer = io.StringIO(content)
            df = pd.read_json(buffer)
        elif isinstance(file_or_buffer, str) and (file_or_buffer.startswith("{") or file_or_buffer.startswith("[")):
            df = pd.read_json(io.StringIO(file_or_buffer))
        else:
            df = pd.read_json(file_or_buffer)

        if df.empty:
            artifact.errors.append("JSON file contains no tabular records.")
            return artifact

        df.columns = [str(c).strip() for c in df.columns]
        artifact.dataframe = df
        return _populate_df_metadata(artifact)
    except Exception as e:
        artifact.errors.append(f"Failed to read JSON: {str(e)}")
        return artifact


def load_parquet_artifact(
    file_or_buffer: Union[str, io.BytesIO, bytes, Any],
    filename: str = "data.parquet"
) -> DatasetArtifact:
    """Load a Parquet columnar file into a unified DatasetArtifact."""
    source_id = str(uuid.uuid4())
    artifact = DatasetArtifact(
        source_id=source_id,
        filename=filename,
        source_type="parquet"
    )

    try:
        if isinstance(file_or_buffer, bytes):
            buffer = io.BytesIO(file_or_buffer)
            df = pd.read_parquet(buffer)
        else:
            df = pd.read_parquet(file_or_buffer)

        if df.empty:
            artifact.errors.append("Parquet file contains no records.")
            return artifact

        df.columns = [str(c).strip() for c in df.columns]
        artifact.dataframe = df
        return _populate_df_metadata(artifact)
    except ImportError:
        artifact.errors.append("Missing dependency 'pyarrow' or 'fastparquet' to read Parquet files.")
        return artifact
    except Exception as e:
        artifact.errors.append(f"Failed to read Parquet file: {str(e)}")
        return artifact


def load_pdf_artifact(
    file_or_buffer: Union[str, io.BytesIO, bytes, Any],
    filename: str = "document.pdf"
) -> DatasetArtifact:
    """
    Extract text and tables from a PDF document.
    Flags scanned (image-only) PDFs when text extraction yields minimal or zero content.
    """
    source_id = str(uuid.uuid4())
    artifact = DatasetArtifact(
        source_id=source_id,
        filename=filename,
        source_type="pdf"
    )

    extracted_pages: List[str] = []
    extracted_tables: List[pd.DataFrame] = []
    page_count = 0

    # Ensure buffer is BytesIO if bytes
    if isinstance(file_or_buffer, bytes):
        buffer = io.BytesIO(file_or_buffer)
    elif isinstance(file_or_buffer, str) and os.path.exists(file_or_buffer):
        with open(file_or_buffer, "rb") as f:
            buffer = io.BytesIO(f.read())
    elif hasattr(file_or_buffer, "read"):
        content = file_or_buffer.read()
        if hasattr(file_or_buffer, "seek"):
            file_or_buffer.seek(0)
        buffer = io.BytesIO(content) if isinstance(content, bytes) else io.BytesIO(content.encode("utf-8"))
    else:
        buffer = file_or_buffer

    # Try pdfplumber first for rich text + table extraction
    pdfplumber_success = False
    try:
        import pdfplumber
        with pdfplumber.open(buffer) as pdf:
            page_count = len(pdf.pages)
            for idx, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                extracted_pages.append(f"--- Page {idx + 1} ---\n{text}")

                # Extract tables on page
                tables = page.extract_tables()
                for table in tables:
                    if table and len(table) > 1:
                        headers = [str(h or f"Col_{i}").strip() for i, h in enumerate(table[0])]
                        rows = table[1:]
                        table_df = pd.DataFrame(rows, columns=headers)
                        extracted_tables.append(table_df)

        pdfplumber_success = True
    except ImportError:
        pass
    except Exception as ex:
        artifact.warnings.append(f"pdfplumber extraction note: {str(ex)}")

    # Fallback to PyMuPDF (fitz) if pdfplumber not present or failed
    if not pdfplumber_success:
        try:
            import fitz
            buffer.seek(0)
            doc = fitz.open(stream=buffer.read(), filetype="pdf")
            page_count = len(doc)
            for idx, page in enumerate(doc):
                text = page.get_text() or ""
                extracted_pages.append(f"--- Page {idx + 1} ---\n{text}")
            doc.close()
        except ImportError:
            if not pdfplumber_success:
                artifact.errors.append("Neither 'pdfplumber' nor 'PyMuPDF' (fitz) is available to parse PDF.")
        except Exception as ex:
            artifact.errors.append(f"Failed to read PDF document: {str(ex)}")

    artifact.page_count = page_count
    full_text = "\n\n".join(extracted_pages).strip()
    artifact.extracted_text = full_text
    artifact.tables = extracted_tables

    # Check for scanned PDF: pages exist but total extracted characters < 60
    if page_count > 0 and len(full_text.strip()) < 60:
        artifact.is_scanned_pdf = True
        artifact.warnings.append("Scanned PDF detected: page text layer is empty or image-based.")

    # If tables were extracted, set the largest table as primary dataframe for analysis
    if extracted_tables:
        largest_table = max(extracted_tables, key=lambda t: len(t) * len(t.columns))
        artifact.dataframe = largest_table
        _populate_df_metadata(artifact)

    return artifact


def load_file_artifact(
    file_or_buffer: Any,
    filename: str
) -> DatasetArtifact:
    """
    Auto-detect file format by filename extension and dispatch to the appropriate loader.
    """
    ext = os.path.splitext(filename)[1].lower()

    if ext == ".csv":
        return load_csv_artifact(file_or_buffer, filename=filename)
    elif ext in [".xlsx", ".xls"]:
        return load_excel_artifact(file_or_buffer, filename=filename)
    elif ext == ".json":
        return load_json_artifact(file_or_buffer, filename=filename)
    elif ext == ".parquet":
        return load_parquet_artifact(file_or_buffer, filename=filename)
    elif ext == ".tsv":
        return load_tsv_artifact(file_or_buffer, filename=filename)
    elif ext == ".pdf":
        return load_pdf_artifact(file_or_buffer, filename=filename)
    elif ext == ".txt":
        # Handle TXT either as delimited tabular or raw text
        source_id = str(uuid.uuid4())
        try:
            content = file_or_buffer.read() if hasattr(file_or_buffer, "read") else file_or_buffer
            if isinstance(content, bytes):
                content = content.decode("utf-8", errors="replace")
            # Try parsing as CSV/TSV if header row detected
            lines = content.strip().split("\n")
            if len(lines) > 1 and ("\t" in lines[0] or "," in lines[0]):
                sep = "\t" if "\t" in lines[0] else ","
                df = pd.read_csv(io.StringIO(content), sep=sep)
                artifact = DatasetArtifact(
                    source_id=source_id,
                    filename=filename,
                    source_type="txt",
                    dataframe=df,
                    extracted_text=content
                )
                return _populate_df_metadata(artifact)
            else:
                return DatasetArtifact(
                    source_id=source_id,
                    filename=filename,
                    source_type="txt",
                    extracted_text=content
                )
        except Exception as ex:
            return DatasetArtifact(
                source_id=source_id,
                filename=filename,
                source_type="txt",
                errors=[f"Failed to read text file: {str(ex)}"]
            )
    else:
        # Unknown extension - attempt CSV parse as default
        try:
            return load_csv_artifact(file_or_buffer, filename=filename)
        except Exception:
            return DatasetArtifact(
                source_id=str(uuid.uuid4()),
                filename=filename,
                source_type="unknown",
                errors=[f"Unsupported file format: {ext}"]
            )


def get_synthetic_artifact(
    num_records: int = 3000,
    seed: int = 42
) -> DatasetArtifact:
    """
    Generate the benchmark reproducible synthetic e-commerce sales dataset.
    """
    df = generate_ecommerce_dataset(num_records=num_records, seed=seed)
    artifact = DatasetArtifact(
        source_id=str(uuid.uuid4()),
        filename=f"synthetic_sales_{num_records}.csv",
        source_type="synthetic",
        dataframe=df,
        metadata={"record_count": num_records, "random_seed": seed}
    )
    return _populate_df_metadata(artifact)
