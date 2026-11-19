import math
import re
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
from app.services.detection.base import QualityIssue


def is_identifier_or_discrete_code(col_name: str, series: pd.Series) -> bool:
    """
    Determine if a column represents an identifier, phone number, postal code,
    or categorical code rather than a continuous numeric measurement.
    Such columns should not be analyzed for statistical distribution outliers (IQR/Z-score).
    """
    col_lower = str(col_name).lower().strip()
    tokens = set(re.split(r'[^a-zA-Z0-9]+', col_lower))

    # Measurement keywords that must ALWAYS be treated as numeric measurements
    MEASUREMENT_TERMS = {
        "age", "amount", "salary", "price", "cost", "revenue", "profit",
        "loss", "score", "rating", "count", "quantity", "qty", "discount",
        "temp", "temperature", "weight", "height", "length", "width", "depth",
        "distance", "duration", "speed", "balance", "total", "tax", "fee",
        "rate", "pct", "percentage", "ratio", "hours", "days", "years", "volume",
        "spend", "sales", "income", "wage", "target", "budget", "unit_price"
    }
    has_measurement_term = bool(tokens & MEASUREMENT_TERMS) or any(
        m in col_lower for m in ["purchase_amount", "total_amount", "net_amount", "gross_amount", "unit_cost"]
    )

    # 1. Phone number detection (by column name or data pattern)
    PHONE_TERMS = {
        "phone", "mobile", "cell", "tel", "telephone", "cellphone", "fax",
        "contact_no", "contact_number", "phone_no", "phone_num", "mobile_no"
    }
    if bool(tokens & PHONE_TERMS) or any(col_lower.endswith(s) for s in ["_phone", "_mobile", "_cell", "_tel"]):
        return True

    # 2. Identifier / ID detection
    ID_TERMS = {
        "id", "uuid", "guid", "ssn", "ein", "pan", "aadhaar", "sin", "sku",
        "isbn", "upc", "ean", "vin", "imei", "cust_id", "user_id", "account_id",
        "client_id", "order_id", "emp_id", "uid", "cid", "pid", "tid", "qid"
    }
    if bool(tokens & ID_TERMS) or col_lower in ID_TERMS:
        return True

    if col_lower == "id" or col_lower.endswith(("_id", "_ident", "_identifier", "_key", "_uuid", "_guid")):
        return True

    if col_lower.startswith(("id_", "uuid_", "guid_")):
        return True

    # Account, card, license, policy, customer, employee numbers
    ID_NUMBER_PREFIXES = (
        "account", "acct", "card", "license", "policy", "customer", "client",
        "member", "patient", "emp", "employee", "order", "invoice", "txn",
        "transaction", "ticket", "serial", "reg", "registration", "badge"
    )
    if any(prefix in tokens for prefix in ID_NUMBER_PREFIXES) and any(suffix in tokens for suffix in ["no", "num", "number", "code", "id"]):
        return True

    # 3. Postal / Zip code detection
    POSTAL_TERMS = {"zip", "zipcode", "postal", "postcode", "pincode"}
    if bool(tokens & POSTAL_TERMS) or any(col_lower.endswith(s) for s in ["_zip", "_postal", "_postcode", "_pin", "_pincode"]):
        return True

    # 4. Discrete Code / Key terms (unless measurement)
    if not has_measurement_term:
        if bool(tokens & {"code", "key"}) and not bool(tokens & {"score", "count", "amount", "price"}):
            return True

    # 5. Semantic phone pattern in data values (even if column is just named 'contact' or 'number')
    non_null_samples = [str(x).strip() for x in series.dropna().iloc[:30] if str(x).strip()]
    if non_null_samples and not has_measurement_term:
        digits_lengths = [len(re.sub(r'\D', '', s)) for s in non_null_samples]
        if digits_lengths and all(9 <= dl <= 15 for dl in digits_lengths) and any(kw in col_lower for kw in ["contact", "number", "num", "dial"]):
            return True

    return False


def detect_statistical_anomalies(df: pd.DataFrame) -> List[QualityIssue]:
    """
    Detect statistical outliers and anomalies in numerical columns using IQR and Z-Score.
    Safely handles small datasets, constant columns, and infinite values.
    Flags anomalies for human inspection rather than treating them automatically as errors.
    Semantic check: excludes identifier columns, phone numbers, and postal codes.
    """
    issues: List[QualityIssue] = []
    total_rows = len(df)
    if total_rows < 4:
        # Small dataset safeguard: statistical distributions are not reliable with < 4 points
        return issues

    for col_idx in range(len(df.columns)):
        series = df.iloc[:, col_idx]
        col = df.columns[col_idx]
        col_str = str(col)

        # Semantic safeguard: Skip identifier columns, phone numbers, postal codes, and discrete codes
        if is_identifier_or_discrete_code(col_str, series):
            continue

        # Extract numeric series
        if not pd.api.types.is_numeric_dtype(series):
            # Attempt numeric coercion only if column is mostly numeric
            numeric_coerced = pd.to_numeric(series, errors="coerce")
            if numeric_coerced.notna().sum() < 4 or (numeric_coerced.notna().sum() / total_rows) < 0.6:
                continue
            num_series = numeric_coerced
        else:
            num_series = series

        valid_mask = num_series.notna()
        finite_mask = valid_mask & np.isfinite(num_series)
        inf_mask = valid_mask & (~finite_mask)
        finite_count = int(finite_mask.sum())

        if finite_count < 4 and not inf_mask.any():
            continue

        clean_vals = num_series[finite_mask].astype(float)

        # Constant column safeguard: if standard deviation is 0, no distribution anomalies exist
        std_val = float(clean_vals.std()) if len(clean_vals) > 1 else 0.0
        mean_val = float(clean_vals.mean()) if len(clean_vals) > 0 else 0.0

        # 1. IQR Method on finite values
        if len(clean_vals) >= 4 and std_val > 0.0 and not math.isnan(std_val):
            q1 = float(clean_vals.quantile(0.25))
            q3 = float(clean_vals.quantile(0.75))
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr if iqr > 0 else mean_val - 3 * std_val
            upper_bound = q3 + 1.5 * iqr if iqr > 0 else mean_val + 3 * std_val
            extreme_lower = q1 - 3.0 * iqr if iqr > 0 else mean_val - 4 * std_val
            extreme_upper = q3 + 3.0 * iqr if iqr > 0 else mean_val + 4 * std_val
        else:
            q1 = q3 = iqr = lower_bound = upper_bound = extreme_lower = extreme_upper = 0.0

        anomalous_rows: List[int] = []
        anomaly_details: List[Dict[str, Any]] = []
        has_extreme = False

        # First add infinite values as extreme anomalies
        if inf_mask.any():
            for idx, is_inf in enumerate(inf_mask):
                if is_inf:
                    row_num = idx + 1
                    anomalous_rows.append(row_num)
                    has_extreme = True
                    val_str = str(num_series.iloc[idx])
                    anomaly_details.append({
                        "row": row_num,
                        "value": val_str,
                        "z_score": 99.99,
                        "is_extreme": True,
                        "bound_violation": "infinite_value",
                    })

        # Next evaluate finite values if distribution exists
        if std_val > 0.0 and not math.isnan(std_val):
            for idx, val in enumerate(num_series):
                if pd.isna(val) or not np.isfinite(val):
                    continue
                val_float = float(val)

                # Calculate Z-score
                z_score = abs((val_float - mean_val) / std_val)

                # Condition: outside IQR bounds OR |Z| > 3.0
                is_iqr_outlier = val_float < lower_bound or val_float > upper_bound
                is_z_outlier = z_score >= 3.0

                if is_iqr_outlier or is_z_outlier:
                    row_num = idx + 1
                    anomalous_rows.append(row_num)

                    is_extreme = (val_float < extreme_lower or val_float > extreme_upper or z_score >= 4.0)
                    if is_extreme:
                        has_extreme = True

                    anomaly_details.append({
                        "row": row_num,
                        "value": round(val_float, 4),
                        "z_score": round(z_score, 2),
                        "is_extreme": is_extreme,
                        "bound_violation": "below_lower" if val_float < lower_bound else "above_upper",
                    })

        if anomalous_rows:
            pct = round((len(anomalous_rows) / total_rows) * 100, 2)
            severity = "warning" if has_extreme else "info"

            sample_strings = [
                f"Row {a['row']}: {a['value']} (Z={a['z_score']}, {'Extreme' if a['is_extreme'] else 'Mild'})"
                for a in anomaly_details[:5]
            ]

            desc_parts = [f"Detected {len(anomalous_rows)} statistical outlier(s) ({pct}%) in '{col}'."]
            if std_val > 0.0:
                desc_parts.append(
                    f"Outside expected bounds [{round(lower_bound, 2)}, {round(upper_bound, 2)}]. "
                    f"Distribution baseline: Mean={round(mean_val, 2)}, Std={round(std_val, 2)}, IQR={round(iqr, 2)}."
                )

            issues.append(
                QualityIssue(
                    id="",
                    category="statistical_anomaly",
                    severity=severity,
                    column=str(col),
                    title=f"Statistical Anomalies in '{col}'",
                    description=" ".join(desc_parts),
                    row_indices=anomalous_rows,
                    affected_count=len(anomalous_rows),
                    sample_values=sample_strings,
                    suggested_action=(
                        "Inspect flagged outlier values to determine if they reflect rare genuine extremes "
                        "or measurement/entry errors requiring trimming or capping."
                    ),
                    metadata={
                        "outlier_count": len(anomalous_rows),
                        "outlier_percentage": pct,
                        "mean": round(mean_val, 4) if std_val > 0 else None,
                        "std": round(std_val, 4) if std_val > 0 else None,
                        "q1": round(q1, 4) if std_val > 0 else None,
                        "q3": round(q3, 4) if std_val > 0 else None,
                        "iqr": round(iqr, 4) if std_val > 0 else None,
                        "lower_bound": round(lower_bound, 4) if std_val > 0 else None,
                        "upper_bound": round(upper_bound, 4) if std_val > 0 else None,
                        "extreme_count": sum(1 for a in anomaly_details if a["is_extreme"]),
                        "anomalies": anomaly_details[:30],
                    },
                )
            )

    return issues
