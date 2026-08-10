"""
Builds data/real_world_pilot_batch.json: hand-labeled rows whose input_query
text is grounded in real, public statements (earnings call transcripts,
shareholder letters) rather than LLM-invented sentences -- see chat history /
PR description for why. Every row's source_text values are verified to be
exact substrings of input_query by validate_real_world_pilot.py.

Each row carries "_source_url" and "_source_note" (underscore-prefixed,
ignored by train_crf.py / build_seq2seq_pairs.py) for provenance so every
row can be traced back to the real quote it's grounded in.
"""

import json

ROLES = ["actor", "object", "intent", "scope", "measure",
         "magnitude", "time", "constraints", "context"]


def field(value=None, status="missing", confidence=0.0, source_text=None):
    return {"value": value, "status": status, "confidence": confidence, "source_text": source_text}


def row(id_, query, url, note, **roles):
    choice = {r: field() for r in ROLES}
    choice.update(roles)
    return {
        "id": id_,
        "input_query": query,
        "choice": choice,
        "objective_status": "sufficient",
        "required_followups": [],
        "_source_url": url,
        "_source_note": note,
    }


TARGET_URL = "https://www.fool.com/earnings/call-transcripts/2026/05/20/target-tgt-q1-2026-earnings-call-transcript/"
PNC_URL = "https://www.fool.com/earnings/call-transcripts/2026/07/22/pnc-pnc-q2-2026-earnings-call-transcript/"
FIS_URL = "https://www.fool.com/earnings/call-transcripts/2026/06/01/fis-q1-2026-earnings-call-transcript/"
FACTSET_URL = "https://www.fool.com/earnings/call-transcripts/2026/07/01/factset-fds-q3-2026-earnings-call-transcript/"
WFC_URL = "https://www.fool.com/earnings/call-transcripts/2026/07/21/wells-fargo-wfc-q2-2026-earnings-call-transcript/"
DHI_URL = "https://www.fool.com/earnings/call-transcripts/2026/07/22/dr-horton-dhi-q3-2026-earnings-call-transcript/"
CFG_URL = "https://www.fool.com/earnings/call-transcripts/2026/07/23/citizens-financial-cfg-q2-2026-earnings-call-transcript/"
BUFFER_URL = "https://buffer.com/shareholders/january-2025"

# 2026-08-05 sourcing pass: targeting Known gaps 0 (actor generic team/role
# phrasing), 1 (measure/scope/context thinness incl. causal/purpose clauses),
# and 2 (testing whether negation-cue constraint phrasing exists in real
# corporate language -- Trane's "without increasing costs" below is a real
# counter-example to the prior "found zero" finding).
INTUIT_URL = "https://www.fool.com/earnings/call-transcripts/2026/02/26/intuit-intu-q2-2026-earnings-call-transcript/"
ALBANY_URL = "https://www.fool.com/earnings/call-transcripts/2026/08/04/albany-international-ain-q2-2026-earnings-call-transcript/"
TRANE_URL = "https://www.fool.com/earnings/call-transcripts/2026/07/30/trane-technologies-tt-q2-2026-earnings-call-transcript/"

# 2026-08-05, second pass same session: rw_036 (Trane) was the only
# "without X" negation-cue constraint example in the whole dataset, and a
# live test proved one example teaches the CRF nothing -- a fresh novel
# query with the same pattern came back with constraints completely
# missing. This batch adds 4 more real "without X" examples across 4 more
# companies so the pattern has enough training signal to actually be
# learnable, plus one held-out eval example to test whether it worked.
# Also corrects Known gap 2's "found zero negation-cue phrasing in real
# corporate language" finding -- it exists, the first search just didn't
# find it.
FACTSET_Q1_URL = "https://www.fool.com/earnings/call-transcripts/2025/12/18/factset-fds-q1-2026-earnings-call-transcript/"
EFC_URL = "https://www.fool.com/earnings/call-transcripts/2026/05/06/efc-q1-2026-earnings-transcript/"
TESLA_URL = "https://www.fool.com/earnings/call-transcripts/2026/01/28/tesla-tsla-q4-2025-earnings-call-transcript/"
CLIMB_URL = "https://www.fool.com/earnings/call-transcripts/2026/04/30/climb-global-clmb-q1-2026-earnings-transcript/"

TMO_URL = "https://www.fool.com/earnings/call-transcripts/2026/07/23/tmo-q2-2026-earnings-call-transcript/"
AGCO_URL = "https://www.fool.com/earnings/call-transcripts/2026/08/03/agco-agco-q2-2026-earnings-call-transcript/"
SPGI_URL = "https://www.fool.com/earnings/call-transcripts/2026/04/28/sp-global-spgi-q1-2026-earnings-transcript/"
DXCM_URL = "https://www.fool.com/earnings/call-transcripts/2026/08/03/dexcom-dxcm-q2-2026-earnings-call-transcript/"

# 2026-08-09 sourcing pass: targeting Known gap 8 (T5 corrupts magnitude
# digits on 3-way joins -- e.g. "10.0%"->"100%" -- because
# data/seq2seq_pairs.jsonl had zero 3-way joined magnitude training pairs,
# only 2-way). This is a T5-layer gap, not a CRF/real-text gap, so one new
# real 3-way example (a new company, not rw_027's exact FactSet sentence,
# which is eval-locked) is enough to teach the pattern.
FFIV_URL = "https://www.fool.com/earnings/call-transcripts/2026/04/28/f5-ffiv-q2-2026-earnings-call-transcript/"

# 2026-08-10 sourcing pass: continuing Known gap 8. Re-running
# data/eval_on_real_world.py after fixing a real scoring bug (see
# eval_on_real_world.py's module docstring -- the old scorer marked a
# multi-value magnitude prediction fully correct if ANY single gold
# element substring-matched anywhere in the whole joined prediction
# string) revealed the round-5 fix from 2026-08-09 was narrower than it
# looked: T5 still corrupts decimal dollar-per-share amounts inside a
# joined magnitude, not just 3-way percentage joins -- direct
# pipe.synthesize() tests found "$0.50"->"$50" (rw_016, already in the
# frozen holdout, now correctly scored as wrong), "$0.75"->garbled
# "$100, $100,", "$1.25"->"$1,25". All 21 pre-existing 2-way-join
# training pairs use whole-dollar or $X.X0-and-up values (e.g. "$2 per
# share", "$700K", "$4.10") -- none exercise a sub-dollar decimal
# per-share amount, which is exactly rw_016's shape and exactly what's
# broken. 3 new real examples below target that gap specifically, each a
# different decimal-precision shape so one example doesn't just teach
# "$0.XX" as a memorized literal: single-digit cents + whole percent
# (Equinox Gold), two-digit cents + decimal percent (Alpine Income), and
# a >$1 decimal + an inexact "over X%" qualifier (Ares). All 3 go to
# training, not eval -- rw_016 (already frozen in the eval holdout) is
# the generalization test for whether this actually fixes the pattern,
# so no new eval row is needed for this specific gap.
EQX_URL = "https://ca.investing.com/news/transcripts/earnings-call-transcript-equinox-gold-rises-on-merger-higher-dividend-in-q2-2026-93CH-4783210"
PINE_URL = "https://www.investing.com/news/transcripts/earnings-call-transcript-alpine-income-beats-q2-2026-estimates-lifts-dividend-93CH-4812003"
ARES_URL = "https://www.fool.com/earnings/call-transcripts/2026/08/03/ares-ares-q2-2026-earnings-call-transcript/"

# 2026-08-10 sourcing pass, continued: Known gap 7 (object swallows a
# leading bare time-adjective with no preposition -- rw_016's "third
# quarter common stock dividend", rw_017's hallucinated "full-year
# guidance"). The 2026-08-08 session searched 8 real-earnings-call
# queries + 3 full transcripts and found nothing usable -- the one
# recurring match ("quarterly dividend") is a frequency adjective, not a
# time-point one. This pass found the real thing: "third quarter
# dividend" (Imperial Oil) and "third quarter 26 dividend" (Employers
# Holdings) -- same bare-time-adjective-directly-before-object-noun
# shape as rw_016, two different companies, neither overlapping
# rw_016's own Wells Fargo sentence. Still only 2 examples of this
# specific object-role pattern (rw_050 already gave the CRF one
# measure-role example of the same underlying shape) -- per this
# project's repeated "one example doesn't generalize" finding, this is
# progress, not a guaranteed fix; see CLAUDE.md Known gap 7 for the
# honest caveat.
IMO_URL = "https://www.fool.com/earnings/call-transcripts/2026/08/07/imperial-oil-imo-q2-2026-earnings-call-transcript/"
EIG_URL = "https://www.theglobeandmail.com/investing/markets/stocks/EIG-N/pressreleases/3730847/employers-holdings-eig-q2-2026-earnings-call-transcript/"

rows = [
    row("rw_001",
        "Target is on track to open over thirty stores in 2026.",
        TARGET_URL, "Michael Fiddelke (CEO), lightly trimmed to a standalone sentence",
        actor=field("Target", "explicit", 0.95, "Target"),
        intent=field("open new stores", "explicit", 0.8, "open"),
        object=field("stores", "explicit", 0.85, "stores"),
        magnitude=field("over thirty", "explicit", 0.9, "over thirty"),
        time=field("2026", "explicit", 0.9, "in 2026"),
        ),
    row("rw_002",
        "Target has more than one hundred store remodels underway in 2026.",
        TARGET_URL, "Michael Fiddelke (CEO), lightly trimmed",
        actor=field("Target", "explicit", 0.95, "Target"),
        object=field("store remodels", "explicit", 0.85, "store remodels"),
        magnitude=field("more than one hundred", "explicit", 0.9, "more than one hundred"),
        time=field("2026", "explicit", 0.85, "in 2026"),
        ),
    row("rw_003",
        "Target added around 1,500 new items and plans to refresh around 40% of its wellness assortment this year.",
        TARGET_URL, "Cara Sylvester (CMO), lightly trimmed",
        actor=field("Target", "explicit", 0.95, "Target"),
        object=field("wellness assortment", "explicit", 0.85, "wellness assortment"),
        intent=field("refresh product assortment", "explicit", 0.85, "refresh"),
        magnitude=field(["around 1,500", "around 40%"], "explicit", 0.9,
                         ["around 1,500", "around 40%"]),
        time=field("this year", "explicit", 0.9, "this year"),
        ),
    row("rw_004",
        "Target has provided more than 300,000 team members and leaders with guest experience training.",
        TARGET_URL, "Lisa Roath (COO), lightly trimmed",
        actor=field("Target", "explicit", 0.95, "Target"),
        object=field("team members and leaders", "explicit", 0.85, "team members and leaders"),
        intent=field("provide guest experience training", "explicit", 0.85, "provided"),
        magnitude=field("more than 300,000", "explicit", 0.9, "more than 300,000"),
        ),
    row("rw_005",
        "Target deployed about $1 billion for capital expenditures in the first quarter and expects about $5 billion of CapEx for the full year.",
        TARGET_URL, "James Lee (CFO), lightly trimmed",
        actor=field("Target", "explicit", 0.95, "Target"),
        object=field("capital expenditures", "explicit", 0.85, "capital expenditures"),
        intent=field("deploy capital expenditures", "explicit", 0.75, "deployed"),
        magnitude=field(["about $1 billion", "about $5 billion"], "explicit", 0.9,
                         ["about $1 billion", "about $5 billion"]),
        time=field(["in the first quarter", "for the full year"], "explicit", 0.9,
                    ["in the first quarter", "for the full year"]),
        ),
    row("rw_006",
        "Target plans to request another small increase in the quarterly dividend later this year, moving closer to its long-term goal of a 40% payout ratio.",
        TARGET_URL, "Michael Fiddelke (CEO), lightly trimmed",
        actor=field("Target", "explicit", 0.95, "Target"),
        object=field("quarterly dividend", "explicit", 0.85, "quarterly dividend"),
        intent=field("increase the dividend", "explicit", 0.8, "increase"),
        measure=field("payout ratio", "explicit", 0.85, "payout ratio"),
        magnitude=field("40%", "explicit", 0.9, "40%"),
        time=field("later this year", "explicit", 0.9, "later this year"),
        ),

    row("rw_007",
        "PNC remains on track to reduce costs by $350 million in 2026 through its continuous improvement program.",
        PNC_URL, "Robert Reilly (CFO), lightly trimmed",
        actor=field("PNC", "explicit", 0.95, "PNC"),
        intent=field("reduce costs", "explicit", 0.9, "reduce"),
        object=field("costs", "explicit", 0.85, "costs"),
        magnitude=field("$350 million", "explicit", 0.95, "$350 million"),
        time=field("2026", "explicit", 0.9, "in 2026"),
        context=field("achieved via the continuous improvement program", "explicit", 0.75,
                       "through its continuous improvement program"),
        ),
    row("rw_008",
        "PNC expects its net interest margin to go above 3% by the end of the year.",
        PNC_URL, "Robert Reilly (CFO), lightly trimmed",
        actor=field("PNC", "explicit", 0.95, "PNC"),
        measure=field("net interest margin", "explicit", 0.9, "net interest margin"),
        magnitude=field("above 3%", "explicit", 0.9, "above 3%"),
        time=field("by the end of the year", "explicit", 0.9, "by the end of the year"),
        ),
    row("rw_009",
        "PNC's operating target for its CET1 capital ratio is around 10%.",
        PNC_URL, "William Demchak (CEO), lightly trimmed",
        actor=field("PNC", "explicit", 0.9, "PNC"),
        measure=field("CET1 capital ratio", "explicit", 0.9, "CET1 capital ratio"),
        magnitude=field("around 10%", "explicit", 0.9, "around 10%"),
        ),
    row("rw_010",
        "PNC expects total revenue to be up approximately 13% compared to 2025.",
        PNC_URL, "Robert Reilly (CFO), lightly trimmed",
        actor=field("PNC", "explicit", 0.9, "PNC"),
        measure=field("total revenue", "explicit", 0.9, "total revenue"),
        magnitude=field("up approximately 13%", "explicit", 0.85, "up approximately 13%"),
        context=field("versus 2025", "explicit", 0.7, "compared to 2025"),
        ),
    row("rw_011",
        "PNC's board approved an 18% increase to its quarterly common stock dividend, raising it to $2 per share.",
        PNC_URL, "William Demchak (CEO), lightly trimmed",
        actor=field("PNC", "explicit", 0.9, "PNC"),
        object=field("quarterly common stock dividend", "explicit", 0.85, "quarterly common stock dividend"),
        intent=field("increase the dividend", "explicit", 0.8, "increase"),
        magnitude=field(["18%", "$2 per share"], "explicit", 0.9, ["18%", "$2 per share"]),
        ),

    row("rw_012",
        "FIS expects free cash flow to double by 2028 to more than $3 billion.",
        FIS_URL, "James Kehoe (CFO), verbatim",
        actor=field("FIS", "explicit", 0.95, "FIS"),
        measure=field("free cash flow", "explicit", 0.9, "free cash flow"),
        intent=field("double free cash flow", "explicit", 0.85, "double"),
        time=field("by 2028", "explicit", 0.9, "by 2028"),
        magnitude=field("more than $3 billion", "explicit", 0.9, "more than $3 billion"),
        ),
    row("rw_013",
        "FIS targets $125 million of long-term revenue synergies from the TSYS acquisition, with $45 million by 2028.",
        FIS_URL, "James Kehoe (CFO), lightly trimmed",
        actor=field("FIS", "explicit", 0.9, "FIS"),
        object=field("revenue synergies", "explicit", 0.85, "revenue synergies"),
        magnitude=field(["$125 million", "$45 million"], "explicit", 0.9, ["$125 million", "$45 million"]),
        time=field("by 2028", "explicit", 0.9, "by 2028"),
        context=field("from the TSYS acquisition", "explicit", 0.8, "from the TSYS acquisition"),
        ),
    row("rw_014",
        "FIS expects cost synergies of $30 million to $40 million in 2026, with most of that flowing through in the second half of the year.",
        FIS_URL, "James Kehoe (CFO), lightly trimmed",
        actor=field("FIS", "explicit", 0.9, "FIS"),
        object=field("cost synergies", "explicit", 0.85, "cost synergies"),
        magnitude=field("$30 million to $40 million", "explicit", 0.9, "$30 million to $40 million"),
        time=field(["in 2026", "in the second half of the year"], "explicit", 0.85,
                    ["in 2026", "in the second half of the year"]),
        ),
    row("rw_015",
        "FIS is guiding to adjusted EPS growth of 8% to 10% for the full year.",
        FIS_URL, "James Kehoe / Stephanie Ferris, lightly trimmed",
        actor=field("FIS", "explicit", 0.9, "FIS"),
        measure=field("adjusted EPS", "explicit", 0.85, "adjusted EPS"),
        intent=field("grow adjusted EPS", "explicit", 0.75, "growth"),
        magnitude=field("8% to 10%", "explicit", 0.9, "8% to 10%"),
        time=field("for the full year", "explicit", 0.9, "for the full year"),
        ),

    row("rw_016",
        "Wells Fargo expects to increase its third quarter common stock dividend by 11% to $0.50 per share, subject to board approval.",
        WFC_URL, "Charles W. Scharf (CEO), verbatim",
        actor=field("Wells Fargo", "explicit", 0.95, "Wells Fargo"),
        object=field("common stock dividend", "explicit", 0.85, "common stock dividend"),
        intent=field("increase the dividend", "explicit", 0.85, "increase"),
        magnitude=field(["11%", "$0.50 per share"], "explicit", 0.9, ["11%", "$0.50 per share"]),
        time=field("third quarter", "explicit", 0.85, "third quarter"),
        constraints=field("subject to board approval", "explicit", 0.85, "subject to board approval"),
        ),
    row("rw_017",
        "Wells Fargo is maintaining its full-year guidance of about $50 billion in net interest income.",
        WFC_URL, "Michael Santomassimo (CFO), lightly trimmed",
        actor=field("Wells Fargo", "explicit", 0.9, "Wells Fargo"),
        measure=field("net interest income", "explicit", 0.85, "net interest income"),
        intent=field("maintain guidance", "explicit", 0.75, "maintaining"),
        magnitude=field("about $50 billion", "explicit", 0.85, "about $50 billion"),
        time=field("full-year", "explicit", 0.85, "full-year"),
        ),
    row("rw_018",
        "Wells Fargo has delivered 24 consecutive quarters of headcount reductions while continuing to invest in its businesses.",
        WFC_URL, "Michael Santomassimo (CFO), lightly trimmed",
        actor=field("Wells Fargo", "explicit", 0.9, "Wells Fargo"),
        object=field("headcount reductions", "explicit", 0.85, "headcount reductions"),
        magnitude=field("24 consecutive quarters", "explicit", 0.9, "24 consecutive quarters"),
        constraints=field("must keep investing in the business while cutting headcount",
                           "explicit", 0.7, "while continuing to invest in its businesses"),
        ),

    row("rw_019",
        "D.R. Horton aims to increase its inventory turn from two times to a target of three times to improve capital efficiency.",
        DHI_URL, "CFO Wheat, lightly trimmed",
        actor=field("D.R. Horton", "explicit", 0.9, "D.R. Horton"),
        measure=field("inventory turn", "explicit", 0.85, "inventory turn"),
        intent=field("increase inventory turn", "explicit", 0.8, "increase"),
        magnitude=field("from two times to a target of three times", "explicit", 0.85,
                         "from two times to a target of three times"),
        context=field("to improve capital efficiency", "explicit", 0.8, "to improve capital efficiency"),
        ),
    row("rw_020",
        "D.R. Horton targets consolidated leverage of around 20% over the long term, down from 23% at the end of June.",
        DHI_URL, "lightly trimmed",
        actor=field("D.R. Horton", "explicit", 0.9, "D.R. Horton"),
        measure=field("consolidated leverage", "explicit", 0.85, "consolidated leverage"),
        magnitude=field(["around 20%", "23%"], "explicit", 0.85, ["around 20%", "23%"]),
        time=field(["over the long term", "at the end of June"], "explicit", 0.8,
                    ["over the long term", "at the end of June"]),
        ),
    row("rw_021",
        "D.R. Horton expects operating cash flow of at least $3 billion for fiscal 2026, while keeping rental inventory around $3 billion.",
        DHI_URL, "lightly trimmed",
        actor=field("D.R. Horton", "explicit", 0.9, "D.R. Horton"),
        measure=field("operating cash flow", "explicit", 0.85, "operating cash flow"),
        magnitude=field("at least $3 billion", "explicit", 0.9, "at least $3 billion"),
        time=field("for fiscal 2026", "explicit", 0.9, "for fiscal 2026"),
        constraints=field("keep rental inventory around $3 billion", "explicit", 0.8,
                           "while keeping rental inventory around $3 billion"),
        ),

    row("rw_022",
        "Citizens expects to exit 2026 with about $100 million of annualized pre-tax benefit from its Reimagine the Bank program, and reaching about $450 million by 2028.",
        CFG_URL, "Aunoy Banerjee, lightly trimmed",
        actor=field("Citizens", "explicit", 0.85, "Citizens"),
        measure=field("annualized pre-tax benefit", "explicit", 0.85, "annualized pre-tax benefit"),
        magnitude=field(["about $100 million", "about $450 million"], "explicit", 0.85,
                         ["about $100 million", "about $450 million"]),
        time=field(["2026", "by 2028"], "explicit", 0.8, ["2026", "by 2028"]),
        context=field("from its Reimagine the Bank program", "explicit", 0.8,
                       "from its Reimagine the Bank program"),
        ),
    row("rw_023",
        "Citizens plans to eliminate approximately 100 to 120 in-store branches as part of its NEXT program, while adding standalone advisory and business banking branches.",
        CFG_URL, "Aunoy Banerjee, lightly trimmed",
        actor=field("Citizens", "explicit", 0.85, "Citizens"),
        object=field("in-store branches", "explicit", 0.85, "in-store branches"),
        intent=field("close in-store branches", "explicit", 0.8, "eliminate"),
        magnitude=field("approximately 100 to 120", "explicit", 0.85, "approximately 100 to 120"),
        context=field("as part of its NEXT program", "explicit", 0.8, "as part of its NEXT program"),
        constraints=field("must still add standalone advisory and business banking branches",
                           "explicit", 0.75, "while adding standalone advisory and business banking branches"),
        ),
    row("rw_024",
        "Citizens' private bank now contributes 11.5% of pre-tax income while maintaining an ROE of around 25%.",
        CFG_URL, "Bruce Van Saun, lightly trimmed",
        actor=field("Citizens", "explicit", 0.85, "Citizens"),
        object=field("private bank", "explicit", 0.8, "private bank"),
        measure=field(["pre-tax income", "ROE"], "explicit", 0.8, ["pre-tax income", "ROE"]),
        magnitude=field(["11.5%", "around 25%"], "explicit", 0.85, ["11.5%", "around 25%"]),
        ),

    row("rw_025",
        "Buffer is on track in 2025 to increase its net profit and bonuses by 5X or more.",
        BUFFER_URL, "verbatim (shareholder update)",
        actor=field("Buffer", "explicit", 0.95, "Buffer"),
        object=field("net profit and bonuses", "explicit", 0.85, "net profit and bonuses"),
        intent=field("increase net profit", "explicit", 0.8, "increase"),
        magnitude=field("by 5X or more", "explicit", 0.9, "by 5X or more"),
        time=field("2025", "explicit", 0.9, "in 2025"),
        ),
    row("rw_026",
        "Buffer plans to expand into a platform that customers and developers can build upon.",
        BUFFER_URL, "verbatim (shareholder update)",
        actor=field("Buffer", "explicit", 0.9, "Buffer"),
        intent=field("expand into a platform", "explicit", 0.8, "expand"),
        object=field("platform", "explicit", 0.8, "platform"),
        context=field("for customers and developers to build upon", "explicit", 0.7,
                       "that customers and developers can build upon"),
        ),

    row("rw_027",
        "FactSet's organic ASV growth was 7.0% in the Americas, 10.0% in Asia Pacific, and 5.0% in EMEA.",
        FACTSET_URL, "TAKEAWAYS section, lightly trimmed",
        actor=field("FactSet", "explicit", 0.9, "FactSet"),
        measure=field("organic ASV growth", "explicit", 0.85, "organic ASV growth"),
        scope=field(["Americas", "Asia Pacific", "EMEA"], "explicit", 0.85,
                     ["in the Americas", "in Asia Pacific", "in EMEA"]),
        magnitude=field(["7.0%", "10.0%", "5.0%"], "explicit", 0.9, ["7.0%", "10.0%", "5.0%"]),
        ),
    row("rw_028",
        "Target's digital channel sales grew nearly 9%, while same-day delivery grew more than 27%.",
        TARGET_URL, "lightly trimmed",
        actor=field("Target", "explicit", 0.9, "Target"),
        scope=field(["digital channel", "same-day delivery"], "explicit", 0.85,
                     ["digital channel", "same-day delivery"]),
        intent=field("grow sales", "explicit", 0.75, "grew"),
        magnitude=field(["nearly 9%", "more than 27%"], "explicit", 0.85, ["nearly 9%", "more than 27%"]),
        ),
    row("rw_029",
        "Citizens continues investing in Florida as a growth area for its private bank.",
        CFG_URL, "Bruce Van Saun, lightly trimmed",
        actor=field("Citizens", "explicit", 0.85, "Citizens"),
        scope=field("Florida", "explicit", 0.85, "Florida"),
        object=field("private bank", "explicit", 0.8, "private bank"),
        intent=field("invest in growth", "explicit", 0.7, "investing"),
        ),
    row("rw_030",
        "Citizens is adding new commercial banking clients across the technology, healthcare, and energy sectors.",
        CFG_URL, "lightly trimmed",
        actor=field("Citizens", "explicit", 0.85, "Citizens"),
        scope=field("technology, healthcare, and energy sectors", "explicit", 0.8,
                     "technology, healthcare, and energy sectors"),
        object=field("commercial banking clients", "explicit", 0.85, "commercial banking clients"),
        intent=field("add new clients", "explicit", 0.75, "adding"),
        ),

    row("rw_031",
        "Intuit's mid-market direct sales team was expanded by approximately 30%.",
        INTUIT_URL, "Sasan K. Goodarzi (CEO), rephrased to third person; generic team-as-actor, not company name",
        actor=field("Intuit's mid-market direct sales team", "explicit", 0.8,
                     "Intuit's mid-market direct sales team"),
        intent=field("expand the sales team", "explicit", 0.7, "was expanded"),
        magnitude=field("approximately 30%", "explicit", 0.9, "approximately 30%"),
        ),
    row("rw_032",
        "FactSet's engineering teams have pushed AI code-authorship share to 27% of committed code.",
        FACTSET_URL, "Sanoke Viswanathan (CEO); original: 'Coding agents now author 27% of committed "
             "code in the engineering teams using these tools' -- rephrased with team as subject",
        actor=field("FactSet's engineering teams", "explicit", 0.8, "FactSet's engineering teams"),
        measure=field("AI code-authorship share", "explicit", 0.75, "AI code-authorship share"),
        magnitude=field("27%", "explicit", 0.9, "27%"),
        object=field("committed code", "explicit", 0.8, "committed code"),
        ),
    row("rw_033",
        "FactSet initiated a roughly 10% reduction in its technology workforce to free up capacity for strategic product development.",
        FACTSET_URL, "Sanoke Viswanathan (CEO), lightly trimmed -- purpose/causal context clause",
        actor=field("FactSet", "explicit", 0.9, "FactSet"),
        intent=field("reduce workforce", "explicit", 0.8, "initiated"),
        object=field("technology workforce", "explicit", 0.85, "technology workforce"),
        magnitude=field("roughly 10%", "explicit", 0.9, "roughly 10%"),
        context=field("freeing up capacity for strategic product development", "explicit", 0.75,
                       "to free up capacity for strategic product development"),
        ),
    row("rw_034",
        "Albany International's Engineered Composites segment grew 16% because of higher production rates across the LEAP, Boeing, and CH-53K programs.",
        ALBANY_URL, "Willard Station, lightly trimmed -- causal context + programs-as-scope",
        actor=field("Albany International", "explicit", 0.85, "Albany International"),
        object=field("Engineered Composites segment", "explicit", 0.85, "Engineered Composites segment"),
        magnitude=field("16%", "explicit", 0.9, "16%"),
        scope=field(["LEAP", "Boeing", "CH-53K programs"], "explicit", 0.8,
                     ["LEAP", "Boeing", "CH-53K programs"]),
        context=field("driven by higher production rates", "explicit", 0.7, "because of higher production rates"),
        ),
    row("rw_035",
        "Albany International's tooling for a next-generation defense program has shifted into the back half of the year.",
        ALBANY_URL, "Gunnar Kleveland, lightly trimmed -- constraint via delayed timeline, not 'subject to' phrasing",
        actor=field("Albany International", "explicit", 0.85, "Albany International"),
        object=field("tooling", "explicit", 0.7, "tooling"),
        scope=field("next-generation defense program", "explicit", 0.7, "next-generation defense program"),
        constraints=field("delivery delayed to the back half of the year", "explicit", 0.75,
                           "has shifted into the back half of the year"),
        ),
    row("rw_036",
        "Trane Technologies is expanding its margins without increasing costs or capital intensity.",
        TRANE_URL, "Christopher Kuehn (CFO), lightly trimmed -- genuine negation-cue constraint in a "
             "formal earnings call; a real counter-example to Known gap 2's 'found zero' finding",
        actor=field("Trane Technologies", "explicit", 0.9, "Trane Technologies"),
        intent=field("expand margins", "explicit", 0.8, "expanding its margins"),
        constraints=field("without increasing costs or capital intensity", "explicit", 0.85,
                           "without increasing costs or capital intensity"),
        ),
    row("rw_037",
        "Trane Technologies' teams in Asia Pacific delivered bookings up 31% this quarter.",
        TRANE_URL, "David Regnery (CEO), lightly trimmed -- regional team-as-actor",
        actor=field("Trane Technologies' teams", "explicit", 0.8, "Trane Technologies' teams"),
        measure=field("bookings", "explicit", 0.8, "bookings"),
        magnitude=field("31%", "explicit", 0.85, "31%"),
        scope=field("Asia Pacific", "explicit", 0.85, "Asia Pacific"),
        time=field("this quarter", "explicit", 0.8, "this quarter"),
        ),
    row("rw_038",
        "The residential business team delivered a very strong second quarter.",
        TRANE_URL, "David Regnery (CEO), lightly trimmed -- actor is a bare role/team phrase with no "
             "company name anchor at all, the exact pattern Known gap 0 flagged",
        actor=field("The residential business team", "explicit", 0.75, "The residential business team"),
        intent=field("perform strongly", "explicit", 0.6, "delivered a very strong"),
        time=field("second quarter", "explicit", 0.7, "second quarter"),
        ),

    row("rw_039",
        "FactSet's data operations team now ingests third-party data at 10 times the speed without adding headcount.",
        FACTSET_Q1_URL, "Helen Shan (CFO), lightly trimmed",
        actor=field("FactSet's data operations team", "explicit", 0.8, "FactSet's data operations team"),
        intent=field("ingest data faster", "explicit", 0.7, "now ingests"),
        object=field("third-party data", "explicit", 0.75, "third-party data"),
        magnitude=field("10 times the speed", "explicit", 0.85, "10 times the speed"),
        constraints=field("without adding headcount", "explicit", 0.85, "without adding headcount"),
        ),
    row("rw_040",
        "The company is growing market share and processing more volume without adding meaningfully to operational headcount.",
        EFC_URL, "Mark Tecotzky (Co-Chief Investment Officer), lightly trimmed",
        actor=field("The company", "explicit", 0.55, "The company"),
        intent=field("grow market share", "explicit", 0.7, "growing market share"),
        constraints=field("without adding meaningfully to operational headcount", "explicit", 0.85,
                           "without adding meaningfully to operational headcount"),
        ),
    row("rw_041",
        "Tesla has continually brought down the cost of its vehicles without sacrificing range, performance, or premiumness.",
        TESLA_URL, "Lars Moravy (VP Vehicle Engineering), lightly trimmed",
        actor=field("Tesla", "explicit", 0.9, "Tesla"),
        intent=field("reduce vehicle costs", "explicit", 0.8, "brought down the cost"),
        object=field("vehicles", "explicit", 0.8, "vehicles"),
        constraints=field("without sacrificing range, performance, or premiumness", "explicit", 0.85,
                           "without sacrificing range, performance, or premiumness"),
        ),
    row("rw_042",
        "Climb Global increased throughput across its platform to support higher volumes of activity without the commensurate increase in head count.",
        CLIMB_URL, "Dale Foster (CEO), lightly trimmed -- purpose clause + negation-cue constraint in one sentence",
        actor=field("Climb Global", "explicit", 0.85, "Climb Global"),
        intent=field("increase throughput", "explicit", 0.75, "increased throughput"),
        object=field("platform", "explicit", 0.6, "platform"),
        context=field("supporting higher volumes of activity", "explicit", 0.7,
                       "to support higher volumes of activity"),
        constraints=field("without the commensurate increase in head count", "explicit", 0.85,
                           "without the commensurate increase in head count"),
        ),
    row("rw_043",
        "Climb Global's strong quarter was driven by the strength of its global platform.",
        CLIMB_URL, "Dale Foster (CEO), lightly trimmed -- causal context clause",
        actor=field("Climb Global", "explicit", 0.85, "Climb Global"),
        context=field("attributed to the strength of its global platform", "explicit", 0.75,
                       "driven by the strength of its global platform"),
        ),

    # 2026-08-08 sourcing pass: targeting the measure subject-position blind
    # spot diagnosed 2026-08-06 (Known gap 1) -- possessive-subject phrasing
    # ("X's <measure> is/was...") and "X expects <measure> to..." phrasing,
    # the two shapes the CRF had near-zero training coverage for. All 4
    # companies (Thermo Fisher, AGCO, S&P Global, DexCom) are new to the
    # dataset, so this also avoids conflating "learned the pattern" with
    # "memorized the company name."
    row("rw_044",
        "Thermo Fisher expects free cash flow to be in the range of $6.9 billion to $7.4 billion for the year.",
        TMO_URL, "James Meyer (CFO), rephrased to third person -- 'expects X' pattern, held out for eval",
        actor=field("Thermo Fisher", "explicit", 0.9, "Thermo Fisher"),
        measure=field("free cash flow", "explicit", 0.85, "free cash flow"),
        magnitude=field("in the range of $6.9 billion to $7.4 billion", "explicit", 0.85,
                         "in the range of $6.9 billion to $7.4 billion"),
        time=field("for the year", "explicit", 0.8, "for the year"),
        ),
    row("rw_045",
        "Thermo Fisher's adjusted operating margin was 22.8% in the second quarter, 90 basis points higher than a year ago.",
        TMO_URL, "Marc Casper (CEO) / James Meyer (CFO), rephrased to possessive-subject form -- "
             "magnitude/time split to match the rw_010/rw_020 convention (bare number in magnitude, "
             "comparison anchor in time) after 2026-08-08 diagnosis showed bundling them taught the "
             "CRF to swallow trailing time clauses into magnitude",
        actor=field("Thermo Fisher", "explicit", 0.9, "Thermo Fisher"),
        measure=field("adjusted operating margin", "explicit", 0.85, "adjusted operating margin"),
        magnitude=field(["22.8%", "90 basis points"], "explicit", 0.85,
                         ["22.8%", "90 basis points"]),
        time=field(["in the second quarter", "a year ago"], "explicit", 0.8,
                    ["in the second quarter", "a year ago"]),
        ),
    row("rw_046",
        "AGCO's adjusted operating margin was 6.6% in the second quarter, 170 basis points lower than the prior year.",
        AGCO_URL, "Damon J. Audia (CFO), rephrased to possessive-subject form -- "
             "magnitude/time split, same fix as rw_045",
        actor=field("AGCO", "explicit", 0.9, "AGCO"),
        measure=field("adjusted operating margin", "explicit", 0.85, "adjusted operating margin"),
        magnitude=field(["6.6%", "170 basis points"], "explicit", 0.85,
                         ["6.6%", "170 basis points"]),
        time=field(["in the second quarter", "the prior year"], "explicit", 0.8,
                    ["in the second quarter", "the prior year"]),
        ),
    row("rw_047",
        "AGCO expects adjusted operating margin of approximately 7.5% for 2026.",
        AGCO_URL, "Damon J. Audia (CFO), rephrased to third person -- 'expects X' pattern",
        actor=field("AGCO", "explicit", 0.9, "AGCO"),
        measure=field("adjusted operating margin", "explicit", 0.85, "adjusted operating margin"),
        magnitude=field("approximately 7.5%", "explicit", 0.85, "approximately 7.5%"),
        time=field("2026", "explicit", 0.8, "for 2026"),
        ),
    row("rw_048",
        "S&P Global's operating margin for its Mobility division expanded 150 basis points year-over-year to 40%.",
        SPGI_URL, "Eric Aboaf (CFO), rephrased to possessive-subject form with division as scope",
        actor=field("S&P Global", "explicit", 0.9, "S&P Global"),
        measure=field("operating margin", "explicit", 0.85, "operating margin"),
        scope=field("Mobility division", "explicit", 0.8, "Mobility division"),
        magnitude=field("expanded 150 basis points year-over-year to 40%", "explicit", 0.85,
                         "expanded 150 basis points year-over-year to 40%"),
        ),
    row("rw_049",
        "DexCom's gross margin was 64.1% of revenue in the second quarter, up from 60.1% a year earlier.",
        DXCM_URL, "Jereme Sylvain (CFO), rephrased to possessive-subject form, held out for eval -- "
             "magnitude/time split, same fix as rw_045/rw_046",
        actor=field("DexCom", "explicit", 0.9, "DexCom"),
        measure=field("gross margin", "explicit", 0.85, "gross margin"),
        magnitude=field(["64.1% of revenue", "60.1%"], "explicit", 0.85,
                         ["64.1% of revenue", "60.1%"]),
        time=field(["in the second quarter", "a year earlier"], "explicit", 0.8,
                    ["in the second quarter", "a year earlier"]),
        ),
    row("rw_050",
        "DexCom expects full-year revenue of $5.18 billion to $5.25 billion, representing growth of 11% to 13%.",
        DXCM_URL, "Jereme Sylvain (CFO), rephrased to third person -- 'expects X' pattern. "
             "2026-08-08 fix: 'full-year' was originally bundled whole into measure "
             "(measure='full-year revenue', time=missing), contradicting the established "
             "convention of splitting a bare time-adjective into its own time span (see "
             "rw_017's holdout gold: measure='net interest income', time='full-year'). That "
             "bug taught the CRF the wrong lesson and caused time false-negatives on "
             "rw_016/rw_017 -- corrected to split time from measure like every other row.",
        actor=field("DexCom", "explicit", 0.9, "DexCom"),
        measure=field("revenue", "explicit", 0.85, "revenue"),
        magnitude=field(["$5.18 billion to $5.25 billion", "growth of 11% to 13%"], "explicit", 0.85,
                         ["$5.18 billion to $5.25 billion", "growth of 11% to 13%"]),
        time=field("full-year", "explicit", 0.8, "full-year"),
        ),
    row("rw_051",
        "F5's revenue grew 3% in the Americas, 22% in EMEA, and 19% in APAC year over year.",
        FFIV_URL, "Cooper Werner (CFO), condensed from 4 sentences to 1 and rephrased to "
             "possessive-subject form -- real 3-way magnitude join (Known gap 8), same shape "
             "as rw_027 (Americas/EMEA/APAC percentages) but a different company so the CRF/T5 "
             "can't just memorize FactSet's numbers.",
        actor=field("F5", "explicit", 0.9, "F5"),
        measure=field("revenue", "explicit", 0.85, "revenue"),
        scope=field(["Americas", "EMEA", "APAC"], "explicit", 0.85,
                    ["in the Americas", "in EMEA", "in APAC"]),
        magnitude=field(["3%", "22%", "19%"], "explicit", 0.9, ["3%", "22%", "19%"]),
        time=field("year over year", "explicit", 0.8, "year over year"),
        ),

    row("rw_052",
        "Equinox Gold's board approved a 50% increase to its annual dividend to $0.09 per share.",
        EQX_URL, "Darren Pylot (President & COO), rephrased to third person -- single-digit-cents "
             "decimal + whole percent, targeting Known gap 8's decimal-dollar-join corruption",
        actor=field("Equinox Gold", "explicit", 0.9, "Equinox Gold"),
        intent=field("increase the dividend", "explicit", 0.8, "increase"),
        object=field("annual dividend", "explicit", 0.85, "annual dividend"),
        magnitude=field(["50%", "$0.09 per share"], "explicit", 0.9, ["50%", "$0.09 per share"]),
        ),
    row("rw_053",
        "Alpine Income Property Trust's board has authorized a 6.7% increase in its quarterly common "
        "dividend to $0.32 per share beginning in the third quarter of 2026.",
        PINE_URL, "John Albright (President & CEO), rephrased to third person -- two-digit-cents "
             "decimal + decimal percent, targeting Known gap 8",
        actor=field("Alpine Income Property Trust", "explicit", 0.9, "Alpine Income Property Trust"),
        intent=field("increase the dividend", "explicit", 0.8, "increase"),
        object=field("quarterly common dividend", "explicit", 0.85, "quarterly common dividend"),
        magnitude=field(["6.7%", "$0.32 per share"], "explicit", 0.9, ["6.7%", "$0.32 per share"]),
        time=field("beginning in the third quarter of 2026", "explicit", 0.8,
                    "beginning in the third quarter of 2026"),
        ),
    row("rw_054",
        "Ares Management declared a quarterly dividend of $1.35 per share on its Class A and nonvoting "
        "common stock, representing an increase of over 20% over its dividend for the same quarter a "
        "year ago.",
        ARES_URL, "Greg Mason (Co-Head of Public Markets, Investor Relations), rephrased to third "
             "person -- decimal dollar over $1 + an inexact 'over X%' qualifier, targeting Known gap 8",
        actor=field("Ares Management", "explicit", 0.9, "Ares Management"),
        intent=field("increase the dividend", "explicit", 0.75, "increase"),
        object=field("quarterly dividend", "explicit", 0.85, "quarterly dividend"),
        magnitude=field(["$1.35 per share", "over 20%"], "explicit", 0.9, ["$1.35 per share", "over 20%"]),
        time=field("for the same quarter a year ago", "explicit", 0.75, "for the same quarter a year ago"),
        ),

    row("rw_055",
        "Imperial Oil declared a third quarter dividend of $0.87 per share.",
        IMO_URL, "Dan Lyons (SVP, Finance & Administration), rephrased to third person -- bare "
             "time-adjective directly before an object noun ('third quarter dividend'), same shape "
             "as rw_016 but a different company, targeting Known gap 7",
        actor=field("Imperial Oil", "explicit", 0.9, "Imperial Oil"),
        intent=field("declare a dividend", "explicit", 0.75, "declared"),
        object=field("dividend", "explicit", 0.8, "dividend"),
        time=field("third quarter", "explicit", 0.75, "third quarter"),
        magnitude=field("$0.87 per share", "explicit", 0.9, "$0.87 per share"),
        ),
    row("rw_056",
        "Employers Holdings' Board of Directors declared a third quarter 26 dividend of $0.34 per "
        "share, consistent with the 6.5% increase it implemented last quarter.",
        EIG_URL, "Katherine Holt Antonello (CEO), rephrased to third person -- same 'third quarter "
             "<object>' shape as rw_055/rw_016, targeting Known gap 7; also a second real example "
             "for Known gap 8 (decimal per-share magnitude, $0.34)",
        actor=field("Employers Holdings", "explicit", 0.9, "Employers Holdings"),
        intent=field("declare a dividend", "explicit", 0.75, "declared"),
        object=field("dividend", "explicit", 0.8, "dividend"),
        time=field("third quarter 26", "explicit", 0.7, "third quarter 26"),
        magnitude=field("$0.34 per share", "explicit", 0.85, "$0.34 per share"),
        context=field("consistent with the prior 6.5% dividend increase", "explicit", 0.7,
                       "consistent with the 6.5% increase it implemented last quarter"),
        ),
]

if __name__ == "__main__":
    with open("data/real_world_pilot_batch.json", "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)
    print(f"Wrote {len(rows)} rows to data/real_world_pilot_batch.json")
