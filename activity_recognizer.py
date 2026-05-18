# this program recognizes activities

import re
import pandas
import numpy as np
from time import sleep
from pathlib import Path
from datetime import datetime, UTC

from DIPPID import SensorUDP
from threading import Thread

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

SAMPLE_RATE = 100
TRAIN_DATASET_PATH = './data'
SENSOR_COLUMNS = set(['acc_x', 'acc_y', 'acc_z', 'gyro_x', 'gyro_y', 'gyro_z'])
EXPECTED = set(['id', 'timestamp']) | SENSOR_COLUMNS
PORT = 5700

def load_data(path):
    match = re.search(rf'-(\w+)-\d+\.csv$', path)
    activity = match.group(1).lower() if match else None

    match activity:
        case 'jumpingjacks' | 'lifting' | 'rowing' | 'running': pass
        # Fix incorrect spelling
        case 'jumpingjack': activity = 'jumpingjacks'
        case _: return None, None

    df = pandas.read_csv(path)

    # Required row is missing
    if bool(EXPECTED - set(df.columns)):
        return None, None

    for column in SENSOR_COLUMNS:
        try:
            df[column].astype(float)

            # If there is a non-changing column
            # the sensor data is mostly likely missing/wrong
            if df[column].nunique() == 1:
                return None, None
        except Exception as e:
            # If the sensor data is not a float
            # it is ill-formatted
            return None, None

    if df['timestamp'].dtype == 'float64':
        df['timestamp'] = (df['timestamp'] * 1000).round().astype(int)

    if not df['timestamp'].dtype == 'int64':
        return None, None

    # If the timestamp is in seconds "estimate" the timestamp using id
    if df['timestamp'].diff().abs().dropna().isin([0, 1]).all():
        df['timestamp'] = df['id'].astype(int) * 10

    # If the timestamp is in milliseconds and sampled less than ~83.333hz
    # Technically we could choose a cut off by 100hz, but this filters
    # some datasets, that might still be "useful".
    if (df['timestamp'].diff().abs().dropna() > 12).any():
        return None, None

    df.index = pandas.to_datetime(df['timestamp'], unit='ms')

    # Sanity "resample" to make sure it is 100hz
    return df.resample('10ms').mean(), activity

def slide_window(df):
    size = int(2 * SAMPLE_RATE) # 2 second window size
    step = int(1 * SAMPLE_RATE) # 1 second overlap

    # Only extract exactly 200 samples, with 100 sample overlap.
    # Last few samples might be dropped, if they do not fit.
    for i in range(0, len(df) - size + 1, step):
        yield df.iloc[i:i + size]

def compute_features(window):
    features = {}

    for column in SENSOR_COLUMNS:
        data = window[column]

        features[f'{column}_mean'] = data.mean()
        features[f'{column}_median'] = data.median()
        features[f'{column}_std'] = data.std()
        features[f'{column}_var'] = data.var()
        features[f'{column}_max'] = data.max()
        features[f'{column}_min'] = data.min()

        # Frequency-Domain
        data_fft = np.abs(np.fft.rfft(data.values))
        features[f'{column}_mean'] = np.mean(data_fft)
        features[f'{column}_median'] = np.median(data_fft)
        features[f'{column}_std'] = np.std(data_fft)
        features[f'{column}_fft_engery'] = np.sum(data_fft ** 2)
        features[f'{column}_fft_peak'] = np.argmax(data_fft)

    return features

def collect_training_data():
    training_data = []
    classifier = []

    skipped = {}

    for path in Path(TRAIN_DATASET_PATH).rglob('*.csv'):
        data, activity = load_data(str(path))

        if data is None or activity is None:
            match = re.search(rf'^([^-]+)-(\w+)-\d+\.csv$', path.name)
            name = match.group(1) if match else '*'
            activity = match.group(2) if match else path.name
            skipped.setdefault(name, set()).add(activity)
            continue

        features = [compute_features(data) for window in slide_window(data)]
        training_data.extend(features)
        classifier.extend([activity] * len(features))

    if skipped:
        print('Some datasets were skipped...')

        for name in sorted(skipped):
            print(f'{name}:\t{", ".join(skipped[name])}')

    return pandas.DataFrame(training_data).to_numpy(), classifier

def train():
    training_data, classifier = collect_training_data()

    X_train, X_test, y_train, y_test = train_test_split(training_data, classifier, test_size=0.2)

    model = RandomForestClassifier(n_estimators=200)
    model.fit(X_train, y_train)

    print('Accuracy: ', model.score(X_test, y_test))

    return model

class Recognizer:

    def __init__(self):
        self.model = train()
        self.buffer = []
        self.prediction = None
        self.proba = [0.0]
        self.cooloff = 0

        self.sensor = SensorUDP(PORT)
        self._thread = Thread(target=self._refresh)
        self._thread.start()

    # Technically this does not run at 100hz
    # but it should be fine
    def _refresh(self):
        while self.sensor:
            acc = self.sensor.get_value('accelerometer')
            gyro = self.sensor.get_value('gyroscope')

            # In case the key is not yet set
            if not acc or not gyro:
                continue

            # Add data to buffer/window
            # and keep its length at 2s
            self.buffer.append({
                'datetime': datetime.now(UTC),
                'acc_x': acc['x'], 'acc_y': acc['y'], 'acc_z': acc['z'],
                'gyro_x': gyro['x'], 'gyro_y': gyro['y'], 'gyro_z': gyro['z']
            })
            # Only keep 2000 samples
            del self.buffer[:-(20 * SAMPLE_RATE)]

            sleep(0.001)

    def predict(self):
        if len(self.buffer) < 20 * SAMPLE_RATE:
            return None

        df = pandas.DataFrame(self.buffer)
        df = df.set_index('datetime')
        df = df.resample('10ms').mean().head(200)

        _features = [compute_features(df)]
        features = pandas.DataFrame(_features).to_numpy()

        prediction = self.model.predict_proba(features)[0]
        proba = prediction.max()
        i = prediction.argmax()

        if self.prediction is not None:
            self.proba.append(prediction[self.prediction])
            del self.proba[:-5]

        # Simple cooloff to prevent random switching
        if i != self.prediction and np.mean(self.proba) < 0.4:
            self.prediction = i if proba > 0.5 else None
            self.proba = [proba] if proba > 0.5 else [0.0]

        return self.model.classes_[self.prediction] if self.prediction else None

    def stop(self):
        self.sensor.disconnect()
        self.sensor = None
        self._thread.join()
