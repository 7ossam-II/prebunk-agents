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

Mean belief (1-7), all feed decisions: true headlines 5.2, false headlines 3.4

## 2. Paired tests, false headlines (same network, seeds and headline in every condition)

hl_diff_pts: Hodges-Lehmann estimate of the paired difference, in percentage points. ci95_boot: paired bootstrap 95% CI (10,000 resamples of the 9 cascades). n_eff: cascades with a nonzero difference (the Wilcoxon test drops ties). holm_p: Holm-adjusted across the 5 tests. by_network: difference of the means over the 3 headlines of each network, a direction check only.

| comparison                                              |   hl_diff_pts | ci95_boot     | lower_in   |   n_eff |   wilcoxon_p |   holm_p | by_network         | networks_lower   |
|:--------------------------------------------------------|--------------:|:--------------|:-----------|--------:|-------------:|---------:|:-------------------|:-----------------|
| 30% random users prebunked vs no prebunking             |          -9   | [-15.0, -1.5] | 7/9        |       8 |       0.039  |    0.078 | -17.0, -4.0, -6.0  | 3/3              |
| 30% hubs prebunked vs no prebunking                     |         -12.5 | [-20.0, -7.0] | 8/9        |       8 |       0.0078 |    0.039 | -21.7, -4.7, -12.3 | 3/3              |
| 30% hubs prebunked late (round 3) vs no prebunking      |          -5   | [-10.0, -2.0] | 8/9        |       8 |       0.0078 |    0.039 | -4.7, -2.0, -10.3  | 3/3              |
| 30% hubs prebunked vs 30% random users prebunked        |          -3.5 | [-7.0, +0.0]  | 5/9        |       5 |       0.062  |    0.078 | -4.7, -0.7, -6.3   | 3/3              |
| 30% hubs prebunked late (round 3) vs 30% hubs prebunked |           8   | [+1.0, +11.5] | 0/9        |       7 |       0.016  |    0.047 | +17.0, +2.7, +2.0  | 0/3              |

Never spread beyond its 3 seed users in any condition, so a zero difference in every comparison: rep 1, headline F.

## 3. Indirect protection: agents who were never prebunked and did not seed the rumor

|                                   |   saw_it_pct |   ci95 |   shared_it_pct |
|:----------------------------------|-------------:|-------:|----------------:|
| No prebunking                     |         70.2 |   18.5 |            19.6 |
| 30% random users prebunked        |         46.3 |   22.8 |            12.1 |
| 30% hubs prebunked                |         29   |   17.8 |             5.1 |
| 30% hubs prebunked late (round 3) |         53.2 |   22.6 |             9.6 |

Paired tests on saw_it_pct (columns as in section 2; Holm-adjusted across these 3 tests):

| comparison                                         |   hl_diff_pts | ci95_boot      | lower_in   |   n_eff |   wilcoxon_p |   holm_p | by_network          | networks_lower   |
|:---------------------------------------------------|--------------:|:---------------|:-----------|--------:|-------------:|---------:|:--------------------|:-----------------|
| 30% hubs prebunked vs no prebunking                |         -42.4 | [-66.6, -16.8] | 9/9        |       9 |       0.0039 |    0.012 | -69.6, -13.8, -40.1 | 3/3              |
| 30% hubs prebunked late (round 3) vs no prebunking |         -10.5 | [-39.7, -6.7]  | 9/9        |       9 |       0.0039 |    0.012 | -10.4, -8.3, -32.2  | 3/3              |
| 30% random users prebunked vs no prebunking        |         -26   | [-42.9, -2.0]  | 7/9        |       9 |       0.055  |    0.055 | -46.3, -5.4, -20.2  | 3/3              |

Share rate once exposed, same agents in both conditions (false headlines; non-seed agents outside the 30% hub set of their network). share_rate_pct is per decision (an agent may reconsider up to 3 times); ever_shared_pct is per exposed agent and cascade.

|                    |   share_rate_pct |   decisions |   ever_shared_pct |   exposed |
|:-------------------|-----------------:|------------:|------------------:|----------:|
| No prebunking      |             16.4 |         525 |              21.8 |       394 |
| 30% hubs prebunked |             14.8 |         210 |              17.7 |       175 |

## 4. Direct effect: share rate once exposed (false headlines)

| agents                         |   share_rate_pct |   mean_belief |   decisions |
|:-------------------------------|-----------------:|--------------:|------------:|
| Not prebunked (all conditions) |             18.8 |          3.44 |        2037 |
| Prebunked (active)             |             10.4 |          3.27 |         520 |

Pooled decisions of different agents (81% of the prebunked decisions are by hubs), so descriptive only.

## 5. Knowing vs doing, by conspiracy mentality (no-prebunking condition)

| conspiracy   |   called_fake_on_MIST_pct |   shared_in_feed_pct |   feed_decisions |
|:-------------|--------------------------:|---------------------:|-----------------:|
| low          |                      99.5 |                  3.2 |              377 |
| moderate     |                      97.1 |                 20.2 |              322 |
| high         |                      90   |                 57   |              165 |

All agents: 19.8% of 864 decisions shared the false headline.

Agents with a perfect 20/20 MIST-20 score only:

| conspiracy   |   agents |   called_fake_on_MIST_pct |   shared_in_feed_pct |   feed_decisions |   agents_shared_at_least_once |
|:-------------|---------:|--------------------------:|---------------------:|-----------------:|------------------------------:|
| low          |       38 |                       100 |                  3.4 |              356 |                             6 |
| moderate     |       29 |                       100 |                 14.5 |              289 |                            12 |
| high         |       17 |                       100 |                 47.5 |              120 |                            11 |

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

## 7. Does the MIST score predict sharing? (no-prebunking condition, false headlines)

MIST score leaves out the spreading headline. 864 decisions from 99 agents, analysed with agents as clusters. GEE logistic regression, exchangeable working correlation; odds ratio per MIST point:

| model                             |   odds_ratio_per_point | ci95         |      p |
|:----------------------------------|-----------------------:|:-------------|-------:|
| MIST score                        |                   0.47 | [0.29, 0.76] | 0.0022 |
| MIST score + conspiracy mentality |                   0.5  | [0.26, 0.99] | 0.045  |

Agent-level Spearman rho = -0.48 (p = 6e-07, n = 99 agents; share rate vs mean MIST score)
Decision-level point-biserial r = -0.37, cluster bootstrap 95% CI [-0.50, -0.23] (10,000 resamples of agents)
85 of 100 agents scored 20/20, so the link rests on the 15 agents in this analysis who did not (2 low, 5 moderate, 8 high conspiracy mentality).

## 8. Caveats

- The 9 cascades are not independent: they come from 3 networks, and the 3 headlines on one network share its agents and graph. The cascade-level tests treat them as independent. 3 networks are too few for a network-level test, so by_network is a direction check only.
- Holm adjustment is within each family (the reach tests in section 2, the indirect-protection tests in section 3), not across the whole report.
