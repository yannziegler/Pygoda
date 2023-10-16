# coding: utf-8

import sys, re, time

import urllib.request
from urllib.parse import quote

import strictyaml as yaml

# Argument:
# /path/to/country.yaml [(Wikidata country IDs)* | (NAME 3166-1 alpha-3 codes)*]

def print_usage():
    print('Usage: wikidata2poly.py /path/to/countries.yaml [ID1 [ID2 ID3...] [+]]\n'
          'ID = Wikidata ID (e.g. Q123456) or entity name in countries.yaml\n'
          '+ = all countries in countries.yaml following the last listed ID.')

narg = len(sys.argv)

if narg < 2:
    print_usage()
    raise TypeError('Please provide an argument.')

name_list = []
if sys.argv[1][-5:] == '.yaml':
    with open(sys.argv[1], 'r') as country_file:
        yaml_content = yaml.load(country_file.read()).data
    ncountries = len(yaml_content)
    countries_names = [None]*ncountries
    countries_wiki = [None]*ncountries
    i = 0
    for name, fields in yaml_content.items():
        countries_names[i] = name
        if 'wikidata' in fields and fields['wikidata']:
            if fields['wikidata'][0] != '~':
                countries_wiki[i] = fields['wikidata']
            else:
                countries_wiki[i] = '~'
        i += 1

    if narg > 2:
        # Select the requested countries
        if sys.argv[2] == '+':
            raise ValueError("'+' must be used after a country name.")

        for arg in sys.argv[2:]:
            # if re.match('^[A-Z]{2}$', arg):
            #     raise ValueError('NAME 3166 alpha-2 not recognized yet.')
            # elif re.match('^[A-Z]{3}$', arg):
            name_list.append(arg)

        if sys.argv[-1] == '+':
            name_list.pop(-1) # last one was '+', not a country name
            if name_list[-1] in countries_names:
                # Add all the countries after the last listed
                if (i := countries_names.index(name_list[-1])) < ncountries - 1:
                    name_list += countries_names[i+1:]
                else:
                    print("Info: %s was the last entry in %s, ignoring '+'" % \
                          (name_list[-1], sys.argv[1]))
            else:
                print('Warning: %s is not a valid entry in %s' % \
                      (name_list[-1], sys.argv[1]))

        wikidata_id_list = []
        missing = []
        for name in name_list:
            try:
                i = countries_names.index(name)
                if countries_wiki[i]:
                    if countries_wiki[i] != '~':
                        wikidata_id_list.append(countries_wiki[i])
                    else:
                        print('Info: ignoring %s due to flagged Wikidata ID in %s' \
                              % (name, sys.argv[1]))
                        name_list[name_list.index(name)] = None
                else:
                    print('Warning: %s has no Wikidata ID in %s' % \
                          (name, sys.argv[1]))
                    name_list[name_list.index(name)] = None
            except ValueError:
                    print('Warning: %s is not a valid entry in %s' % \
                          (name, sys.argv[1]))
                    name_list[name_list.index(name)] = None
        name_list = [name for name in name_list if name]

    else:
        # Select all countries
        name_list = [name for name, wikidata in\
                     zip(countries_names, countries_wiki)
                     if wikidata]
        wikidata_id_list = [wikidata for wikidata in countries_wiki
                            if wikidata]

    assert len(name_list) == len(wikidata_id_list)
else:
    print_usage()
    exit(1)

    # TODO: provide only Wikidata ID and get OSM ID and poly in return
    # wikidata_id_list = []
    # while re.match('^Q[0-9]+', sys.argv[-1]):
    #     wikidata_id_list.append(sys.argv[-1])
    #     sys.argv.pop()
    # wikidata_id_list.reverse() # not necessary but restore the original order

    # if len(sys.argv) > 2:
    #     print_usage()
    #     raise ValueError('Argument \'%s\' not recognized.' % sys.argv[-1])

nid = len(wikidata_id_list)

if not nid:
    print('Nothing to do.')
    exit()

if not name_list:
    # We have used Wikidata ID directly, we don't know the corresponding NAME codes
    name_list = [None]*nid

# Overpass API requests to get OSM ID from Wikidata ID
print('%d OSM ID will be recovered from OSM Overpass API...' % nid)
# overpass_url = 'https://overpass-api.de/api/interpreter?data='
overpass_url = 'https://lz4.overpass-api.de/api/interpreter?data='
overpass_request_skel = '[out:csv(::id)];relation[wikidata=%s][admin_level~"[0-max]"];out ids;'
overpass_request_sub_skel = '[out:csv(::id)];relation[wikidata=%s];out ids;'
# You can check those requests on https://overpass-turbo.eu/

# Note: alternatively, we could use Wikidata API: https://query.wikidata.org
# BUT (1) OSM seems more reliable with Wikidata ID systematically
# AND (2) there is no guarantee that the OSM ID be up to date on Wikidata, see:
# https://www.wikidata.org/wiki/Wikidata:OpenStreetMap#Linking_from_Wikidata_to_OSM

# For example, using NAME code directly:
# SELECT ?OSMIDLabel WHERE {
#   ?country wdt:P298 "%s"; # NAME 3166 alpha-3 code
#            wdt:P402 ?OSMID. # OSM relation ID
# }
# ...or getting OSM ID from Wikidata ID as we do with Overpass:
# SELECT ?OSMID WHERE {
#   wd:%s wdt:P402 ?OSMID .
# }
# Play with this example there: 'https://query.wikidata.org/#SELECT-20-3FOSMID-20WHERE-20-7B-0A-20-20wd-3A%s-20wdt-3AP402-20-3FOSMID-20.-0A-7D'
# wikidata_query_skel = 'https://query.wikidata.org/sparql?query=SELECT-20-3FOSMID-20WHERE-20-7B-0A-20-20wd-3A%s-20wdt-3AP402-20-3FOSMID-20.-0A-7D'
# wikidata = 'Q212429'
# wikidata_query = (wikidata_query_skel % wikidata).replace('-', '%')
# print(wikidata_query)
wikidata_url = 'https://query.wikidata.org/sparql?query='
wikidata_query_skel = 'SELECT-20-3FOSMID-20WHERE-20-7B-0A-20-20wd-3A%s-20wdt-3AP402-20-3FOSMID-20.-0A-7D'

# OSM polygons service requests to get WKT polygons from OSM ID
print('Poly sets will be recovered from OSM poly service...')
osmpoly_url = 'http://polygons.openstreetmap.fr/get_wkt.py?id=%s&params=0'

# Output files
filename_one_skel = '../data/WKT/%s.wkt'
filename_two_skel = '../data/WKT/%s_%s.wkt'

osm_id_list = [None]*nid
poly_list = [None]*nid
http_errors, poly_errors = [], []
for i, name, wikidata in zip(range(nid), name_list, wikidata_id_list):
    if name:
        print('Getting OSM ID for %s (%s)...' % (wikidata, name), end='')
    else:
        print('Getting OSM ID for %s...' % wikidata, end='')

    time.sleep(5) # to avoid overloading the server

    # Get the OSM ID from OSM Overpass API
    overpass_request = overpass_request_skel % wikidata
    overpass_request = overpass_url + quote(overpass_request)
    overpass_contents = b''
    try:
        overpass_contents = []
        n = 6 # admin level for research
        n_id = -1 # number of IDs found
        use_relation = True # look for a relation by default
        while n_id != 1:
            overpass_contents = urllib.request.\
                                urlopen(overpass_request.\
                                        replace('max', str(n))).read()
            overpass_contents = overpass_contents.decode('utf-8',
                                                         'backslashreplace')
            overpass_contents = overpass_contents.split('\n')
            # ID(s) start on 2nd line and last line is empty
            overpass_contents = overpass_contents[1:-1]

            if n - 1 < 1 or n + 1 > 6:
                break

            n_id = len(overpass_contents)
            if n_id > 1:
                print('\n [Info] several OSM ID found.')
                print(' Looking for admin levels smaller than %d... ' % n, end='')
                n -= 1
            elif n_id == 0:
                print('\n [Info] no OSM ID found.')
                if use_relation:
                    use_relation = False # use a 'way' next time
                    print(' Trying with a way instead of a relation...', end='')
                else:
                    use_relation = True # use a 'relation' next time
                    print(' Looking for admin levels larger than %d... ' % n, end='')
                    n += 1

            if use_relation:
                # Look for a relation (for larger features)
                overpass_request = overpass_request.replace('way', 'relation')
            else:
                # Look for a way instead of a relation (for smaller features)
                overpass_request = overpass_request.replace('relation', 'way')

            time.sleep(2) # to avoid overloading the server

        if len(overpass_contents) == 1:
            overpass_contents = overpass_contents[0]
        else:
            print('\n [Info] failed to get a unique OSM ID from overpass API')
            print('        ...last attempt with a wikidata query')
            # Try again with a wikidata query
            wikidata_query = wikidata_query_skel % wikidata
            wikidata_query = wikidata_url + wikidata_query.replace('-', '%')
            wikidata_contents = urllib.request.urlopen(wikidata_query).read()
            wikidata_contents = wikidata_contents.decode('utf-8',
                                                         'backslashreplace')
            wikidata_contents = re.sub("[ \t\r\n]", "", wikidata_contents)
            match = re.findall(r"<bindingname='OSMID'><literal>([0-9]+)</literal>",
                                wikidata_contents)
            if match:
                overpass_contents = match[0]
            else:
                print(' [Warning] failed to get an OSM ID')
                print(' Check overpass request:', overpass_request)
                print(' Check wikidata query:', wikidata_query)
                continue

        #if not re.match('[0-9]+', overpass_contents):
        #    # Look for a way instead of a relation (for smaller features)
        #    overpass_request = overpass_request.replace('relation', 'way')
        #    overpass_contents = urllib.request.urlopen(overpass_request).read()
        #    overpass_contents = overpass_contents.decode('utf-8',
        #                                                 'backslashreplace')
        #    overpass_contents = overpass_contents.split('\n')[1]

        # Extract OSM ID from the result
        if matched_id := re.search('[0-9]+', overpass_contents):
            osm_id = matched_id.group(0)
            osm_id_list[i] = osm_id
            print(' id:%s' % osm_id, end='')
        else:
            print('\n [Warning] no OSM ID retrieved')
            print(' Check overpass request:', overpass_request)
            print(' Check wikidata query:', wikidata_query)
            continue
    except urllib.error.HTTPError:
        print('\n [HTTP Error] skipping')
        http_errors.append((name, wikidata))
        continue

    # Get the poly in WKT format from OSM poly service
    print(' > getting poly...', end='')

    osmpoly_request = osmpoly_url % osm_id
    osmpoly_contents = b''
    try:
        osmpoly_contents = urllib.request.urlopen(osmpoly_request).read()
    except urllib.error.HTTPError as e:
        reply = e.read().decode('utf-8', 'backslashreplace')
        if 'olygon' in reply:
            # 'Polygon wasn't properly generated'
            poly_errors.append((name, osm_id))
            print('\n [Polygon error] server replied:')
        else:
            # Other server error
            http_errors.append((name, wikidata))
            if reply:
                print('\n [OSM HTTP Error] server replied:')
            else:
                print('\n [OSM HTTP Error] skipping')
        if reply:
            if reply[-1] == '\n':
                reply = reply[:-1]
            print(' %s%s' % (reply[:70], ' [...]' if len(reply) > 70 else ''))
        print(' Check:', osmpoly_request)
        continue

    if osmpoly_contents[0:4] != b'SRID':
        print('\n [Polygon error] skipping')
        print('\n Check request:', osmpoly_request)
        poly_errors.append((name, osm_id))
        continue

    poly_list[i] = osmpoly_contents

    # Write the poly to the disk
    if name:
        name = re.sub("[' ]", "+", name)
        name = re.sub("[)(]", "", name)
        filename = filename_two_skel % (wikidata, name)
    else:
        filename = filename_one_skel % wikidata

    with open(filename, 'wb') as poly_file:
        poly_file.write(poly_list[i])

    print('done')

print('DONE')

if None in osm_id_list:
    print('\nSummary of OSM ID errors (check and/or try again):')
    for i, osm_id in enumerate(osm_id_list):
        if not osm_id:
            print(name_list[i], wikidata_id_list[i])

if http_errors:
    print('\nSummary of HTTP errors (try again later):')
    for error_name, error_wiki in http_errors:
        print(error_name, error_wiki)

if poly_errors:
    print('\nSummary of Poly errors:')
    print('(*) Check these ID manually on http://polygons.openstreetmap.fr')
    for error_name, error_osm in poly_errors:
        print(error_name, 'id:%s' % error_osm)

# Keep the retrieved OSM ID in a file
# Note that they might be outdated in the future:
# https://www.wikidata.org/wiki/Wikidata:OpenStreetMap#Linking_from_Wikidata_to_OSM
# To visualise OSM relations in OpenStreetMap, go here:
# https://www.openstreetmap.org/?relation=%s % osm_id
wikidata_osm_ids = ''
for wikidata, osm_id in zip(wikidata_id_list, osm_id_list):
    wikidata_osm_ids += '%s %s\n' % (wikidata, osm_id if osm_id else 'None')
with open('../data/wikidata_osm_ids.txt', 'w+') as osm_id_file:
    osm_id_file.write(wikidata_osm_ids)
