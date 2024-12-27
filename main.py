import numpy as np
import pandas as pd
import serial
import matplotlib.pyplot as plt
from scipy.signal import savgol_filter


def convert_bits_to_voltage(v_range, n_bits, value_in, v_lim):
    """Converts ADC bits to voltage."""
    v_out = value_in * v_range / (2 ** n_bits)
    return min(v_out, v_lim)  # Ensure v_out does not exceed v_lim


def clean_data(ser):
    """Reads and cleans data from the serial port."""
    while True:
        if ser.read(1) == b'*' and ser.read(1) == b'*':
            data = ser.read(4)
            if len(data) == 4:
                return [int.from_bytes(data[i:i + 1], byteorder='big') for i in range(4)]


def slice_useful_data(array, threshold_high=None, threshold_low=None):
    """
    Identifica e suddivide i dati utili in base a soglie.

    Parametri:
        array (np.array): Array dei dati.
        threshold_high (float, opzionale): Soglia superiore per considerare i dati "alti".
        threshold_low (float, opzionale): Soglia inferiore per considerare i dati "bassi".

    Restituisce:
        array (np.array): Array originale.
        start (int): Inizio del primo intervallo utile.
        end (int): Fine del primo intervallo utile.
    """
    # Se le soglie non sono specificate, calcolale automaticamente
    if threshold_high is None or threshold_low is None:
        mean = np.mean(array)
        std = np.std(array)
        threshold_high = mean + 1.5 * std  # Soglia alta (media + 1.5 deviazioni standard)
        threshold_low = mean - 1.5 * std  # Soglia bassa (media - 1.5 deviazioni standard)

    print(f"Soglie calcolate: threshold_high={threshold_high:.3f}, threshold_low={threshold_low:.3f}")

    # Trova gli indici in cui il valore supera la soglia alta o scende sotto la soglia bassa
    high_indices = np.where(array > threshold_high)[0]
    low_indices = np.where(array < threshold_low)[0]

    # Unisci gli indici alti e bassi per trovare l'intervallo utile
    useful_indices = np.sort(np.concatenate((high_indices, low_indices)))

    if len(useful_indices) == 0:
        print("Nessun valore utile trovato.")
        return array, None, None

    # Identifica l'inizio e la fine del primo intervallo continuo utile
    start = useful_indices[0]
    end = useful_indices[0]

    for i in range(1, len(useful_indices)):
        if useful_indices[i] == useful_indices[i - 1] + 1:
            end = useful_indices[i]
        else:
            break

    print(f"Intervallo utile trovato: start={start}, end={end}")
    return array, start, end


def read_serial_data(ser):
    """Reads and processes serial data."""
    cleaned_data = clean_data(ser)
    if not cleaned_data:
        return None

    data_acquired = [
        cleaned_data[0] + 256 * cleaned_data[1],
        cleaned_data[2] + 256 * cleaned_data[3],
    ]

    data_acquired[0] = convert_bits_to_voltage(3.3, 12, data_acquired[0], 3.3)
    data_acquired[1] = convert_bits_to_voltage(2.5, 12, data_acquired[1], 1.5)

    return data_acquired


def smooth_data(data, window_length=11, polyorder=2):
    """Applies Savitzky-Golay filter to smooth data."""
    if window_length % 2 == 0:
        window_length += 1  # Ensure window length is odd
    if window_length > len(data):
        window_length = len(data)  # Ensure window length is not greater than data size
    return savgol_filter(data, window_length=window_length, polyorder=polyorder)

def calculate_thresholds(data, k=2):
    """Calculates dynamic thresholds based on mean and standard deviation."""
    mean = np.mean(data)
    std = np.std(data)
    high_threshold = mean + k * std
    low_threshold = mean - k * std
    return high_threshold, low_threshold


def classify_data(data, high_threshold, low_threshold):
    """Classifies data as high or low based on thresholds."""
    high_indices = np.where(data > high_threshold)[0]
    low_indices = np.where(data < low_threshold)[0]
    return high_indices, low_indices


def plot_classified_data(data, smoothed_data, high_threshold, low_threshold, high_indices, low_indices):
    """Plots classified data with thresholds."""
    plt.figure(figsize=(10, 6))
    plt.plot(data, label="Raw Data", alpha=0.5, color='gray')
    plt.plot(smoothed_data, label="Smoothed Data", linewidth=2, color='blue')
    plt.axhline(high_threshold, color='red', linestyle='--', label="High Threshold")
    plt.axhline(low_threshold, color='green', linestyle='--', label="Low Threshold")
    plt.scatter(high_indices, smoothed_data[high_indices], color='red', label="High Values", zorder=5)
    plt.scatter(low_indices, smoothed_data[low_indices], color='green', label="Low Values", zorder=5)
    plt.xlabel("Sample Index")
    plt.ylabel("Voltage (V)")
    plt.title("Voltage Analysis with Thresholds")
    plt.legend()
    plt.show()

def simple_plot(csv_file):
    """Reads data from a CSV file and plots it using matplotlib."""
    data = pd.read_csv(csv_file)
    plt.figure(figsize=(10, 6))
    for column in data.columns:
        plt.plot(data[column], label=column)
    plt.xlabel('Index')
    plt.ylabel('Values')
    plt.title('Simple Plot')
    plt.legend()
    plt.show()

def save_data_to_csv(filename, data_array):
    """Saves data to a CSV file."""
    np.savetxt(filename, data_array, delimiter=',')


def main():
    serial_port = '/dev/ttyUSB0'
    baud_rate = 921600
    max_measurements = 25000

    try:
        ser = serial.Serial(serial_port, baud_rate)
        ser.flushInput()

        ch4_data = []
        ch5_data = []

        while len(ch4_data) < max_measurements:
            data = read_serial_data(ser)
            if data:
                ch4_data.append(data[0])
                ch5_data.append(data[1])
                print(f"Measurement {len(ch4_data)}")

        ch4_data = np.array(ch4_data)
        ch5_data = np.array(ch5_data)

        save_data_to_csv('ch4.csv', ch4_data)
        save_data_to_csv('ch5.csv', ch5_data)

        ch5_data, start, end = slice_useful_data(ch5_data)
        if start is not None and end is not None:
            ch4_data = ch4_data[start:end]

            # Smooth the data
            smoothed_data = smooth_data(ch4_data)

            # Calculate thresholds
            high_threshold, low_threshold = calculate_thresholds(smoothed_data)

            # Classify the data
            high_indices, low_indices = classify_data(smoothed_data, high_threshold, low_threshold)

            # Plot classified data
            plot_classified_data(ch4_data, smoothed_data, high_threshold, low_threshold, high_indices, low_indices)

            # Plot the raw data
            simple_plot('ch4.csv')
            simple_plot('ch5.csv')

    except serial.SerialException as e:
        print(f"Serial port error: {e}")
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()


if __name__ == '__main__':
    main()
