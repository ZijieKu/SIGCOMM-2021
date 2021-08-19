import json
from itertools import chain
from pathlib import Path

from crawler.common import (
    get_url, get_browser, get_config,
    fetch_html_content, fetch_all_articles_urls,
    fetch_article_author_info, get_2021_urls
)


def get_author_info() -> dict:
    fname = './results/author_info.json'
    if Path(fname).exists():
        with open(fname, 'r') as f:
            author_info = json.load(f)
        return author_info

    driver = get_browser()
    # , "2021" # requires special parsing because all tabs are not loaded by default
    years = [
        "2001",
        "2002",
        "2021"
    ]
    urls = dict()
    for year in years:
        urls[year] = {'year': year, 'url': get_url(year) if year != '2021' else get_2021_urls()}
    try:
        for year in urls:
            print(f'processing SIGCOMM {year} event...')
            el = urls[year]
            print(f'ACM digital library url: {el["url"]}')

            if year == '2021':
                el['content'] = []
                urls[year]['article_links'] = []
                urls[year]['author_set'] = []
                for subTab in el['url']:
                    content = fetch_html_content(driver, subTab)
                    el['content'].append(content)
                    urls[year]['article_links'].append(fetch_all_articles_urls(content))
                urls[year]['article_links'] = list(chain(*urls[year]['article_links']))
            else:
                el['content'] = fetch_html_content(driver, el['url'])
                urls[year]['article_links'] = fetch_all_articles_urls(el['content'])
            urls[year]['author_set'] = fetch_article_author_info(driver, urls[year])
            print(f'author_set: {urls[year]["author_set"]}')
    except Exception as e:
        print(f'Exception {e}')
    # remember to quit driver
    driver.quit()

    author_info = {
        '2001': list(urls['2001']['author_set']),
        '2002': list(urls['2002']['author_set']),
        '2021': list(urls['2021']['author_set'])
    }
    print(f'dumping author_info to json output: {author_info}')
    with open('./results/author_info.json', 'w') as f:
        json.dump(author_info, f)
    return author_info


def main():
    author_info = get_author_info()
    print(f'author_info: {author_info}')
    intersect_2001_2021 = set(author_info['2001']).intersection(set(author_info['2021']))
    intersect_2002_2021 = set(author_info['2002']).intersection(set(author_info['2021']))
    intersect_0102_2021 = set(author_info['2001']).union(author_info['2002']).intersection(set(author_info['2021']))
    all_three_events = set(author_info['2001']).intersection(author_info['2002']).intersection(set(author_info['2021']))
    print(f'there are {len(intersect_2001_2021)} authors whose paper was accepted in both SIGCOMM 2001 and 2021 events')
    print(f'\tthey are {intersect_2001_2021}')
    print(f'there are {len(intersect_2002_2021)} authors whose paper was accepted in both SIGCOMM 2002 and 2021 events')
    print(f'\tthey are {intersect_2002_2021}')
    print(f'there are {len(intersect_0102_2021)} authors whose paper was accepted in both SIGCOMM (2001/2002) and '
          f'2021 events')
    print(f'\tthey are {intersect_0102_2021}')
    print(
        f'there are {len(all_three_events)} authors whose paper was accepted in 2001, 2002 and 2021 events')
    print(f'\tthey are {all_three_events}')

    print(f'Personal profile can be found here -> https://dl.acm.org/profile/[id]')


if __name__ == '__main__':
    main()
