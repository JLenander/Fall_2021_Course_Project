"""CSC110 Fall 2021 Project, process_data

Contains the code to process the dataset date and perform other calculations before
the visualization step.

This file is Copyright (c) 2021 Joshua Lenander
"""
from datetime import datetime

import pandas
from shapely.geometry import MultiPolygon, Point, Polygon


def calc_average_response_times(incidents: pandas.DataFrame, alarm_boxes: pandas.DataFrame, start=datetime(2016, 1, 1), end=datetime(2021, 5, 6)) -> pandas.DataFrame:
    """Calculate the average response time (in seconds) for each alarm box in alarm_boxes
    restrict calculation to times after <start> and before <end>.
    <start> bound is inclusive
    <end> bound is exclusive

    Returns a dataframe with columns alarm_box_code, alarm_box_location, latitude, longitude
        alarm_box_incident_count, and alarm_box_average_response

    Preconditions:
        - start < end
    """

    # Create a series mapping the alarm box codes to an integer of the incident count
    incident_count = pandas.Series(data=0, index=alarm_boxes.alarm_box_code)

    # Create a series mappping the alarm box codes to a sum of the incident response times
    incident_rspns_sum = pandas.Series(data=0, index=alarm_boxes.alarm_box_code)

    # Locate the specific range of incidents
    incidents_in_range = incidents.loc[incidents.incident_datetime >= start].loc[incidents.incident_datetime < end]

    for incident in incidents_in_range.itertuples():
        code = incident.alarm_box_code
        
        # Ignore alarm boxes we do not have location data for
        if code in incident_count:
            incident_count[code] += 1
            incident_rspns_sum[code] += incident.incident_response_seconds_qy

    avg_response = pandas.DataFrame({'alarm_box_code': alarm_boxes.alarm_box_code, 'alarm_box_location': alarm_boxes.alarm_box_location,
                                    'latitude': alarm_boxes.latitude, 'longitude': alarm_boxes.longitude, 'incident_count': incident_count.values})

    # Handle divison of zeros by substituting incident counts of 0 with 1. The incident counts are
    # already loaded into the dataframe so this operation does not affect avg_response counts.
    # Incident counts of 0 correspond to response sums of 0 so average response should be 0/1 = 0.0
    incident_count.replace(to_replace=0, value=1, inplace=True)

    # Perform the average calculation
    avg_response['average_response_time'] = avg_response.apply(
        axis='columns', func=lambda row: incident_rspns_sum.at[row.alarm_box_code] / incident_count[row.alarm_box_code])

    return avg_response


def remove_outliers_average_response(avg_response: pandas.DataFrame, min_incident_count=3) -> pandas.DataFrame:
    """Returns a new average response dataframe with outliers removed

    The following are considered outliers and are removed from the dataframe:
        - incident_count of < min_incident_count

    Preconditions:
        - avg_response is a dataframe in the format specified by calc_average_response_times
    """
    return avg_response.drop(index=avg_response.loc[avg_response['incident_count'] < min_incident_count].index)


def remove_outliers_companies_response(companies_response: pandas.DataFrame) -> pandas.DataFrame:
    """Returns a new company response times dataframe with outliers removed

    Known outliers, Engine 70 and Ladder 53

    FOLLOWING NOT IMPLEMENTED
    The following are considered outliers and are removed from the dataframe:
        - companies_response.response_times < 1.0
        - companies_response.response_times > 2500.0

    Preconditions:
        - companies_response is a dataframe in the format specified by calc_companies_response_time
    """
    E70_indices = companies_response.loc[companies_response.company_name == 'Engine 70'].index
    L53_indices = companies_response.loc[companies_response.company_name == 'Ladder 53'].index
    
    companies_response = companies_response.drop(E70_indices)
    companies_response = companies_response.drop(L53_indices)

    print('Have not implemented avg_response >1.0 or <2500.0')
    return companies_response


def convert_geojson_to_shapely(multipolygon: dict) -> MultiPolygon:
    """Converts the geojson formatted multipolygon into a shapely MultiPolygon object

    Preconditions:
        - multipolygon is a geojson formatted multipolygon dictionary
    """
    geojson_polygons = multipolygon['coordinates']
    shapely_polygons = []
    for json_polygon in geojson_polygons:
        shapely_polygons.append(
            Polygon(json_polygon[0], holes=json_polygon[1:]))

    return MultiPolygon(shapely_polygons)


def calc_companies_response_time(fire_companies: pandas.DataFrame, alarm_boxes: pandas.DataFrame,
    avg_response: pandas.DataFrame) -> pandas.DataFrame:
    """Calculate the average response time for each fire company
    Returns a copy of fire_companies with a new column for average response time

    <avg_response> is a dataframe in the format of the output of calc_average_response_time

    Each company's average response time is the average of each alarm box's response time
    contained within the company boundary

    Preconditions:
        - fire_companies is a valid dataframe of the fire companies
        - alarm_boxes is a valid dataframe of the alarm boxes
        - avg_response is a valid dataframe of the average response time per alarm box
    """
    company_to_boxes = _map_companies_to_alarm_boxes(
        fire_companies, alarm_boxes)

    company_response_times = pandas.Series(
        data=0, index=list(company_to_boxes.keys()))
    for company_name in company_to_boxes:
        company_average_response = 0.0

        # The segment of the response times corresponding to the company
        company_response_segment = avg_response.loc[avg_response['alarm_box_code'].isin(
            company_to_boxes[company_name])]

        # Avoid divide by 0
        if len(company_response_segment) > 0:
            company_average_response = company_response_segment.average_response_time.sum() / \
                len(company_response_segment)

        company_response_times.at[company_name] = company_average_response

    firehouse_copy = fire_companies.copy()
    firehouse_copy['response_times'] = company_response_times.values
    return firehouse_copy


def _map_companies_to_alarm_boxes(fire_companies: pandas.DataFrame, alarm_boxes: pandas.DataFrame) -> dict[str, list[str]]:
    """Maps the fire company boundaries to the alarm boxes located within
    Returns a dictionary mapping the company name to a list of alarm box codes

    Helper for calc_companies_response_time

    Preconditions:
        - fire_companies is a valid dataframe of the fire companies
        - alarm_boxes is a valid dataframe of the alarm boxes
    """
    # dict of company name to the list of alarm box names
    company_to_boxes = {row.company_name: []
                        for _, row in fire_companies.iterrows()}
    # dict of company name to the shapely multipolygon shape of the boundary
    company_boundaries = _get_shapely_geometry(fire_companies)
    # dict of alarm box point codes to the alarm box point location
    alarm_box_locations = {row.alarm_box_code: Point(
        row.longitude, row.latitude) for _, row in alarm_boxes.iterrows()}

    for company_name in company_to_boxes.keys():
        company_to_boxes[company_name] = _find_alarm_boxes_in_boundary(
            alarm_box_locations, company_boundaries[company_name])

        # Remove the boxes that were found in the boundary from the dictionary
        # (each box can only be in one space)
        for box_code in company_to_boxes[company_name]:
            alarm_box_locations.pop(box_code)

    return company_to_boxes


def _find_alarm_boxes_in_boundary(boxes: dict[str, Point], boundary: MultiPolygon) -> list[str]:
    """Returns the list of alarm boxes codes that are within the boundary

    Helper for map_companies_to_alarm_boxes

    Preconditions:
        - Each Point object in boxes corresponds to it's key's alarm box position.
    """
    contained_list = []
    for alarm_box in boxes:
        if boundary.contains(boxes[alarm_box]):
            contained_list.append(alarm_box)

    return contained_list


def _get_shapely_geometry(fire_companies: pandas.DataFrame) -> dict[str, MultiPolygon]:
    """Return a dictionary mapping the company name to the shapely multipolygon object

    Helper for map_companies_to_alarm_boxes

    Preconditions:
        - fire_companies is a valid dataframe of the fire companies
    """
    shapes = {}
    for _, row in fire_companies.iterrows():
        shapes[row.company_name] = convert_geojson_to_shapely(row.the_geom)
    return shapes


def concat_company_responses(companies_response_by_year: dict[int, pandas.DataFrame]) -> pandas.DataFrame:
    """Return a single dataframe of company response data by year
    Returned dataframe contains a column "year" that points to what year the data is for.
    Modifies each original dataframe to include the year column.

    Input dictionary companies_response_times_by_year has the year as the key pointing to a
    dataframe of the format specified in calc_companies_response_time

    Used for plotly animation of the response time data
    """

    for year in companies_response_by_year:
        # A new column 'year' containing *year* is added to the dataframe pointed to by *year*
        # *year* is an integer.
        companies_response_by_year[year]['year'] = year
    
    return pandas.concat([companies_response_by_year[year] for year in companies_response_by_year], ignore_index=True)
