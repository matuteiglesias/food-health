"""Offline, private visual atlas of canonical anthropometric measurements.

Reads the existing SQLite snapshot (never Google Sheets directly), generates
reproducible PNG charts plus a local HTML index. Nothing is uploaded or
published. Default charts use only actual observed measurements. Regressions
are clearly labeled descriptive/in-sample and never extrapolated.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from html import escape
import json
import os
from pathlib import Path
import re

METRICS = (
    "Weight", "Body Fat", "Muscle", "Neck", "Shoulder", "Chest",
    "Flexed", "Arm", "Forearm", "Waist", "Belly", "Hips",
    "Butt", "Butt#2", "Thigh", "Calf",
)
METRIC_LABELS = {
    "Weight": "Weight (kg)", "Body Fat": "Body Fat (%)",
    "Muscle": "Device muscle (%)",
    "Butt": "Butt [first source column]",
    "Butt#2": "Butt [second source column]",
}
RELATIONS = (
    ("Muscle", "Body Fat", 1),
    ("device_muscle_mass_kg", "fat_mass_kg", 1),
    ("device_muscle_mass_kg", "lean_body_mass_kg", 1),
    ("Weight", "Body Fat", 1),
    ("fat_mass_kg", "Waist", 2), ("fat_mass_kg", "Belly", 2),
    ("fat_mass_kg", "Hips", 2), ("fat_mass_kg", "Butt#2", 2),
    ("Body Fat", "Waist", 2), ("Body Fat", "Belly", 2),
    ("Body Fat", "Hips", 2), ("Body Fat", "Butt#2", 2),
    ("device_muscle_mass_kg", "Arm", 1),
    ("device_muscle_mass_kg", "Flexed", 1),
    ("Chest", "device_muscle_mass_kg", 1),
    ("Weight", "Waist", 2),
)


def _mpl():
    import matplotlib
    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    import numpy as np
    return plt, mdates, np


def _slug(value: str) -> str:
    return re.sub("[^a-z0-9]+", "-", value.lower()).strip("-")


def _label(metric: str) -> str:
    return METRIC_LABELS.get(metric, metric.replace("_", " ").title())


def _style(ax):
    ax.grid(alpha=0.18)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def _save(fig, folder: Path, filename: str):
    plt, _, _ = _mpl()
    path = folder / filename
    temporary = folder / ("." + filename + ".tmp.png")
    fig.savefig(temporary, dpi=134, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)
    return filename


def _line(ax, series, *, colour: str = "#0D7280", label: str = "Observed"):
    ax.scatter(series.dropna().index, series.dropna().values,
               s=14, alpha=0.55, c=colour, label=label, linewidths=0)
    _style(ax)


def _plot_gapped_line(ax, dates, values, *, max_gap_days=30, **kwargs):
    """Never visually connect observations separated by long missing periods."""
    import pandas as pd
    d = pd.to_datetime(dates)
    if len(d) != len(values):
        raise ValueError("Line dates and values must have equal length")
    if not len(d):
        return
    left = 0
    for right in range(1, len(d) + 1):
        if right == len(d) or (d[right] - d[right - 1]).days > max_gap_days:
            options = dict(kwargs)
            if left > 0:
                options["label"] = "_nolegend_"
            ax.plot(d[left:right], values[left:right], **options)
            left = right


def _rolling(ax, records, field: str):
    from .trends import rolling_observed_mean
    import pandas as pd
    trend = rolling_observed_mean(records, field, window_days=30, min_days=3)
    if trend:
        dates = pd.to_datetime([r["date"] for r in trend])
        means = [r["mean"] for r in trend]
        _plot_gapped_line(ax, dates, means, max_gap_days=30, color="#EF8A49",
                         lw=2, label="Trailing 30 days (observed days only)")


def _overview(folder, daily, records):
    plt, _, _ = _mpl()
    fields = ["Weight", "Waist", "Body Fat", "Muscle"]
    fig, axs = plt.subplots(2, 2, figsize=(14.5, 8.5), layout="constrained")
    for ax, col in zip(axs.ravel(), fields):
        if col in daily:
            _line(ax, daily[col]); _rolling(ax, records, col)
        ax.set_title(_label(col), loc="left", fontweight="bold")
        ax.set_xlabel("Date")
        ax.legend(loc="best", fontsize=8) if ax.has_data() else None
    fig.suptitle("Personal measurements | observed trajectories", fontsize=17, weight="bold")
    return _save(fig, folder, "overview.png")


def _coverage(folder, raw, fields):
    plt, mdates, np = _mpl()
    import pandas as pd
    period = pd.period_range(raw["date"].min().to_period("M"),raw["date"].max().to_period("M"),freq="M")
    if not len(period):
        return None
    grid=np.array([
        [int(((raw["date"].dt.to_period("M") == month)&raw[f].notna()).sum()) for month in period]
        for f in fields
    ],dtype=float)
    fig,ax=plt.subplots(figsize=(15,max(4,len(fields)*.38)),layout="constrained")
    im=ax.imshow(grid,aspect="auto",interpolation="nearest",cmap="Blues")
    ax.set_yticks(range(len(fields)),[_label(f) for f in fields],fontsize=9)
    ticks=list(range(0,len(period),max(1,len(period)//14)))
    ax.set_xticks(ticks,[str(period[t]) for t in ticks],rotation=45,ha="right")
    fig.colorbar(im,ax=ax,shrink=.73,label="Observed records per month")
    ax.set_title("Measurement coverage | blank ≠ zero",weight="bold",loc="left")
    return _save(fig,folder,"coverage.png")


def _field_chart(folder, daily, records, field: str, historical_goals=None):
    plt, mdates, np = _mpl()
    import pandas as pd
    values=daily[field].dropna()
    if len(values)<3:
        return None
    fig,axs=plt.subplots(3,1,figsize=(14,11.8),layout="constrained")
    _line(axs[0],values)
    _rolling(axs[0],records,field)
    if historical_goals is not None and field in historical_goals:
        axs[0].axhline(historical_goals[field], color="#7753A1", lw=1,
                       linestyle="--", label="Historical goal (opt-in, not current)")
    axs[0].legend(fontsize=8,loc="best")
    axs[0].set_title("Observation dates + trailing average (no filled days)",loc="left")
    # Sequential year-month boxes, last 24 *months with observations*.
    box_labels=sorted(set(values.index.to_period("M").astype(str)))[-24:]
    boxes=[values[values.index.to_period("M").astype(str)==month].tolist() for month in box_labels]
    axs[1].boxplot(boxes,positions=range(len(boxes)),patch_artist=True,
                   boxprops=dict(facecolor="#D3E5E8",edgecolor="#407481"),
                   medianprops=dict(color="#D97D40",linewidth=1.4))
    axs[1].set_xticks(range(len(box_labels)),box_labels,rotation=60,ha="right",fontsize=7)
    axs[1].set_title("Distribution by sequential month (latest 24 measured months)",loc="left")
    _style(axs[1])
    # Same calendar X across years; year-specific degree-2 fit uses only in-year points.
    for year,part in values.groupby(values.index.year):
        x=part.index.dayofyear
        axs[2].scatter(x,part.values,s=13,alpha=.52,label=str(year))
        if len(part)>=9 and len(set(x))>=8:
            coeff=np.polyfit(x,part.values,deg=2)
            axis=np.linspace(float(min(x)),float(max(x)),65)
            axs[2].plot(axis,np.polyval(coeff,axis),alpha=.76,lw=1)
    axs[2].set_xlabel("Day of year (leap years have shifted day-of-year indexing)")
    axs[2].set_title("Year-by-year comparison + descriptive within-year quadratic fits",loc="left")
    axs[2].legend(ncol=6,fontsize=8)
    _style(axs[2])
    fig.suptitle(f"{_label(field)} — {len(values)} measured days",fontsize=15,weight="bold")
    return _save(fig,folder,"metric-"+_slug(field)+".png")


def _body_comp(folder,daily):
    plt,_,_= _mpl()
    metrics=("Weight","Body Fat","Muscle","fat_mass_kg","lean_body_mass_kg","device_muscle_mass_kg")
    fig,axs=plt.subplots(3,2,figsize=(14,10.5),layout="constrained")
    for ax,name in zip(axs.ravel(),metrics):
        if name in daily and daily[name].notna().sum()>=3:
            _line(ax,daily[name],colour="#407E92")
        ax.set_title(_label(name),loc="left")
    fig.suptitle("Body composition | device estimates are derived, not directly measured mass",weight="bold")
    return _save(fig,folder,"body-composition.png")


def _ratios(folder,daily):
    plt,_,_=_mpl()
    names=("SWR","CWR","WHR_legacy_hips_over_waist")
    fig,ax=plt.subplots(figsize=(14,4.9),layout="constrained")
    for name in names:
        if name in daily and daily[name].notna().sum()>=3:
            v=daily[name].dropna()
            _plot_gapped_line(ax,v.index,v.values,max_gap_days=30,
                                 marker=".",lw=.9,alpha=.9,label=name)
    _style(ax);ax.legend(loc="best",fontsize=9)
    ax.set_title("Anthropometric proportions | WHR legacy = Hips / Waist (NOT clinical Waist / Hips)",
                 loc="left",weight="bold")
    return _save(fig,folder,"ratios.png")


def _weekly_and_change(folder,daily):
    from .plot_data import weekly_stats,two_month_changes
    plt,_,_=_mpl()
    fig,axs=plt.subplots(4,1,figsize=(14,12),layout="constrained")
    for ax,field in zip(axs[:2],("Weight","Waist")):
        if field in daily:
            weekly=weekly_stats(daily,field)
            ax.bar(weekly.index,weekly["change"],width=4,alpha=.65)
            ax.axhline(0,lw=1,color="#333")
        ax.set_title(f"{_label(field)} | week-to-week mean difference; weeks lacking measurements excluded",loc="left")
        _style(ax)
    for ax, bin_days in zip(axs[2:],(18,30)):
        if "Weight" in daily:
            values=two_month_changes(daily,bin_days=bin_days)
            ax.plot(values.index,values["delta_2bins"],marker="o",markersize=3,lw=1)
            ax.axhline(0,lw=1,color="#333")
        ax.set_title(f"Weight | 2 × {bin_days}-day bin difference (observed bins only)",loc="left")
        _style(ax)
    fig.suptitle("Change diagnostics | sampling varies over time",fontsize=15,weight="bold")
    return _save(fig,folder,"changes.png")


def _relationship(folder,daily,x,y,degree=1):
    from .plot_data import paired_frame,descriptive_fit
    plt,_,_= _mpl()
    pairs=paired_frame(daily,x,y,min_points=8)
    if pairs is None:
        return None
    fig,ax=plt.subplots(figsize=(7.6,5.7),layout="constrained")
    ax.scatter(pairs[x],pairs[y],s=15,alpha=.27,c="#5C7685",linewidths=0,
               label="Paired same-day observations")
    tail=pairs.tail(15)
    ax.scatter(tail[x],tail[y],s=30,alpha=.85,c="#D78B45",linewidths=0,
               label="Latest 15 paired observations")
    fit=descriptive_fit(pairs,x=x,y=y,degree=degree)
    if fit is not None:
        suffix="" if fit["r2"] is None else f" · in-sample R²={fit['r2']:.2f}"
        ax.plot(fit["x"],fit["y"],c="#244E68",lw=2,linestyle="--",
                label=f"In-range degree {degree} fit{suffix}")
    ax.set_xlabel(_label(x));ax.set_ylabel(_label(y))
    ax.set_title(f"{_label(y)} vs {_label(x)} · n={len(pairs)}",loc="left",weight="bold")
    ax.legend(fontsize=7,loc="best")
    _style(ax)
    return _save(fig,folder,"relationship-"+_slug(x)+"-"+_slug(y)+".png")


def _activity_plots(folder,activity_path):
    """Archive-only workout occurrence charts (never mislabeled as current)."""
    from .activity import load_legacy_activity, CHANNELS
    plt,_,np=_mpl()
    activity=load_legacy_activity(activity_path)
    weekly=activity.resample("W-SUN").sum()
    fig,axs=plt.subplots(2,1,figsize=(13.5,8),layout="constrained")
    for channel in CHANNELS:
        # A blank source week has no recorded activity; it is not verified
        # zero activity, so show a gap instead of a false zero-valued line.
        observed=weekly[channel].where(weekly[channel]>0)
        axs[0].plot(observed.index,observed.values,marker=".",linewidth=1,label=channel)
    axs[0].legend()
    axs[0].set_title("Weeks with activity recorded (blank weeks UNKNOWN; 2022–2023 only)",loc="left")
    _style(axs[0])
    marked=activity[activity["Resistance"]>0]
    if len(marked):
        dates=marked.index
        axs[1].scatter(dates,dates.dayofweek,s=22,c="#0D7280",marker="s",alpha=.75)
        axs[1].set_yticks(range(7),["Mon","Tue","Wed","Thu","Fri","Sat","Sun"])
        axs[1].set_xlabel("Historical calendar date")
    axs[1].set_title("Resistance recorded days by weekday (missing logs ≠ inactivity)",loc="left")
    _style(axs[1])
    fig.suptitle("Historical training activity | old volume.csv",fontsize=16,weight="bold")
    return _save(fig,folder,"historical-activity.png"),len(activity)


def _correlation_matrix(folder,daily,fields):
    plt,_,np=_mpl()
    cols=[f for f in fields if f in daily and daily[f].notna().sum()>=8]
    if len(cols)<3:
        return None
    corr=daily[cols].corr(min_periods=8).to_numpy()
    masked=np.ma.masked_invalid(corr)
    fig,ax=plt.subplots(figsize=(11,9),layout="constrained")
    image=ax.imshow(masked,cmap="coolwarm",vmin=-1,vmax=1,interpolation="nearest")
    ax.set_xticks(range(len(cols)),[_label(f) for f in cols],rotation=45,ha="right",fontsize=8)
    ax.set_yticks(range(len(cols)),[_label(f) for f in cols],fontsize=8)
    fig.colorbar(image,ax=ax,shrink=.7,label="Pearson r (paired measured dates only)")
    ax.set_title("Exploratory correlations | pairwise available dates, no causal inference",
                 loc="left",weight="bold")
    return _save(fig,folder,"correlation-matrix.png")


def _goals_chart(folder, comparison):
    plt,_,np=_mpl()
    fig,ax=plt.subplots(figsize=(11,max(4,len(comparison)*.42)),layout="constrained")
    names=[r["metric"] for r in comparison]
    pct=[100*(r["recent_mean"]-r["goal"])/r["goal"] for r in comparison]
    ax.barh(range(len(names)),pct,color="#75869c",alpha=.8)
    ax.set_yticks(range(len(names)),[_label(n) for n in names])
    ax.axvline(0,color="#222",lw=1)
    ax.set_xlabel("Recent observed mean relative to HISTORICAL goal (%)")
    ax.set_title("Legacy goals | explicit opt-in only; NOT current prescriptions",
                 loc="left",weight="bold")
    _style(ax)
    return _save(fig,folder,"historical-goals.png")


def _write_index(folder, sections, raw, daily, extra):
    # All report contents stay PRIVATE; local HTML only links relative PNG files.
    def group(label, items):
        if not items: return ""
        entries="".join(
            f'<article class="tile"><a href="{escape(filename,quote=True)}"><img loading="lazy" src="{escape(filename,quote=True)}" alt="{escape(title,quote=True)}"></a><div class="caption">{escape(title)}</div></article>'
            for title,filename in items
        )
        return f'<section><h2>{escape(label)} <small>{len(items)} plots</small></h2><div class="gallery">{entries}</div></section>'
    content="".join(group(title, items) for title,items in sections.items())
    is_enriched = extra.get("data_mode") == "enriched"
    report_title = "Measurement Atlas — Enriched" if is_enriched else "Measurement Atlas"
    report_intro = (
        "This local exploratory variant includes observed values AND model estimates "
        "of missing fields on the same dates. Estimated values are not measurements; "
        "no dates have been inserted."
        if is_enriched else
        "Rebuilt from the canonical Personal Measurements spreadsheet and private local SQLite. "
        "Every chart is generated from observed values unless explicitly labeled as derived "
        "or a descriptive in-sample regression."
    )
    report_notice = (
        "ENRICHED VIEW: all chart statistics, correlations and fits here combine "
        "direct measurements with conditional kernel estimates. PNG captions that "
        "say observed reflect the original chart code, but here may include estimates. "
        "These guesses are exploratory, not new direct readings or clinical measurements; "
        "the old scale's body-fat/muscle proxy is especially uncertain after 2023. "
        "No additional dates were created."
        if is_enriched else
        "Missing days are not zero. Trends use only measured days; within-day "
        "duplicates are averaged solely for plotting. Body composition percentages "
        "are instrument estimates, and fitted lines are descriptive, not predictions. "
        "Archive activity is not today's training record. These private files "
        "must not be uploaded to a public repository."
    )
    if is_enriched:
        content = '<div class="notice"><strong>Estimated field values included: '+str(extra.get("estimated_value_count", 0))+'</strong> — Please interpret apparent smoother trends and higher correlations cautiously: some data points were model-estimated.</div>' + content
    if extra.get("legacy_goals_comparison"):
        content = '<div class="notice"><strong>Historical goals enabled:</strong> targets were loaded from a private archived CSV. They are NOT current health, fitness or body-weight prescriptions.</div>' + content
    comparisons=extra.get("period_comparisons",[])
    yearly=extra.get("yearly_summary",[])
    def table_row(parts):
        return "<tr>"+"".join("<td>"+escape(str(part))+"</td>" for part in parts)+"</tr>"
    if comparisons:
        rows="".join(table_row([
            _label(row["metric"]),row["previous_observed_days"],
            row["current_observed_days"],f'{row["previous_mean"]:.2f}',
            f'{row["current_mean"]:.2f}',f'{row["change"]:+.2f}'
        ]) for row in comparisons)
        content+='<section><h2>Latest 90-day comparison</h2><p>Two consecutive 90-calendar-day windows ending at the last observed date. Means are computed only from measured dates; unequal counts can limit comparability.</p><div class="table-wrap"><table><thead><tr><th>Metric</th><th>Prior days</th><th>Recent days</th><th>Prior mean</th><th>Recent mean</th><th>Change</th></tr></thead><tbody>'+rows+'</tbody></table></div></section>'
    coverage=extra.get("observed_field_recency",[])
    if coverage:
        rows="".join(table_row([
            _label(item["metric"]),item["observed_rows"],
            item["last_observed_date"],item["days_behind_last_snapshot_observation"]
        ]) for item in coverage)
        content+='<section><details open><summary>Measurement coverage and recency by field</summary><p>Last recorded date varies by metric. Missing recent measurements are not evidence of unchanged values.</p><div class="table-wrap"><table><thead><tr><th>Metric</th><th>Observed rows</th><th>Latest recorded</th><th>Days before latest observation</th></tr></thead><tbody>'+rows+'</tbody></table></div></details></section>'
    if yearly:
        rows="".join(table_row([
            _label(row["metric"]),row["year"],row["observed_days"],
            f'{row["mean"]:.2f}',f'{row["first"]:.2f}',f'{row["last"]:.2f}'
        ]) for row in yearly)
        content+='<section><details><summary>Annual descriptive table (expand)</summary><div class="table-wrap"><table><thead><tr><th>Metric</th><th>Year</th><th>Days</th><th>Mean</th><th>First</th><th>Last</th></tr></thead><tbody>'+rows+'</tbody></table></div></details></section>'
    legacy=extra.get("legacy_goals_comparison",[])
    if legacy:
        rows="".join(table_row([
            _label(row["metric"]),row["observed_days"],
            f'{row["recent_mean"]:.2f}',f'{row["goal"]:.2f}',
            f'{row["gap"]:+.2f}',f'{row["forty_pct_step"]:.2f}'
        ]) for row in legacy)
        content+='<section><details><summary>OPT-IN historical goals comparison (not current targets)</summary><div class="table-wrap"><table><thead><tr><th>Metric</th><th>Days</th><th>Observed</th><th>Old goal</th><th>Gap</th><th>40% step (old formula)</th></tr></thead><tbody>'+rows+'</tbody></table></div></details></section>'
    first=raw["date"].min().date().isoformat()
    last=raw["date"].max().date().isoformat()
    html=f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Food · Health | {escape(report_title)}</title>
<style>
:root{{--ink:#22313d;--paper:#f5f7f7;--teal:#08737e;--muted:#647582}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font:15px/1.6 system-ui,-apple-system,Arial,sans-serif}}
header{{background:#123e4c;color:white;padding:40px max(5vw,20px)}}header h1{{font-size:clamp(30px,4vw,48px);margin:0}}
header p{{max-width:850px;color:#d2e1e4}}.stats{{display:flex;gap:24px;flex-wrap:wrap;margin-top:16px}}
.stat strong{{display:block;font-size:23px}}main{{max-width:1450px;padding:24px 3vw 80px;margin:auto}}
.notice{{padding:16px 21px;border-left:3px solid var(--teal);background:white;margin:12px 0 32px}}
section{{margin-top:44px}}h2{{border-bottom:1px solid #cad4d8;padding-bottom:10px;font-size:25px}}
small{{color:#72858b;font-weight:400;font-size:14px}}.gallery{{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,450px),1fr));gap:19px}}
.tile{{background:white;border:1px solid #dae0e2;border-radius:9px;overflow:hidden;box-shadow:0 4px 20px #253b440a}}
.tile img{{width:100%;display:block;object-fit:contain;max-height:490px;background:white}}
.caption{{font-size:14px;padding:9px 16px;color:#324e57}}
.table-wrap{{overflow:auto;background:white;padding:16px;border-radius:9px}}table{{border-collapse:collapse;width:100%;min-width:650px}}th,td{{text-align:left;border-bottom:1px solid #e0e5e7;padding:7px 12px}}th{{background:#e8f1f3}}details summary{{cursor:pointer;font-size:18px;font-weight:650;padding:12px}}footer{{color:#70848b;margin-top:40px}}
</style></head><body><header><h1>{escape(report_title)}</h1>
<p>{escape(report_intro)}</p>
<div class="stats"><div class="stat"><strong>{len(raw)}</strong>source observation rows</div>
<div class="stat"><strong>{len(daily)}</strong>unique calendar dates</div>
<div class="stat"><strong>{escape(first)} → {escape(last)}</strong>date coverage</div>
<div class="stat"><strong>{extra.get("chart_count",0)}</strong>charts</div></div></header>
<main><div class="notice"><strong>How to interpret</strong> — {escape(report_notice)}</div>
{content}
<footer>Generated locally {escape(extra["generated_utc"])} · No network request or source-sheet changes · Data and images remain in ignored .local/</footer></main></body></html>"""
    target=folder/"index.html"
    temporary=folder/".index.tmp"
    temporary.write_text(html,encoding="utf-8")
    os.chmod(temporary,0o600)
    os.replace(temporary,target)
    return target


def generate_dashboard(records, *, output_dir, height_m=None, activity_file=None, goals_file=None, data_mode="observed", estimated_value_count=0):
    """Generate rich, privacy-preserving HTML/PNG atlas from SQLite records."""
    if data_mode not in ("observed", "enriched"):
        raise ValueError("Unsupported report data mode")
    if type(estimated_value_count) is not int or estimated_value_count < 0:
        raise ValueError("Invalid estimated value count")
    from .plot_data import observed_frames,observation_counts
    plt,_,_=_mpl()
    plt.rcParams.update({
        "font.size": 10, "axes.titlesize": 11, "figure.facecolor": "white",
        "axes.labelcolor": "#34475a", "axes.edgecolor": "#c8d0d6",
    })
    output=Path(output_dir).expanduser().resolve()
    output.mkdir(parents=True,exist_ok=True,mode=0o700)
    os.chmod(output,0o700)
    previous_figures = set()
    previous_manifest = output / "manifest.json"
    if previous_manifest.is_file():
        try:
            prior = json.loads(previous_manifest.read_text(encoding="utf-8"))
            if prior.get("schema_version") == 1:
                previous_figures = {
                    item for group in prior.get("chart_sections", {}).values()
                    for item in group if isinstance(item, str)
                    and item.endswith(".png") and Path(item).name == item
                }
        except (ValueError, TypeError):
            pass  # No deletion without a valid previous provenance manifest.
    raw,daily=observed_frames(records,height_m=height_m)
    historical_goals=None
    comparison=[]
    if goals_file is not None:
        from .goals import load_goal_values,compare_goals
        historical_goals=load_goal_values(goals_file)["goals"]
        comparison=compare_goals(daily,historical_goals)
    observed_fields=[field for field in METRICS if field in raw and raw[field].notna().sum()>=3]
    sections=defaultdict(list)
    sections["Overview"].append(("Observed + estimated trajectories" if data_mode == "enriched" else "Observed trajectories",_overview(output,daily,records)))
    sections["Overview"].append(("Historical coverage",_coverage(output,raw,observed_fields)))
    sections["Overview"].append(("Body composition (estimates)",_body_comp(output,daily)))
    sections["Overview"].append(("Anthropometric ratios",_ratios(output,daily)))
    sections["Overview"].append(("Changes in time (observed bins)",_weekly_and_change(output,daily)))
    cor_name=_correlation_matrix(output,daily,["Weight","Body Fat","Muscle","Waist","Belly","Hips","Chest","Arm"])
    if cor_name:
        sections["Overview"].append(("Pairwise correlation matrix (exploratory)",cor_name))
    if comparison:
        sections["Historical goals (explicit opt-in)"].append(("Old goals vs measured data",_goals_chart(output,comparison)))
    for field in observed_fields:
        name=_field_chart(output,daily,records,field,historical_goals=historical_goals)
        if name:sections["Individual measurements"].append((_label(field),name))
    for x,y,degree in RELATIONS:
        name=_relationship(output,daily,x,y,degree=degree)
        if name:sections["Paired relationships and in-range fits"].append((f"{_label(y)} vs {_label(x)}",name))
    activity_rows=0
    if activity_file is not None and Path(activity_file).is_file():
        name,activity_rows=_activity_plots(output,activity_file)
        sections["Archived activity"].append(("Recorded activity 2022–2023 only",name))
    from .analysis_tables import yearly_summary,period_comparisons,pairwise_correlations
    import hashlib
    record_fingerprint=hashlib.sha256(json.dumps(sorted(records,key=lambda row:(row["date"],row["source_row"])),sort_keys=True,separators=(",",":")).encode("utf-8")).hexdigest()
    tables_fields=[x for x in METRICS if x in daily]
    recency=[
        {
            "metric":name,
            "observed_rows":int(raw[name].notna().sum()),
            "last_observed_date":str(raw.loc[raw[name].notna(),"date"].max().date()),
            "days_behind_last_snapshot_observation":int(
                (raw["date"].max()-raw.loc[raw[name].notna(),"date"].max()).days
            ),
        }
        for name in observed_fields
    ]
    metadata={
        "observed_field_recency":recency,
        "period_comparisons":period_comparisons(daily,tables_fields),
        "yearly_summary":yearly_summary(daily,tables_fields),
        "pairwise_correlations":pairwise_correlations(daily,["Weight","Body Fat","Muscle","Waist","Belly","Hips","Chest","Arm"]),
        "legacy_goals_comparison":comparison,
        "schema_version": 1,
        "data_mode": data_mode,
        "estimated_value_count": estimated_value_count,
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "Personal Measurements / MEDIDAS · private SQLite projection",
        "source_rows":len(raw),"unique_dates":len(daily),
        "source_observation_sha256":record_fingerprint,
        "date_first":str(daily.index.min().date()),
        "date_last":str(daily.index.max().date()),
        "observed_counts":{k:int(v) for k,v in observation_counts(raw).items()},
        "chart_count":sum(len(items) for items in sections.values()),
        "activity_archive_rows":activity_rows,
        "chart_sections":{name:[file for _,file in items] for name,items in sections.items()},
        "semantics": (
            "observed plus kernel-estimated missing fields on existing dates; no new dates"
            if data_mode == "enriched"
            else "observed-only, descriptive derived measures; no filled calendar dates"
        ),
    }
    meta=output/"manifest.json"
    temp=output/".manifest.tmp"
    temp.write_text(json.dumps(metadata,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    os.chmod(temp,0o600)
    os.replace(temp,meta)
    index=_write_index(output,sections,raw,daily,metadata)
    current_figures = {item for group in metadata["chart_sections"].values() for item in group}
    for obsolete in previous_figures - current_figures:
        # Remove only previously reported generated PNGs; do not touch other
        # files in the user's private directory.
        artifact = output / obsolete
        if artifact.is_file() and not artifact.is_symlink():
            artifact.unlink()
    return {"index":index,"manifest":meta,"figures":metadata["chart_count"],"source_rows":len(raw),"activity_rows":activity_rows}
