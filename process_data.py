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
    # Sort the dataframe to be ascending to allow for early return
    incidents = incidents.sort_values('incident_datetime', ignore_index=True)

    # Create a series mapping the alarm box codes to an integer of the incident count
    incident_count = pandas.Series(data=0, index=alarm_boxes.alarm_box_code)

    # Create a series mappping the alarm box codes to a sum of the incident response times
    incident_rspns_sum = pandas.Series(
        data=0, index=alarm_boxes.alarm_box_code)

    for _, incident in incidents.iterrows():
        if incident.incident_datetime > end:
            # Create the new dataframe and return the values.
            return _generate_response_dataframe(alarm_boxes, incident_count, incident_rspns_sum)
        elif incident.incident_datetime >= start:
            if incident.alarm_box_code in incident_count:
                # Update the accumulators
                incident_count[incident.alarm_box_code] += 1
                incident_rspns_sum[incident.alarm_box_code] += incident.incident_response_seconds_qy

    return _generate_response_dataframe(alarm_boxes, incident_count, incident_rspns_sum)


def _generate_response_dataframe(alarm_boxes: pandas.DataFrame, incident_count: pandas.Series, incident_rspns_sum: pandas.Series) -> pandas.DataFrame:
    """Generate the pandas dataframe holding alarm box code, location, latitude, longitude,
    incident count, and average response time from the incident_count and incident_rspns_sum series

    Generates the return value of calc_average_response_times

    Helper for calc_average_response_time
    """
    avg_response = pandas.DataFrame({'alarm_box_code': alarm_boxes.alarm_box_code, 'alarm_box_location': alarm_boxes.alarm_box_location,
                                    'latitude': alarm_boxes.latitude, 'longitude': alarm_boxes.longitude, 'incident_count': incident_count.values})

    # Handle divison of zeros by substituting incident counts of 0 with 1. The incident counts are
    # already loaded into the dataframe so this operation does not affect avg_response counts.
    # Incident counts of 0 correspond to response sums of 0 so average response should be 0/1 = 0.0
    incident_count = incident_count.replace(to_replace=0, value=1)
    avg_response['average_response_time'] = avg_response.apply(
        axis='columns', func=lambda row: incident_rspns_sum.at[row.alarm_box_code] / incident_count[row.alarm_box_code])

    return avg_response


def remove_outliers_average_response(avg_response: pandas.DataFrame) -> pandas.DataFrame:
    """Removes outliers in the average response times dataframe

    The following are considered outliers and are removed from the dataframe:
        - incident_count of < 6

    Preconditions:
        - avg_response is a dataframe in the format specified by calc_average_response_times
    """
    return avg_response.drop(index=avg_response.loc[avg_response['incident_count'] <= 5].index)


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
