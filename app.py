import asyncio
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

from fake_temperature import seasonal_temperatures, month_to_season, generate_realistic_temperature_data
from call_weather import get_current_temperature_sync
from rolling_window import add_rolling_stats
from benchmarks import sync_requests, async_requests

st.set_page_config(
	page_title="Kolesnikov Temperature",
	layout="wide"
)

st.title("Анализ температурных данных")

st.sidebar.header("Источник данных")
condition = st.sidebar.radio(
	"Выберите режим:",
	["Загрузите файл", ":rainbow[Сгенерируйте данные]"],
	captions= [
		"У вас уже есть файл с температурой",
		"Приложение создаст файл за вас"
	]
)

df = st.session_state.get("file_create")

if condition == "Загрузите файл":
	file = st.sidebar.file_uploader("temperature_data.csv", type=["csv"])
	if file is not None:
		df = pd.read_csv(file)
else:
	if st.sidebar.button("Сгенерировать"):
		st.session_state["file_create"] = generate_realistic_temperature_data(
			cities=list(seasonal_temperatures.keys())
		)
		st.session_state["file_create"].to_csv("temperature_data.csv", index=False)
		st.sidebar.success("Файл с погодой готов к анализу")

	df = st.session_state.get("file_create")

if df is None:
	st.info(
		"Выберите источник данных в боковом меню,"
		"чтобы начать анализ температур"
	)
	st.stop()

st.sidebar.header("OpenWeatherMap API")

api_key_input = st.sidebar.text_input(
	"API Key",
	type="password"
)

if st.sidebar.button("Отправить ключ"):
	st.session_state["api_key"] = api_key_input

# Выбор города
st.subheader("Выбор города")
cities = sorted(df["city"].unique())
city = st.selectbox("Город", cities)
city_df = df[df["city"] == city].copy()
city_df["timestamp"] = pd.to_datetime(city_df["timestamp"])
city_df = city_df.sort_values("timestamp")

# 1 инфографика
st.subheader("Описательная статистика")
stats = city_df["temperature"].describe()
st.dataframe(stats.to_frame("Значение"))

# 2 инфографика
WINDOW = 30
city_df = add_rolling_stats(city_df, window=WINDOW)

st.subheader("Временной ряд температуры и аномалий")
fig = go.Figure()

fig.add_trace(go.Scatter(
	x=city_df["timestamp"],
	y=city_df["temperature"],
	mode="lines",
	name="Температура"
))

fig.add_trace(go.Scatter(
	x=city_df["timestamp"],
	y=city_df["rolling_mean"],
	mode="lines",
	name="Скользящее среднее (30 дней)"
))

fig.add_trace(go.Scatter(
	x=city_df[city_df["anomaly"]]["timestamp"],
	y=city_df[city_df["anomaly"]]["temperature"],
	mode="markers",
	name="Аномалии",
	marker=dict(color="red", size=6)
))

st.plotly_chart(fig, use_container_width=True)

# 3 инфографика
st.subheader("Сезонные профили")

season_stats = (
	city_df
	.groupby("season")["temperature"]
	.agg(["mean", "std"])
	.reset_index()
)

st.dataframe(season_stats)

# 4 инфографика
fig_season = go.Figure()

fig_season.add_trace(go.Bar(
	x=season_stats["season"],
	y=season_stats["mean"],
	error_y=dict(type="data", array=season_stats["std"]),
	name="Средняя температура ± σ"
))

st.plotly_chart(fig_season, use_container_width=True)

# Дополнительная возможность сравнить погоду с другим городом
st.subheader("Сравнение с другим городом")

city_compare = st.selectbox(
	"Выберите второй город",
	[c for c in cities if c != city]
)

city_df_2 = df[df["city"] == city_compare].copy()
city_df_2["timestamp"] = pd.to_datetime(city_df_2["timestamp"])
city_df_2 = city_df_2.sort_values("timestamp")

city_df_2["rolling_mean"] = (
	city_df_2["temperature"]
	.rolling(window=WINDOW)
	.mean()
)

st.subheader("Сравнение температур двух городов")

fig_compare = go.Figure()

# Город 1 — температура
fig_compare.add_trace(go.Scatter(
	x=city_df["timestamp"],
	y=city_df["temperature"],
	mode="lines",
	name=f"{city} — температура"
))

# Город 2 — температура
fig_compare.add_trace(go.Scatter(
	x=city_df_2["timestamp"],
	y=city_df_2["temperature"],
	mode="lines",
	marker=dict(color="green"),
	name=f"{city_compare} — температура"
))

fig_compare.update_layout(
	xaxis_title="Дата",
	yaxis_title="Температура, °C",
	title=f"Сравнение температур: {city} vs {city_compare}"
)

st.plotly_chart(fig_compare, use_container_width=True)

# Получение реальных данных с сайта
api_key = st.session_state.get("api_key")

if api_key:
	st.sidebar.success("API ключ сохранён")
else:
	st.sidebar.info("Введите и отправьте API ключ")

current_temp = None

if api_key:
	weather = get_current_temperature_sync(city, api_key)

	if weather.get("cod") == 401:
		st.warning("Неверный API ключ. Проверьте корректность ключа.")
	elif weather.get("cod") != 200:
		st.warning("Не удалось получить данные о погоде!")
	else:
		current_temp = weather["main"]["temp"]
		st.subheader("Текущая температура")
		st.metric("Температура сейчас", f"{current_temp} °C")
else:
	st.warning("Введите API ключ, чтобы получить текущую температуру!")
	
if current_temp is None:
	st.info(
		"Текущая температура недоступна."
		"Сравнение с нормой сезона не выполнено."
	)
	st.stop()

current_month = datetime.now().month
current_season = month_to_season[current_month]
season_row = season_stats[season_stats["season"] == current_season].iloc[0]
season_mean = season_row["mean"]
season_std = season_row["std"]
season_min = season_mean - 2 * season_std
season_max = season_mean + 2 * season_std

fig_norm = go.Figure()

fig_norm.add_trace(go.Bar(
	x=["Норма сезона"],
	y=[season_mean],
	error_y=dict(
		type="data",
		array=[season_max - season_mean],
		arrayminus=[season_mean - season_min]
	),
	name=f"{current_season.capitalize()} (норма ±2σ)"
))

fig_norm.add_trace(go.Scatter(
	x=["Норма сезона"],
	y=[current_temp],
	mode="markers",
	marker=dict(size=14, color="red"),
	name="Текущая температура"
))

fig_norm.update_layout(
	title=f"Сравнение текущей температуры с нормой сезона ({current_season})",
	yaxis_title="Температура, °C"
)

st.plotly_chart(fig_norm, use_container_width=True)

if season_min <= current_temp <= season_max:
	st.success("Температура в пределах сезонной нормы")
else:
	st.warning("Температура аномальна для данного сезона")

st.subheader("Эксперимент с запросами")
num_cities = st.slider(
	"Количество городов для теста",
	min_value=1,
	max_value=5,
	value=5
)

# Бенчмарк для сравнения скорости выполнения запросов
run_benchmark = st.button("**Сравнить sync vs async**")
if run_benchmark and api_key:
	all_test_cities = ["Berlin", "Cairo", "Dubai", "Beijing", "Moscow"]
	test_cities = all_test_cities[:num_cities]

	sync_time = sync_requests(test_cities, api_key)
	async_time = asyncio.run(async_requests(test_cities, api_key))

	st.subheader("Сравнение способов запроса")
	st.write(f"Тестируемые города: {', '.join(test_cities)}")
	col1, col2 = st.columns(2)
	col1.metric("Синхронный", f"{sync_time:.3f} сек")
	col2.metric("Асинхронный", f"{async_time:.3f} сек")
