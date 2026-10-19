# Pilot results: pilot

Model deepseek-flash | 100 agents | 3 networks | 8 rounds | 30% prebunked | 2946 API calls, 0 failures

## 1. Final reach (share of all agents who shared the headline)

| headlines   | condition                         |   final_reach_pct |   ci95 |   n_cascades |   change_vs_control_pct |
|:------------|:----------------------------------|------------------:|-------:|-------------:|------------------------:|
| fake        | No prebunking                     |              22   |    6.4 |            9 |                     nan |
| fake        | 30% random users prebunked        |              13   |    6.2 |            9 |                     -41 |
| fake        | 30% hubs prebunked                |               9.1 |    4.3 |            9 |                     -59 |
| fake        | 30% hubs prebunked late (round 3) |              16.3 |    6.2 |            9 |                     -26 |
| real        | No prebunking                     |               3.9 |    1.2 |            9 |                     nan |
| real        | 30% random users prebunked        |               3.4 |    0.8 |            9 |                     -11 |
| real        | 30% hubs prebunked                |               4.3 |    1.7 |            9 |                      11 |
| real        | 30% hubs prebunked late (round 3) |               3.9 |    1.3 |            9 |                       0 |

## 2. Paired tests, false headlines (same network, seeds and headline in every condition)

| comparison                                              |   diff_pts | ci95          | lower_in   |   wilcoxon_p |
|:--------------------------------------------------------|-----------:|:--------------|:-----------|-------------:|
| 30% random users prebunked vs no prebunking             |       -9   | [-16.1, -1.9] | 7/9        |       0.039  |
| 30% hubs prebunked vs no prebunking                     |      -12.9 | [-19.8, -6.0] | 8/9        |       0.0078 |
| 30% hubs prebunked late (round 3) vs no prebunking      |       -5.7 | [-10.1, -1.2] | 8/9        |       0.0078 |
| 30% hubs prebunked vs 30% random users prebunked        |       -3.9 | [-7.4, -0.4]  | 5/9        |       0.062  |
| 30% hubs prebunked late (round 3) vs 30% hubs prebunked |        7.2 | [+1.4, +13.1] | 0/9        |       0.016  |

## 3. Indirect protection: agents who were never prebunked and did not seed the rumor

|                                   |   saw_it_pct |   ci95 |   shared_it_pct |
|:----------------------------------|-------------:|-------:|----------------:|
| No prebunking                     |         70.2 |   18.5 |            19.6 |
| 30% random users prebunked        |         46.3 |   22.8 |            12.1 |
| 30% hubs prebunked                |         29   |   17.8 |             5.1 |
| 30% hubs prebunked late (round 3) |         53.2 |   22.6 |             9.6 |

## 4. Direct effect: share rate once exposed (false headlines)

| agents                         |   share_rate_pct |   mean_belief |   decisions |
|:-------------------------------|-----------------:|--------------:|------------:|
| Not prebunked (all conditions) |             18.8 |          3.44 |        2037 |
| Prebunked (active)             |             10.4 |          3.27 |         520 |

## 5. Knowing vs doing, by conspiracy mentality (no-prebunking condition)

| conspiracy   |   called_fake_on_MIST_pct |   shared_in_feed_pct |   feed_decisions |
|:-------------|--------------------------:|---------------------:|-----------------:|
| low          |                      99.5 |                  3.2 |              377 |
| moderate     |                      97.1 |                 20.2 |              322 |
| high         |                      90   |                 57   |              165 |

Other traits (share rate when exposed):

| thinking                         |   share_rate |   belief |   n |
|:---------------------------------|-------------:|---------:|----:|
| sometimes stop to think          |         0.28 |     3.78 | 265 |
| usually go with your gut         |         0.21 |     3.61 | 303 |
| usually stop and think carefully |         0.11 |     3.19 | 296 |

| sharing                                           |   share_rate |   belief |   n |
|:--------------------------------------------------|-------------:|---------:|----:|
| often share headlines without reading the article |         0.19 |     3.23 | 185 |
| rarely share news posts                           |         0    |     3.4  | 280 |
| sometimes share headlines that grab you           |         0.34 |     3.74 | 399 |

## 6. MIST-20: agents vs humans

Fake headlines spotted: humans 66.1%, agents 96.3%, agents after prebunk 100.0%
Real headlines accepted: humans 69.4%, agents 100.0%, agents after prebunk 100.0%
Item difficulty, agents vs humans: r = 0.49 (p = 0.029)
MIST score (leaving out the spreading item) vs sharing: point-biserial r = -0.37 (p = 1.6e-29, n = 864 decisions)
