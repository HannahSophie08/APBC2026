

Bot uses breadth-first search to find shortest path to gold pots.
Saves known tile positions across rounds to remember the map.
Picks the best gold pot when multiple are present (closest, breaking ties by gold amount).
Falls back to scored exploration when no path to gold exists, preferring unknown tiles and avoiding recently visited ones.
Avoids walls, mines, and other players when planning moves.

Hannah: initial BFS bot with map memory
Naja: improved exploration scoring and multi-gold-pot handling
Anna: bug fixes (mine and player collision avoidance)