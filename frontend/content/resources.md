# Reference shelf for Alpha.

Evoverse uses these sources as orientation points for artificial life, evolution, astrobiology, and simulation literacy. They are references, not endorsements or copied content.

## Foundational cellular automata

- [Conway's Game of Life](https://en.wikipedia.org/wiki/Conway%27s_Game_of_Life): Foundational zero-player cellular automaton reference for grid state, ticks, emergence, and simple local rules.
- [ConwayLife.com](https://conwaylife.com/): Community, LifeWiki, pattern references, and tooling around Conway's Game of Life and related cellular automata.

Evoverse uses Conway's Game of Life as a conceptual origin, not as a direct rule clone. Conway's model is binary and local: cells live, die, or are born from neighbor counts. Evoverse keeps the grid and tick-based emergence, then raises each cell into a region aggregate so the product can track species, population, resources, collapse, interventions, events, and historical comparisons.

The design deliberately combines cellular automata, artificial-life ecology, resource dynamics, event sourcing, snapshot comparison, and observer/catalyst interaction. That combination makes Alpha less mathematically minimal than Conway's Life, but more legible as a product experience.

[Genesis Notes](/genesis) explains how that conceptual origin becomes Alpha's first product-facing world state.

## Biology and artificial life references

- [NASA Astrobiology](https://science.nasa.gov/astrobiology/): Origins, evolution, distribution, and future of life in the universe.
- [Darwin Online: On the Origin of Species](https://darwin-online.org.uk/EditorialIntroductions/Freeman_OntheOriginofSpecies.html): Primary historical reference for natural selection and species-level thinking.
- [International Society for Artificial Life](https://alife.org/): Community, publications, conferences, and current Artificial Life research signals.
- [Lenia: Biology of Artificial Life](https://arxiv.org/abs/1812.05433): Continuous cellular automata work useful for thinking about generated lifeforms.

## Origins of life & homochirality

These inform Alpha's *chirality field* — a symmetry-breaking maturity mechanic. The repository design note `docs/CHIRALITY_AND_MIND.md` explains how they map onto the tick engine. Orientation points, not endorsements.

- [Origin of biological homochirality by crystallization of an RNA precursor on a magnetic surface](https://www.science.org/doi/10.1126/sciadv.adg8274) (Ozturk, Liu, Sutherland, Sasselov — *Science Advances*, 2023; open preprint [arXiv:2303.01394](https://arxiv.org/abs/2303.01394)): racemic RNA precursor reaches full single-handedness on a magnetic surface via symmetry breaking + self-amplification.
- [Chirality-Induced Avalanche Magnetization of Magnetite by an RNA Precursor](https://arxiv.org/abs/2304.09095) (Ozturk et al. — *Nature Communications*, 2023): the feedback loop that makes the broken hand spread and lock persistently.
- [The central dogma of biological homochirality: how does chiral information propagate in a prebiotic network?](https://pmc.ncbi.nlm.nih.gov/articles/PMC7615580/) (Ozturk, Sasselov, Sutherland — *J. Chem. Phys.*, 2023): chirality treated as one-way *information*, à la Crick's central dogma.
- "On the origins of life's homochirality: inducing enantiomeric excess with spin-polarized electrons" (Ozturk & Sasselov — *PNAS*, 2022) and [Life's homochirality across a prebiotic network](https://www.pnas.org/doi/10.1073/pnas.2505126122) (*PNAS*, 2025): the spin-selectivity basis and network-level robustness. Full list on the author's [publications page](https://sukrufurkanozturk.owlstown.net/projects).
- [Autopoiesis and Cognition](https://en.wikipedia.org/wiki/Autopoiesis) (Maturana & Varela, 1980) and Prof. Dr. Türker Kılıç's network-science ("bağlantısallık") framing: orientation for treating *thought* as life's information process folded back on itself — the second tier in the chirality-and-mind design.

## Related writing

- [Evoverse: Not Creating a World, but Witnessing One](https://medium.com/@eresicibora/evoverse-bir-d%C3%BCnyay%C4%B1-yaratmak-de%C4%9Fil-ona-tan%C4%B1kl%C4%B1k-etmek-b7be7bcf5f30): Essay by Bora ERESICI on Evoverse's observe-don't-command stance.
- [God at the Interface: An Essay on Being, Nothingness, and the Evolutionary, Philological, and Cognitive Origins of Belief](https://medium.com/@eresicibora/aray%C3%BCzdeki-tanr%C4%B1-varl%C4%B1k-hi%C3%A7lik-ve-inanc%C4%B1n-evrimsel-filolojik-ve-bili%C5%9Fsel-k%C3%B6kenleri-%C3%BCzerine-bir-7c1ace03adea): Essay by Bora ERESICI that references Evoverse.
