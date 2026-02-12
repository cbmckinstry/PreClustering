from __future__ import annotations

from flask import Flask, render_template, request, session, redirect, url_for
from flask_session import Session
from Master import *
import os
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import requests
import ipaddress
import redis
import json
import uuid
from werkzeug.middleware.proxy_fix import ProxyFix
from datetime import timedelta


app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

IS_RENDER = bool(os.environ.get("RENDER")) or bool(os.environ.get("RENDER_SERVICE_ID"))
COOKIE_SECURE = True if IS_RENDER else False

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=COOKIE_SECURE,
)

redis_url = os.environ.get("REDIS_URL", "").strip()

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_USE_SIGNER"] = True
app.config["SESSION_KEY_PREFIX"] = os.environ.get("SESSION_KEY_PREFIX", "session:clustering:")

DEVICE_COOKIE_NAME = "device_id"
DEVICE_COOKIE_MAX_AGE = 60 * 60 * 24 * 365 * 2
LOG_RETENTION_DAYS = 365 * 2

def get_device_id() -> str:
    did = request.cookies.get(DEVICE_COOKIE_NAME)
    if did and 16 <= len(did) <= 80:
        return did

    return uuid.uuid4().hex

def build_user_map(entries: list[dict]) -> dict[str, int]:
    entries_oldest_first = sorted(entries, key=lambda e: e.get("timestamp", ""))

    first_seen: dict[str, str] = {}
    for e in entries_oldest_first:
        did = e.get("device_id")
        if not did:
            continue
        first_seen.setdefault(did, e.get("timestamp", ""))

    ordered = sorted(first_seen.items(), key=lambda x: (x[1], x[0]))

    return {did: i for i, (did, _) in enumerate(ordered, start=1)}

def _location_key_from_geo(geo: dict | None) -> str:
    if not geo:
        return "Location unknown"
    city = geo.get("city") or "Unknown city"
    region = geo.get("region") or "Unknown region"
    country = geo.get("country") or "Unknown country"
    return f"{city}, {region}, {country}"


def build_grouped_entries(entries: list[dict]) -> dict[int, dict[str, list[dict]]]:
    user_map = build_user_map(entries)

    grouped: dict[int, dict[str, list[dict]]] = {}

    for e in entries:
        did = e.get("device_id") or ""
        user_num = user_map.get(did, 0)  # 0 only if device_id missing
        loc_key = _location_key_from_geo(e.get("geo"))
        grouped.setdefault(user_num, {}).setdefault(loc_key, []).append(e)

    for u in grouped:
        for loc in grouped[u]:
            grouped[u][loc].sort(key=lambda e: e.get("timestamp", ""), reverse=True)

    def loc_newest_ts(u: int, loc: str) -> str:
        L = grouped[u][loc]
        return L[0].get("timestamp", "") if L else ""

    ordered_grouped: dict[int, dict[str, list[dict]]]= {}
    for u in list(grouped.keys()):
        ordered_locs = sorted(grouped[u].keys(), key=lambda loc: loc_newest_ts(u, loc), reverse=True)
        ordered_grouped[u] = {loc: grouped[u][loc] for loc in ordered_locs}

    def user_newest_ts(u: int) -> str:
        locs = ordered_grouped.get(u, {})
        if not locs:
            return ""
        first_loc = next(iter(locs.values()))
        return first_loc[0].get("timestamp", "") if first_loc else ""

    ordered_users = sorted(ordered_grouped.keys(), key=user_newest_ts, reverse=True)
    ordered_users = sorted(ordered_users, key=lambda u: (u == 0,))  # push 0 last

    return {u: ordered_grouped[u] for u in ordered_users}

if redis_url:
    app.config["SESSION_TYPE"] = "redis"
    app.config["SESSION_REDIS"] = redis.Redis.from_url(redis_url)
else:
    app.config["SESSION_TYPE"] = "filesystem"
    session_dir = Path(app.instance_path) / "flask_session"
    session_dir.mkdir(parents=True, exist_ok=True)
    app.config["SESSION_FILE_DIR"] = str(session_dir)
Session(app)

TRAINER_PASSWORD_VIEW = os.environ.get("TRAINER_PASSWORD_VIEW", "change-me")

def is_trainer_authed() -> bool:
    return bool(session.get("trainer_authed", False))

HIDDEN_IPS_RAW = os.environ.get("HIDDEN_IPS", "").strip()
HIDDEN_IPS = {x.strip() for x in HIDDEN_IPS_RAW.split(",") if x.strip()}

def is_hidden_ip(ip: str) -> bool:
    return ip in HIDDEN_IPS

LOG_KEY_PREFIX = os.environ.get("LOG_KEY_PREFIX", "logs:preclustering:")
LOG_LIST_KEY = LOG_KEY_PREFIX + "trainer_log"
LOG_COUNTER_KEY = LOG_KEY_PREFIX + "trainer_id"

rdb = redis.Redis.from_url(redis_url, decode_responses=True) if redis_url else None
MAX_LOG_ENTRIES = int(os.environ.get("MAX_LOG_ENTRIES", "20000"))

DATA_LOG_FALLBACK: list[dict] = []
LOG_COUNTER_FALLBACK = 0

def _next_local_id() -> int:
    global LOG_COUNTER_FALLBACK
    if rdb:
        return int(rdb.incr(LOG_COUNTER_KEY))
    LOG_COUNTER_FALLBACK += 1
    return LOG_COUNTER_FALLBACK

def log_append(entry: dict):
    entry = dict(entry)
    ip = entry.get("ip", "")

    if entry.get("event") in {"view", "view-test"}:
        return
    if is_hidden_ip(ip):
        return

    entry.setdefault("id", _next_local_id())

    if rdb:
        rdb.rpush(LOG_LIST_KEY, json.dumps(entry))
        rdb.ltrim(LOG_LIST_KEY, -MAX_LOG_ENTRIES, -1)
    else:
        DATA_LOG_FALLBACK.append(entry)
        if len(DATA_LOG_FALLBACK) > MAX_LOG_ENTRIES:
            del DATA_LOG_FALLBACK[:-MAX_LOG_ENTRIES]

def log_get_all() -> list[dict]:
    if rdb:
        raw = rdb.lrange(LOG_LIST_KEY, 0, -1)
        out = []
        for s in raw:
            try:
                out.append(json.loads(s))
            except Exception:
                pass
        return out
    return list(DATA_LOG_FALLBACK)

def purge_old_entries():
    cutoff = datetime.now(ZoneInfo("America/Chicago")) - timedelta(days=LOG_RETENTION_DAYS)

    def is_recent(e):
        try:
            ts = datetime.strptime(e.get("timestamp", ""), "%Y-%m-%d  %H:%M:%S")
            ts = ts.replace(tzinfo=ZoneInfo("America/Chicago"))
            return ts >= cutoff
        except Exception:
            return False  # drop malformed timestamps

    if rdb:
        raw = rdb.lrange(LOG_LIST_KEY, 0, -1)
        kept = []
        for s in raw:
            try:
                e = json.loads(s)
                if is_recent(e):
                    kept.append(s)
            except Exception:
                pass

        pipe = rdb.pipeline()
        pipe.delete(LOG_LIST_KEY)
        if kept:
            pipe.rpush(LOG_LIST_KEY, *kept)
            pipe.ltrim(LOG_LIST_KEY, -MAX_LOG_ENTRIES, -1)
        pipe.execute()
    else:
        global DATA_LOG_FALLBACK
        DATA_LOG_FALLBACK = [e for e in DATA_LOG_FALLBACK if is_recent(e)]

def _build_matrices_payload_lines(people: int, crews: int) -> list[str]:
    return [
        f"  People: {people}",
        f"  Crews: {crews}",
    ]

def _now_ts() -> str:
    return datetime.now(ZoneInfo("America/Chicago")).strftime("%Y-%m-%d  %H:%M:%S")

def is_public_ip(ip: str) -> bool:
    try:
        a = ipaddress.ip_address(ip)
        return not (a.is_private or a.is_loopback or a.is_reserved or a.is_multicast or a.is_link_local)
    except ValueError:
        return False

def get_client_ip():
    xff = request.headers.get("X-Forwarded-For", "")
    if xff:
        parts = [p.strip() for p in xff.split(",") if p.strip()]
        for ip in parts:
            if is_public_ip(ip):
                return ip, xff
        return (parts[0] if parts else (request.remote_addr or "")), xff
    return request.remote_addr or "", ""

WIPE_ALL_IPS_RAW = os.environ.get("WIPE_ALL_IPS", "").strip().lower()
WIPE_ALL_IPS = WIPE_ALL_IPS_RAW in {"1", "true", "yes", "y", "on"}

def wipe_all_ips_from_storage():
    global DATA_LOG_FALLBACK, LOG_COUNTER_FALLBACK

    if rdb:
        pipe = rdb.pipeline()
        pipe.delete(LOG_LIST_KEY)
        pipe.delete(LOG_COUNTER_KEY)
        pipe.execute()
    else:
        DATA_LOG_FALLBACK = []
        LOG_COUNTER_FALLBACK = 0

if WIPE_ALL_IPS:
    wipe_all_ips_from_storage()


def purge_hidden_ips_from_redis():
    if not rdb:
        return

    raw = rdb.lrange(LOG_LIST_KEY, 0, -1)
    kept = []
    for s in raw:
        try:
            e = json.loads(s)
            if is_hidden_ip(e.get("ip", "")):
                continue
            kept.append(s)
        except Exception:
            kept.append(s)
    pipe = rdb.pipeline()
    pipe.delete(LOG_LIST_KEY)
    if kept:
        pipe.rpush(LOG_LIST_KEY, *kept)
        pipe.ltrim(LOG_LIST_KEY, -MAX_LOG_ENTRIES, -1)
    pipe.execute()
purge_hidden_ips_from_redis()

def lookup_city(ip: str):
    try:
        if ip.startswith("127.") or ip == "::1":
            return {"city": "Localhost", "region": None, "country": None}
        resp = requests.get(f"http://ip-api.com/json/{ip}", timeout=2)
        data = resp.json()
        if data.get("status") != "success":
            return None
        return {"city": data.get("city"), "region": data.get("regionName"), "country": data.get("country")}
    except Exception:
        return None

def _format_loc(geo):
    if not geo:
        return "Location unknown"
    city = geo.get("city") or "Unknown city"
    region = geo.get("region") or "Unknown region"
    country = geo.get("country") or "Unknown country"
    return f"{city}, {region}, {country}"

def print_event(event: str, user_ip: str, device_id: str, geo, xff_chain: str, remote_addr: str, payload_lines: list[str] | None):

    if is_hidden_ip(user_ip):
        return

    print(f"\n{event.upper()} @ {_now_ts()}", flush=True)
    print(f"  Device: {device_id}", flush=True)
    print(f"  IP: {user_ip}", flush=True)
    print(f"  Location: {_format_loc(geo)}", flush=True)

    if xff_chain:
        print(f"  X-Forwarded-For: {xff_chain}", flush=True)
    if remote_addr:
        print(f"  Remote Addr: {remote_addr}", flush=True)

    if payload_lines:
        print("", flush=True)
        for line in payload_lines:
            print(line, flush=True)

    print("-" * 40, flush=True)

def _safe_return_path(path: str | None) -> str:
    allowed = {"/", "/test"}
    return path if path in allowed else "/"


@app.route("/", methods=["GET", "POST"], strict_slashes=False)
def index():
    user_ip, xff_chain = get_client_ip()
    geo = lookup_city(user_ip)
    device_id = get_device_id()

    if request.method == "GET":
        session["return_after_matrices"] = "/"

        return render_template(
            "index.html",
            vehlist=",".join(
                map(
                    str,
                    session.get("vehlist", [])
                    if isinstance(session.get("vehlist", []), list)
                    else [session.get("vehlist")],
                )
            ),
            pers5=session.get("pers5", ""),
            pers6=session.get("pers6", ""),
            results=session.get("results"),
            totalhelp=session.get("totalhelp"),
            sorted_allocations=session.get("sorted_allocations"),
            rem_vehs=session.get("rem_vehs"),
            allocations_only=session.get("allocations_only", 0),
            pull_combinations=session.get("pull_combinations", 0),
            error_message=None,
            backupsize=session.get("backupsize"),
            alllist=session.get("alllist"),
            matrices_result=session.get("matrices_result"),
            ranges_result=session.get("ranges_result"),
            total_people=session.get("total_people", ""),
            people=session.get("people", ""),
            crews=session.get("crews", ""),
            zip=zip,
            enumerate=enumerate,
            len=len,
        )

    pers5 = pers6 = 0
    vehlist_input = ""
    try:
        vehlist_input = request.form.get("vehlist", "").strip()
        pull_combinations = int(request.form.get("pull_combinations", 0))
        pers5 = int(request.form.get("pers5") or 0)
        pers6 = int(request.form.get("pers6") or 0)
        vehlist = [int(x.strip()) for x in vehlist_input.split(",") if x.strip()]

        if not is_hidden_ip(user_ip):
            log_append({
                "ip": user_ip,
                "device_id": device_id,
                "xff": xff_chain,
                "remote_addr": request.remote_addr,
                "geo": geo,
                "timestamp": _now_ts(),
                "event": "input",
                "input": {
                    "vehlist": vehlist,
                    "pers5": pers5,
                    "pers6": pers6,
                    "pull_combinations": pull_combinations,
                },
            })

        # ----- computation unchanged -----
        veh2 = vehlist.copy()
        veh2.sort(reverse=True)
        validate_inputs(vehlist, pers5, pers6)

        backup_group = pers5
        backupsize = 5
        primary_group = pers6

        results_1 = optimal_allocation(veh2[:].copy(), primary_group, backup_group, 6, backupsize)
        results = trickle_down(results_1, backupsize)
        off = [backup_group - results[0][0], primary_group - results[0][1]]

        if not results or not isinstance(results, list) or len(results) < 2:
            raise ValueError("Invalid results returned from calculations.")

        sorted_allocations, sorted_spaces, sorted_sizes, number = sort_closestalg_output(results, backupsize)

        if sum(off) <= pers6 and backupsize == 5:
            combos, listing = call_sixesFlipped(sorted_allocations, sorted_spaces, off.copy(), backupsize, None)
        else:
            combos, listing = call_combine(sorted_allocations, sorted_spaces, off.copy(), backupsize, None)

        listing1 = listing.copy()
        combos1 = combos.copy()
        combos3 = combos1.copy()
        listing3 = listing1.copy()
        rem_vehs1 = unused(sorted_allocations.copy(), combos.copy())

        if combos:
            for elem in rem_vehs1:
                combos1.append([elem])
                listing1.append([0, 0])

            combos2, newalloc = call_optimize(
                sorted_allocations.copy(),
                listing1,
                backupsize,
                combos1,
                sorted_spaces,
            )
            combos3 = combos2
            listing3 = newalloc

        combos, listing, progress = cleanup(combos3, sorted_spaces, listing3)
        while progress:
            combos,listing, progress = cleanup(combos, sorted_spaces, listing)
        damage = harm(combos.copy(), sorted_allocations.copy())
        totalhelp = combosSum(combos.copy(), sorted_allocations.copy(), off.copy())

        combos = person_calc(combos.copy(), sorted_sizes.copy())
        alllist = alltogether(combos, listing, damage)

        less = nonzero(sorted_spaces, sorted_sizes)
        rem_vehs2 = unused1(less[1], combos.copy())
        rem_vehs = quant(rem_vehs2)

        restored_vehs, restored_all, restored_spaces = restore_order(
            vehlist[:].copy(), sorted_sizes, sorted_allocations, sorted_spaces
        )

        combined_sorted_data = [
            [restored_vehs[i], restored_all[i], restored_spaces[i], number[i]]
            for i in range(len(sorted_sizes))
        ]

        session["sorted_allocations"] = combined_sorted_data
        session["totalhelp"] = totalhelp
        session["alllist"] = alllist
        session["backupsize"] = backupsize

        if pull_combinations==0:
            session["vehlist"] = vehlist
            session["pers5"] = pers5
            session["pers6"] = pers6
        elif pull_combinations!=0:
            session["vehlist"] = allone(combos.copy())
            session["pers6"] = totalhelp[1]
            session["pers5"] = totalhelp[0]

        session["rem_vehs"] = rem_vehs
        session["results"] = [results[0], off]

        return redirect(url_for("index"))

    except Exception as e:
        return render_template(
            "index.html",
            error_message=f"An error occurred: {str(e)}",
            vehlist=vehlist_input,
            pers5=pers5,
            pers6=pers6,
            results=None,
            totalhelp=None,
            sorted_allocations=None,
            rem_vehs=None,
            alllist=None,
            backupsize=None,
            matrices_result=session.get("matrices_result"),
            allocations_only=int(request.form.get("allocations_only", 0)),
            ranges_result=session.get("ranges_result"),
            total_people=session.get("total_people", ""),
            people=session.get("people", ""),
            crews=session.get("crews", ""),
            zip=zip,
            enumerate=enumerate,
            len=len,
        )

@app.route("/test", methods=["GET", "POST"], strict_slashes=False)
def test_page():
    user_ip, xff_chain = get_client_ip()
    geo = lookup_city(user_ip)
    device_id = get_device_id()

    if request.method == "GET":
        session["return_after_matrices"] = "/test"

        pending = session.pop("pending_matrices_test_print", None)
        if pending and (not is_hidden_ip(user_ip)):
            print_event(
                event="matrices-test",
                user_ip=user_ip,
                device_id=device_id,
                geo=geo,
                xff_chain=xff_chain,
                remote_addr=request.remote_addr or "",
                payload_lines=pending,
            )


        return render_template(
            "index.html",
            vehlist=",".join(
                map(
                    str,
                    session.get("vehlist", [])
                    if isinstance(session.get("vehlist", []), list)
                    else [session.get("vehlist")],
                )
            ),
            pers5=session.get("pers5", ""),
            pers6=session.get("pers6", ""),
            results=session.get("results"),
            totalhelp=session.get("totalhelp"),
            sorted_allocations=session.get("sorted_allocations"),
            rem_vehs=session.get("rem_vehs"),
            allocations_only=session.get("allocations_only", 0),
            pull_combinations=session.get("pull_combinations", 0),
            error_message=None,
            backupsize=session.get("backupsize"),
            alllist=session.get("alllist"),
            matrices_result=session.get("matrices_result"),
            ranges_result=session.get("ranges_result"),
            total_people=session.get("total_people", ""),
            people=session.get("people", ""),
            crews=session.get("crews", ""),
            zip=zip,
            enumerate=enumerate,
            len=len,
        )

    pers5 = pers6 = 0
    vehlist_input = ""
    try:
        vehlist_input = request.form.get("vehlist", "").strip()
        pull_combinations = int(request.form.get("pull_combinations", 0))
        pers5 = int(request.form.get("pers5") or 0)
        pers6 = int(request.form.get("pers6") or 0)
        vehlist = [int(x.strip()) for x in vehlist_input.split(",") if x.strip()]

        veh2 = vehlist.copy()
        veh2.sort(reverse=True)
        validate_inputs(vehlist, pers5, pers6)

        backup_group = pers5
        backupsize = 5
        primary_group = pers6

        results_1 = optimal_allocation(veh2[:].copy(), primary_group, backup_group, 6, backupsize)
        results = trickle_down(results_1, backupsize)
        off = [backup_group - results[0][0], primary_group - results[0][1]]

        if not results or not isinstance(results, list) or len(results) < 2:
            raise ValueError("Invalid results returned from calculations.")

        sorted_allocations, sorted_spaces, sorted_sizes, number = sort_closestalg_output(results, backupsize)

        if sum(off) <= pers6 and backupsize == 5:
            combos, listing = call_sixesFlipped(sorted_allocations, sorted_spaces, off.copy(), backupsize, None)
        else:
            combos, listing = call_combine(sorted_allocations, sorted_spaces, off.copy(), backupsize, None)

        listing1 = listing.copy()
        combos1 = combos.copy()
        combos3 = combos1.copy()
        listing3 = listing1.copy()
        rem_vehs1 = unused(sorted_allocations.copy(), combos.copy())

        if combos:
            for elem in rem_vehs1:
                combos1.append([elem])
                listing1.append([0, 0])

            combos2, newalloc = call_optimize(
                sorted_allocations.copy(),
                listing1,
                backupsize,
                combos1,
                sorted_spaces,
            )
            combos3 = combos2
            listing3 = newalloc

        combos, listing, progress = cleanup(combos3, sorted_spaces, listing3)
        while progress:
            combos,listing, progress = cleanup(combos, sorted_spaces, listing)
        damage = harm(combos.copy(), sorted_allocations.copy())
        totalhelp = combosSum(combos.copy(), sorted_allocations.copy(), off.copy())

        combos = person_calc(combos.copy(), sorted_sizes.copy())
        alllist = alltogether(combos, listing, damage)

        less = nonzero(sorted_spaces, sorted_sizes)
        rem_vehs2 = unused1(less[1], combos.copy())
        rem_vehs = quant(rem_vehs2)

        restored_vehs, restored_all, restored_spaces = restore_order(
            vehlist[:].copy(), sorted_sizes, sorted_allocations, sorted_spaces
        )

        combined_sorted_data = [
            [restored_vehs[i], restored_all[i], restored_spaces[i], number[i]]
            for i in range(len(sorted_sizes))
        ]

        session["sorted_allocations"] = combined_sorted_data
        session["totalhelp"] = totalhelp
        session["alllist"] = alllist
        session["backupsize"] = backupsize

        if pull_combinations==0:
            session["vehlist"] = vehlist
            session["pers5"] = pers5
            session["pers6"] = pers6
        elif pull_combinations!=0:
            session["vehlist"] = allone(combos.copy())
            session["pers6"] = totalhelp[1]
            session["pers5"] = totalhelp[0]

        session["rem_vehs"] = rem_vehs
        session["results"] = [results[0], off]

        return redirect(url_for("test_page"))

    except Exception as e:
        return render_template(
            "index.html",
            error_message=f"An error occurred: {str(e)}",
            vehlist=vehlist_input,
            pers5=pers5,
            pers6=pers6,
            results=None,
            totalhelp=None,
            sorted_allocations=None,
            rem_vehs=None,
            alllist=None,
            backupsize=None,
            matrices_result=session.get("matrices_result"),
            allocations_only=int(request.form.get("allocations_only", 0)),
            ranges_result=session.get("ranges_result"),
            total_people=session.get("total_people", ""),
            people=session.get("people", ""),
            crews=session.get("crews", ""),
            zip=zip,
            enumerate=enumerate,
            len=len,
        )

@app.route("/matrices", methods=["POST"])
def matrices():
    return_path = _safe_return_path(session.get("return_after_matrices"))

    user_ip, xff_chain = get_client_ip()
    geo = lookup_city(user_ip)
    device_id = get_device_id()

    try:
        people_input = request.form.get("people", "").strip()
        crews_input = request.form.get("crews", "").strip()
        people = int(people_input) if people_input else 0
        crews = int(crews_input) if crews_input else 0

        session["matrices_result"] = compute_matrices(people, crews)
        session["ranges_result"] = compute_ranges(people)
        session["people"] = people
        session["crews"] = crews

        if (not is_hidden_ip(user_ip)):
            if return_path == "/test":
                session["pending_matrices_test_print"] = _build_matrices_payload_lines(
                    people, crews
                )
            else:
                log_append({
                    "ip": user_ip,
                    "device_id": device_id,
                    "xff": xff_chain,
                    "remote_addr": request.remote_addr,
                    "geo": geo,
                    "timestamp": _now_ts(),
                    "event": "matrices",
                    "input": {
                        "people": people,
                        "crews": crews,
                        "return_path": return_path,
                    },
                })

    except Exception:
        pass

    return redirect(return_path)

@app.route("/logout/trainer", methods=["POST"], strict_slashes=False)
def logout_trainer():
    session.pop("trainer_authed", None)
    return ("", 204)

@app.route("/trainer_login", methods=["GET", "POST"], strict_slashes=False)
def trainer_login():
    error = None
    if request.method == "POST":
        pwd = request.form.get("password", "")
        if pwd == TRAINER_PASSWORD_VIEW:
            session["trainer_authed"] = True
            return render_template(
                "set_tab_ok.html",
                tab_key="tab_ok_trainer",
                next_url=url_for("trainer_view"),
            )
        error = "Incorrect password."
    return render_template("trainer_login.html", error=error)

@app.route("/trainer", strict_slashes=False)
def trainer_view():
    if not is_trainer_authed():
        session.pop("trainer_authed", None)
        return redirect(url_for("trainer_login"))

    purge_old_entries()

    entries = log_get_all()
    entries = [e for e in entries if e.get("event") in {"input", "matrices"}]

    grouped_entries = build_grouped_entries(entries)
    return render_template("trainer.html", grouped_entries=grouped_entries)


@app.route("/view_once", methods=["POST"], strict_slashes=False)
def view_once():
    user_ip, xff_chain = get_client_ip()
    geo = lookup_city(user_ip)
    device_id = get_device_id()

    if is_hidden_ip(user_ip):
        return ("", 204)

    data = request.get_json(silent=True) or {}
    tab_id = (data.get("tab_id") or "").strip()
    if not tab_id or len(tab_id) > 80:
        return ("", 204)

    seen = session.get("view_once_seen_tabs", {})
    last_ip = seen.get(tab_id)

    if last_ip != user_ip:
        print_event(
            event="view",
            user_ip=user_ip,
            device_id=device_id,
            geo=geo,
            xff_chain=xff_chain,
            remote_addr=request.remote_addr or "",
            payload_lines=None,
        )

        seen[tab_id] = user_ip

        if len(seen) > 200:
            items = list(seen.items())[-200:]
            seen = dict(items)

        session["view_once_seen_tabs"] = seen

    return ("", 204)

@app.after_request
def after_request(resp):
    if request.path.startswith("/trainer"):
        resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"

    if not request.cookies.get(DEVICE_COOKIE_NAME):
        did = get_device_id()
        resp.set_cookie(
            DEVICE_COOKIE_NAME,
            did,
            max_age=DEVICE_COOKIE_MAX_AGE,
            httponly=True,
            samesite="Lax",
            secure=COOKIE_SECURE,
            path="/",
        )

    return resp

if __name__ == "__main__":
    app.run()
