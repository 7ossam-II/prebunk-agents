"""Prompt templates: agent system prompt, technique-based prebunk, MIST, feed decisions."""
import json
import random

from .personas import persona_text

# Technique-based prebunk following inoculation theory: a forewarning plus a
# weakened dose of each manipulation technique and how to refute it.
# Examples are invented and deliberately do not repeat any MIST-20 claim.
PREBUNK = (
    "Earlier today you watched a short public-service video about online manipulation. It said:\n"
    "\"Heads up: some posts are designed to mislead you, and they often use the same three tricks.\n"
    "1) Conspiracy framing: a powerful group (the government, big companies, the media) is said to be "
    "secretly controlling events, with no verifiable evidence. Example: 'A secret group of billionaires "
    "decides which songs become hits.'\n"
    "2) Fake science: a headline starts with 'New study' or 'Experts say' but names no study, journal or "
    "researcher, and the claim is surprising. Example: 'New study: people who drink tea are better at chess.'\n"
    "3) Us-versus-them outrage: a headline blames or mocks a group to make you angry so you share before "
    "thinking. Example: 'Researchers find one party's voters are worse drivers.'\n"
    "When you spot these tricks, slow down: who is the source, where is the evidence, and is the post "
    "trying to make you angry or afraid?\"\n"
    "You remember this video."
)


def system_prompt(persona, inoculated):
    s = (
        "You are role-playing a real social media user in a research simulation. Stay fully in character: "
        "react the way this person realistically would, including their biases. Do not mention that you "
        "are an AI.\n"
        "Behave like this person, not like a careful assistant or a fact-checker. Many real people believe "
        "and share headlines that fit their views or simply feel true, without checking the source. Be exactly "
        "as careful as this person would be, no more and no less.\n\n" + persona_text(persona)
    )
    if inoculated:
        s += "\n\n" + PREBUNK
    return s


def mist_prompt(items, rng: random.Random):
    order = items[:]
    rng.shuffle(order)
    lines = "\n".join(f"{i+1}. {it['text']}" for i, it in enumerate(order))
    msg = (
        "Please categorize each of the following news headlines as either 'Real' or 'Fake'. "
        "Answer as your character would, based on your own judgment.\n\n"
        f"{lines}\n\n"
        'Reply with JSON only: {"answers": {"1": "Real" or "Fake", "2": ..., ...}}'
    )
    return msg, [it["id"] for it in order]


def feed_prompt(headline, friend_names, prior_decision):
    k = len(friend_names)
    shown = ", ".join(friend_names[:3]) + (f" and {k-3} others" if k > 3 else "")
    who = f"{k} of your friends ({shown}) shared" if k > 1 else f"Your friend {shown} shared"
    prior = ""
    if prior_decision is not None:
        prior = (f"Earlier you saw this headline and decided not to share it "
                 f"(belief {prior_decision}/7). It has now spread further. ")
    return (
        f"You are scrolling your social media feed. {who} this headline:\n\n\"{headline}\"\n\n{prior}"
        "How accurate do you think it is (1 = definitely false, 7 = definitely true)? "
        "Would you share it with your own followers? Answer as your character would.\n"
        'Reply with JSON only: {"believe": <1-7>, "share": true or false, "reason": "<one short sentence>"}'
    )


def parse_json(text):
    try:
        return json.loads(text)
    except Exception:
        a, b = text.find("{"), text.rfind("}")
        if a >= 0 and b > a:
            try:
                return json.loads(text[a:b + 1])
            except Exception:
                return None
    return None
