# BW Query Assistant

A small FastAPI service that serves SAP BW/4HANA style InfoProvider data through an OData-like REST API, plus a rule based natural language endpoint. It runs offline with sample sales data, so anyone can clone it and try it in a minute.

![CI](https://github.com/Lakshminarayana7844/bw-query-assistant/actions/workflows/ci.yml/badge.svg)

## Why

In BW/4HANA projects, consumers (SAPUI5 apps, Fiori tiles, scripts) usually read data through OData. This project shows the same pattern on a lightweight stack: a typed query layer with `$filter`, `$select`, `$orderby`, `$top`, `$skip` and `$count`, clear 400 errors for bad queries, and a plain-language entry point for business users.

## Endpoints

| Endpoint | Purpose |
|---|---|
| `GET /health` | liveness check |
| `GET /odata` | service document, lists InfoProviders |
| `GET /odata/{provider}/$metadata` | dimensions, measures, attributes |
| `GET /odata/{provider}` | query data with OData options |
| `GET /ask?q=...` | natural language question, returns the plan and the rows |

Sample InfoProvider: `ZSD_C01` (sales cube) with dimensions CalendarDay, Material, Region, SalesOrg and measures Quantity, NetValue.

## Examples

```bash
curl -G localhost:8000/odata/ZSD_C01 --data-urlencode "\$filter=Region eq 'APAC' and Quantity gt 20" --data-urlencode '$select=Material,NetValue' --data-urlencode '$orderby=NetValue desc' --data-urlencode '$top=5' --data-urlencode '$count=true'
curl -G localhost:8000/ask --data-urlencode "q=top 3 materials by quantity in EMEA"
curl -G localhost:8000/ask --data-urlencode "q=total net value by region"
```

Supported filter operators: `eq ne gt ge lt le`, joined with `and`. Text values go in single quotes.

Supported questions: a measure (net value, revenue, quantity, units), optional `by region|material|sales org|day`, optional `top N`, optional region or material filter, `average` or total.

## Run

```bash
pip install -r requirements.txt
python -m pytest -q
uvicorn app.main:app --reload
```

Docker:

```bash
docker build -t bw-query-assistant .
docker run -p 8000:8000 bw-query-assistant
```

Interactive docs are at `/docs`.

## Design notes

- The natural language layer is rules, not an LLM. It is deterministic, testable and needs no API key. It returns the parsed plan with every answer, so users can see how the question was understood.
- Type checks on filters (text vs number) return 400 instead of silently returning nothing.
- Swapping the CSV for a real BW source means replacing `load()` in `app/main.py`, for example with a call to an OData service or a HANA query.
- CI runs the tests, then builds the Docker image and calls the running container.

## Layout

```
app/odata.py   query parser ($filter, $select, ...)
app/nl.py      question to plan
app/main.py    FastAPI routes
data/          sample sales data
tests/         15 tests
```
