import re
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from config import GUILD_CONFIGS
from db import manager
from web.auth import require_auth, require_manage_events

router = APIRouter(prefix="/api/events", tags=["events"])

VALID_MODES = {'individual', 'team', 'combined_shared', 'combined_versus', 'combined_individual'}
VALID_TASK_TYPES = {'skill_xp', 'slayer_tier', 'dungeon_xp', 'collection'}
VALID_DIFFICULTIES = {'easy', 'medium', 'hard'}


def _serialize_event(e: dict) -> dict:
    return {
        **e,
        'guilds': list(e['guilds']),
        'starts_at': e['starts_at'].isoformat() if e['starts_at'] else None,
        'ends_at': e['ends_at'].isoformat() if e['ends_at'] else None,
        'created_at': e['created_at'].isoformat() if e['created_at'] else None,
    }


def _serialize_task(t: dict) -> dict:
    return {**t, 'target': t['target'] if isinstance(t['target'], dict) else {}}


def _serialize_card_entry(entry: dict) -> dict:
    return {
        **_serialize_task({k: entry[k] for k in ('id', 'position', 'name', 'description', 'task_type', 'target', 'difficulty')}),
        'baseline': entry['baseline'],
        'current_val': entry['current_val'],
        'completed': bool(entry['completed']) if entry['completed'] is not None else False,
        'completed_at': entry['completed_at'].isoformat() if entry['completed_at'] else None,
        'last_updated': entry['last_updated'].isoformat() if entry['last_updated'] else None,
        'progress': max(0.0, (entry['current_val'] or 0) - (entry['baseline'] or 0)) if entry['baseline'] is not None else None,
    }


# ── List / create events ──────────────────────────────────────────────────────

@router.get("")
def list_events(claims=Depends(require_auth)):
    is_manager = claims.get("manage_events") or claims.get("admin")
    events = manager.get_events(include_drafts=bool(is_manager))
    return {"events": [_serialize_event(e) for e in events]}


class CreateEventBody(BaseModel):
    slug: str
    name: str
    mode: str
    guilds: List[str]
    starts_at: datetime
    ends_at: datetime


@router.post("", status_code=201)
def create_event(body: CreateEventBody, _=Depends(require_manage_events)):
    if not re.match(r'^[a-z0-9-]+$', body.slug):
        raise HTTPException(400, "Slug must be lowercase alphanumeric and dashes only")
    if manager.get_event_by_slug(body.slug):
        raise HTTPException(409, "An event with this slug already exists")
    if body.mode not in VALID_MODES:
        raise HTTPException(400, f"Invalid mode — must be one of: {', '.join(VALID_MODES)}")
    valid_guilds = set(GUILD_CONFIGS.keys())
    if not body.guilds or not all(g in valid_guilds for g in body.guilds):
        raise HTTPException(400, f"guilds must be a non-empty list of valid guild keys: {', '.join(valid_guilds)}")
    if body.ends_at <= body.starts_at:
        raise HTTPException(400, "ends_at must be after starts_at")
    event_id = manager.create_event(body.slug, body.name, body.mode, body.guilds, body.starts_at, body.ends_at)
    return {"status": "created", "id": event_id, "slug": body.slug}


# ── Single event ─────────────────────────────────────────────────────────────

@router.get("/{slug}")
def get_event(slug: str, claims=Depends(require_auth)):
    event = manager.get_event_by_slug(slug)
    if not event:
        raise HTTPException(404, "Event not found")
    is_manager = claims.get("manage_events") or claims.get("admin")
    if event['status'] == 'draft' and not is_manager:
        raise HTTPException(404, "Event not found")
    tasks = manager.get_bingo_tasks(event['id'])
    return {
        "event": _serialize_event(event),
        "tasks": [_serialize_task(t) for t in tasks],
    }


class UpdateEventBody(BaseModel):
    name: str
    mode: str
    guilds: List[str]
    starts_at: datetime
    ends_at: datetime


@router.patch("/{slug}")
def update_event(slug: str, body: UpdateEventBody, _=Depends(require_manage_events)):
    event = manager.get_event_by_slug(slug)
    if not event:
        raise HTTPException(404, "Event not found")
    if event['status'] == 'active':
        raise HTTPException(400, "Cannot edit an active event — end it first")
    if body.mode not in VALID_MODES:
        raise HTTPException(400, f"Invalid mode")
    if body.ends_at <= body.starts_at:
        raise HTTPException(400, "ends_at must be after starts_at")
    manager.update_event(slug, body.name, body.mode, body.guilds, body.starts_at, body.ends_at)
    return {"status": "updated"}


class UpdateStatusBody(BaseModel):
    status: str


@router.patch("/{slug}/status")
def update_status(slug: str, body: UpdateStatusBody, _=Depends(require_manage_events)):
    event = manager.get_event_by_slug(slug)
    if not event:
        raise HTTPException(404, "Event not found")
    if body.status not in ('draft', 'active', 'ended'):
        raise HTTPException(400, "status must be draft, active, or ended")
    if body.status == 'active':
        tasks = manager.get_bingo_tasks(event['id'])
        filled = [t for t in tasks if t['task_type'] != 'free']
        if len(filled) < 24:
            raise HTTPException(400, f"All 24 task squares must be filled before activating ({len(filled)}/24 set)")
    manager.update_event_status(slug, body.status)
    return {"status": "updated"}


@router.delete("/{slug}")
def delete_event(slug: str, _=Depends(require_manage_events)):
    event = manager.get_event_by_slug(slug)
    if not event:
        raise HTTPException(404, "Event not found")
    if event['status'] != 'draft':
        raise HTTPException(400, "Only draft events can be deleted")
    manager.delete_event(slug)
    return {"status": "deleted"}


# ── Task management ───────────────────────────────────────────────────────────

class UpsertTaskBody(BaseModel):
    name: str
    description: str = ""
    task_type: str
    target: dict
    difficulty: str = "medium"


@router.put("/{slug}/tasks/{position}")
def upsert_task(slug: str, position: int, body: UpsertTaskBody, _=Depends(require_manage_events)):
    event = manager.get_event_by_slug(slug)
    if not event:
        raise HTTPException(404, "Event not found")
    if position < 0 or position > 24 or position == 12:
        raise HTTPException(400, "Position must be 0–24; position 12 is reserved for the free space")
    if event['status'] == 'active':
        raise HTTPException(400, "Cannot edit tasks of an active event")
    if body.task_type not in VALID_TASK_TYPES:
        raise HTTPException(400, f"task_type must be one of: {', '.join(VALID_TASK_TYPES)}")
    if body.difficulty not in VALID_DIFFICULTIES:
        raise HTTPException(400, f"difficulty must be easy, medium, or hard")
    if 'amount' not in body.target and body.task_type != 'slayer_tier':
        raise HTTPException(400, "target must include 'amount'")
    manager.upsert_bingo_task(event['id'], position, body.name, body.description,
                               body.task_type, body.target, body.difficulty)
    return {"status": "ok"}


@router.delete("/{slug}/tasks/{position}")
def delete_task(slug: str, position: int, _=Depends(require_manage_events)):
    event = manager.get_event_by_slug(slug)
    if not event:
        raise HTTPException(404, "Event not found")
    if position == 12:
        raise HTTPException(400, "Cannot remove the free space")
    if event['status'] == 'active':
        raise HTTPException(400, "Cannot edit tasks of an active event")
    manager.delete_bingo_task(event['id'], position)
    return {"status": "ok"}


# ── Progress / leaderboard ────────────────────────────────────────────────────

@router.get("/{slug}/card/{uuid}")
def get_player_card(slug: str, uuid: str, claims=Depends(require_auth)):
    event = manager.get_event_by_slug(slug)
    if not event:
        raise HTTPException(404, "Event not found")
    is_manager = claims.get("manage_events") or claims.get("admin")
    if event['status'] == 'draft' and not is_manager:
        raise HTTPException(404, "Event not found")
    card = manager.get_player_bingo_card(event['id'], uuid)
    return {"card": [_serialize_card_entry(e) for e in card]}


@router.get("/{slug}/leaderboard")
def get_leaderboard(slug: str, claims=Depends(require_auth)):
    event = manager.get_event_by_slug(slug)
    if not event:
        raise HTTPException(404, "Event not found")
    is_manager = claims.get("manage_events") or claims.get("admin")
    if event['status'] == 'draft' and not is_manager:
        raise HTTPException(404, "Event not found")
    rows = manager.get_bingo_leaderboard(event['id'])
    return {"leaderboard": [
        {
            "uuid": r['uuid'],
            "ign": r['ign'],
            "completed_count": r['completed_count'],
            "blackout": r['completed_count'] == 24,
            "discord_name": r['discord_name'],
            "discord_avatar": r['discord_avatar'],
            "guild_key": r['guild_key'],
            "last_updated": r['last_updated'].isoformat() if r['last_updated'] else None,
        }
        for r in rows
    ]}
