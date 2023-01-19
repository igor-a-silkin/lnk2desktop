# lnk2desktop
 [![Python 3.7](https://img.shields.io/badge/python-3.7-blue.svg)](https://www.python.org/downloads/release/python-370/) [![Python 3.8](https://img.shields.io/badge/python-3.8-blue.svg)](https://www.python.org/downloads/release/python-380/) [![liblnk](https://img.shields.io/badge/requirements-liblnk-blue.svg)](https://github.com/libyal/liblnk) [![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black) [![License: MIT](https://img.shields.io/badge/License-MIT-blueviolet.svg)](https://github.com/igor-a-silkin/lnk2desktop/blob/main/LICENSE)
## Конвертер файлов ярлыков Windows *.url и *.lnk в формат *.desktop Linux

**lnk2desktop** - скрипт, написанный на языке Python 3.x, служит для конвертации файлов форматов Windows **.url** и **.lnk** в формат ярлыков **.desktop** Linux. При переходе с ОС Windows на Linux и переносе пользовательских данных, включая каталог "Рабочий стол", можно столкнуться с проблемой неработоспособности ярлыков, т.к. в Linux они имеют свой формат, отличный от Windows. Данный скрипт решает эту проблему.

## Установка
 Для парсинга проприетарного Windows формата *.lnk скрипт **lnk2desktop** использует библиотеки **liblnk-utils** и **liblnk1**. В большинстве дистрибутивов Linux с их установкой проблем не возникает, т.к. они входят в состав официального репозитория. Например, для Ubuntu установка данных библиотек сводится к запуску следующей команды:
```sh
sudo apt install liblnk-utils
```
Но для некоторых российских ОС, например, Astra Linux, необходимо вручную скачать и установить пакеты обоих библиотек (liblnk-utils зависит от liblnk1). Для Astra Linux понадобятся скачанные **.deb**-пакеты (подходят из Ubuntu), команда их установки выглядит следующим образом:
```sh
sudo dpkg -i liblnk1
sudo dpkg -i liblnk-utils
```
Далее **lnk2desktop** просто запускается как обычный Python-скрипт:

## Особенности
Скрипт имеет следующие параметры командной строки:
- **[-p]** - каталог для поиска и обработки файлов ярлыков Windows
- **[-d]** - флаг, указывающий обрабатывать или нет файлы в каталоге "Рабочий стол". По умолчанию "**да**" (при запуске без **-d**)

При запуске без параметров **lnk2desktop** ищет файлы *.url и *.lnk в текущем и в каталоге "Рабочий стол" пользователя и конвертирует их в формат *.desktop Linux, создавая файлы с теми же именами, но с расширением *.desktop.

Обработанные файлы перемещаются в каталог **backups_link** в профиле пользователя, в случае его отсутствия каталог будет создан. При этом для *.lnk-файлов скрипт пытается найти файл-источник, на который ссылается ярлык (атрибут Local path или Network path) и на его основе создает файл *.desktop.

## Лицензия

[MIT](https://github.com/igor-a-silkin/lnk2desktop/blob/main/LICENSE)
