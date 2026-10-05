"""All API instances share one PostgreSQL primary; no in-process sum."""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from psycopg import OperationalError
from psycopg_pool import AsyncConnectionPool, PoolTimeout


@asynccontextmanager
async def lifespan(app: FastAPI):
    pool = AsyncConnectionPool(os.environ["DATABASE_URL"], min_size=1,
                               max_size=int(os.getenv("DB_POOL_SIZE", "5")),
                               timeout=10, open=False,
                               kwargs={"options": "-c statement_timeout=10000 -c lock_timeout=5000"})
    await pool.open(wait=True)
    app.state.pool = pool
    try:
        yield
    finally:
        await pool.close()


app = FastAPI(title="Consistent Abacus", lifespan=lifespan)


class Addition(BaseModel):
    model_config = ConfigDict(extra="forbid")
    number: int = Field(strict=True, ge=-(2**63), le=2**63 - 1)


class Sum(BaseModel):
    sum: int


async def execute(sql, parameters=()):
    try:
        async with app.state.pool.connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(sql, parameters)
                row = await cursor.fetchone()
            # Connection context commits before we return/acknowledge success.
        if row is None:
            raise HTTPException(503, "Counter has not been initialized")
        return {"sum": int(row[0])}
    except (OperationalError, PoolTimeout) as error:
        raise HTTPException(503, "Database unavailable; outcome may be unknown. Do not blindly retry POST.") from error


@app.post("/abacus/number", response_model=Sum)
async def add(body: Addition):
    return await execute("UPDATE abacus SET total = total + %s WHERE id = 1 RETURNING total", (body.number,))


@app.get("/abacus/sum", response_model=Sum)
async def get_sum():
    return await execute("SELECT total FROM abacus WHERE id = 1")


@app.delete("/abacus/sum", response_model=Sum)
async def reset():
    return await execute("UPDATE abacus SET total = 0 WHERE id = 1 RETURNING total")
