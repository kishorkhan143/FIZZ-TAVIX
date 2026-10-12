"""
Synthetic shared-lab login generator (no real identities / production logs).

Labels
  0 NORMAL            ordinary logins incl. typo noise (1-2 fails then success)
  1 BRUTE_FORCE       many rapid failures against one account from one source
  2 PASSWORD_SPRAY    one source, many different accounts, 1-2 fails each
  3 FAIL_THEN_SUCCESS several failures then a success (possible account takeover)
  4 AFTER_HOURS       successful login outside lab hours

Scenarios deliberately overlap with normal behaviour (slow brute force, benign
late-evening sessions, 3-fail typo bursts) so the model must learn boundaries,
not a hard-coded threshold.
"""
import random
from datetime import datetime, timedelta, timezone

LABELS = ["NORMAL", "BRUTE_FORCE", "PASSWORD_SPRAY", "FAIL_THEN_SUCCESS", "AFTER_HOURS"]
COUNTRIES = ["India"] * 9 + ["United States", "Germany", "Singapore"]


def _rec(rid, ts, user, ip, ok, comp, country="India"):
    return {"row_number": rid, "timestamp": ts, "user": user, "ip": ip,
            "status": "SUCCESS" if ok else "FAILURE", "target_computer": comp, "country": country}


def generate(n_per_class=600, seed=0):
    """Return list of (records_for_one_scenario, label). Each scenario is self-contained."""
    rng = random.Random(seed)
    out = []
    rid = [0]

    def nid():
        rid[0] += 1
        return rid[0]

    def base_day():
        d = datetime(2026, 10, 1, tzinfo=timezone.utc) + timedelta(days=rng.randint(0, 20))
        return d

    def uid():
        return f"stu{rng.randint(1, 400):03d}"

    def ipaddr():
        return f"10.{rng.randint(0, 3)}.{rng.randint(0, 20)}.{rng.randint(2, 250)}"

    def comp():
        return f"LAB{rng.randint(1, 4)}-PC{rng.randint(1, 30):02d}"

    def lab_time():
        return base_day().replace(hour=rng.randint(8, 17), minute=rng.randint(0, 59), second=rng.randint(0, 59))

    def off_time():
        return base_day().replace(hour=rng.choice([0, 1, 2, 3, 4, 5, 19, 20, 21, 22, 23]),
                                  minute=rng.randint(0, 59), second=rng.randint(0, 59))

    for _ in range(n_per_class):
        # ---- 0 NORMAL
        u, ip, c, t = uid(), ipaddr(), comp(), lab_time()
        recs = []
        kind = rng.random()
        if kind < 0.55:                                  # clean login(s)
            for _k in range(rng.randint(1, 3)):
                recs.append(_rec(nid(), t, u, ip, True, c, rng.choice(COUNTRIES)))
                t += timedelta(minutes=rng.randint(20, 120))
        elif kind < 0.85:                                # typo then success
            for _k in range(rng.randint(1, 2)):
                recs.append(_rec(nid(), t, u, ip, False, c)); t += timedelta(seconds=rng.randint(8, 60))
            recs.append(_rec(nid(), t, u, ip, True, c))
        elif kind < 0.93:                                # forgotten password: 3 slow fails then success
            for _k in range(3):
                recs.append(_rec(nid(), t, u, ip, False, c)); t += timedelta(seconds=rng.randint(30, 150))
            recs.append(_rec(nid(), t, u, ip, True, c))
        else:                                            # legit late-evening lab session (grey zone)
            t = base_day().replace(hour=rng.choice([18, 19]), minute=rng.randint(0, 40))
            recs.append(_rec(nid(), t, u, ip, True, c))
        # bystander traffic
        for _k in range(rng.randint(0, 3)):
            recs.append(_rec(nid(), lab_time(), uid(), ipaddr(), rng.random() > 0.1, comp()))
        out.append((recs, 0, (u, ip)))

        # ---- 1 BRUTE_FORCE
        u, ip, c, t = uid(), ipaddr(), comp(), lab_time()
        n = rng.randint(5, 40)
        slow = rng.random() < 0.25                       # low-and-slow variant
        recs = []
        for _k in range(n):
            recs.append(_rec(nid(), t, u, ip, False, c, rng.choice(COUNTRIES)))
            t += timedelta(seconds=rng.randint(20, 70) if slow else rng.randint(1, 15))
        if rng.random() < 0.15:
            recs.append(_rec(nid(), t, u, ip, True, c))
        out.append((recs, 1, (u, ip)))

        # ---- 2 PASSWORD_SPRAY
        ip, t = ipaddr(), lab_time()
        k = rng.randint(4, 25)
        recs = []
        for _k in range(k):
            u = f"stu{rng.randint(1, 400):03d}"
            for _j in range(rng.randint(1, 2)):
                recs.append(_rec(nid(), t, u, ip, False, comp()))
                t += timedelta(seconds=rng.randint(2, 25))
        if rng.random() < 0.2:
            recs.append(_rec(nid(), t, u, ip, True, comp()))
        out.append((recs, 2, (None, ip)))

        # ---- 3 FAIL_THEN_SUCCESS
        u, ip, c, t = uid(), ipaddr(), comp(), lab_time()
        recs = []
        for _k in range(rng.randint(4, 12)):
            recs.append(_rec(nid(), t, u, ip, False, c)); t += timedelta(seconds=rng.randint(3, 40))
        recs.append(_rec(nid(), t, u, ip, True, c, rng.choice(COUNTRIES)))
        out.append((recs, 3, (u, ip)))

        # ---- 4 AFTER_HOURS
        u, ip, c, t = uid(), ipaddr(), comp(), off_time()
        recs = [_rec(nid(), t, u, ip, True, c)]
        if rng.random() < 0.4:
            recs.append(_rec(nid(), t + timedelta(minutes=rng.randint(5, 90)), u, ip, True, c))
        out.append((recs, 4, (u, ip)))
    return out
