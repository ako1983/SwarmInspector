"""
core/weave_setup.py
W&B Weave initialization and op decorators.

Every agent is wrapped with @weave.op() so every call appears in the Weave UI.
Inspector agents get an "inspector." prefix; subject agents get "agent.".
"""

import os
import functools
import logging

logger = logging.getLogger(__name__)

PROJECT_NAME = "swarm-inspector-weavehacks4"

_weave_client = None
_entity = None
_weave_available = False


def init_weave() -> None:
    global _weave_client, _entity, _weave_available

    if _weave_client is not None:
        return

    try:
        import weave
        import wandb

        api_key = os.getenv("WANDB_API_KEY")
        if api_key:
            wandb.login(key=api_key, relogin=False)

        _weave_client = weave.init(PROJECT_NAME)
        _weave_available = True

        # Resolve entity for URL construction
        try:
            api = wandb.Api()
            _entity = api.default_entity
        except Exception:
            _entity = os.getenv("WANDB_ENTITY", "")

        logger.info(f"Weave initialized: {get_weave_url()}")

    except Exception as exc:
        logger.warning(f"Weave init failed ({exc}) — traces will not be recorded")
        _weave_available = False


def get_weave_url() -> str | None:
    if not _entity:
        return None
    return f"https://wandb.ai/{_entity}/{PROJECT_NAME}/weave"


def _make_op_decorator(prefix: str, name: str):
    """Returns a decorator that wraps an async function with weave.op() tracing."""
    def decorator(fn):
        if not _weave_available:
            # Weave not initialised yet — try to apply lazily at first call
            @functools.wraps(fn)
            async def lazy_wrapper(*args, **kwargs):
                return await fn(*args, **kwargs)
            return lazy_wrapper

        try:
            import weave

            @weave.op()
            @functools.wraps(fn)
            async def traced(*args, **kwargs):
                return await fn(*args, **kwargs)

            traced.__name__ = f"{prefix}.{name}"
            traced.__qualname__ = f"{prefix}.{name}"
            return traced

        except Exception:
            @functools.wraps(fn)
            async def fallback(*args, **kwargs):
                return await fn(*args, **kwargs)
            return fallback

    return decorator


def agent_op(name: str):
    """Decorator factory for subject-swarm agent nodes."""
    def decorator(fn):
        # Apply lazily so the decorator works even before init_weave() is called
        _fn = fn

        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            nonlocal _fn
            if _weave_available and not hasattr(wrapper, "_weave_wrapped"):
                try:
                    import weave
                    _fn = weave.op()(_fn)
                    _fn.__name__ = f"agent.{name}"
                    wrapper._weave_wrapped = True
                except Exception:
                    pass
            return await _fn(*args, **kwargs)

        return wrapper

    return decorator


def inspector_op(name: str):
    """Decorator factory for inspector swarm agent nodes."""
    def decorator(fn):
        _fn = fn

        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            nonlocal _fn
            if _weave_available and not hasattr(wrapper, "_weave_wrapped"):
                try:
                    import weave
                    _fn = weave.op()(_fn)
                    _fn.__name__ = f"inspector.{name}"
                    wrapper._weave_wrapped = True
                except Exception:
                    pass
            return await _fn(*args, **kwargs)

        return wrapper

    return decorator
