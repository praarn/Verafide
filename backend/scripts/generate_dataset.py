"""
generate_dataset.py
--------------------
Builds a labeled training corpus (data/train_data.csv) used to train the
bundled models. The corpus is synthetically composed from topic/entity pools
and two distinct writing styles (measured/attributed vs. sensational/
unverified), which is a well known technique for bootstrapping text
classifiers when a large licensed corpus isn't available in the build
environment.

IMPORTANT (read this before shipping to real production):
This generator gives the app a fully working, self-consistent model out of
the box. For a real deployment, swap this out for (or blend it with) a
large real-world labeled dataset such as WELFake, ISOT Fake News, or LIAR.
The training pipeline in train_models.py only needs a CSV with `text` and
`label` (1 = real, 0 = fake) columns, so you can drop in a different CSV
at data/train_data.csv and rerun `python scripts/train_models.py` without
touching any other code.
"""

import csv
import random

random.seed(42)

TOPICS = ["politics", "health", "technology", "science", "finance", "sports", "environment", "entertainment"]

ENTITIES = {
    "politics": ["the Senate Finance Committee", "the state legislature", "the mayor's office", "the Department of Labor", "the European Parliament", "the city council"],
    "health": ["the CDC", "Johns Hopkins researchers", "the World Health Organization", "a peer-reviewed study in The Lancet", "the FDA", "local hospital administrators"],
    "technology": ["engineers at the company", "the product team", "independent security researchers", "the standards committee", "the university's robotics lab", "the open-source maintainers"],
    "science": ["a team at the national observatory", "climate researchers", "the geological survey", "NASA's science directorate", "a university physics department", "marine biologists"],
    "finance": ["the central bank", "market analysts", "the treasury department", "the ratings agency", "the exchange's regulators", "the pension fund's trustees"],
    "sports": ["the league office", "the team's coaching staff", "the athletic commission", "tournament organizers", "the players' union", "the stadium authority"],
    "environment": ["state environmental regulators", "the forestry service", "conservation researchers", "the water management board", "the wildlife agency", "the coastal authority"],
    "entertainment": ["the studio's publicist", "festival organizers", "the awards committee", "the network", "the production company", "the artist's management"],
}

REAL_VERBS = ["announced", "confirmed", "reported", "released data showing", "clarified", "published findings indicating", "said in a statement", "outlined a plan to"]
REAL_HEDGES = ["according to figures released Tuesday", "based on a review of public records", "pending further review", "though final numbers have not been confirmed", "as part of a routine quarterly update", "following a months-long inquiry"]
REAL_SUBJECTS = {
    "politics": ["a proposed increase in the municipal budget", "changes to the local permitting process", "a new committee assignment", "revisions to the zoning code", "the timeline for the infrastructure bill"],
    "health": ["a modest decline in flu cases this season", "updated guidance on booster timing", "a new study on sleep and memory", "changes to hospital staffing ratios", "a trial testing a generic blood pressure drug"],
    "technology": ["a security patch for a widely used library", "quarterly earnings for the cloud division", "a delay in the chip's production timeline", "a new accessibility feature", "an update to the app's privacy settings"],
    "science": ["a newly catalogued asteroid", "a small increase in regional rainfall", "a fossil found during routine excavation", "a refinement to an existing climate model", "a new measurement of a distant galaxy's rotation"],
    "finance": ["a quarter-point change to the benchmark rate", "an upward revision to GDP estimates", "a routine audit of municipal bonds", "a modest rise in consumer confidence", "an update to lending standards"],
    "sports": ["a scheduling change for the playoffs", "a minor rule clarification", "a roster move ahead of the deadline", "the venue for next season's opener", "a review of instant-replay procedures"],
    "environment": ["a survey of local water quality", "a seasonal update on reservoir levels", "a new permit for a recycling facility", "a habitat restoration project's first-year results", "an update to the drought monitor"],
    "entertainment": ["the release date for a documentary", "a cast addition for the upcoming season", "ticket sales for the festival", "a schedule change for the ceremony", "a soundtrack credit correction"],
}

FAKE_OPENERS = [
    "You won't believe what", "SHOCKING: Insiders reveal", "BREAKING: Leaked documents show",
    "They don't want you to know that", "Doctors are FURIOUS after", "Secret memo exposes how",
    "What the mainstream media is HIDING:", "EXCLUSIVE: Whistleblower claims",
]
FAKE_CLAIMS = {
    "politics": ["a secret vote was held at midnight to strip citizens of basic rights", "officials are quietly funneling millions to an unnamed shell company", "a hidden clause will let the government seize private property overnight"],
    "health": ["a common vitamin cures the disease doctors don't want you curing", "hospitals are hiding a miracle treatment to protect profits", "a leaked lab report shows the vaccine contains untested nanoparticles"],
    "technology": ["your phone is secretly recording every word you say and selling it", "a hidden switch lets the company shut down your device remotely", "engineers discovered the app can control devices without permission"],
    "science": ["scientists secretly proved the theory is a complete hoax", "a suppressed study shows the phenomenon was faked in a lab", "leaked data reveals the entire field has been covering up the truth"],
    "finance": ["banks are secretly planning to freeze all accounts next week", "a hidden algorithm is rigging the market against ordinary investors", "insiders admit the currency will collapse within days"],
    "sports": ["the championship was secretly fixed by league executives", "a banned substance scandal is being covered up by officials", "players were secretly paid to throw the final match"],
    "environment": ["officials are hiding proof that the water supply is poisoned", "a leaked report shows the disaster was covered up for years", "secret documents reveal the company dumped toxic waste for decades"],
    "entertainment": ["a leaked contract proves the show was scripted from the start", "insiders reveal the star was secretly replaced months ago", "a hidden clause shows the award was bought, not earned"],
}
FAKE_TAGS = ["Share before this gets DELETED!!!", "The truth they buried for YEARS.", "Wake up, people!!!", "This changes EVERYTHING.", "Mainstream media refuses to cover this.", "Forward this to everyone you know."]

REAL_TEMPLATE = "{entity} {verb} {subject}, {hedge}. Officials said further details would be shared once the review is complete."
REAL_TEMPLATE2 = "In a statement, {entity} {verb} {subject}. The update, {hedge}, follows a routine internal process."

FAKE_TEMPLATE = "{opener} {claim}. {tag}"
FAKE_TEMPLATE2 = "{opener} {claim} — and {tag_lower}"


def make_real_row(topic):
    entity = random.choice(ENTITIES[topic])
    verb = random.choice(REAL_VERBS)
    subject = random.choice(REAL_SUBJECTS[topic])
    hedge = random.choice(REAL_HEDGES)
    template = random.choice([REAL_TEMPLATE, REAL_TEMPLATE2])
    return template.format(entity=entity, verb=verb, subject=subject, hedge=hedge)


def make_fake_row(topic):
    opener = random.choice(FAKE_OPENERS)
    claim = random.choice(FAKE_CLAIMS[topic])
    tag = random.choice(FAKE_TAGS)
    template = random.choice([FAKE_TEMPLATE, FAKE_TEMPLATE2])
    return template.format(opener=opener, claim=claim, tag=tag, tag_lower=tag.lower())


def build_dataset(rows_per_topic=190):
    rows = []
    for topic in TOPICS:
        seen = set()
        attempts = 0
        while len([r for r in rows if r[2] == topic and r[1] == 1]) < rows_per_topic and attempts < rows_per_topic * 10:
            text = make_real_row(topic)
            attempts += 1
            if text in seen:
                continue
            seen.add(text)
            rows.append((text, 1, topic))
        seen = set()
        attempts = 0
        while len([r for r in rows if r[2] == topic and r[1] == 0]) < rows_per_topic and attempts < rows_per_topic * 10:
            text = make_fake_row(topic)
            attempts += 1
            if text in seen:
                continue
            seen.add(text)
            rows.append((text, 0, topic))
    random.shuffle(rows)
    return rows


def main():
    rows = build_dataset()
    out_path = "data/train_data_synthetic.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["text", "label", "topic"])
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {out_path}")


if __name__ == "__main__":
    main()
