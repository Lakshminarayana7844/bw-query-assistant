"""Small OData-style query parser: $filter, $select, $orderby, $top, $skip."""
import re
import pandas as pd

OPS = {"eq": "==", "ne": "!=", "gt": ">", "ge": ">=", "lt": "<", "le": "<="}
TOKEN = re.compile(r"^\s*(\w+)\s+(eq|ne|gt|ge|lt|le)\s+('(?:[^']*)'|-?\d+(?:\.\d+)?)\s*$")


class QueryError(ValueError):
    pass


def apply_filter(df: pd.DataFrame, expr: str) -> pd.DataFrame:
    if not expr:
        return df
    for part in re.split(r"\s+and\s+", expr.strip()):
        m = TOKEN.match(part)
        if not m:
            raise QueryError(f"cannot parse filter part: {part!r}")
        col, op, raw = m.groups()
        if col not in df.columns:
            raise QueryError(f"unknown field: {col}")
        if raw.startswith("'"):
            val = raw[1:-1]
        else:
            val = float(raw)
        series = df[col]
        if pd.api.types.is_numeric_dtype(series) and isinstance(val, str):
            raise QueryError(f"field {col} is numeric")
        if not pd.api.types.is_numeric_dtype(series) and not isinstance(val, str):
            raise QueryError(f"field {col} is text, use quotes")
        df = df[_cmp(series, op, val)]
    return df


def _cmp(s, op, v):
    return {"eq": s == v, "ne": s != v, "gt": s > v, "ge": s >= v, "lt": s < v, "le": s <= v}[op]


def apply_select(df: pd.DataFrame, expr: str) -> pd.DataFrame:
    if not expr:
        return df
    cols = [c.strip() for c in expr.split(",") if c.strip()]
    bad = [c for c in cols if c not in df.columns]
    if bad:
        raise QueryError(f"unknown field: {bad[0]}")
    return df[cols]


def apply_orderby(df: pd.DataFrame, expr: str) -> pd.DataFrame:
    if not expr:
        return df
    cols, asc = [], []
    for part in expr.split(","):
        bits = part.strip().split()
        if not bits or len(bits) > 2 or (len(bits) == 2 and bits[1] not in ("asc", "desc")):
            raise QueryError(f"cannot parse orderby: {part!r}")
        if bits[0] not in df.columns:
            raise QueryError(f"unknown field: {bits[0]}")
        cols.append(bits[0])
        asc.append(not (len(bits) == 2 and bits[1] == "desc"))
    return df.sort_values(cols, ascending=asc, kind="stable")


def run_query(df, filter=None, select=None, orderby=None, top=None, skip=0):
    df = apply_filter(df, filter or "")
    total = len(df)
    df = apply_orderby(df, orderby or "")
    df = df.iloc[skip:]
    if top is not None:
        df = df.iloc[:top]
    df = apply_select(df, select or "")
    return total, df
