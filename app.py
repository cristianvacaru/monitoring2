# import streamlit as st
# import requests
# import json
# import os
# import sqlite3
# from datetime import datetime
# import time
# from dateutil.relativedelta import relativedelta
# import pandas as pd
# import time
# import io
# import xlsxwriter




# # Streamlit app-------------------------
# st.set_page_config(page_title='APVs Monitoring', page_icon='🌲', layout="wide", initial_sidebar_state="auto", menu_items=None)
# st.title('APVs Monitoring')

# tab1, tab2 = st.tabs(["APVs", "National Parks"])

# with tab1:
#     # Statistics
#     conn = sqlite3.connect('mydatabase.db')
#     c = conn.cursor()



#     # Execute a SQL query to get the maximum date from the date_added column
#     c.execute("SELECT MAX(date_added) FROM mytable")
#     result = c.fetchone()
#     last_date_added = result[0]

#     # Convert the date from the database to a Python datetime object
#     last_date_added = datetime.strptime(last_date_added, '%Y-%m-%d')

#     st.metric("Last update date: ", last_date_added.strftime('%B %d, %Y'))


#     # Fetch the data from the apv_data table
#     c.execute('SELECT lat, lng, nr, denumire, emitent_denumire, autorizatie_titular, ocol, volumInitial, volum, stare, tratament, naturaProdus, judet FROM apv_data')
#     data = c.fetchall()



#     # Filtering section:
#     df = pd.read_sql_query("SELECT nr, denumire as DenumireAPV, emitent_denumire as Emitent, autorizatie_titular as TitularAutorizatie, ocol, volumInitial as VolumTotal, volum as VolumRasinoase, judet, stare, tratament, date_added, national_park FROM apv_data WHERE emiteAvize = 1 and volum > 50 ORDER by volum desc", conn)

#     # Convert 'date_added' column to datetime format
#     df['date_added'] = pd.to_datetime(df['date_added'], format='%Y-%m-%d')

#     # Create a dictionary to store options for each judet and ocol combination
#     options = {}
#     for judet in df["judet"].unique():
#         options[judet] = {}
#         for ocol in df[df["judet"] == judet]["ocol"].unique():
#             options[judet][ocol] = df[(df["judet"] == judet) & (df["ocol"] == ocol)]["judet"].tolist()

#     # Create a multiselect widget for 'judet' column
#     selected_judet = st.sidebar.multiselect(
#         "Select judet", sorted(df["judet"].unique())
#     )

#     # Create a multiselect widget for 'ocol' column based on selected judet
#     selected_ocol = []
#     for judet in selected_judet:
#         options_for_judet = options.get(judet, {})
#         selected_ocol += st.sidebar.multiselect(
#             f"Select ocol for {judet}", sorted(options_for_judet.keys()), key=judet)

#     # Create a function to highlight rows with 'national_park' = 1
#     def highlight_national_park(row):
#         # Create a list to store the background color for each cell
#         background_color = [''] * len(row)

#         # Check if 'national_park' column has a value of 1
#         if row['national_park'] == 1:
#             # Set the background color of all cells in the row to red
#             background_color = ['background-color: red'] * len(row)

#         return background_color
#     # Filter data based on selected judet and ocol
#     if not selected_judet:
#         styled_df = df.style.apply(highlight_national_park, axis=1).format("{:.2f}", subset=pd.IndexSlice[:, df.select_dtypes(include='float').columns])
#         st.dataframe(styled_df)
        
#     else:
#         if not selected_ocol:
#             filtered_df = df[df["judet"].isin(selected_judet)]
#         else:
#             filtered_df = df[(df["judet"].isin(selected_judet)) & (df["ocol"].isin(selected_ocol))]
        
#         # Date range selecting
#         date_range = st.sidebar.date_input('Select date range', value=(df['date_added'].min().date(), df['date_added'].max().date()))

#         # Convert date_range values to datetime64[ns]
#         date_start = pd.to_datetime(date_range[0])
#         date_end = pd.to_datetime(date_range[1]) if len(date_range) > 1 else date_start

#         # Adjust date range for single date selection
#         if date_start == date_end:
#             date_end += pd.DateOffset(days=1)
        
#         # Filter data based on selected date range
#         filtered_df = filtered_df[(filtered_df['date_added'] >= date_start) & (filtered_df['date_added'] <= date_end)]
        
#         # Create a new dataframe with the selected judets and ocols
#         new_df = pd.DataFrame(columns=df.columns)
#         for judet in selected_judet:
#             judet_df = filtered_df[filtered_df["judet"] == judet]
#             if not selected_ocol:
#                 new_df = new_df.append(judet_df)
#             else:
#                 for ocol in selected_ocol:
#                     ocol_df = judet_df[judet_df["ocol"] == ocol]
#                     new_df = new_df.append(ocol_df)


#         # Display filtered dataframe
#         styled_df = new_df.style.apply(highlight_national_park, axis=1).format("{:.2f}", subset=pd.IndexSlice[:, new_df.select_dtypes(include='float').columns])
#         st.dataframe(styled_df)


#         # Download the results DataFrame as an Excel file
#         def convert_df(new_df):
#             excel_data = io.BytesIO()
#             with pd.ExcelWriter(excel_data, engine='xlsxwriter') as writer:
#                 new_df.to_excel(writer, index=False)
#             excel_data.seek(0)
#             return excel_data.getvalue()

#         excel_data = convert_df(new_df)

#         st.download_button(
#             "Download results as .xlsx",
#             excel_data,
#             "export.xlsx",
#             "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
#             key='download-excel'
#         )

#     st.caption('Rows marked with :red[RED] are plots that overlap polygons of National Parks.')
#     # Download the DataFrame as an Excel file
#     def convert_df2(df):
#         excel_data = io.BytesIO()
#         with pd.ExcelWriter(excel_data, engine='xlsxwriter') as writer:
#             df.to_excel(writer, index=False)
#         excel_data.seek(0)
#         return excel_data.getvalue()

#     excel_data = convert_df2(df)

#     st.download_button(
#         "Download entire table",
#         excel_data,
#         "export.xlsx",
#         "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
#         key='download-excel'
#     )

#     conn.close()

# with tab2:
#     # NP section
#     conn = sqlite3.connect('np_database.db')
#     c = conn.cursor()
    
    
#     number_of_entries = c.execute('SELECT COUNT(*) FROM np_data')
#     result = c.fetchone()
#     total_apvs = result[0]
#     st.metric("Total APVs registered in NPs: ", total_apvs)
                                  
#     st.write('Plots from where can be issued delivery notes:')

        
#     df = pd.read_sql_query("SELECT nr, lat, lng, emiteAvize, text as NP_name, denumire, up, ua, emitent_denumire, autorizatie_titular, ocol, volumInitial, stare, tratament, naturaProdus, judet, date_added FROM np_data", conn)
#     df_filtered = pd.read_sql_query("SELECT nr, lat, lng, emiteAvize, text as NP_name, denumire, up, ua, emitent_denumire, autorizatie_titular, ocol, volumInitial, stare, tratament, naturaProdus, judet, date_added FROM np_data WHERE emiteAvize = 1", conn)
#     df_filtered = df_filtered.style.format({"Expense": lambda x : '{:.4f}'.format(x)})
#     st.dataframe(df_filtered)
#     # Download the DataFrame as an Excel file
#     def convert_df3(df):
#         excel_data = io.BytesIO()
#         with pd.ExcelWriter(excel_data, engine='xlsxwriter') as writer:
#             df.to_excel(writer, index=False)
#         excel_data.seek(0)
#         return excel_data.getvalue()

#     excel_data = convert_df3(df)

#     st.download_button(
#         "Download NP plots data",
#         excel_data,
#         "export.xlsx",
#         "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
#         key='download-excel3'
#     )
                
import streamlit as st
import requests
import json
import os
import sqlite3
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import pandas as pd
import time
import io
import xlsxwriter
import folium
from streamlit_folium import folium_static


def check_password():
    if "password" not in st.session_state:
        st.session_state["password"] = ""  # Initialize the "password" key with an empty string

    def password_entered():
        # Checks whether a password entered by the user is correct
        if st.session_state["password"] == st.secrets["password"]:
            st.session_state["password_correct"] = True
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show input for password.
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        # Password not correct, show input + error.
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        st.error("😕 Password incorrect")
        return False
    else:
        # Password correct.
        return True


if check_password():
        
    # Streamlit app-------------------------
    st.set_page_config(page_title='APVs Monitoring', page_icon='🌲', layout="wide", initial_sidebar_state="auto", menu_items=None)
    st.title('APVs Monitoring')

    tab1, tab2, tab3, tab4 = st.tabs(["APVs", "National Parks", "NP delivery notes", "Transport routes"])

    with tab1:
        
        # Statistics
        conn = sqlite3.connect('mydatabase.db')
        c = conn.cursor()

        # Execute a SQL query to get the maximum date from the date_added column
        c.execute("SELECT MAX(date_added) FROM apv_data")
        result = c.fetchone()
        last_date_added = result[0]

        # Convert the date from the database to a Python datetime object
        last_date_added = datetime.strptime(last_date_added, '%Y-%m-%d')


        st.metric("Last update date: ", last_date_added.strftime('%B %d, %Y'))
        st.markdown(f'<span style="background-color: red; color: black;">RED</span>: plots that overlap polygons of National Parks.', unsafe_allow_html=True)
        st.markdown(f'<span style="background-color: yellow; color: black;">YELLOW</span>: plots added in the last 10 days.', unsafe_allow_html=True)
        # Fetch the data from the apv_data table
        c.execute('SELECT lat, lng, nr, denumire, emitent_denumire, autorizatie_titular, ocol, volumInitial, volum, stare, tratament, naturaProdus, judet FROM apv_data')
        data = c.fetchall()

        # Filtering section:
        df = pd.read_sql_query("SELECT nr, denumire as DenumireAPV, emitent_denumire as Emitent, autorizatie_titular as TitularAutorizatie, ocol, volumInitial as VolumTotal, volum as VolumRasinoase, judet, stare, tratament, date_added, national_park, lat, lng FROM apv_data WHERE emiteAvize = 1 and volum > 50 ORDER by volum desc", conn)

        # Convert 'date_added' column to datetime format
        df['date_added'] = pd.to_datetime(df['date_added'], format='%Y-%m-%d')

        # Create a dictionary to store options for each judet and ocol combination
        options = {}
        for judet in df["judet"].unique():
            options[judet] = {}
            for ocol in df[df["judet"] == judet]["ocol"].unique():
                options[judet][ocol] = df[(df["judet"] == judet) & (df["ocol"] == ocol)]["judet"].tolist()

        # Create a multiselect widget for 'judet' column
        selected_judet = st.sidebar.multiselect(
            "Select judet", sorted(df["judet"].unique())
        )

        # Create a multiselect widget for 'ocol' column based on selected judet
        selected_ocol = []
        for judet in selected_judet:
            options_for_judet = options.get(judet, {})
            selected_ocol += st.sidebar.multiselect(
                f"Select ocol for {judet}", sorted(options_for_judet.keys()), key=judet)
        

        # Create a function to highlight rows with 'national_park' = 1
        def highlight_national_park(row):
            # Create a list to store the background color for each cell
            background_color = [''] * len(row)

            # Check if 'national_park' column has a value of 1
            if row['national_park'] == 1:
                # Set the background color of all cells in the row to red
                background_color = ['background-color: red'] * len(row)

            # Check if 'date_added' column date is within the last 10 days
            ten_days_ago = pd.Timestamp.now() - pd.DateOffset(days=10)
            if row['date_added'] >= ten_days_ago:
                # Set the background color of all cells in the row to green
                background_color = ['background-color: yellow'] * len(row)

            return background_color

        # Filter data based on selected judet and ocol
        if not selected_judet:
            styled_df = df.style.apply(highlight_national_park, axis=1).format("{:.2f}", subset=pd.IndexSlice[:, df.select_dtypes(include='float').columns])
            st.dataframe(styled_df)
        else:
            if not selected_ocol:
                filtered_df = df[df["judet"].isin(selected_judet)]
            else:
                filtered_df = df[(df["judet"].isin(selected_judet)) & (df["ocol"].isin(selected_ocol))]

            # Date range selecting
            date_range = st.sidebar.date_input('Select date range', value=(df['date_added'].min().date(), df['date_added'].max().date()))

            # Convert date_range values to datetime64[ns]
            date_start = pd.to_datetime(date_range[0])
            date_end = pd.to_datetime(date_range[1]) if len(date_range) > 1 else date_start

            # Adjust date range for single date selection
            if date_start == date_end:
                date_end += pd.DateOffset(days=1)

            # Filter data based on selected date range
            filtered_df = filtered_df[(filtered_df['date_added'] >= date_start) & (filtered_df['date_added'] <= date_end)]

            # Create a new dataframe with the selected judets and ocols
            dfs = []
            for judet in selected_judet:
                judet_df = filtered_df[filtered_df["judet"] == judet]
                if not selected_ocol:
                    dfs.append(judet_df)
                else:
                    for ocol in selected_ocol:
                        ocol_df = judet_df[judet_df["ocol"] == ocol]
                        dfs.append(ocol_df)
            new_df = pd.concat(dfs)

            # Display filtered dataframe with highlighted rows
            styled_df = new_df.style.apply(highlight_national_park, axis=1).format("{:.2f}", subset=pd.IndexSlice[:, new_df.select_dtypes(include='float').columns])
            st.dataframe(styled_df)


            # Download the results DataFrame as an Excel file
            def convert_df(new_df):
                excel_data = io.BytesIO()
                with pd.ExcelWriter(excel_data, engine='xlsxwriter') as writer:
                    new_df.to_excel(writer, index=False)
                excel_data.seek(0)
                return excel_data.getvalue()

            excel_data = convert_df(new_df)

            st.download_button(
                "Download results as .xlsx",
                excel_data,
                "export.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key='download-excel'
            )


        # Download the DataFrame as an Excel file
        def convert_df2(df):
            excel_data = io.BytesIO()
            with pd.ExcelWriter(excel_data, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False)
            excel_data.seek(0)
            return excel_data.getvalue()

        excel_data = convert_df2(df)

        st.download_button(
            "Download entire table",
            excel_data,
            "export.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key='download-excel-all'
        )


    # Close database connection
    conn.close()

    with tab2:
        # NP section
        conn = sqlite3.connect('np_database.db')
        c = conn.cursor()
        
        
        number_of_entries = c.execute('SELECT COUNT(*) FROM np_data')
        result = c.fetchone()
        total_apvs = result[0]
        st.metric("Total APVs registered in NPs: ", total_apvs)
                                    
        st.write('Plots from where can be issued delivery notes:')

            
        df = pd.read_sql_query("SELECT nr, lat, lng, emiteAvize, text as NP_name, denumire, up, ua, emitent_denumire, autorizatie_titular, ocol, volumInitial, volum, volumRasinoase, exploatari, prelungiri, stare, codStare, tratament, naturaProdus, judet, date_added FROM np_data", conn)

        df_filtered = pd.read_sql_query("SELECT nr, lat, lng, emiteAvize, text as NP_name, denumire, up, ua, emitent_denumire, autorizatie_titular, ocol, volumInitial, volum, volumRasinoase, exploatari, prelungiri, stare, codStare, tratament, naturaProdus, judet, date_added FROM np_data WHERE emiteAvize = 1", conn)
        df_filtered = df_filtered.style.format({"Expense": lambda x : '{:.4f}'.format(x)})
        st.dataframe(df_filtered)

        # Download the DataFrame as an Excel file
        def convert_df3(df):
            excel_data = io.BytesIO()
            with pd.ExcelWriter(excel_data, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False)
            excel_data.seek(0)
            return excel_data.getvalue()

        excel_data = convert_df3(df)

        st.download_button(
            "Download NP plots data",
            excel_data,
            "export.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key='download-excel3'
        )




    with tab3:
        # NP delivery notes section
        
        conn = sqlite3.connect('np_database.db')
        c = conn.cursor()
        
        
        st.write('Avize:')
        df = pd.read_sql_query("select codAviz, nrIdentificare, nrApv, provenienta, tipAviz, numeTipAviz, volum, emitent_denumire, valabilitate_emitere, valabilitate_finalizare, marfa_grupeSpecii, marfa_specii, marfa_sortimente, marfa_total, last_lat, last_lng, possible_logyard, distance_to_logyard from codAviz_data", conn)
        df_avize = pd.read_sql_query("select codAviz, nrIdentificare, nrApv, provenienta, tipAviz, numeTipAviz, volum, emitent_denumire, valabilitate_emitere, valabilitate_finalizare, marfa_grupeSpecii, marfa_specii, marfa_sortimente, marfa_total, last_lat, last_lng, possible_logyard, distance_to_logyard from codAviz_data where distance_to_logyard > 0.1 AND (julianday('now') - julianday(valabilitate_finalizare)) < 10", conn)
        
        st.dataframe(df_avize)
        
        # Download the DataFrame as an Excel file
        def convert_df4(df):
            excel_data = io.BytesIO()
            with pd.ExcelWriter(excel_data, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False)
            excel_data.seek(0)
            return excel_data.getvalue()

        excel_data = convert_df4(df)

        st.download_button(
            "Download NP delivery notes data",
            excel_data,
            "export.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key='download-excel4'
        )
        # Define the directory where the Excel files are stored
        directory_path = "archive/"

        # Get a list of Excel files in the directory
        csv_files = [f for f in os.listdir(directory_path) if f.endswith(".csv")]
        st.title("Archive list of NP deliveries")

        # Let the user select a file to download
        selected_file = st.selectbox("Select a file to download", csv_files)

        if selected_file:
            file_path = os.path.join(directory_path, selected_file)
            # Display a download button
            download_button = st.button("Download File")
            if download_button:
                with open(file_path, "rb") as file:
                    file_contents = file.read()
                    st.download_button(
                        label="Click here to download",
                        data=file_contents,
                        file_name=selected_file,
                        mime="text/csv",
                    )


    with tab4:
        # Function to fetch route coordinates from the API
        def fetch_route_coordinates_from_api(endpoint):
            response = requests.get(endpoint)
            if response.status_code == 200:
                return response.json()
            else:
                st.write("No available route in inspectorulpadurii")
                return None

        # Function to fetch route coordinates from the local database
        def fetch_route_coordinates_from_database(codAviz):
            conn = sqlite3.connect("np_database.db")
            cursor = conn.cursor()

            cursor.execute("SELECT route_data FROM codAviz_data WHERE codAviz=?", (codAviz,))
            result = cursor.fetchone()

            conn.close()

            if result:
                return json.loads(result[0])  # Parse the route_data from the database
            else:
                st.write("No data found in the local database.")
                return None

        # Function to display route on the map using Folium
        def display_route_on_map(route_coordinates):
            m = folium.Map(location=[route_coordinates[0]['lat'], route_coordinates[0]['lng']], zoom_start=12)
            folium.PolyLine([(coord['lat'], coord['lng']) for coord in route_coordinates], color='blue').add_to(m)
            return m

        st.title("Display Route on Map")

        # Input box for user to enter the API endpoint
        endpoint_input = st.text_input("Enter Aviz number:")

        if endpoint_input:
            with st.spinner("Fetching route data..."):
                endpoint_api = f"https://inspectorulpadurii.ro/api/aviz/{endpoint_input}/route"

                # Fetch route coordinates from the API
                route_coordinates_api = fetch_route_coordinates_from_api(endpoint_api)

                if route_coordinates_api:
                    # Display the route from the API
                    st.write("Route Map (from inspectorulpadurii):")
                    folium_map_api = display_route_on_map(route_coordinates_api)
                    folium_static(folium_map_api)
                else:
                    # If API call fails, try fetching from the local database
                    route_coordinates_db = fetch_route_coordinates_from_database(endpoint_input)

                    if route_coordinates_db:
                        # Display the route from the local database
                        st.write("Route Map (from database):")
                        folium_map_db = display_route_on_map(route_coordinates_db)
                        folium_static(folium_map_db)
