import requests
from bs4 import BeautifulSoup

def fetch_trending_repos(language, date_range):
    url = f'https://github.com/trending/{language}?since={date_range}'
    response = requests.get(url)
    if response.status_code != 200:
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    repo_list = soup.find_all('article', class_='Box-row')

    trending_repos = []
    for repo in repo_list:
        name_tag = repo.find('h2', class_='h3')
        name = name_tag.text.strip().replace('\n', '').replace(' ', '') if name_tag else 'Unknown'

        url = f"https://github.com{name}" if name != 'Unknown' else 'Unknown'

        description_tag = repo.find('p', class_='col-9')
        description = description_tag.text.strip() if description_tag else 'No description'

        language_tag = repo.find('span', itemprop='programmingLanguage')
        repo_language = language_tag.text.strip() if language_tag else 'Unknown'

        stars_tag = repo.find('a', class_='Link--muted')
        stars = stars_tag.text.strip().replace(',', '') if stars_tag else '0'

        trending_repos.append({
            'name': name,
            'url': url,
            'description': description,
            'language': repo_language,
            'stars': int(stars) if stars.isdigit() else 0
        })

    return trending_repos