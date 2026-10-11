"""Synthetic data for "The slow wave", a fan-inspired thought experiment.

A world of 12 regions sits around an island. The island's leader controls a
destructive wave. Three paths are compared:

  Full wave        the wave crosses every region fast, with no warning
                   (the "loop" ending).
  Talks only       no wave; the island negotiates while facing a risk of
                   invasion every season.
  Circular plan    the wave moves slowly around the circle, one region at a
                   time. Each region evacuates to the island before the wave
                   arrives and goes home after it passes. The wave deters
                   invasion while it runs.

The circular plan depends on one person keeping it slow. Each season there's
a chance the leader turns rogue and speeds the wave up. Then a containment
strike can stop them. The leader can rewrite the memories and resolve of
Eldians (their people), which weakens most opposition. Two caveats change who
can still act:

  Ackerman immunity   Ackermans are Eldian but their memories can't be
                      rewritten, so they keep their full strength against
                      the leader.
  Friends' freedom    the leader promised not to restrict their friends, so
                      the friends choose for themselves each season: help
                      the evacuation, oppose the leader, or stand aside.
                      Freedom cuts both ways: they can also halt a plan that
                      was still on course.

A third group responds to whatever the leader does:

  Yeagerists          a hardline faction on the island. Hosting foreigners
                      builds their grievance. As it grows they may harass
                      evacuees sheltering on the island, press the leader to
                      speed the wave up, or stage a coup that forces a full
                      wave. They shield a leader who has turned rogue. They
                      are Eldian, so a leader on course could rewrite their
                      resolve; that is a switch, off by default, because it
                      means controlling their own people's minds.

Everything here is invented, and every number is an assumption you can change.
Two effects are BUILT IN:
  return_trust   regions that see earlier evacuees go home safely agree to
                 evacuate more readily (the circular part of the hypothesis).
                 Set it to 0 for the honest baseline.
  the caveats    containment strength comes from the opposition model below;
                 it isn't measured from anything.
"""
from dataclasses import dataclass, asdict, replace

import numpy as np
import pandas as pd

STRATEGIES = ["Full wave", "Talks only", "Circular plan"]
CAVEAT_CASES = [
    ("Neither caveat", False, False),
    ("Friends' freedom only", False, True),
    ("Ackerman immunity only", True, False),
    ("Both caveats", True, True),
]
REGIONS = 12
FRIENDS = 4
CONTAIN_SCALE = 0.5   # converts opposition strength into a per-season chance of success


@dataclass
class Settings:
    histories: int = 400
    seasons: int = 48
    pace: int = 3                  # seasons the slow wave spends on each region
    capacity: float = 0.7          # share of a region the island can host at once
    tariff: bool = True            # regions pay up front for refugee slots
    base_trust: float = 0.0        # log-odds of agreeing to evacuate, before any returns
    return_trust: float = 2.5      # added log-odds once every earlier region came home
    rogue_hazard: float = 0.01     # chance per season the leader turns rogue
    memory_reach: float = 0.9      # share of Eldian resolve the leader can rewrite
    ackerman_immune: bool = True
    friends_free: bool = True
    objection: float = 0.06        # chance per season a free friend objects to a plan on course
    invasion_hazard: float = 0.03  # chance per season the island is invaded, with no wave running
    settlement: float = 0.02       # chance per season talks settle it, with no wave running
    yeagerist_strength: float = 0.3   # Yeagerists' share of the island's armed force; 0 removes them
    yeagerist_hostility: float = 1.0  # how fast hosting foreigners builds their grievance
    rewrite_yeagerists: bool = False  # a leader on course rewrites Yeagerist resolve (an ethical cost)
    seed: int = 7


def _sigmoid(x):
    return 1 / (1 + np.exp(-x))


def _opposition(s, rng, friends_oppose_p):
    """Containment strength against the leader this season, and who took part."""
    eldian_left = 1 - s.memory_reach
    allies = 0.15                                  # non-Eldian allies, untouched by memory
    ackerman = 0.35 * (1.0 if s.ackerman_immune else eldian_left)
    if s.friends_free:
        n_friends = int((rng.random(FRIENDS) < friends_oppose_p).sum())
    else:
        n_friends = 0                              # restricted: their resolve is rewritten
    friends = 0.08 * n_friends
    others = 0.2 * eldian_left
    return CONTAIN_SCALE * (allies + ackerman + friends + others), n_friends


def _yeagerist_force(s, rogue):
    """Yeagerist force that acts this season. A leader on course may rewrite their resolve; a rogue one won't."""
    y = s.yeagerist_strength
    if s.rewrite_yeagerists and not rogue:
        y *= 1 - s.memory_reach
    return y


def run_history(s: Settings, strategy: str, rng: np.random.Generator, hid: int):
    pop = rng.uniform(0.5, 1.5, REGIONS)
    pop = pop / pop.sum() * 100                    # % of the world's people
    wealth = rng.uniform(0, 1, REGIONS)
    order = rng.permutation(REGIONS)               # the order the wave visits
    paid = (rng.random(REGIONS) < _sigmoid(-1 + 3 * wealth)) if s.tariff else np.ones(REGIONS, bool)

    lost = np.zeros(REGIONS)
    flattened = np.zeros(REGIONS, bool)
    agreed = np.full(REGIONS, np.nan)
    hosted_ok = 0                                  # earlier regions whose people came home
    hosted_total = 0
    island_fell = False
    rogue_since = None
    contained_at = None
    halted_by_friends = False
    on_plan = strategy == "Circular plan"
    rogue = strategy == "Full wave"
    if rogue:
        rogue_since = 1
    next_region = 0
    events = []
    # Yeagerist draws use their own stream, so with strength 0 every other draw matches the model without them.
    yrng = np.random.default_rng([s.seed, hid, 2])
    grievance = 0.0
    coup_season = None
    harassed_lost = 0.0
    hosting = None                                 # region whose evacuees are on the island now

    for t in range(1, s.seasons + 1):
        if island_fell:
            break
        # Yeagerists respond.
        y = _yeagerist_force(s, rogue)
        pressure = 0.0
        if s.yeagerist_strength > 0:
            grievance *= 0.95
            if on_plan and hosting is not None:
                grievance += 0.15 * s.yeagerist_hostility    # foreigners sheltering on the island
            elif not rogue and strategy != "Full wave":
                grievance += 0.06 * s.yeagerist_hostility    # stalled talks, the island still at risk
            else:
                grievance = max(grievance - 0.2, 0.0)         # a wave is running at full speed
            heat = _sigmoid(2 * (grievance - 2))
            pressure = 0.03 * y * heat
            # Harassment of evacuees on the island; free friends may step in to protect them.
            if on_plan and hosting is not None and yrng.random() < y * heat:
                guards = int((yrng.random(FRIENDS) < 0.5).sum()) if s.friends_free else 0
                hit = 0.1 * (0.7 ** guards) * agreed[hosting] * pop[hosting]
                lost[hosting] += hit
                harassed_lost += hit
                events.append((t, "Yeagerists harassed evacuees" + (f" ({guards} friends protected them)" if guards else "")))
            # A coup that forces a full wave.
            if not rogue and strategy != "Full wave" and coup_season is None:
                if yrng.random() < 0.25 * y * _sigmoid(2 * (grievance - 3)):
                    defenders = int((yrng.random(FRIENDS) < 0.6).sum()) if s.friends_free else FRIENDS
                    if yrng.random() < _sigmoid(4 * (y - 0.15)) * (1 - 0.15 * defenders):
                        on_plan, rogue, rogue_since, coup_season = False, True, t, t
                        events.append((t, "Yeagerist coup forced a full wave"))
                    else:
                        events.append((t, f"Yeagerist coup failed ({defenders} friends defended)"))
        # The leader's choice.
        if on_plan and rng.random() < s.rogue_hazard + pressure:
            on_plan, rogue, rogue_since = False, True, t
            events.append((t, "Leader turned rogue" + (" (Yeagerist pressure had raised the odds)" if pressure >= s.rogue_hazard else "")))
        # Free friends may object to a plan still on course.
        if on_plan and s.friends_free:
            obj_p = s.objection * (1.5 if s.tariff else 1.0)
            objectors = int((rng.random(FRIENDS) < obj_p).sum())
            if objectors >= 2:
                strength, _ = _opposition(s, rng, 0.0)
                strength += CONTAIN_SCALE * 0.08 * objectors
                strength *= 1 - 0.6 * _yeagerist_force(s, rogue)   # Yeagerists back the wave
                if rng.random() < 1 - np.exp(-strength):
                    on_plan, halted_by_friends = False, True
                    events.append((t, f"{objectors} friends halted the plan"))
        if not on_plan:
            hosting = None                         # evacuees go home or scatter once the plan stops
        # The wave.
        if rogue:
            for _ in range(2):                     # fast: two regions a season, no warning
                if next_region < REGIONS:
                    r = order[next_region]
                    lost[r] += pop[r] * 0.7          # no warning, no evacuation
                    flattened[r] = True
                    next_region += 1
        elif on_plan and next_region < REGIONS and (t - 1) % s.pace == 0:
            r = order[next_region]
            trust = hosted_ok / hosted_total if hosted_total else 0.0
            willing = _sigmoid(s.base_trust + s.return_trust * trust + rng.normal(0, 0.4))
            cap = s.capacity * (1.25 if s.tariff else 1.0)   # tariffs fund more room
            slots = cap if paid[r] else cap * 0.3
            if s.friends_free:
                slots += 0.03 * int((rng.random(FRIENDS) < 0.5).sum())  # friends who help
            evacuated = min(willing, slots, 1.0)
            agreed[r] = evacuated
            hosting = r
            lost[r] += pop[r] * (1 - evacuated) * 0.7
            flattened[r] = True
            hosted_total += 1
            hosted_ok += 1                         # on course, evacuees go home after it passes
            next_region += 1
            if next_region == REGIONS:
                on_plan, hosting = False, None
                events.append((t, "Wave finished the circle"))
        # Containment of a rogue leader.
        if rogue:
            strength, n = _opposition(s, rng, 0.7)
            strength *= 1 - 0.6 * _yeagerist_force(s, rogue)       # Yeagerists shield a rogue leader
            if rng.random() < 1 - np.exp(-strength):
                rogue, contained_at = False, t
                events.append((t, f"Leader contained ({n} friends took part)"))
        # Invasion of the island: deterred while a wave runs.
        wave_running = rogue or on_plan
        hz = s.invasion_hazard * (0.2 if wave_running else 1.0)
        if strategy == "Full wave" or contained_at is not None:
            hz *= 1.0 if wave_running else 1.5     # retaliation after an unwarned wave
        if not wave_running and rng.random() < s.settlement:
            events.append((t, "Talks reached a settlement"))
            break
        if rng.random() < hz:
            island_fell = True
            events.append((t, "Island invaded"))

    lost_paid = lost[paid & flattened].sum() / max(pop[paid & flattened].sum(), 1e-9) * 100 if s.tariff else np.nan
    lost_unpaid = lost[~paid & flattened].sum() / max(pop[~paid & flattened].sum(), 1e-9) * 100 if s.tariff else np.nan
    summary = {
        "history": hid, "strategy": strategy, "world_lost_pct": round(lost.sum(), 3),
        "regions_flattened": int(flattened.sum()), "island_fell": island_fell,
        "turned_rogue": rogue_since is not None and strategy == "Circular plan" and coup_season is None,
        "wave_forced": rogue_since is not None and strategy != "Full wave",
        "contained_season": contained_at,
        "seasons_to_contain": (contained_at - rogue_since + 1) if contained_at and rogue_since else None,
        "halted_by_friends": halted_by_friends,
        "completed": strategy == "Circular plan" and next_region == REGIONS and rogue_since is None
                     and not halted_by_friends,
        "yeagerist_coup": coup_season is not None, "coup_season": coup_season,
        "lost_to_harassment_pct": round(harassed_lost, 3), "yeagerist_grievance_end": round(grievance, 3),
        "lost_pct_paid_regions": None if np.isnan(lost_paid) else round(lost_paid, 3),
        "lost_pct_unpaid_regions": None if np.isnan(lost_unpaid) else round(lost_unpaid, 3),
    }
    regions = pd.DataFrame({
        "history": hid, "strategy": strategy, "visit_order": np.argsort(order) + 1,
        "region": [f"R{i + 1:02d}" for i in range(REGIONS)], "people_pct": pop.round(3),
        "wealth": wealth.round(3), "paid_tariff": paid, "agreed_to_go": agreed.round(3),
        "lost_pct": lost.round(3), "flattened": flattened,
    })
    return summary, regions, events


def simulate(s: Settings = Settings()):
    """Every strategy on the same worlds: history i uses the same seed under each."""
    rows, regions, stories = [], [], {}
    for strategy in STRATEGIES:
        for h in range(s.histories):
            rng = np.random.default_rng([s.seed, h])
            summ, reg, ev = run_history(s, strategy, rng, h + 1)
            rows.append(summ)
            regions.append(reg)
            if h < 20:
                stories[(strategy, h + 1)] = ev
    hist = pd.DataFrame(rows)
    hist.attrs["settings"] = asdict(s)
    reg = pd.concat(regions, ignore_index=True)
    return hist, reg, stories


def caveat_grid(s: Settings = Settings()) -> pd.DataFrame:
    """The circular plan under each combination of the two caveats, same worlds."""
    out = []
    for label, ack, free in CAVEAT_CASES:
        s2 = replace(s, ackerman_immune=ack, friends_free=free)
        rows = [run_history(s2, "Circular plan", np.random.default_rng([s.seed, h]), h + 1)[0]
                for h in range(s.histories)]
        df = pd.DataFrame(rows)
        turned = df[df["turned_rogue"]]
        out.append({
            "case": label, "ackerman_immune": ack, "friends_free": free,
            "turned": len(turned),
            "stopped_within_2": (turned["seasons_to_contain"].fillna(99) <= 2).mean() if len(turned) else np.nan,
            "lost_when_turned": turned["world_lost_pct"].mean() if len(turned) else np.nan,
            "halted_on_course": df["halted_by_friends"].mean(),
            "world_lost": df["world_lost_pct"].mean(),
            "island_fell": df["island_fell"].mean(),
        })
    return pd.DataFrame(out)


YEAGERIST_LEVELS = [0.0, 0.15, 0.3, 0.45, 0.6]


def yeagerist_grid(s: Settings = Settings()) -> pd.DataFrame:
    """Talks only and the circular plan across Yeagerist strengths, with and without rewriting their resolve."""
    out = []
    for rewrite in (False, True):
        for level in YEAGERIST_LEVELS:
            s2 = replace(s, yeagerist_strength=level, rewrite_yeagerists=rewrite)
            for strategy in ("Talks only", "Circular plan"):
                df = pd.DataFrame([run_history(s2, strategy, np.random.default_rng([s.seed, h]), h + 1)[0]
                                   for h in range(s.histories)])
                out.append({
                    "strategy": strategy, "yeagerist_strength": level, "rewrite": rewrite,
                    "coup": df["yeagerist_coup"].mean(), "wave_forced": df["wave_forced"].mean(),
                    "completed": df["completed"].mean(), "world_lost": df["world_lost_pct"].mean(),
                    "harassment_lost": df["lost_to_harassment_pct"].mean(),
                })
    return pd.DataFrame(out)


def strategy_summary(hist: pd.DataFrame) -> pd.DataFrame:
    return hist.groupby("strategy").agg(
        world_lost=("world_lost_pct", "mean"), world_lost_median=("world_lost_pct", "median"),
        island_fell=("island_fell", "mean"), regions_flattened=("regions_flattened", "mean"),
    ).reindex(STRATEGIES)


if __name__ == "__main__":
    import os
    os.makedirs("data", exist_ok=True)
    hist, reg, _ = simulate()
    hist.to_csv("data/slow_wave_histories.csv", index=False)
    reg.to_csv("data/slow_wave_regions.csv", index=False)
    pd.set_option("display.width", 160)
    print(strategy_summary(hist).round(3))
    print(caveat_grid().round(3))
    print(yeagerist_grid(Settings(histories=200)).round(3).to_string())
    print("return_trust = 0:")
    h0, r0, _ = simulate(Settings(return_trust=0))
    print(strategy_summary(h0).round(3))
