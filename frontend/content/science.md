# Does Alpha flock?

A starling flock turns as one body. No bird leads it. Each one watches a handful of neighbours, and yet a turn started at one edge crosses thousands of birds in under a second. In 2010 a group of physicists in Rome worked out why: the birds' correlations are scale-free. The reach of one bird's influence is not fixed at some number of metres — it grows with the flock itself. A flock of three thousand correlates across three thousand. That is the fingerprint of a system sitting exactly at a tipping point, and it is what lets a thousand animals behave like one.

Alpha is not a flock. It is 108 regions on a fixed grid, and its "velocities" are things like stability and resource density. But the question carries over intact, and so does the arithmetic that answers it: does a region's influence reach across the world, or die at its own doorstep?

The vocabulary on this page is ours, not the field's — "reach", "flocking", "patches" all have proper names in the literature. The [FAQ maps every one of them](/faq), so you can go find the papers.

## How the reach is measured

Take every region's stability and subtract the world average. What is left is which regions run hot and which run cold. Now ask: when one runs hot, do the regions one step away run hot too? Then two steps, three, across the map. Plot that against distance and you have the reach curve.

Because hot and cold cancel exactly — that is what subtracting the average does — the curve has to dip below zero somewhere. The crossing is not news; the arithmetic guarantees it. Where it crosses is the news. That distance is the reach: how far a region's influence carries before it stops meaning anything.

The starling paper proves that same cancellation as an exact identity, which makes it a test the measurement can be held to rather than a footnote. Ours passes it to fourteen decimal places, so whatever the numbers below say, a bent ruler is not the reason.

## Why a big reach is not enough

A long reach could just mean a big map. The deciding question is whether reach grows with the map. Double the world; if the reach doubles too, the system is scale-free and it flocks. If the reach stays put, it has a fixed patch size and that is all.

That is how the starling result was reached, and it was never a claim about one flock. The group in Rome filmed twenty-four of them, from a hundred and twenty birds up to four thousand, measured each flock's reach, and found it landed at about a third of the flock's width every time. The finding is the line through those twenty-four points. No single flock could have carried it.

## One world is not an experiment

Alpha grows from a seed: one number that fixes every roll the world will ever make. Change it and the same rules build a different world — same physics, different history. So a reach measured in one seeded world is a fact about that world, not about the rules that made it.

That matters more than it sounds. Run the size test under one seed, then another, and the trend it reports swings by about ±0.09 with nothing changed but the seed — while the entire gap between "reach does not grow" and "reach grows the way a flock's does" is 0.17 wide. One world lands wherever its seed drops it. This page used to print that coin flip as the answer.

So the test now builds four sizes under eight seeds — thirty-two worlds — and reports the trend along with the spread the seeds actually produced. It may call the question settled only when that spread falls entirely on one side of the line. Otherwise it says the run did not settle it, which is a thing the old single-world test had no way to say and often should have.

Thirty-two worlds cost minutes, so the test does not run when you open this page. The worker measures it on a timer and this page reports what it last found. Each world is replayed to a fixed depth rather than to Alpha's present age, because Alpha settles early — its chirality locks within a few hundred ticks, and the reach at tick twelve thousand is the reach at two thousand for six times the work. The question is whether the *rules* flock, which is not a question about how old Alpha happens to be today. The page gives you both numbers anyway: how deep the test replayed, and how old Alpha was when it ran.

## What the reach turns out to be

The ensemble has run, and the answer is not close. Across thirty-two worlds — four sizes from a hundred and eight regions up to four hundred and thirty-two, eight seeds each — the reach barely moves: it sits near one to two regions at every size, and the trend against size comes back with a spread that straddles the line rather than falling cleanly on one side. By the test's own rule that reads as *did not settle it*. But the seed spread is not the whole reason, and here the phrase means something sharper than "measure more."

Alpha's fields do not talk to their neighbours. A region's stability, energy, and resource each move on their own noise, pulled toward a world-wide average and drawn down by the life inside that one region — there is no term anywhere that couples a region to the one beside it. Without such a term the reach *cannot* grow with the map, because nothing carries a fluctuation from one region to the next. The measurement is not short of worlds; it is reading a length pinned at the grid's own doorstep by construction. Ten thousand regions would report the same one-to-two.

So the honest answer is that Alpha, as written, does not flock — not "not yet," but *not with these rules*. The single term that would change it is a spatial coupling: let each region's field pull a little toward the average of its neighbours (a lattice Laplacian), and reach becomes something the coupling strength can tune — weak coupling, short reach; strong coupling, a reach that grows with the world the way a flock's does. That term is not in Alpha today. Adding it, then sweeping it to watch reach track the coupling, is what would turn this page from a null result into an experiment. Until then it reports an honest null: the rules do not flock, and the measurement says so cleanly.

## Where Alpha does sit at a tipping point

The reach test looked for a critical transition in space and found none. But Alpha has one — in a different variable. Its regions each carry a molecular *handedness*, and whether the whole world commits to a single hand turns on one control parameter: the strength of a symmetry-breaking field. Sweep that field across eight seeds and the world snaps between two regimes. At field strength zero, no world of the eight ever goes single-handed; nudge it to a small value and every one of the eight does. The map goes from a patchwork of opposing hands to one hand everywhere, and the crossover is sharp.

The fingerprint the flock test was hunting for shows up here plainly: **critical slowing**. As you tune the world toward the edge of the transition, the time it takes a region to lock its hand stretches out — around 58 ticks well inside the committed regime, 69 nearer the edge, 81 nearer still, and then, past the critical point, never. A relaxation time that diverges as you approach a threshold is the textbook signature of a continuous transition, and Alpha reproduces it. So the honest scorecard is: Alpha does not flock in space, but it does sit at a genuine tipping point in its chirality — a phase transition with a control parameter, a sharp boundary, and critical slowing on approach.

This one is measured offline rather than live — the sweep costs a few minutes across the seed ensemble, so it runs from `make sweep` and `make phase` rather than on page load. The full phase diagram, the mechanism, and the papers it maps onto are in the [chirality design note](/faq); the raw sweep lives in the repository.

## Why some numbers are missing

Several statistics on this page can be computed and would not mean anything. Rather than print a confident-looking figure built on three observations, those panels leave the slot empty and say what is missing.

A number on a screen gets believed, and a believed number gets quoted. Greying one out does not help — a faded number is still read. So where the evidence cannot carry a figure, there is no figure, only the reason and the amount of evidence it would take. Every panel states how much it stands on.
