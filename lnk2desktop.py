#!/usr/bin/python3
"""
Конвертирует файлы форматов *.url и *.lnk Windows в формат *.desktop Linux

Параметры:
    [-p]  -> Каталог для поиска и обработки файлов ярлыков Windows
    [-d]  -> Флаг, указывающий обрабатывать или нет файлы в каталоге "Рабочий 
    стол". По умолчанию "да" (при запуске без -d)

    При запуске без параметров ищет файлы *.url и *.lnk в текущем и в каталоге 
    "Рабочий стол" пользователя и конвертирует их в формат *.desktop Linux, 
    создавая файлы с теми же именами, но с расширением *.desktop.
    
    Обработанные файлы перемещает в каталог backups_link в профиле пользователя,
    в случае его отсутствия каталог будет создан. При этом для *.lnk-файлов 
    пытается найти файл-источник, на который ссылается ярлык (атрибут Local path
    или Network path) и на его основе создает файл *.desktop.

Функции:
    search_item(name, source_list, root_dir) -> string
    search_file_location(filename) -> tuple(string, string)
    get_file_name_or_path(row, splitter, logger) -> string
    prepare_lnk_desktop(link_dict, path, filename, pict, logger) -> dictionary
    write_desktop_link(link_dict, filename, logger) -> boolean
    analyze_lnk(filename, logger) -> tuple(dictionary, string)
    alalyze_url(line, filename, logger=None) -> dictionary
    move_lnk_file(filename, logger, backup_folder=BACKUP_FOLDER)
    get_desktop_folder(filename, logger) -> string
    search_files(template, ext, logger) -> integer
    create_logger(name=__name__) -> tuple(object, "")
    output_result(result, log_name)
    start(args)
"""


import argparse
import glob
import os
import subprocess
import re
import logging
import sys


URL_EXT: str = "*.url"
LNK_EXT: str = "*.lnk"
DESKTOP_EXT: str = ".desktop"
LOG_EXT: str = ".log"

EXTENSIONS = (URL_EXT, LNK_EXT)

LNKINFO: str = "lnkinfo"
CODEPAGE: str = "windows-1251"
LOCAL_PATH: str = "Local path"
NETWORK_PATH: str = "Network path"

USER_DIRS_FILE: str = ".config/user-dirs.dirs"
BACKUP_FOLDER: str = "backups_link"

DESKTOP_MASK: str = "XDG_DESKTOP_DIR="

OFFSET_OUTPUT: int = 4
OFFSET_OUTPUT_TWICE: int = 8
OFFSET_RESULT: int = 10

PICT_URL: str = "text-html"
PICT_FOLDER: str = "document-folder"

MSG_ERR_READ_LNK: str = "read_lnk_error"
MSG_ERR_LIB_NOT_FOUND: str = "liblnk_utils_not_found"
MSG_SUCCESS: str = "success_read_lnk"
MSG_FAIL: str = "common_fail"

NEED_INSTALL_MSG: str = """
    Возможно, на вашем компьютере отсутствует пакет liblnk-utils. Для его 
    установки используйте следующие команды:
    В Astra Linux необходимо скачать и установить вручную следующие пакеты:
    liblnk1
    liblnk-utils (зависит от liblnk1)
    Установка:
    sudo dpkg -i liblnk1
    sudo dpkg -i liblnk-utils

    В Debian (Ubuntu):
    sudo apt install liblnk-utils
    """

link = {
    "[Desktop Entry]": "",
    "Encoding": "UTF-8",
    "Name": "",
    "Type": "Link",
    "StartupNotify": "true",
    "URL": "",
    "Icon": "text-html",
    "Name[ru]": "",
    "NoDisplay": "false",
    "Hidden": "false",
}


def search_item(pattern, source_list, root_dir):
    """
    Возвращает найденный элемент (файл или каталог), соответствующий шаблону поиска

    Параметры:
        pattern (string)    - искомое имя файла или каталога
        source_list (list)  - список файлов или каталог, среди которых проводится поиск
        root_dir (string)   - каталог, в котором проводится поиск

    Возвращаемое значение:
        result (string)     - найденное имя файла или каталога
    """

    result = ""
    for item in source_list:
        if item == pattern:
            result = os.path.join(root_dir, item)
            break

    return result


def search_file_location(filename):
    """
    Возвращает кортеж с именем искомого файла или каталога и именем значка для него

    Параметры:
        filename (string)   - искомое имя файла или каталога

    Возвращаемое значение:
        (tuple)             - полный путь к найденному файлу и имя значка для него
    """

    pict = ""
    file_location = ""

    for root, dirs, files in os.walk(os.path.expanduser("~")):
        file_location = search_item(filename, files, root)
        if file_location == "":
            file_location = search_item(filename, dirs, root)
            if not file_location == "":
                pict = PICT_FOLDER

        if not file_location == "":
            break

    return (file_location, pict)


def get_file_name_or_path(row, splitter, logger):
    """
    Возвращает часть строки, содержащую имя файла, либо итоговый каталог без полного пути

    Параметры:
        row (string)        - путь к файлу или каталогу в формате Windows
        splitter (string)   - разделитель пути
        logger (object)     - объект Logger для логирования ошибок

    Возвращаемое значение:
        result (string)     - имя файла, либо итоговый каталог без полного пути
    """

    result = ""
    if not row == None:
        try:
            path_list = row.split(splitter)
            if len(path_list) >= 2:
                result = path_list[len(path_list) - 1].strip()
        except AttributeError as e:
            print(f"Ошибка при чтении ярлыка: {e.args}")
            logger.exception("AttributeError")
    return result


def prepare_lnk_desktop(link_dict, path, filename, pict, logger):
    """
    Возвращает заполненный словарь - шаблон для создания *.desktop-файла

    Параметры:
        link_dict (dictionary)  - словарь с параметрами *.desktop-файла
        path (string)           - путь к целевому объекту ярлыка
        filename (string)       - имя файла ярлыка
        pict (string)           - имя значка для типа ярлыка
        logger (object)         - объект Logger для логирования ошибок

    Возвращаемое значение:
        result (dictionary)     - заполенный словарь
    """

    result = None
    try:
        if not path == "" and not filename == "":
            link_dict["URL"] = path
            link_dict["Name"] = filename
            link_dict["Name[ru]"] = filename
            link_dict["Icon"] = pict
            result = link_dict
    except AttributeError as e:
        print(f"Ошибка при чтении ярлыка: {e.args}")
        logger.exception("AttributeError")
    return result


def write_desktop_link(link_dict, filename, logger):
    """
    Возвращает истину в случае успешного создания файла *.desktop

    Параметры:
        link_dict (dictionary)  - словарь с параметрами *.desktop-файла
        filename (string)       - имя файла ярлыка
        logger (object)         - объект Logger для логирования ошибок

    Возвращаемое значение:
        result (boolean)        - истина в случае успеха, иначе ложь
    """

    result = False
    try:
        if not link_dict == None:
            new_name = f"{os.path.splitext(filename)[0]}{DESKTOP_EXT}"
            with open(new_name, "w") as f:
                for key, value in link_dict.items():
                    if key == "[Desktop Entry]":
                        f.write(f"{key}\n")
                    else:
                        f.write(f"{key}={value}\n")
            logger.info(
                f'Файл "{filename}" успешно сконвертирован в "{new_name}"'
            )
            result = True
    except PermissionError:
        print(f'Ошибка при записи файла "{filename}": доступ запрещен!')
        logger.exception("PermissionError")
    except FileNotFoundError:
        print(
            f'Ошибка при записи файла "{filename}": нет такого файла или каталога!'
            )
        logger.exception("FileNotFoundError")
    except AttributeError as e:
        print(f'Ошибка при записи файла "{filename}": {e.args}')
        logger.exception("AttributeError")
    return result


def analyze_lnk(filename, logger):
    """
    Парсит файлы *.lnk и возвращает кортеж: заполненный словарь - шаблон для создания *.desktop-файла и строку с кодом ошибки

    Параметры:
        filename (string)       - имя файла ярлыка
        logger (object)         - объект Logger для логирования ошибок

    Возвращаемое значение:
        result (dictionary)     - заполенный словарь
    """

    result_link = None
    result_msg = MSG_FAIL
    if not filename == None:
        if os.path.exists(filename):
            try:
                link_info = subprocess.run(
                    [LNKINFO, "-c", CODEPAGE, filename],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    encoding="utf-8",
                )
                if link_info.returncode == 0:
                    link_info_list = link_info.stdout.split("\n")

                    for line in link_info_list:
                        row_line = r"" + line
                        if NETWORK_PATH in row_line:
                            full_path = get_file_name_or_path(row_line, ":", logger)
                            origin_name = get_file_name_or_path(full_path, "\\", logger)
                            result_link = prepare_lnk_desktop(
                                link, full_path, origin_name, PICT_URL, logger
                            )
                            result_msg = MSG_SUCCESS
                            break

                        elif LOCAL_PATH in row_line:
                            win_path = get_file_name_or_path(row_line, ":", logger)
                            origin_name = get_file_name_or_path(win_path, "\\", logger)
                            full_path, pict = search_file_location(origin_name)
                            result_link = prepare_lnk_desktop(
                                link, full_path, origin_name, pict, logger
                            )
                            result_msg = MSG_SUCCESS
                            break
                else:
                    result_msg = MSG_ERR_LIB_NOT_FOUND
                    print(f'Ошибка при чтении ярлыка "{filename}": {link_info.stderr}')
                    logger.exception(
                        f'Ошибка при чтении ярлыка "{filename}": {link_info.stderr}'
                    )
            except FileNotFoundError:
                result_msg = MSG_ERR_READ_LNK
                print(
                    f'Ошибка при запуске команды "{LNKINFO}": нет такого файла или каталога!\n{NEED_INSTALL_MSG}'
                )
                logger.exception("FileNotFoundError")
    return (result_link, result_msg)


def alalyze_url(row, filename, logger=None):
    """
    Парсит файлы *.url и возвращает заполенный словарь - шаблон для создания *.desktop-файла

    Параметры:
        row (string)            - строка для поиска URL
        filename (string)       - имя файла ярлыка
        logger (object)         - объект Logger для логирования ошибок

    Возвращаемое значение:
        result (dictionary)     - заполенный словарь
    """

    result = None
    try:
        if not row.strip().find("URL") == -1:
            address_list = row.strip().split("=")
            address = ""
            if len(address_list) == 2:
                address = address_list[1]
            name = os.path.splitext(os.path.basename(filename))[0]
            link["Name"] = name
            link["Name[ru]"] = name
            link["URL"] = address

            if not name == "" and not address == "":
                result = link
    except AttributeError:
        print("Ошибка при обработке файла!")
        logger.exception("AttributeError")

    return result


def move_lnk_file(filename, logger, backup_folder=BACKUP_FOLDER):
    """
    Перемещает обработанный файл *.url или *.lnk в каталог резервных копий, если каталога нет - создает

    Параметры:
        filename (string)       - имя файла ярлыка
        logger (object)         - объект Logger для логирования ошибок
        backup_folder (string)  - каталог для хранения резервных копий ярлыков Windows

    Возвращаемое значение:
        нет
    """

    backup_path = os.path.join(os.path.expanduser("~"), backup_folder)
    try:
        if not os.path.exists(backup_path):
            os.makedirs(backup_path)

        os.replace(filename, os.path.join(backup_path, os.path.basename(filename)))
        logger.info(
            f'Файл "{filename}" успешно обработан перемещен в каталог "{backup_path}"'
        )
    except PermissionError:
        print(f'Ошибка при создании каталога "{backup_path}": доступ запрещен!')
        logger.exception("PermissionError")
    except FileNotFoundError as e:
        print(
            f'Ошибка при перемещении файла "{filename}" в каталог "{backup_path}":\n{e.args}'
        )
        logger.exception("FileNotFoundError")


def get_desktop_folder(filename, logger):
    """
    Возвращает каталог "Рабочий стол" текущего пользователя, путем парсинга файла .config/user-dirs.dirs и чтения параметра XDG_DESKTOP_DIR

    Параметры:
        filename (string)   - полный путь к файлу .config/user-dirs.dirs
        logger (object)     - объект Logger для логирования ошибок

    Возвращаемое значение:
        result (string) - полный путь к каталогу "Рабочий стол" текущего 
        пользователя
    """

    result = ""
    try:
        with open(filename) as f:
            lines = f.readlines()
            regexp = r"".join(f"{DESKTOP_MASK}(?P<folder>.+)")
            try:
                for line in lines:
                    match = re.search(regexp, line)
                    if not match == None:
                        desktop_path_list = match.group("folder").strip('"').split("/")
                        home_dir = desktop_path_list[0].replace("$", "")
                        desktop_dir = desktop_path_list[len(desktop_path_list) - 1]
                        result = os.path.join(os.environ.get(home_dir), desktop_dir)
                        break
            except AttributeError:
                logger.exception("AttributeError")
    except PermissionError:
        print(f'Ошибка при чтении файла "{filename}": доступ запрещен!')
        logger.exception("PermissionError")
    except IOError as e:
        print(f'Ошибка при открытии файла "{filename}"!\n{e.args}')
        logger.exception("IOError")

    return result


def search_files(pattern, ext, logger):
    """
    Возвращает количество найденных и обработанных ярлыков Windows

    Параметры:
        pattern (string) - шаблон поиска: каталог, в котором производить поиск
        ext (string)     - расширение искомых файлов
        logger (object)  - объект Logger для логирования ошибок

    Возвращаемое значение:
        result (integer) - количество найденных и обработанных ярлыков Windows
    """

    result = 0
    try:
        files = glob.glob(pattern)
        for file in files:
            try:
                if ext == URL_EXT:
                    is_processed = False
                    with open(file) as f:
                        lines = f.readlines()
                        for line in lines:
                            link_fill = alalyze_url(line, file, logger)
                            if not link_fill == None:
                                is_processed = write_desktop_link(
                                    link_fill, file, logger
                                )
                                break
                    if is_processed:
                        move_lnk_file(file, logger)
                        result += 1

                elif ext == LNK_EXT:
                    result_link, result_msg = analyze_lnk(file, logger)
                    if result_msg == MSG_SUCCESS: 
                        if write_desktop_link(result_link, file, logger):
                            move_lnk_file(file, logger)
                            result += 1
                    elif result_msg == MSG_ERR_LIB_NOT_FOUND:
                        break
            except IOError as e:
                print(f'Ошибка при открытии файла "{file}"!\n{e.args}')
                logger.exception("IOError")
    except PermissionError:
        print(f"Ошибка при поиске файлов: доступ запрещен!")
        logger.exception("PermissionError")

    return result


def create_logger(name=__name__):
    """
    Возвращает кортеж из объекта логгера и его имени

    Параметры:
        name (string)           - имя, с которым будет создан логгер

    Возвращаемое значение:
        tuple(object, string)   - кортеж из объекта логгера и его имени
    """

    lnk_logger = logging.getLogger(name)
    lnk_logger.setLevel(logging.INFO)

    logger_name = f"{name}{LOG_EXT}"
    lnk_handler = logging.FileHandler(logger_name, mode="w")
    lnk_formatter = logging.Formatter("%(name)s %(asctime)s %(levelname)s %(message)s")

    lnk_handler.setFormatter(lnk_formatter)
    lnk_logger.addHandler(lnk_handler)

    lnk_logger.info(
        f'Запуск скрипта "{name}" для конвертации ярлыков Windows в формат Linux...'
    )

    return (lnk_logger, logger_name)


def output_result(output_result, log_name):
    """
    Выводит результаты работы скрипта на экран

    Параметры:
        output_result (list of strings) - список строк для вывода

    Возвращаемое значение:
        нет
    """

    print("Результат работы скрипта:")
    for folder, values in output_result.items():
        print(f'{" " * OFFSET_OUTPUT}Каталог "{folder}":')
        for ext, value in values.items():
            print(
                f'{" " * OFFSET_OUTPUT_TWICE}Обработано файлов {ext}:{value: {OFFSET_RESULT}}'
            )
        print("")
    print(f'Подробности в файле "{os.path.join(os.path.expanduser("~"), log_name)}"')


def start(args):
    """
    Точка входа в скрипт - инициализация переменных и запуск процедуры поиска файлов ярлыков

    Параметры:
        args (namespace) - заполенное пространство имен аргументов скрипта

    Возвращаемое значение:
        нет
    """

    logger, log_name = create_logger(os.path.splitext(sys.argv[0])[0])

    search_folders = []
    if not args.process_desktop:
        search_folders = [
            get_desktop_folder(
                os.path.join(os.path.expanduser("~"), USER_DIRS_FILE), logger
            )
        ]

    if not args.path == None:
        search_folders.append(f"{args.path}")
    else:
        search_folders.append(os.getcwd())

    result = {}
    for folder in search_folders:
        result[folder] = {}
        for ext in EXTENSIONS:
            result[folder][ext] = search_files(f"{folder}/{ext}", ext, logger)

    output_result(result, log_name)


parser = argparse.ArgumentParser(
    description="Скрипт для конвертации ярлыков Windows в формат Linux"
)
parser.add_argument(
    "-p", dest="path", help="Каталог для поиска и обработки файлов ярлыков Windows"
)
parser.add_argument(
    "-d",
    action="store_true",
    default=False,
    dest="process_desktop",
    help='Обрабатывать или нет файлы в каталоге "Рабочий стол". По умолчанию "да"',
)

parser.set_defaults(func=start)


if __name__ == "__main__":
    args = parser.parse_args()
    args.func(args)
