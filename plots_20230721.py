import polars as pl
import plotly.graph_objects as go
from plotly_resampler import FigureResampler
import numpy as np
from plotly.subplots import make_subplots
import glob
import os
from plotly_resampler.aggregation import MinMaxLTTB
from win32api import GetSystemMetrics
##pip install kaleido==0.1.0post1

def plots(logpath):
    folder_path = '\\'.join(logpath.split('\\')[:-1])
    file_path = folder_path + '\\*.csv'
    Timestamp_plotted = False
    data = {}
    params = {}
    for path in glob.glob(file_path):
        file_type = path.split('\\')[-1].split('_')[0].split()[0]
        df = pl.read_csv(path)
        if path.split('\\')[-1].split('.')[0].split()[0] == 'SoundMain':
            data[file_type] = np.array(df[df.columns[0]])
        else:
            data[file_type] = np.array(df[df.columns[1]])
        if Timestamp_plotted == False:
            try:
                data['Timestamp'] = np.array(df['Timestamp'])
            except:
                pass

    # print(data.keys())
    fig = FigureResampler(
        make_subplots(rows=len(data.keys()), cols=1),
        default_downsampler=MinMaxLTTB(parallel=True))
    
    order_cols = ['Timestamp', 'CV1', 'CTR', 'CTY', 'CTB', 'VRY', 'SMG', 'AC1', 'AC2', 'GYR', 'PRS', 'WTF', 'SoundMain']

    i = 0
    for key in order_cols:
        if key in data.keys():
            i += 1
            index = np.arange(0, data[key].shape[0], 1)
            fig.add_trace(go.Scatter(name=key), hf_x=index, hf_y=np.array(data[key]), row=i, col=1)
            params[f'yaxis{i}'] = {'title' : key}

    print(params)
    params['title_text'] = "Data plots " + folder_path
    params['height'] = len(data.keys()) * 600
    params['width'] = GetSystemMetrics[0]
    fig.update_layout(**params)
    plot_path = os.path.join(folder_path, 'sensor_plots.pdf')
    print(plot_path)
    fig.write_image(plot_path, format='pdf', engine = 'kaleido')
    fig.show_dash()