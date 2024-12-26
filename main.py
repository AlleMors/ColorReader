import numpy as np
import serial
import time
import pandas as pd
from matplotlib import pyplot as plt


# Format of the data transmitted by the serial streamer (Nucleo_L476RG +
# STEAVL-AKI001V1)
# byte 1 --> '*'
# byte 2 --> '*'
# byte 3 --> lower byte of IN4
# byte 4 --> upper byte of IN4
# byte 5 --> lower byte of IN5
# byte 6 --> upper byte of IN5

def convert_bits_to_voltage(v_range, n_bits, value_in, v_lim):
    v_out = value_in * v_range / (2 ** n_bits)

    # checking the v_out to eliminate peaks
    if v_out > v_lim:
        v_out = v_lim

    return v_out


# clean readed data by chat gpt
def clean_data(ser):
    while True:
        data = ser.read(1)
        if data == b'*':  # se leggo il primo asterisco
            data = ser.read(1)  # vedo se ce n'è un secondo
            if data == b'*':  # se leggo il secondo asterisco dopo il primo
                data = ser.read(4)  # leggi i 4 bytes  dati
                if data:
                    # Convertiamo i 4 byte in un array di 4 interi
                    int_values = [int.from_bytes(data[i:i + 1], byteorder='big') for i in range(4)]
                    return int_values


def slice_usefull_data(array):
    # Trova dove i valori sono "accesi" (1)
    accesi = np.where(array == 1)[0]  # Restituisce gli indici dei valori accesi

    if len(accesi) == 0:
        # Se non ci sono valori accesi
        return array, None, None

    # Determina l'inizio e la fine del primo intervallo completo di accesi
    inizio_dati_utili = accesi[0]
    fine_dati_utili = accesi[0]

    # Trova il primo intervallo completo, ovvero senza interruzioni
    for i in range(1, len(accesi)):
        if accesi[i] == accesi[i - 1] + 1:  # Controlla se i valori sono consecutivi
            fine_dati_utili = accesi[i]  # Allunga l'intervallo
        else:
            break  # Una discontinuità interrompe l'intervallo completo

    print(inizio_dati_utili, fine_dati_utili)

    # Restituisce l'array, l'inizio e la fine dei dati utili
    return array, inizio_dati_utili, fine_dati_utili


def read_serial_data(ser):
    # Read raw data from the serial port and
    # converting each 8-byte array from binary coding to a decimal number
    cleaned_data = clean_data(ser)
    # print("Data acquired raw value:")
    # print(cleaned_data)

    if not cleaned_data:
        return

    # ADC have 12 coding bits
    # 1°byte = first 8 coding bits(0; 255)
    # 2°byte = last 4 coding bits + 4 empty bits (256;4096)
    # to unite the 2 decimal numbers represented by the 2 bytes in only 1 decimal number limited between ( 0 ; 2^12 = 4096)

    data_acquired = [cleaned_data[0] + 256 * cleaned_data[1],
                     cleaned_data[2] + 256 * cleaned_data[3]]

    # print("Data Converted beetween [0;4096] :")
    # print(data_acquired)

    # print("Data in V:")
    data_acquired[0] = convert_bits_to_voltage(3.3, 12, data_acquired[0], 3.3)
    data_acquired[1] = convert_bits_to_voltage(2.5, 12, data_acquired[1], 1.5)

    # print(data_acquired)
    return data_acquired


def plotting_read_data(data_array, title, ch):
    if ch == 5:
        plt.plot(data_array.round(2))
        plt.xlabel('Index')
        plt.ylabel('Value')
        plt.title(str(title))
        plt.show()

    if ch == 4:
        # Define the ranges and colors
        ranges = [
            (500, 2500, 'red'),
            (3500, 5500, 'green'),
            (6500, 8500, 'blue')
        ]

        # Create the plot
        plt.figure()

        # Plot each range with its corresponding color
        for start, end, color in ranges:
            plt.plot(np.arange(start, end + 1), data_array[start:end + 1], color=color, label=color)

        # Add labels and title
        plt.xlabel("Index")
        plt.ylabel("Value")
        plt.title("Colored Sections of Data")

        # Add legend
        plt.legend()

        # Show the plot
        plt.show()


if __name__ == '__main__':
    # Serial port configuration
    serial_port = 'COM9'
    baud_rate = 921600
    # Create a serial port object
    ser = serial.Serial(serial_port, baud_rate)

    # Flush input buffer
    ser.flushInput()

    # Start reading data (you might want to use a loop or a timer for continuous reading)

    max_measurements = 25000
    measurements_for_each_color = max_measurements / 3
    read_data_ch4_array = []
    read_data_ch5_array = []

    while True:
        current_measurement_number = len(read_data_ch4_array)
        if current_measurement_number < max_measurements:
            out = read_serial_data(ser)
            read_data_ch4_array.append(out[0])
            read_data_ch5_array.append(out[1])
            print(current_measurement_number)
        else:
            # calcolo  media delle letture del colore rosso
            # converto da array a numpy_array
            # print(read_data_ch4_array)
            read_data_ch4_array = np.array(read_data_ch4_array)
            read_data_ch5_array = np.array(read_data_ch5_array)

            # Salva l'array in un file CSV
            # nella prova ho salvato nei csv le letture di un oggetto BLU
            np.savetxt('ch4.csv', read_data_ch4_array, delimiter=',')
            np.savetxt('ch5.csv', read_data_ch5_array, delimiter=',')

            # cutting out the initial data that could be half of a previous measuration cycle
            read_data_ch5_array, inizio_dati_utili, fine_dati_utili = slice_usefull_data(read_data_ch5_array)

            # reshaping the ch4 array to contain only usefull data
            read_data_ch4_array = read_data_ch4_array[inizio_dati_utili: fine_dati_utili]

            # Calculate averages for red, green, and blue channels
            # uso solo i valori centrali degli intervalli di raccolta
            red_mean = np.mean(read_data_ch4_array[500:2500])
            green_mean = np.mean(read_data_ch4_array[3500:5500])
            blue_mean = np.mean(read_data_ch4_array[6500:8500])

            # computing which is the most prevalent colour in the read obj
            max_mean_value = max(red_mean, green_mean, blue_mean)

            # default color value
            read_color = 'white'

            # print resulting color
            if max_mean_value == red_mean:
                read_color = 'red'
            elif max_mean_value == green_mean:
                read_color = 'green'
            else:
                read_color = 'blue'

            print("the obj has color: ", read_color)

            plotting_read_data(read_data_ch4_array, "ch4_graph", 4)
            plotting_read_data(read_data_ch4_array, "ch4_graph", 5)
            plotting_read_data(read_data_ch5_array, "ch5_graph", 5)

            break
