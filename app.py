"""The slow wave: a circular migration thought experiment on synthetic data."""
from dataclasses import replace

import altair as alt
import pandas as pd
import streamlit as st

from simulate import STRATEGIES, Settings, caveat_grid, simulate, strategy_summary, yeagerist_grid

st.set_page_config(page_title="The slow wave", page_icon="🌊", layout="wide")

COLORS = {"Full wave": "#C25E00", "Talks only": "#0072B2", "Circular plan": "#6B5CB8"}
SHAPES = {"Full wave": "square", "Talks only": "circle", "Circular plan": "triangle-up"}
color = alt.Scale(domain=STRATEGIES, range=[COLORS[s] for s in STRATEGIES])
shape = alt.Scale(domain=STRATEGIES, range=[SHAPES[s] for s in STRATEGIES])


@st.cache_data(show_spinner="Running the histories…")
def run(s: Settings):
    hist, reg, stories = simulate(s)
    base_hist, base_reg, _ = simulate(replace(s, return_trust=0.0))
    return hist, reg, stories, base_reg, caveat_grid(s), yeagerist_grid(s)


with st.sidebar:
    st.header("Assumptions")
    st.caption("Every number here is invented. Move them and watch what changes.")
    st.subheader("The circular plan")
    pace = st.slider("Rounds the wave spends on each region", 1, 4, 3)
    capacity = st.slider("Share of a region the island can host", 0.2, 1.0, 0.7, 0.05)
    tariff = st.toggle("Regions pay a tariff for refugee slots", value=True,
                       help="Tariffs fund 25% more room, but regions that don't pay get only 30% of their slots.")
    return_trust = st.slider("Trust gained from seeing evacuees go home", 0.0, 4.0, 2.5, 0.25,
                             help="The built-in circular effect. Set to 0 for the honest baseline.")
    st.subheader("The leader")
    rogue_hazard = st.slider("Chance per round the leader turns rogue", 0.0, 0.05, 0.01, 0.005, format="%.3f")
    memory_reach = st.slider("Share of Eldian resolve the leader can rewrite", 0.0, 1.0, 0.9, 0.05)
    st.subheader("The two caveats")
    ackerman = st.toggle("Ackerman immunity", value=True,
                         help="Ackermans' memories can't be rewritten, so they can still act against the leader.")
    friends = st.toggle("Friends' freedom", value=True,
                        help="The leader doesn't restrict their friends; each round they choose for themselves.")
    objection = st.slider("Chance per round a free friend objects to a plan on course", 0.0, 0.2, 0.06, 0.01,
                          disabled=not friends)
    st.subheader("The Yeagerists")
    yeag = st.slider("Yeagerists' share of the island's armed force", 0.0, 0.6, 0.3, 0.05,
                     help="Set to 0 to remove them; the rest of the model is then unchanged.")
    hostility = st.slider("How fast hosting foreigners angers them", 0.0, 2.0, 1.0, 0.25, disabled=yeag == 0)
    rewrite = st.toggle("Leader rewrites Yeagerist resolve while on course", value=False, disabled=yeag == 0,
                        help="Yeagerists are Eldian, so the leader can do this. It means controlling their "
                             "own people's minds, which is why it's off by default.")
    st.subheader("The world")
    invasion = st.slider("Chance per round the island is invaded, with no wave running", 0.0, 0.1, 0.03, 0.005,
                         format="%.3f")
    settlement = st.slider("Chance per round talks settle it, with no wave running", 0.0, 0.1, 0.02, 0.005,
                           format="%.3f")
    st.subheader("Run")
    histories = st.select_slider("Histories per path", [100, 200, 400], value=200)
    seed = st.number_input("Seed", 1, 9999, 7)

s = Settings(histories=histories, pace=pace, capacity=capacity, tariff=tariff, return_trust=return_trust,
             rogue_hazard=rogue_hazard, memory_reach=memory_reach, ackerman_immune=ackerman,
             friends_free=friends, objection=objection, invasion_hazard=invasion, settlement=settlement,
             yeagerist_strength=yeag, yeagerist_hostility=hostility, rewrite_yeagerists=rewrite, seed=int(seed))
hist, reg, stories, base_reg, grid, ygrid = run(s)
summ = strategy_summary(hist)

st.title("The slow wave")
st.markdown(
    "A destructive wave can't be stopped, only steered. What if it crossed the world slowly, one region at a "
    "time, and each region sheltered on the island before it arrived and went home after it passed? "
    "This simulates that **circular migration** idea against two other paths, and asks what happens when the "
    "one person steering the wave stops being accountable, and how a hardline faction at home responds."
)
st.info(
    "All data here is synthetic. The patterns come from assumptions set in the sidebar, not from evidence: "
    "the trust effect, the strength of each caveat and the Yeagerists' responses are built in. A fan-made thought experiment inspired by "
    "*Attack on Titan*.",
    icon="ℹ️",
)

cols = st.columns(3)
for col, name in zip(cols, STRATEGIES):
    row = summ.loc[name]
    col.metric(f"{name}: world's people lost, average", f"{row.world_lost:.0f}%")
    col.caption(f"The island was invaded in {row.island_fell:.0%} of histories, and "
                f"{row.regions_flattened:.1f} of 12 regions were flattened on average.")

st.subheader("Who carries the cost")
st.caption("Each mark is one history. The same 12-region worlds are replayed under every path.")
left, right = st.columns([3, 2])
jitter = alt.Chart(hist).transform_calculate(j="random()").mark_point(filled=True, opacity=0.35, size=28).encode(
    x=alt.X("world_lost_pct:Q", title="World's people lost (%)", scale=alt.Scale(domain=[0, 75])),
    y=alt.Y("strategy:N", sort=STRATEGIES, title=None),
    yOffset=alt.YOffset("j:Q"),
    color=alt.Color("strategy:N", scale=color, legend=None),
    shape=alt.Shape("strategy:N", scale=shape, legend=None),
    tooltip=["strategy", "history", "world_lost_pct", "regions_flattened", "island_fell"],
)
median = alt.Chart(hist).mark_tick(color="#222", thickness=3, size=34).encode(
    x="median(world_lost_pct):Q", y=alt.Y("strategy:N", sort=STRATEGIES))
left.altair_chart((jitter + median).properties(height=260, title="Lives lost in the world (black tick: median)"),
                  width="stretch", theme=None)
fell = summ.reset_index()[["strategy", "island_fell"]]
bars = alt.Chart(fell).mark_bar().encode(
    x=alt.X("island_fell:Q", title="Histories where the island was invaded", axis=alt.Axis(format="%"),
            scale=alt.Scale(domain=[0, 1])),
    y=alt.Y("strategy:N", sort=STRATEGIES, title=None),
    color=alt.Color("strategy:N", scale=color, legend=None),
    tooltip=["strategy", alt.Tooltip("island_fell:Q", format=".0%")],
)
labels = bars.mark_text(align="left", dx=4).encode(text=alt.Text("island_fell:Q", format=".0%"), color=alt.value("#222"))
right.altair_chart((bars + labels).properties(height=260, title="Risk to the island"), width="stretch", theme=None)
st.caption("Talks put the risk on the island; a wave puts it on the world. The circular plan tries to shrink both, "
           "and every region it passes is still flattened, even when its people get out.")

st.subheader("Does trust come back around?")
st.caption("Share of each region that evacuated, by the order the wave reached it, in histories where the plan was "
           "still on course. Dashed: the same worlds with the trust effect switched off.")
def by_order(r, label):
    on = r[(r["strategy"] == "Circular plan") & r["agreed_to_go"].notna()]
    out = on.groupby("visit_order")["agreed_to_go"].mean().reset_index()
    out["version"] = label
    return out
trust = pd.concat([by_order(reg, "Trust effect as set"), by_order(base_reg, "Trust effect off")])
tchart = alt.Chart(trust).mark_line(point=True, color=COLORS["Circular plan"]).encode(
    x=alt.X("visit_order:O", title="Region, in the order the wave reached it"),
    y=alt.Y("agreed_to_go:Q", title="Share evacuated", axis=alt.Axis(format="%"), scale=alt.Scale(domain=[0, 1])),
    strokeDash=alt.StrokeDash("version:N", scale=alt.Scale(domain=["Trust effect as set", "Trust effect off"],
                                                           range=[[1, 0], [6, 4]]), title=None),
    tooltip=["version", "visit_order", alt.Tooltip("agreed_to_go:Q", format=".0%")],
).properties(height=260)
st.altair_chart(tchart.configure_legend(orient="bottom"), width="stretch", theme=None)

st.subheader("The two caveats")
st.markdown(
    "The leader can rewrite the memories and resolve of Eldians, which leaves most opponents unable to act. "
    "**Ackerman immunity** keeps Ackermans, who are Eldian, out of that reach. **Friends' freedom** means the "
    "leader never restricts their friends, so each round the friends decide for themselves. Below, the circular "
    "plan is replayed on the same worlds with each caveat on and off, whatever the toggles say."
)
g = grid.copy()
long = pd.concat([
    g.assign(measure="Rogue turns stopped within 2 rounds", value=g["stopped_within_2"]),
    g.assign(measure="Plans halted while still on course", value=g["halted_on_course"]),
])
cases = list(g["case"])
gchart = alt.Chart(long).mark_bar().encode(
    y=alt.Y("case:N", sort=cases, title=None),
    x=alt.X("value:Q", title=None, axis=alt.Axis(format="%"), scale=alt.Scale(domain=[0, 1])),
    color=alt.Color("measure:N", legend=None, scale=alt.Scale(
        domain=["Rogue turns stopped within 2 rounds", "Plans halted while still on course"],
        range=["#009E73", "#B4562A"])),
    tooltip=["case", "measure", alt.Tooltip("value:Q", format=".0%")],
)
gtext = gchart.mark_text(align="left", dx=4, color="#222").encode(text=alt.Text("value:Q", format=".0%"))
c1, c2 = st.columns(2)
for col, m in zip([c1, c2], ["Rogue turns stopped within 2 rounds", "Plans halted while still on course"]):
    col.altair_chart((gchart + gtext).transform_filter(alt.datum.measure == m).properties(height=200, title=m),
                     width="stretch", theme=None)
st.caption(
    f"Rogue turns per case: {', '.join(f'{c} {n}' for c, n in zip(g['case'], g['turned']))}, out of "
    f"{s.histories} histories. Freedom cuts both ways: free friends add a check on a rogue leader, and they can "
    "also stop a plan that was still keeping its promises."
)

st.subheader("How the Yeagerists respond")
st.markdown(
    "The Yeagerists want the island safe and don't want foreigners on it. Every round the island shelters "
    "evacuees, their grievance grows. As it does, they may **harass evacuees**, **press the leader to speed the wave "
    "up**, or **stage a coup** that forces a full wave. If the leader turns rogue, they **shield** them from "
    "containment. They are Eldian, so a leader on course could simply rewrite their resolve. Below, the same worlds "
    "are replayed at each Yeagerist strength, with and without that rewrite."
)
yg = ygrid.copy()
yg["version"] = yg["rewrite"].map({False: "Their minds left alone", True: "Their resolve rewritten"})
dash = alt.StrokeDash("version:N", title=None, scale=alt.Scale(
    domain=["Their minds left alone", "Their resolve rewritten"], range=[[1, 0], [6, 4]]))
ycolor = alt.Color("strategy:N", title=None, scale=alt.Scale(
    domain=["Talks only", "Circular plan"], range=[COLORS["Talks only"], COLORS["Circular plan"]]))
yshape = alt.Shape("strategy:N", title=None, scale=alt.Scale(
    domain=["Talks only", "Circular plan"], range=[SHAPES["Talks only"], SHAPES["Circular plan"]]))
def yline(field, title):
    base = alt.Chart(yg).encode(
        x=alt.X("yeagerist_strength:Q", title="Yeagerists' share of the armed force", axis=alt.Axis(format="%")),
        y=alt.Y(f"{field}:Q", title=None, axis=alt.Axis(format="%"), scale=alt.Scale(domainMin=0)),
        color=ycolor, detail="version:N",
        tooltip=["strategy", "version", alt.Tooltip("yeagerist_strength:Q", format=".0%"),
                 alt.Tooltip(f"{field}:Q", format=".0%")],
    )
    lines = base.mark_line(strokeWidth=2).encode(strokeDash=dash)
    points = base.mark_point(filled=True, size=50).encode(shape=yshape)
    return (lines + points).properties(height=240, title=title)


y1, y2 = st.columns(2)
y1.altair_chart(yline("wave_forced", "Histories pushed into a full wave (coup or rogue leader)")
                .configure_legend(orient="bottom", columns=2), width="stretch", theme=None)
y2.altair_chart(yline("completed", "Circular plans completed as promised")
                .transform_filter(alt.datum.strategy == "Circular plan")
                .configure_legend(orient="bottom", columns=2), width="stretch", theme=None)
here = yg[(yg["strategy"] == "Circular plan") & (~yg["rewrite"])]
lo, hi = here.iloc[0], here.iloc[-1]
st.caption(
    f"For the circular plan, a full wave was forced in {lo.wave_forced:.0%} of histories with no Yeagerists and "
    f"{hi.wave_forced:.0%} at a {hi.yeagerist_strength:.0%} share; coups alone caused {hi.coup:.0%}. Talks only "
    "rarely gives them time: the island is often invaded or settled first. Rewriting their resolve erases most of "
    "the effect, which is the uncomfortable part: the cleanest result needs the leader to control their own people's "
    "minds. Harassment cost evacuees up to "
    f"{here['harassment_lost'].max():.1f}% of the world's people on average."
)

if tariff:
    st.subheader("Who pays for a slot")
    st.caption("Share of people lost in regions that paid the tariff and regions that didn't, circular plan only. "
               "Wealthier regions were more likely to pay.")
    circ = hist[hist["strategy"] == "Circular plan"].melt(
        value_vars=["lost_pct_paid_regions", "lost_pct_unpaid_regions"], var_name="group", value_name="lost").dropna()
    circ["group"] = circ["group"].map({"lost_pct_paid_regions": "Paid the tariff",
                                       "lost_pct_unpaid_regions": "Didn't pay"})
    pay = alt.Chart(circ).mark_boxplot(size=36, color="#6B5CB8", median={"color": "#222"}).encode(
        x=alt.X("lost:Q", title="People lost in those regions (%)"),
        y=alt.Y("group:N", title=None, sort=["Paid the tariff", "Didn't pay"]),
    ).properties(height=170)
    st.altair_chart(pay, width="stretch", theme=None)

st.subheader("One history")
pick = st.selectbox("History", list(range(1, 21)), format_func=lambda h: f"World {h}")
story_reg = reg[(reg["history"] == pick)].copy()
story_reg["evacuated"] = story_reg["agreed_to_go"].fillna(0) * story_reg["people_pct"]
story_reg["lost"] = story_reg["lost_pct"]
story_reg["untouched"] = story_reg.apply(lambda r: r.people_pct if not r.flattened else 0, axis=1)
story_reg["stayed_safe"] = (story_reg["people_pct"] - story_reg["evacuated"] - story_reg["lost"]
                            - story_reg["untouched"]).clip(lower=0)
tidy = story_reg.melt(id_vars=["strategy", "visit_order", "region"],
                      value_vars=["evacuated", "stayed_safe", "lost", "untouched"], var_name="outcome",
                      value_name="pct")
names = {"evacuated": "Sheltered on the island", "stayed_safe": "Stayed and survived", "lost": "Lost",
         "untouched": "Wave never reached"}
tidy["outcome"] = tidy["outcome"].map(names)
order = list(names.values())
story = alt.Chart(tidy).mark_bar().encode(
    x=alt.X("visit_order:O", title="Region, in the order the wave would reach it"),
    y=alt.Y("pct:Q", title="% of the world's people"),
    color=alt.Color("outcome:N", sort=order, scale=alt.Scale(domain=order,
                    range=["#6B5CB8", "#A9A3D6", "#C25E00", "#D9D9D9"]), title=None),
    order=alt.Order("order:Q"),
    column=alt.Column("strategy:N", sort=STRATEGIES, title=None),
    tooltip=["strategy", "region", "outcome", alt.Tooltip("pct:Q", format=".2f")],
).transform_calculate(order=f"indexof({order}, datum.outcome)").properties(width=260, height=220)
st.altair_chart(story.configure_legend(orient="bottom"), theme=None)
ev_cols = st.columns(3)
for col, name in zip(ev_cols, STRATEGIES):
    col.markdown(f"**{name}**")
    events = stories.get((name, pick), [])
    col.markdown("\n".join(f"- Round {t}: {e}" for t, e in events) or "- Nothing decisive within 48 rounds")

with st.expander("How the simulation works"):
    st.markdown(f"""
- **The world**: 12 regions of random size and wealth around an island, over 48 rounds. Each history is replayed
  under all three paths with the same seed, so differences come from the path, not the world.
- **Full wave**: the wave crosses two regions a round with no warning, and 70% of the people in its path are lost.
- **Talks only**: no wave. Each round the island faces a {invasion:.1%} chance of invasion and a {settlement:.1%}
  chance that talks settle things.
- **Circular plan**: the wave spends {pace} round(s) on each region. Before it arrives, the region evacuates to the
  island, limited by willingness and by room ({capacity:.0%} of a region, more with tariffs). People who stay face the
  same 70% loss. Evacuees go home after the wave passes, and later regions trust the plan more for each earlier
  region that came home. While a wave runs, invasion is five times less likely.
- **The leader**: each round on course there's a {rogue_hazard:.1%} chance they turn rogue and the wave speeds up.
  Containment then has a chance each round that grows with the opposition's strength: non-Eldian allies (never
  affected by memory), Ackermans (full strength if immune, otherwise reduced like any Eldian), other Eldians
  (reduced by memory reach) and any free friends who choose to act.
- **Free friends** each decide every round. On a rogue leader, each acts with 70% chance. On a plan still on course,
  each objects with the chance you set (1.5 times as often with tariffs), and two or more objecting friends can halt
  it. Half of them help with the evacuation each round, adding a little room.
- After an unwarned wave or a containment strike, invasion becomes 1.5 times as likely as before.
- **Yeagerists** ({yeag:.0%} of the armed force) build grievance each round the island hosts evacuees, more slowly
  while talks drag on, and lose it while a full wave runs. As grievance rises they may harass the region sheltering
  on the island (each free friend has an even chance of stepping in to protect them), add to the chance the leader
  turns rogue, or attempt a coup. A coup forces a full wave; it's less likely to succeed for every friend who
  defends the island. Free friends each defend with 60% chance; restricted friends always defend, because the
  leader directs them. Yeagerists also cut a rogue leader's chance of being contained and resist free friends who
  try to halt the plan. Set their share to 0 and the rest of the model runs exactly as it would without them.
""")

with st.expander("What this leaves out, and the ethics"):
    st.markdown("""
- **Getting out isn't the same as being unharmed.** Every region the plan passes is flattened: homes, farms,
  infrastructure. People come home to ruins, and that cost doesn't appear in the "lost" numbers.
- **The tariff turns refuge into something bought.** Regions that can't pay are left with less room, and the
  "Who pays" chart shows who bears that. Refuge offered only for payment would be widely considered unjust.
- **Forced displacement of whole populations is itself a serious harm**, even when temporary.
- **Rewriting the Yeagerists' resolve** removes most of their effect in this model, and it means a leader controlling
  their own people's minds to keep a plan on track. That's the same power the caveats exist to check.
- **The Yeagerists here are a faction model, not a portrait.** Their responses are three invented rules, and real
  hardline movements are driven by much more than one grievance number.
- **Circular migration** has a different meaning in migration research, where it describes people who move back
  and forth between countries for work. Here it's used loosely for a population leaving and returning in a circle.
- This is a thought experiment about accountability and trust, set in a fictional world. It isn't a policy proposal,
  and no result here is evidence about real people.
""")

with st.expander("The data"):
    st.dataframe(hist, width="stretch", hide_index=True, height=240)
    d1, d2 = st.columns(2)
    d1.download_button("Download histories (CSV)", hist.to_csv(index=False), "slow_wave_histories.csv", "text/csv")
    d2.download_button("Download regions (CSV)", reg.to_csv(index=False), "slow_wave_regions.csv", "text/csv")

st.caption("Synthetic data. Fan-made and not affiliated with the creators of Attack on Titan.")
