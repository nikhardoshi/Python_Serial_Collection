import polars as pl
import plotly.graph_objects as go
from plotly_resampler import FigureResampler
import numpy as np
from plotly.subplots import make_subplots
import glob
from plotly_resampler.aggregation import MinMaxLTTB

def plots(logpath):
    path = '\\'.join(logpath.split('\\')[:-1])
    file_path = path + '\\*.csv'
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
        default_n_shown_samples=2000,
        default_downsampler=MinMaxLTTB(parallel=True))
    
    order_cols = ['Timestamp', 'CV1', 'CVR', 'CVY', 'CVB', 'VRY', 'SMG', 'ACC', 'GYR', 'PRS', 'WTF', 'SoundMain']

    i = 0
    for key in order_cols:
        if key in data.keys():
            i += 1
            index = np.arange(0, data[key].shape[0], 1)
            fig.add_trace(go.Scatter(name=key), hf_x=index, hf_y=np.array(data[key]), row=i, col=1)

    print(params)
    params['title_text'] = "Data plots"
    params['height'] = len(data.keys()) * 600
    fig.update_layout(**params)
 
    fig.show_dash()