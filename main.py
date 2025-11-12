## imports
import requests
from flask import Flask, render_template, request, flash, url_for, redirect
import pandas as pd
import os
import io
import pygal
from pygal.style import *
from datetime import date

#create a flask app object and set app variables
app = Flask(__name__)
app.config["DEBUG"] = True
app.config["SECRET_KEY"] = 'your secret key'


# function to fetch data through API connection using user input
def fetch_data_through_api(symbol, api_key, function):
    url = "https://www.alphavantage.co/query"
    
    # parameters for the request
    params = {
        "function": function,  
        "symbol": symbol,
        "outputsize": "full",
        "datatype": "csv",
        "apikey": api_key
    }
    
    if function == "TIME_SERIES_INTRADAY":
        params["interval"] = "60min"
    
    try:
        # make the request
        response = requests.get(url, params=params)
        response.raise_for_status()  # will raise an error if the request failed
        
        df = pd.read_csv(io.StringIO(response.text))
        
        expected_cols = {'timestamp', 'open', 'high', 'low', 'close', 'volume'}
        if not expected_cols.issubset(df.columns):
            print("\n***********************\nUnexpected data format from API.\n***********************\n")
            return None
        
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df[['open', 'high', 'low', 'close', 'volume']] = df[['open', 'high', 'low', 'close', 'volume']].astype(float)
        
        # now the timestamp is the index, so we can do df.loc[start_date:end_date] with our dataframe
        df = df.set_index('timestamp')
        df = df.sort_index()
        
        return df
    except requests.exceptions.RequestException:
        print("\nAPI Request failed.")
    except Exception as e:
        print(f"\nFailed to process data: {e}")
        
    return None


# function to parse data and send data to graph
def get_data(symbol, chart_type, time_series, start_date, end_date):
    API_KEY = os.getenv("ALPHAVANTAGE_API_KEY", "38Z6ROU8EAKF0E9C")

    df = fetch_data_through_api(symbol, API_KEY, time_series)
    
    # if the data was not fetched for whatever reason, get_data should return None or may just be empty
    if df is None or df.empty:
        print("\n***********************\nNo data fetched. Please try a different symbol or date range.\n***********************\n")
        return None
    
    filtered_df = df.loc[start_date:end_date]
    
    if filtered_df.empty:
        print("\n***********************\nNo data found for the specified date range.\n***********************\n")
        return None
    
    print(f"\nFetched {len(df)} records for {symbol}.")
    print(f"Displaying data from {start_date.date()} to {end_date.date()}: {len(filtered_df)} records.")
    print(f"Will use {chart_type} chart\n")
    
    return filtered_df

#function to create line chart
def create_line_chart(df, symbol, start_date, end_date):
    line_chart = pygal.Line(
        style=LightStyle, 
        x_label_rotation=20, 
        show_minor_x_labels=True,
        show_major_x_lables=True,
        truncate_label=10,
        show_legend=True
    )
    line_chart.title = f"Stock Data for {symbol}: {start_date.date()} to {end_date.date()}"
    line_chart.x_labels = [x.strftime("%Y-%m-%d") for x in df.index]

    line_chart.add("Open", df['open'].tolist())
    line_chart.add("High", df['high'].tolist())
    line_chart.add("Low", df['low'].tolist())
    line_chart.add("Close", df['close'].tolist())

    return line_chart.render_data_uri()

#function to create bar chart
def create_bar_chart(df, symbol, start_date, end_date):
    bar_chart = pygal.Bar(
        style=LightStyle, 
        x_label_rotation=20, 
        show_minor_x_labels=True,
        show_major_x_labels=True,
        truncate_label=10,
        show_legend=True
    )
    bar_chart.title = f"Stock Data for {symbol}: {start_date.date()} to {end_date.date()}"
    bar_chart.x_labels = [x.strftime("%Y-%m-%d") for x in df.index]

    bar_chart.add("Open", df['open'].tolist())
    bar_chart.add("High", df['high'].tolist())
    bar_chart.add("Low", df['low'].tolist())
    bar_chart.add("Close", df['close'].tolist())

    return bar_chart.render_data_uri()



# function to get and validate user input
@app.route('/', methods = ('GET','POST'))
def index():
    
    # QUINCY: GET_SYMBOLS FUNCTION NEEDS TO BE USED HERE INSTEAD OF THE CODE BELOW
    def get_symbols():
        try:
            csv_path = os.path.join(os.path.dirname(__file__), 'stocks.csv')
            df = pd.read_csv(csv_path)
            if 'Symbol' not in df.columns:
                print("Error: 'Symbol' column not found in CSV")
                return[]
            return df ['Symbol'].dropna().tolist()
        except Exception as e:
            print(f"Error loading symbols from CSV: {e}")
            return[]
        
    symbols = get_symbols()
    if not symbols:
        flash("No Symbols avalable. Please check the file loading your data to the form")
        
    # holds chart if we make one
    chart_to_display = None


    if request.method == "POST":
        
        # gets input from form when Submit is pushed
        symbol = request.form.get('symbolOption')
        chart_type = request.form.get('chartTypeOption')
        time_series = request.form.get('timeSeriesOption')
        
        # ensures all information was submitted
        if not symbol:
            flash("Please select a stock symbol.")
            return render_template('index.html', symbols=symbols, chart_to_display=None)
        if not chart_type:
            flash("Please select a chart type.")
            return render_template('index.html', symbols=symbols, chart_to_display=None)
        if not time_series:
            flash("Please select a time series.")
            return render_template('index.html', symbols=symbols, chart_to_display=None)
        
        try:
            start_date_str = request.form.get('startDateOption')
            end_date_str = request.form.get('endDateOption')
            
            start_date = pd.Timestamp(start_date_str)
            end_date = pd.Timestamp(end_date_str)
        except Exception as e:
            flash(f"Invalid date format. Please enter valid dates. Error: {e}")
            return render_template('index.html', symbols=symbols, chart_to_display=None)
        
        # checks if start date less than end date and start date, end date in date range
        if start_date < pd.Timestamp("2000-01-01"):
            flash("Start date must be after 2000-01-01.")
            return render_template('index.html', symbols=symbols, chart_to_display=None)
        elif start_date > end_date:
            flash("Start date must be earlier than end date.")
            return render_template('index.html', symbols=symbols, chart_to_display=None)
        elif end_date > pd.Timestamp.today().normalize():
            flash("End date must be before today's date.")
            return render_template('index.html', symbols=symbols, chart_to_display=None)

        # mapping natural language to function required by API
        # converting Daily to TIME_SERIES_DAILY, etc.  
        time_series_map = {
            "Intraday": "TIME_SERIES_INTRADAY",
            "Daily": "TIME_SERIES_DAILY",
            "Weekly": "TIME_SERIES_WEEKLY",
            "Monthly": "TIME_SERIES_MONTHLY"
        }
        api_function = time_series_map.get(time_series)
        if not api_function:
            flash(f"Invalid time series selected: {time_series}")
            return render_template('index.html', symbols=symbols, chart_to_display=None)

        # gets dataframe from API
        print(symbol, chart_type, api_function, start_date, end_date)
        result = get_data(symbol, chart_type, api_function, start_date, end_date)
        
        if result is None or result.empty:
            flash("No data found for the selected symbol and date range. Please try again.")
            return render_template('index.html', symbols=symbols, chart_to_display=None)

        # returns chart to display 
        if chart_type == "Bar":
            chart_to_display = create_bar_chart(result, symbol, start_date, end_date)
        elif chart_type == "Line":
            chart_to_display = create_line_chart(result, symbol, start_date, end_date)
            
    return render_template('index.html', symbols=symbols, chart_to_display=chart_to_display)
    
    
#run the application
app.run(host="0.0.0.0", debug=True)
#removed port=5005 to containerize