import sqlite3
import requests
from bs4 import BeautifulSoup
import sys
import re

def insert_racecard(racedate, racecourse, raceno):
    url = 'https://racing.hkjc.com/racing/information/English/racing/RaceCard.aspx?RaceDate={0}&Racecourse={1}&RaceNo={2}'.format(racedate, racecourse, raceno)
    response = requests.get(url)
    if response.status_code == 200:
        try:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            extract_dist = soup.find('div', class_ = 'commContent raceCard').find('div', class_='margin_top10').find('div', class_ = 'f_fs13').get_text()
            pat = r'\d+M'
            
            dist = re.findall(pat, extract_dist)[0][:-1]
            
            print(dist)
            
            
            racecard_table = soup.find('table', id = 'racecardlist')
            tbody = racecard_table.find('tbody').find('tbody')
            trs = tbody.find_all('tr')
            racecard = []
            if racecourse == "ST":
                racecourse = 'Sha Tin Turf'
            elif racecourse == 'HV':
                racecourse = 'Happy Valley Turf'
            else:
                raise ValueError("It is Sha Tin AWT")
            for tr in trs:
                tds = tr.find_all('td')
                lst =[dist, racecourse]
                valid_entry = True
                for td in tds:
                    try:
                        if td.find('span', class_='color_red').get_text().strip() == '(Scratched)':
                            valid_entry = False
                            break
                    except:
                        if td.get_text() == None:
                            lst.append('')
                        else:
                            pattern = r'\([-+]?\d+\)'
                            stripped_text = re.sub(pattern, '', td.get_text()).strip()
                            lst.append(stripped_text)
                if valid_entry:
                    racecard.append(tuple(lst))
                
            conn = sqlite3.connect('horseracing_data.db')
            cursor = conn.cursor()
            cursor.execute('DELETE FROM racecard')
            cursor.executemany('''
            INSERT OR REPLACE INTO racecard (
            dist,
            track,
            horse_num,
            last_six_runs,
            color,
            horse,
            brand,
            weight,
            jockey,
            overwt,
            draw,
            trainer,
            intl_rtg,
            rtg,
            rtg_change,
            horse_wt_declaration,
            wt_change_vdeclaration,
            best_time,
            age,
            wfa,
            sex,
            season_stakes,
            priority,
            days_since_last,
            gear,
            owner,
            sire,
            dam,
            import_cat)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', racecard)
            conn.commit()
            # TODO: Eliminate scratched out horse
            cursor.execute("DELETE FROM racecard WHERE horse LIKE '%(Scratched)%';")
            conn.close()
            
            
            
            return 0
        except AttributeError:
            print('Double check if the racecard information is available at provided url')
            print(url)
            return 1
    else:
        print("Failed to retrieve HTML content. Status code:", response.status_code)
        return 1

def rank_racecards_by_jockey_performance():
    conn = sqlite3.connect('horseracing_data.db')
    cursor = conn.cursor()

    # Retrieve jockey performance data from the databas
    cursor.execute('''
        SELECT rc.horse, jw.win, jw.seconds, jw.thirds, jw.runs
        FROM racecard rc
        INNER JOIN jockey_performance jw ON rc.jockey = jw.name
        WHERE rc.track = jw.location and jw.distance = rc.dist
    ''')
    racecards_performance = cursor.fetchall()

    # Define a function to calculate the performance score for each racecard
    def calculate_performance_score(racecard_performance):
        wins, seconds, thirds, num_races = racecard_performance[1:]
        performance_score = (wins * 3 + seconds * 2 + thirds * 1)/num_races
        return performance_score

    # Calculate performance score for each racecard and sort them in descending order
    ranked_racecards = sorted(racecards_performance, key=lambda x: calculate_performance_score(x), reverse=True)
    cursor.execute('''
                   DROP TABLE IF EXISTS temp_rjockey_ranking;
                   ''')
    
    # Create a temporary table to store the ranking
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS temp_rjockey_ranking (
            rank INT PRIMARY KEY,
            horse TEXT,
            score REAL
        )
    ''')

    # Insert ranked racecards into the temporary table
    cursor.executemany('''
        INSERT INTO temp_rjockey_ranking (rank, horse, score)
        VALUES (?, ?, ?)
    ''', [(i+1, ranked_racecards[i][0], calculate_performance_score(ranked_racecards[i])) for i in range(len(ranked_racecards))])
    conn.commit()

    cursor.execute('''
        SELECT * FROM temp_rjockey_ranking
    ''')
    ranked_racecards_from_temp_table = cursor.fetchall()
    print('by_jockey')
    print_rank(ranked_racecards_from_temp_table)
    write_rank(ranked_racecards_from_temp_table, 'Jockey Historic Performance on Track and Distance')    
    conn.close()
    
def rank_racecards_by_trainer_performance():
    conn = sqlite3.connect('horseracing_data.db')
    cursor = conn.cursor()

    # Retrieve trainer performance data from the database
    cursor.execute('''
        SELECT rc.horse, tw.win, tw.seconds, tw.thirds, tw.runs
        FROM racecard rc
        INNER JOIN trainer_performance tw ON rc.trainer = tw.name
        WHERE rc.track = tw.location and tw.distance = rc.dist
    ''')
    racecards_performance = cursor.fetchall()
    # Calculate performance score for each racecard and sort them in descending order
    ranked_racecards = sorted(racecards_performance, key=lambda x: calculate_performance_score(x), reverse=True)
    
    cursor.execute("DROP TABLE IF EXISTS temp_rtrainer_ranking")
    
    # Create a temporary table to store the ranking
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS temp_rtrainer_ranking (
            rank INT PRIMARY KEY,
            horse TEXT,
            score REAL
        )
    ''')

    # Insert ranked racecards into the temporary table
    cursor.executemany('''
        INSERT INTO temp_rtrainer_ranking (rank, horse, score)
        VALUES (?, ?, ?)
    ''', [(i+1, ranked_racecards[i][0], calculate_performance_score(ranked_racecards[i])) for i in range(len(ranked_racecards))])
    conn.commit()
    # Display the ranked racecards from the temporary table
    cursor.execute('''
        SELECT * FROM temp_rtrainer_ranking
    ''')
    ranked_racecards_from_temp_table = cursor.fetchall()
    print('by_trainer')
    print_rank(ranked_racecards_from_temp_table)
    write_rank(ranked_racecards_from_temp_table, 'Trainer Historic Performance on Track and Distance')
    conn.close()
    
def rank_racecards_by_horse_performance():
    conn = sqlite3.connect('horseracing_data.db')
    cursor = conn.cursor()

    # Retrieve trainer performance data from the database
    cursor.execute('''
        SELECT rc.horse, hw.win, hw.seconds, hw.thirds, hw.runs
        FROM racecard rc
        INNER JOIN horse_performance hw ON rc.horse = hw.name
        WHERE rc.track = hw.location and hw.distance = rc.dist
    ''')
    racecards_performance = cursor.fetchall()
    

    # Calculate performance score for each racecard and sort them in descending order
    ranked_racecards = sorted(racecards_performance, key=lambda x: calculate_performance_score(x), reverse=True)
    cursor.execute('''
                   DROP TABLE IF EXISTS temp_rhorse_ranking;
                   ''')
    
    # Create a temporary table to store the ranking
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS temp_rhorse_ranking (
            rank INT PRIMARY KEY,
            horse TEXT,
            score REAL
        )
    ''')

    # Insert ranked racecards into the temporary table
    cursor.executemany('''
        INSERT INTO temp_rhorse_ranking (rank, horse, score)
        VALUES (?, ?, ?)
    ''', [(i+1, ranked_racecards[i][0], calculate_performance_score(ranked_racecards[i])) for i in range(len(ranked_racecards))])
    conn.commit()
    # Display the ranked racecards from the temporary table
    cursor.execute('''
        SELECT * FROM temp_rhorse_ranking
    ''')
    ranked_racecards_from_temp_table = cursor.fetchall()
    print('by_horse')
    
    print_rank(ranked_racecards_from_temp_table)
    write_rank(ranked_racecards_from_temp_table, 'Horse Historic Performance on Track and Distance')
    conn.close()
    
def rank_by_stakes():
    conn = sqlite3.connect('horseracing_data.db')
    cursor = conn.cursor()
    # Retrieve horse stakes data from the database
    cursor.execute('''
        SELECT rc.horse, h.season_stakes, h.total_stakes
        FROM racecard rc
        INNER JOIN horse h ON rc.horse = h.name
    ''')
    racecards_stakes = cursor.fetchall()
    
    ranked_racecards = sorted(racecards_stakes, key=lambda x: calc_stakes_score(x), reverse=True)
    cursor.execute('''
                   DROP TABLE IF EXISTS temp_stakes_ranking;
                   ''')
    
    # Create a temporary table to store the ranking
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS temp_stakes_ranking (
            rank INT PRIMARY KEY,
            horse TEXT,
            score REAL
        )
    ''')
    
    # Insert ranked racecards into the temporary table
    cursor.executemany('''
        INSERT INTO temp_stakes_ranking (rank, horse, score)
        VALUES (?, ?, ?)
    ''', [(i+1, ranked_racecards[i][0], calc_stakes_score(ranked_racecards[i])) for i in range(len(ranked_racecards))])
    conn.commit()
    # Display the ranked racecards from the temporary table
    cursor.execute('''
        SELECT * FROM temp_stakes_ranking
    ''')
    ranked_racecards_from_temp_table = cursor.fetchall()
    print('by_stakes')
    print_rank(ranked_racecards_from_temp_table)
    write_rank(ranked_racecards_from_temp_table, 'Stakes Won by Horse')
    conn.close()
    
def rank_horses_by_last_six_rounds():
    conn = sqlite3.connect('horseracing_data.db')
    cursor = conn.cursor()

    # Retrieve horse data from the database
    cursor.execute('''
        SELECT horse, last_six_runs
        FROM racecard
    ''')
    horses_data = cursor.fetchall()

    # Define a function to calculate the score for each horse
    def calculate_score(last_six_runs):
        if last_six_runs == '-':
            return float('inf')  # Assign a high score for horses with no records
        placements = [int(place) for place in last_six_runs.split('/') if place and place != '-']
        score = sum(placements) + (6 - len(placements)) * 3  # Penalize missing rounds
        # Check if the placement has improved
        if len(placements) == 6 and all(placements[i] <= placements[i+1] for i in range(5)):
            score -= 5  # Additional score for improved placement
        return score
    
    # Calculate scores for each horse and sort them in ascending order
    ranked_horses = sorted(horses_data, key=lambda x: calculate_score(x[1]))
    
    cursor.execute("DROP TABLE IF EXISTS temp_recent_ranking")
    
    # Create a temporary table to store the ranking
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS temp_recent_ranking (
            rank INT PRIMARY KEY,
            horse TEXT,
            score REAL
        )
    ''')
    
    # Insert ranked horses into the temporary table
    for rank, (horse, last_six_runs) in enumerate(ranked_horses, start=1):
        score = calculate_score(last_six_runs)
        cursor.execute('''
            INSERT INTO temp_recent_ranking (rank, horse, score)
            VALUES (?, ?, ?)
        ''', (rank, horse, score))
    conn.commit()
    ranked_horses = cursor.execute('select * from temp_recent_ranking').fetchall()
    print('by_recent')
    print_rank(ranked_horses)
    write_rank(ranked_horses, 'Recent Placement')
    conn.close()
    
def rank_by_barrier_draw():
    conn = sqlite3.connect('horseracing_data.db')
    cursor = conn.cursor()

    # Retrieve horse data from the database
    cursor.execute('''
        SELECT horse, draw
        FROM racecard
    ''')
    horses_data = cursor.fetchall()

    # Define a function to calculate the score for each horse
    def calculate_score(draw):
        return draw
    
    # Calculate scores for each horse and sort them in ascending order
    ranked_horses = sorted(horses_data, key=lambda x: calculate_score(x[1]))
    
    cursor.execute("DROP TABLE IF EXISTS temp_draw_ranking")
    
    # Create a temporary table to store the ranking
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS temp_draw_ranking (
            rank INT PRIMARY KEY,
            horse TEXT,
            score REAL
        )
    ''')
    
    # Insert ranked horses into the temporary table
    for rank, (horse, last_six_runs) in enumerate(ranked_horses, start=1):
        score = calculate_score(last_six_runs)
        cursor.execute('''
            INSERT INTO temp_draw_ranking (rank, horse, score)
            VALUES (?, ?, ?)
        ''', (rank, horse, score))
    conn.commit()
    
    ranked_horses = cursor.execute('select * from temp_draw_ranking').fetchall()
    print('by_draw')
    print_rank(ranked_horses)
    write_rank(ranked_horses, 'Barrier Draw')
    conn.close()
    
def rank_horses_by_rtg_change():
    conn = sqlite3.connect('horseracing_data.db')
    cursor = conn.cursor()

    # Retrieve horse data from the database
    cursor.execute('''
        SELECT horse, rtg_change
        FROM racecard
    ''')
    horses_data = cursor.fetchall()

    # Define a function to calculate the score for each horse
    def calculate_score(rtg_change):
        if rtg_change == '-':
            return float('inf')  # Assign a high score for horses with no change
        else:
            return int(rtg_change)  # Use the value of the change

    # Calculate scores for each horse and sort them in ascending order
    ranked_horses = sorted(horses_data, key=lambda x: calculate_score(x[1]))

    cursor.execute("DROP TABLE IF EXISTS temp_rtg_change_ranking")
    
    # Create a temporary table to store the ranking
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS temp_rtg_change_ranking (
            rank INT PRIMARY KEY,
            horse TEXT,
            score REAL
        )
    ''')

    # Insert ranked horses into the temporary table
    for rank, (horse, rtg_change) in enumerate(ranked_horses, start=1):
        score = calculate_score(rtg_change)
        cursor.execute('''
            INSERT INTO temp_rtg_change_ranking (rank, horse, score)
            VALUES (?, ?, ?)
        ''', (rank, horse, score))

    # Commit changes to the database
    conn.commit()

    rank = cursor.execute("select * from temp_rtg_change_ranking").fetchall()
    print('by_rtg_change')
    print_rank(rank)
    write_rank(rank, 'Rating Change')
    
    # Close the connection
    conn.close()
    
def create_master_ranking(*weights):
    if len(weights) != 7:
        print("Error: Please provide weights for all 7 ranking criteria.")
        return

    conn = sqlite3.connect('horseracing_data.db')
    cursor = conn.cursor()

    # Retrieve data from the temporary ranking tables
    tables = [
        'temp_rjockey_ranking',
        'temp_rtrainer_ranking',
        'temp_rhorse_ranking',
        'temp_stakes_ranking',
        'temp_recent_ranking',
        'temp_draw_ranking',
        'temp_rtg_change_ranking'
    ]

    # Create a dictionary to store the rankings of each horse in each table
    horse_rankings = {}
    for i, table in enumerate(tables):
        cursor.execute(f'SELECT horse FROM {table} ORDER BY rank')
        ranking = cursor.fetchall()
        for j, (horse,) in enumerate(ranking, start=1):
            if horse not in horse_rankings:
                cursor.execute('SELECT COUNT(*) FROM racecard')
                total_entries = cursor.fetchone()[0]
                horse_rankings[horse] = [total_entries] * 7  # Default to total number of entries in racecard
            horse_rankings[horse][i] = j

            
    

    # Calculate the average rank for each horse based on the weights
    master_ranking = {}
    for horse, ranks in horse_rankings.items():
        average_rank = sum(rank * weight for rank, weight in zip(ranks, weights))
        master_ranking[horse] = average_rank

    # Sort horses by their average ranks
    sorted_master_ranking = sorted(master_ranking.items(), key=lambda x: x[1])
    
    cursor.execute("DROP TABLE IF EXISTS temp_master_ranking")

    # Create a temporary table to store the master ranking
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS temp_master_ranking (
            rank INT PRIMARY KEY,
            horse TEXT,
            score REAL
        )
    ''')

    # Insert ranked horses into the temporary table
    for rank, (horse, score) in enumerate(sorted_master_ranking, start=1):
        cursor.execute('''
            INSERT INTO temp_master_ranking (rank, horse, score)
            VALUES (?, ?, ?)
        ''', (rank, horse, score))

    # Commit changes to the database
    conn.commit()

    # Display the master ranking
    cursor.execute('SELECT * FROM temp_master_ranking')
    master_ranking_data = cursor.fetchall()
    print('Master Ranking')
    print_rank(master_ranking_data)
    write_rank(master_ranking_data, 'Master Ranking')
    # Close the connection
    conn.close()

def write_rank(ranked_data, standard):
    global file
    with open(file, 'a') as f:
        f.write("\nRank Standard : " + standard)
        f.write("\nRank | Horse Name | Score\n")
        f.write("---------------------------\n")
        for horse in ranked_data:
            f.write(f"{horse[0]}| {horse[1]}| {horse[2]}\n")

    
def print_rank(ranked_data):
    print("Rank | Horse Name | Score")
    print("---------------------------")
    for horse in ranked_data:
        print(f"{horse[0]}| {horse[1]}| {horse[2]}")

def calc_stakes_score(horse_stakes):
    season, total = horse_stakes[1:]
    return season


# Define a function to calculate the performance score for each racecard
def calculate_performance_score(racecard_performance):
    wins, seconds, thirds, num_races = racecard_performance[1:]
    performance_score = (wins * 10 + seconds * 6 + thirds * 4)/num_races
    return performance_score
        
if __name__ == "__main__":
    global file
    if insert_racecard(sys.argv[1],sys.argv[2],sys.argv[3]) == 0:
        if len(sys.argv) == 5:
            file = sys.argv[4]
            with open(file, 'w') as f:
                f.write("\nRace Day : " + sys.argv[1])
                f.write("\nRace track : "+ sys.argv[2])
                f.write("\nRace Number : "+ sys.argv[3])
                f.write("\n---------------------------\n")
    
        rank_racecards_by_jockey_performance()
        rank_racecards_by_horse_performance()
        rank_racecards_by_trainer_performance()
        rank_by_stakes()
        rank_horses_by_last_six_rounds()
        rank_by_barrier_draw()
        rank_horses_by_rtg_change()
        
        create_master_ranking(1,1,1,1,1,1,1)
    
