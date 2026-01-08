'''
РАБОТА С АСИНХРОННОСТЬЮ!
Сайт с информацией о погоде быстро присылает ответ, поэтому для одного города нет особого преимущества в выборе подхода
Но вот разница уже видна при выборе нескольких городов!
1. При синхронном выполнении HTTP-запросы выполняются последовательно, и общее время работы является суммой времени каждого запроса.
2. При асинхронном подходе все запросы отправляются практически одновременно, и общее время выполнения определяется самым медленным запросом.
При одном запросе разница между синхронным и асинхронным подходом незначительна из-за накладных расходов на создание асинхронных задач.
Однако при увеличении количества городов асинхронный подход демонстрирует существенное ускорение.
'''
import time
import asyncio
from call_weather import (
	get_current_temperature_sync,
	get_current_temperature_async
)

def sync_requests(cities, api_key):
	start = time.perf_counter()

	for city in cities:
		get_current_temperature_sync(city, api_key)

	return time.perf_counter() - start


async def async_requests(cities, api_key):
	start = time.perf_counter()

	tasks = [
		get_current_temperature_async(city, api_key)
		for city in cities
	]

	await asyncio.gather(*tasks)

	return time.perf_counter() - start
