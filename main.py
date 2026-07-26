import serial
import time
import struct

def check_connection(port='/dev/ttyUSB0', baudrate=115200):
    try:
        with serial.Serial(port, baudrate, timeout=0.5) as ser:
            time.sleep(2)

            # 2. Жестко очищаем буферы приема и передачи от старого мусора
            ser.reset_input_buffer()
            ser.reset_output_buffer()
            # Отправляем MSP_STATUS (код 101)
            # Пакет: $ M < [len=0] [code=101/0x65] [crc=101/0x65]
            packet = b'$M<\x00\x65\x65'  # Исправлен '0' на '\x00'
            ser.write(packet)
            ser.flush()

            # Читаем ответ (с запасом, так как статус бывает длинным)
            response = ser.read(50)

            if response:
                print(f"Ответ от дрона: {response.hex()}")
                if b'$M>' in response:
                    print("✅ Успех: Дрон ответил на команду!")
                else:
                    print("⚠️ Получен какой-то мусор, проверьте скорость (baudrate).")
            else:
                print("❌ Ошибка: Дрон молчит. Проверьте кабель и настройки UART.")

    except serial.SerialException as e:
        print(f"Ошибка COM-порта: {e}")

def send_msp_command(ser, cmd_code, payload=b''):
    """
    Отправляет команду MSP на полетный контроллер.
    cmd_code: код команды (целое число)
    payload: байтовые данные (bytes)
    """
    header = b'$M<'
    length = len(payload)
    cmd_byte = bytes([cmd_code])

    checksum_data = bytes([length]) + cmd_byte + payload

    checksum = 0
    for b in checksum_data:
        checksum ^= b

    packet = header + bytes([length]) + cmd_byte + payload + bytes([checksum])

    ser.write(packet)
    print(f"Отправлен пакет: {packet.hex()}")

# Переносим исполняемый код в блок __main__
if __name__ == "__main__":
    SERIAL_PORT = '/dev/ttyUSB0'  # замените на ваш порт (на Windows обычно 'COM3' и т.д.)

    print("--- Проверка соединения ---")
    check_connection(SERIAL_PORT)

    print("\n--- Отправка команды MSP_IDENT ---")
    try:
        with serial.Serial(SERIAL_PORT, 115200, timeout=1) as ser:
            send_msp_command(ser, 100)  # MSP_IDENT

            # Ответ на MSP_IDENT обычно занимает минимум 13 байт
            response = ser.read(20)
            print(f"Ответ дрона: {response.hex()}")

            print("\n--- Тестовый запуск двигателей ---")
            # ВНИМАНИЕ: СНИМИТЕ ПРОПЕЛЛЕРЫ ПЕРЕД ТЕСТИРОВАНИЕМ!
            # Код 214 - MSP_SET_MOTOR. 8 значений типа uint16_t, little-endian
            # Значение 1000 = выключено, 1150 = небольшая скорость.
            # Запускаем первые 4 мотора (для квадрокоптера), остальные оставляем на 1000
            motors_on_payload = struct.pack('<8H', 1150, 1150, 1150, 1150, 1000, 1000, 1000, 1000)
            send_msp_command(ser, 214, motors_on_payload)
            print("Двигатели включены. Ожидание 10 секунд...")

            time.sleep(10)

            print("\n--- Остановка двигателей ---")
            # Отправляем 1000 на все моторы для их полной остановки
            motors_off_payload = struct.pack('<8H', 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000)
            send_msp_command(ser, 214, motors_off_payload)
            print("Двигатели выключены.")

    except Exception as e:
        print(f"Ошибка: {e}")