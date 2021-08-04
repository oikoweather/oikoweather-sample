import os
import json
import requests
import math

from ladybug.epw import EPW
from ladybug.location import Location
from ladybug.analysisperiod import AnalysisPeriod
from ladybug.sunpath import Sunpath
from ladybug.skymodel import estimate_illuminance_from_irradiance
from ladybug.config import folders


def oiko_make_epw(api_key, city, country, latitude, longitude, year):
    '''
    Args:}
        api_key: User API key for OikoLab.
        city: city name as string
        country: country name as string.
        latitude: Location latitude between -90 and 90
        longitude: Location longitude between -180 (west) and 180 (east)
        year: year between 1980 and 2019
    '''

    parameters = [
        'temperature', 'dewpoint_temperature',
        'surface_solar_radiation', 'surface_thermal_radiation',
        'surface_direct_solar_radiation', 'surface_diffuse_solar_radiation',
        'relative_humidity', 'wind_speed', 'surface_pressure', 'total_cloud_cover'
    ]
    location = Location(city=city, country=country, latitude=latitude, longitude=longitude)
    
    # create the payload
    payload = {
        'param': parameters,
        'start': '{}-01-01T00:00:00'.format(year),
        'end': '{}-12-31T23:00:00'.format(year),
        'lat': location.latitude,
        'lon': location.longitude,
    }

    # make the request
    r = requests.get('https://api.oikolab.com/weather',
                     params=payload,
                     headers={'content-encoding': 'gzip',
                              'Connection': 'close',
                              'api-key': '{}'.format(api_key)})

    if r.status_code == 200:
        attributes = r.json()['attributes']
        weather_data = json.loads(r.json()['data'])
    else:
        print(r.text)
        return None


    # set the UTC offset on the location based on the request
    location.time_zone = attributes['utc_offset']
    leap_yr = True if year % 4 == 0 else False

    # create a dictionary of timeseries data streams
    data_dict = {}
    data_values = zip(*weather_data['data'])
    for param, data in zip(parameters, data_values):
        data_dict[param] = data

    # compute solar radiation components and estimate illuminance from irradiance
    datetimes = AnalysisPeriod(is_leap_year=leap_yr).datetimes

    direct_normal_irr = []
    gh_ill = []
    dn_ill = []
    dh_ill = []
    sp = Sunpath.from_location(location)
    sp.is_leap_year = leap_yr
    for dt, glob_hr, dir_hr, dif_hr, dp in zip(
            datetimes, data_dict['surface_solar_radiation'],
            data_dict['surface_direct_solar_radiation'],
            data_dict['surface_diffuse_solar_radiation'], 
            data_dict['dewpoint_temperature']):
        sun = sp.calculate_sun_from_date_time(dt)
        alt = sun.altitude
        dir_nr = dir_hr / math.sin(math.radians(alt)) if alt > 0 else 0
        direct_normal_irr.append(dir_nr)
        gh, dn, dh, z = estimate_illuminance_from_irradiance(alt, glob_hr, dir_nr, dif_hr, dp)
        gh_ill.append(gh)
        dn_ill.append(dn)
        dh_ill.append(dh)

    # create the EPW object and set properties
    epw = EPW.from_missing_values(is_leap_year=leap_yr)
    epw.location = location
    epw.years.values = [year] * 8760 if not leap_yr else [year] * 8784
    epw.dry_bulb_temperature.values = data_dict['temperature']
    epw.dew_point_temperature.values = data_dict['dewpoint_temperature']
    epw.global_horizontal_radiation.values = data_dict['surface_solar_radiation']
    epw.direct_normal_radiation.values = direct_normal_irr
    epw.diffuse_horizontal_radiation.values = data_dict['surface_diffuse_solar_radiation']
    epw.global_horizontal_illuminance.values = gh_ill
    epw.direct_normal_illuminance.values = dn_ill
    epw.diffuse_horizontal_illuminance.values = dh_ill
    epw.horizontal_infrared_radiation_intensity.values = data_dict['surface_thermal_radiation']
    epw.relative_humidity.values = [val * 100.0 for val in data_dict['relative_humidity']]
    epw.atmospheric_station_pressure.values = data_dict['surface_pressure']
    epw.total_sky_cover.values = data_dict['total_cloud_cover']
    epw.wind_speed.values = data_dict['wind_speed']
    
    # write EPW to a file
    file_path = os.path.join(folders.default_epw_folder, '{}_{}.epw'.format(location.city, year))
    epw.save(file_path)
    print('EPW file generated and saved to - %s'% file_path)
    
    return file_path


api_key = '<INSERT YOUR API KEY HERE>'            # API key from https://oikolab.com/profile after signing up to a subscription
city, country ='Ross Ice Shelf', 'Antartica'
latitude, longitude = -81.5, -175.0
year = 2010

oiko_make_epw(api_key, city, country, latitude, longitude, year)
