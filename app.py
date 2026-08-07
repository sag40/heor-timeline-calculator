


import streamlit as st

def check_password():
    if st.session_state.get("password_correct"):
        return True
    pwd = st.text_input("Password", type="password")
    if pwd == "HEOR_Lock1!":
        st.session_state.password_correct = True
        st.rerun()
    elif pwd:
        st.error("Incorrect password")
    return False

if not check_password():
    st.stop()

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy import stats
import datetime

st.set_page_config(
    page_title="AI Holdout Timeline Calculator",
    page_icon="🧪",
    layout="wide",
)

# ── Outcome configuration (defaults from Spring Health Snowflake, Aug 2026) ───
OUTCOMES = {
    "PHQ-9 Change": {
        "prevalence_default": 38.0,
        "reassess_default":   50.0,
        "sd":                 5.71,
        "units":              "PHQ-9 points",
        "yaxis_title":        "Minimum Detectable Effect (PHQ-9 points)",
        "note":               "Members with baseline PHQ-9 ≥ 10 who complete a follow-up within 90 days",
        "has_prevalence":     True,
        "has_reassess":       True,
        "target_default":     0.50,
        "target_step":        0.05,
        "tiers": [
            (0.50, "0.5 pts",  "#2ca02c"),
            (0.75, "0.75 pts", "#ff7f0e"),
            (1.00, "1 pt",     "#d62728"),
        ],
    },
    "GAD-7 Change": {
        "prevalence_default": 34.6,
        "reassess_default":   50.0,
        "sd":                 5.27,
        "units":              "GAD-7 points",
        "yaxis_title":        "Minimum Detectable Effect (GAD-7 points)",
        "note":               "Members with baseline GAD-7 ≥ 10 who complete a follow-up within 90 days",
        "has_prevalence":     True,
        "has_reassess":       True,
        "target_default":     0.50,
        "target_step":        0.05,
        "tiers": [
            (0.50, "0.5 pts",  "#2ca02c"),
            (0.75, "0.75 pts", "#ff7f0e"),
            (1.00, "1 pt",     "#d62728"),
        ],
    },
    "Sessions – all members": {
        "prevalence_default": 100.0,
        "reassess_default":   100.0,
        "sd":                 3.14,
        "units":              "sessions",
        "yaxis_title":        "Minimum Detectable Effect (sessions, 90-day cumulative)",
        "note":               "All new members — no assessment completion required",
        "has_prevalence":     False,
        "has_reassess":       False,
        "target_default":     0.25,
        "target_step":        0.05,
        "tiers": [
            (0.25, "0.25 sessions", "#2ca02c"),
            (0.50, "0.5 sessions",  "#ff7f0e"),
            (1.00, "1 session",     "#d62728"),
        ],
    },
    "Sessions – elevated only (PHQ or GAD ≥ 10)": {
        "prevalence_default": 36.3,
        "reassess_default":   100.0,
        "sd":                 3.14,
        "units":              "sessions",
        "yaxis_title":        "Minimum Detectable Effect (sessions, 90-day cumulative)",
        "note":               "Members with baseline PHQ-9 or GAD-7 ≥ 10 (~36% of new members)",
        "has_prevalence":     True,
        "has_reassess":       False,
        "target_default":     0.25,
        "target_step":        0.05,
        "tiers": [
            (0.25, "0.25 sessions", "#2ca02c"),
            (0.50, "0.5 sessions",  "#ff7f0e"),
            (1.00, "1 session",     "#d62728"),
        ],
    },
}

# ── Header & tabs ─────────────────────────────────────────────────────────────
st.title("AI Holdout Product Testing Timeline Calculator")
st.caption("Spring Health HEOR · Dr. Scott Graupensperger · scott.graupensperger@springhealth.com")

tab_about, tab_calc = st.tabs(["About", "Calculator"])

# ══════════════════════════════════════════════════════════════════════════════
# ABOUT TAB
# ══════════════════════════════════════════════════════════════════════════════
with tab_about:
    st.subheader("What is this tool?")
    st.markdown(
        """
        This calculator helps Spring Health's Product team answer a simple question:

        > **If we launch an AI feature today, when will we have enough data to know whether it's working?**

        You choose an outcome you care about (symptom improvement or session engagement),
        enter the size of the effect you expect the AI to produce, and the tool tells you
        the earliest date at which results can be trusted.
        """
    )

    st.subheader("What is the AI holdout?")
    st.markdown(
        """
        Approximately **3% of all Spring Health members** are randomly assigned to a permanent
        "holdout" group — they are never exposed to any AI-powered features. This group is
        maintained globally across all products.

        When a new AI feature launches, we compare outcomes for:
        - **ITT group (~97%)** — members who received the AI feature
        - **Holdout group (~3%)** — members who never received any AI features

        Because the holdout is randomly assigned, any difference in outcomes can be
        attributed to the AI, not pre-existing differences between groups.
        """
    )

    st.subheader("How to use this tool")
    st.markdown(
        """
        1. **Click the Calculator tab** above
        2. **Choose an outcome** — PHQ-9 change, GAD-7 change, or session counts
        3. **Enter the effect size you expect** — e.g., "I expect the AI to produce a 0.5-point
           improvement in PHQ-9 scores." Larger expected effects are confirmable sooner.
        4. **Optionally enter a launch date** to see real calendar dates instead of month counts
        5. **Read the result** — the top card shows the earliest date (or month) at which
           you'll have 80% power to confirm your expected effect

        All default values are pre-filled from Spring Health's actual platform data.
        Adjust enrollment rate, holdout percentage, and re-assessment rate in the left
        sidebar to model different scenarios.
        """
    )

    st.subheader("Key assumptions")
    st.markdown(
        """
        | Assumption | Default value | Source |
        |---|---|---|
        | Monthly new members | 22,000 | Trailing 12-month avg, Snowflake (Jul 2026) |
        | AI holdout rate | 3.01% | `member_feature_holdouts` table (Aug 2026) |
        | PHQ-9 elevated at baseline | 38.0% | `APEX_QUESTIONNAIRE_SCORE_COMPARISON` |
        | GAD-7 elevated at baseline | 34.6% | `APEX_QUESTIONNAIRE_SCORE_COMPARISON` |
        | Re-assessment completion | 50% | Company KPI tracking (mid-2026 actuals) |
        | SD of PHQ-9 change | 5.71 pts | Members with follow-up ≤ 90 days |
        | SD of GAD-7 change | 5.27 pts | Members with follow-up ≤ 90 days |
        | SD of sessions (90-day) | 3.14 | `APEX_FACT_APPOINTMENTS` |

        Power calculations use a two-sample z-test at α = 0.05, 80% power (adjustable).
        Because the ITT group is ~97× larger than the holdout, statistical power is driven
        almost entirely by the holdout group size.
        """
    )

    st.subheader("Limitations")
    st.markdown(
        """
        - This tool plans for **detecting whether an effect exists** — it does not tell you
          whether the effect is clinically meaningful on its own.
        - Re-assessment rates and baseline prevalence are population-level averages.
          A feature targeting a specific sub-population may differ.
        - Projections assume the feature launches to 100% of eligible ITT members immediately.
          Phased rollouts would require adjusting the monthly enrollment input downward.
        - All defaults will drift over time as Spring Health grows. Update annually.
        """
    )

    st.info("Ready to run a projection? Click the **Calculator** tab above.")

# ══════════════════════════════════════════════════════════════════════════════
# CALCULATOR TAB
# ══════════════════════════════════════════════════════════════════════════════
with tab_calc:

    # ── Outcome selector ──────────────────────────────────────────────────────
    outcome_name = st.radio("Outcome", list(OUTCOMES.keys()), horizontal=True)
    cfg = OUTCOMES[outcome_name]
    st.caption(f"_{cfg['note']}_")
    st.divider()

    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.header("Parameters")

        st.subheader("Launch Date")
        use_launch_date = st.checkbox(
            "Convert timeline to calendar dates",
            value=False,
            help="Enter a launch date to show real month/year labels on the chart and an estimated confirmation date.",
        )
        if use_launch_date:
            launch_date = st.date_input(
                "Anticipated launch date",
                value=datetime.date.today(),
            )
        else:
            launch_date = None

        st.subheader("Enrollment")
        monthly_enrollment = st.number_input(
            "Monthly new members",
            min_value=1_000, max_value=100_000, value=22_000, step=500,
            help="Trailing 12-month average as of July 2026: ~22,000.",
        )
        holdout_pct = st.number_input(
            "AI holdout rate (%)",
            min_value=0.1, max_value=20.0, value=3.01, step=0.01, format="%.2f",
            help="Global AI holdout rate as of August 2026: 3.01%.",
        )

        if cfg["has_prevalence"]:
            st.subheader("Sub-population Filter")
            prevalence_pct = st.number_input(
                "% of new members meeting baseline threshold",
                min_value=1.0, max_value=100.0,
                value=cfg["prevalence_default"], step=0.1, format="%.1f",
                help="Pulled from Spring Health Snowflake (Aug 2026). Edit to reflect a targeted sub-population.",
            )
        else:
            prevalence_pct = 100.0

        if cfg["has_reassess"]:
            st.subheader("Re-assessment Completion")
            reassess_pct = st.number_input(
                "Re-assessment completion rate (%)",
                min_value=1.0, max_value=100.0,
                value=cfg["reassess_default"], step=0.1, format="%.1f",
                help="% of eligible members who complete a follow-up assessment. "
                     "Company-tracked KPI as of mid-2026: ~50% overall, trending toward 60% year-end target.",
            )
        else:
            reassess_pct = 100.0

        st.subheader("Expected Effect Size")
        target_raw = st.number_input(
            f"Expected effect ({cfg['units']})",
            min_value=0.01, max_value=cfg["sd"] * 2,
            value=cfg["target_default"],
            step=cfg["target_step"],
            format="%.2f",
            help=(
                "How large an improvement do you expect the AI feature to produce? "
                "Larger expected effects are confirmable sooner."
            ),
        )
        target_d = target_raw / cfg["sd"]
        st.caption(f"≡ Cohen's d = {target_d:.3f}")

        st.subheader("Statistical Thresholds")
        alpha        = st.selectbox("Significance level (α)", [0.05, 0.01], index=0)
        power_target = st.selectbox("Power", [0.80, 0.90], index=0)

        st.subheader("Projection Window")
        max_months = st.slider("Months to project", min_value=1, max_value=24, value=6)

    # ── Core calculations ─────────────────────────────────────────────────────
    holdout_rate   = holdout_pct    / 100.0
    prevalence     = prevalence_pct / 100.0
    reassess_rate  = reassess_pct   / 100.0
    effective_rate = prevalence * reassess_rate

    months    = np.arange(1, max_months + 1)
    n_holdout = months * monthly_enrollment * holdout_rate       * effective_rate
    n_itt     = months * monthly_enrollment * (1 - holdout_rate) * effective_rate

    z_alpha = stats.norm.ppf(1.0 - alpha / 2)
    z_beta  = stats.norm.ppf(power_target)

    mdes_d   = (z_alpha + z_beta) * np.sqrt(1.0 / n_holdout + 1.0 / n_itt)
    mdes_raw = mdes_d * cfg["sd"]

    crossover_idx    = np.where(mdes_d <= target_d)[0]
    months_to_detect = int(months[crossover_idx[0]]) if len(crossover_idx) > 0 else None

    # Build x-axis: real datetimes if launch date supplied, integers otherwise
    if use_launch_date and launch_date is not None:
        launch_ts = pd.Timestamp(launch_date)
        x_vals = [launch_ts + pd.DateOffset(months=int(m)) for m in months]
        confirm_x     = launch_ts + pd.DateOffset(months=months_to_detect) if months_to_detect else None
        confirm_label = confirm_x.strftime("%b %Y") if confirm_x else None
        def month_label(n):
            return (launch_ts + pd.DateOffset(months=int(n))).strftime("%b %Y")
    else:
        x_vals        = list(months)
        confirm_x     = months_to_detect
        confirm_label = None
        def month_label(n):
            return f"Month {n}"

    # ── Metric cards ──────────────────────────────────────────────────────────
    st.subheader("At-a-Glance")
    c1, c2, c3, c4 = st.columns(4)

    if months_to_detect is not None:
        n_ho_det  = int(monthly_enrollment * holdout_rate       * effective_rate * months_to_detect)
        n_itt_det = int(monthly_enrollment * (1 - holdout_rate) * effective_rate * months_to_detect)
        if confirm_label:
            c1_label = "Estimated confirmation date"
            c1_value = confirm_label
            c1_help  = f"{months_to_detect} months after launch — first point at which you have {power_target:.0%} power to confirm ≥ {target_raw:.2f} {cfg['units']}."
        else:
            c1_label = f"Months to confirm ≥ {target_raw:.2f} {cfg['units']}"
            c1_value = f"{months_to_detect} months"
            c1_help  = f"First month at which you have {power_target:.0%} power to detect the expected effect."
        c1.metric(c1_label, c1_value, help=c1_help)
        c2.metric("Analyzable holdout N at confirmation", f"{n_ho_det:,}")
        c3.metric("Analyzable ITT N at confirmation", f"{n_itt_det:,}")
    else:
        c1.metric(f"Months to confirm ≥ {target_raw:.2f} {cfg['units']}", f">{max_months} months")
        c2.metric(f"Analyzable holdout N at {month_label(max_months)}", f"{int(n_holdout[-1]):,}")
        c3.metric(f"Analyzable ITT N at {month_label(max_months)}", f"{int(n_itt[-1]):,}")

    eff_per_month = int(monthly_enrollment * holdout_rate * effective_rate)
    c4.metric(
        "Analyzable holdout / month",
        f"{eff_per_month:,}",
        help="New holdout members × prevalence filter × re-assessment rate.",
    )

    steps = [f"{int(monthly_enrollment * holdout_rate):,} gross holdout/month"]
    if cfg["has_prevalence"]:
        steps.append(f"× {prevalence_pct:.1f}% elevated → {int(monthly_enrollment * holdout_rate * prevalence):,}")
    if cfg["has_reassess"]:
        steps.append(f"× {reassess_pct:.1f}% re-assessed → {eff_per_month:,} analyzable/month")
    st.caption("Enrollment funnel: " + "  →  ".join(steps))

    # ── Power curve ───────────────────────────────────────────────────────────
    st.subheader("When Can You Confirm Your Expected Effect?")

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=x_vals, y=mdes_raw,
        mode="lines",
        name="MDE",
        line=dict(color="#1f77b4", width=3),
        hovertemplate=f"%{{x}}<br>MDE = %{{y:.2f}} {cfg['units']}<extra></extra>",
    ))

    for raw_val, label, color in cfg["tiers"]:
        fig.add_hline(
            y=raw_val, line_dash="dash", line_color=color, line_width=1.5,
            annotation_text=label,
            annotation_position="bottom right",
            annotation_font_color=color,
        )

    if months_to_detect is not None and confirm_x is not None:
        vline_label = f"  Can confirm from {confirm_label}" if confirm_label else f"  Month {months_to_detect}"
        vline_x = confirm_x.timestamp() * 1000 if use_launch_date else confirm_x
        fig.add_vline(
            x=vline_x,
            line_dash="dot", line_color="#7f7f7f",
            annotation_text=vline_label,
            annotation_position="top left",
        )

    y_max = max(cfg["tiers"][-1][0] * 1.3, float(mdes_raw[0]) * 1.1)
    fig.update_layout(
        xaxis=dict(
            title="Calendar month" if use_launch_date else "Months since feature launch",
            tickformat="%b %Y" if use_launch_date else None,
        ),
        yaxis_title=cfg["yaxis_title"],
        yaxis=dict(range=[0, y_max]),
        template="plotly_white",
        height=460,
        margin=dict(r=180, t=80),
        title=dict(
            text=(
                f"Detection threshold falls over time as sample accumulates — "
                f"once it drops below your expected effect, you have {power_target:.0%} power to confirm it.<br>"
                f"<sup>α = {alpha}  |  power = {power_target:.0%}  |  "
                f"{eff_per_month:,} analyzable holdout members/month  |  outcome: {outcome_name}</sup>"
            ),
            font=dict(size=13),
        ),
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── Projection table ──────────────────────────────────────────────────────
    st.subheader("Projection Table")
    checkpoints = [m for m in [1, 2, 3, 4, 5, 6, 9, 12, 18, 24] if m <= max_months]

    rows = []
    for m in checkpoints:
        nh = int(monthly_enrollment * holdout_rate       * effective_rate * m)
        ni = int(monthly_enrollment * (1 - holdout_rate) * effective_rate * m)
        md_raw = (z_alpha + z_beta) * np.sqrt(1.0 / nh + 1.0 / ni) * cfg["sd"] if nh > 0 and ni > 0 else float("nan")
        row = {"Months post-launch": m}
        if use_launch_date:
            row["Date"] = month_label(m)
        row.update({
            "Analyzable holdout N":               f"{nh:,}",
            "Analyzable ITT N":                   f"{ni:,}",
            f"MDE ({cfg['units']})":              f"{md_raw:.2f}" if not np.isnan(md_raw) else "—",
            f"Confirms ≥ {target_raw:.2f} {cfg['units']}?":
                "Yes ✓" if (not np.isnan(md_raw) and md_raw <= target_raw) else "Not yet",
        })
        rows.append(row)

    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

    st.divider()
    st.caption(
        "**Data sources (Aug 2026):** Enrollment rate and holdout % from Spring Health Snowflake. "
        "Baseline prevalence from `ANALYTICS.APEX.APEX_QUESTIONNAIRE_SCORE_COMPARISON` (trailing 12 months). "
        "Re-assessment rate default (50%) from company KPI tracking (mid-2026 actuals; year-end target: 60%). "
        "SD of change scores from members with follow-up ≤ 90 days; SD of sessions from `ANALYTICS.APEX.APEX_FACT_APPOINTMENTS`."
    )
    st.caption(
        "Maintained by Spring Health's Health Economics & Outcomes Research (HEOR) Team · "
        "Lead: Dr. Scott Graupensperger · scott.graupensperger@springhealth.com"
    )
