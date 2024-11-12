"""
This script exports trail data from Wikiloc and updates a map on MapHub with the trail information.
Modules:
    collections: Provides specialized container datatypes.
    os: Provides a way of using operating system dependent functionality.
    click: A package for creating command line interfaces.
    json: Provides methods for parsing JSON.
    playwright: A library to automate Chromium, Firefox, and WebKit browsers.
    requests: A simple HTTP library for Python.
Functions:
    trail_data_to_geojson(trail_data): Converts trail data to GeoJSON format.
    update_map(map_id, geojson): Updates a map on MapHub with the given GeoJSON data.
    refresh_map_image(map_id): Refreshes the image of a map on MapHub.
    create_maphub_trailmap(trail_title, trail_uri, trail_geojson): Creates a new map on MapHub with the given trail data.
    _browser_context(p, interactive, devtools, scale_factor, browser, browser_args, user_agent, timeout, reduced_motion, bypass_csp, auth_username, auth_password): Sets up a browser context for Playwright.
    skip_or_fail(response, skip, fail): Handles HTTP response errors.
    _evaluate_js(page, javascript): Evaluates JavaScript on a given Playwright page.
    get_wikiloc_data(wikiloc_url): Retrieves trail data from a Wikiloc URL.
    main(trail_url): Main function to execute the script.
Usage:
    Run the script with a Wikiloc trail URL as an argument to export the trail data and update the MapHub map.

"""
from collections import defaultdict
import os

import click
import json
import playwright
import requests

from playwright.sync_api import sync_playwright, Error

MAPHUB_KEY = os.environ['MAPHUB_KEY']
MARKER_DICT = defaultdict(lambda: "location-pin")
MARKER_DICT.update({
    "Intersection": "crossing",
    "Cave": "summit",
    "River": "dam",
    "Tree": "forest",
    "Waterfall": "dam",
    "Museum": "museum",
    "Castle": "museum",
})


def update_geojson(trail_geojson: dict, trail_waypoints: dict)->dict:
    """Updates the GeoJSON data with the waypoint information and changes some aesthetic settings."""
    trail_waypoints_dict = {f"{w['lon']}-{w['lat']}":w for w in trail_waypoints}
    for f in trail_geojson['features']:
        if 'geometry' in f:
            key = f"{f['geometry']['coordinates'][0]}-{f['geometry']['coordinates'][1]}"
            if key in trail_waypoints_dict:
                waypoint_info = trail_waypoints_dict[key]
                
                f['properties'] = {
                    "title": waypoint_info['name'],
                    "description": f'Elevation: {waypoint_info["elevation"]}m',
                    "marker-symbol": MARKER_DICT[waypoint_info.get("pictogramName")],
                }

    print("FOUND PICTOGRAMS:", set(waypoint_info.get("pictogramName") for waypoint_info in trail_waypoints))

    # we color in green the start
    [f for f in trail_geojson['features'] if f.get('geometry',{}).get('type')=='Point'][0]["properties"]["marker-color"] = "#3cc954"
    return trail_geojson

def update_map(map_id, geojson):
    """
    Updates a map on MapHub with the given GeoJSON data.
    Args:
        map_id (str): The ID of the map to update.
        geojson (dict): The GeoJSON data to update the map with.
    Returns:
        None
    Raises:
        Exception: If the map update fails, prints the error message.
    Example:
        geojson_data = {
                        "description": "The world-famous British Museum exhibits the works of man from prehistoric to modern times, from around the world.",
                        "marker-symbol": "museum"
            ]
        update_map("your_map_id", geojson_data)
    """

    url = 'https://maphub.net/api/1/map/update'

    args = {
        'map_id': map_id,
        'geojson': geojson,
        'basemap': 'maphub-earth',
        'description': 'test description',
        'visibility': 'public',
    }

    headers = {'Authorization': 'Token ' + MAPHUB_KEY}

    res = requests.post(url, json=args, headers=headers)
    data = res.json()

    if 'id' not in data:
        print(data['error'])
        return

    print('Map updated')


def refresh_map_image(map_id):
    """
    Refreshes the image of a map on MapHub.
    This function sends a POST request to the MapHub API to refresh the image of a map
    specified by the map_id. It prints the response from the API, which includes the 
    refreshed map image details or an error message if the refresh fails.
    Args:
        map_id (str): The ID of the map to refresh.
    Returns:
        None
    """

    print("REFRESHING MAP IMAGE")
    url = 'https://maphub.net/api/1/map/refresh_image'

    args = {
        'map_id': map_id,
    }

    headers = {'Authorization': 'Token ' + MAPHUB_KEY}

    res = requests.post(url, json=args, headers=headers)
    data = res.json()

    if 'id' not in data:
        print(data['error'])
        return


def create_maphub_trailmap(trail_title, trail_uri, trail_geojson):
    """
    Creates a new trail map on MapHub and updates it with the provided GeoJSON data.
    Args:
        trail_title (str): The title of the trail map.
        trail_uri (str): The URI for the trail map.
        trail_geojson (dict): The GeoJSON data representing the trail.
    Raises:
        requests.exceptions.RequestException: If there is an issue with the HTTP request.
    Returns:
        None
    """

    print("CREATING MAPHUB MAP")
    url = 'https://maphub.net/api/1/map/upload'

    args = {
        'file_type': 'empty',
        'title': trail_title,
        'short_name': trail_uri,
        'visibility': 'public',
    }

    headers = {
        'Authorization': 'Token ' + MAPHUB_KEY,
        'MapHub-API-Arg': json.dumps(args),
    }

    res = requests.post(url, headers=headers)
    data = res.json()
    map_id = data["id"]
    update_map(map_id, trail_geojson)
    refresh_map_image(map_id)
    print(f"MAP CREATED! ID: '{map_id}', TITLE: '{trail_title}', URL: '{data['url']}'")

def _browser_context(
    p,
    interactive=False,
    devtools=False,
    scale_factor=None,
    browser="chromium",
    browser_args=None,
    user_agent=None,
    timeout=None,
    reduced_motion=False,
    bypass_csp=False,
    auth_username=None,
    auth_password=None,
):
    browser_kwargs = dict(
        headless=not interactive, devtools=devtools, args=browser_args
    )
    if browser == "chromium":
        browser_obj = p.chromium.launch(**browser_kwargs)
    elif browser == "firefox":
        browser_obj = p.firefox.launch(**browser_kwargs)
    elif browser == "webkit":
        browser_obj = p.webkit.launch(**browser_kwargs)
    else:
        browser_kwargs["channel"] = browser
        browser_obj = p.chromium.launch(**browser_kwargs)
    context_args = {}
    if scale_factor:
        context_args["device_scale_factor"] = scale_factor
    if reduced_motion:
        context_args["reduced_motion"] = "reduce"
    if user_agent is not None:
        context_args["user_agent"] = user_agent
    if bypass_csp:
        context_args["bypass_csp"] = bypass_csp
    if auth_username and auth_password:
        context_args["http_credentials"] = {
            "username": auth_username,
            "password": auth_password,
        }
    context = browser_obj.new_context(**context_args)
    if timeout:
        context.set_default_timeout(timeout)
    return context, browser_obj


def skip_or_fail(response: playwright.sync_api.Response, skip: bool = False, fail: bool = True) -> None:
    if skip and fail:
        raise click.ClickException("--skip and --fail cannot be used together")
    if str(response.status)[0] in ("4", "5"):
        if skip:
            click.echo(
                "{} error for {}, skipping".format(response.status, response.url),
                err=True,
            )
            # Exit with a 0 status code
            raise SystemExit
        elif fail:
            raise click.ClickException(
                "{} error for {}".format(response.status, response.url)
            )


def _evaluate_js(page: playwright.sync_api.Page, javascript: str) -> dict:
    try:
        return page.evaluate(javascript)
    except Error as error:
        raise click.ClickException(error.message)
    

def get_wikiloc_data(wikiloc_url: str)->tuple:
    print(f"GETTING WIKILOC DATA FROM URL {wikiloc_url}")
    # these are the manually labeled points
    trail_waypoints_js = "mapData.waypoints"
    # these are the points that are automatically generated by the leaflet map
    trail_geojson_js = "var collection = {'type':'FeatureCollection','features':[]}; trailMap.eachLayer(function (layer) {if (typeof(layer.toGeoJSON) === 'function') collection.features.push(layer.toGeoJSON())}); collection"
    title_js = "document.title"
    uri_js = "window.location.pathname"
    
    with sync_playwright() as p:
            context, browser_obj = _browser_context(
                p,
            )
            page = context.new_page()
            response = page.goto(wikiloc_url)
            skip_or_fail(response)
            trail_geojson = _evaluate_js(page, trail_geojson_js)
            trail_waypoints = _evaluate_js(page, trail_waypoints_js)
            trail_title = _evaluate_js(page, title_js).split("|",1)[1].strip()
            trail_uri = _evaluate_js(page, uri_js)
            browser_obj.close()

    return trail_geojson, trail_waypoints, trail_title, trail_uri


@click.command()
@click.argument("trail_url")
def main(trail_url: str):
    trail_geojson, trail_waypoints, trail_title, trail_uri = get_wikiloc_data(trail_url)
    updated_geojson = update_geojson(trail_geojson, trail_waypoints)
    create_maphub_trailmap(trail_title=trail_title, trail_uri=trail_uri, trail_geojson=updated_geojson)


if __name__ == "__main__":
    main()
    
