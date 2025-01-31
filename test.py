import requests
from bs4 import BeautifulSoup

def extract_horse_info(html_content):
    # Parse the HTML content using BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')

    # Extract information about horses
    page_div = soup.find_all("table", class_="starter")[0]
    page_div = page_div.find("tbody")
    race_rows = page_div.find_all("tr")
    #print(race_rows)
    for race_row in race_rows:
        racer_info = race_row.find_all("td")
        #print(racer_info)
        for info in racer_info:
            try:
                print(info.find("a").string.strip())
            except Exception:
                if info.string is None:
                    print('-')
                    continue
                print(info.string.strip())
        print()

# Example: Get HTML content from the provided link
while(True):
    try:
        url = 'https://racing.hkjc.com/racing/information/English/racing/RaceCard.aspx'
        response = requests.get(url)

        if response.status_code == 200:
            html_content = response.content
            extract_horse_info(html_content)
            break
        else:
            print(f"Failed to retrieve the HTML content. Status code: {response.status_code}")
    except Exception:
        continue
