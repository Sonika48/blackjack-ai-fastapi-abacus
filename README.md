# Python 3.12+ coding assignment

Two independent applications: a terminal multi-agent Blackjack game and a strongly consistent FastAPI sum service.

## Setup

Use Python 3.12 or newer and Docker with Compose for the database demo.

```sh
cd /path/to/assignment
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Task 1 — Blackjack / Applied AI

The application has one dealer agent, three AI player agents (Ada, Turing, Grace), and one human seat. Each agent has its own role and decisions. Direct Python orchestration avoids adding an unnecessary agent framework. In default mode, agents use an Ollama LLM over its local HTTP API. Install Ollama separately, run its server, and download a model:

```sh
ollama pull llama3.2
python blackjack.py
```

Say “deal me the next card”, “hit me”, or “I think I should stand”. The dealer LLM classifies your intent; each player LLM decides whether to request a card based on its hand and personality. `--model MODEL` selects another installed model; `--ollama-url URL` selects its endpoint. The program announces the final cards, scores and winner(s).

For a dependency-free, reproducible game demonstration:

```sh
python blackjack.py --offline --auto --seed 42
python blackjack.py --offline
```

**Offline mode is rule-based AI simulation, not LLM inference.** Default mode uses the LLM for both dealer intent recognition and player decisions. An LLM/server error ends the game with an actionable message; it never silently switches modes.

Rules and assumptions:

- `draw_card()` returns a uniform random integer from 2 through 11. Cards are independent; there is no finite deck or special ace handling.
- A player can request at most three cards, including the first card. There is no automatic initial deal.
- The wording “under 21” is interpreted literally: 21 and higher are ineligible. To use conventional Blackjack rules, change eligibility to `<= 21` and the stopping threshold accordingly.
- Ties produce joint winners; if everyone is ineligible or has no cards, there is no winner. Standing before any draw is allowed but cannot win.
- The dealer orchestrates turns and exclusively invokes the draw function; players pass requests to the dealer and receive no tool handle. Deterministic checks enforce turn ownership, card limits and stopping regardless of model output. This is an application capability boundary, not a sandbox for hostile Python code.
- The dealer is not a competing player. The human takes a turn, then all three AI players take theirs.

```sh
python -m unittest discover -s tests -v
```

## Task 2 — FastAPI / consistency

Start two independent API containers and a shared PostgreSQL primary:

```sh
docker compose up --build -d
docker compose logs -f api1 api2
```

In another terminal:

```sh
curl -X POST http://localhost:8001/abacus/number \
  -H 'Content-Type: application/json' -d '{"number":10}'
curl -X POST http://localhost:8002/abacus/number \
  -H 'Content-Type: application/json' -d '{"number":5}'
curl http://localhost:8001/abacus/sum
curl http://localhost:8002/abacus/sum
curl -X DELETE http://localhost:8002/abacus/sum
curl http://localhost:8001/abacus/sum
python demo_abacus.py --requests 1000 --concurrency 50
```

Responses use `{"sum": N}`. Both GET requests above return 15, assuming no other writers. The demo resets the counter and requires exclusive use of this demo database. It asserts that all 1,000 acknowledgments have distinct totals 1..1000 and both nodes agree on 1000. It also checks negative inputs, rejected malformed inputs, resets across nodes, and racing reset/add operations. It prints measured throughput rather than claiming an unmeasured performance target. API docs are at http://localhost:8001/docs and http://localhost:8002/docs.

The input contract is a signed 64-bit JSON integer. Booleans, floats, strings, null and extra fields are rejected with 422. PostgreSQL `NUMERIC` stores the accumulated integer without 64-bit sum overflow (subject to PostgreSQL's numeric size limit). Negative numbers are supported. If arbitrary decimals were required, define precision and rounding explicitly rather than accumulate binary floats.

### Why this remains correct on N nodes

Each API node has a connection pool but no local sum or cache. Every node accesses the **same PostgreSQL primary**:

```sql
UPDATE abacus SET total = total + $1 WHERE id = 1 RETURNING total;
UPDATE abacus SET total = 0 WHERE id = 1 RETURNING total;
SELECT total FROM abacus WHERE id = 1;
```

PostgreSQL locks the shared row during each update. Concurrent additions and resets serialize, avoiding a read-modify-write race. Each successful write response is sent after its transaction commits. GET uses a fresh statement snapshot on the primary and sees committed data; a GET overlapping a write may observe either side of that write, which is a valid linearizable ordering. Once a write has completed, a subsequent GET observes that write or a later operation. A reset concurrent with addition either precedes or follows it; it does not mean future additions stay zero.

This provides linearizable counter operations during normal operation of a single primary. No process-local lock can provide this guarantee across containers, and asynchronous read replicas must not serve GET requests.

The requested 1,000 additions per minute is about 17 per second. A short single-row transaction is a reasonable design for this target, but actual capacity must be measured with the included demo on the intended hardware. A single counter is intentionally a write serialization point; adding API nodes does not eliminate that bottleneck. At 100 API nodes, the default five-connection pools could use 500 database connections: lower per-node pool limits and/or use PgBouncer with a bounded database connection budget. Place a load balancer in front of interchangeable API nodes.

### Durability, failures, and deployment limits

- Preserve PostgreSQL `fsync` and `synchronous_commit` defaults. The Compose volume retains state across restarts. This local demo has one database and does not claim database high availability.
- For highly available deployments, use synchronous replication, leader fencing and a failover policy that never promotes a stale replica. Linearizability across database failures needs these operational guarantees; PostgreSQL alone does not configure them for you. Prefer unavailability to stale reads during partitions.
- Database connection/pool/lock failures return 503 rather than an invented sum. Some other database failures return 500. A dropped connection or lost HTTP response can leave a committed POST outcome unknown. Retrying a POST can double-count: exactly-once retries require a client-supplied idempotency key and a deduplication record committed in the same transaction. That extension is outside the specified API contract.
- The credentials in Compose are for local demonstration. Configure secrets, authentication, TLS and restricted database access for deployment. Use a dedicated migration step to initialize production schema; application startup never resets the counter. The initialization SQL runs on first creation of the Docker database volume.

Stop containers while preserving data:

```sh
docker compose down
```

Remove demo data intentionally:

```sh
docker compose down -v
```

References: [PostgreSQL transaction isolation](https://www.postgresql.org/docs/17/transaction-iso.html), [PostgreSQL explicit locking](https://www.postgresql.org/docs/17/explicit-locking.html), [FastAPI deployment workers](https://fastapi.tiangolo.com/deployment/server-workers/), [Ollama generate API](https://docs.ollama.com/api/generate).

## Verification status

See `VALIDATION.md` for checks run in the authoring environment and checks that require your local Docker/Ollama installation.
