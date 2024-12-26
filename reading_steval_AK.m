%Format of the data transmitted by the serial streamer (Nucleo_L476RG +
%STEAVL-AKI001V1)
%byte 1 --> '*'
%byte 2 --> '*'
%byte 3 --> lower byte of IN4
%byte 4 --> upper byte of IN4
%byte 5 --> lower byte of IN5
%byte 6 --> upper byte of IN5

function v_out = converting_bits_to_v ( v_range, n_bits ,value_in )
    v_out = value_in * v_range /(2 ^ n_bits);
end

%clean readed data by chat gpt
function newArray = processDataArray(dataArray)
    % Trova gli indici dei doppi asterischi
    doubleAsteriskIndices = find(dataArray == '*' & circshift(dataArray, -1) == '*');

    % Se non ci sono doppi asterischi, restituisci un array vuoto
    if isempty(doubleAsteriskIndices)
        newArray = [];
        return;
    end

    % Inizia a costruire il nuovo array a partire dal primo doppio asterisco
    startIndex = doubleAsteriskIndices(1) + 2;
    endIndex = min(startIndex + 3, length(dataArray)); % Limita l'indice finale alla lunghezza dell'array
    newArray = [dataArray(startIndex:endIndex)];
end


function read_serial_data(src, evt)
    % Read raw data from the serial port and 
    % coverting each 8 byte array from binary coding to a decimal number 
    raw_data = read(src, 11, "uint8");
    
    %process data to have a usefull reading
    cleaned_data = processDataArray(raw_data);

    % Extract data from the raw data
    data_acquired = zeros(2,1);
    
    % ADC have 12 coding bits 
    % 1°byte = first 8 coding bits (0;255)
    % 2°byte = last 4 coding bits + 4 empty bits (256;4096)
    % to unite the 2 decimal number represented by the 2 bytes in only 1
    % decimal number limited between ( 0 ; 2^12 = 4096)
    data_acquired(1,1) = cleaned_data(1)+256*cleaned_data(2);
    data_acquired(2,1) = cleaned_data(3)+256*cleaned_data(4);

    disp("data_acquired raw value: ");
    disp (data_acquired)
    
    %conveting reading to voltages
    disp ("data in V: ");
    data_acquired(1,1) = converting_bits_to_v( 3.3 , 12 ,data_acquired(1,1));
    data_acquired(2,1) = converting_bits_to_v(3.3 , 12 , data_acquired(2,1));
    disp(data_acquired)
    
end


% Initialize serial port
serial_port = "COM9";
data_rate = 921600;
Steval_ak = serialport(serial_port, data_rate);

% Set terminator character for reading and writing
configureTerminator(Steval_ak, 42, "LF");

% Set up callback function
configureCallback(Steval_ak, "terminator", @read_serial_data);


% Start data acquisition
% #flush(device) flushes all data from both the input and output buffers of the specified serial port.
flush(Steval_ak);  % Initial flush to clear any existing data

