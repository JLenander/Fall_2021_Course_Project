"""CSC110 Fall 2021 Project, plot_data

Contains the code to plot the processed data using plotly.
Also contains the io code to save the plots into the directory 'output'

This file is Copyright (c) 2021 Joshua Lenander
"""
import math
import pandas
import plotly.express as px


def plot_firehouses(firehouses: pandas.DataFrame, output=True) -> None:
    """Plot the firehouse locations on a scatter mapbox map using plotly.

    if <output> is True, instead of calling fig.show(), will save the plotly graph into
    the output directory as an html file.

    Preconditions:
        - firehouses is a valid dataframe of the firehouses
    """
    fig = px.scatter_mapbox(firehouses,
                            lat='latitude',
                            lon='longitude',
                            mapbox_style='carto-positron',
                            hover_name='facilityname')

    if output:
        fig.write_html('output/firehouses.html')
    else:
        fig.show()


def plot_companies(fire_companies: pandas.DataFrame, output=True) -> None:
    """Plot the fire companies on a choropleth mapbox map using plotly.

    if <output> is True, instead of calling fig.show(), will save the plotly graph into
    the output directory as an html file.

    Preconditions:
        - fire_companies is a valid dataframe of the fire companies
    """
    json_geom = _format_companies_for_plotly(fire_companies)

    fig = px.choropleth_mapbox(fire_companies,
                               geojson=json_geom,
                               locations='company_name',
                               featureidkey='properties.company',
                               title='Firehouse Company Boundaries',
                               labels={'fire_bn': 'battalion',
                                       'fire_div': 'fire_division'},
                               color='fire_div',
                               color_continuous_scale=px.colors.sequential.algae,
                               mapbox_style='carto-positron',
                               hover_name='company_name',
                               hover_data=['company_name',
                                           'fire_bn', 'fire_div'],
                               center={'lat': 40.70, 'lon': -74.0},
                               zoom=9,
                               opacity=1.0,
                               width=1000,
                               height=600)

    if output:
        fig.write_html('output/fire_companies.html')
    else:
        fig.show()


def plot_companies_and_firehouses(fire_companies: pandas.DataFrame, firehouses: pandas.DataFrame, output=True) -> None:
    """Plot the fire companies and firehouse locations on a choropleth mapbox map using plotly.
    (the firehouse locations are a scatter map added to the choropleth map)

    if <output> is True, instead of calling fig.show(), will save the plotly graph into
    the output directory as an html file.

    Preconditions:
        - fire_companies is a valid dataframe of the fire companies
        - firehouses is a valid dataframe of the firehouses
    """
    json_geom = _format_companies_for_plotly(fire_companies)

    fig = px.choropleth_mapbox(fire_companies,
                               geojson=json_geom,
                               locations='company_name',
                               featureidkey='properties.company',
                               title='Firehouse locations and Company Boundaries',
                               labels={'fire_bn': 'battalion',
                                       'fire_div': 'fire_division'},
                               color='fire_div',
                               color_continuous_scale=px.colors.sequential.algae,
                               mapbox_style='carto-positron',
                               hover_data=['company_name',
                                           'fire_bn', 'fire_div'],
                               center={'lat': 40.70, 'lon': -74.0},
                               zoom=9,
                               opacity=1.0,
                               width=1000,
                               height=600)

    fig.add_scattermapbox(lat=firehouses.latitude, lon=firehouses.longitude, mode='markers+text',
                          text=firehouses.facilityname, marker_size=5, marker_color='rgb(0,0,0)')

    if output:
        fig.write_html('output/firehouses_and_companies.html')
    else:
        fig.show()


def plot_companies_and_response_times_animated(fire_companies_response_time: pandas.DataFrame, 
    fire_companies: pandas.DataFrame, output=True) -> None:
    """Plot the fire companies and their average response times on a choropleth map.

    Separates the data by month using plotly's animation feature.

    Input data should have a column fora piece of data's month and year.
    Format of this column should be 

    if <output> is True, instead of calling fig.show(), will save the plotly graph into
    the output directory as an html file.

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
                               title=f'Average Incident Response Times by Company By Month and Year',
                               animation_frame='date',
                               animation_group='company_name',
                               labels={
                                   'response_times': 'average_response_time'},
                               color='response_times',
                               color_continuous_scale=px.colors.sequential.thermal,
                               range_color=color_range,
                               mapbox_style='carto-positron',
                               hover_data=['company_name', 'response_times', 'incident_count'],
                               center={'lat': 40.70, 'lon': -74.0},
                               zoom=9,
                               opacity=1.0,
                               width=1280,
                               height=720)

    if output:
        fig.write_html(f'output/avg_response_time_anim.html', auto_play=False)
    else:
        fig.show()


def _format_companies_for_plotly(fire_companies: pandas.DataFrame) -> dict:
    """Formats the geojson to be within a FeatureCollection

    Each MultiPolygon dictionary is within a Feature dicionary.
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
