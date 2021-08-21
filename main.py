import argparse
import json
from itertools import chain
from pathlib import Path

from crawler.common import (
   get_url, get_browser, fetch_html_content, fetch_all_articles_urls,
   fetch_article_author_info, get_2021_urls
)


def get_args_parser():
   parser = argparse.ArgumentParser('info', add_help=False)
   parser.add_argument('--author', action='store_true', default=False)
   parser.add_argument('--affiliation', action='store_true', default=False)

   return parser


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
      '2001': urls['2001']['author_set'],
      '2002': urls['2002']['author_set'],
      '2021': urls['2021']['author_set']
   }
   print(f'dumping author_info to json output: {author_info}')
   with open('./results/author_info.json', 'w') as f:
      json.dump(author_info, f)
   return author_info


def get_affiliation_info(author_info):
   driver = get_browser()
   university_2002 = {}
   university_2021 = {}
   others_2002 = {}
   others_2021 = {}
   manual_check = []
   for year in ['2002', '2021']:
      for author_id in author_info[year]:
         try:
            soup = fetch_html_content(driver, f'https://dl.acm.org/profile/{author_id}')
            name = soup.find('h1', {'class': 'title'}).contents[0]
            print(f'author id is: {author_id}')
            print(f'name is {name}')
            institution_soup = soup.find('ul', {'class': 'list-of-institutions'}).find_all('a')
            for inst in institution_soup:
               inst = inst.contents[0].lower()
               if year == '2002':
                  affiliation_handle(year, inst, university_2002, others_2002)
               elif year == '2021':
                  affiliation_handle(year, inst, university_2021, others_2021)
         except Exception as e:
            print(f'!!manual check => https://dl.acm.org/profile/{author_id}')
            manual_check.append(f'https://dl.acm.org/profile/{author_id}')
            continue

   university = {
      '2002': university_2002,
      '2021': university_2021,
   }
   others = {
      '2002': others_2002,
      '2021': others_2021,
   }
   print(f'dumping university info')
   with open('./results/university_info.json', 'w') as f:
      json.dump(university, f)

   print(f'dumping others info')
   with open('./results/other_info.json', 'w') as f1:
      json.dump(others, f1)

   print(f'dumping manual check info')
   with open('./results/manual_info.json', 'w') as f2:
      json.dump(manual_check, f2)

   driver.quit()


# given all_urls[year][article_links], go thru each article's list of institutions
# 1. determine if it's an academia-only paper or has industry involved
# 2. output the list of universities to the results folder
def academia(all_urls: list):
   universities = []

   keywords = [
      'university', 'college', 'institute of technology', 'uc', 'epfl', 'mit', 'usc', 'virginia tech', 'icsi',
      'cornell', 'eth', 'kaust', 'tu delft', 'uiuc'
   ]

   for year in all_urls.keys:
      # count total number of academia papers in that year
      num_academia = 0
      for article_link in all_urls[year]:
         all_academia = True
         # loop thru the list
         for inst in all_urls[year][article_link]:
            # check if it's an inst
            inst_lower = inst.lower()
            isInst = False
            for key in keywords:
               if key in inst_lower:
                  universities.append(inst)
                  isInst = True

            if not isInst:
               all_academia = False  # if didn't find a key

         # check if this paper is all academia
         if all_academia:
            num_academia += 1

      # print the industry vs. academia count in this year
      print(f'The total number of papers in {year} is {len(all_urls[year])}')
      print(f'Academia paper in {year}: {num_academia}')
      print(f'Industry involved papers in {year}: {len(all_urls[year]) - num_academia}')

   print(f'dumping universities info')
   with open('./results/universities.json', 'w') as f:
      json.dump(universities, f)


def affiliation_handle(year, inst, university, others):
   if 'university' in inst or 'college' in inst or 'institute of technology' in inst:
      university[inst] = university.get(inst, 0) + 1
      print(f'{year} academia {inst} count is {university[inst]}')
   else:
      others[inst] = others.get(inst, 0) + 1
      print(f'{year} others {inst} count is {others[inst]}')


def main(args):
   if args.author:
      author_info = get_author_info()

      multi_profile_author = dict()
      for author_name in (author_info['2001'].keys() | author_info['2002'].keys() | author_info['2021'].keys()):
         ids = set()
         try:
            if author_name in author_info['2001']:
               for id in author_info['2001'][author_name]:
                  ids.add(id)
            if author_name in author_info['2002']:
               for id in author_info['2002'][author_name]:
                  ids.add(id)
            if author_name in author_info['2021']:
               for id in author_info['2021'][author_name]:
                  ids.add(id)
         except Exception as e:
            print(f'cannot process {author_name}')
            continue
         if len(ids) > 1:
            multi_profile_author[author_name] = ids

      print(f'multiple profile authors:')
      for author in multi_profile_author:
         print(f'author with multiple profile: {author} : {multi_profile_author[author]}')

      # print(f'author_info: {author_info}')
      print(f'2001 & 2002 attendees: {len(author_info["2001"].keys() & author_info["2002"].keys())}')
      print(f'2001 & 2021 attendees: {len(author_info["2001"].keys() & author_info["2021"].keys())}')
      print(f'(2001 | 2002) & 2021 attendees: '
            f'{len((author_info["2001"].keys() | author_info["2002"].keys()) & author_info["2021"].keys())}')
      print(f'2001 & 2002 & 2021 attendees: '
            f'{len(author_info["2001"].keys() & author_info["2002"].keys() & author_info["2021"].keys())}')
      # print(f'Personal profile can be found here -> https://dl.acm.org/profile/[id]')

   elif args.affiliation:
      author_info = get_author_info()
      get_affiliation_info(author_info)


if __name__ == '__main__':
   parser = argparse.ArgumentParser('info', parents=[get_args_parser()])
   args = parser.parse_args()
   main(args)
