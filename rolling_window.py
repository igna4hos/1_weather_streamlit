# Добавляет скользящее среднее, std и аномалии (±2σ)
import pandas as pd

def add_rolling_stats(
	df: pd.DataFrame,
	window: int = 30,
	value_col: str = "temperature"
) -> pd.DataFrame:

	df = df.copy()

	df["rolling_mean"] = (
		df[value_col]
		.rolling(window=window)
		.mean()
	)

	df["rolling_std"] = (
		df[value_col]
		.rolling(window=window)
		.std()
	)

	df["upper_bound"] = df["rolling_mean"] + 2 * df["rolling_std"]
	df["lower_bound"] = df["rolling_mean"] - 2 * df["rolling_std"]

	df["anomaly"] = (
		(df[value_col] > df["upper_bound"]) |
		(df[value_col] < df["lower_bound"])
	)

	return df
