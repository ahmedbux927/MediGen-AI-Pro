-- Stage 4 (Master Prompt v4): sell by pack as well as by unit.
-- units_per_pack = how many single units are in one pack/strip (e.g. 10).
-- NULL means the item is sold by unit only. Stock and prices stay per unit;
-- the counter screen converts packs to units when the bill is made.
ALTER TABLE medicines ADD COLUMN units_per_pack INT NULL;
