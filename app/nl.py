"""Rule based natural language to query. No LLM, no API key, fully deterministic."""
import re

MEASURES = {"net value": "NetValue", "revenue": "NetValue", "sales": "NetValue", "quantity": "Quantity", "units": "Quantity"}
DIMS = {"region": "Region", "material": "Material", "product": "Material", "sales org": "SalesOrg", "day": "CalendarDay"}


def parse(question: str) -> dict:
    q = question.lower().strip().rstrip("?.")
    measure = next((v for k, v in MEASURES.items() if k in q), None)
    if measure is None:
        raise ValueError("could not find a measure (try: net value, revenue, quantity)")
    m = re.search(r"\bby (region|material|product|sales org|day)\b", q)
    dim = DIMS[m.group(1)] if m else None
    if dim is None:
        # "top 3 materials by quantity": the dimension comes right after "top N"
        t2 = re.search(r"\btop \d+ (region|material|product|sales org|day)s?\b", q)
        if t2:
            dim = DIMS[t2.group(1)]
    agg = "mean" if re.search(r"\b(average|avg|mean)\b", q) else "sum"
    top = None
    t = re.search(r"\btop (\d+)\b", q)
    if t:
        top = int(t.group(1))
    filters = {}
    for region in ("emea", "apac", "amer"):
        if re.search(rf"\b{region}\b", q):
            filters["Region"] = region.upper()
    mm = re.search(r"\bm-\d{3}\b", q)
    if mm:
        filters["Material"] = mm.group(0).upper()
    if dim is None and top is None and not filters and agg == "sum" and "total" not in q:
        raise ValueError("could not find what to group by (try: 'total net value by region')")
    return {"measure": measure, "dimension": dim, "agg": agg, "top": top, "filters": filters}
