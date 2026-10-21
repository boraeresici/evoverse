-- Refugium grace before extinction (recovery model, Layer C): a lineage at or
-- under the extinction floor is not declared extinct on the first tick it dips
-- there — it keeps being simulated for a grace window so a recovering habitat can
-- lift it back, and only a collapse that outlasts the grace (or a true zero) ends
-- it. This column counts the consecutive ticks a species has sat at/under the
-- floor; it resets on recovery and is cleared when the lineage is finalised
-- extinct. Extinction stays permanent — the grace only bounds when it is declared.
-- See app/domain/models.py Species and SpeciesStatusRules.relict_grace_ticks. As
-- with the transient decline high-water mark (015), this is current-state only;
-- historical frames need no grace timer, so no snapshot-table change is required.

ALTER TABLE species
  ADD COLUMN IF NOT EXISTS extinction_grace_ticks INTEGER NOT NULL DEFAULT 0;
