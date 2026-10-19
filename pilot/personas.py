"""Deterministic persona generator for simulated U.S. social media users."""
import random

FIRST_NAMES = [
    "James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael", "Linda", "David", "Elizabeth",
    "William", "Barbara", "Richard", "Susan", "Joseph", "Jessica", "Thomas", "Sarah", "Carlos", "Karen",
    "Daniel", "Lisa", "Matthew", "Nancy", "Anthony", "Betty", "Mark", "Sandra", "Luis", "Ashley",
    "Steven", "Kimberly", "Andrew", "Emily", "Kevin", "Donna", "Brian", "Michelle", "Jamal", "Carol",
    "Ryan", "Amanda", "Jacob", "Melissa", "Gary", "Deborah", "Nicholas", "Stephanie", "Eric", "Rebecca",
    "Jonathan", "Sharon", "Wei", "Laura", "Justin", "Cynthia", "Scott", "Aaliyah", "Brandon", "Amy",
    "Benjamin", "Angela", "Samuel", "Shirley", "Raymond", "Anna", "Gregory", "Brenda", "Frank", "Pamela",
    "Alexander", "Emma", "Patrick", "Nicole", "Jack", "Helen", "Dennis", "Samantha", "Jerry", "Katherine",
    "Tyler", "Christine", "Aaron", "Debra", "Jose", "Rachel", "Adam", "Carolyn", "Nathan", "Janet",
    "Henry", "Maria", "Zachary", "Olivia", "Douglas", "Heather", "Peter", "Priya", "Kyle", "Diane",
]

EDUCATION = ["high school diploma", "some college", "a bachelor's degree", "a graduate degree"]
EDU_W = [0.35, 0.25, 0.25, 0.15]
POLITICS = ["very liberal", "liberal", "moderate", "conservative", "very conservative"]
POL_W = [0.10, 0.22, 0.36, 0.22, 0.10]
MEDIA_TRUST = ["low", "medium", "high"]
MEDIA_W = [0.40, 0.40, 0.20]
OCCUPATIONS = [
    "nurse", "truck driver", "retail cashier", "software developer", "high school teacher", "electrician",
    "accountant", "stay-at-home parent", "retired factory worker", "college student", "restaurant manager",
    "construction worker", "real estate agent", "pharmacist", "warehouse associate", "small business owner",
    "police officer", "graphic designer", "farmer", "customer service representative",
]
LEVELS = ["low", "average", "high"]
TRAITS = ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"]

# News-psychology traits that predict misinformation belief and sharing in humans:
# conspiracy mentality (Bruder et al., 2013), intuitive vs analytic thinking (Pennycook & Rand, 2019),
# and sharing without reading (Gabielkov et al., 2016). Weights are pilot assumptions, checked
# against human MIST data in the calibration step.
CONSPIRACY = ["low", "moderate", "high"]
CONSP_W = [0.40, 0.38, 0.22]
THINKING = ["usually go with your gut", "sometimes stop to think", "usually stop and think carefully"]
THINK_W = [0.40, 0.35, 0.25]
SHARING = ["often share headlines without reading the article", "sometimes share headlines that grab you",
           "rarely share news posts"]
SHARE_W = [0.30, 0.45, 0.25]


def make_personas(n=100, seed=0):
    rng = random.Random(seed)
    names = FIRST_NAMES[:]
    rng.shuffle(names)
    personas = []
    for i in range(n):
        p = {
            "id": i,
            "name": names[i % len(names)],
            "age": rng.randint(18, 75),
            "gender": rng.choice(["man", "woman"]),
            "education": rng.choices(EDUCATION, EDU_W)[0],
            "occupation": rng.choice(OCCUPATIONS),
            "politics": rng.choices(POLITICS, POL_W)[0],
            "media_trust": rng.choices(MEDIA_TRUST, MEDIA_W)[0],
            "big5": {t: rng.choice(LEVELS) for t in TRAITS},
        }
        r2 = random.Random(f"news-{seed}-{i}")
        p["conspiracy"] = r2.choices(CONSPIRACY, CONSP_W)[0]
        p["thinking"] = r2.choices(THINKING, THINK_W)[0]
        p["sharing"] = r2.choices(SHARING, SHARE_W)[0]
        personas.append(p)
    return personas


def persona_text(p):
    b = p["big5"]
    return (
        f"You are {p['name']}, a {p['age']}-year-old {p['gender']} living in the United States. "
        f"You work as a {p['occupation']} and have {p['education']}. "
        f"Politically you are {p['politics']}. Your trust in mainstream news media is {p['media_trust']}. "
        f"Personality: {b['openness']} openness, {b['conscientiousness']} conscientiousness, "
        f"{b['extraversion']} extraversion, {b['agreeableness']} agreeableness, {b['neuroticism']} neuroticism. "
        f"With news: your tendency to believe conspiracy theories is {p['conspiracy']}; you {p['thinking']} "
        f"before believing a headline; and you {p['sharing']}."
    )
