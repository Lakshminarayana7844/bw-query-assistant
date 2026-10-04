from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException, Query

from . import nl, odata

DATA = Path(__file__).resolve().parent.parent / "data" / "sales.csv"

app = FastAPI(title="BW Query Assistant", version="1.0.0")

PROVIDERS = {
    "ZSD_C01": {
        "description": "Sales cube (sample)",
        "dimensions": ["CalendarDay", "Material", "Region", "SalesOrg"],
        "measures": ["Quantity", "NetValue"],
        "attributes": ["Currency"],
    }
}


def load(provider: str) -> pd.DataFrame:
    if provider not in PROVIDERS:
        raise HTTPException(404, f"unknown InfoProvider: {provider}")
    return pd.read_csv(DATA)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/odata")
def service_document():
    return {"value": [{"name": k, "url": k} for k in PROVIDERS]}


@app.get("/odata/{provider}/$metadata")
def metadata(provider: str):
    if provider not in PROVIDERS:
        raise HTTPException(404, f"unknown InfoProvider: {provider}")
    return PROVIDERS[provider]


@app.get("/odata/{provider}")
def query(
    provider: str,
    filter: str | None = Query(None, alias="$filter"),
    select: str | None = Query(None, alias="$select"),
    orderby: str | None = Query(None, alias="$orderby"),
    top: int | None = Query(None, alias="$top", ge=0, le=1000),
    skip: int = Query(0, alias="$skip", ge=0),
    count: bool = Query(False, alias="$count"),
):
    df = load(provider)
    try:
        total, out = odata.run_query(df, filter, select, orderby, top, skip)
    except odata.QueryError as e:
        raise HTTPException(400, str(e))
    body = {"value": out.to_dict(orient="records")}
    if count:
        body["@odata.count"] = total
    return body


@app.get("/ask")
def ask(q: str = Query(..., min_length=3)):
    try:
        plan = nl.parse(q)
    except ValueError as e:
        raise HTTPException(400, str(e))
    df = load("ZSD_C01")
    for col, val in plan["filters"].items():
        df = df[df[col] == val]
    m = plan["measure"]
    if plan["dimension"]:
        res = df.groupby(plan["dimension"])[m].agg(plan["agg"]).round(2).sort_values(ascending=False)
        if plan["top"]:
            res = res.head(plan["top"])
        rows = [{plan["dimension"]: k, m: float(v)} for k, v in res.items()]
    else:
        rows = [{m: round(float(df[m].agg(plan["agg"])), 2)}]
    return {"plan": plan, "rows": rows}
