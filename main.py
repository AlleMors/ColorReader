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


def slice_useful_data(array, threshold=0.75):
    """
    Identifies and slices useful data based on a threshold.

    Parameters:
        array (np.array): Array of data.
        threshold (float): Threshold to consider data useful.

    Returns:
        array (np.array): Original array.
        start (int): Start of the first useful interval.
        end (int): End of the first useful interval.
    """
    print(f"Threshold used: {threshold:.3f}")

    # Find indices where the value exceeds the threshold
    high_indices = np.where(array > threshold)[0]

    if len(high_indices) == 0:
        print("No useful values found.")
        return array, None, None

    # Find the longest continuous interval of high values
    longest_start = high_indices[0]
    longest_end = high_indices[0]
    current_start = high_indices[0]
    current_end = high_indices[0]

    for i in range(1, len(high_indices)):
        if high_indices[i] == high_indices[i - 1] + 1:
            current_end = high_indices[i]
        else:
            if (current_end - current_start) > (longest_end - longest_start):
                longest_start = current_start
                longest_end = current_end
            current_start = high_indices[i]
            current_end = high_indices[i]

    # Check the last interval
    if (current_end - current_start) > (longest_end - longest_start):
        longest_start = current_start
        longest_end = current_end

    print(f"Useful interval found: start={longest_start}, end={longest_end}")
    return array, longest_start, longest_end


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

            # Calculate the length of each color interval
            interval_length = (end - start) // 3

            # Calculate averages for red, green, and blue channels
            red_mean = np.mean(ch4_data[:interval_length])
            green_mean = np.mean(ch4_data[interval_length:2 * interval_length])
            blue_mean = np.mean(ch4_data[2 * interval_length:])

            # Normalize the RGB values to be between 0 and 1
            max_value = max(red_mean, green_mean, blue_mean)
            red_value = red_mean / max_value
            green_value = green_mean / max_value
            blue_value = blue_mean / max_value

            # Display the detected color
            plt.figure(figsize=(2, 2))
            plt.imshow([[(red_value, green_value, blue_value)]])
            plt.axis('off')
            plt.title(f'Detected Color: R={red_value:.2f}, G={green_value:.2f}, B={blue_value:.2f}')
            plt.show()

            # Plot the raw data
            plt.figure(figsize=(10, 6))
            plt.plot(ch4_data, label="ch4 Data")
            plt.axvline(interval_length, color='r', linestyle='--', label="Red Interval")
            plt.axvline(2 * interval_length, color='g', linestyle='--', label="Green Interval")
            plt.axvline(3 * interval_length, color='b', linestyle='--', label="Blue Interval")
            plt.xlabel('Index')
            plt.ylabel('Voltage (V)')
            plt.title('ch4 Data with Color Intervals')
            plt.legend()
            plt.show()

    except serial.SerialException as e:
        print(f"Serial port error: {e}")
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()


if __name__ == '__main__':
    main()