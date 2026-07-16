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

That test is expensive — it rebuilds the universe from its seed at four different sizes and replays every tick — so it does not run when you open this page. The simulation worker measures it on a timer and this page reports what it last found, with the tick it was measured at. That is how the claim honestly reads anyway: you ran the experiment, you report what it said.

## Why some numbers are missing

Several statistics on this page can be computed and would not mean anything. Rather than print a confident-looking figure built on three observations, those panels leave the slot empty and say what is missing.

A number on a screen gets believed, and a believed number gets quoted. Greying one out does not help — a faded number is still read. So where the evidence cannot carry a figure, there is no figure, only the reason and the amount of evidence it would take. Every panel states how much it stands on.
