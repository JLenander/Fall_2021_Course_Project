"""CSC110 Fall 2021 Project, data_io

Contains the code to get data from datasets and databases.
Also contains code to save and load processed data into local files.

This file is Copyright (c) 2021 Joshua Lenander
"""
from datetime import datetime

import pandas
import requests


def save_data_frame(df: pandas.DataFrame, path: str) -> None:
    """Saves the dataframe data into a csv file. It is recommended to save to
    the directory 'data/processed/'

    Does not save the indices of the dataframe data in the file.
    """
    df.to_csv(path, index=False)


def load_data_frame(path: str) -> pandas.DataFrame:
    """Loads the dataframe data from a csv file. By convention, the file should be in
    the directory 'data/processed/'
    """
    return pandas.read_csv(path)


def request_incidents(app_token='', filename='data/Fire_Incident_Dispatch_2016_to_2021.csv') -> bool:
    """Uses the database socrata api to request and download the fdny incident dispatch data
    into a csv file.

    Filters to be between jan 1st 2016 to may 5th 2021 (data is only available up to may 5th)
    Free app token optional for lower throttling limit
    (Highly recommend calling this iwth an app token, otherwise it would take too long)

    Returns whether the operation was successful

    Warning! This is expected to be a large file (almost a gigabyte)

    Preconditions:
        - app_token == '' or a valid socrata app_token
    """
    # Filter between jan 1st 2016 to may 5th 2021 using socrata api.
    # Also filter to only include values with valid incident response times.
    url = ('https://data.cityofnewyork.us/resource/8m42-w767.csv?'
           'VALID_INCIDENT_RSPNS_TIME_INDC=Y&'
           '$where=incident_datetime%20between%20%272016-01-01T00:00:00%27%20'
           'and%20%272021-05-05T23:59:59%27&$limit=3000000')

    # If app token supplied, append it to the request
    if app_token != '':
        url += f'&$$app_token={app_token}'

    data = requests.get(url)

    # Response 200, content should contain the csv data.
    if data.ok:
        open(filename, 'wb').write(data.content)
        return True

    return False


def load_incidents(filename='data/Fire_Incident_Dispatch_2016_to_2021.csv') -> pandas.DataFrame:
    """Load a dataframe of the fire incidents.
    Uses the memory_map option to improve loading and memory performance.

    Cuts policeprecinct, citycouncildistrict, communitydistrict, communityschooldistrict,
    congressionaldistrict, dispatch_response_seconds_qy, valid_dispatch_rspns_time_indc,
    and valid_incident_rspns_time_indc

    Preconditions:
        - filename exists
    """
    incidents = pandas.read_csv(filename, memory_map=True)

    # convert the incident datetime string into a datetime object (which is then converted into a pandas.timestamp obj)
    incidents['incident_datetime'] = incidents.apply(
        axis='columns', func=lambda row: datetime.fromisoformat(row.incident_datetime))

    # some zip codes are missing which is inferred as NaN but this forces zipcodes to be type float64.
    # convert NaNs to -1 so zipcodes are just int64
    incidents.zipcode.fillna(-1, inplace=True, downcast='int64')

    # generate the alarm_box_code from the alarm_box_borough and the alarm_box_number
    incidents['alarm_box_code'] = incidents.apply(
        axis='columns', func=lambda row: _generate_alarm_box_code(row.alarm_box_borough, row.alarm_box_number))

    # drop some unneeded columns
    incidents = incidents.drop(axis='columns', labels=['policeprecinct', 'citycouncildistrict', 'communitydistrict',
                                                       'communityschooldistrict', 'congressionaldistrict',
                                                       'dispatch_response_seconds_qy', 'valid_dispatch_rspns_time_indc',
                                                       'valid_incident_rspns_time_indc'])

    # ensure incidents sorted by incident_datetime
    incidents = incidents.sort_values('incident_datetime', ignore_index=True)
    return incidents


def _generate_alarm_box_code(borough: str, number: int) -> str:
    """Generates the alarm box code from the borough prefix and the alarm box number

    Helper for load_incidents

    Preconditions:
        - borough in {'BROOKLYN', 'BRONX', 'QUEENS', 'MANHATTAN', 'STATEN ISLAND', 'RICHMOND / STATEN ISLAND'}
        - 0 <= number <= 9999

    >>> generate_alarm_box_code('MANHATTAN', 171)
    'M0171'
    """
    borough_prefixes = {'BROOKLYN': 'B', 'BRONX': 'X', 'QUEENS': 'Q',
                        'MANHATTAN': 'M', 'STATEN ISLAND': 'R', 'RICHMOND / STATEN ISLAND': 'R'}
    return borough_prefixes[borough] + f'{number:04}'


def load_firehouse_data() -> pandas.DataFrame:
    """Loads the physical fire house location data into a pandas dataframe
    Also adds data for the list of companies in the firehouse (listed in facilityname)
    and adds data for the location in geojson format.

    Cuts community_board, community_council, census_tract, bin (building identification number) and bbl
    """
    # dataset link
    url = 'https://data.cityofnewyork.us/resource/hc8x-tcnd.json'
    firehouses = pandas.read_json(url)

    # Drop some uneeded columns
    firehouses = firehouses.drop(axis='columns', labels=['community_board',
                                 'community_council', 'census_tract', 'bin', 'bbl'])

    # Rename a few columns for consistency
    firehouses.rename({'facilityaddress': 'address', 'postcode': 'zipcode',
                      'nta': 'neighborhood'}, axis='columns', inplace=True)

    # companies is a list of the companies located in the firehouse (ex. [Engine 1, Ladder 24])
    firehouses['companies'] = firehouses.apply(
        axis=1, func=lambda row: row.facilityname.split('/'))

    return firehouses


def load_fire_companies_data() -> pandas.DataFrame:
    """Loads the data for the boundaries of the fire companies into a pandas dataframe

    Cuts shape_leng, and shape_area
    """
    url = 'https://data.cityofnewyork.us/resource/bst7-5464.json'
    df = pandas.read_json(url)

    # Drop some unneeded columns
    df = df.drop(axis='columns', labels=['shape_leng', 'shape_area'])

    # Extract the name of the company from the fire_co_type and the fire_co_num
    df['company_name'] = df.apply(axis=1, func=_get_company_name)

    return df


def _get_company_name(row: pandas.Series) -> str:
    """Generates the company name from the fire_co_type and the fire_co_num

    Helper for load_fire_companies_data
    """
    type_to_name = {'L': 'Ladder', 'E': 'Engine', 'Q': 'Squad'}
    return type_to_name[row.fire_co_type] + ' ' + str(row.fire_co_num)


def load_alarm_boxes() -> pandas.DataFrame:
    """Gets the location data for in service alarm boxes
    uses local csv data because api data is different

    the dataset contains duplicate entries due to some points having multiple districts.
    removes these duplicates

    Cuts COMMUNITYDISTICT, CITYCOUNCIL, and Location Point
    """
    file = 'data/In-Service_Alarm_Box_Locations.csv'
    df = pandas.read_csv(file)

    # Note this is not a typo, the dataset misspelled district as distic
    df = df.drop(axis='columns', labels=[
                 'COMMUNITYDISTICT', 'CITYCOUNCIL', 'Location Point'])

    # Rename columns for consistency
    df = df.rename({'BOROBOX': 'alarm_box_code', 'BOX_TYPE': 'alarm_box_type',
                    'LOCATION': 'alarm_box_location', 'ZIP': 'zipcode', 'BOROUGH': 'borough',
                    'LATITUDE': 'latitude', 'LONGITUDE': 'longitude'}, axis='columns')

    # Drop the duplicate entries. Duplicate entries exist for boxes on the borders
    # of community and city council districts. No difference in location or box code.
    df = df.drop_duplicates(subset='alarm_box_code')

    return df
