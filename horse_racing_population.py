import locale
import sqlite3
import requests
from bs4 import BeautifulSoup
import concurrent.futures


def retrieve_jockeys():
    url = "https://racing.hkjc.com/racing/information/English/Jockey/JockeyRanking.aspx"

    # Send a GET request to the URL
    response = requests.get(url)

    # Check if the request was successful (status code 200)
    if response.status_code == 200:
        # Parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find the desired portion of the HTML
        content_container = soup.find("div", id="contentContainer")
        content = content_container.find("div", class_="content")
        inner_content = content.find("div", id="innerContent")
        comm_content = inner_content.find("div", class_="commContent")
        ranking = comm_content.find("div", class_="Ranking")
        table = ranking.find("table", class_ = "table_bd")
        table = table.find("tbody", class_="f_tac f_fs12")
        
        tbody = table
        jockey_data = parse_jockey_trainer_html(tbody)
        
        populate_jockey_data(jockey_data, "horseracing_data.db")

    else:
        print("Failed to retrieve HTML content. Status code:", response.status_code)
        
def retrieve_trainers():
    url = "https://racing.hkjc.com/racing/information/English/Trainers/TrainerRanking.aspx"

    # Send a GET request to the URL
    response = requests.get(url)

    # Check if the request was successful (status code 200)
    if response.status_code == 200:
        # Parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find the desired portion of the HTML
        content_container = soup.find("div", id="contentContainer")
        content = content_container.find("div", class_="content")
        inner_content = content.find("div", id="innerContent")
        comm_content = inner_content.find("div", class_="commContent")
        ranking = comm_content.find("div", class_="Ranking")
        table = ranking.find("table", class_ = "table_bd f_fs13")
        table = table.find("tbody", class_="f_tac f_fs12")
        
        tbody = table
        trainer_data = parse_jockey_trainer_html(tbody)
        
        populate_trainer_data(trainer_data, "horseracing_data.db")

    else:
        print("Failed to retrieve HTML content. Status code:", response.status_code)
        
def extract_horses():
    horses = []
    horses = horse_extraction_by_location("https://racing.hkjc.com/racing/information/english/Horse/ListByLocation.aspx?Location=HK", horses)
    horses = horse_extraction_by_location("https://racing.hkjc.com/racing/information/english/Horse/ListByLocation.aspx?Location=CH", horses)
    populate_horse_data(horses, 'horseracing_data.db')
    
def populate_horse_data(horses, db_file):
    # Create connection to SQLite database
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    cursor.execute('''
    DROP TABLE IF EXISTS Horse
    ''')
    
    # Create horse table if it doesn't exist
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Horse (
        name TEXT PRIMARY KEY,
        season_stakes INTEGER,
        total_stakes INTEGER,
        rating INTEGER,
        link TEXT
    );
    ''')
    # Insert or replace jockey data into the database
    cursor.executemany('''
    INSERT OR REPLACE INTO Horse (name, season_stakes, total_stakes, rating, link)
    VALUES (?, ?, ?, ?, ?)
    ''', horses)
    
    # Commit changes and close connection
    conn.commit()
    conn.close()
          
def horse_extraction_by_location(url, horses):
    # Send a GET request to the URL
    response = requests.get(url)

    # Check if the request was successful (status code 200)
    if response.status_code == 200:
        # Parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find the desired portion of the HTML
        content_container = soup.find("div", id="contentContainer")
        content = content_container.find("div", class_="content")
        inner_content = content.find("div", id="innerContent")
        comm_content = inner_content.find("div", class_="commContent")
        table = comm_content.find_all("table", class_ = "bigborder")[1]
        table = table.find('table')
        lis = table.find_all('li')
        
        with concurrent.futures.ThreadPoolExecutor() as executor:
            # Submit tasks for each li element
            future_to_li = {executor.submit(process_li, li): li for li in lis}
            # Retrieve results as they are completed
            for future in concurrent.futures.as_completed(future_to_li):
                li = future_to_li[future]
                try:
                    result = future.result()
                    horses.append(result)
                except Exception as e:
                    print(f"An error occurred for li: {li}: {e}")
        return horses
    else:
        print("Failed to retrieve HTML content. Status code:", response.status_code)

def process_li(li):
    a = li.find('a')
    horse_name = a.get_text().strip()
    link = a['href']
    season_stakes, total_stakes, rating = extract_horse_detail(link)
    return horse_name, season_stakes, total_stakes, rating, link
   
def extract_horse_detail(url):
    url = 'https://racing.hkjc.com'+url
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        horse_profile = soup.find('table', class_ = 'horseProfile')
        tr = horse_profile.find('tr')

        tables = tr.find_all('table', class_ = 'table_eng_text')
        season_stakes, total_stakes, rating = (None, None, None)
        for tr in tables[0].find_all('tr'):
            tds = tr.find_all('td')
            if 'Season Stakes' in tds[0].get_text().strip():
                season_stakes = dollar_to_number(tds[2].get_text().strip())
            if 'Total Stakes' in tds[0].get_text().strip():
                total_stakes = dollar_to_number(tds[2].get_text().strip())
            if season_stakes and total_stakes:
                break
        for tr in tables[1].find_all('tr'):
            tds = tr.find_all('td')
            if 'Current Rating' in tds[0].get_text().strip():
                rating = tds[2].get_text().strip()
                if rating == '':
                    rating = -1
                break
        
        return season_stakes, total_stakes, rating 
        
        
                
    else:
        print("Failed to retrieve HTML content. Status code:", response.status_code)
        return (None, None, None)
    
def parse_jockey_trainer_html(tbody):
    dataset = []

    if tbody:
        # Iterate over each row in the table
        rows = tbody.find_all("tr")
        for row in rows:
            # Extract jockey attributes
            row_data = [data.get_text().strip() for data in row.find_all("td")]
            
            # Extract link
            link = row.find("a")["href"]
            # Add jockey data to list
            dataset.append((*row_data, link))
    return dataset

def populate_jockey_data(jockey_data, db_file):
    # Create connection to SQLite database
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    cursor.execute("drop table if exists jockeys")
    
    # Create jockeys table if it doesn't exist
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS jockeys (
        name TEXT PRIMARY KEY,
        wins INTEGER,
        seconds INTEGER,
        thirds INTEGER,
        fourths INTEGER,
        fifths INTEGER,
        num_races INTEGER,
        prize_money INTEGER,
        link TEXT
    );
    ''')
    
    # Insert or replace jockey data into the database
    cursor.executemany('''
    INSERT OR REPLACE INTO jockeys (name, wins, seconds, thirds, fourths, fifths, num_races, prize_money, link)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', jockey_data)
    
    # Commit changes and close connection
    conn.commit()
    conn.close()
    
def populate_trainer_data(trainer_data, db_file):
    # Create connection to SQLite database
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    cursor.execute("drop table if exists trainers")
    
    # Create jockeys table if it doesn't exist
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS trainers (
        name TEXT PRIMARY KEY,
        wins INTEGER,
        seconds INTEGER,
        thirds INTEGER,
        fourths INTEGER,
        fifths INTEGER,
        num_races INTEGER,
        prize_money INTEGER,
        link TEXT
    );
    ''')
    
    # Insert or replace jockey data into the database
    cursor.executemany('''
    INSERT OR REPLACE INTO trainers (name, wins, seconds, thirds, fourths, fifths, num_races, prize_money, link)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', trainer_data)
    
    # Commit changes and close connection
    conn.commit()
    conn.close()
    
def create_location_distance():
    # Create connection to SQLite database
    conn = sqlite3.connect('horseracing_data.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS location_distance (
        location TEXT,
        distance INTEGER,
        PRIMARY KEY (location, distance)
    );
    ''')
    
    inserts = [
        "INSERT OR REPLACE INTO location_distance (location, distance) VALUES('Happy Valley Turf', 1000)",
        "INSERT OR REPLACE INTO location_distance (location, distance) VALUES('Happy Valley Turf', 1200)",
        "INSERT OR REPLACE INTO location_distance (location, distance) VALUES('Happy Valley Turf', 1650)",
        "INSERT OR REPLACE INTO location_distance (location, distance) VALUES('Happy Valley Turf', 1800)",
        "INSERT OR REPLACE INTO location_distance (location, distance) VALUES('Happy Valley Turf', 2200)",
        "INSERT OR REPLACE INTO location_distance (location, distance) VALUES('Sha Tin AWT', 1200)",
        "INSERT OR REPLACE INTO location_distance (location, distance) VALUES('Sha Tin AWT', 1650)",
        "INSERT OR REPLACE INTO location_distance (location, distance) VALUES('Sha Tin AWT', 1800)",
        "INSERT OR REPLACE INTO location_distance (location, distance) VALUES('Sha Tin Turf', 1000)",
        "INSERT OR REPLACE INTO location_distance (location, distance) VALUES('Sha Tin Turf', 1200)",
        "INSERT OR REPLACE INTO location_distance (location, distance) VALUES('Sha Tin Turf', 1400)",
        "INSERT OR REPLACE INTO location_distance (location, distance) VALUES('Sha Tin Turf', 1600)",
        "INSERT OR REPLACE INTO location_distance (location, distance) VALUES('Sha Tin Turf', 1800)",
        "INSERT OR REPLACE INTO location_distance (location, distance) VALUES('Sha Tin Turf', 2000)",
        "INSERT OR REPLACE INTO location_distance (location, distance) VALUES('Sha Tin Turf', 2200)",
        "INSERT OR REPLACE INTO location_distance (location, distance) VALUES('Sha Tin Turf', 2400)"
    ]
    
    for insert in inserts:
        cursor.execute(insert)
    
    conn.commit()
    conn.close()
    
def insert_jockey_performance():
    # Create connection to SQLite database
    conn = sqlite3.connect('horseracing_data.db')
    cursor = conn.cursor()
    
    cursor.execute("DROP TABLE IF EXISTS jockey_performance")
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS jockey_performance (
        name TEXT,
        location TEXT,
        distance INTEGER,
        win INTEGER,
        seconds INTEGER,
        thirds INTEGER,
        runs INTEGER,
        PRIMARY KEY (name, location, distance),
        FOREIGN KEY (name) REFERENCES jockeys(name),
        FOREIGN KEY (location, distance) REFERENCES location_distance(location, distance)
    );
    ''')
    
    jockeys = cursor.execute("select * from jockeys").fetchall()
    
    jockey_performance = []
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
    # Submit tasks for each jockey
        futures = [executor.submit(extract_jockey_performance, jockey) for jockey in jockeys]

        # Iterate over the completed futures and extend jockey_performance with their results
        for future in concurrent.futures.as_completed(futures):
            jockey_performance.extend(future.result())
    
    cursor.executemany('''
    INSERT OR REPLACE INTO jockey_performance (name, location, distance, win, seconds, thirds, runs)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', jockey_performance)
    conn.commit()
    conn.close()
    
def extract_jockey_performance(jockey):
    url = 'https://racing.hkjc.com' + jockey[8]
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        jockey_profile = soup.find('div', class_ = 'jockey_left commInfo_left')
        nav = jockey_profile.find('div', class_ = 'nav')
        ul = nav.find('ul')
        li = ul.find_all('li')[1]
        url = li.find('a')['href']
        dist_performances = enter_jockey_performance(url)
        result = []
        for dist_performance in dist_performances:
            result.append((jockey[0], *dist_performance))
        return result
        
    else:
        print("Failed to retrieve HTML content. Status code:", response.status_code)
        return None
    
def insert_trainer_performance():
    # Create connection to SQLite database
    conn = sqlite3.connect('horseracing_data.db')
    cursor = conn.cursor()
    
    cursor.execute("DROP TABLE IF EXISTS trainer_performance")
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS trainer_performance (
        name TEXT,
        location TEXT,
        distance INTEGER,
        win INTEGER,
        seconds INTEGER,
        thirds INTEGER,
        runs INTEGER,
        PRIMARY KEY (name, location, distance),
        FOREIGN KEY (name) REFERENCES trainers(name),
        FOREIGN KEY (location, distance) REFERENCES location_distance(location, distance)
    );
    ''')
    
    trainers = cursor.execute("select * from trainers").fetchall()
    
    trainer_performance = []
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        # Submit tasks for each trainer
        futures = [executor.submit(extract_trainer_performance, trainer) for trainer in trainers]

        # Iterate over the completed futures and extend trainer_performance with their results
        for future in concurrent.futures.as_completed(futures):
            trainer_performance.extend(future.result())
    
    cursor.executemany('''
    INSERT OR REPLACE INTO trainer_performance (name, location, distance, win, seconds, thirds, runs)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', trainer_performance)
    
    conn.commit()
    conn.close()
    
def extract_trainer_performance(trainer):
    url = 'https://racing.hkjc.com' + trainer[8]
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        trainer_profile = soup.find('div', class_ = 'trainer_left commInfo_left')
        nav = trainer_profile.find('div', class_ = 'nav')
        ul = nav.find('ul')
        li = ul.find_all('li')[1]
        url = li.find('a')['href']
        dist_performances = enter_trainer_performance(url)
        result = []
        for dist_performance in dist_performances:
            result.append((trainer[0], *dist_performance))
        return result
        
    else:
        print("Failed to retrieve HTML content. Status code:", response.status_code)
        return None
    
def enter_trainer_performance(url):
    url = 'https://racing.hkjc.com' + url
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        commContent = soup.find('div', class_='trainerWinStat commContent')
        performance = commContent.find('div', class_='performance')
        table = performance.find('table', class_='table_bd')
        tbody = table.find('tbody')
        tr = tbody.find_all('tr')
        dist_performances = []
        for i in range(5):
            tds = tr[i].find_all('td')
            if i == 0:
                tds = tds[1:]
            dist = tds[0].get_text().strip()
            win = tds[1].get_text().strip()
            seconds = tds[2].get_text().strip()
            thirds = tds[3].get_text().strip()
            runs = tds[4].get_text().strip()
            dist_performances.append(('Happy Valley Turf', dist, win, seconds, thirds, runs))
        for i in range(5, 8):
            tds = tr[i].find_all('td')
            if i == 5:
                tds = tds[2:]
            dist = tds[0].get_text().strip()
            win = tds[1].get_text().strip()
            seconds = tds[2].get_text().strip()
            thirds = tds[3].get_text().strip()
            runs = tds[4].get_text().strip()
            dist_performances.append(('Sha Tin AWT', dist, win, seconds, thirds, runs))
        for i in range(8, 16):
            tds = tr[i].find_all('td')
            if i == 8:
                tds = tds[1:]
            dist = tds[0].get_text().strip()
            win = tds[1].get_text().strip()
            seconds = tds[2].get_text().strip()
            thirds = tds[3].get_text().strip()
            runs = tds[4].get_text().strip()
            dist_performances.append(('Sha Tin Turf', dist, win, seconds, thirds, runs))
        
        return dist_performances
    else:
        print("Failed to retrieve HTML content. Status code:", response.status_code)
        return None
    
def enter_jockey_performance(url):
    url = 'https://racing.hkjc.com' + url
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        commContent = soup.find('div', class_='jockeyWinStat commContent')
        performance = commContent.find('div', class_='performance')
        tbody = performance.find('tbody', class_='f_fs13')
        tr = tbody.find_all('tr')
        dist_performances = []
        for i in range(5):
            tds = tr[i].find_all('td')
            if i == 0:
                tds = tds[1:]
            dist = tds[0].get_text().strip()
            win = tds[1].get_text().strip()
            seconds = tds[2].get_text().strip()
            thirds = tds[3].get_text().strip()
            runs = tds[4].get_text().strip()
            dist_performances.append(('Happy Valley Turf', dist, win, seconds, thirds, runs))
        for i in range(5, 8):
            tds = tr[i].find_all('td')
            if i == 5:
                tds = tds[2:]
            dist = tds[0].get_text().strip()
            win = tds[1].get_text().strip()
            seconds = tds[2].get_text().strip()
            thirds = tds[3].get_text().strip()
            runs = tds[4].get_text().strip()
            dist_performances.append(('Sha Tin AWT', dist, win, seconds, thirds, runs))
        for i in range(8, 16):
            tds = tr[i].find_all('td')
            if i == 8:
                tds = tds[1:]
            dist = tds[0].get_text().strip()
            win = tds[1].get_text().strip()
            seconds = tds[2].get_text().strip()
            thirds = tds[3].get_text().strip()
            runs = tds[4].get_text().strip()
            dist_performances.append(('Sha Tin Turf', dist, win, seconds, thirds, runs))
        
        return dist_performances
    else:
        print("Failed to retrieve HTML content. Status code:", response.status_code)
        return None
    
def dollar_to_number(dollar_str):
    # Set the locale to en_US to handle dollar format
    locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
    
    # Remove any non-numeric characters from the string
    numeric_str = locale.atof(dollar_str.strip('$').replace(',', ''))
    
    return numeric_str

def insert_horse_performance():
    # Create connection to SQLite database
    conn = sqlite3.connect('horseracing_data.db')
    cursor = conn.cursor()
    
    cursor.execute("DROP TABLE IF EXISTS horse_performance")
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS horse_performance (
        name TEXT,
        location TEXT,
        distance INTEGER,
        win INTEGER,
        seconds INTEGER,
        thirds INTEGER,
        runs INTEGER,
        PRIMARY KEY (name, location, distance),
        FOREIGN KEY (name) REFERENCES horse(name),
        FOREIGN KEY (location, distance) REFERENCES location_distance(location, distance)
    );
    ''')
    
    horses = cursor.execute("select * from horse").fetchall()
    
    horse_performance = []
    # Concurrently extract horse performance for each horse
    with concurrent.futures.ThreadPoolExecutor() as executor:
        # Submit tasks for each horse
        future_to_horse = {executor.submit(extract_horse_performance, horse): horse for horse in horses}
        
        # Retrieve results as they are completed
        for future in concurrent.futures.as_completed(future_to_horse):
            horse = future_to_horse[future]
            performances = future.result()
            if performances:
                horse_performance.extend(performances)
    
    cursor.executemany('''
    INSERT OR REPLACE INTO horse_performance (name, location, distance, win, seconds, thirds, runs)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', horse_performance)
    
    conn.commit()
    conn.close()
    
def extract_horse_performance(horse):
    url = 'https://racing.hkjc.com' + horse[4]
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        trainer_profile = soup.find('table', class_ = 'horseProfile')
        table = trainer_profile.find('table')
        tbody = table.find('tbody')
        tr = tbody.find_all('tr')[1]
        td = tr.find('td', class_='table_eng_text')
        li = td.find_all('li')[2]
        url = li.find('a')['href']
        dist_performances = enter_horse_performance(url)
        result = []
        for dist_performance in dist_performances:
            result.append((horse[0], *dist_performance))
        return result
        
    else:
        print("Failed to retrieve HTML content. Status code:", response.status_code)
        return None
    
def enter_horse_performance(url):
    url = 'https://racing.hkjc.com' + url
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        performance = soup.find('table', class_='horseperformance')
        if performance:
            tbody = performance.find('tbody')
            trs = tbody.find_all('tr')
            dist_performances = []
            start = 0
            location = None
            for tr in trs:
                tds = tr.find_all('td')
                if len(tds) == 1:
                    start += 1
                    continue
                if start == 2:
                    if tds[0].get_text() != '':
                        location = tds[0].get_text().strip()
                    try:
                        distance = int(tds[1].get_text().strip().strip('m'))
                    except ValueError:
                        continue
                    runs = int(tds[2].get_text().strip())
                    win = int(tds[3].get_text().strip())
                    seconds = int(tds[4].get_text().strip())
                    thirds = int(tds[5].get_text().strip())
                    dist_performances.append((location, distance, win, seconds, thirds, runs))
                elif start == 3:
                    break
            return dist_performances
        else:
            return []
    else:
        print("Failed to retrieve HTML content. Status code:", response.status_code)
        return None

def create_racecard_table():
    # Create connection to SQLite database
    conn = sqlite3.connect('horseracing_data.db')
    cursor = conn.cursor()
    
    cursor.execute("DROP TABLE IF EXISTS racecard")
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS racecard (
        dist TEXT,
        track TEXT,
        horse_num INTEGER PRIMARY KEY,
        last_six_runs TEXT,
        color TEXT,
        horse TEXT,
        brand TEXT,
        weight INTEGER,
        jockey TEXT,
        overwt TEXT,
        draw INTEGER,
        trainer TEXT,
        intl_rtg INTEGER,
        rtg INTEGER,
        rtg_change INTEGER,
        horse_wt_declaration INTEGER,
        wt_change_vdeclaration INTEGER,
        best_time TEXT,
        age INTEGER,
        wfa TEXT,
        sex TEXT,
        season_stakes INTEGER,
        priority TEXT,
        days_since_last INTEGER,
        gear TEXT,
        owner TEXT,
        sire TEXT,
        dam TEXT,
        import_cat TEXT,
        FOREIGN KEY (horse) REFERENCES horse(name),
        FOREIGN KEY (jockey) REFERENCES jockeys(name),
        FOREIGN KEY (trainer) REFERENCES trainers(name)
    );
    ''')
    conn.commit()
    conn.close()

def initialize():
    
    retrieve_jockeys()
    print('retrieved jockeys')
    retrieve_trainers()
    print('retrieved trainers')
    extract_horses()
    print('extracted horses')
    create_location_distance()
    print('identified tracks')
    insert_jockey_performance()
    print('inserted jockey performance')
    insert_trainer_performance()
    print('inserted trainer performance')
    insert_horse_performance()
    print('inserted horse performance')
    #create_racecard_table()
    
if __name__ == "__main__":
    initialize()
    