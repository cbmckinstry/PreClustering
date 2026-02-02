from Master import *
import csv
from pathlib import Path
from itertools import combinations_with_replacement
from datetime import datetime
from zoneinfo import ZoneInfo
from collections import Counter

def main(vehlist,pers5,pers6):
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

        if all(flags):
            break

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

def multisets(n,upper):
    return [list(c) for c in combinations_with_replacement(range(1, upper), n)]

def multiset_subset(combos, vehicles):
    used = Counter(x for combo in combos for x in combo)
    avail = Counter(vehicles)
    return all(used[v] <= avail[v] for v in used)

if __name__ == '__main__':
    lower=26
    upper=30
    vers = [0,1]
    priorities = [6,5]
    for size in range(lower,upper+1):
        for ver in vers:
            for pr in priorities:
                vars = [0, 5, 4, 3, 2, 1]
                sets = multisets(size, pr)

                timestamp = datetime.now().strftime("%M%S")
                filepath = Path.home() / "Desktop" / f"trial{pr}s-{ver}" / f"{size}_{timestamp}.csv"

                skip_sums = {1, 2, 3, 4, 7, 8, 9, 13, 14, 19}

                for vehicles in sets:
                    s = sum(vehicles)
                    if s in skip_sums and ver!=1:
                        continue
                    if pr==6:
                        if ver==0:
                            pers5 = vars[s%6]
                            remainder = s - 5*pers5
                            pers6 = remainder // 6
                        else:
                            pers6 = s//6
                            pers5 = 0
                    elif pr==5:
                        if ver==0:
                            pers6 = s%5
                            remainder = s - 6*pers6
                            pers5 = remainder // 5
                        else:
                            pers5 = s//5
                            pers6 = 0
                    else:
                        break
                    combos, init, off = main(vehicles, pers5, pers6)
                    if combos:
                        combos = [sorted(inner) for inner in combos]
                    used_space = sum(sum(c) for c in combos) if combos else 0
                    validCheck = (
                        combos is not None and init is not None and off is not None
                        and len(init) == len(combos)
                        and multiset_subset(combos, vehicles)
                        and s >= used_space >= 5*off[0] + 6*off[1]
                        and sum(i[0] for i in init) == off[0]
                        and sum(i[1] for i in init) == off[1]
                    )
                    flags = determineflags(combos, init)
                    writetocsv(filepath, vehicles, pers5, pers6, combos, validCheck, flags)

                timestamp = datetime.now(ZoneInfo("America/Chicago")).strftime("%Y-%m-%d %H:%M:%S %Z")

                print(f"[{timestamp}] Wrote results for {size} to: {filepath}")
    print("All done!")
