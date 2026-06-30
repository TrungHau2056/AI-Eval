from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.observability.costs import end_run, run_details

router = APIRouter(prefix="/api/costs", tags=["costs"])


@router.get("/current")
def get_current_costs():
    return run_details()


@router.get("/runs/{run_id}")
def get_cost_run(run_id: str):
    details = run_details(run_id)
    if not details["events"]:
        raise HTTPException(404, f"Cost run not found: {run_id}")
    return details


@router.post("/end-run")
def end_current_cost_run():
    return {"summary": end_run()}
