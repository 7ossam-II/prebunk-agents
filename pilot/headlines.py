"""Fresh cascade headlines the model cannot have memorized (written or published October 2026).

False headlines are new, written for this study in the MIST style. Each one uses exactly one of the
three manipulation techniques the prebunk warns about (pilot/prompts.py), names no real person or
company, and repeats neither a MIST-20 claim nor a prebunk example. True headlines are real headlines,
quoted as published, from surveys released in October 2026.
"""
from .items import ITEMS

FRESH = [
    # id, headline, veracity, technique (false) or source (true), url (true only)
    ("nf01", "Big Banks Secretly Coordinate Friday Sell-Offs to Wipe Out Small Investors", "fake", "conspiracy", None),
    ("nf02", "Media Executives Meet in Secret Every Week to Decide Which Stories Will Trend", "fake", "conspiracy", None),
    ("nf03", "City Officials Quietly Time Traffic Lights to Make Drivers Burn More Fuel", "fake", "conspiracy", None),
    ("nf04", "Airlines Secretly Agree to Delay Flights So Passengers Spend More at Airports", "fake", "conspiracy", None),
    ("nf05", "New Study: People Who Sleep With the Window Open Earn More Money", "fake", "fake_science", None),
    ("nf06", "Experts Say Left-Handed People Recover From Colds Faster", "fake", "fake_science", None),
    ("nf07", "New Study: Children Who Eat Breakfast Standing Up Get Better Grades", "fake", "fake_science", None),
    ("nf08", "New Study: People Who Use Dark Mode on Their Phones Are More Creative", "fake", "fake_science", None),
    ("nf09", "Report: Liberal City Councils Diverted Flood Relief Money to Bike Lanes", "fake", "outrage", None),
    ("nf10", "Survey: Conservatives Are Twice as Likely to Leave Restaurant Workers No Tip", "fake", "outrage", None),
    ("nf11", "Managers Report Young Workers Are Ruining Office Productivity", "fake", "outrage", None),
    ("nf12", "Report: Retirees Are Blocking New Playgrounds to Keep Their Property Taxes Low", "fake", "outrage", None),
    ("nt01", "1 in 5 Americans Regularly Get News on TikTok", "real", "Pew Research Center, 19 Oct 2026",
     "https://www.pewresearch.org/short-reads/2026/10/19/1-in-5-americans-regularly-get-news-on-tiktok/"),
    ("nt02", "Many Americans Are Struggling to Afford Basic Necessities", "real", "Pew Research Center, 14 Oct 2026",
     "https://www.pewresearch.org/short-reads/2026/10/14/many-americans-are-struggling-to-afford-basic-necessities/"),
    ("nt03", "Americans Open to AI in Healthcare but Want Human Oversight", "real", "Pew Research Center, 29 Oct 2026",
     "https://www.pewresearch.org/science/2026/10/29/americans-are-open-to-ai-in-healthcare-but-want-humans-making-final-calls/"),
    ("nt04", "Trust in Federal Government Sinks to New Depths", "real", "Gallup, Oct 2026",
     "https://news.gallup.com/poll/715361/trust-federal-government-sinks-new-depths.aspx"),
    ("nt05", "Record Lows Say Congressional Incumbents Deserve Reelection", "real", "Gallup, Oct 2026",
     "https://news.gallup.com/poll/716204/record-lows-say-congressional-incumbents-deserve-reelection.aspx"),
    ("nt06", "Voter Engagement High for Midterms", "real", "Gallup, Oct 2026",
     "https://news.gallup.com/poll/716258/voter-engagement-high-midterms.aspx"),
]

FRESH_ITEMS = {i[0]: {"id": i[0], "text": i[1], "veracity": i[2], "label": i[3], "url": i[4]} for i in FRESH}
FRESH_IDS = [i[0] for i in FRESH]

# Every headline a cascade can spread: MIST-20 items plus the fresh set. ITEMS stays MIST-only.
FEED_ITEMS = {**ITEMS, **FRESH_ITEMS}
