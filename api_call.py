import requests
import json
import os
import sqlite3
from datetime import datetime, timedelta
import time
from dateutil.relativedelta import relativedelta
import pandas as pd
import geopandas as gpd
import csv
from shapely.geometry import Point
from shapely.ops import cascaded_union
from geopy.distance import geodesic
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


# Function to make the API call and insert the data into the database
def make_api_call():
    # Connect to the SQLite database
    conn = sqlite3.connect('mydatabase.db')
    c = conn.cursor()

    # Create a table in the database to store the data
    c.execute('CREATE TABLE IF NOT EXISTS mytable (nr INTEGER PRIMARY KEY, lat REAL, lng REAL, specii TEXT, stare TEXT, emiteAvize INTEGER, date_added TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS new_entries (nr INTEGER PRIMARY KEY, lat REAL, lng REAL, specii TEXT, stare TEXT, emiteAvize INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS temp_table (nr INTEGER PRIMARY KEY, lat REAL, lng REAL, stare TEXT, emiteAvize INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS apv_data (nr TEXT PRIMARY KEY, denumire TEXT, emitent_denumire TEXT, autorizatie_titular TEXT, ocol TEXT, volumInitial REAL, volum REAL, stare TEXT, tratament TEXT, naturaProdus TEXT, judet TEXT, emiteAvize INTEGER, national_park INTEGER, lat REAL, lng REAL, date_added TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS national_parks (nr INTEGER PRIMARY KEY, lat REAL, lng REAL, index_right INTEGER, localId TEXT, CharacterS TEXT, text TEXT, Tip_NP TEXT, Arie REAL, Cod NP)')

    # Check if the response has been cached and is less than 24 hours old
    cache_file = 'ignore_folder/response_cache.json'
    cache_time_limit = 86400  # 24 hours in seconds
    if os.path.exists(cache_file):
        cache_modified_time = os.path.getmtime(cache_file)
        current_time = time.time()
        if current_time - cache_modified_time <= cache_time_limit:
            with open(cache_file, 'r') as f:
                response_text = f.read()
        else:
            # If the cache is older than 24 hours, make a request to the API and cache the response
            response = requests.get('https://www.inspectorulpadurii.ro/api/apv/locations?numar=')
            response_text = response.text
            with open(cache_file, 'w') as f:
                f.write(response_text)
    else:
        # If the cache file doesn't exist, make a request to the API and cache the response
        response = requests.get('https://www.inspectorulpadurii.ro/api/apv/locations?numar=')
        response_text = response.text
        with open(cache_file, 'w') as f:
            f.write(response_text)

    # Parse the JSON response and extract the desired fields
    data = json.loads(response_text)
    desired_fields = [{'nr': item['nr'], 'lat': item['latLng']['lat'], 'lng': item['latLng']['lng'], 'stare': item['stare'], 'emiteAvize': item['emiteAvize']} for item in data]

    # Insert or replace the new data into the temporary table
    for item in desired_fields:
        c.execute('INSERT OR REPLACE INTO temp_table (nr, lat, lng, stare, emiteAvize) VALUES (?, ?, ?, ?, ?)', (item['nr'], item['lat'], item['lng'], item['stare'], item['emiteAvize']))


    # Select the rows from the temporary table where emiteAvize is True
    c.execute('SELECT nr FROM temp_table WHERE emiteAvize = 1')
    result = c.fetchall()
    nr_list = [row[0] for row in result]
        
    for nr in nr_list:
        c.execute('SELECT * FROM mytable WHERE nr = ?', (nr,))
        if not c.fetchone():  # If the nr doesn't exist in mytable
            c.execute('SELECT * FROM temp_table WHERE nr = ?', (nr,))
            new_entry = c.fetchone()
            current_date = datetime.now().strftime('%Y-%m-%d')
            c.execute('INSERT OR REPLACE INTO mytable (nr, lat, lng, stare, emiteAvize, date_added) VALUES (?, ?, ?, ?, ?, ?)', (new_entry[0], new_entry[1], new_entry[2], new_entry[3], new_entry[4], current_date))
            c.execute('INSERT INTO new_entries (nr, lat, lng, stare, emiteAvize) VALUES (?, ?, ?, ?, ?)', (new_entry[0], new_entry[1], new_entry[2], new_entry[3], new_entry[4]))


    # Commit the changes to the database
    conn.commit()

    # Make a request to add the species into table
    c.execute('SELECT nr FROM new_entries')
    result = c.fetchall()
    for entry in result:
        nr = entry[0]
        response = requests.get(f'https://www.inspectorulpadurii.ro/api/apv/{nr}/grupe-specii')
        data_specii = response.json()
        # Check if the data is a list
        if isinstance(data_specii, list):
            # Iterate over the list and replace "RĂȘINOASE" with "RASINOASE" in each element
            for i in range(len(data_specii)):
                if isinstance(data_specii[i], str):
                    data_specii[i] = data_specii[i].replace("RĂȘINOASE", "RASINOASE")
        data_specii_str = json.dumps(data_specii)

        c.execute("UPDATE mytable SET specii = ? WHERE nr = ?", (data_specii_str, nr))
        c.execute("UPDATE new_entries SET specii = ? WHERE nr = ?", (data_specii_str, nr))



    # Make a request to the API for each new entry
    c.execute('SELECT nr FROM new_entries WHERE specii LIKE "%RASINOASE%" AND emiteAvize = ?', (True,))
    result = c.fetchall()
    for entry in result:
        nr = entry[0]
        response = requests.get(f'https://www.inspectorulpadurii.ro/api/apv/{nr}')
        data_apv = json.loads(response.text)

        # Extract the desired fields from the API response
        denumire = data_apv['denumire']
        emitent_denumire = data_apv['emitent']['denumire']
        autorizatie_titular = data_apv['autorizatie']['titular']
        ocol = data_apv['ocol']
        volumInitial = data_apv['volumInitial']
        volum = data_apv['volumGrupeSpecii']['RĂȘINOASE']
        stare = data_apv['stare']
        tratament = data_apv['tratament']
        naturaProdus = data_apv['naturaProdus']
        judet = data_apv['judet']
        date_added = datetime.now().strftime('%Y-%m-%d')

        # Insert the new data into the apv_data table
        c.execute('INSERT INTO apv_data (nr, denumire, emitent_denumire, autorizatie_titular, ocol, volumInitial, volum, stare, tratament, naturaProdus, judet, date_added) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', (nr, denumire, emitent_denumire, autorizatie_titular, ocol, volumInitial, volum,  stare, tratament, naturaProdus, judet, date_added))

    # Make a request to update emiteAvize in apv_data table based on response_cache.json
    with open(cache_file, 'r') as f:
        response_text = f.read()
    data_cache = json.loads(response_text)
    emiteAvize_values = {item['nr']: item['emiteAvize'] for item in data_cache}

    for nr, emiteAvize in emiteAvize_values.items():
        c.execute("UPDATE apv_data SET emiteAvize = ? WHERE nr = ?", (emiteAvize, nr))


    # National Parks Check
    

    df = pd.read_sql_query("SELECT nr, lat, lng FROM mytable", conn)
    points_geodf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.lng, df.lat), crs='EPSG:4326')
    
    shp_poli_np = 'shp_files/np_poli.shp'
    poly_gdf = gpd.read_file(shp_poli_np)
    
    #Extract points from inside NP poly
    join_geodf = gpd.sjoin(points_geodf, poly_gdf)
    np_df = pd.DataFrame(join_geodf.drop(columns='geometry'))
    
    # Insert np_df into the 'national_parks' table
    np_df.to_sql('national_parks', conn, if_exists='replace', index=False)
    
    # Update the 'np' column in the 'apv_data' table based on 'nr'
    c.execute("UPDATE apv_data SET national_park = 1 WHERE nr IN (SELECT nr FROM national_parks)")
    # ADD lat and lng to apv_data
    c.execute('UPDATE apv_data SET lat = (SELECT lat FROM mytable WHERE apv_data.nr = mytable.nr), lng = (SELECT lng FROM mytable WHERE apv_data.nr = mytable.nr)')

    # Drop the new_entries table
    c.execute('DROP TABLE new_entries')
    c.execute('DROP TABLE temp_table')

    # Commit the changes and close the database connection
    conn.commit()
    conn.close()


def np_check():
    # Load data from the cache file
    cache_file = 'ignore_folder/response_cache.json'
    with open(cache_file, 'r') as f:
        response_text = f.read()
    data = json.loads(response_text)
    
    # Extract desired fields from the data
    desired_fields = [{'nr': item['nr'], 'lat': item['latLng']['lat'], 'lng': item['latLng']['lng'], 'stare': item['stare'], 'emiteAvize': item['emiteAvize']} for item in data]

    # Connect to the SQLite database
    conn = sqlite3.connect('np_database.db')
    c = conn.cursor()

    # Create a table in the database to store the data
    c.execute('CREATE TABLE IF NOT EXISTS apv_list (nr INTEGER PRIMARY KEY, lat REAL, lng REAL, stare TEXT, emiteAvize INTEGER, date_added TEXT)')

    # Get existing 'nr' values from apv_list table
    c.execute('SELECT nr FROM apv_list')
    existing_nrs = set([row[0] for row in c.fetchall()])

    # Filter desired_fields to include only new entries
    new_entries = [item for item in desired_fields if item['nr'] not in existing_nrs]

    if new_entries:
        # Insert the new entries into a temporary table
        temp_table_name = 'temp_apv_list'
        c.execute(f'CREATE TABLE IF NOT EXISTS {temp_table_name} (nr INTEGER PRIMARY KEY, lat REAL, lng REAL, stare TEXT, emiteAvize INTEGER, date_added TEXT)')

        for item in new_entries:
            current_date = datetime.now().strftime('%Y-%m-%d')
            c.execute(f'INSERT OR REPLACE INTO {temp_table_name} (nr, lat, lng, stare, emiteAvize, date_added) VALUES (?, ?, ?, ?, ?, ?)', (item['nr'], item['lat'], item['lng'], item['stare'], item['emiteAvize'], current_date))

        # Copy data from the temporary table to the main table
        c.execute(f'INSERT OR REPLACE INTO apv_list SELECT * FROM {temp_table_name}')

        # Query the database to get the list of NP plots
        df = pd.read_sql_query(f'SELECT nr, lat, lng, emiteAvize FROM {temp_table_name}', conn)
        points_geodf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.lng, df.lat), crs='EPSG:4326')

        # Load the NP polygons from the shapefile
        shp_poli_np = 'shp_files/np_poli.shp'
        poly_gdf = gpd.read_file(shp_poli_np)

        # Extract points from inside NP polygons
        join_geodf = gpd.sjoin(points_geodf, poly_gdf)
        np_df = pd.DataFrame(join_geodf.drop(columns='geometry'))
 
        api_table_name = 'np_data'
        c.execute(f'CREATE TABLE IF NOT EXISTS {api_table_name} (nr INTEGER PRIMARY KEY, lat REAL, lng REAL, emiteAvize INTEGER, text TEXT, denumire TEXT, up TEXT, ua TEXT, emitent_denumire TEXT, autorizatie_titular TEXT, ocol TEXT, volumInitial TEXT, volum REAL, volumRasinoase REAL, exploatari TEXT, prelungiri TEXT, stare TEXT, codStare INTEGER, tratament TEXT, naturaProdus TEXT, judet TEXT, date_added TEXT)')

        for index, row in np_df.iterrows():
            nr = row['nr']
            emiteAvize = row['emiteAvize']
            api_url = f'https://www.inspectorulpadurii.ro/api/apv/{nr}'
            api_response = requests.get(api_url)
            if api_response.status_code == 200:
                api_data = api_response.json()
                if api_data:
                    denumire = api_data['denumire']
                    up = api_data['up']
                    ua = api_data['ua']
                    emitent_denumire = api_data['emitent']['denumire']
                    autorizatie_titular = api_data['autorizatie']['titular']
                    ocol = api_data['ocol']
                    volumInitial = api_data['volumInitial']
                    volum = api_data['volum']
                    volumRasinoase = api_data['volumGrupeSpecii'].get('RĂȘINOASE', None) if api_data['volumGrupeSpecii'] else None
                    exploatari = json.dumps(api_data['exploatari'])
                    prelungiri = json.dumps(api_data['prelungiri'])
                    stare = api_data['stare']
                    codStare = api_data['codStare']
                    tratament = api_data['tratament']
                    naturaProdus = api_data['naturaProdus']
                    judet = api_data['judet']
                    text = row['text']
                    date_added = datetime.now().strftime('%Y-%m-%d')
                    
                    # Insert or update individual row
                    c.execute(f'''
                        INSERT INTO {api_table_name} (nr, lat, lng, emiteAvize, text, denumire, up, ua, emitent_denumire, autorizatie_titular, ocol, volumInitial, volum, volumRasinoase, exploatari, prelungiri, stare, codStare, tratament, naturaProdus, judet, date_added)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT (nr) DO UPDATE SET
                        lat = excluded.lat,
                        lng = excluded.lng,
                        emiteAvize = excluded.emiteAvize,
                        text = excluded.text,
                        denumire = excluded.denumire,
                        up = excluded.up,
                        ua = excluded.ua,
                        emitent_denumire = excluded.emitent_denumire,
                        autorizatie_titular = excluded.autorizatie_titular,
                        ocol = excluded.ocol,
                        volumInitial = excluded.volumInitial,
                        volum = excluded.volum,
                        volumRasinoase = excluded.volumRasinoase,
                        exploatari = excluded.exploatari,
                        prelungiri = excluded.prelungiri,
                        stare = excluded.stare,
                        codStare = excluded.codStare,
                        tratament = excluded.tratament,
                        naturaProdus = excluded.naturaProdus,
                        judet = excluded.judet,
                        date_added = CASE WHEN {api_table_name}.date_added IS NULL THEN excluded.date_added ELSE {api_table_name}.date_added END
                    ''', (nr, row['lat'], row['lng'], emiteAvize, text, denumire, up, ua, emitent_denumire, autorizatie_titular, ocol, volumInitial, volum, volumRasinoase, exploatari, prelungiri, stare, codStare, tratament, naturaProdus, judet, date_added))
                    
        # Commit changes to the database and close the connection
        c.execute(f'DROP TABLE {temp_table_name}')
        conn.commit()
        conn.close()
        

def extract_codAviz():
    # Connect to the SQLite database
    conn = sqlite3.connect('np_database.db')
    c = conn.cursor()

    # Create a new table to store the extracted codAviz data
    c.execute('CREATE TABLE IF NOT EXISTS codAviz_data (codAviz TEXT PRIMARY KEY, nrIdentificare TEXT, nrApv TEXT, provenienta TEXT, tipAviz TEXT, numeTipAviz TEXT, volum TEXT, emitent_denumire TEXT, valabilitate_emitere DATE, valabilitate_finalizare DATE, marfa_grupeSpecii TEXT, marfa_specii TEXT, marfa_sortimente TEXT, marfa_total TEXT, route_data TEXT, last_lat REAL, last_lng REAL, possible_logyard TEXT, distance_to_logyard TEXT, sent_status INTEGER DEFAULT 0)')

    # Get the list of 'nr' values from np_data table where emiteAvize is 1
    c.execute("SELECT nr FROM np_data WHERE emiteAvize = 1")
    nr_list = [row[0] for row in c.fetchall()]

    for nr in nr_list:
        # Make the API call
        url = f"https://inspectorulpadurii.ro/api/aviz/locations?nr=&cod=&nrApv={nr}&tip="
        response = requests.get(url)
        
        if response.status_code == 200:
            api_data = response.json()
            codAviz_list = api_data.get("codAviz", [])

            # Insert the extracted codAviz data into the new table
            for codAviz in codAviz_list:
                c.execute('INSERT OR IGNORE INTO codAviz_data (codAviz) VALUES (?)', (codAviz,))

    # Commit changes to the database and close the connection
    conn.commit()
    conn.close()

def fetch_aviz_data():
    # Connect to the SQLite database
    conn = sqlite3.connect('np_database.db')
    c = conn.cursor()

    # Get the list of 'codAviz' values from codAviz_data table that haven't been fetched yet
    c.execute("SELECT codAviz FROM codAviz_data WHERE nrIdentificare IS NULL")
    codAviz_list = [row[0] for row in c.fetchall()]

    api_table_name = 'codAviz_data'

    for codAviz in codAviz_list:
        # Make the API call
        url = f"https://inspectorulpadurii.ro/api/aviz/{codAviz}"
        response = requests.get(url)

        if response.status_code == 200:
            api_data = response.json()

            # Extract the desired data from the response
            nrIdentificare = api_data.get("nrIdentificare")
            nrApv = api_data.get("nrApv")
            provenienta = api_data.get("provenienta")
            tipAviz = api_data.get("tipAviz")
            numeTipAviz = api_data.get("numeTipAviz")
            volum = api_data.get("volum", {}).get("total")
            emitent_denumire = api_data.get("emitent", {}).get("denumire")
            marfa_grupeSpecii = api_data.get("marfa", {}).get("grupeSpecii")
            marfa_specii = api_data.get("marfa", {}).get("specii")
            marfa_sortimente = api_data.get("marfa", {}).get("sortimente")
            marfa_total = api_data.get("marfa", {}).get("total")
            valabilitate_emitere_epoch = api_data.get("valabilitate", {}).get("emitere")
            valabilitate_finalizare_epoch = api_data.get("valabilitate", {}).get("finalizare")

            # Convert epoch timestamps to date and time
            valabilitate_emitere = datetime.fromtimestamp(valabilitate_emitere_epoch / 1000).strftime('%Y-%m-%d %H:%M:%S')
            valabilitate_finalizare = datetime.fromtimestamp(valabilitate_finalizare_epoch / 1000).strftime('%Y-%m-%d %H:%M:%S')

            # Update the corresponding row in the codAviz_data table
            c.execute(f'''
                UPDATE {api_table_name}
                SET nrIdentificare = ?,
                    nrApv = ?,
                    provenienta = ?,
                    tipAviz = ?,
                    numeTipAviz = ?,
                    volum = ?,
                    emitent_denumire = ?,
                    valabilitate_emitere = ?,
                    valabilitate_finalizare = ?,
                    marfa_grupeSpecii = ?,
                    marfa_specii = ?,
                    marfa_sortimente = ?,
                    marfa_total = ?
                WHERE codAviz = ?
            ''', (nrIdentificare, nrApv, provenienta, tipAviz, numeTipAviz, volum, emitent_denumire,
                  valabilitate_emitere, valabilitate_finalizare, marfa_grupeSpecii, marfa_specii,
                  marfa_sortimente, marfa_total, codAviz))

    # Commit changes to the database and close the connection
    conn.commit()
    conn.close()


def fetch_route_data():
    # Connect to the SQLite database
    conn = sqlite3.connect('np_database.db')
    c = conn.cursor()

    # Get the list of 'codAviz' values from codAviz_data table
    c.execute("SELECT codAviz FROM codAviz_data")
    codAviz_list = [row[0] for row in c.fetchall()]

    api_table_name = 'codAviz_data'

    for codAviz in codAviz_list:
        # Check if route data has already been fetched for this codAviz
        c.execute(f"SELECT codAviz FROM {api_table_name} WHERE codAviz = ? AND route_data IS NULL", (codAviz,))
        existing_route = c.fetchone()

        if existing_route:
            # Make the API call
            url = f"https://inspectorulpadurii.ro/api/aviz/{codAviz}/route"
            response = requests.get(url)

            if response.status_code == 200:
                api_data = response.json()

                # Convert the list of coordinates to a string
                route_data = json.dumps(api_data)

                # Extract the last pair of coordinates
                last_coordinates = api_data[-1]

                # Update the corresponding rows in the np_data table
                c.execute(f'''
                    UPDATE {api_table_name}
                    SET route_data = ?,
                        last_lat = ?,
                        last_lng = ?
                    WHERE codAviz = ?
                ''', (route_data, last_coordinates['lat'], last_coordinates['lng'], codAviz))

    # Commit changes to the database and close the connection
    conn.commit()
    conn.close()


def np_aviz_check():
    # Read CSV file and extract coordinates and names
    buffer_radius = 500  # in meters
    possible_logyards = []

    with open('logyards.csv', 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            name = row['name'].strip()
            lat = row['latitude']
            lng = row['longitude']

            # Skip rows with empty latitude or longitude
            if lat is None or lat == '' or lng is None or lng == '':
                continue

            lat = float(lat)
            lng = float(lng)
            possible_logyards.append({
                'name': name,
                'latitude': lat,
                'longitude': lng
            })

    # Iterate over each row in codAviz_data table
    conn = sqlite3.connect('np_database.db')
    c = conn.cursor()

    c.execute("SELECT codAviz, last_lat, last_lng FROM codAviz_data")
    rows = c.fetchall()

    # Check if last_lat and last_lng fall within any logyards
    for row in rows:
        codAviz = row[0]
        last_lat = row[1]
        last_lng = row[2]

        # Skip rows with None or empty latitude or longitude
        if last_lat is None or last_lng is None or last_lat == '' or last_lng == '':
            continue

        last_lat = float(last_lat)
        last_lng = float(last_lng)

        possible_logyard = None
        distance = None

        for logyard in possible_logyards:
            logyard_lat = logyard['latitude']
            logyard_lng = logyard['longitude']
            logyard_name = logyard['name']

            # Calculate the distance between coordinates
            dist = geodesic((last_lat, last_lng), (logyard_lat, logyard_lng)).meters

            if dist <= buffer_radius:
                possible_logyard = logyard_name
                distance = dist
                break

        # Update codAviz_data table with matching logyard and distance
        c.execute("UPDATE codAviz_data SET possible_logyard = ?, distance_to_logyard = ? WHERE codAviz = ?", (possible_logyard, distance, codAviz))

    # Commit changes to the database and close the connection
    conn.commit()
    conn.close()

# Define a function to shrink the database size
def shrink_database(database_file):
    conn = sqlite3.connect(database_file)

    # Execute the VACUUM command to optimize the database and reduce its size
    conn.execute('VACUUM')

    # Commit the changes and close the database connection
    conn.commit()
    conn.close()    


# # Your App Password (generated in your Google Account settings)
# app_password = "nyiuccqoctidcjow"


def send_email(subject, body, receiver_emails):
    # Email configuration
    sender_email = 'apv.monitoring.app@gmail.com'
    sender_password = 'nyiuccqoctidcjow'


    # Create a multipart message
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = ', '.join(receiver_emails)  # Join multiple recipient emails with a comma and space
    msg['Subject'] = subject

    # Attach the HTML body
    msg.attach(MIMEText(body, 'html'))
    
    # Send the email
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, receiver_emails, text)
        server.quit()
        print('Email sent successfully')
    except Exception as e:
        print(f'Error sending email: {str(e)}')

def send_unsent_entries_email():
    # Connect to the SQLite database
    conn = sqlite3.connect('np_database.db')
    c = conn.cursor()

    # Query for unsent rows in codAviz_data table
    query = "SELECT codAviz as Aviz, nrIdentificare as Truck_number, nrApv as APV, emitent_denumire as Company, valabilitate_emitere as start_transport, valabilitate_finalizare as end_transport, marfa_grupeSpecii as Group_species, marfa_specii as Species, marfa_sortimente as Sortiment, round(marfa_total, 2) as Volume, possible_logyard as HS_log_yard, ROUND(distance_to_logyard) as Distance_to_log_yard FROM codAviz_data WHERE distance_to_logyard > 0.1 AND (julianday('now') - julianday(valabilitate_finalizare)) < 10 AND sent_status = 0 AND marfa_grupeSpecii = 'RĂȘINOASE' ORDER BY Distance_to_log_yard"
    df_unsent_entries = pd.read_sql_query(query, conn)

    # Check if there are unsent entries
    if not df_unsent_entries.empty:
        # Create a table inside the email body
        email_body = df_unsent_entries.to_html(index=False, escape=False, border=0, classes="table table-striped", justify="center")

        # List of recipient email addresses
        receiver_emails = ['cristian.vacaru@hs.ro', 'alexandru.bahrin@hs.ro', 'vladut.ciobica@hs.ro', 'adrian.lucan@hs.ro', 'laszlo.jager@hs.at']  # Add more email addresses as needed

        # Prompt to ask if the email should be sent
        send_email_option = input("Do you want to send the email with the list of unsent entries? (Y/N): ").strip().lower()

        if send_email_option == 'y':
            # Send an email with the unsent entries as an HTML table
            subject = 'NP delivery notes notification'
            body = f'<html><body><p>Hi, please find the latest National Park delivery notes with possible unloading in HS log yards</p>{email_body}</body></html>'
            send_email(subject, body, receiver_emails)

            # Mark the sent entries as sent (set sent_status to 1)
            c.execute("UPDATE codAviz_data SET sent_status = 1 WHERE sent_status = 0")

            # Commit changes and close the connection
            conn.commit()
            conn.close()

            print('Unsent entries sent and marked as sent.')
        elif send_email_option == 'n':
            print('Email not sent. Entries remain unsent.')
        else:
            print('Invalid option. Email not sent.')

    else:
        print('No unsent entries to send.')


def archive_old_entries():
    # Connect to the SQLite database
    conn = sqlite3.connect('np_database.db')
    c = conn.cursor()

    # Define the archive folder path
    archive_folder = 'archive'
    os.makedirs(archive_folder, exist_ok=True)

    # Calculate the date threshold for archiving (end of previous month)
    today = datetime.today()
    last_day_previous_month = (today.replace(day=1) - timedelta(days=1)).replace(day=1)

    # Calculate the date threshold for archiving (end of the month before last month)
    last_day_before_last_month = (last_day_previous_month - timedelta(days=1)).replace(day=1)

    # Define the archive filename based on the month and year of data being archived
    archive_filename = last_day_before_last_month.strftime('%b%Y') + '_archive.csv'

    # Query for entries to archive (valabilitate_finalizare before last day of previous month)
    query = "SELECT * FROM codAviz_data WHERE valabilitate_finalizare <= ?"
    params = (last_day_previous_month.strftime('%Y-%m-%d %H:%M:%S'),)
    df_archive_entries = pd.read_sql_query(query, conn, params=params)

    # Check if there are entries to archive
    if not df_archive_entries.empty:
        # Create the archive file path
        archive_file_path = os.path.join(archive_folder, archive_filename)

        # Check if the archive file already exists, and if so, append to it
        mode = 'w' if not os.path.isfile(archive_file_path) else 'a'

        # Save the entries to the archive file
        df_archive_entries.to_csv(archive_file_path, mode=mode, index=False)

        # Delete the archived entries from the database
        c.execute("DELETE FROM codAviz_data WHERE valabilitate_finalizare <= ?", (last_day_previous_month.strftime('%Y-%m-%d %H:%M:%S'),))

        # Commit changes and close the connection
        conn.commit()
        conn.close()

        print(f'Archived entries from {last_day_previous_month.strftime("%B %Y")} saved to {archive_file_path} and deleted from the database.')
    else:
        print('No entries to archive.')


import subprocess

def commit_and_push_to_github(commit_message):
    try:
        # Stage all changes
        subprocess.run(['git', 'add', '.'])

        # Set skip-worktree for the specific file (ignore_folder/response_cache.json)
        subprocess.run(['git', 'update-index', '--skip-worktree', 'ignore_folder/response_cache.json'])

        # Commit with the given commit_message
        subprocess.run(['git', 'commit', '-m', commit_message])

        # Push to GitHub (you might need to provide your GitHub credentials)
        subprocess.run(['git', 'push'])

        print(f'Changes committed and pushed to GitHub with message: {commit_message}')
    except Exception as e:
        print(f'Error: {str(e)}')



from fuzzywuzzy import fuzz, process
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service

def parse_date_from_filename(filename):
    date_str = os.path.splitext(filename)[0]  # Remove the file extension
    try:
        return datetime.strptime(date_str, '%y%m%d')
    except ValueError:
        return None

def match_supplier_id(name, supplier_data):
    if name is None:
        return "1684"  # Replace with the default value for None

    # Use fuzzywuzzy to get a list of matches
    matches = process.extract(name, supplier_data['Name'], limit=1, scorer=fuzz.token_sort_ratio)
       
    # Select the best match (above a certain threshold, e.g., 80)
    best_match = max(matches, key=lambda x: x[1])

    # Extract the ID for the best match, or return "1684" if no match found
    matched_id = supplier_data.loc[best_match[2], 'ID'] if best_match[1] > 90 else "1684"
       
    return matched_id

def prepare_import_file():
    # Define the path to the database and the output folder
    database_path = 'np_database.db'
    output_folder = 'np_import/'

    # Create the np_import folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)

    # Get the current date as YYMMDD
    today = datetime.today()
    date_str = today.strftime('%y%m%d')

    # Define the output Excel file path
    output_file = os.path.join(output_folder, f'{date_str}.xlsx')
    # Check if the file already exists
    if os.path.exists(output_file):
        print(f"File {output_file} already exists. Aborting data export.")
        return  # Exit the function
    
    # Determine the last export date from the existing files
    existing_files = os.listdir(output_folder)
    last_export_date = None
    
    for file in existing_files:
        file_date = parse_date_from_filename(file)
        if file_date:
            if last_export_date is None or file_date > last_export_date:
                last_export_date = file_date

    if last_export_date is None:
        last_export_date = today  # Default to today if no previous exports

    
    # Load the "np_id.csv" file into a DataFrame
    np_id_df = pd.read_csv('np_id.csv')

    # Convert the "Name" column to lowercase for case-insensitive matching
    np_id_df['Name'] = np_id_df['Name'].str.lower()

    # Create a dictionary with lowercase "Name" as keys and "Id" as values
    np_id_dict = dict(zip(np_id_df['Name'], np_id_df['Id']))

    # Load the "fmu_id.xls" Excel file into a DataFrame
    fmu_id_df = pd.read_excel('fmu_id.xls')

    # Convert the "Nume" column to lowercase for case-insensitive matching
    fmu_id_df['Nume'] = fmu_id_df['Nume'].str.lower()

    # Create a dictionary with lowercase "Nume" as keys and "ID" as values
    fmu_id_dict = dict(zip(fmu_id_df['Nume'], fmu_id_df['ID']))

    # Connect to the SQLite database
    conn = sqlite3.connect(database_path)

    # Define your SQL query to select new entries between last export and today
    sql_query = f"SELECT nr, lat, lng, emiteAvize, text, denumire, up, ua, emitent_denumire, " \
                f"autorizatie_titular, ocol, volumInitial, stare, tratament, naturaProdus, judet, date_added " \
                f"FROM np_data " \
                f"WHERE date_added >= '{(last_export_date + timedelta(days=1)).strftime('%Y-%m-%d')}' " \
                f"AND date_added < '{today.strftime('%Y-%m-%d')}'"
  

    # Execute the query and read the results into a DataFrame
    df_np_data = pd.read_sql_query(sql_query, conn)
    
    # Check if there are no entries in the DataFrame
    if df_np_data.empty:
        print("No new entries found. Skipping data export.")
        return

    # Load the supplier data from the XLSX file
    supplier_data = pd.read_excel('supplier_id.xlsx')

    # Replace 'autorizatie_titular' values with matching IDs or "1684" if no match found
    df_np_data['autorizatie_titular'] = df_np_data['autorizatie_titular'].apply(lambda x: match_supplier_id(x, supplier_data))

    # Convert the "text" column to lowercase for case-insensitive matching
    df_np_data['text'] = df_np_data['text'].str.lower()

    # Replace "text" values with "Id" values based on the dictionary
    df_np_data['text'] = df_np_data['text'].map(np_id_dict)

    # Convert the "ocol" column to lowercase for case-insensitive matching
    df_np_data['ocol'] = df_np_data['ocol'].str.lower()

    # Replace "ocol" values with "ID" values based on the dictionary and add "278" for unmatched entries
    df_np_data['ocol'] = df_np_data['ocol'].map(fmu_id_dict).fillna('278')
    
    # Close the database connection
    conn.close()
    
    # Replace column names in the DataFrame
    df_np_data.rename(columns={'nr': 'sumal', 'text': 'national_park', 'up': 'production_unit', 'ua': 'sub_compartments',
                            'autorizatie_titular': 'supplier_id', 'ocol': 'fmu_id'}, inplace=True)

    # Set default values for the 'used_in_ticom' and 'is_daf' columns
    df_np_data['used_in_ticom'] = 0
    df_np_data['is_daf'] = 0
    df_np_data['mill'] = ""
    df_np_data['total_plot_volume'] = ""
    df_np_data['harvesting_start'] = ""
    df_np_data['harvesting_end'] = ""
    df_np_data['number_of_resinous_trees'] = ""
    df_np_data['plot_surface'] = ""
    df_np_data['age'] = ""
    df_np_data['saw_logs_volume'] = ""
    df_np_data['bark_volume'] = ""
    df_np_data['diameter'] = ""
    df_np_data['height'] = ""
    df_np_data['harvesting_company'] = ""
    df_np_data['comment'] = ""
    df_np_data['ownership'] = ""
    # Define the desired column order
    column_order = ['sumal', 'national_park', 'mill', 'used_in_ticom', 'is_daf', 'total_plot_volume', 'harvesting_start', 
                    'harvesting_end', 'number_of_resinous_trees', 'plot_surface', 'age', 'production_unit', 
                    'sub_compartments', 'saw_logs_volume', 'bark_volume', 'diameter', 'height', 'supplier_id', 
                    'harvesting_company', 'comment', 'fmu_id', 'ownership']
    
    df_np_data = df_np_data[column_order]
    
    # Save the DataFrame to an Excel file
    df_np_data.to_excel(output_file, index=False)
    
    # Perform web automation to upload the file
    automate_website_login(output_file)
    
    # Display a success message
    print(f"Data exported to {output_file}")
    
    
def is_website_available(url):
    try:
        response = requests.get(url)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False
      
def automate_website_login(output_file):
    website_url = 'https://dds.hstimbergroup.local/apvs'
    
     # Check if the website is available
    if not is_website_available(website_url):
        user_response = input("Website is not available. Type 'Y' to retry: ")
        if user_response.lower() != 'y':
            return
    
    # Set the path to the ChromeDriver executable
    chrome_driver_path = 'chromedriver.exe'

    # Create a Service object with the path to ChromeDriver
    service = Service(chrome_driver_path)

    # Create a new instance of the Chrome driver
    driver = webdriver.Chrome(service=service)

    # Open the website
    driver.get('https://dds.hstimbergroup.local/apvs')

    # Find the username and password input fields and the login button
    username_field = driver.find_element(By.XPATH, '//*[@id="username"]')
    password_field = driver.find_element(By.XPATH, '//*[@id="password"]')
    login_button = driver.find_element(By.XPATH, '//*[@id="app"]/div/div/div/div[2]/div/form/div[4]/div/button')

    # Enter your login credentials
    username_field.send_keys('cristian.vacaru')
    password_field.send_keys('Password6!')

    # Click the login button
    login_button.click()

    # Click on the button that triggers the pop-out element
    upload_button = driver.find_element(By.CSS_SELECTOR, 'body > div.wrapper > div > section > div:nth-child(5) > div > div > div.panel-body > div.clearfix.text-right > button:nth-child(1)')
    upload_button.click()

    # Wait for a few seconds to ensure the pop-out element is fully loaded
    time.sleep(5)

    # Find the file input element
    file_input = driver.find_element(By.XPATH, '//*[@id="name"]')
    
    # Get the absolute path of the file
    absolute_output_file = os.path.abspath(output_file)
    # Provide the absolute file path using send_keys
    file_input.send_keys(absolute_output_file)
    

    # Wait for some time to allow the file to upload
    time.sleep(10)

    # Find the "Save" button using the XPath
    save_button = driver.find_element(By.XPATH, '//*[@id="importModal"]/div/div/form/div/div[2]/button[2]')

    # Click the "Save" button
    save_button.click()
    time.sleep(50)
    
     # Access the second website
    second_website_url = 'https://apv-monitoring.streamlit.app/'
    driver.get(second_website_url)

    # Wait for the page to load
    time.sleep(5)

    # Find the input element and type 'secret'
    secret_input = driver.find_element(By.XPATH, '//*[@id="root"]/div[1]/div[1]/div/div/div/section/div[1]/div[1]/div/div/div/div[1]/div')
    secret_input.send_keys('secret')

    # Press Enter after typing 'secret'
    secret_input.send_keys(Keys.ENTER)

    # Wait for 50 seconds
    time.sleep(50)



make_api_call()
np_check()
extract_codAviz()
fetch_aviz_data()
fetch_route_data()
np_aviz_check()


# Call the function to archive entries older than 2 months
archive_old_entries()

# Call the function to send unsent entries in an email and mark them as sent
send_unsent_entries_email()

# Call the shrink_database function for your SQLite databases
shrink_database('mydatabase.db')
shrink_database('np_database.db')

# Call the function with your desired commit message
commit_message = 'auto_update'
commit_and_push_to_github(commit_message)

prepare_import_file()


