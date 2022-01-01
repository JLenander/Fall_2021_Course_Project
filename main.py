"""CSC110 Fall 2021 Project, main file

Contains the main project function

This file is Copyright (c) 2021 Joshua Lenander
"""
from datetime import datetime
from dateutil.relativedelta import *

import data_io
import plot_data
import process_data


def main():
    """The main block for the project
    Running should produce an output file in output/
    """
    # firehouses = data_io.load_firehouse_data()
    fire_companies = data_io.load_fire_companies_data()
    alarm_boxes = data_io.load_alarm_boxes()
    incidents = data_io.load_incidents()

    # Start and End bounds for the data range. Start bound is inclusive, end bound is exclusive.
    start_date = datetime(2018,4,1)
    end_date = datetime(2021,5,1) # Incident data only available until 2021/05/06

    # Dict mapping month to alarm box response dataframe
    alarm_box_response = {}

    # Calculate each month's alarm box response
    current_date = start_date
    while current_date < end_date:
        next_month = current_date + relativedelta(months=+1)
        alarm_box_response[current_date] = process_data.get_response_time_per_alarm_box(incidents, alarm_boxes, start=current_date, end=next_month)
        current_date = next_month

    company_to_boxes = process_data.map_companies_to_alarm_boxes(fire_companies, alarm_boxes)
    # Dict mapping the month to the company response dataframe
    company_responses = {}
    for date in alarm_box_response:
        company_responses[date] = process_data.calc_companies_response_time(fire_companies, alarm_box_response[date], company_to_boxes)
    
    # Concatenate the results into one dataframe with a date column
    company_responses_by_month = process_data.concat_company_responses(company_responses)

    # Date is a pandas timestamp object and needs to be converted to a string.
    # Also trims the day from the timestamp.
    company_responses_by_month.date = company_responses_by_month.date.apply(lambda timestamp: f'{timestamp.year}-{timestamp.month}')

    # Save company_responses_by_month to file
    data_io.save_data_frame(company_responses_by_month, 'data/processed/company_responses_by_month.csv')
    # # Load company_responses_by_month from file
    # company_responses_by_month = data_io.load_data_frame('data/processed/company_responses_by_month.csv')

    # Optionally remove outliers in response data. This will leave holes in the map for regions with no data
    company_responses_by_month = process_data.remove_outliers_companies_response(company_responses_by_month)

    plot_data.plot_companies_and_response_times_animated(company_responses_by_month, fire_companies, True)
    # plot_data.plot_companies_and_firehouses(fire_companies, firehouses, True)

    # TODO remove geom from processed data and save company to boxes instead

if __name__ == '__main__':
    main()
