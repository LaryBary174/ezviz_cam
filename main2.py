import serial
import time
import struct
import sys
import termios

def force_raw_mode(fd):
    """Жестко отключаем текстовые фильтры Linux, чтобы нули не пропадали"""
    try:
        attrs = termios.tcgetattr(fd)
        # Отключаем входные фильтры
        attrs[0] &= ~(termios.IGNBRK | termios.BRKINT | termios.PARMRK | termios.ISTRIP | termios.INLCR | termios.IGNCR | termios.ICRNL | termios.IXON)
        # Отключаем выходную обработку
        attrs[1] &= ~termios.OPOST
        # Отключаем эхо и канонический режим
        attrs[3] &= ~(termios.ECHO | termios.ECHONL | termios.ICANON | termios.ISIG | termios.IEXTEN)
        termios.tcsetattr(fd, termios.TCSANOW, attrs)
    except Exception as e:
        print(f"Не удалось применить termios: {e}")

def send_msp_command(ser, cmd_code, payload=b''):
    """Отправляет команду MSP"""
    header = b'$M<'
    length = len(payload)
    cmd_byte = bytes([cmd_code])

    checksum_data = bytes([length]) + cmd_byte + payload
    checksum = 0
    for b in checksum_data:
        checksum ^= b

    packet = header + bytes([length]) + cmd_byte + payload + bytes([checksum])

    ser.reset_input_buffer()
    ser.write(packet)
    ser.flush()
    print(f"Отправлен пакет: {packet.hex()}")

def check_connection(ser):
    """Проверяет связь по MSP (MSP_STATUS)"""
    send_msp_command(ser, 101)  # 101 - MSP_STATUS
    time.sleep(0.1)
    response = ser.read(50)

    if response:
        print(f"Ответ от дрона: {response.hex()}")
        if b'$M>' in response:
            print("✅ Успех: Дрон ответил на команду!")
            return True
        else:
            print("⚠️ Получен мусор. Дрон все еще в режиме CLI или терминал Linux шалит.")
            return False
    else:
        print("❌ Ошибка: Дрон молчит.")
        return False

if __name__ == "__main__":
    SERIAL_PORT = '/dev/ttyACM0'  # Проверьте, что порт правильный!

    try:
        # Открываем порт
        with serial.Serial(SERIAL_PORT, 115200, timeout=1) as ser:
            if sys.platform != 'win32':
                force_raw_mode(ser.fileno())

            # КРИТИЧЕСКИ ВАЖНО для Linux: DTR/RTS = False, чтобы дрон не уходил в CLI!
            ser.dtr = False
            ser.rts = False
            time.sleep(1) # Ждем стабилизации порта

            print("--- Проверка соединения ---")
            is_connected = check_connection(ser)

            if is_connected:
                print("\n--- Отправка команды MSP_IDENT ---")
                send_msp_command(ser, 100)
                response = ser.read(20)
                print(f"Ответ дрона: {response.hex()}")

                print("\n--- Тестовый запуск двигателей ---")
                # ВНИМАНИЕ: СНИМИТЕ ПРОПЕЛЛЕРЫ ПЕРЕД ТЕСТИРОВАНИЕМ!
                motors_on_payload = struct.pack('<8H', 1150, 1150, 1150, 1150, 1000, 1000, 1000, 1000)
                send_msp_command(ser, 214, motors_on_payload)
                print("Двигатели включены. Ожидание 10 секунд...")

                time.sleep(10)

                print("\n--- Остановка двигателей ---")
                motors_off_payload = struct.pack('<8H', 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000)
                send_msp_command(ser, 214, motors_off_payload)
                print("Двигатели выключены.")
            else:
                print("\nСвязь не установлена, прерываем запуск двигателей.")

    except serial.SerialException as e:
        print(f"Ошибка COM-порта: {e}")
    except Exception as e:
        print(f"Критическая ошибка: {e}")