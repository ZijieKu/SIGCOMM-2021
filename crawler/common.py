import json
from urllib.parse import urljoin, urlencode

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

with open('./crawler/config.json', 'r') as f:
    config = json.loads(f.read())


class URL(str):
    def __new__(cls, *value):
        if value:
            v0 = value[0]
            if not (isinstance(v0, str) or isinstance(v0, URL)):
                raise TypeError(f'Unexpected type for URL: "{type(v0)}"')
            if not (v0.startswith('http://') or v0.startswith('https://')):
                raise ValueError(f'Passed string value "{v0}" is not an'
                                 f' "http*://" or "ws*://" URL')
            return str.__new__(cls, *value)


class DriverException(Exception):
    def __init__(self, message):
        self.message = message


class HTMLContentException(Exception):
    def __init__(self, message):
        self.message = message


def get_browser() -> webdriver:
    try:
        # define browser options
        chrome_options = Options()
        chrome_options.add_argument("--window-size=1920,1080")
        # hide browser information
        chrome_options.add_argument('--headless')
        driver = webdriver.Chrome(executable_path=config['CHROME']['PATH'],
                                  options=chrome_options)
    except Exception as e:
        raise DriverException(f'unable to load chrome driver. see error: {e}')
    return driver


def get_2021_urls() -> list:
    urls = set()
    base_url = config['URL']["2021"]['BASE_URL']
    path = config['URL']["2021"]['PATH']
    params = config['URL']["2021"]['PARAMS']['tocHeading']
    for param in params:
        encoded_param = urlencode({'tocHeading': param})
        urls.add(URL(urljoin(base_url, path + '?' + encoded_param)))
    return urls


def get_url(year: str) -> URL:
    base_url = config['URL'][year]['BASE_URL']
    path = config['URL'][year]['PATH']
    return URL(urljoin(base_url, path))


def fetch_html_content(driver: webdriver, url: str) -> BeautifulSoup:
    try:
        print(f'fetching {url} web content...')
        driver.get(url)
        htmltext = driver.page_source
        soup = BeautifulSoup(htmltext, 'html.parser')
    except Exception as e:
        raise HTMLContentException(f'unable to process web content. see {e}')
    return soup


def fetch_all_articles_urls(soup: BeautifulSoup) -> list:
    articles = soup.find_all('h5', {'class': 'issue-item__title'})
    article_urls = []
    print('parsing article urls...')
    if articles:
        for article in articles:
            if article.find('a', href=True):
                doi_url = article.find('a', href=True).attrs['href']
                article_urls.append(doi_url)
            else:
                print(f'[WARNING] no article link found {article}')
    else:
        raise Exception(f'no `issue-item__title` discovered. please confirm the site is working.')
    return article_urls


def fetch_article_author_info(driver: webdriver, url: dict) -> dict:
    print(f'scrapping article author info...')
    article_authors = dict()  # use {article, authors} pair for verification purpose
    distinct_author_list = dict()
    year = url['year']
    article_full_urls = list()
    try:
        for article_link in url['article_links']:
            article_full_url = urljoin(config['URL'][year]['BASE_URL'], article_link)
            article_full_urls.append(article_full_url)
            author_list = fetch_html_content(driver, article_full_url) \
                .find('ul', {'ariaa-label': 'authors'}) \
                .find_all('li', {'class': 'loa__item'})
            article_authors[article_link] = []
            print(f'\t{len(author_list)} author(s) discovered for article {article_link}')
            for author in author_list:
                author_inst = author.find('span', {'class': 'loa_author_inst'})
                author_name = author.find('span', {'class': 'loa__author-name'})
                try:
                    name = None
                    id = None
                    if author_name and author_name.find('span'):
                        name = author_name.find('span').contents[1]
                    if author_inst and author_inst.find('p') and author_inst.find('p')['data-doi']:
                        id = author_inst.find('p').attrs['data-doi'].split('-')[1]
                        article_authors[article_link].append(id)
                    if name is None or id is None:
                        raise Exception(f'wrong author name: {name} or id: {id}')
                    else:
                        if name in distinct_author_list:
                            distinct_author_list[name].append(id)
                        else:
                            distinct_author_list[name] = [id]
                    print(f'discovered author: {id} - {name}')
                except Exception as e:
                    print(
                        f'[WARNING] please manually investigate {article_full_url} for {author_name} with {author_inst}')
                    continue
        print(
            f'discovered a total of {len(article_full_urls)} articles and {len(distinct_author_list)} distinct authors')
    except Exception as e:
        raise Exception(f'error happened when scrapping author info: {e}')
    return distinct_author_list


def fetch_affiliation_info(driver: webdriver, url: dict) -> dict:
    print(f'scrapping article affiliation info...')
    article_authors = dict()  # use {article, authors} pair for verification purpose
    distinct_author_list = dict()
    article_insts = dict()

    year = url['year']
    article_full_urls = list()
    try:
        for article_link in url['article_links']:
            article_full_url = urljoin(config['URL'][year]['BASE_URL'], article_link)
            article_full_urls.append(article_full_url)
            author_list = fetch_html_content(driver, article_full_url) \
                .find('ul', {'ariaa-label': 'authors'}) \
                .find_all('li', {'class': 'loa__item'})
            article_authors[article_link] = []
            print(f'\t{len(author_list)} author(s) discovered for article {article_link}')
            inst_set = set()
            for author in author_list:
                author_inst = author.find('span', {'class': 'loa_author_inst'})
                author_name = author.find('span', {'class': 'loa__author-name'})
                try:
                    if author_inst and author_inst.find('p'):
                        inst = author_inst.find('p').contents[0]
                        inst_set.add(inst)
                        print(f'discovered institution for {article_full_url} is {inst}')
                except Exception as e:
                    print(
                        f'[WARNING] please manually investigate {article_full_url} for {author_name} with {author_inst}')
                    continue
            article_insts[article_link] = list(inst_set)
        print(
            f'discovered a total of {len(article_full_urls)} articles and {len(distinct_author_list)} distinct authors')
    except Exception as e:
        raise Exception(f'error happened when scrapping author info: {e}')
    return article_insts


def get_config() -> dict:
    return config
