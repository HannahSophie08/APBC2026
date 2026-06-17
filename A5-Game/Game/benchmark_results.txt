Benchmark results (QUICK_TEST=False)
N_GAMES_PER_MAP = 25, ROUNDS = 200
================================================================================

--- random ---
  v4        wins= 6 ( 24.0%)  mean= 590.6  median= 581.0  stdev=205.0  min= 224  max=1078
  v5        wins= 5 ( 20.0%)  mean= 539.3  median= 569.0  stdev=234.6  min=  99  max= 950
  v6        wins= 1 (  4.0%)  mean= 410.6  median= 467.0  stdev=154.7  min= 202  max= 731
  scout     wins=11 ( 44.0%)  mean= 644.0  median= 691.0  stdev=213.8  min= 213  max=1083
  beatme    wins= 2 (  8.0%)  mean= 490.8  median= 547.0  stdev=130.6  min= 269  max= 698

--- maze_map ---
  v4        wins= 9 ( 36.0%)  mean= 387.4  median= 355.0  stdev=140.1  min=  99  max= 581
  v5        wins= 4 ( 16.0%)  mean= 379.4  median= 348.0  stdev=124.3  min=  99  max= 629
  v6        wins= 5 ( 20.0%)  mean= 368.4  median= 328.0  stdev=161.6  min=  99  max= 798
  scout     wins= 2 (  8.0%)  mean= 305.8  median= 293.0  stdev=142.7  min=  99  max= 642
  beatme    wins= 5 ( 20.0%)  mean= 386.4  median= 381.0  stdev=120.4  min= 231  max= 744

--- floodfill_map ---
  v4        wins= 4 ( 16.0%)  mean= 617.3  median= 575.0  stdev=205.4  min= 342  max=1210
  v5        wins=11 ( 44.0%)  mean= 711.6  median= 738.0  stdev=179.6  min= 303  max=1043
  v6        wins= 2 (  8.0%)  mean= 500.5  median= 477.0  stdev=144.2  min= 231  max= 837
  scout     wins= 7 ( 28.0%)  mean= 706.0  median= 694.0  stdev=265.6  min= 295  max=1452
  beatme    wins= 1 (  4.0%)  mean= 502.0  median= 485.0  stdev=172.5  min= 134  max=1018

--- inverse_floodfill_map ---
  v4        wins= 2 (  8.0%)  mean= 491.6  median= 484.0  stdev=237.6  min=  99  max=1084
  v5        wins= 7 ( 28.0%)  mean= 574.8  median= 548.0  stdev=266.4  min=  99  max=1219
  v6        wins= 3 ( 12.0%)  mean= 481.9  median= 480.0  stdev=197.1  min=  99  max= 903
  scout     wins= 9 ( 36.0%)  mean= 560.6  median= 581.0  stdev=247.7  min=  99  max=1010
  beatme    wins= 4 ( 16.0%)  mean= 545.7  median= 552.0  stdev=134.9  min= 255  max= 821

--- random_coverage_map ---
  v4        wins= 4 ( 16.0%)  mean= 616.5  median= 596.0  stdev=248.8  min=  99  max=1072
  v5        wins= 8 ( 32.0%)  mean= 676.0  median= 697.0  stdev=248.2  min=  99  max=1096
  v6        wins= 2 (  8.0%)  mean= 551.1  median= 549.0  stdev=206.4  min= 222  max=1021
  scout     wins=10 ( 40.0%)  mean= 746.5  median= 774.0  stdev=222.3  min=  99  max=1069
  beatme    wins= 1 (  4.0%)  mean= 442.5  median= 457.0  stdev=164.2  min= 171  max= 846

--- mazes_and_caves ---
  v4        wins= 1 (  4.0%)  mean= 177.6  median=  99.0  stdev= 93.0  min=  99  max= 356
  v5        wins= 0 (  0.0%)  mean= 177.5  median= 197.0  stdev= 85.7  min=  99  max= 409
  v6        wins= 6 ( 24.0%)  mean= 214.2  median= 196.0  stdev=132.8  min=  99  max= 547
  scout     wins= 3 ( 12.0%)  mean= 178.0  median= 182.0  stdev= 95.8  min=  99  max= 400
  beatme    wins=15 ( 60.0%)  mean= 371.7  median= 379.0  stdev= 95.7  min= 275  max= 623

=== OVERALL (150 games) ===
  v4        wins= 26 ( 17.3%)  mean= 480.2  median= 463.5  stdev=249.6  min=  99  max=1210
  v5        wins= 35 ( 23.3%)  mean= 509.8  median= 486.5  stdev=269.8  min=  99  max=1219
  v6        wins= 19 ( 12.7%)  mean= 421.1  median= 446.5  stdev=198.9  min=  99  max=1021
  scout     wins= 42 ( 28.0%)  mean= 523.5  median= 498.0  stdev=293.1  min=  99  max=1452
  beatme    wins= 28 ( 18.7%)  mean= 456.5  median= 456.0  stdev=150.2  min= 134  max=1018

=== SCOUT representative games ===
  worst : gold=99, map=maze_map, seed=1065759580
  median: gold=502, map=floodfill_map, seed=1523830624
  best  : gold=1452, map=floodfill_map, seed=2864328291