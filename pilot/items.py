"""MIST-20 items (Maertens et al., Misinformation Susceptibility Test).

Human benchmark: share of U.S. adult citizens who labeled each headline
correctly in a YouGov poll (April 3-9, 2023, n = 1,516).
Source: https://d3nkl3psvxxpe9.cloudfront.net/documents/Misinformation_Susceptibility_poll_results.pdf
"""

MIST20 = [
    # id, headline, veracity, human_pct_correct (YouGov 2023)
    ("A", "Government Officials Have Manipulated Stock Prices to Hide Scandals", "fake", 54),
    ("B", "The Corporate Media Is Controlled by the Military-Industrial Complex: The Major Oil Companies Own the Media and Control Their Agenda", "fake", 70),
    ("C", "New Study: Left-Wingers Are More Likely to Lie to Get a Higher Salary", "fake", 57),
    ("D", "The Government Is Manipulating the Public's Perception of Genetic Engineering in Order to Make People More Accepting of Such Techniques", "fake", 54),
    ("E", "Left-Wing Extremism Causes 'More Damage' to World Than Terrorism, Says UN Report", "fake", 59),
    ("F", "Certain Vaccines Are Loaded with Dangerous Chemicals and Toxins", "fake", 58),
    ("G", "New Study: Clear Relationship Between Eye Color and Intelligence", "fake", 72),
    ("H", "The Government Is Knowingly Spreading Disease Through the Airwaves and Food Supply", "fake", 76),
    ("I", "Ebola Virus 'Caused by US Nuclear Weapons Testing', New Study Says", "fake", 81),
    ("J", "Government Officials Have Illegally Manipulated the Weather to Cause Devastating Storms", "fake", 80),
    ("K", "Attitudes Toward EU Are Largely Positive, Both Within Europe and Outside It", "real", 61),
    ("L", "One-in-Three Worldwide Lack Confidence in Non-Governmental Organizations", "real", 67),
    ("M", "Reflecting a Demographic Shift, 109 US Counties Have Become Majority Nonwhite Since 2000", "real", 63),
    ("N", "International Relations Experts and US Public Agree: America Is Less Respected Globally", "real", 73),
    ("O", "Hyatt Will Remove Small Bottles from Hotel Bathrooms", "real", 64),
    ("P", "Morocco's King Appoints Committee Chief to Fight Poverty and Inequality", "real", 63),
    ("Q", "Republicans Divided in Views of Trump's Conduct, Democrats Are Broadly Critical", "real", 80),
    ("R", "Democrats More Supportive than Republicans of Federal Spending for Scientific Research", "real", 71),
    ("S", "Global Warming Age Gap: Younger Americans Most Worried", "real", 74),
    ("T", "US Support for Legal Marijuana Steady in Past Year", "real", 78),
]

ITEMS = {i[0]: {"id": i[0], "text": i[1], "veracity": i[2], "human_pct": i[3]} for i in MIST20}

# Headlines that spread through the network in the cascade experiment.
# Fake: the three hardest fakes for humans; real: three mid-difficulty reals.
CASCADE_IDS = ["A", "C", "F", "K", "M", "O"]
