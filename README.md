# The slow wave

A circular migration thought experiment in Streamlit, on synthetic data.

A destructive wave can't be stopped, only steered. What if it crossed the world slowly, one region at a time, and each region sheltered on the island before it arrived and went home after it passed? This compares that circular plan with two other paths, a full wave and talks only, across hundreds of invented 12-region worlds. It also asks what happens when the one person steering the wave stops being accountable.

Two caveats decide who can still stop a leader who turns rogue:

- **Ackerman immunity.** The leader can rewrite the memories and resolve of Eldians, but not Ackermans, so they keep their full strength against the leader.
- **Friends' freedom.** The leader promised never to restrict their friends, so the friends choose for themselves each round. That's a check on a rogue leader, and it also means they can halt a plan that was still on course.

A third group responds to the plan:

- **Yeagerists.** A hardline faction on the island whose grievance grows each round the island shelters foreigners. They may harass evacuees, press the leader to speed the wave up, or stage a coup that forces a full wave, and they shield a leader who has turned rogue. They are Eldian, so a switch lets the leader rewrite their resolve; it's off by default because that means controlling their own people's minds. Set their share of the armed force to 0 and the rest of the model runs exactly as it would without them.

The idea was sparked by themes in *Attack on Titan*. Nothing here is real data. The trust effect (regions that see evacuees go home are more willing to go) and the strength of each caveat are assumptions built into the model; set "Trust gained from seeing evacuees go home" to 0 for the honest baseline. The Yeagerists' responses are built in too.

## Run it

```
pip install -r requirements.txt
streamlit run app.py
```

`python simulate.py` regenerates the CSVs in `data/` and prints the summaries.

## What's inside

- `simulate.py`: the simulation and summaries, in plain NumPy and pandas.
- `app.py`: the Streamlit app.
- `data/`: the default synthetic dataset (400 histories per path, seed 7).
- `.streamlit/config.toml`: light theme, usage statistics off.

Fan-made and not affiliated with the creators of Attack on Titan.
