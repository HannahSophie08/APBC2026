Benchmark results (QUICK_TEST=False)
N_GAMES_PER_MAP = 25, ROUNDS = 1000
================================================================================

--- random ---
  v5        wins= 1 (  4.0%)  mean=1563.8  median=1489.0  stdev=432.4  min= 871  max=2549
  v5.2      wins= 0 (  0.0%)  mean= 886.9  median= 838.0  stdev=327.3  min= 308  max=1791
  v5new     wins= 0 (  0.0%)  mean= 826.5  median= 749.0  stdev=300.6  min= 421  max=1478
  botHannah  wins=10 ( 40.0%)  mean=3727.0  median=1030.0  stdev=4367.0  min=   0  max=10761
  group2    wins=14 ( 56.0%)  mean=3076.6  median=1950.0  stdev=3206.3  min=   5  max=9160

--- maze_map ---
  v5        wins= 0 (  0.0%)  mean=1078.6  median=1044.0  stdev=378.3  min= 495  max=2132
  v5.2      wins= 1 (  4.0%)  mean=1806.6  median=1772.0  stdev=372.0  min=1331  max=2602
  v5new     wins= 5 ( 20.0%)  mean=1871.4  median=1770.0  stdev=380.3  min=1167  max=2703
  botHannah  wins= 0 (  0.0%)  mean=  60.9  median=  31.0  stdev= 75.7  min=   0  max= 268
  group2    wins=19 ( 76.0%)  mean=2740.3  median=2671.0  stdev=817.2  min=1640  max=5018

--- floodfill_map ---
  v5        wins= 0 (  0.0%)  mean=1088.2  median=1098.0  stdev=312.6  min= 448  max=1641
  v5.2      wins= 0 (  0.0%)  mean= 416.2  median= 353.0  stdev=176.5  min= 212  max= 892
  v5new     wins= 0 (  0.0%)  mean= 376.0  median= 278.0  stdev=198.4  min= 214  max= 892
  botHannah  wins=24 ( 96.0%)  mean=7550.8  median=6624.0  stdev=3967.9  min=2307  max=12559
  group2    wins= 1 (  4.0%)  mean= 752.0  median=   9.0  stdev=1011.4  min=   0  max=3129

--- inverse_floodfill_map ---
  v5        wins= 1 (  4.0%)  mean=2151.8  median=2051.0  stdev=605.5  min=1416  max=3377
  v5.2      wins= 1 (  4.0%)  mean=1866.6  median=1750.0  stdev=435.4  min=1038  max=2549
  v5new     wins= 1 (  4.0%)  mean=1843.0  median=1836.0  stdev=459.9  min=1044  max=2855
  botHannah  wins= 0 (  0.0%)  mean= 178.4  median=  31.0  stdev=466.7  min=   0  max=2259
  group2    wins=22 ( 88.0%)  mean=4075.4  median=4241.0  stdev=1449.7  min= 375  max=7034

--- random_coverage_map ---
  v5        wins= 0 (  0.0%)  mean=1136.9  median=1097.0  stdev=472.7  min= 364  max=2689
  v5.2      wins= 0 (  0.0%)  mean= 523.2  median= 489.0  stdev=193.6  min= 264  max= 972
  v5new     wins= 0 (  0.0%)  mean= 454.2  median= 435.0  stdev=165.4  min= 277  max= 911
  botHannah  wins=21 ( 84.0%)  mean=5154.2  median=3463.0  stdev=3696.6  min= 889  max=12427
  group2    wins= 4 ( 16.0%)  mean=1511.8  median=1630.0  stdev=1308.9  min=   2  max=4694

--- mazes_and_caves ---
  v5        wins= 0 (  0.0%)  mean= 475.5  median= 474.0  stdev=254.0  min=  99  max=1339
  v5.2      wins= 0 (  0.0%)  mean=1192.8  median=1148.0  stdev=175.9  min= 912  max=1642
  v5new     wins= 3 ( 12.0%)  mean=1343.4  median=1330.0  stdev=183.9  min=1025  max=1904
  botHannah  wins= 0 (  0.0%)  mean=   7.0  median=   3.0  stdev= 11.5  min=   0  max=  44
  group2    wins=22 ( 88.0%)  mean=2892.0  median=2771.0  stdev=1052.6  min=1066  max=6164

=== OVERALL (150 games) ===
  v5        wins=  2 (  1.3%)  mean=1249.2  median=1184.0  stdev=662.9  min=  99  max=3377
  v5.2      wins=  2 (  1.3%)  mean=1115.4  median=1085.0  stdev=641.6  min= 212  max=2602
  v5new     wins=  9 (  6.0%)  mean=1119.1  median=1172.0  stdev=678.7  min= 214  max=2855
  botHannah  wins= 55 ( 36.7%)  mean=2779.7  median= 198.5  stdev=4052.9  min=   0  max=12559
  group2    wins= 82 ( 54.7%)  mean=2508.0  median=2440.5  stdev=1976.2  min=   0  max=9160

=== SCOUT representative games ===
  worst : gold=214, map=floodfill_map, seed=4053037482
  median: gold=1176, map=inverse_floodfill_map, seed=1204641400
  best  : gold=2855, map=inverse_floodfill_map, seed=1158868681


The results show that our old versions as well as my new versions dont perform good at all, Hannahs bot is strong when group 2 bot is weak which is a good approach as we wont be able to beat them in their good maps probably 

Improvement therefore should be made on Hannahs version focussing on the weaknesses of group 2 for example