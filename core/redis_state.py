"""
core/redis_state.py
Shared state layer — tries real Redis, falls back to an in-memory dict.

Both the subject swarm and the inspector swarm read/write through this layer.
RedisState is a singleton (call get_state() everywhere).
"""

import asyncio
import json
import os
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Thresholds used by the monitor agent
STALL_THRESHOLD = 8.0    # seconds without a heartbeat → silent_drop
LOOP_THRESHOLD = 6       # tool calls before we start checking for loops


class RedisState:
    """
    Unified state store.  Uses Redis when available, falls back to a plain dict.
    All public methods are async so callers never need to branch.
    """

    def __init__(self):
        self._mem: dict = {}          # in-memory fallback store
        self._redis = None            # aioredis client (may remain None)
        self._lock = asyncio.Lock()
        self._use_memory = True

    async def connect(self) -> None:
        url = os.getenv("REDIS_URL", "redis://localhost:6379")
        try:
            import redis.asyncio as aioredis
            client = aioredis.from_url(url, decode_responses=True, socket_connect_timeout=2)
            await client.ping()
            self._redis = client
            self._use_memory = False
            logger.info(f"Connected to Redis at {url}")
        except Exception as exc:
            logger.info(f"Redis unavailable ({exc}) — using in-memory fallback")
            self._use_memory = True

    # ── Low-level get/set ─────────────────────────────────────────────────────

    async def _set(self, key: str, value: str, ex: int = 300) -> None:
        if self._use_memory:
            async with self._lock:
                self._mem[key] = value
        else:
            await self._redis.set(key, value, ex=ex)

    async def _get(self, key: str) -> Optional[str]:
        if self._use_memory:
            async with self._lock:
                return self._mem.get(key)
        else:
            return await self._redis.get(key)

    async def _delete(self, key: str) -> None:
        if self._use_memory:
            async with self._lock:
                self._mem.pop(key, None)
        else:
            await self._redis.delete(key)

    # ── Heartbeats ────────────────────────────────────────────────────────────

    async def write_heartbeat(
        self, ticker: str, agent_id: str, tool: str = "", call_count: int = 0
    ) -> None:
        key = f"swarm:{ticker}:heartbeat:{agent_id}"
        data = {
            "agent_id": agent_id,
            "last_seen": time.time(),
            "call_count": call_count,
            "last_tool": tool,
            "status": "running",
        }
        await self._set(key, json.dumps(data))

    async def read_heartbeat(self, ticker: str, agent_id: str) -> Optional[dict]:
        key = f"swarm:{ticker}:heartbeat:{agent_id}"
        raw = await self._get(key)
        return json.loads(raw) if raw else None

    async def get_all_heartbeats(
        self, ticker: str, agent_ids: list[str]
    ) -> dict[str, dict]:
        result = {}
        for agent_id in agent_ids:
            hb = await self.read_heartbeat(ticker, agent_id)
            if hb:
                result[agent_id] = hb
        return result

    # ── Agent lifecycle ───────────────────────────────────────────────────────

    async def mark_agent_done(self, ticker: str, agent_id: str) -> None:
        key = f"swarm:{ticker}:heartbeat:{agent_id}"
        raw = await self._get(key)
        if raw:
            data = json.loads(raw)
            data["status"] = "done"
            await self._set(key, json.dumps(data))

    async def mark_agent_failed(self, ticker: str, agent_id: str) -> None:
        key = f"swarm:{ticker}:heartbeat:{agent_id}"
        raw = await self._get(key)
        data = json.loads(raw) if raw else {"agent_id": agent_id}
        data["status"] = "failed"
        await self._set(key, json.dumps(data))

    # ── Failure injection ─────────────────────────────────────────────────────

    async def inject_failure(
        self, ticker: str, agent_id: str, failure_type: str
    ) -> None:
        key = f"swarm:{ticker}:failure:{agent_id}"
        await self._set(key, failure_type)
        logger.info(f"Failure injected: {agent_id} → {failure_type}")

    async def check_failure_injection(
        self, ticker: str, agent_id: str
    ) -> Optional[str]:
        key = f"swarm:{ticker}:failure:{agent_id}"
        failure = await self._get(key)
        if failure:
            await self._delete(key)   # consume once
        return failure

    # ── Recovery signals ──────────────────────────────────────────────────────

    async def signal_recovery(
        self, ticker: str, agent_id: str, payload: dict
    ) -> None:
        key = f"swarm:{ticker}:recovery:{agent_id}"
        await self._set(key, json.dumps(payload))
        logger.info(f"Recovery signal sent to {agent_id}: {payload}")

    async def check_recovery_signal(
        self, ticker: str, agent_id: str
    ) -> Optional[dict]:
        key = f"swarm:{ticker}:recovery:{agent_id}"
        raw = await self._get(key)
        if raw:
            await self._delete(key)   # consume once
            return json.loads(raw)
        return None

    # ── Swarm-level status ────────────────────────────────────────────────────

    async def get_swarm_summary(self, ticker: str) -> dict:
        agents = ["earnings_agent", "risk_agent", "sentiment_agent", "synthesis_agent"]
        heartbeats = await self.get_all_heartbeats(ticker, agents)
        return {
            "ticker": ticker,
            "agents": heartbeats,
            "timestamp": time.time(),
        }


# ── Singleton ─────────────────────────────────────────────────────────────────

_state_instance: Optional[RedisState] = None


def get_state() -> RedisState:
    global _state_instance
    if _state_instance is None:
        _state_instance = RedisState()
    return _state_instance


async def init_state() -> RedisState:
    """Call once at startup to attempt Redis connection."""
    state = get_state()
    await state.connect()
    return state
