# SIGCOMM-2021

---

* This scrapper was created to know more about ex-SIGCOMM authors, whose papers were accepted in the past and the current event.

## Chrome Driver
* https://chromedriver.chromium.org/downloads

## Notes
* Do NOT use the following in the `fetch_all_issues`, because not all authors will be included.
```python
doi_links = soup.find_all('ul', attrs={'aria-label': 'authors'})
```
