import re
from typing import List, Tuple, Dict, Any, Optional
import pandas as pd
from app.services.detection.base import QualityIssue

# Robust RFC-compliant email regex
EMAIL_REGEX = re.compile(
    r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$"
)

# Common date formats regex detector
DATE_FORMAT_REGEX = re.compile(
    r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}$|^\d{1,2}[-/]\d{1,2}[-/]\d{4}$|^\d{4}[-/]\d{1,2}[-/]\d{1,2}[ T]\d{1,2}:\d{2}"
)

# Phone number regex detector (international, dashed, dotted, bracketed)
PHONE_REGEX = re.compile(
    r"^\+?[0-9]{1,4}?[-.\s]?\(?[0-9]{1,4}?\)?[-.\s]?[0-9]{1,4}[-.\s]?[0-9]{1,9}$"
)


def _get_name_tokens(col_name: str) -> set:
    """Extract individual words/tokens from a column name."""
    return set(re.split(r'[^a-zA-Z0-9]+', col_name.lower()))


def is_email_column(col_name: str, sample_values: List[str]) -> bool:
    """Check if column is intended to contain email addresses."""
    col_lower = col_name.lower()
    tokens = _get_name_tokens(col_name)

    name_matches = bool(
        tokens & {"email", "emails"} or
        col_lower.endswith(("_email", "_mail")) or
        col_lower.startswith("email")
    )
    if name_matches:
        if not sample_values:
            return True
        # Verify at least one value has '@' and no spaces
        return any("@" in val and " " not in val.strip() for val in sample_values)

    if not sample_values:
        return False

    # Data-driven heuristic: >= 30% of sample values look like standalone emails
    match_count = sum(1 for val in sample_values if "@" in val and "." in val and " " not in val.strip())
    return (match_count / len(sample_values)) >= 0.30


def is_phone_column(col_name: str, sample_values: List[str]) -> bool:
    """Check if column is intended to contain phone numbers."""
    # Disambiguate against dates: if column matches date heuristics, it is not a phone column
    if is_date_column(col_name, sample_values):
        return False

    col_lower = col_name.lower()
    tokens = _get_name_tokens(col_name)
    phone_tokens = {"phone", "mobile", "cell", "tel", "telephone", "cellphone", "fax", "contact_no"}

    name_matches = bool(
        tokens & phone_tokens or
        col_lower.endswith(("_phone", "_mobile", "_cell", "_tel")) or
        col_lower.startswith(("phone", "mobile", "tel"))
    )
    if name_matches:
        if not sample_values:
            return True
        return any(any(c.isdigit() for c in val) for val in sample_values)

    if not sample_values:
        return False

    def looks_like_phone(val: str) -> bool:
        v = val.strip()
        # Exclude dates that happen to match phone regex
        if DATE_FORMAT_REGEX.search(v):
            return False
        digits = [c for c in v if c.isdigit()]
        return 7 <= len(digits) <= 15 and bool(PHONE_REGEX.match(v))

    match_count = sum(1 for val in sample_values if looks_like_phone(val))
    return (match_count / len(sample_values)) >= 0.40


def is_date_column(col_name: str, sample_values: List[str]) -> bool:
    """Check if column is intended to contain date or datetime entries."""
    col_lower = col_name.lower()
    tokens = _get_name_tokens(col_name)
    date_tokens = {
        "date", "dob", "birth", "created", "updated", "timestamp",
        "joined", "expiry", "deadline", "hire_date", "datetime"
    }

    name_matches = bool(
        tokens & date_tokens or
        col_lower.endswith(("_date", "_at", "_time")) or
        col_lower.startswith("date_")
    )
    if name_matches:
        if not sample_values:
            return True
        for v in sample_values:
            if DATE_FORMAT_REGEX.search(v.strip()):
                return True
            try:
                p = pd.to_datetime(v.strip(), errors="coerce", format="mixed")
                if pd.notna(p):
                    return True
            except Exception:
                pass
        return False

    if not sample_values:
        return False

    match_count = sum(1 for val in sample_values if DATE_FORMAT_REGEX.search(val.strip()))
    return (match_count / len(sample_values)) >= 0.40


def is_numeric_string_column(col_name: str, sample_values: List[str]) -> bool:
    """Check if column is intended to be purely numeric (e.g. price, quantity, zip, age)."""
    col_lower = col_name.lower()
    tokens = _get_name_tokens(col_name)
    num_tokens = {
        "price", "amount", "salary", "cost", "total", "quantity",
        "count", "age", "zip", "postal", "year", "score", "revenue", "income"
    }

    name_matches = bool(
        tokens & num_tokens or
        col_lower.endswith(("_amount", "_price", "_cost", "_count", "_score", "_qty"))
    )
    if name_matches:
        if not sample_values:
            return True
        match_count = 0
        for v in sample_values:
            clean = re.sub(r'[\$,€£%\s]', '', v)
            try:
                float(clean)
                match_count += 1
            except ValueError:
                pass
        return (match_count / len(sample_values)) >= 0.20

    if not sample_values:
        return False

    match_count = 0
    for v in sample_values:
        clean = re.sub(r'[\$,€£%\s]', '', v)
        try:
            float(clean)
            match_count += 1
        except ValueError:
            pass
    return (match_count / len(sample_values)) >= 0.50


def validate_email(val: str) -> Optional[str]:
    """Return reason if email is invalid, else None."""
    val = val.strip()
    if not val or val.lower() in ("null", "none", "n/a", "-", "nil", "unknown"):
        return None
    if not EMAIL_REGEX.match(val):
        if "@" not in val:
            return "Missing '@' symbol"
        if val.count("@") > 1:
            return "Multiple '@' symbols"
        if not re.search(r"\.[a-zA-Z]{2,}$", val):
            return "Missing or invalid domain extension (.com, .org, etc.)"
        return "Invalid email characters or structure"
    return None


def validate_phone(val: str) -> Optional[str]:
    """Return reason if phone number string is invalid, else None."""
    val = val.strip()
    if not val or val.lower() in ("null", "none", "n/a", "-", "nil", "unknown"):
        return None
    if any(c.isalpha() for c in val):
        return f"Contains alphabetical characters in phone field: '{val}'"
    digits = [c for c in val if c.isdigit()]
    if len(digits) < 7:
        return f"Phone number has too few digits ({len(digits)} digits; expected 7-15): '{val}'"
    if len(digits) > 15:
        return f"Phone number exceeds maximum standard length ({len(digits)} digits; expected 7-15): '{val}'"
    if not PHONE_REGEX.match(val):
        return f"Invalid phone format structure: '{val}'"
    return None


def validate_date(val: str) -> Optional[str]:
    """Return reason if date string is unparseable or invalid, else None."""
    val = val.strip()
    if not val or val.lower() in ("null", "none", "n/a", "-", "nil", "unknown"):
        return None
    try:
        parsed = pd.to_datetime(val, errors="coerce", format="mixed")
        if pd.isna(parsed):
            return f"Unparseable date expression: '{val}'"
        if parsed.year < 1850 or parsed.year > 2150:
            return f"Year {parsed.year} is outside plausible range (1850-2150)"
        return None
    except Exception as e:
        return f"Date format parse error: {str(e)}"


def validate_numeric(val: str) -> Optional[str]:
    """Return reason if numeric string contains invalid characters, else None."""
    val = val.strip()
    if not val or val.lower() in ("null", "none", "n/a", "-", "nil", "unknown"):
        return None
    clean = re.sub(r'[\$,€£%]', '', val).strip()
    try:
        float(clean)
        if re.search(r'[\$,€£%]', val):
            return f"Contains currency or percentage symbol in numeric field: '{val}'"
        return None
    except ValueError:
        return f"Cannot parse as valid number: '{val}'"


def detect_invalid_formats(df: pd.DataFrame) -> List[QualityIssue]:
    """
    Detect format violations in columns that represent emails, phones, dates, or numeric strings.
    Does not assume every string column is an email or date.
    """
    issues: List[QualityIssue] = []
    total_rows = len(df)
    if total_rows == 0:
        return issues

    for col_idx in range(len(df.columns)):
        series = df.iloc[:, col_idx]
        col_str = str(df.columns[col_idx])

        # Only inspect object/string columns or mixed types
        if series.dtype != "object" and not pd.api.types.is_string_dtype(series):
            continue

        non_null_mask = series.notna()
        non_null_series = series[non_null_mask].astype(str)
        if non_null_series.empty:
            continue

        sample_vals = non_null_series.head(30).tolist()

        # 1. Email Format Check
        if is_email_column(col_str, sample_vals):
            invalid_email_rows: List[int] = []
            sample_invalid_emails: List[str] = []
            reasons: List[str] = []

            for idx, raw_val in enumerate(series):
                if pd.isna(raw_val):
                    continue
                reason = validate_email(str(raw_val))
                if reason:
                    invalid_email_rows.append(idx + 1)
                    if len(sample_invalid_emails) < 5:
                        sample_invalid_emails.append(f"Row {idx + 1}: '{raw_val}' ({reason})")
                    if reason not in reasons and len(reasons) < 3:
                        reasons.append(reason)

            if invalid_email_rows:
                pct = round((len(invalid_email_rows) / total_rows) * 100, 2)
                issues.append(
                    QualityIssue(
                        id="",
                        category="invalid_format",
                        severity="critical",
                        column=col_str,
                        title=f"Invalid Email Formats in '{col_str}'",
                        description=(
                            f"Detected {len(invalid_email_rows)} invalid email address(es) ({pct}%) in '{col_str}'. "
                            f"Violations: {'; '.join(reasons)}."
                        ),
                        row_indices=invalid_email_rows,
                        affected_count=len(invalid_email_rows),
                        sample_values=sample_invalid_emails,
                        suggested_action="Correct malformed domain extensions, fix missing '@' symbols, or request verified addresses.",
                        metadata={
                            "expected_format": "user@example.com",
                            "invalid_count": len(invalid_email_rows),
                            "invalid_percentage": pct,
                        },
                    )
                )
            continue

        # 2. Date Format Check
        if is_date_column(col_str, sample_vals):
            invalid_date_rows: List[int] = []
            sample_invalid_dates: List[str] = []

            for idx, raw_val in enumerate(series):
                if pd.isna(raw_val):
                    continue
                val_str = str(raw_val).strip()
                if not val_str:
                    continue
                reason = validate_date(val_str)
                if reason:
                    invalid_date_rows.append(idx + 1)
                    if len(sample_invalid_dates) < 5:
                        sample_invalid_dates.append(f"Row {idx + 1}: '{val_str}'")

            if invalid_date_rows:
                pct = round((len(invalid_date_rows) / total_rows) * 100, 2)
                issues.append(
                    QualityIssue(
                        id="",
                        category="invalid_format",
                        severity="warning",
                        column=col_str,
                        title=f"Invalid Date Formats in '{col_str}'",
                        description=(
                            f"Detected {len(invalid_date_rows)} unparseable or out-of-range date value(s) ({pct}%) in '{col_str}'."
                        ),
                        row_indices=invalid_date_rows,
                        affected_count=len(invalid_date_rows),
                        sample_values=sample_invalid_dates,
                        suggested_action="Standardize date strings to ISO-8601 format (YYYY-MM-DD).",
                        metadata={
                            "expected_format": "YYYY-MM-DD",
                            "invalid_count": len(invalid_date_rows),
                            "invalid_percentage": pct,
                        },
                    )
                )
            continue

        # 3. Phone Number Format Check
        if is_phone_column(col_str, sample_vals):
            invalid_phone_rows: List[int] = []
            sample_invalid_phones: List[str] = []
            phone_reasons: List[str] = []

            for idx, raw_val in enumerate(series):
                if pd.isna(raw_val):
                    continue
                val_str = str(raw_val).strip()
                if not val_str:
                    continue
                reason = validate_phone(val_str)
                if reason:
                    invalid_phone_rows.append(idx + 1)
                    if len(sample_invalid_phones) < 5:
                        sample_invalid_phones.append(f"Row {idx + 1}: '{val_str}' ({reason})")
                    if reason not in phone_reasons and len(phone_reasons) < 3:
                        phone_reasons.append(reason)

            if invalid_phone_rows:
                pct = round((len(invalid_phone_rows) / total_rows) * 100, 2)
                issues.append(
                    QualityIssue(
                        id="",
                        category="invalid_format",
                        severity="warning",
                        column=col_str,
                        title=f"Invalid Phone Numbers in '{col_str}'",
                        description=(
                            f"Detected {len(invalid_phone_rows)} invalid phone number(s) ({pct}%) in '{col_str}'. "
                            f"Violations: {'; '.join(phone_reasons)}."
                        ),
                        row_indices=invalid_phone_rows,
                        affected_count=len(invalid_phone_rows),
                        sample_values=sample_invalid_phones,
                        suggested_action="Standardize phone numbers using E.164 or canonical international format.",
                        metadata={
                            "expected_format": "+1-555-010-0199 or 10-15 digits",
                            "invalid_count": len(invalid_phone_rows),
                            "invalid_percentage": pct,
                        },
                    )
                )
            continue

        # 4. Numeric String Check
        if is_numeric_string_column(col_str, sample_vals):
            invalid_num_rows: List[int] = []
            sample_invalid_nums: List[str] = []

            for idx, raw_val in enumerate(series):
                if pd.isna(raw_val):
                    continue
                val_str = str(raw_val).strip()
                if not val_str:
                    continue
                reason = validate_numeric(val_str)
                if reason:
                    invalid_num_rows.append(idx + 1)
                    if len(sample_invalid_nums) < 5:
                        sample_invalid_nums.append(f"Row {idx + 1}: '{val_str}' ({reason})")

            if invalid_num_rows:
                pct = round((len(invalid_num_rows) / total_rows) * 100, 2)
                issues.append(
                    QualityIssue(
                        id="",
                        category="invalid_format",
                        severity="warning",
                        column=col_str,
                        title=f"Non-numeric Values in '{col_str}'",
                        description=(
                            f"Detected {len(invalid_num_rows)} text or corrupted entry/entries ({pct}%) in numeric column '{col_str}'."
                        ),
                        row_indices=invalid_num_rows,
                        affected_count=len(invalid_num_rows),
                        sample_values=sample_invalid_nums,
                        suggested_action="Strip currency/unit symbols or convert non-numeric tokens into null/zero.",
                        metadata={
                            "expected_format": "Standard Float / Integer",
                            "invalid_count": len(invalid_num_rows),
                            "invalid_percentage": pct,
                        },
                    )
                )

    return issues
