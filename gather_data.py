# this program gathers sensor data
from DIPPID import SensorUDP
import pandas
import time
from datetime import datetime, UTC
import glob
import re
from pathlib import Path

# use UPD (via WiFi) for communication
PORT = 5700
CAPTURE_TIMEOUT = 10

sensor = SensorUDP(PORT)

name = ''
activity = ''
can_press_button = True

def sanitize(str: string) -> string:
    # Filter any character that is not a letter, number or '_'
    return ''.join([c for c in str.lower().replace(' ', '_') if c.isalnum() or c == '_'])

def chooseName():
    global name
    previous = name

    name = sanitize(input(f'Enter your name{f' ({previous})' if previous else ''}: '))
    # If user entered nothing, but we have a previous name use that
    name = previous if not name and previous else name

    # Repeat until we have a valid name
    while not name: name = sanitize(input(f'Enter your name: '))

def chooseActivity():
    global activity
    previous = activity

    print('Activity List:')
    print('1) running')
    print('2) rowing')
    print('3) lifting')
    print('4) jumpingjacks')
    activity = sanitize(input(f'Enter 1-4 or the activity name{f' ({activity})' if activity else ''}: '))
    # If user entered nothing, but we have a previous activity use that
    activity = previous if not activity and previous else activity

    # Repeat until we have a valid name
    while not activity: activity = sanitize(input(f'Enter 1-4 or the activity name: '))

    match activity:
        case '1': activity = 'running'
        case '2': activity = 'rowing'
        case '3': activity = 'lifting'
        case '4': activity = 'jumpingjacks'

def findNextNumber():
    num = []
    files = glob.glob(f'./data/{name}-{activity}-*.csv')
    for file in files:
        match = re.search(rf'/{re.escape(name)}-{re.escape(activity)}-(\d+)\.csv$', file)
        if match:
            num.append(int(match.group(1)))

    if num:
        print(f'Found {len(num)} previous recording/s for {activity}')
        return max(num) + 1

    return 1

def captureData() -> [{ datetime: datetime, acc_x: float, acc_y: float, acc_z: float, gyro_x: float, gyro_y: float, gyro_z: float }]:
    data = []

    print(f'Starting in: 3', end='\r')
    time.sleep(1)
    print(f'Starting in: 2', end='\r')
    time.sleep(1)
    print(f'Starting in: 1', end='\r')
    time.sleep(1)

    start = time.time()
    while time.time() - start < CAPTURE_TIMEOUT: # Record until timeout is reached
        acc = sensor.get_value('accelerometer')
        gyro = sensor.get_value('gyroscope')

        data.append({
            'datetime': datetime.now(UTC),
            'acc_x': acc['x'], 'acc_y': acc['y'], 'acc_z': acc['z'],
            'gyro_x': gyro['x'], 'gyro_y': gyro['y'], 'gyro_z': gyro['z']
        })

        time_passed = int(time.time() - start)
        print(f'Still Recording for: {str(10 - time_passed)}s ', end='\r')

        time.sleep(0.001) # Sample at ~1000Hz aka. 1/1000 = 0.001

    print(f'Still Recording for: done')

    return data

def saveCSV(data: [{ datetime: datetime, acc_x: float, acc_y: float, acc_z: float, gyro_x: float, gyro_y: float, gyro_z: float }], filename: string) -> None:
    # Create the data frame
    data_frame = pandas.DataFrame(data)

    # Set the timestamp as the index
    data_frame = data_frame.set_index('datetime')

    # Resample to 100 Hz (aka 10ms intervals)
    data_frame = data_frame.resample('10ms').mean().interpolate()

    # Only keep exactly 10 seconds
    data_frame = data_frame.head(1000)

    # Add timestamp field (convert from nano- to milli-seconds)
    data_frame.insert(0, 'timestamp', data_frame.index.astype('int64') // 1_000_000)

    # Add the id field
    data_frame.insert(0, 'id', range(len(data_frame)))

    # Save the data frame as csv and keep the index (timestamp)
    data_frame.to_csv(filename, index=False)

def handleButton(btn: 0 | 1) -> None:
    global can_press_button

    # Safeguard against button release or early button_press
    if btn != 1 or not can_press_button: return

    can_press_button = False
    captured_data = captureData()

    # Repeat until y or n
    while (save_data := input('Save data (y/n): ')) not in ['y', 'n']: pass

    if save_data == 'y':
        # Ensure the output directory exists
        Path('data').mkdir(exist_ok = True)

        saveCSV(captured_data, f'./data/{name}-{activity}-{findNextNumber()}.csv')

    while (continue_capture := input('Capture more data (y/n): ')) not in ['y', 'n']: pass

    if continue_capture == 'n':

        # Stop worker thread
        # Workaround to avoid using a worker queue
        # Since calling join on the same thread raises an exception
        sensor._connection_thread = None
        sensor.disconnect()
        return

    chooseName()
    chooseActivity()

    print('Please press button 1 on your phone to start recording')
    print('Waiting for button input ...')
    can_press_button = True

chooseName()
chooseActivity()

print('Please press button 1 on your phone to start recording')
print('Waiting for button input ...')
sensor.register_callback('button_1', handleButton)
