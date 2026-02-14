from __future__ import annotations

import logging
import subprocess
import time
import os
import socket
import re
from pathlib import Path


# ==========================================
# KEEP NORMAL OUTPUT, ONLY FILTER PY4J SPAM
# ==========================================

class _DropPy4JSpam(logging.Filter):
    DROP_SUBSTRINGS = (
        "Exception while sending command.",
        "Py4JNetworkError",
        "Answer from Java side is empty",
        "An error occurred while trying to connect to the Java server",
        "Connection refused",
        "Connection reset by peer",
        "Error while receiving",
    )

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        if record.name.startswith("py4j"):
            return False
        return not any(s in msg for s in self.DROP_SUBSTRINGS)


def _install_logging_filters():
    root = logging.getLogger()
    root.addFilter(_DropPy4JSpam())
    for h in root.handlers:
        h.addFilter(_DropPy4JSpam())
    logging.getLogger("py4j").setLevel(logging.CRITICAL)
    logging.getLogger("py4j.java_gateway").setLevel(logging.CRITICAL)


_install_logging_filters()


# ==========================================
# PROJECT CONFIG
# ==========================================

PROJECT_DIR = Path(__file__).resolve().parent
JAVA_CLASS = "Combine"
PY4J_JAR = PROJECT_DIR / "py4j0.10.9.9.jar"

PY4J_HOST = "127.0.0.1"
PY4J_PORT = 25333

CP_SEP = ";" if os.name == "nt" else ":"
os.chdir(PROJECT_DIR)


# ==========================================
# JAVA CONTROL
# ==========================================

def compile_java():
    java_file = PROJECT_DIR / f"{JAVA_CLASS}.java"
    class_file = PROJECT_DIR / f"{JAVA_CLASS}.class"

    if not PY4J_JAR.exists():
        raise RuntimeError(f"py4j jar not found at: {PY4J_JAR}")
    if not java_file.exists():
        raise RuntimeError(f"Java file not found at: {java_file}")

    needs_compile = True
    if class_file.exists():
        needs_compile = java_file.stat().st_mtime > class_file.stat().st_mtime

    if needs_compile:
        print("[*] Compiling Java...")
        cp = f"{PY4J_JAR}{CP_SEP}{PROJECT_DIR}"
        subprocess.check_call(["javac", "-cp", cp, str(java_file)])
    else:
        print("[*] Java already compiled.")


def start_java():
    print("[*] Starting Java GatewayServer...")
    cp = f"{PY4J_JAR}{CP_SEP}{PROJECT_DIR}"
    cmd = ["java", "-cp", cp, JAVA_CLASS]
    proc = subprocess.Popen(cmd, cwd=str(PROJECT_DIR))
    return proc


def wait_for_port(host: str, port: int, timeout_s: float = 20.0):
    deadline = time.time() + timeout_s
    last_err = None
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return
        except OSError as e:
            last_err = e
            time.sleep(0.2)
    raise RuntimeError(
        f"Py4J port not reachable at {host}:{port} after {timeout_s}s. Last error: {last_err}"
    )


def hard_kill(proc):
    if proc is None:
        return
    try:
        proc.kill()
    except Exception:
        pass


def shutdown_gateway_if_present():
    try:
        import Extension
        gw = getattr(Extension, "gateway", None)
        if gw is not None:
            try:
                gw.shutdown()
            except Exception:
                pass
            try:
                gw.close()
            except Exception:
                pass
    except Exception:
        pass


# ==========================================
# TRIAL FOLDER NAMING (GLOBAL A COUNTER)
# ==========================================

_TRIAL_ANY_RE = re.compile(r"^Trial_.*_(\d+)$")


def _next_global_A(base_dir: Path) -> int:
    """
    Scan base_dir for folders like Trial_*_<A> and return next A.
    """
    max_a = -1
    for p in base_dir.iterdir():
        if not p.is_dir():
            continue
        name = p.name
        if not name.startswith("Trial_"):
            continue
        m = _TRIAL_ANY_RE.match(name)
        if m:
            try:
                a = int(m.group(1))
                max_a = max(max_a, a)
            except ValueError:
                pass
    return max_a + 1


def next_trial_run_dir(base_dir: Path, lower: int, upper: int) -> Path:
    """
    Returns a unique run folder: Trial_{lower}-{upper}_{A}
    where A is globally unique across all Trial_* folders.
    """
    a = _next_global_A(base_dir)
    return base_dir / f"Trial_{lower}-{upper}_{a}"


# ==========================================
# MAIN
# ==========================================

java_proc = None
try:
    compile_java()
    java_proc = start_java()
    wait_for_port(PY4J_HOST, PY4J_PORT, timeout_s=20.0)

    # Now that Java is up, importing Master/Extension won't fail
    from Master import *  # noqa

    import csv
    from itertools import combinations_with_replacement
    from datetime import datetime
    from zoneinfo import ZoneInfo
    from collections import Counter

    def _ts_chicago() -> str:
        return datetime.now(ZoneInfo("America/Chicago")).strftime("%Y-%m-%d %H:%M:%S %Z")

    def log_new_block(run_dir: Path, lower: int, upper: int):
        print(f"[{_ts_chicago()}] ****** [BLOCK] " + str(lower)+"-"+str(upper)+ " ******")

    def log_new_size(run_dir: Path, size: int):
        print(f"[{_ts_chicago()}] [SIZE] {size}")

    def main(vehlist, pers5, pers6):
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
            combos, listing, progress = cleanup(combos, sorted_spaces, listing)

        combos = person_calc(combos.copy(), sorted_sizes.copy())
        return combos, listing, off


    def determineflags(combos, init):
        flags = [False, False, False, False, False, False, False]
        if not combos:
            return flags

        have_any4 = False
        seen3 = []
        have_two3_diff = False
        have_bad4 = False
        have_bad5 = False

        for x, c in enumerate(combos):
            L = len(c)
            if L not in (2, 3, 4, 5, 6):
                continue

            total = 5 * init[x][0] + 6 * init[x][1]

            if L == 4:
                have_any4 = True
                flags[2] = True
                if total < 15 and total not in {5, 6}:
                    have_bad4 = True

            elif L == 2:
                flags[0] = True

            elif L == 3:
                flags[1] = True
                if any(abs(total - t) >= 5 for t in seen3):
                    have_two3_diff = True
                seen3.append(total)

            elif L == 5:
                flags[3] = True
                if total < 20 and total not in {5, 6}:
                    have_bad5 = True

            elif L == 6:
                flags[4] = True

            if have_any4 and have_two3_diff:
                flags[5] = True
            if have_bad4 and have_bad5:
                flags[6] = True

        return flags


    def writetocsv(filepath, vehicles, pers5, pers6, combos, validCheck, flags):
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        file_exists = path.exists()

        combos_str = "" if not combos else "|".join(",".join(map(str, c)) for c in combos)

        with path.open("a", newline="") as f:
            w = csv.writer(f)
            if not file_exists:
                w.writerow([
                    "vehicles",
                    "sum_vehicles",
                    "pers5",
                    "pers6",
                    "ValidCombos",
                    "2s",
                    "3s",
                    "4s",
                    "5s",
                    "6s",
                    "4+3+3 Flag",
                    "5+4 Flag",
                    "combos"
                ])

            w.writerow([
                list(vehicles),
                sum(vehicles),
                pers5,
                pers6,
                validCheck,
                flags[0],
                flags[1],
                flags[2],
                flags[3],
                flags[4],
                flags[5],
                flags[6],
                combos_str
            ])


    def multisets(n, upper):
        return [list(c) for c in combinations_with_replacement(range(1, upper), n)]


    def multiset_subset(combos, vehicles):
        used = Counter(x for combo in combos for x in combo)
        avail = Counter(vehicles)
        return all(used[v] <= avail[v] for v in used)


    if __name__ == "__main__":

        start_lower = 5
        end_upper = 10
        block_size = 3  #inclusive on each end

        vers = [1, 0]
        priorities = [6, 5]
        print_pr = ["Most", "All"]

        BASE_DIR = Path(__file__).resolve().parent

        lower = start_lower
        while lower <= end_upper:
            upper = min(lower + block_size - 1, end_upper)

            RUN_DIR = next_trial_run_dir(BASE_DIR, lower, upper)
            RUN_DIR.mkdir(parents=True, exist_ok=False)

            # LOG: new block introduced
            log_new_block(RUN_DIR, lower, upper)

            for size in range(lower, upper + 1):
                # LOG: new size introduced
                log_new_size(RUN_DIR, size)

                for pr in priorities:
                    for ver in vers:
                        vars = [0, 5, 4, 3, 2, 1]
                        sets = multisets(size, pr)

                        filepath = RUN_DIR / f"{size}" / f"{pr}s_{print_pr[ver]}.csv"

                        skip_sums = {1, 2, 3, 4, 7, 8, 9, 13, 14, 19}

                        for vehicles in sets:
                            s = sum(vehicles)
                            if s in skip_sums and ver != 1:
                                continue

                            if pr == 6:
                                if ver == 0:
                                    pers5 = vars[s % 6]
                                    remainder = s - 5 * pers5
                                    pers6 = remainder // 6
                                else:
                                    pers6 = s // 6
                                    pers5 = 0

                            elif pr == 5:
                                if ver == 0:
                                    pers6 = s % 5
                                    remainder = s - 6 * pers6
                                    pers5 = remainder // 5
                                else:
                                    pers5 = s // 5
                                    pers6 = 0
                            else:
                                continue

                            combos, init, off = main(vehicles, pers5, pers6)

                            if combos:
                                combos = [sorted(inner) for inner in combos]

                            used_space = sum(sum(c) for c in combos) if combos else 0
                            validCheck = (
                                    combos is not None and init is not None and off is not None
                                    and len(init) == len(combos)
                                    and multiset_subset(combos, vehicles)
                                    and s >= used_space >= 5 * off[0] + 6 * off[1]
                                    and sum(i[0] for i in init) == off[0]
                                    and sum(i[1] for i in init) == off[1]
                            )

                            flags = determineflags(combos, init)
                            writetocsv(filepath, vehicles, pers5, pers6, combos, validCheck, flags)

                        print(f"[{_ts_chicago()}] Wrote results for {size}-{pr}s-{print_pr[ver]} to: {filepath}")

            lower += block_size

        print("All done!")

finally:
    shutdown_gateway_if_present()
    hard_kill(java_proc)
    print("[*] Shutdown complete.")