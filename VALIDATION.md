# Validation

Checks executed with Python 3.12.14:

- `python -m unittest discover -s tests -v`: all 5 tests passed. Covers strict-under-21 eligibility, tied winners, no eligible winners, exclusive dealer tool invocation, turn ownership, three-card cap, stand/bust enforcement, player decision isolation, and offline natural-language requests.
- `python blackjack.py --offline --auto --seed 42`: completed all four turns; scores 11, 14, 16, 19; Grace declared winner.
- `python -m compileall -q .`: Python sources compiled successfully.

Not executed here:

- Live Ollama inference: no Ollama server/model in the authoring environment.
- FastAPI/PostgreSQL integration, Docker Compose startup and throughput: Docker and service dependencies are unavailable in the authoring environment. Syntax compilation does not establish API/database correctness. Run `docker compose up --build -d`, then `python demo_abacus.py` after setup to verify the actual two-node system.

The demo is an executable integration check, not a fabricated test result. Performance and failover guarantees must be validated on the intended deployment.
