"""
Balloon telemetry parsing, display, and logging.

__authors__ = ['Quinn Kupec', 'Zachary Burnett']
"""

import logging
import os
import sys
import time
from datetime import datetime

from huginn import connections, tracks
from huginn.writer import write_aprs_packet_tracks

BALLOON_CALLSIGNS = ['W3EAX-8', 'W3EAX-12', 'W3EAX-13', 'W3EAX-14']
INTERVAL_SECONDS = 5
DESKTOP_PATH = os.path.join(os.path.expanduser('~'), 'Desktop')

if __name__ == '__main__':
    if len(sys.argv) > 0 and '-h' not in sys.argv:
        serial_port = sys.argv[1] if len(sys.argv) > 1 else None
        log_filename = sys.argv[2] if len(sys.argv) > 2 else DESKTOP_PATH
        output_filename = sys.argv[3] if len(sys.argv) > 3 else None

        if os.path.isdir(log_filename):
            if not os.path.exists(log_filename):
                os.mkdir(log_filename)
            log_filename = os.path.join(log_filename, f'{datetime.now():%Y%m%dT%H%M%S}_huginn_log.txt')

        if output_filename is not None:
            output_directory = os.path.dirname(output_filename)
            if not os.path.exists(output_directory):
                os.makedirs(output_directory)

        log_format = '[%(asctime)s] %(levelname)-8s: %(message)s'
        logging.basicConfig(filename=log_filename, level=logging.DEBUG, datefmt='%Y-%m-%d %H:%M:%S', format=log_format)
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        console.setFormatter(logging.Formatter(log_format))
        logging.getLogger('').addHandler(console)

        aprs_connections = []
        if serial_port is not None and 'txt' in serial_port:
            try:
                text_file = connections.TextFile(serial_port)
                aprs_connections.append(text_file)
            except Exception as error:
                logging.warning(f'{error.__class__.__name__}: {error}')
        else:
            try:
                radio = connections.Radio(serial_port)
                serial_port = radio.serial_port
                logging.info(f'opened port {serial_port}')
                aprs_connections.append(radio)
            except Exception as error:
                logging.warning(f'{error.__class__.__name__}: {error}')
        try:
            aprs_api = connections.APRS_fi(BALLOON_CALLSIGNS)
            logging.info(f'established connection to API')
            aprs_connections.append(aprs_api)
        except Exception as error:
            logging.warning(f'{error.__class__.__name__}: {error}')

        packet_tracks = {}
        while True:
            logging.debug(f'receiving packets from {len(aprs_connections)} source(s)')

            parsed_packets = []
            for aprs_connection in aprs_connections:
                parsed_packets.extend(aprs_connection.packets)

            logging.debug(f'received {len(parsed_packets)} packets')

            if len(parsed_packets) > 0:
                for parsed_packet in parsed_packets:
                    callsign = parsed_packet['callsign']

                    if callsign in packet_tracks:
                        if parsed_packet not in packet_tracks[callsign]:
                            packet_tracks[callsign].append(parsed_packet)
                        else:
                            logging.debug(f'{callsign:8} - received duplicate packet: {parsed_packet}')
                            continue
                    else:
                        packet_tracks[callsign] = tracks.APRSTrack(callsign, [parsed_packet])
                        logging.debug(f'{callsign:8} - started tracking callsign')

                    logging.info(f'{callsign:8} - received new packet: {parsed_packet}')

                    if 'longitude' in parsed_packet and 'latitude' in parsed_packet:
                        ascent_rate = packet_tracks[callsign].ascent_rate[-1]
                        ground_speed = packet_tracks[callsign].ground_speed[-1]
                        seconds_to_impact = packet_tracks[callsign].seconds_to_impact
                        logging.info(f'{callsign:8} - Ascent rate (m/s): {ascent_rate}')
                        logging.info(f'{callsign:8} - Ground speed (m/s): {ground_speed}')
                        if seconds_to_impact >= 0:
                            logging.info(f'{callsign:8} - Estimated time until landing (s): {seconds_to_impact}')

                if output_filename is not None:
                    write_aprs_packet_tracks(packet_tracks.values(), output_filename)

            time.sleep(INTERVAL_SECONDS)
    else:
        print('usage: huginn serial_port [log_path] [output_file]')
