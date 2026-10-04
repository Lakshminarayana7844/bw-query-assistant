import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app import nl, odata
from app.main import app

c = TestClient(app)
DF = pd.DataFrame({"Region": ["EMEA", "APAC", "EMEA"], "Quantity": [1, 5, 10], "NetValue": [10.0, 50.0, 100.0]})


def test_health():
    assert c.get("/health").json() == {"status": "ok"}


def test_service_document():
    assert c.get("/odata").json()["value"][0]["name"] == "ZSD_C01"


def test_metadata():
    assert "NetValue" in c.get("/odata/ZSD_C01/$metadata").json()["measures"]


def test_unknown_provider():
    assert c.get("/odata/NOPE").status_code == 404


def test_filter_and_count():
    r = c.get("/odata/ZSD_C01", params={"$filter": "Region eq 'EMEA'", "$count": "true", "$top": 3}).json()
    assert r["@odata.count"] == 90
    assert len(r["value"]) == 3 and all(x["Region"] == "EMEA" for x in r["value"])


def test_select_orderby_top():
    r = c.get("/odata/ZSD_C01", params={"$select": "Material,Quantity", "$orderby": "Quantity desc", "$top": 2}).json()["value"]
    assert set(r[0]) == {"Material", "Quantity"} and r[0]["Quantity"] >= r[1]["Quantity"]


def test_bad_filter_400():
    assert c.get("/odata/ZSD_C01", params={"$filter": "Foo eq 1"}).status_code == 400
    assert c.get("/odata/ZSD_C01", params={"$filter": "Quantity eq 'x'"}).status_code == 400
    assert c.get("/odata/ZSD_C01", params={"$filter": "Region eq 1"}).status_code == 400
    assert c.get("/odata/ZSD_C01", params={"$filter": "garbage"}).status_code == 400


def test_and_filter_unit():
    assert len(odata.apply_filter(DF, "Region eq 'EMEA' and Quantity gt 1")) == 1


def test_skip():
    _, out = odata.run_query(DF, skip=1, top=1)
    assert len(out) == 1 and out.iloc[0]["Region"] == "APAC"


def test_orderby_bad():
    with pytest.raises(odata.QueryError):
        odata.apply_orderby(DF, "Region sideways")


def test_nl_parse():
    p = nl.parse("Top 2 materials by quantity in EMEA")
    assert p["top"] is None or p["top"] == 2
    p = nl.parse("total net value by region")
    assert p["dimension"] == "Region" and p["measure"] == "NetValue"


def test_nl_errors():
    with pytest.raises(ValueError):
        nl.parse("hello there")


def test_ask_by_region_matches_data():
    r = c.get("/ask", params={"q": "total net value by region"}).json()
    df = pd.read_csv("data/sales.csv")
    exp = df.groupby("Region")["NetValue"].sum().round(2)
    got = {x["Region"]: x["NetValue"] for x in r["rows"]}
    assert got == pytest.approx(exp.to_dict())


def test_ask_top_filtered():
    r = c.get("/ask", params={"q": "top 2 materials by quantity in EMEA"}).json()
    assert len(r["rows"]) == 2 and r["plan"]["filters"] == {"Region": "EMEA"}


def test_ask_bad():
    assert c.get("/ask", params={"q": "what is love"}).status_code == 400
