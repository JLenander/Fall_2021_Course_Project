"""CSC110 Fall 2021 Project, plot_data

Contains the code to plot the processed data using plotly.
Also contains the io code to save the plots into the directory 'output'

This file is Copyright (c) 2021 Joshua Lenander
"""
import math
import pandas
import plotly.express as px
import plotly.graph_objects


def plot_firehouses(firehouses: pandas.DataFrame, output=True) -> None:
    """Plot the firehouse locations on a scatter mapbox map using plotly.

    if <output> is True, save the plotly graph into the output directory as an html file.

    Preconditions:
        - firehouses is a valid dataframe of the firehouses
    """
    fig = px.scatter_mapbox(firehouses,
                            title='FDNY Firehouse Locations',
                            lat='latitude',
                            lon='longitude',
                            mapbox_style='carto-positron',
                            hover_name='facilityname',
                            hover_data=['address', 'zipcode', 'neighborhood'],
                            zoom=10)

    fig.show()
    if output:
        fig.write_html('output/firehouses.html')


def plot_alarm_boxes(alarm_boxes: pandas.DataFrame, output=True) -> None:
    """Plot the alarm boxes on a scatter mapbox using plotly

    if <output> is True, save the plotly graph into the output directory as an html file.

    Preconditions:
        - alarm_boxes is a valid dataframe of the alarm boxes
    """
    fig = px.scatter_mapbox(alarm_boxes,
                            title='FDNY Alarm Box Locations',
                            lat='latitude',
                            lon='longitude',
                            mapbox_style='carto-positron',
                            hover_name='alarm_box_code',
                            hover_data=['alarm_box_code', 'alarm_box_location'],
                            zoom=10)

    fig.show()
    if output:
        fig.write_html('output/alarm_boxes.html')


def _get_companies_plot(fire_companies: pandas.DataFrame, opacity=1.0) -> plotly.graph_objects.Figure:
    """Returns the plot of the fire companies on a choropleth mapbox map

    In the plot, color is by company type (Engine, Ladder, or Squad)

    Preconditions:
        - fire_companies is a valid dataframe of the fire companies
    """
    json_geom = _format_companies_for_plotly(fire_companies)

    # Create a copy of the fire companies and
    # Replace the company type letter with the full description name.
    fire_co_type_map = {'E': 'Engine', 'L': 'Ladder', 'Q': 'Squad'}
    fire_companies = fire_companies.copy()
    fire_companies['fire_co_type'] = fire_companies['fire_co_type'].apply(lambda type: fire_co_type_map[type])

    return px.choropleth_mapbox(fire_companies,
                                geojson=json_geom,
                                locations='company_name',
                                featureidkey='properties.company',
                                title='Firehouse Company Boundaries by Fire Company Type',
                                labels={'fire_bn': 'battalion',
                                        'fire_div': 'fire_division',
                                        'fire_co_type': 'fire_company_type'},
                                color='fire_co_type',
                                color_discrete_sequence=px.colors.qualitative.Pastel,
                                mapbox_style='carto-positron',
                                hover_name='company_name',
                                hover_data=['company_name',
                                            'fire_bn', 'fire_div'],
                                center={'lat': 40.70504, 'lon': -73.97223},
                                zoom=9,
                                opacity=opacity)


def plot_companies(fire_companies: pandas.DataFrame, output=True, opacity=1.0) -> None:
    """Plot the fire company boundaries on a choropleth mapbox map using plotly.

    if <output> is True, save the plotly graph into the output directory as an html file.

    Preconditions:
        - fire_companies is a valid dataframe of the fire companies
    """
    fig = _get_companies_plot(fire_companies, opacity)

    fig.show()
    if output:
        fig.write_html(f'output/fire_companies_opacity_{int(opacity * 100)}_percent.html')


def plot_companies_and_alarm_boxes(fire_companies: pandas.DataFrame, alarm_boxes, output=True, opacity=1.0) -> None:
    """Plot the fire company boundaries and alarm box locations on a choropleth mapbox map using plotly.

    if <output> is True, save the plotly graph into the output directory as an html file.

    Preconditions:
        - fire_companies is a valid dataframe of the fire companies
    """
    fig = _get_companies_plot(fire_companies, opacity)

    # Custom data for the hover information on the alarm box trace.
    # array is parallel to the alarm_boxes dataframe and contains
    # alarm_box_code and alarm box location for each alarm box
    customdata = [[alarm_boxes.alarm_box_code.iat[i], alarm_boxes.alarm_box_location.iat[i]]
                  for i in range(len(alarm_boxes))]

    fig.add_scattermapbox(customdata=customdata,
                          lat=alarm_boxes.latitude, lon=alarm_boxes.longitude, mode='markers',
                          hovertemplate=('<b>%{customdata[0]}</b><br><br>latitude=%{lat}<br>'
                                         'longitude=%{lon}<br>alarm_box_code=%{customdata[0]}'
                                         '<br>alarm_box_location=%{customdata[1]}<extra></extra>'),
                          marker_size=5, marker_color='rgb(0,0,0)', name='Alarm Boxes')

    # Update title
    fig.update_layout({'title': 'Fire Company boundaries and Alarm Box locations'})

    fig.show()
    if output:
        fig.write_html(f'output/fire_companies_and_alarm_boxes_opacity_{int(opacity * 100)}_percent.html')


def plot_companies_and_firehouses(fire_companies: pandas.DataFrame, firehouses: pandas.DataFrame, output=True, opacity=1.0) -> None:
    """Plot the fire companies and firehouse locations on a choropleth mapbox map using plotly.
    (the firehouse locations are a scatter map added to the choropleth map)

    if <output> is True, save the plotly graph into the output directory as an html file.

    Preconditions:
        - fire_companies is a valid dataframe of the fire companies
        - firehouses is a valid dataframe of the firehouses
    """
    fig = _get_companies_plot(fire_companies, opacity)

    # Custom data for the hover information on the alarm box trace.
    # array is parallel to the firehouses dataframe and contains
    # facilityname, address, zipcode, and neighborhood for each firehouse
    customdata = [[firehouses.facilityname.iat[i], firehouses.address.iat[i], firehouses.zipcode.iat[i],
                  firehouses.neighborhood.iat[i]] for i in range(len(firehouses))]

    fig.add_scattermapbox(customdata=customdata,
                          lat=firehouses.latitude, lon=firehouses.longitude, mode='markers',
                          hovertemplate=('<b>%{customdata[0]}</b><br><br>latitude=%{lat}<br>'
                                         'longitude=%{lon}<br>address=%{customdata[1]}<br>'
                                         'zipcode=%{customdata[2]}<br>'
                                         'neighborhood=%{customdata[3]}<extra></extra>'),
                          marker_size=6, marker_color='rgb(0,0,0)', name='Firehouses')

    # Update title
    fig.update_layout({'title': 'Firehouses and Fire Company boundaries'})

    fig.show()
    if output:
        fig.write_html(f'output/firehouses_and_companies_opacity_{int(opacity * 100)}_percent.html')


def plot_companies_and_response_times_animated(fire_companies_response_time: pandas.DataFrame,
                                               fire_companies: pandas.DataFrame, output=True, opacity=1.0) -> None:
    """Plot the fire companies and their average response times on a choropleth map.

    Separates the data by month using plotly's animation feature.

    Input data should have a column fora piece of data's month and year.
    Format of this column should be

    if <output> is True, save the plotly graph into the output directory as an html file.

    Preconditions:
        - fire_companies_response_time is a valid dataframe of the fire companies
        with the response_times from process_data.calc_companies_response_time
        - fire_companies is a valid dataframe of the fire companies from data_io.load_fire_companies_data
    """
    json_geom = _format_companies_for_plotly(fire_companies)

    # Find and round the minimum and maximum response times to the appropriate tens place
    # for the range of color.
    min_response = math.floor(fire_companies_response_time.response_times.min() / 10) * 10
    max_response = math.ceil(fire_companies_response_time.response_times.max() / 10) * 10
    color_range = [min_response, max_response]

    fig = px.choropleth_mapbox(fire_companies_response_time,
                               geojson=json_geom,
                               locations='company_name',
                               featureidkey='properties.company',
                               title=f'Average Incident Response Times per Company by Month and Year',
                               animation_frame='date',
                               animation_group='company_name',
                               labels={
                                   'response_times': 'average_response_time'},
                               color='response_times',
                               color_continuous_scale=px.colors.sequential.thermal,
                               range_color=color_range,
                               mapbox_style='carto-positron',
                               hover_data=['company_name', 'response_times', 'incident_count'],
                               center={'lat': 40.70504, 'lon': -73.97223},
                               zoom=9,
                               opacity=opacity)

    fig.show()
    if output:
        fig.write_html(f'output/avg_response_time_opacity_{int(opacity * 100)}_percent.html', auto_play=False)


def _format_companies_for_plotly(fire_companies: pandas.DataFrame) -> dict:
    """Formats the geojson to be within a FeatureCollection

    Each MultiPolygon dictionary is within a Feature dictionary.
    Each Feature Dictionary has properties and is within the FeatureCollection dictionary

    The id plotly uses will be part of the features property

    Helper for plot_companies and plot_companies_and_firehouses and plot_companies_and_response_time

    Preconditions:
        - fire_companies is a valid dataframe of the fire companies
    """
    # Use properties.key for featureidkey in plotly
    the_geom_list = list(fire_companies.the_geom)
    new_json_geom = {'type': 'FeatureCollection', 'features': []}
    for i in range(len(the_geom_list)):
        new_feature = {}
        new_feature['type'] = 'Feature'
        new_feature['properties'] = {
            'company': fire_companies.company_name[i], 'battalion': fire_companies.fire_bn[i]}
        new_feature['geometry'] = the_geom_list[i]
        new_json_geom['features'].append(new_feature)

    return new_json_geom
