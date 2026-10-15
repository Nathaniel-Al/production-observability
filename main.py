import json, logging, os, sys, time, uuid
from collections import deque
from fastapi import FastAPI, Query, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest

EMAIL = os.environ.get("EXAM_EMAIL", "25ds3000071@ds.study.iitm.ac.in")
START = time.monotonic()

# Single unlabeled counter: exposes exactly `http_requests_total`.
REQUESTS = Counter("http_requests_total", "Total HTTP requests, all endpoints")

LOG_BUFFER = deque(maxlen=2000)          # in-memory ring buffer for /logs/tail
stdout_logger = logging.getLogger("app")
stdout_logger.setLevel(logging.INFO)
stdout_logger.propagate = False
_h = logging.StreamHandler(sys.stdout)
_h.setFormatter(logging.Formatter("%(message)s"))
stdout_logger.addHandler(_h)

def log(level: str, path: str, request_id: str, **extra):
    entry = {"level": level, "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()) + f".{int(time.time()*1000)%1000:03d}Z",
             "path": path, "request_id": request_id, **extra}
    LOG_BUFFER.append(entry)
    stdout_logger.info(json.dumps(entry))

app = FastAPI()

@app.middleware("http")
async def instrument(request: Request, call_next):
    REQUESTS.inc()                                    # every request, any endpoint
    rid = str(uuid.uuid4())
    start = time.perf_counter()
    try:
        response = await call_next(request)
        status = response.status_code
        level = "INFO" if status < 500 else "ERROR"
    except Exception:
        response = Response("Internal Server Error", status_code=500)
        status, level = 500, "ERROR"
    response.headers["X-Request-ID"] = rid
    log(level, request.url.path, rid, method=request.method, status=status,
        duration_ms=round((time.perf_counter() - start) * 1000, 3))
    return response

@app.get("/work")
async def work(n: int = Query(1, ge=0)):
    acc = 0
    for i in range(min(n, 100_000)):                  # bounded real work
        acc += i * i
    return {"email": EMAIL, "done": n}

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/healthz")
async def healthz():
    return {"status": "ok", "uptime_s": round(time.monotonic() - START, 3)}

@app.get("/logs/tail")
async def logs_tail(limit: int = Query(20, ge=1, le=2000)):
    return list(LOG_BUFFER)[-limit:]

@app.get("/")
async def root():
    return {"ok": True}
