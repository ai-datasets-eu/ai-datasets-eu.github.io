"""Draws all charts on the site.

Run from the repository root:  python figures/make_figures.py

1. Result charts for the survey pages: one entry in FIGURES per chart.
2. The three adoption time series on the overview page (individuals, workers,
   firms). These are built from the YAML header of every survey page (fields:
   month, adoption-individuals, adoption-workers, adoption-firms, coverage,
   series, earlier-waves), so they update when a survey is added. Lines join
   only the waves of one survey (same `series`), never different surveys.
"""
import re

import numpy as np
from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import yaml
from matplotlib.lines import Line2D

ACCENT = "#1f4e79"      # site navy
HIGHLIGHT = "#e2703a"   # headline value
TRACK = "#e9eff5"
INK = "#1d2733"
MUTED = "#6b7785"
OUT = Path(__file__).parent
ROOT = OUT.parent

plt.rcParams["font.family"] = ["Fira Sans", "Segoe UI", "DejaVu Sans"]
plt.rcParams["svg.fonttype"] = "path"

# name: (title, unit, [(label, value), ...]).  A label starting with "*" is the
# headline value and is drawn in the highlight colour.
FIGURES = {
    # Eurostat, ICT usage in enterprises
    "eurostat-ent-2024-size": (
        "Enterprises using AI, by size, 2024",
        "% of enterprises with 10+ employees, EU",
        [("*All", 13.5), ("Small (10-49)", 11.2), ("Medium (50-249)", 21.0), ("Large (250+)", 41.2)],
    ),
    "eurostat-ent-size": (
        "Enterprises using AI, by size, 2025",
        "% of enterprises with 10+ employees, EU",
        [("*All", 20.0), ("Small (10-49)", 17.0), ("Medium (50-249)", 30.4), ("Large (250+)", 55.0)],
    ),
    "eurostat-ent-trend": (
        "Enterprises using AI, 2024 and 2025",
        "% of enterprises with 10+ employees, EU",
        [("2024", 13.5), ("*2025", 20.0)],
    ),
    # Eurostat, ICT usage by individuals 2025
    "eurostat-ind-purpose": (
        "Use of generative AI tools, by purpose, 2025",
        "% of people aged 16-74, EU, last 3 months",
        [("Any purpose", 32.7), ("Private", 25.5), ("Work", 15.4), ("*Work, employed people aged 25-64", 21.9), ("Formal education", 9.3)],
    ),
    "eurostat-ind-age": (
        "Use of generative AI tools, by age, 2025",
        "% of age group, EU, last 3 months",
        [("Aged 16-74", 32.7), ("Aged 16-24", 63.8)],
    ),
    # ECB SAFE, Q4 2025
    "ecb-safe-intensity": (
        "Use of AI technologies in the firm, Q4 2025",
        "% of firms, 12 euro area countries, weighted by employment",
        [("Not in use", 27), ("Very infrequent / pilot", 33), ("Moderate use", 31), ("Significant use", 7)],
    ),
    "ecb-safe-size": (
        "Firms not using AI, by size, Q4 2025",
        "% of firms in each size class, 12 euro area countries",
        [("SMEs", 35), ("Large firms", 13)],
    ),
    # JRC AIM-WORK 2024-25
    "jrc-aim-work": (
        "Digital tools and algorithmic management at work",
        "% of EU workers",
        [
            ("Use digital devices", 90),
            ("Working hours digitally monitored", 37),
            ("*Use AI tools", 30),
            ("Schedule set automatically", 24),
        ],
    ),
    # Cedefop AI skills survey 2024
    "cedefop-use": (
        "AI at the workplace",
        "% of workers, 11 EU countries",
        [("AI is used at their workplace", 28), ("It is not", 55), ("Not sure", 16)],
    ),
    "cedefop-tasks": (
        "How AI has changed job tasks",
        "% of workers who use AI at work, 11 EU countries",
        [
            ("Do some tasks faster", 67),
            ("Do some new or different tasks", 41),
            ("No longer do some tasks", 30),
            ("Have less control over tasks", 17),
        ],
    ),
    # Special Eurobarometer 554, 2024
    "eb554-views": (
        "Views on robots and AI at work",
        "% who agree, EU",
        [
            ("Speed up how fast tasks get done", 73),
            ("Needed for boring or repetitive jobs", 66),
            ("More jobs will disappear than be created", 66),
            ("Harm communication between colleagues", 61),
            ("Can make accurate decisions at work", 53),
        ],
    ),
    "eb554-management": (
        "Activities done by digital technologies, including AI",
        "% of people with a current or past job, EU",
        [
            ("Monitoring workers' activities", 24),
            ("Allocating tasks to workers", 22),
            ("Assessing performance", 21),
            ("Hiring workers", 18),
        ],
    ),
    # DG ECFIN consumer survey, ad hoc AI module, Feb-Mar 2026
    "ecfin-use": (
        "Use of AI technologies, early 2026",
        "%, 18 EU Member States",
        [("Use AI for any purpose (all respondents)", 54), ("*Use AI for work (employed)", 34.5)],
    ),
    "ecfin-impact": (
        "What people who use AI for work report",
        "% of those using AI for work, 18 EU Member States",
        [("AI makes tasks faster", 91), ("Worried about losing their job to AI", 41)],
    ),
    # Flash Eurobarometer 578, Mar-Apr 2026
    "fl578-use": (
        "AI and algorithmic management in SMEs and mid-caps, 2026",
        "% of companies with 1-749 employees, EU",
        [("*Already use it", 42), ("Plan to use it", 21)],
    ),
    "fl578-barriers": (
        "Barriers to wider AI adoption",
        "% of companies with 1-749 employees, EU",
        [("High investment costs", 50), ("Legal uncertainty", 49), ("Lack of expertise", 48)],
    ),
    # Bick et al., worker survey
    "bick-2025": (
        "Workers using generative AI for work, May-June 2025",
        "% of employed people aged 18-67 (18-63 in France)",
        [("Netherlands", 33.9), ("Sweden", 33.1), ("Germany", 30.7), ("France", 28.0), ("Italy", 24.5),
         ("United Kingdom", 34.7), ("United States", 39.4)],
    ),
    "bick-2026": (
        "Workers using generative AI for work, January-February 2026",
        "% of employed people aged 18-67 (18-63 in France)",
        [("Sweden", 35.6), ("Netherlands", 35.6), ("Germany", 31.5), ("France", 28.1), ("Italy", 25.6),
         ("United Kingdom", 36.3), ("United States", 43.0)],
    ),
    # ECB Consumer Expectations Survey
    "ecb-ces-trend": (
        "Workers using AI in their work",
        "% of workers, 11 euro area countries",
        [("2024", 26), ("2025", 41), ("*2026", 52)],
    ),
    "ecb-ces-education": (
        "AI use at work by education, 2026",
        "% of workers, 11 euro area countries",
        [("Highly educated", 61), ("Lower education", 37)],
    ),
    # EIB Investment Survey 2025
    "eibis-genai": (
        "Firms using generative AI as measured by the EIB, 2025",
        "% of firms, weighted by value added; combines two questions (see text)",
        [("*European Union", 37), ("United States", 36)],
    ),
    # Private surveys
    "aws-trend": (
        "Businesses that say they have adopted AI",
        "% of businesses, 17 European countries",
        [("2024", 33), ("2025", 42), ("*2026", 54)],
    ),
    "aws-stage": (
        "How far AI adopters have got, 2026",
        "% of businesses that have adopted AI; shares as published, they sum to 97%",
        [("Basic stage", 58), ("Intermediate", 17), ("Advanced", 22)],
    ),
    "sdworx": (
        "AI at work in 16 European countries",
        "% of employees, unless stated",
        [("*Use AI at least once a week (2026)", 29), ("Regularly use AI at work (2025)", 23),
         ("Regularly use AI at work (2024)", 18), ("Employers investing in AI (2025)", 38)],
    ),
    "ey-barometer": (
        "Workers and AI, 9 Western European countries",
        "% of managers and employees",
        [("*Ever used or been involved with AI (2025)", 78), ("Same question (2024)", 72),
         ("Positive attitude towards AI (2025)", 70)],
    ),
    "deloitte-use": (
        "Generative AI: awareness and use, mid-2024",
        "% of people aged 16-75, 11 European countries",
        [("*Have used generative AI", 44), ("Aware but not using", 22), ("Unaware or unsure", 34)],
    ),
    "deloitte-purpose": (
        "What generative AI is used for, mid-2024",
        "% of people aware of generative AI",
        [("Personal tasks", 47), ("Work", 23)],
    ),
    "kpmg-countries": (
        "People using AI regularly or semi-regularly, EU countries",
        "% of people, any purpose, Nov 2024-Jan 2025; selected EU countries",
        [('Latvia (highest in the EU)', 72), ('Poland', 69), ('Italy', 60), ('Spain', 60), ('France', 51),
         ('Germany', 51), ('Belgium', 47), ('Netherlands (lowest in the EU)', 43)],
    ),
    "pwc-hopes": (
        "Employees using AI at work, 2026",
        "% of employees, May-June 2026",
        [('*Belgium', 56), ('Western Europe', 56), ('North America', 55), ('Asia Pacific', 72), ('Middle East', 80)],
    ),
    "mckinsey-regions": (
        "Organisations using AI in at least one function, 2025",
        "% of respondents to McKinsey's online survey, by region, as published in the AI Index 2026",
        [('*Europe', 91), ('North America', 90), ('All regions', 88), ('Greater China', 88),
         ('Developing markets', 88), ('Asia-Pacific', 82)],
    ),
    "mckinsey-jobs": (
        "AI and head count: expected and reported change",
        "% of respondents whose organisation regularly uses AI, global",
        [('Expect a decline next year, 2025 survey', 32), ('*Expect a decline next year, 2026 survey', 39),
         ('Expect little or no change next year, 2026 survey', 43), ('Report a decline over the past year, 2026 survey', 14)],
    ),
    # National surveys
    "ifo-trend": (
        "German firms using AI in their business processes",
        "% of firms, ifo Business Survey",
        [('2023', 13.3), ('2024', 27), ('2025', 40.9), ('*2026', 54.5)],
    ),
    "bundesbank-genai": (
        "German firms using or planning to use generative AI",
        "% of firms, firm-weighted; all three years asked in Q2 2025",
        [('2024', 26), ('*2025', 44), ('2026', 56)],
    ),
    "bdi-trend": (
        "Italian firms using AI",
        "% of firms with 20+ employees",
        [('2024', 13), ('Start of 2025', 27), ('*Start of 2026', 32)],
    ),
    "bdf-use": (
        "French firms using AI, early 2026",
        "% of firms with 20+ employees",
        [('*Generative AI', 67), ('Non-generative AI', 35), ('Generative AI, 20-49 employees', 64), ('Generative AI, 1,000+ employees', 83)],
    ),
    "bde-use": (
        "Spanish firms using AI, late 2024",
        "% of firms",
        [('*Any AI', 19.9), ('Generative AI', 18.1), ('Predictive AI', 14.6)],
    ),
    "iab-size": (
        "German establishments using generative AI, 2025",
        "% of establishments, by number of employees",
        [('*All', 24), ('1-9', 21), ('10-49', 28), ('50-199', 38), ('200+', 48)],
    ),
    "diwabe": (
        "How often German employees work with AI programs, 2024",
        "% of employees aged 16-65",
        [('Never', 35.7), ('Rarely or sometimes', 44.8), ('*Often or always', 19.6)],
    ),
    "austria": (
        "Generative AI use in Austria, last three months",
        "% of people aged 16-74",
        [('2024', 28.0), ('*2025', 39.4), ('Employed people, 2025', 43.2), ('Aged 16-24, 2025', 73.2)],
    ),
    "cbs-work": (
        "Dutch workers using AI for their work, 2025",
        "% of adults in paid work",
        [('*All', 42.9), ('Higher education', 55.5), ('Medium education', 32.0), ('Lower education', 19.7)],
    ),
    "tno-wea": (
        "Dutch employers using algorithms, AI or big data, 2024",
        "% of establishments with 5+ employees",
        [('*All', 12.8), ('5-9 employees', 10.5), ('10-49', 11.8), ('50-99', 26.4), ('100+', 27.2)],
    ),
    "humlum": (
        "Danish workers in AI-exposed occupations using ChatGPT for work",
        "% of workers in 11 occupations",
        [('Late 2023', 39.8), ('*Late 2024', 49.1)],
    ),
    "etla": (
        "Generative AI use in Finland, October 2024",
        "% of group",
        [('Have used generative AI (all aged 18-79)', 47), ('*Have used it for work (people in work)', 29), ('Use it weekly (people in work)', 11)],
    ),
    "tem-barometer": (
        "AI at Finnish workplaces, autumn 2025",
        "% of wage earners; last two bars: % of those whose workplace uses AI",
        [('*AI is used at their workplace', 45), ('Of those: AI improved their own efficiency', 45), ('Of those: AI replaced some work tasks', 18)],
    ),
    "nbp": (
        "Polish enterprises using AI tools",
        "% of surveyed non-financial enterprises; large firms over-represented",
        [('Q4 2024', 13.7), ('*Q2 2026', 42), ('Large firms, Q2 2026', 59), ('Medium-sized firms, Q2 2026', 43),
         ('Small and micro firms, Q2 2026', 28)],
    ),
    "bopf-2026": (
        "German firms using at least one AI technology, 2026",
        "% of firms, employment-weighted",
        [('January 2026', 65), ('*July 2026', 78)],
    ),
    "insee-tic": (
        "French enterprises using AI",
        "% of enterprises with 10+ employees",
        [('2023', 6), ('2024', 10), ('*2025', 18), ('10-49 employees, 2025', 15), ('50-249, 2025', 31), ('250+, 2025', 58)],
    ),
    "sige-ai": (
        "How important is AI to Italian firms? Q3 2024",
        "% of firms with 50+ employees in industry and non-financial services",
        [('*Important and already adopting it', 11.2), ('Important, plan to adopt within 2 years', 28.4),
         ('Not important for the business', 33.4), ("Don't know or no answer", 26.9)],
    ),
    "bdi-households": (
        "Generative AI use in Italy, August-September 2024",
        "% of respondents to the Bank of Italy household survey",
        [('*Used it in the past 12 months', 26), ('Use it at least weekly', 10),
         ('Workers and retirees: used it in the past 12 months', 36), ('Workers and retirees: use it at least weekly', 13)],
    ),
    "statbel-ent": (
        "Belgian enterprises using AI",
        "% of enterprises with 10+ persons employed",
        [('2023', 13.8), ('2024', 24.7), ('*2025', 34.5), ('Brussels, 2025', 42.3), ('Flanders, 2025', 34.8), ('Wallonia, 2025', 30.2)],
    ),
    "statbel-ind": (
        "Generative AI use in Belgium, 2025",
        "% of people aged 16-74 (unless stated), last 3 months",
        [('*All', 42.0), ('Brussels', 47.1), ('Flanders', 43.5), ('Wallonia', 37.5),
         ('Workers', 48.5), ('Aged 16-24', 74.4), ('Aged 65-74', 11.7)],
    ),
    "dst-ent": (
        "Danish enterprises using AI",
        "% of enterprises with 10+ employees, reference month January",
        [('2023', 15), ('2024', 28), ('2025', 42), ('*2026', 59), ('AI to produce written text or speech, 2026', 44)],
    ),
    "dst-ind": (
        "AI use in Denmark, by situation",
        "% of residents aged 16+",
        [('In connection with work, 2024', 21), ('*In connection with work, 2025', 27),
         ('Private purposes, 2025', 34), ('Use it daily, 2025', 11)],
    ),
    # EU surveys added from the wider search
    "dd-use": (
        "Use of generative AI tools, early 2026",
        "% of people aged 15+, EU",
        [('*In personal life or for work or studies', 61), ('In personal life', 59), ('For work or studies', 49), ('At least weekly, personal life', 43), ('At least weekly, work or studies', 39)],
    ),
    "dd-age": (
        "Use of generative AI in personal life, by age",
        "% of age group, EU",
        [('Aged 15-24', 87), ('Aged 55+', 34)],
    ),
    "osh-pulse": (
        "Digital technologies used for the main job, April 2025",
        "% of workers, EU",
        [('*Software or tools powered by AI', 18), ('Machines or robots that think and decide', 6), ('Any advanced digital technology', 32), ('Tasks or shifts allocated automatically', 27)],
    ),
    "eibis26": (
        "Firms using generative AI, 2026",
        "% of firms",
        [('*European Union', 67), ('United States', 71), ('EU SMEs', 58), ('EU large firms', 74)],
    ),
    "esener": (
        "Digital technologies used in establishments, 2024",
        "% of establishments with 5+ employees, EU",
        [('*Machines, systems or computers that use AI', 7), ('Automatic allocation of tasks or shifts', 9), ("Monitoring of workers' performance", 7), ('AI, information and communication sector', 21)],
    ),
    "fl559": (
        "Enterprises that have adopted AI, early 2025",
        "% of enterprises, EU",
        [('*All SMEs (1-249 employees)', 14), ('Micro (1-9)', 14), ('Small (10-49)', 12), ('Medium (50-249)', 13), ('Large (500+)', 24), ('Startups', 21)],
    ),
    "eurostat-ind-nouse": (
        "Main reason for not using generative AI, 2025",
        "% of people aged 16-74 who did not use it in the last 3 months, EU",
        [('*No need', 64.3), ('Did not know how to use them', 13.8), ('Did not know they existed', 8.5),
         ('Concerns about privacy, security or safety', 7.3), ('Other', 5.4)],
    ),
    "oecd-sme": (
        "SMEs where someone uses generative AI for work, late 2024",
        "% of SMEs (1-249 employees)",
        [('*All 7 countries', 31), ('Germany', 38.7), ('Austria', 34.1), ('Ireland', 33.0),
         ('One-person firms, 7 countries', 23.6), ('50-249 employees, 7 countries', 45.8)],
    ),
}


def bar_chart(name, title, unit, rows):
    """Label-above-bar chart: rounded bars on a pale 0-100% track."""
    n = len(rows)
    pitch, head = 0.56, 0.78                      # inches per row, inches for title block
    height = head + pitch * n + 0.05
    fig = plt.figure(figsize=(6.6, height))
    ax = fig.add_axes([0.012, 0.0, 0.976, (pitch * n + 0.05) / height])
    ax.set_xlim(0, 100)
    ax.set_ylim(n - 0.42, -0.72)
    ax.axis("off")
    for i, (label, value) in enumerate(rows):
        star = label.startswith("*")
        label = label.lstrip("*")
        colour = HIGHLIGHT if star else ACCENT
        ax.plot([1.2, 98.8], [i, i], color=TRACK, lw=9, solid_capstyle="round", zorder=1)
        ax.plot([1.2, max(value - 1.2, 1.21)], [i, i], color=colour, lw=9, solid_capstyle="round", zorder=2)
        ax.text(0, i - 0.36, label, ha="left", va="center", fontsize=10.5, color=INK)
        ax.text(100, i - 0.36, f"{value:g}%", ha="right", va="center", fontsize=11.5,
                fontweight="bold", color=colour)
    fig.text(0.012, 1 - 0.20 / height, title, fontsize=13, fontweight="bold", color=ACCENT, va="center")
    fig.text(0.012, 1 - 0.47 / height, unit, fontsize=9.5, color=MUTED, va="center")
    fig.savefig(OUT / f"{name}.svg", transparent=True)
    plt.close(fig)


def survey_points():
    """Read month / adoption fields from the YAML header of every survey page."""
    points = []
    for path in sorted(ROOT.glob("surveys/*/*.qmd")):
        text = path.read_text(encoding="utf8")
        meta = yaml.safe_load(text.split("---")[1])
        if not meta.get("month"):
            continue
        base = {
            "label": meta.get("chart-label", meta["title"]),
            "coverage": meta.get("coverage", "eu27"),
            "series": meta.get("series"),
            "pos": meta.get("label-pos"),
            # link from the overview page to this survey's page
            "url": path.relative_to(ROOT).with_suffix(".html").as_posix(),
        }
        waves = [{"month": meta["month"], "workers": meta.get("adoption-workers"),
                  "firms": meta.get("adoption-firms"), "individuals": meta.get("adoption-individuals")}]
        waves += meta.get("earlier-waves", [])        # earlier waves documented on the same page
        for wave in waves:
            year, month = str(wave["month"]).split("-")
            for kind in KINDS:
                if wave.get(kind) is not None:
                    points.append({**base, "kind": kind, "value": float(wave[kind]),
                                   "when": date(int(year), int(month), 15)})
    return points


# One colour per population, matching the pills on the survey pages
KINDS = {
    "individuals": ("#5b47a8", "AI use by individuals", "% of people using AI for any purpose"),
    "workers": ("#1d7a4a", "AI use by workers", "% of workers using AI for their job"),
    "firms": ("#c9731a", "AI use by firms", "% of firms using AI"),
}


# Marker per country coverage: (marker, filled, legend label)
COVERAGE = {
    "eu27": ("o", True, "EU-27"),
    "euro-area": ("D", False, "Euro area"),
    "eu-subset": ("s", False, "10+ EU countries"),
    "few": ("^", False, "Under 10 countries"),
}


def timeline(kind, points):
    colour, title, unit = KINDS[kind]
    fig, ax = plt.subplots(figsize=(7.4, 5.0))
    fig.subplots_adjust(left=0.07, right=0.98, top=0.84, bottom=0.085)
    top = max(p["value"] for p in points)
    ax.set_ylim(0, 10 * (int(top * 1.18) // 10 + 1))
    ax.set_xlim(date(2024, 1, 1), date(2027, 5, 31))

    # Line joining, in date order, the waves of one survey (same `series` in the page header).
    # Different surveys are never joined: their definitions and populations differ.
    for series in sorted({p["series"] for p in points if p["series"]}):
        group = sorted((p for p in points if p["series"] == series), key=lambda p: p["when"])
        if len(group) > 1:
            ax.plot([p["when"] for p in group], [p["value"] for p in group], color=colour, lw=2.4,
                    alpha=0.4, solid_capstyle="round", solid_joinstyle="round", zorder=2)

    # Linear trend fitted through every dot on the chart (ordinary least squares, each
    # survey wave counted once), so it is visible which surveys sit above or below it.
    has_trend = len(points) >= 3
    if has_trend:
        days = [p["when"].toordinal() for p in points]
        slope, intercept = np.polyfit(days, [p["value"] for p in points], 1)
        ends = [min(days) - 45, max(days) + 45]
        ax.plot([date.fromordinal(d) for d in ends], [slope * d + intercept for d in ends],
                color=MUTED, lw=1.6, linestyle=(0, (5, 4)), alpha=0.8, zorder=1)

    offsets = {"right": (10, 0), "above": (-6, 14), "below": (-6, -15)}
    for p in points:
        marker, filled, _ = COVERAGE[p["coverage"]]
        # Each dot and its label link to the survey's page (works because the SVG is inlined)
        ax.scatter(p["when"], p["value"], s=150 if marker == "o" else 120, marker=marker, zorder=3,
                   linewidths=2.4, edgecolors="white" if filled else colour,
                   facecolors=colour if filled else "white", urls=[p["url"]])
        # Labels sit above the dot (survey name on its latest wave only);
        # label-pos in the page header overrides this.
        text = f"{p['label']}  {p['value']:g}%"
        if p["series"]:
            latest = max(q["when"] for q in points if q["series"] == p["series"])
            if p["when"] != latest:
                text = f"{p['value']:g}%"
        ax.annotate(text, (p["when"], p["value"]), textcoords="offset points",
                    xytext=offsets[p["pos"] or "above"],
                    ha="left", va="center", fontsize=10, color=INK, url=p["url"])

    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.xaxis.set_minor_locator(mdates.MonthLocator(bymonth=(4, 7, 10)))
    for label in ax.get_xticklabels():
        label.set_horizontalalignment("left")
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:g}%")
    ax.grid(axis="y", color="#dde3ea", lw=0.9, linestyle=(0, (2, 4)))
    ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color("#c5ccd4")
    ax.tick_params(axis="both", which="major", length=0, labelsize=9.5, labelcolor=MUTED, pad=5)
    ax.tick_params(axis="x", which="minor", length=3, color="#c5ccd4")

    fig.text(0.5, 0.955, title, fontsize=17, fontweight="bold", color=colour, va="center", ha="center")
    present = {p["coverage"] for p in points}
    handles = [
        Line2D([], [], marker=marker, ls="", ms=9 if filled else 8, mew=0 if filled else 2.2,
               mec=colour, mfc=colour if filled else "white", label=label)
        for key, (marker, filled, label) in COVERAGE.items() if key in present
    ]
    if has_trend:
        handles.append(Line2D([], [], color=MUTED, lw=1.6, linestyle=(0, (5, 4)), alpha=0.8,
                              label="Linear trend, all surveys"))
    fig.legend(handles=handles, loc="center", bbox_to_anchor=(0.5, 0.890), ncol=len(handles), frameon=False,
               fontsize=9.5, labelcolor=MUTED, handletextpad=0.2, columnspacing=1.6)
    target = OUT / f"adoption-{kind}.svg"
    fig.savefig(target, transparent=True)
    plt.close(fig)
    # Inline copy for the overview page: links inside an <img> are not clickable,
    # so the page embeds the SVG markup itself.
    svg = target.read_text(encoding="utf8")
    svg = svg[svg.index("<svg"):]
    svg = re.sub(r'<svg ([^>]*?)width="[^"]*" height="[^"]*"',
                 r'<svg \1class="adoption-chart" role="img" aria-label="%s"' % title, svg, count=1)
    (OUT / f"adoption-{kind}.inline.html").write_text(svg, encoding="utf8")


if __name__ == "__main__":
    for old in OUT.glob("*.svg"):
        old.unlink()
    for name, (title, unit, rows) in FIGURES.items():
        bar_chart(name, title, unit, rows)
    points = survey_points()
    for kind in KINDS:
        timeline(kind, [p for p in points if p["kind"] == kind])
    print(f"wrote {len(FIGURES) + len(KINDS)} figures to {OUT}")
