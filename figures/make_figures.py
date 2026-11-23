"""Draws all charts on the site.

Run from the repository root:  python figures/make_figures.py

1. Result charts for the survey pages: one entry in FIGURES per chart.
2. The three adoption time series on the overview page (individuals, workers,
   firms), written as plain SVG (figures/adoption-*.inline.html) and styled in styles.css. These are built from the YAML header of every survey page (fields:
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
import matplotlib.pyplot as plt
import yaml

# European Commission palette: blue, EU flag yellow, light grey, dark grey
EC_BLUE, EC_YELLOW, EC_GREY_LIGHT, EC_GREY_DARK = "#004494", "#FFCC00", "#C5C6C8", "#646567"
ACCENT = EC_BLUE        # site blue
HIGHLIGHT = EC_YELLOW   # headline bar
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
        "% of people aged 16-74, EU, last 3 months; several purposes possible",
        [("Any purpose", 32.7), ("Private", 25.5), ("Work", 15.4), ("*Work, employed people aged 25-64", 21.9), ("Formal education", 9.3)],
    ),
    "eurostat-ind-age": (
        "Use of generative AI tools, by age, 2025",
        "% of age group, EU, any purpose, last 3 months",
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
        "% of managers and employees; use not limited to work",
        [("*Ever used or been involved with AI (2025)", 78), ("Same question (2024)", 72),
         ("Positive attitude towards AI (2025)", 70)],
    ),
    "deloitte-use": (
        "Generative AI: awareness and use, mid-2024",
        "% of people aged 16-75, 11 European countries, any purpose",
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
        "% of people aged 16-74, any purpose",
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
        "% of respondents to the Bank of Italy household survey, any purpose",
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
        "% of people aged 16-74 (unless stated), any purpose, last 3 months",
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
        # Yellow is too light for text, so the headline value is printed in ink
        ax.text(100, i - 0.36, f"{value:g}%", ha="right", va="center", fontsize=11.5,
                fontweight="bold", color=INK if star else colour)
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
            "title": meta["title"],
            "where": meta.get("where", ""),
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
    "individuals": (EC_BLUE, "AI use by individuals", "% of people using AI for any purpose"),
    "workers": (EC_YELLOW, "AI use by workers", "% of workers using AI for their job"),
    "firms": (EC_GREY_DARK, "AI use by firms", "% of firms using AI"),
}


# Marker per country coverage: (marker, filled, legend label)
COVERAGE = {
    "eu27": ("o", True, "EU-27"),
    "euro-area": ("D", False, "Euro area"),
    "eu-subset": ("s", False, "10+ EU countries"),
    "few": ("^", False, "Under 10 countries"),
}


def timeline(kind, points):
    """Overview time series, drawn twice: a compact version and a wide, flatter one for big
    screens. styles.css shows one or the other, so labels stay the same size at any width."""
    svgs = [timeline_svg(kind, points, 900, 380, "compact"), timeline_svg(kind, points, 1300, 430, "wide")]
    (OUT / f"adoption-{kind}.inline.html").write_text("\n".join(svgs), encoding="utf8")


def timeline_svg(kind, points, W, H, variant):
    """One overview time series as plain SVG, so that text uses the page font,
    dots link to the survey pages and show a tooltip, and the chart scales with the page."""
    colour, title, unit = KINDS[kind]
    left, right, top, bottom = 40, 110, 40, 32          # plot margins; labels may run into the right margin
    x0, x1 = date(2024, 1, 1).toordinal(), date(2027, 1, 1).toordinal()
    ymax = 10 * (int(max(p["value"] for p in points) * 1.15) // 10 + 1)
    pw, ph = W - left - right, H - top - bottom
    X = lambda d: left + (d.toordinal() - x0) / (x1 - x0) * pw
    Y = lambda v: top + ph - v / ymax * ph
    esc = lambda t: str(t).replace("&", "&amp;").replace("<", "&lt;").replace('"', "&quot;")
    out = [f'<svg viewBox="0 0 {W} {H}" class="adoption-chart chart-{kind} chart-{variant}" role="img" '
           f'aria-label="{esc(title)}" xmlns="http://www.w3.org/2000/svg" style="--c:{colour}">']

    # Year written under the middle of each year
    for year in range(2024, 2027):
        a, b = X(date(year, 1, 1)), X(date(year + 1, 1, 1))
        out.append(f'<text class="axis year" x="{(a + b) / 2:.1f}" y="{H - 8}">{year}</text>')
    # Horizontal gridlines; the % sign only on the top label
    step = 10 if ymax <= 60 else 20
    for v in range(0, ymax + 1, step):
        out.append(f'<line class="grid{" base" if v == 0 else ""}" x1="{left}" x2="{left + pw}" '
                   f'y1="{Y(v):.1f}" y2="{Y(v):.1f}"/>')
        out.append(f'<text class="axis ytick" x="{left - 8}" y="{Y(v) + 4:.1f}">{v}{"%" if v == ymax - ymax % step else ""}</text>')

    # Linear trend through every dot (each survey wave counted once)
    if len(points) >= 3:
        days = [p["when"].toordinal() for p in points]
        slope, intercept = np.polyfit(days, [p["value"] for p in points], 1)
        d0, d1 = min(days) - 45, max(days) + 45
        ya, yb = Y(slope * d0 + intercept), Y(slope * d1 + intercept)
        xa, xb = X(date.fromordinal(d0)), X(date.fromordinal(d1))
        out.append(f'<line class="trend" x1="{xa:.1f}" y1="{ya:.1f}" x2="{xb:.1f}" y2="{yb:.1f}"/>')

    # Lines joining the waves of one survey (same `series`); different surveys are never joined
    for series in sorted({p["series"] for p in points if p["series"]}):
        group = sorted((p for p in points if p["series"] == series), key=lambda p: p["when"])
        if len(group) > 1:
            path = " ".join(f"{'M' if i == 0 else 'L'}{X(p['when']):.1f},{Y(p['value']):.1f}"
                            for i, p in enumerate(group))
            out.append(f'<path class="series" d="{path}"/>')

    # Dots with labels: survey name in grey, value in bold. Name only on the latest wave of a series.
    offsets = {"right": (12, 4, "start"), "above": (0, -14, "middle"), "below": (0, 22, "middle")}
    for p in sorted(points, key=lambda p: p["when"]):
        x, y = X(p["when"]), Y(p["value"])
        marker, filled, cov = COVERAGE[p["coverage"]]
        cls = "dot filled" if filled else "dot hollow"
        if marker == "o":
            shape = f'<circle class="{cls}" cx="{x:.1f}" cy="{y:.1f}" r="7"/>'
        elif marker == "s":
            shape = f'<rect class="{cls}" x="{x - 6:.1f}" y="{y - 6:.1f}" width="12" height="12" rx="1.5"/>'
        else:
            shape = (f'<path class="{cls}" d="M{x:.1f},{y - 7.5:.1f} L{x + 7:.1f},{y + 5:.1f} '
                     f'L{x - 7:.1f},{y + 5:.1f} Z"/>')
        name = p["label"]
        if p["series"] and p["when"] != max(q["when"] for q in points if q["series"] == p["series"]):
            name = ""
        dx, dy, anchor = offsets[p["pos"] or "above"]
        label = (f'<tspan class="name">{esc(name)} </tspan>' if name else "") + f'<tspan class="val">{p["value"]:g}%</tspan>'
        tip = f'{p["title"]}, {p["when"]:%B %Y}: {p["value"]:g}% ({p["where"]})'
        out.append(f'<a href="{p["url"]}" class="point"><title>{esc(tip)}</title>{shape}'
                   f'<text class="label" x="{x + dx:.1f}" y="{y + dy:.1f}" text-anchor="{anchor}">{label}</text></a>')

    # Legend: coverage only, top left
    lx = left
    for key, (marker, filled, text) in COVERAGE.items():
        if key not in {p["coverage"] for p in points}:
            continue
        cls = "dot filled" if filled else "dot hollow"
        cy = 16
        if marker == "o":
            out.append(f'<circle class="{cls} key" cx="{lx + 5}" cy="{cy}" r="5"/>')
        elif marker == "s":
            out.append(f'<rect class="{cls} key" x="{lx}" y="{cy - 5}" width="10" height="10" rx="1"/>')
        else:
            out.append(f'<path class="{cls} key" d="M{lx + 5},{cy - 6} L{lx + 10.5},{cy + 4} L{lx - 0.5},{cy + 4} Z"/>')
        out.append(f'<text class="legend" x="{lx + 16}" y="{cy + 4}">{text}</text>')
        lx += 32 + 7.4 * len(text)
    out.append("</svg>")
    return "\n".join(out)


def overview_stats(points):
    """Opening lines of the overview page: the range of estimates from the surveys fielded in the
    latest year, one bullet each for individuals, workers and firms (bullets in the chart colours)."""
    rows, years = [], set()
    who = {"individuals": "of people", "workers": "of workers", "firms": "of firms"}
    for kind in KINDS:
        group = [p for p in points if p["kind"] == kind]
        year = max(p["when"].year for p in group)
        latest = [p for p in group if p["when"].year == year]
        lo, hi = round(min(p["value"] for p in latest)), round(max(p["value"] for p in latest))
        text = f"{lo}%" if lo == hi else f"{lo} to {hi}%"
        rows.append(f'<li class="fig-{kind}"><span><a class="fig" href="#{kind}">{text}</a> {who[kind]}</span></li>')
        years.add(year)
    year = " and ".join(str(y) for y in sorted(years))
    html = (f'<div class="lede"><p>Surveys fielded in {year} put the share using AI at:</p>'
            f'<ul class="lede-list">{"".join(rows)}</ul>'
            "<p>These ranges are wide, because each survey makes different choices when defining:</p>"
            '<ul class="lede-list lede-list-plain"><li><span>artificial intelligence tools</span></li><li><span>adoption and intensity</span></li>'
            "<li><span>the target population</span></li>"
            "<li><span>&hellip;</span></li></ul></div>")
    (OUT / "overview-stats.inline.html").write_text(html, encoding="utf8")


EU_COUNTRIES = {  # Eurostat codes (EL = Greece)
    "BE": "Belgium", "BG": "Bulgaria", "CZ": "Czechia", "DK": "Denmark", "DE": "Germany", "EE": "Estonia",
    "IE": "Ireland", "EL": "Greece", "ES": "Spain", "FR": "France", "HR": "Croatia", "IT": "Italy",
    "CY": "Cyprus", "LV": "Latvia", "LT": "Lithuania", "LU": "Luxembourg", "HU": "Hungary", "MT": "Malta",
    "NL": "Netherlands", "AT": "Austria", "PL": "Poland", "PT": "Portugal", "RO": "Romania", "SI": "Slovenia",
    "SK": "Slovakia", "FI": "Finland", "SE": "Sweden",
}
EURO_AREA = ["AT", "BE", "HR", "CY", "EE", "FI", "FR", "DE", "EL", "IE", "IT", "LV", "LT", "LU", "MT",
             "NL", "PT", "SK", "SI", "ES"]   # 20 members in 2024-25


def pops(asked, use):
    """Who a survey covers, for the sidebar dot and filter: the groups named in `asked`, plus
    workers when a survey of individuals also asks about use at work (`use: both`)."""
    out = [k for k in ("individuals", "workers", "firms") if k in asked]
    if "individuals" in out and use == "both" and "workers" not in out:
        out.insert(1, "workers")
    return out


def survey_index():
    """Every EU survey page: title, year, page path, who was asked, EU countries covered."""
    out = []
    for path in sorted(ROOT.glob("surveys/*/*.qmd")):
        meta = yaml.safe_load(path.read_text(encoding="utf8").split("---")[1])
        asked = str(meta.get("asked", "")).lower()
        cov = meta.get("countries", "eu27")
        codes = (list(EU_COUNTRIES) if cov == "eu27" else EURO_AREA if cov == "euro-area" else list(cov))
        unknown = set(codes) - set(EU_COUNTRIES)
        if unknown:
            raise ValueError(f"{path}: unknown country codes {sorted(unknown)}")
        out.append({"title": meta["title"], "year": path.parent.name,
                    "url": path.relative_to(ROOT).with_suffix(".html").as_posix(),
                    "pops": pops(asked, meta.get("use")),
                    "countries": codes})
    return out


def country_pages():
    """Country pages (countries/*.qmd): EU country code -> page path and number of national surveys."""
    pages = {}
    for path in sorted(ROOT.glob("countries/*.qmd")):
        text = path.read_text(encoding="utf8")
        code = yaml.safe_load(text.split("---")[1]).get("country")
        if code not in EU_COUNTRIES:
            raise ValueError(f"{path}: `country` must be an EU country code, not {code!r}")
        pages[code] = {"url": path.relative_to(ROOT).with_suffix(".html").as_posix(), "stem": path.stem,
                       "n": text.count("{.survey-entry")}
    return pages


def sidebar_data(surveys, pages):
    """Data for the sidebar script (includes/sidebar.html): for each survey page, who was asked
    and which EU countries it covers; the EU countries; and the countries with their own page."""
    import json
    data = {"surveys": {s["url"]: {"pops": s["pops"], "countries": s["countries"]} for s in surveys},
            "countries": sorted(EU_COUNTRIES.items(), key=lambda kv: kv[1]),
            "national": {code: page["url"] for code, page in pages.items()}}
    (ROOT / "includes" / "sidebar-data.html").write_text(
        "<script>window.SIDEBAR_DATA = " + json.dumps(data) + ";</script>", encoding="utf8")


def country_grid(surveys, pages):
    """Index of the country evidence page: one tile per EU country, each linking to its page."""
    tiles = []
    for code, name in sorted(EU_COUNTRIES.items(), key=lambda kv: kv[1]):
        page = pages.get(code)
        if not page:
            raise ValueError(f"no page in countries/ for {name} ({code})")
        n_eu = sum(code in s["countries"] for s in surveys)
        n = page["n"]
        count = f'{n} national survey{"s" if n != 1 else ""}' if n else "No national surveys yet"
        tiles.append(f'<a class="country-tile{" has-national" if n else ""}" href="{page["url"]}">'
                     f'<span class="ct-name">{name}</span><span class="ct-count">{count}</span>'
                     f'<span class="ct-eu">{n_eu} EU-wide surveys</span></a>')
    (OUT / "country-grid.inline.html").write_text('<div class="country-grid">' + "".join(tiles) + "</div>",
                                                encoding="utf8")


def company_surveys():
    """Company surveys and the EU countries they cover, from the `companies` field in the header of
    company-surveys.qmd. `countries` is a list of EU codes, or "eu27"; `notes` gives a country's
    own figure where the source publishes one."""
    meta = yaml.safe_load((ROOT / "company-surveys.qmd").read_text(encoding="utf8").split("---")[1])
    out = []
    for c in meta.get("companies", []):
        cov = c.get("countries") or []
        codes = list(EU_COUNTRIES) if cov == "eu27" else list(cov)
        unknown = set(codes) - set(EU_COUNTRIES) - {"none"}
        if unknown:
            raise ValueError(f"company-surveys.qmd, {c['name']}: unknown country codes {sorted(unknown)}")
        out.append({**c, "countries": codes, "notes": c.get("notes") or {}})
    return out


def country_coverage(surveys, pages, companies):
    """For each country page: the EU-wide surveys and the company surveys that cover the country
    (includes/coverage/<page>.html)."""
    folder = ROOT / "includes" / "coverage"
    folder.mkdir(parents=True, exist_ok=True)
    for old in folder.glob("*.html"):
        old.unlink()
    for code, page in pages.items():
        name = EU_COUNTRIES[code]
        covering = [s for s in surveys if code in s["countries"]]
        items = "".join(
            f'<li><a href="../{s["url"]}" class="cov-link {" ".join("pop-" + p for p in s["pops"])}">'
            f'{s["title"]}</a> <span class="cov-year">{s["year"]}</span></li>'
            for s in sorted(covering, key=lambda s: (-int(s["year"]), s["title"])))
        html = (f'<section class="coverage"><h2>EU-wide surveys covering {name}</h2>'
                f'<p class="coverage-note">{len(covering)} of the {len(surveys)} EU survey pages include {name}. '
                'The dot shows who was asked: <span class="key key-individuals"></span>individuals, '
                '<span class="key key-workers"></span>workers, <span class="key key-firms"></span>firms.</p>'
                f'<ul class="coverage-list">{items}</ul></section>')
        mine = [c for c in companies if code in c["countries"]]
        if mine:
            rows = "".join(
                f'<li><a href="../company-surveys.html#{c["anchor"]}">{c["name"]}</a>'
                f' <span class="cov-year">{c["company"]}, {c["year"]}</span>'
                + (f'<div class="cov-note">{c["notes"][code]}</div>' if code in c["notes"] else "")
                + "</li>"
                for c in mine)
            html += (f'<section class="coverage coverage-company"><h2>Company surveys covering {name}</h2>'
                     '<p class="coverage-note">Run or commissioned by private companies. Most use online panels '
                     'and loose definitions of "using AI" and publish little on method, so treat them with care; '
                     'they are not plotted on the overview.</p>'
                     f'<ul class="coverage-list company-list">{rows}</ul></section>')
        (folder / f'{page["stem"]}.html').write_text(html, encoding="utf8")


if __name__ == "__main__":
    for old in OUT.glob("*.svg"):
        old.unlink()
    for name, (title, unit, rows) in FIGURES.items():
        bar_chart(name, title, unit, rows)
    points = survey_points()
    for kind in KINDS:
        timeline(kind, [p for p in points if p["kind"] == kind])
    overview_stats(points)
    surveys, pages = survey_index(), country_pages()
    sidebar_data(surveys, pages)
    country_grid(surveys, pages)
    country_coverage(surveys, pages, company_surveys())
    print(f"wrote {len(FIGURES)} survey charts and {len(KINDS)} overview charts to {OUT}")
