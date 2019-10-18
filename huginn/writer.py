import os

import fastkml.geometry
import geojson
from fastkml import kml

from huginn.tracks import APRSTrack

KML_STANDARD = '{http://www.opengis.net/kml/2.2}'


def write_aprs_packet_tracks(packet_tracks: [APRSTrack], output_filename: str):
    extension = os.path.splitext(output_filename)[1]
    if extension == '.kml':
        output_kml = kml.KML()
        document = kml.Document(KML_STANDARD, '1', 'root document', 'root document, containing geometries')
        output_kml.append(document)

        for packet_track_index, packet_track in enumerate(packet_tracks):
            for packet_index, packet in enumerate(packet_track):
                placemark = kml.Placemark(KML_STANDARD, f'1 {packet_track_index} {packet_index}',
                                          f'{packet_track.callsign} {packet.time:%Y%m%d%H%M%S}',
                                          f'altitude={packet.coordinates[-1]} ascent_rate={packet_track.ascent_rate[packet_index]} ground_speed={packet_track.ground_speed[packet_index]}')
                placemark.geometry = {'type': 'Point', 'coordinates': fastkml.geometry.Point(packet.coordinates)}
                document.append(placemark)

            placemark = kml.Placemark(KML_STANDARD, f'1 {packet_track_index}', packet_track.callsign,
                                      f'altitude={packet_track.coordinates[-1, -1]} ascent_rate={packet_track.ascent_rate[-1]} ground_speed={packet_track.ground_speed[-1]} seconds_to_impact={packet_track.seconds_to_impact}')
            placemark.geometry = {'type': 'LineString',
                                  'coordinates': fastkml.geometry.LineString(packet_track.coordinates.tolist())}
            document.append(placemark)

        with open(output_filename, 'w') as output_file:
            output_file.write(output_kml.to_string())
    elif extension == '.geojson':
        features = []
        for packet_track in packet_tracks:
            features.extend(geojson.Feature(geometry=geojson.Point(packet.coordinates),
                                            properties={'time': f'{packet.time:%Y%m%d%H%M%S}',
                                                        'callsign': packet_track.callsign,
                                                        'altitude': packet_track.coordinates[-1, -1],
                                                        'ascent_rate': packet_track.ascent_rate[packet_index],
                                                        'ground_speed': packet_track.ground_speed[packet_index]})
                            for packet_index, packet in enumerate(packet_track))

            features.append(
                geojson.Feature(geometry=geojson.LineString([packet.coordinates for packet in packet_track.packets]),
                                properties={'time': f'{packet_track.packets[-1].time:%Y%m%d%H%M%S}',
                                            'callsign': packet_track.callsign,
                                            'altitude': packet_track.coordinates[-1, -1],
                                            'ascent_rate': packet_track.ascent_rate[-1],
                                            'ground_speed': packet_track.ground_speed[-1],
                                            'seconds_to_impact': packet_track.seconds_to_impact}))

        features = geojson.FeatureCollection(features)

        with open(output_filename, 'w') as output_file:
            geojson.dump(features, output_file)
    else:
        raise NotImplementedError(f'saving to file type "{extension}" has not been implemented')