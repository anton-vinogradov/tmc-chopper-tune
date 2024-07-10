import csv
import importlib
import os
import sys
from datetime import datetime

import numpy as np
import pandas
import plotly.graph_objects as go
import plotly.io as pio
from tqdm import tqdm

RESULTS_FOLDER = os.path.expanduser('~/printer_data/config/adxl_results/chopper_magnitude')
DATA_FOLDER = '/tmp'
CUTOFF_RANGE = 5
WINDOW_T_SEC = 0.5


def setup_klipper_import():
    global shaper_calibrate
    sys.path.append(os.path.join('~/klipper', 'klippy'))
    shaper_calibrate = importlib.import_module('.shaper_calibrate', 'extras')


def clean():
    os.system('rm -f /tmp/*.csv')


def process():
    setup_klipper_import()
    res = []
    for file_name in os.listdir(DATA_FOLDER):
        if file_name.endswith('.csv'):
            file_path = os.path.join(DATA_FOLDER, file_name)
            with open(file_path, 'r') as file:
                data = np.array([[float(row["#time"]),
                                  float(row["accel_x"]),
                                  float(row["accel_y"]),
                                  float(row["accel_z"])] for row in csv.DictReader(file)])
                ln = len(data)
                data = data[ln // 2:-ln // 4]

                n = data.shape[0]
                t = data[-1, 0] - data[0, 0]
                freq = n / t
                # Round up to the nearest power of 2 for faster FFT
                m = 1 << int(freq * WINDOW_T_SEC - 1).bit_length()

                # Calculate PSD (power spectral density) of vibrations per
                # frequency bins (the same bins for X, Y, and Z)
                px = shaper_calibrate._psd(data[:, 1], freq, m)
                py = shaper_calibrate._psd(data[:, 2], freq, m)
                pz = shaper_calibrate._psd(data[:, 3], freq, m)

                res.append([file_name, px.mean(), py.mean(), pz.mean()])

    df = pandas.DataFrame(res)
    df.to_csv(RESULTS_FOLDER + "/res.csv")


def check_export_path(path):
    if not os.path.exists(path):
        try:
            os.makedirs(path)
        except OSError as e:
            print(f'Error generate path {path}: {e}')


def parse_arguments():
    args = sys.argv[1:]
    parsed_args = {}
    for arg in args:
        name, value = arg.split('=')
        parsed_args[name] = int(value) if value.isdigit() else value
    return parsed_args


def calculate_static_measures(file_path):
    with open(file_path, 'r') as file:
        static = np.array([[float(row["accel_x"]),
                            float(row["accel_y"]),
                            float(row["accel_z"])] for row in csv.DictReader(file)])
        return static.mean(axis=0)


def main():
    print('Magnitude graphs generation...')
    args = parse_arguments()
    accelerometer = args.get('accel_chip')
    driver = args.get('driver')
    current_date = datetime.now().strftime('%Y%m%d_%H%M%S')
    csv_files, target_file = [], ''
    for f in os.listdir(DATA_FOLDER):
        if f.endswith('.csv'):
            if f.endswith('-stand_still.csv'):
                target_file = f
            else:
                csv_files.append(f)
    csv_files = sorted(csv_files)
    parameters_list = []

    for tbl in range(args.get('tbl_min'), args.get('tbl_max') + 1):
        for toff in range(args.get('toff_min'), args.get('toff_max') + 1):
            for hstrt in range(args.get('hstrt_min'), args.get('hstrt_max') + 1):
                for hend in range(args.get('hend_min'), args.get('hend_max') + 1):
                    for speed in range(args.get('min_speed'), args.get('max_speed') + 1):
                        parameters_list.append(f'tbl={tbl}_toff={toff}_hstrt={hstrt}_hend={hend}_speed={speed}')

    # Check input count csvs
    if len(csv_files) != len(parameters_list):
        print(f'Warning!!! The number of CSV files ({len(csv_files)}) does not match the expected number '
              f'of combinations based on the provided parameters ({len(parameters_list)})')
        print('Please check your input and try again')
        sys.exit(1)

    # Binding magnitude on registers
    results = []
    static = calculate_static_measures(os.path.join(DATA_FOLDER, target_file))
    for csv_file, parameters in tqdm(zip(csv_files, parameters_list), desc='Processing CSV files',
                                     total=len(csv_files)):
        file_path = os.path.join(DATA_FOLDER, csv_file)
        with open(file_path, 'r') as file:
            data = np.array([[float(row["accel_x"]),
                              float(row["accel_y"]),
                              float(row["accel_z"])] for row in csv.DictReader(file)]) - static

        trim_size = len(data) // CUTOFF_RANGE
        data = data[trim_size:-trim_size]
        md_magnitude = np.median([np.linalg.norm(row) for row in data])

        toff = int(parameters.split('_')[1].split('=')[1])
        results.append({'file_name': csv_file, 'median magnitude': md_magnitude,
                        'parameters': parameters, 'color': toff})

    # Graphs generation
    colors = ['', '#2F4F4F', '#12B57F', '#9DB512', '#DF8816', '#1297B5', '#5912B5', '#B51284', '#127D0C']
    params = [results, sorted(results, key=lambda x: x['median magnitude'])]
    names = ['', 'sorted_']
    for param, name in zip(params, names):
        fig = go.Figure()
        for entry in param:
            fig.add_trace(go.Bar(x=[entry['median magnitude']], y=[entry['parameters']],
                                 marker_color=colors[entry['color'] if entry['color'] <= 8 else entry['color'] - 8],
                                 orientation='h', showlegend=False))
        fig.update_layout(title='Median Magnitude vs Parameters', xaxis_title='Median Magnitude',
                          yaxis_title='Parameters', coloraxis_showscale=True)
        plot_html_path = os.path.join(RESULTS_FOLDER,
                                      f'{name}interactive_plot_{accelerometer}_tmc{driver}_{current_date}.html')
        pio.write_html(fig, plot_html_path, auto_open=False)

    # Export Info
    try:
        print(
            f'Access to interactive plot at: {"/".join(plot_html_path.split("/")[:-1] + [plot_html_path.split(names[1])[1]])}')
    except IndexError:
        print(f'Access to interactive plot at: {plot_html_path}')


if __name__ == '__main__':
    if sys.argv[1] == 'clean':
        clean()
    elif sys.argv[1] == 'process':
        process()
    else:
        check_export_path(RESULTS_FOLDER)
        main()
