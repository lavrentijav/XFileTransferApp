import socket
import socket as sk
import asyncio
import os
import zlib
import threading
import time
import pickle
import hashlib
from tqdm import tqdm
import queue
import configparser
from collections.abc import Iterable
from LocalizationForVersion_0_0_2 import Languages

from typing import List

if "config.ini" not in os.listdir():
    conf = open("config.ini", "w")
    conf.write(
        """
#FILE - file to send
#SAVE_PATH - dir to save received file
#MAX_PACKET_SIZE - what weight 1 packet to send in kbytes
#LANGUAGES - language [ru, en, it, de, ja, zh, ko, tr]
[Settings server]
FILE = test.txt
MAX_PORTS = 4
HOST_IP = 127.0.0.1
HOST_PORT = 55500
MAX_PACKET_SIZE = 4096
[Settings client]
SAVE_PATH = .
HOST_IP = 127.0.0.1
HOST_PORT = 55500
[Languages]
LANGUAGE = en
"""
    )
    conf.close()

class Process:

    @staticmethod
    def get_size_in_optimum_unit(size, unit="bytes", step=1000):
        global TRANSLATOR

        size_kilo = size / step  # 10^3
        size_mega = size_kilo / step  # 10^6
        size_giga = size_mega / step  # 10^9
        size_tera = size_giga / step  # 10^12
        size_peta = size_tera / step  # 10^15
        size_exa = size_peta / step  # 10^18
        size_zetta = size_exa / step  # 10^21
        size_yotta = size_zetta / step  # 10^24
        size_ronna = size_yotta / step  # 10^27
        size_quetta = size_ronna / step  # 10^30

        if size_quetta > 0.5:
            size = size_quetta
            unit = TRANSLATOR.get_unit("Quetta") + unit
        elif size_ronna > 0.5:
            size = size_ronna
            unit = TRANSLATOR.get_unit("Ronna") + unit
        elif size_yotta > 0.5:
            size = size_yotta
            unit = TRANSLATOR.get_unit("Yotta") + unit
        elif size_zetta > 0.5:
            size = size_zetta
            unit = TRANSLATOR.get_unit("Zetta") + unit
        elif size_exa > 0.5:
            size = size_exa
            unit = TRANSLATOR.get_unit("Exa") + unit
        elif size_peta > 0.5:
            size = size_peta
            unit = TRANSLATOR.get_unit("Peta") + unit
        elif size_tera > 0.5:
            size = size_tera
            unit = TRANSLATOR.get_unit("Tera") + unit
        elif size_giga > 0.5:
            size = size_giga
            unit = TRANSLATOR.get_unit("Giga") + unit
        elif size_mega > 0.5:
            size = size_mega
            unit = TRANSLATOR.get_unit("Mega") + unit
        elif size_kilo > 0.5:
            size = size_kilo
            unit = TRANSLATOR.get_unit("Kilo") + unit
        else:
            size = size
            unit = unit

        return {"size": round(size, 3), "unit": unit}



    @staticmethod
    def clear_temp_folder(folder_path, progress_info: str = "Очистка"):

        def delete_file(files: queue.Queue, progress: queue.Queue):
            while not files.empty():
                os.remove(files.get(timeout=1))
                progress.put(1)

        files = queue.Queue()
        bar = queue.Queue()
        for file in os.listdir(folder_path):
            files.put(file)

        threading.Thread(target=delete_file, args=(files, bar)).start()
        threading.Thread(target=delete_file, args=(files, bar)).start()
        threading.Thread(target=delete_file, args=(files, bar)).start()

        with tqdm(total=len(os.listdir(folder_path)), unit="Files",
                  unit_scale=True, desc=progress_info, ascii=True) as pbar1:
            while not bar.empty():
                pbar1.update(bar.get(timeout=1))


    @staticmethod
    def ensure_path_exists(path):
        """
        Проверяет, существует ли указанный путь. Если нет, создает его.
        Путь может быть как абсолютным, так и относительным.

        :param path: Путь, который нужно проверить или создать.
        :return: Полный путь к указанной директории.
        """
        # Получаем абсолютный путь
        if os.path.isabs(path):
            full_path = path
        else:
            full_path = os.path.join(os.getcwd(), path)

        full_path = os.path.normpath(full_path)

        # Проверяем, существует ли путь
        if not os.path.exists(full_path):
            # Если нет, создаем директорию
            os.makedirs(full_path)
        else:
            pass

        return full_path

    @staticmethod
    def combine_chunks_from_directory(directory, output_file):
        # Получаем список всех файлов в директории и сортируем их
        chunk_files = [str(f) + ".bin" for f in range(len(os.listdir(directory)))]

        outfile = os.open(output_file,
                          flags=((os.O_RDWR | os.O_CREAT | os.O_BINARY) if os.name == "nt" else os.O_RDWR | os.O_CREAT))
        with tqdm(total=len(chunk_files), unit="Files",
                  unit_scale=True, desc="Merging File") as pbar2:
            for chunk_filename in chunk_files:
                chunk_path = os.path.join(directory, chunk_filename)
                infile = os.open(chunk_path,
                                 flags=((os.O_RDONLY | os.O_BINARY) if os.name == "nt" else os.O_RDONLY))
                os.write(outfile, os.read(infile, os.path.getsize(chunk_path)))
                os.close(infile)
                pbar2.update(1)
        os.close(outfile)

    @staticmethod
    def clear_operative_drive(save_thread: queue.Queue):
        flag = ((os.O_RDWR | os.O_CREAT | os.O_BINARY) if os.name == "nt" else os.O_RDWR | os.O_CREAT)
        while True:
            try:
                data2save = save_thread.get(timeout=1)
                data_id, data = data2save["id"], data2save["data"]
                packet_file = os.open(f"client_temp/{data_id}.bin", flags=flag)
                os.write(packet_file, data)
                os.close(packet_file)
            except queue.Empty:
                break

    @staticmethod
    def calculate_file_hash(file_path, hash_algorithm='sha1'):
        hash_func = hashlib.new(hash_algorithm)

        with open(file_path, 'rb') as f:
            # Читаем файл по частям
            while chunk := f.read(4096):
                hash_func.update(chunk)

        return hash_func.hexdigest()

    @staticmethod
    def get_name_from_path(path: str):
        if path.find("/") != -1:
            file_name = path.split("/")[-1]
        elif path.find("//") != -1:
            file_name = path.split("//")[-1]
        elif path.find("\\") != -1:
            file_name = path.split("\\")[-1]
        else:
            file_name = path
        return file_name

    @staticmethod
    def port_is_free(test_host="127.0.0.1", port=1024):
        sock = sk.socket(sk.AF_INET, sk.SOCK_STREAM)
        try:
            sock.bind((test_host, port))
            sock.close()
            return port
        except OSError:
            return -1

    @staticmethod
    def count_lowest_elements(data):
        # Извлекаем все значения из словарей и преобразуем их в числа
        def is_iterable(variable):
            return isinstance(variable, Iterable)

        def get_count(variable):
            if is_iterable(variable):
                return sum(get_count(element) for element in variable)
            else:
                return 1

        return get_count(data)

    @staticmethod
    def compress_data(data: bytes) -> bytes:
        return zlib.compress(data)

    @staticmethod
    def decompress_data(data: bytes) -> bytes:
        return zlib.decompress(data)

    @staticmethod
    def generate_large_data(size: int) -> bytes:
        return os.urandom(size)

    @staticmethod
    def calculate_number_of_chunks(file_path, chunk_size=4096):
        file_size = os.path.getsize(file_path)  # Получаем размер файла в байтах
        number_of_chunks = (file_size + chunk_size - 1) // chunk_size  # Вычисляем количество частей
        return number_of_chunks

    @staticmethod
    def split_file(input_file: str, save_dir: str, chunk_size: int = 4096) -> list:
        files = []
        # Открытие файла для чтения в бинарном формате
        flags = ((os.O_RDONLY | os.O_BINARY) if os.name == "nt" else os.O_RDONLY)
        file_descriptor = os.open(input_file, flags)

        def read_save(file_descriptor, chunk_size, save_dir, files_numbers, files):
            while True:
                # Чтение блока данных
                chunk = os.read(file_descriptor, chunk_size)

                # Если данные пустые, значит достигнут конец файла
                if not chunk:
                    break
                # Обработка прочитанных данных
                chunk_filename = f'{save_dir}/{files_numbers.get()}'  # Формат имени файла

                chunk_file = open(chunk_filename, "xb")
                chunk_file.write(chunk)
                chunk_file.close()

                files.put(chunk_filename)

        files_numbers = queue.Queue()
        success_file_names = queue.Queue()

        number_chunks = Process.calculate_number_of_chunks(input_file, chunk_size)

        for i in range(number_chunks):
            files_numbers.put(i)

        with tqdm(total=number_chunks, unit="Files", unit_scale=True, desc="Creating cache") as pbar2:
            cacher_th_1 = threading.Thread(target=read_save,
                                           args=(file_descriptor,
                                                 chunk_size,
                                                 save_dir,
                                                 files_numbers,
                                                 success_file_names))
            cacher_th_2 = threading.Thread(target=read_save,
                                           args=(file_descriptor,
                                                 chunk_size,
                                                 save_dir,
                                                 files_numbers,
                                                 success_file_names))
            cacher_th_3 = threading.Thread(target=read_save,
                                           args=(file_descriptor,
                                                 chunk_size,
                                                 save_dir,
                                                 files_numbers,
                                                 success_file_names))

            cacher_th_1.start()
            cacher_th_2.start()
            cacher_th_3.start()
            while True:
                # Чтение блока данных
                try:
                    chunk_filename = success_file_names.get(timeout=1)
                except queue.Empty:
                    break
                pbar2.update(1)

        return files

    @staticmethod
    def update_progress_bar(total_size, progress_queue, info, work: bool = True):
        with tqdm(total=total_size, unit="it", unit_scale=True, desc=info) as pbar:
            while work:
                try:
                    chunk_size = progress_queue.get(timeout=2)  # Ждем обновления
                    pbar.update(chunk_size)
                except queue.Empty:
                    break


class Server:

    @staticmethod
    def set_hash(my_socket, data: bytes):
        # Шаг 1: отправка хэша
        hash_value = hashlib.sha1(data).hexdigest()
        client_check_code_hash = None
        while client_check_code_hash != "*#*#MATCH#*#*":
            my_socket.sendall(pickle.dumps(hash_value))

            # Шаг 3: ожидание подтверждения от клиента
            response_code = my_socket.recv(1024)
            response_code = pickle.loads(response_code)
            if response_code == "*#*#CONFIR#*#*":
                response_code = "*#*#ACK#*#*"

            if response_code == "*#*#ACK#*#*":
                # Шаг 4: повторная отправка хэша
                my_socket.sendall(pickle.dumps(hash_value))

                # Шаг 5: ожидание проверки хэша
                client_response = my_socket.recv(1024)
                client_check_code_hash = pickle.loads(client_response)

                while client_check_code_hash != "*#*#MATCH#*#*" and client_check_code_hash != "*#*#MISMATCH#*#*":
                    client_response = my_socket.recv(1024)
                    client_check_code_hash = pickle.loads(client_response)


                if client_check_code_hash == "*#*#MATCH#*#*":
                    return
                elif client_check_code_hash == "*#*#MISMATCH#*#*":
                    continue  # Возврат к шагу 1

    @staticmethod
    def set_data(my_socket, bin_data):
        client_check_code_data = None
        while client_check_code_data != "*#*#CONFIR#*#*":
            # Шаг 7: отправка пакета
            my_socket.sendall(pickle.dumps("*#*#THIS_DATA#*#*"))
            client_check_code_data = my_socket.recv(1024)
            client_check_code_data = pickle.loads(client_check_code_data)

            if client_check_code_data == "*#*#CONFIR#*#*":
                my_socket.sendall(bin_data)
                my_socket.recv(1024)
                return
            else:
                continue

    @staticmethod
    def check_valid(my_socket, data):
        client_check_code_valid = None
        while client_check_code_valid != "*#*#VALID#*#*":
            # Шаг 9: ожидание подтверждения от клиента
            my_socket.sendall(pickle.dumps("*#*#DATA_VALIDATION#*#*"))

            client_check_code_valid = my_socket.recv(1024)
            client_check_code_valid = pickle.loads(client_check_code_valid)

            if client_check_code_valid == "*#*#NOT_VALID#*#*":
                Server.set_data(my_socket, data)
                continue
            elif client_check_code_valid == "*#*#VALID#*#*":
                return

    @staticmethod
    def torrent_server(my_socket: sk.socket,
                       progress_queue: queue.Queue, file_names: List[str], dir_save: str = "server_temp",
                       work: bool = True):
        while work is False:
            time.sleep(0.1)
        for file_packet_name in file_names:
            p_id = file_packet_name.split("/")[-1].split(".")[0]
            file_packet = os.open(dir_save + "/" + file_packet_name,
                                  flags=((os.O_RDONLY | os.O_BINARY) if os.name == "nt" else os.O_RDONLY))
            file_size = os.path.getsize(dir_save + "/" + file_packet_name)
            paket_id, packet = p_id, os.read(file_packet, file_size)
            os.close(file_packet)
            send_data = {
                paket_id: packet
            }
            send_data = pickle.dumps(send_data)
            my_socket.sendall(pickle.dumps("*#*#MORE_DATA#*#*"))
            my_socket.recv(1024)
            Server.set_hash(my_socket, send_data)
            Server.set_data(my_socket, send_data)
            Server.check_valid(my_socket, send_data)
            progress_queue.put(1)

        my_socket.sendall(pickle.dumps("*#*#END#*#*"))
        my_socket.recv(1024)
        my_socket.close()

    @staticmethod
    def update_progress_bar(total_size, progress_queue, work: bool = True):
        with tqdm(total=total_size, unit="it", unit_scale=True, desc='Скачивание файла') as pbar:
            while work:
                try:
                    chunk_size = progress_queue.get(timeout=2)  # Ждем обновления
                    pbar.update(chunk_size)
                except queue.Empty:
                    break

    @staticmethod
    def send_data(file_info: dict, my_socket: socket.socket,
                  max_ports_connecting: int = 4, block_size: int = 4096, my_host_ip: str = '127.0.0.1'):
        global TRANSLATOR
        count_blocks: int = file_info["CountBlocks"]
        cache_file_dir: str = file_info["CacheDir"]
        file_weight_bytes: int = file_info["FileWeight"]
        file_hash: str = file_info["FileHash"]
        file_name: str = file_info["FileName"]
        file_size: int = file_info["FileSize"]
        files_names: list = os.listdir(cache_file_dir)

        ports = []

        min_port = 50000
        max_port = 65535

        for i in range(min_port, max_port):
            if len(ports) >= max_ports_connecting:
                break
            else:
                try:
                    port_id = Process.port_is_free(my_host_ip, i)
                    if port_id != -1:
                        ports += [port_id]
                except IOError:
                    continue

        num_threads = min(len(ports), count_blocks)

        while True:
            get_request = my_socket.recv(1024)
            get_request = pickle.loads(get_request)
            if get_request == "*#*#PORTS#*#*":
                my_socket.sendall(pickle.dumps(ports[:num_threads]))
            elif get_request == "*#*#COUNT_BLOCKS#*#*":
                my_socket.sendall(pickle.dumps(count_blocks))
            elif get_request == "*#*#FILE_HASH#*#*":
                my_socket.sendall(pickle.dumps(file_hash))
            elif get_request == "*#*#FILE_NAME#*#*":
                my_socket.sendall(pickle.dumps(file_name))
            elif get_request == "*#*#BLOCK_SIZE#*#*":
                my_socket.sendall(pickle.dumps(block_size))
            elif get_request == "*#*#FILE_SIZE#*#*":
                my_socket.sendall(pickle.dumps(file_size))
            elif get_request == "*#*#END#*#*":
                break

        my_socket.close()

        threads = []
        files = []
        for i in range(len(ports)):
            files.append([])
            for j in range(i, len(files_names), len(ports)):
                files[-1].append(files_names[j])

        progress_bar_queue = queue.Queue()
        work = False

        if work:
            pass

        for id_t_port in range(num_threads):
            t_port = ports[id_t_port]
            s = sk.socket()
            s.bind((my_host_ip, t_port))
            s.listen(1)
            my_socket, _ = s.accept()
            th = threading.Thread(target=Server.torrent_server,
                                  args=(
                                      my_socket, progress_bar_queue, files[id_t_port], cache_file_dir,
                                      lambda work: work))
            th.start()

            threads.append(th)

        work = True

        if work:
            pass

        bar = threading.Thread(target=Process.update_progress_bar,
                               args=(count_blocks, progress_bar_queue, "Sending", lambda work: work))
        bar.start()

        start_time = time.perf_counter()

        for thread in threads:
            thread.join()

        bar.join()

        work = False

        if work:
            pass

        end_time = time.perf_counter()

        speed, unit_s = Process.get_size_in_optimum_unit(file_weight_bytes / (end_time - start_time),
                                                       "", 1024)

        data_weight, unit_w = Process.get_size_in_optimum_unit(file_weight_bytes, "", 1024)

        print(TRANSLATOR.get_text("AllPackagesSent"))
        print(TRANSLATOR.get_text("TransferTime") % str(end_time - start_time))
        print(TRANSLATOR.get_text("TransferSpeed") % (str(speed) + unit_s))
        print(TRANSLATOR.get_text("DataWeight") % (str(data_weight) + unit_w))
        print()

    @staticmethod
    async def start_send_data(file_path: str, my_host_ip='192.168.1.11', main_port=4080, max_ports_connecting=4,
                              block_size: int = 4096):
        print(TRANSLATOR.get_text("Preparing"))

        data_weight_bytes = os.path.getsize(file_path)
        file_name = Process.get_name_from_path(file_path)
        data_hash = Process.calculate_file_hash(file_path)

        if "server_temp" not in os.listdir():
            os.mkdir("server_temp")

        files_names = os.listdir("server_temp")
        Process.clear_temp_folder("server_temp", TRANSLATOR.get_text("ClearingCache"))

        files_names = Process.split_file(file_path, "server_temp", block_size)

        # Кол-во блоков для передачи

        len_blocks = Process.calculate_number_of_chunks(file_path, block_size)

        # Запуск сервера и создание информационного сокета с клиентом

        s = sk.socket()
        s.bind((my_host_ip, main_port))
        s.listen(1)
        data_weight, unit_w = Process.get_size_in_optimum_unit(data_weight_bytes, "", 1024)
        print(TRANSLATOR.get_text("DataWeight") % (str(data_weight) + unit_w))
        print(TRANSLATOR.get_text("BlocksCount") % str(len_blocks))
        print(TRANSLATOR.get_text("ServerStarted") % (my_host_ip, main_port))
        my_socket, addr = s.accept()

        file_info = {
            "FileName": file_name,
            "FileHash": data_hash,
            "CacheDir": "sever_temp",
            "CountBlocks": len_blocks,
            "FileWeight": data_weight_bytes,
            "FileSize": data_weight_bytes
        }

        Server.send_data(file_info, my_socket,
                         max_ports_connecting=max_ports_connecting, block_size=block_size,
                         my_host_ip=my_host_ip)

        # Передача информации о данных

        Process.clear_temp_folder("server_temp", TRANSLATOR.get_text("ClearingCache"))


class Client:

    @staticmethod
    def get_hash(my_socket) -> str:
        """
        Функция для клиента, которая получает хэш от сервера.
        """
        hash_value_1 = ""
        hash_value_2 = "."
        while hash_value_1 != hash_value_2:
            # Шаг 2: получение хэша
            hash_value_1 = my_socket.recv(1024)
            hash_value_1 = pickle.loads(hash_value_1)

            # Шаг 3: отправка кода, что хэш получен
            my_socket.sendall(pickle.dumps("*#*#ACK#*#*"))

            # Шаг 5: проверка хэша
            hash_value_2 = my_socket.recv(1024)
            hash_value_2 = pickle.loads(hash_value_2)

            if hash_value_1 == hash_value_2:
                my_socket.sendall(pickle.dumps("*#*#MATCH#*#*"))
            else:
                my_socket.sendall(pickle.dumps("*#*#MISMATCH#*#*"))
        return hash_value_1

    @staticmethod
    def get_data(my_socket, packet_size: int = 4096) -> dict:
        server_response = None
        data_packet = {}
        while server_response != "*#*#THIS_DATA#*#*":
            server_response = my_socket.recv(1024)
            server_response = pickle.loads(server_response)

            if server_response == "*#*#THIS_DATA#*#*":
                my_socket.sendall(pickle.dumps("*#*#CONFIR#*#*"))
                max_data_size = int(packet_size * 2)
                data_chunk = my_socket.recv(max_data_size)

                data = pickle.loads(data_chunk)
                del data_chunk
                data_packet.update(data)
                my_socket.sendall(pickle.dumps("*#*#CONFIR#*#*"))
        return data_packet

    @staticmethod
    def validation(my_socket: socket.socket, valid_hash, my_data: dict, packet_size: int = 4096):
        valid = False
        while valid is not True:
            server_response = my_socket.recv(1024)
            server_response = pickle.loads(server_response)
            if server_response == "*#*#DATA_VALIDATION#*#*":
                data_packet_hash = hashlib.sha1(pickle.dumps(my_data)).hexdigest()

                if data_packet_hash == valid_hash:
                    valid = True
                else:
                    my_socket.sendall(pickle.dumps("*#*#NOT_VALID#*#*"))
                    break
        else:
            my_socket.sendall(pickle.dumps("*#*#VALID#*#*"))
            return my_data
        data = Client.get_data(my_socket=my_socket, packet_size=packet_size)
        return Client.validation(my_socket=my_socket, valid_hash=valid_hash, my_data=data, packet_size=packet_size)

    @staticmethod
    def torrent_client(my_socket: socket.socket, progress: queue.Queue, save_parser: queue.Queue,
                       packet_size: int = 4096):
        """
        Функция для клиента, которая обрабатывает получение данных от сервера.
        """

        my_socket.recv(1024)
        my_socket.sendall(pickle.dumps("*#*#ACKNOWLEDGE#*#*"))

        while True:
            valid_hash = Client.get_hash(my_socket)

            my_data = Client.get_data(my_socket, packet_size)

            my_data = Client.validation(my_socket, valid_hash, my_data)

            data_code = my_socket.recv(1024)
            data_code = pickle.loads(data_code)

            data = {
                "id": list(my_data.keys())[0],
                "data": list(my_data.values())[0]
            }
            save_parser.put(data)

            progress.put(1)

            if data_code == "*#*#END#*#*":
                my_socket.sendall(pickle.dumps("*#*#ACKNOWLEDGE#*#*"))
                my_socket.close()
                return
            elif data_code == "*#*#MORE_DATA#*#*":
                my_socket.sendall(pickle.dumps("*#*#ACKNOWLEDGE#*#*"))
                continue

    @staticmethod
    def receive_data(host='192.168.1.11', info_port=-1, save_dir: str = "."):
        global TRANSLATOR
        if "client_temp" not in os.listdir():
            os.mkdir("client_temp")
        Process.clear_temp_folder("client_temp", "Очистка кэша")

        my_socket = socket.socket()
        my_socket.connect((host, info_port))
        my_socket.sendall(pickle.dumps("*#*#PORTS#*#*"))
        ports = pickle.loads(my_socket.recv(4092))
        my_socket.sendall(pickle.dumps("*#*#COUNT_BLOCKS#*#*"))
        len_blocks = pickle.loads(my_socket.recv(4092))
        my_socket.sendall(pickle.dumps("*#*#FILE_HASH#*#*"))
        final_hash = pickle.loads(my_socket.recv(4092))
        my_socket.sendall(pickle.dumps("*#*#FILE_NAME#*#*"))
        file_name = pickle.loads(my_socket.recv(4092))
        my_socket.sendall(pickle.dumps("*#*#BLOCK_SIZE#*#*"))
        block_size = pickle.loads(my_socket.recv(4092))
        my_socket.sendall(pickle.dumps("*#*#FILE_SIZE#*#*"))
        file_size = pickle.loads(my_socket.recv(4092))
        my_socket.sendall(pickle.dumps("*#*#END#*#*"))
        my_socket.close()

        file_name = os.path.join(Process.ensure_path_exists(save_dir), file_name)

        progress_queue = queue.Queue()
        saver_queue = queue.Queue()

        threads = []
        for port in ports:
            s = socket.socket()
            time.sleep(round(1073741824 / file_size, 3))
            s.connect((host, port))
            th = threading.Thread(target=Client.torrent_client, args=(s, progress_queue, saver_queue, block_size))
            th.start()
            threads.append(th)

        work = True

        if work:
            pass

        bar = threading.Thread(target=Process.update_progress_bar,
                               args=(len_blocks, progress_queue, "Получение файла", lambda work: work))
        saver = threading.Thread(target=Process.clear_operative_drive, args=(saver_queue,))

        bar.start()
        saver.start()

        start_time_download = time.perf_counter()
        for future in threads:
            future.join()

        work = False

        if work:
            pass

        bar.join()
        saver.join()

        end_time_download = time.perf_counter()
        start_time_joiner = time.perf_counter()

        Process.combine_chunks_from_directory("client_temp", file_name)

        file_hash = Process.calculate_file_hash(file_name)

        end_time_joiner = time.perf_counter()

        data_weight_bytes = os.path.getsize(file_name)

        data_weight_kbytes = data_weight_bytes / 1024
        data_weight_mbytes = data_weight_kbytes / 1024
        data_weight_gbytes = data_weight_mbytes / 1024

        print(TRANSLATOR.get_text("DataTransferCompleted"))
        data_weight, unit_w = Process.get_size_in_optimum_unit(data_weight_bytes, "", 1024)
        speed_d, unit_sd = Process.get_size_in_optimum_unit(
            data_weight_bytes / (end_time_download - start_time_download), "", 1024)
        speed_j, unit_sj = Process.get_size_in_optimum_unit(
            data_weight_bytes / (end_time_joiner - start_time_joiner), "", 1024)
        print(TRANSLATOR.get_text("DataReceivedWeight") % (str(data_weight) + unit_w))

        print(TRANSLATOR.get_text("TransferTime") % (str(end_time_download - start_time_download)))
        print(TRANSLATOR.get_text("DataTransferSpeed") % (str(speed_d) + unit_sd))
        print(TRANSLATOR.get_text("MergingSpeed") % (str(speed_j) + unit_sj))
        print(TRANSLATOR.get_text("HashCheck") % (str(file_hash) == str(final_hash)))

        Process.clear_temp_folder("client_temp", TRANSLATOR.get_text("ClearingCache"))

        my_socket.close()


if __name__ == '__main__':

    config = configparser.ConfigParser()
    # Читаем файл конфигурации
    config.read('config.ini')

    current_language = config.get('Languages', 'LANGUAGE', fallback="en")

    TRANSLATOR = Languages(current_language)

    print(TRANSLATOR.get_text("GetMode"))
    MOD = int(input(TRANSLATOR.get_text("GetOptions")))
    if MOD == 1:
        print(TRANSLATOR.get_text("ClientLoading"))

        # Извлекаем значения
        save_path = input(TRANSLATOR.get_text("EnterSavePath"))
        if save_path == "":
            SAVE_PATH = config.get('Settings client', 'SAVE_PATH', fallback=".")
        else:
            SAVE_PATH = save_path

        host_ip = input(TRANSLATOR.get_text("EnterServerIP"))
        if host_ip == "":
            HOST_IP = config.get('Settings client', 'HOST_IP', fallback="127.0.0.1")
        else:
            HOST_IP = host_ip

        host_port = input(TRANSLATOR.get_text("EnterMainPort"))
        if host_port == "":
            HOST_PORT = config.getint('Settings client', 'HOST_PORT', fallback=55001)
        else:
            HOST_PORT = int(host_port)

        del save_path
        del host_ip
        del host_port

        Client.receive_data(HOST_IP, HOST_PORT, SAVE_PATH)

    elif MOD == 2:
        print(TRANSLATOR.get_text("ServerLoading"))

        # Извлекаем значения

        file = input(TRANSLATOR.get_text("EnterSendFilePath"))
        if file == "":
            FILE = config.get('Settings server', 'FILE', fallback=".")
        else:
            FILE = file

        host_ip = input(TRANSLATOR.get_text("EnterServerIP"))
        if host_ip == "":
            HOST_IP = config.get('Settings server', 'HOST_IP', fallback="127.0.0.1")
        else:
            HOST_IP = host_ip

        host_port = input(TRANSLATOR.get_text("EnterMainPort"))
        if host_port == "":
            HOST_PORT = config.getint('Settings server', 'HOST_PORT', fallback=55001)
        else:
            HOST_PORT = int(host_port)

        max_ports = input(TRANSLATOR.get_text("EnterMaxPorts"))
        if max_ports == "":
            MAX_PORTS = config.getint('Settings server', 'MAX_PORTS', fallback=4)
        else:
            MAX_PORTS = int(max_ports)

        max_pack_size = input(TRANSLATOR.get_text("EnterMaxPacketSize"))
        if max_pack_size == "":
            MAX_PACKET_SIZE = config.getint('Settings server', 'MAX_PACKET_SIZE', fallback=4096)
        else:
            MAX_PACKET_SIZE = int(max_pack_size)

        del host_port
        del max_ports
        del max_pack_size
        del host_ip
        del file

        # Выводим значения
        print(TRANSLATOR.get_text("FilePath") % FILE)
        print(TRANSLATOR.get_text("PacketSize") % MAX_PACKET_SIZE)
        print(TRANSLATOR.get_text("HostIP") % HOST_IP)
        print(TRANSLATOR.get_text("HostPort") % HOST_PORT)
        print(TRANSLATOR.get_text("MaxPorts") % MAX_PORTS)
        asyncio.run(Server.start_send_data(FILE, HOST_IP, HOST_PORT,
                                           MAX_PORTS, MAX_PACKET_SIZE))
