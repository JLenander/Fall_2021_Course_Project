"""CSC110 Fall 2021 Project, main file

Contains the main project function

This file is Copyright (c) 2021 Joshua Lenander
"""
import data_io
import plot_data
import process_data


def main():
    """The main block for the project
    Should save 3 files into the output directory
    """
    fire_companies = data_io.load_fire_companies_data()
    # firehouses = data_io.load_firehouse_data()
    # incidents = data_io.load_incidents()
    alarm_boxes = data_io.load_alarm_boxes()

    # avg_response_2018 = data_io.load_data_frame('data/processed/avg_response_2018.csv')
    # avg_response_2019 = data_io.load_data_frame('data/processed/avg_response_2019.csv')
    # avg_response_2020 = data_io.load_data_frame('data/processed/avg_response_2020.csv')

    avg_responses = {year: data_io.load_data_frame(f'data/processed/avg_response_{year}.csv') 
                          for year in {2018, 2019, 2020}}

    for year in avg_responses:
        avg_responses[year] = process_data.remove_outliers_average_response(avg_responses[year])

    # companies_2018 = process_data.calc_companies_response_time(fire_companies, alarm_boxes, avg_response_2018)
    # companies_2019 = process_data.calc_companies_response_time(fire_companies, alarm_boxes, avg_response_2019)
    # companies_2020 = process_data.calc_companies_response_time(fire_companies, alarm_boxes, avg_response_2020)

    companies_response = {year: process_data.calc_companies_response_time(fire_companies, 
                          alarm_boxes, avg_responses[year]) for year in {2018, 2019, 2020}}


    # plot_data.plot_companies_and_firehouses(fire_companies, firehouses, True)
    # plot_data.plot_companies_and_response_time(companies_2018, 2018, True)
    # plot_data.plot_companies_and_response_time(companies_2019, 2019, True)
    # plot_data.plot_companies_and_response_time(companies_2020, 2020, True)

    companies_response_with_date = process_data.concat_company_responses(companies_response)

    companies_response_with_date = process_data.remove_outliers_companies_response(companies_response_with_date)

    plot_data.plot_companies_and_response_times_animated(companies_response_with_date, fire_companies, True)

if __name__ == '__main__':
    main()
