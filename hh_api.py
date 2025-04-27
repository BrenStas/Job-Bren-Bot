import requests

def search_hh(query, city=1, salary=0, period=30, schedule='any', page=0):
    url = "https://api.hh.ru/vacancies"
    params = {
        "text": query,
        "area": city,
        "salary": salary,
        "period": period,
        "per_page": 5,
        "page": page
    }
    if schedule == 'remote':
        params['schedule'] = 'remote'
    elif schedule == 'office':
        params['schedule'] = 'fullDay'
    elif schedule == 'flexible':
        params['schedule'] = 'flexible'

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        vacancies = response.json().get("items", [])
        results = [f"HH: {v['name']} - {v['alternate_url']}" for v in vacancies]
        return results
    except Exception as e:
        print(f"Ошибка при запросе к HH: {e}")
        return []
