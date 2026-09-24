import json
import glob
from pathlib import Path

import pandas as pd


# --------------------------------------------------
# 1. Find IPL JSON files
# --------------------------------------------------

DATA_DIR = Path("data")
JSON_DIR = DATA_DIR / "ipl_json"

files = sorted(glob.glob(str(JSON_DIR / "*.json")))

if not files:
    raise FileNotFoundError(
        f"No JSON files found in {JSON_DIR}. "
        "Check that the IPL ZIP file has been extracted."
    )

print("Total match files:", len(files))


# --------------------------------------------------
# 2. Read one match as a sample
# --------------------------------------------------

with open(files[0], "r", encoding="utf-8") as f:
    sample_match = json.load(f)

print("\n===== SAMPLE MATCH =====")
print("Teams:", sample_match["info"]["teams"])
print("Date:", sample_match["info"]["dates"])
print("Venue:", sample_match["info"].get("venue", "Unknown"))
print("Number of innings:", len(sample_match["innings"]))


# --------------------------------------------------
# 3. Extract delivery-level data from all matches
# --------------------------------------------------

print("\n===== EXTRACTING ALL DELIVERIES =====")

batting_data = []

for file_path in files:

    with open(file_path, "r", encoding="utf-8") as f:
        match = json.load(f)

    match_id = Path(file_path).stem
    date = match["info"]["dates"][0]
    season = str(match["info"].get("season", date[:4]))
    venue = match["info"].get("venue", "Unknown")
    teams = match["info"]["teams"]

    for innings_no, innings in enumerate(match["innings"], start=1):

        batting_team = innings["team"]

        opponents = [
            team for team in teams
            if team != batting_team
        ]
        opponent_team = opponents[0] if opponents else "Unknown"

        for over in innings["overs"]:

            over_number = over["over"]

            for delivery_number, delivery in enumerate(
                over["deliveries"], start=1
            ):

                batter = delivery["batter"]
                bowler = delivery["bowler"]

                runs = delivery["runs"]
                batter_runs = runs["batter"]
                total_runs = runs["total"]

                extras_dict = delivery.get("extras", {})
                total_extras = sum(extras_dict.values())

                # Extras by type
                wides = extras_dict.get("wides", 0)
                no_balls = extras_dict.get("noballs", 0)
                byes = extras_dict.get("byes", 0)
                legbyes = extras_dict.get("legbyes", 0)
                penalty = extras_dict.get("penalty", 0)

                # A wide is not a ball faced.
                # A no-ball can count as a ball faced.
                balls_faced = 0 if wides > 0 else 1

                # Batter boundaries
                fours = 1 if batter_runs == 4 else 0
                sixes = 1 if batter_runs == 6 else 0

                # Wickets recorded on this delivery
                wickets = delivery.get("wickets", [])

                dismissed_players = [
                    wicket.get("player_out")
                    for wicket in wickets
                    if wicket.get("player_out")
                ]

                dismissal_types = [
                    wicket.get("kind")
                    for wicket in wickets
                    if wicket.get("kind")
                ]

                batting_data.append({
                    "match_id": match_id,
                    "date": date,
                    "season": season,
                    "venue": venue,
                    "batting_team": batting_team,
                    "opponent_team": opponent_team,
                    "innings_no": innings_no,
                    "over": over_number,
                    "delivery_number": delivery_number,
                    "batter": batter,
                    "bowler": bowler,
                    "batter_runs": batter_runs,
                    "total_runs": total_runs,
                    "extras": total_extras,
                    "wides": wides,
                    "no_balls": no_balls,
                    "byes": byes,
                    "legbyes": legbyes,
                    "penalty": penalty,
                    "balls_faced": balls_faced,
                    "fours": fours,
                    "sixes": sixes,
                    "wicket_count": len(wickets),
                    "dismissed_players": "|".join(dismissed_players),
                    "dismissal_types": "|".join(dismissal_types)
                })


# --------------------------------------------------
# 4. Create DataFrame and save delivery data
# --------------------------------------------------

df = pd.DataFrame(batting_data)

df["date"] = pd.to_datetime(df["date"])

delivery_csv = DATA_DIR / "ipl_batting_deliveries.csv"
df.to_csv(delivery_csv, index=False)

print("\n===== DELIVERY DATA =====")
print("Rows:", len(df))
print("Columns:", len(df.columns))
print("Matches:", df["match_id"].nunique())
print("Teams:", df["batting_team"].nunique())
print("Players:", df["batter"].nunique())
print("Date range:", df["date"].min().date(), "to", df["date"].max().date())
print("Duplicate deliveries:", df.duplicated(
    subset=["match_id", "innings_no", "over", "delivery_number"]
).sum())
print("Saved:", delivery_csv)


# --------------------------------------------------
# 5. Create innings-level batting scores
# --------------------------------------------------

print("\n===== CREATING INNINGS SCORES =====")

innings_scores = (
    df.groupby(["match_id", "innings_no", "batter"], as_index=False)
    .agg(
        runs=("batter_runs", "sum"),
        balls_faced=("balls_faced", "sum"),
        fours=("fours", "sum"),
        sixes=("sixes", "sum")
    )
)


# --------------------------------------------------
# 6. Count dismissals for each batter
# --------------------------------------------------

dismissal_records = []

for file_path in files:

    with open(file_path, "r", encoding="utf-8") as f:
        match = json.load(f)

    match_id = Path(file_path).stem

    for innings_no, innings in enumerate(match["innings"], start=1):

        for over in innings["overs"]:
            for delivery in over["deliveries"]:

                for wicket in delivery.get("wickets", []):

                    player_out = wicket.get("player_out")
                    dismissal_type = wicket.get("kind")

                    # Retired hurt is not counted as a dismissal
                    if (
                        player_out
                        and dismissal_type != "retired hurt"
                    ):
                        dismissal_records.append({
                            "match_id": match_id,
                            "innings_no": innings_no,
                            "batter": player_out
                        })

dismissals_df = pd.DataFrame(
    dismissal_records,
    columns=["match_id", "innings_no", "batter"]
)

if dismissals_df.empty:
    dismissals_df = pd.DataFrame(
        columns=["match_id", "innings_no", "batter", "dismissals"]
    )
else:
    dismissals_df = (
        dismissals_df
        .groupby(["match_id", "innings_no", "batter"])
        .size()
        .reset_index(name="dismissals")
    )


# --------------------------------------------------
# 7. Combine innings scores and dismissals
# --------------------------------------------------

innings_scores = innings_scores.merge(
    dismissals_df,
    on=["match_id", "innings_no", "batter"],
    how="left"
)

innings_scores["dismissals"] = (
    innings_scores["dismissals"]
    .fillna(0)
    .astype(int)
)


# --------------------------------------------------
# 8. Create player-level batting summary
# --------------------------------------------------

print("\n===== CREATING PLAYER BATTING SUMMARY =====")

player_summary = (
    df.groupby("batter", as_index=False)
    .agg(
        matches=("match_id", "nunique"),
        runs=("batter_runs", "sum"),
        balls_faced=("balls_faced", "sum"),
        fours=("fours", "sum"),
        sixes=("sixes", "sum")
    )
)

innings_summary = (
    innings_scores.groupby("batter", as_index=False)
    .agg(
        innings=("runs", "count"),
        dismissals=("dismissals", "sum"),
        fifties=("runs", lambda scores: ((scores >= 50) & (scores < 100)).sum()),
        hundreds=("runs", lambda scores: (scores >= 100).sum()),
        highest_score=("runs", "max")
    )
)

player_summary = player_summary.merge(
    innings_summary,
    on="batter",
    how="left"
)

# Strike rate = runs / balls faced * 100
# Strike rate = runs / balls faced * 100
player_summary["strike_rate"] = (
    player_summary["runs"]
    .div(player_summary["balls_faced"].replace(0, float("nan")))
    .mul(100)
).round(2)

# Batting average = runs / dismissals
player_summary["batting_average"] = (
    player_summary["runs"]
    .div(player_summary["dismissals"].replace(0, float("nan")))
).round(2)


# --------------------------------------------------
# 9. Save player summary
# --------------------------------------------------

summary_csv = DATA_DIR / "player_batting_summary.csv"
player_summary.to_csv(summary_csv, index=False)

print("\nTop 20 players by runs:")
print(player_summary.head(20).to_string(index=False))

print("\nSaved:", summary_csv)


# --------------------------------------------------
# 10. Data quality checks
# --------------------------------------------------

print("\n===== DATA QUALITY CHECK =====")

print("\nMissing values in delivery data:")
print(df.isnull().sum())

print("\nDuplicate delivery keys:")
print(
    df.duplicated(
        subset=[
            "match_id",
            "innings_no",
            "over",
            "delivery_number"
        ]
    ).sum()
)

print("\nTotal batter runs:", df["batter_runs"].sum())
print("Total extras:", df["extras"].sum())
print("Total recorded wickets:", df["wicket_count"].sum())

print("\nAll processing completed successfully!")
# --------------------------------------------------
# 11. Create bowler-level summary
# --------------------------------------------------

print("\n===== CREATING BOWLING SUMMARY =====")

bowling_df = df.copy()

# Bowler's conceded runs:
# Exclude byes, leg-byes, and penalty runs.
bowling_df["bowler_runs_conceded"] = (
    bowling_df["total_runs"]
    - bowling_df["byes"]
    - bowling_df["legbyes"]
    - bowling_df["penalty"]
)

# Legal balls: wides and no-balls are not legal deliveries.
bowling_df["legal_balls"] = (
    (bowling_df["wides"] == 0)
    & (bowling_df["no_balls"] == 0)
).astype(int)

# Wickets credited to the bowler.
# Run outs and other non-bowler dismissals are excluded.
non_bowler_wickets = {
    "run out",
    "retired hurt",
    "retired out",
    "obstructing the field",
    "hit the ball twice",
    "handled the ball"
}

def count_bowler_wickets(dismissal_types):
    if not dismissal_types:
        return 0

    kinds = dismissal_types.split("|")

    return sum(
        kind not in non_bowler_wickets
        for kind in kinds
    )

bowling_df["bowler_wickets"] = (
    bowling_df["dismissal_types"]
    .fillna("")
    .apply(count_bowler_wickets)
)

# Aggregate bowler stats
bowler_summary = (
    bowling_df.groupby("bowler", as_index=False)
    .agg(
        matches=("match_id", "nunique"),
        legal_balls=("legal_balls", "sum"),
        runs_conceded=("bowler_runs_conceded", "sum"),
        wickets=("bowler_wickets", "sum")
    )
)

# Overs shown as decimal overs, e.g. 10.3 means 10 overs + 3 balls.
# Economy uses the actual legal-ball count.
bowler_summary["overs"] = (
    bowler_summary["legal_balls"] // 6
    + (bowler_summary["legal_balls"] % 6) / 10
).round(1)

bowler_summary["economy"] = (
    bowler_summary["runs_conceded"]
    .div(bowler_summary["legal_balls"].replace(0, float("nan")))
    .mul(6)
).round(2)

bowler_summary = bowler_summary.sort_values(
    ["wickets", "economy"],
    ascending=[False, True]
).reset_index(drop=True)

# Save bowling summary
bowling_csv = DATA_DIR / "player_bowling_summary.csv"
bowler_summary.to_csv(bowling_csv, index=False)

print("\nTop 20 bowlers by wickets:")
print(bowler_summary.head(20).to_string(index=False))

print("\nSaved:", bowling_csv)

# --------------------------------------------------
# 12. Create match-level summary
# --------------------------------------------------

print("\n===== CREATING MATCH SUMMARY =====")

match_summary = (
    df.groupby("match_id", as_index=False)
    .agg(
        date=("date", "first"),
        venue=("venue", "first"),
        total_runs=("total_runs", "sum"),
        total_extras=("extras", "sum"),
        total_wickets=("wicket_count", "sum"),
        teams=("batting_team", lambda x: " vs ".join(x.unique()))
    )
)

# Add season/year
match_summary["year"] = match_summary["date"].dt.year

# IPL season label
match_summary["season"] = match_summary["year"].astype(str)

match_csv = DATA_DIR / "ipl_match_summary.csv"
match_summary.to_csv(match_csv, index=False)

print("\nMatch summary:")
print(match_summary.head(10).to_string(index=False))

print("\nTotal matches:", len(match_summary))
print("Saved:", match_csv)

# --------------------------------------------------
# 13. Season-wise analysis
# --------------------------------------------------

print("\n===== SEASON-WISE ANALYSIS =====")

season_summary = (
    df.groupby(df["date"].dt.year, as_index=False)
    .agg(
        total_runs=("total_runs", "sum"),
        batter_runs=("batter_runs", "sum"),
        extras=("extras", "sum"),
        wickets=("wicket_count", "sum"),
        deliveries=("match_id", "count"),
        matches=("match_id", "nunique"),
        players=("batter", "nunique"),
        teams=("batting_team", "nunique")
    )
    .rename(columns={"date": "year"})
)

season_summary["run_rate"] = (
    season_summary["total_runs"]
    .div(season_summary["deliveries"])
    .mul(6)
).round(2)

season_summary = season_summary.sort_values("year")

print("\nSeason-wise summary:")
print(season_summary.to_string(index=False))

season_csv = DATA_DIR / "season_summary.csv"
season_summary.to_csv(season_csv, index=False)

print("\nSaved:", season_csv)

# --------------------------------------------------
# 14. Team / innings analysis
# --------------------------------------------------

print("\n===== TEAM / INNINGS ANALYSIS =====")

team_innings_summary = (
    df.groupby(
        ["match_id", "date", "venue", "innings_no",
         "batting_team", "opponent_team"],
        as_index=False
    )
    .agg(
        runs=("total_runs", "sum"),
        batter_runs=("batter_runs", "sum"),
        extras=("extras", "sum"),
        wickets=("wicket_count", "sum"),
        deliveries=("match_id", "count")
    )
)

team_innings_summary["year"] = (
    team_innings_summary["date"].dt.year
)

team_innings_summary["run_rate"] = (
    team_innings_summary["runs"]
    .div(team_innings_summary["deliveries"])
    .mul(6)
).round(2)

team_innings_summary = team_innings_summary.sort_values(
    ["year", "runs"],
    ascending=[True, False]
).reset_index(drop=True)

team_innings_csv = DATA_DIR / "team_innings_summary.csv"

team_innings_summary.to_csv(
    team_innings_csv,
    index=False
)

print("\nTop 20 innings by runs:")
print(
    team_innings_summary
    .sort_values("runs", ascending=False)
    .head(20)
    .to_string(index=False)
)

print("\nSaved:", team_innings_csv)

print("\nTeam innings rows:", len(team_innings_summary))
print("Unique teams:", team_innings_summary["batting_team"].nunique())
# --------------------------------------------------
# 15. Team-wise performance summary
# --------------------------------------------------

print("\n===== TEAM-WISE PERFORMANCE =====")

team_summary = (
    team_innings_summary
    .groupby("batting_team", as_index=False)
    .agg(
        innings=("match_id", "count"),
        total_runs=("runs", "sum"),
        average_runs=("runs", "mean"),
        total_wickets=("wickets", "sum"),
        total_deliveries=("deliveries", "sum"),
        matches=("match_id", "nunique"),
        opponents=("opponent_team", "nunique"),
        venues=("venue", "nunique")
    )
)

team_summary["run_rate"] = (
    team_summary["total_runs"]
    .div(team_summary["total_deliveries"])
    .mul(6)
).round(2)

team_summary["average_runs"] = (
    team_summary["average_runs"]
).round(2)

team_summary = team_summary.sort_values(
    "total_runs",
    ascending=False
).reset_index(drop=True)

team_csv = DATA_DIR / "team_summary.csv"

team_summary.to_csv(
    team_csv,
    index=False
)

print("\nTeam-wise performance:")
print(team_summary.to_string(index=False))

print("\nSaved:", team_csv)

# --------------------------------------------------
# 16. Venue-wise analysis
# --------------------------------------------------

print("\n===== VENUE-WISE ANALYSIS =====")

venue_summary = (
    team_innings_summary
    .groupby("venue", as_index=False)
    .agg(
        innings=("match_id", "count"),
        matches=("match_id", "nunique"),
        total_runs=("runs", "sum"),
        average_innings_score=("runs", "mean"),
        total_wickets=("wickets", "sum"),
        total_deliveries=("deliveries", "sum"),
        teams=("batting_team", "nunique")
    )
)

venue_summary["run_rate"] = (
    venue_summary["total_runs"]
    .div(venue_summary["total_deliveries"])
    .mul(6)
).round(2)

venue_summary["average_innings_score"] = (
    venue_summary["average_innings_score"]
).round(2)

venue_summary = venue_summary.sort_values(
    "total_runs",
    ascending=False
).reset_index(drop=True)

venue_csv = DATA_DIR / "venue_summary.csv"

venue_summary.to_csv(
    venue_csv,
    index=False
)

print("\nTop 20 venues by total runs:")
print(
    venue_summary
    .head(20)
    .to_string(index=False)
)

print("\nTotal venues:", len(venue_summary))
print("Saved:", venue_csv)

season_summary = (
    df.groupby("season", as_index=False)
    .agg(
        total_runs=("total_runs", "sum"),
        batter_runs=("batter_runs", "sum"),
        extras=("extras", "sum"),
        wickets=("wicket_count", "sum"),
        deliveries=("match_id", "count"),
        matches=("match_id", "nunique"),
        players=("batter", "nunique"),
        teams=("batting_team", "nunique")
    )
)

season_summary["run_rate"] = (
    season_summary["total_runs"]
    .div(season_summary["deliveries"])
    .mul(6)
).round(2)

season_summary = season_summary.sort_values("season")