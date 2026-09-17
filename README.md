# Physical baseline model (HEAPO heat pumps)

Say a house used 14,000 kWh of electricity last year. Is that bad?

You can't tell. A big old farmhouse with an electric water tank will burn a lot no matter
how well it's run. A small new flat will look fine even if something is genuinely wrong
with it. The raw number doesn't mean much on its own.

So this model asks a different question. How much more does this house use than *the same
house* would if it had been built to today's Swiss building rules? Same size, same plot,
same weather, same number of people in it. The only things that change are how well it's
insulated, whether it has radiators or floor heating, and how old the heat pump is.

To get that, we build the house twice on paper. Once the way it really is, once the way
the rules would have it. The difference between the two is the answer.

This came out of a research fellowship at Technology Campus Mainburg (THD), using
[HEAPO](https://arxiv.org/abs/2503.16993), a Swiss dataset of smart meter readings and
on-site inspections from about 1,400 homes.

## The rule that shaped everything

No number in here was picked because it made the results look good.

That sounds obvious. It isn't. The tempting move, when your model disagrees with the
meter, is to nudge a constant until they line up. Then you have a model that agrees with
your data and tells you nothing, because you fitted it to the answer.

So every constant comes from a published source, and the registry records where it came
from and whether someone actually opened the document and read it there. When the physics
and the meter disagree, we write down that they disagree. If a constant happened to
reproduce the measurements perfectly, that would worry me rather than please me.

The meter is only used for one thing: the weather.

## What comes out

A list of houses, worst first, and for each one a note about who should go and fix it.

That last part matters more than the ranking. The gap splits into two halves. Most of it
is usually the building itself, so insulation, radiators, the hot water tank, all of which
need a builder. The rest is the heat pump being an older design than what you'd install
today, which needs an installer. Telling someone "this house wastes 8,000 kWh a year" is
useless. Telling them "7,500 of that is the walls and 500 is the heat pump" is something
they can act on.

Of the 214 inspected homes:

| | how many | what it means |
|---|---:|---|
| act on these | 40 | clearly using more than the rules allow, and in the worst quarter |
| confirmed, lower priority | 118 | also using more, just less of it |
| can't say | 14 | the maths ran, but the uncertainty is wider than the result |
| never ran | 42 | missing building data, or too short a meter record |

There's no "this house is fine" category, on purpose. To say a house is fine you'd need
the whole uncertainty range to sit at or below the rules, and not one house in the set
does. So the model either finds extra usage or says nothing. It never hands out a clean
bill of health.

Every figure comes with a range rather than a single number, because the published
sources themselves disagree with each other. The ranking uses the *bottom* of that range.
If a house is listed at 7,142 kWh, that's the "at least this much" figure, the one that
survives reading every source in the least flattering way.

## Where to start

The walkthrough is the best entry point. It follows one house from the floor area an
inspector wrote on a form all the way to its place at the top of the list, and every
number along the way is labelled with where it came from: measured in the field, read out
of a published document, or calculated by us.

| file | what's in it |
|---|---|
| `outputs/p27/reports/p27_walkthrough.md` | the walkthrough. Read this one first. The `.html` next to it prints nicely if you want it on paper |
| `outputs/export/SCHEMA_v2.md` | what every column in the output means, and how it should be displayed |
| `outputs/export/physical_baseline_v2.parquet` | the results: 214 houses, 66 columns |
| `constants_ch.json` | every constant, with its source and whether it was verified |
| `CLAUDE.md` | the long version. Every decision, including the ones we rejected and why |

## Running it

Needs numpy and pandas. Matplotlib too, if you want the figures redrawn.

```
p22_registry.py      # the constants and their sources
p24_lifecycle.py     # should this heat pump be replaced or kept?
p13_visit_queue.py   # the visit axis
p11_export.py        # the output file. Refuses to write if a check fails
p_notebook.py        # the notebook
p27_walkthrough.py   # the walkthrough
```

Then run `p_test_all.py`, which runs three sets of checks and gives you one answer:

```
p_pipeline_test.py   141 checks on the physics and the pipeline
p10_portability.py    23 checks that no HEAPO column name leaked into the physics code
p28_page_test.py      runs the dashboard page without needing Streamlit installed
```

They're three files rather than one because each proves a different thing. When something
breaks you want to know which thing.

The raw HEAPO data isn't in this repository. It's read from the folder above and never
written to.

## Using it on other data

The physics code doesn't know anything about HEAPO. It asks for "floor area" and "number
of residents" as roles, and a small adapter file maps those onto whatever a given dataset
calls them. If you want to run this on German or Austrian homes, you write a new adapter
and a new constants file. `p10_portability.py` fails the build if a HEAPO column name ever
sneaks into the physics layer, which is the only way to keep that honest over time.

The method travels. The constants don't, since they're Swiss building rules.

## What it's bad at

Worth knowing before you trust any single number.

It's harsher on old houses than new ones. Per square metre, the physics underestimates
newer buildings by somewhere between a quarter and a half, so a straight ranking drifts
towards older homes. We kept construction era as a filter and kept the within-era ranking
as a separate column, but the tilt is real.

Some of the insulation values were read off bar charts in a government report, because
that's the only place they're published. They match the report's own text, but they're
approximate, and they're marked as derived rather than verified so you can tell them
apart.

The insulation split comes from one Swiss reference building, with a German building
typology used to set the uncertainty range around it.

The expected lifetime for air source heat pumps rests on 53 units, 43 of them from a
single installer. The authors of that study say themselves it's the weaker half of their
data. Ground source sits on 223 units and is more solid.

For 63 houses nobody wrote down when the heat pump was installed. Those show a heat pump
figure of zero, which does not mean the heat pump is fine. It means we're not claiming
anything, and the range next to it is the part to read.

Neither of the two energy totals is a power bill. Fridges, lights and washing machines
are left out of both, so only the difference between them tells you anything.

## What this model is not

It doesn't tell you whether a heat pump is set up wrong. That's a separate model with its
own section, and the two are never added together into one score.

It also isn't the same thing as comparing a house against similar houses nearby. That's a
third model, answering "is this house unusual for its type" rather than "is this house
worse than the rules allow". Both are useful. They're different questions, and mixing
their numbers would give you something that answers neither.
