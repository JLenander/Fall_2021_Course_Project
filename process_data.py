"""CSC110 Fall 2021 Project, process_data

Contains the code to process the dataset date and perform other calculations before
the visualization step.

This file is Copyright (c) 2021 Joshua Lenander
"""
from datetime import datetime

import pandas
from shapely.geometry import MultiPolygon, Point, Polygon


def get_response_time_per_alarm_box(incidents: pandas.DataFrame, alarm_boxes: pandas.DataFrame,
                                    start=datetime(2016, 1, 1), end=datetime(2021, 5, 6)) -> pandas.DataFrame:
    """Extract the sum of the response times (in seconds) for each alarm box in alarm_boxes
    restrict data to times after <start> and before <end>.
    <start> bound is inclusive
    <end> bound is exclusive

    Returns a dataframe with columns alarm_box_code, alarm_box_location, latitude, longitude
        incident_count, and response_time_sum

    Preconditions:
        - start < end
    """

    # Create a series mapping the alarm box codes to an integer of the incident count
    incident_count = pandas.Series(data=0, index=alarm_boxes.alarm_box_code)

    # Create a series mapping the alarm box codes to a sum of the incident response times
    incident_rspns_sum = pandas.Series(data=0, index=alarm_boxes.alarm_box_code)

    # Locate the specific range of incidents
    incidents_in_range = incidents.loc[incidents.incident_datetime >= start].loc[incidents.incident_datetime < end]

    for incident in incidents_in_range.itertuples():
        code = incident.alarm_box_code

        # Ignore alarm boxes we do not have location data for
        if code in incident_count:
            incident_count[code] += 1
            incident_rspns_sum[code] += incident.incident_response_seconds_qy

    alarm_box_response = pandas.DataFrame({'alarm_box_code': alarm_boxes.alarm_box_code, 'alarm_box_location': alarm_boxes.alarm_box_location,
                                    'latitude': alarm_boxes.latitude, 'longitude': alarm_boxes.longitude, 'incident_count': incident_count.values,
                                    'response_time_sum': incident_rspns_sum.values})

    return alarm_box_response

# NOTE no longer correct for this implementation
# def remove_outliers_average_response(avg_response: pandas.DataFrame, min_incident_count=3) -> pandas.DataFrame:
#     """Returns a new average response dataframe with outliers removed

#     The following are considered outliers and are removed from the dataframe:
#         - incident_count of < min_incident_count

#     Preconditions:
#         - avg_response is a dataframe in the format specified by calc_average_response_times
#     """
#     return avg_response.drop(index=avg_response.loc[avg_response['incident_count'] < min_incident_count].index)


def remove_outliers_companies_response(companies_response: pandas.DataFrame) -> pandas.DataFrame:
    """Returns a new company response times dataframe with outliers removed

    The following are considered outliers and are removed from the dataframe:
        - companies_response.response_times < 1.0
        - companies_response.response_times > 2500.0

    Preconditions:
        - companies_response is a dataframe in the format specified by calc_companies_response_time
    """
    lower_bound_indices = companies_response.loc[companies_response.response_times < 1.0].index
    upper_bound_indices = companies_response.loc[companies_response.response_times > 2500.0].index

    companies_response = companies_response.drop(lower_bound_indices)
    companies_response = companies_response.drop(upper_bound_indices)

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


def calc_companies_response_time(fire_companies: pandas.DataFrame, alarm_box_response: pandas.DataFrame,
                                 company_to_boxes: dict[str, list[str]]) -> pandas.DataFrame:
    """Calculate the average response time for each fire company
    Returns a copy of fire_companies with a new column for average response time and a new column
    for the number of incidents recorded for that company.

    <alarm_box_response> is a dataframe in the format of the output of get_response_time_per_alarm_box
    <company_to_boxes> is a dictionary in the format of the output of map_companies_to_alarm_boxes

    Each company's average response time is the average of each alarm box's response time
    contained within the company boundary

    Preconditions:
        - fire_companies is a valid dataframe of the fire companies
        - alarm_box_response is a valid dataframe of the response time data per alarm box
        - company_to_boxes is a dictionary mapping the fire companies name to a list of alarm boxes
            located within that company. See map_companies_to_alarm_boxes
    """
    # DataFrame connecting company name to the average response times for the company and to incident counts.
    company_response_times = pandas.DataFrame(data={'response_times': 0.0, 'incident_count': 0},
                                              index=list(company_to_boxes.keys()), columns=['response_times', 'incident_count'])

    for company_name in company_to_boxes:
        # The segment of the alarm box response times corresponding to the company
        company_response_segment = alarm_box_response.loc[alarm_box_response['alarm_box_code'].isin(
            company_to_boxes[company_name])]

        # Avoid divide by 0
        if company_response_segment.response_time_sum.sum() > 0:
            avg_time = company_response_segment.response_time_sum.sum() / company_response_segment.incident_count.sum()
            company_response_times.response_times.at[company_name] = avg_time

        company_response_times.incident_count.at[company_name] = company_response_segment.incident_count.sum()

    firehouse_copy = fire_companies.copy()
    # Drop unused field the_geom
    firehouse_copy = firehouse_copy.drop(columns='the_geom')
    firehouse_copy['response_times'] = company_response_times.response_times.values
    firehouse_copy['incident_count'] = company_response_times.incident_count.values
    return firehouse_copy


def map_companies_to_alarm_boxes(fire_companies: pandas.DataFrame, alarm_boxes: pandas.DataFrame) -> dict[str, list[str]]:
    """Maps the fire company boundaries to the alarm boxes located within
    Returns a dictionary mapping the company name to a list of alarm box codes

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


def concat_company_responses(companies_response_by_month: dict[datetime, pandas.DataFrame]) -> pandas.DataFrame:
    """Return a single dataframe of company response data by month
    Returned dataframe contains a column "date" that points to what date the data is for.
    Modifies each original dataframe to include the date column.

    Input dictionary companies_response_times_by_month has a datetime object as the key pointing to a
    dataframe of the format specified in calc_companies_response_time.


    Used for plotly animation of the response time data
    """

    for date in companies_response_by_month:
        # A new column 'date' containing *date* is added to the dataframe pointed to by *date*
        # *date* is a datetime object
        companies_response_by_month[date]['date'] = date

    return pandas.concat([companies_response_by_month[date] for date in companies_response_by_month], ignore_index=True)
