import requests

SUPERJOB_API_KEY = "v3.r.128957429.ebce85881099515a8f11d2afb618682d210c0581.c0d5368e224645c5bcacc1343a73bbf06cb533e1"

def search_superjob(query, city=1, salary=0, schedule='any'):
    headers = {
        'X-Api-App-Id': SUPERJOB_API_KEY
    }
    url = "https://api.superjob.ru/2.0/vacancies/"
    params = {
        "keyword": query,
        "town": city,
        "payment_from": salary,
        "count": 5
    }
    if schedule == 'remote':
        params['isRemoteWork'] = 1  # Только удаленка

    try:
        response = requests.get(url, headers=headers, params=params)
        response.encoding = 'utf-8'  # ⬅️ Добавляем правильную кодировку!
        response.raise_for_status()
        vacancies = response.json().get("objects", [])
        results = [f"SuperJob: {v['profession']} - {v['link']}" for v in vacancies]
        return results
    except Exception as e:
        print(f"Ошибка при запросе к SuperJob: {e}")
        return []
