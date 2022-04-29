#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals

import os
import datetime

from flight_info_tools.parse_filenames import *
from flight_info_tools.path_constants import ALLOWED_IMAGES_EXTENSIONS
from flight_info_tools.ReferenceFile import ReferenceFile
from common.startup.initialization import config
from .validator_gui import Ui_Dialog
from PySide2 import QtWidgets

MAX_UNREFERENCED_IMAGES_NUMBER = 5
DAY_PATTERN = r'^20[\d]{2}_[\d]{2}_[\d]{2}$'
GNSS_LOG_DIR_NAME = u'GNSS_log'


def safe_print(*args, **kwargs):
    try:
        print(*args, **kwargs)
    except UnicodeError:
        print('Failure! Unicode error.')

class StartWindow(QtWidgets.QDialog, Ui_Dialog):
    def __init__(self):
        super().__init__()
        self.ui = Ui_Dialog()
        self.setupUi(self)
        self.browse.clicked.connect(self.get_AFS)
        self.validateafs.clicked.connect(self.startValidating)

    def get_AFS(self):
        directory = QtWidgets.QFileDialog.getExistingDirectory(self, _("Select Directory to validate AFS"))
        self.lineEdit.setText(directory)

    def startValidating(self):
        path = self.lineEdit.text()
        timestr = datetime.datetime.now().strftime('%Y.%m.%d_%H.%M')
        try:
            path = path.decode('utf-8')
        except AttributeError:
            pass

        validateAFS(
            path,
            os.path.join(path, 'ErrorsInData%s.txt' % timestr),
            # rename=True
            rename=False
        )
        self.window().close()

class AFSDataValidator():
    def __init__(self, path, outpath, rename=False, validate=True, progress=None):
        self.path = os.path.abspath(path)
        self.outpath = os.path.abspath(outpath)
        self.rename = rename



        self.errors = dict()
        self.error_counter = None

        if progress:
            self.progress = progress

        else:
            self.progress = lambda x: None

        self.current_date_dir_path = None
        self.current_flight_dir_name = None
        self.current_flight_dir_path = None
        self.current_photo_dir_name = None
        self.current_photo_dir_path = None
        self.current_gcs_dir_path = None
        self.current_gnss_dir_path = None
        self.current_gnss_dir_name = None

        self.current_date = None
        self.current_fltype = None
        self.current_bortstr = None
        self.current_flnum = None

        if validate:
            self.validate()
            self.export_errors()





    @staticmethod
    def check_content_log_dir(path, year=None, parsed_cam=None):
# так случилось,
# что данные с бортовых приёмников стали конверитировать в rinex и скаладывать в папку rinex
# Теперь приходится просматривать файлы не только в GNSS_log, но и в rinex
        paths = list()
        paths.append(path)
        for dir in os.listdir(path):
            if dir.endswith('rinex'):
                paths.append(path + '\\' + dir)
                
        if not parsed_cam:
            parsed_cam = [u'', u'', u'', u'']
        if not year:
            year = datetime.datetime.now().year

        day, fltype, bort, flnum = parsed_cam

        str_year = str(year).zfill(4)[2:]

        rinex_o = (u'.%so' % str_year, '.obs')
        rinex_n = (u'.%sn' % str_year, '.nav')
        rinex_g = (u'.%sg' % str_year, '.nav')
        dat = u'.dat'
        marks = u'.marks'
        ps_file = (u'.tps', u'.jps', u'.ubx')

        ex_rin_o = None
        ex_rin_n = None
        ex_rin_g = None
        ex_rin_dat = None
        ex_rin_marks = None
        ex_ps_file = None

        bad_names = False

        checked_rinex = None
        for gnss_dir in paths:
            for f in os.listdir(gnss_dir):
                filestr = f.lower()
                if (day not in f or bort not in f or flnum not in f) and not f.startswith(u'sensors_'):
                    bad_names = True
                    safe_print(f)

                if filestr.endswith(rinex_o):
                    ex_rin_o = True
                    #checked_rinex = check_rinex_file(os.path.join(gnss_dir, filestr))
                if filestr.endswith(rinex_n):
                    ex_rin_n = True
                if filestr.endswith(rinex_g):
                    ex_rin_g = True
                if filestr.endswith(dat):
                    ex_rin_dat = True
                if filestr.endswith(marks):
                    ex_rin_marks = True
                if filestr.endswith(ps_file):
                    ex_ps_file = True

            files = []
            if not ex_rin_o:
                files.append(rinex_o)
            if not ex_rin_n:
                files.append(rinex_n)
            if not ex_rin_g:
                files.append(rinex_g)
            if not ex_rin_dat:
                files.append(dat)
            if not ex_rin_marks:
                files.append(marks)
            if not ex_ps_file:
                files.append(ps_file)

            res = []
            if files:
                mes = u'Не хватает файлов с такими расширениями: "' + str(files)
                res.append(mes)

            if bad_names:
                res.append(
                    u'Файл(ы) в папке называются неверно. Правильный префикс:"%s". ' % u'_'.join([day, bort, flnum]))
            if checked_rinex:
                res.append(checked_rinex)
        return u'. '.join(res)

    def rename_events(self, gnss_log_path, parsed_cam):
        day, fltype, bort, flnum = parsed_cam

        try:
            files = os.listdir(gnss_log_path)
        except OSError:
            return u'Нет папки "GNSS_log"'

        dat_files = []
        marks_files = []
        for f in files:
            name, ext = os.path.splitext(f)
            ext_low = ext.lower()
            if ext_low == u'.dat':
                dat_files.append(f)
            elif ext_low == u'.marks':
                marks_files.append(f)

        for f in dat_files:
            ev_fltype = MATCH_EVENTS_FLTYPE.get(fltype, None)
            if ev_fltype is None:
                continue
            if ev_fltype in f:
                s = os.path.join(gnss_log_path, f)
                d = os.path.join(gnss_log_path, u'_'.join([day, fltype, bort, flnum]) + u'.dat')
                message = 'Rename:\nFrom: %s\nTo:   %s\n' % (s, d)
                try:
                    safe_print(message)
                except IOError:
                    pass
                os.rename(s, d)

        for f in marks_files:
            ev_fltype = MATCH_EVENTS_FLTYPE[fltype]
            if ev_fltype in f:
                s = os.path.join(gnss_log_path, f)
                d = os.path.join(gnss_log_path, u'_'.join([day, fltype, bort, flnum]) + u'.marks')
                message = 'Rename:\nFrom: %s\nTo:   %s\n' % (s, d)
                try:
                    safe_print(message)
                except IOError:
                    pass
                os.rename(s, d)

    def check_events_existence(self, gnss_log_path, parsed_cam, rename=False):

        dat = False
        marks = False
        

        day, fltype, bort, flnum = parsed_cam
        bort = bort[4:]

        if day and fltype and bort and flnum:
            pass
        else:
            return u'День, тип, номер борта или номер полета не распознаны'

        if rename:
            self.rename_events(gnss_log_path, parsed_cam)

        try:
            files = os.listdir(gnss_log_path + '\\rinex')
        except OSError:
            return u'Нет папки "GNSS_log или rinex"'

        for f in files:
            if day in f and bort in f and flnum in f and fltype in f:
                name, ext = os.path.splitext(f)
                if ext.lower() == u'.dat':
                    dat = True
                elif ext.lower() == u'.marks':
                    marks = True
        if dat and marks:
            return
        else:
            return u'Файлы ивентов фотографирования не найдены'

    def check_kml_and_txt_existence(self, photo_dir_path, photo_base, rename=False):
        kml_u = photo_base + u'_.kml'
        kml = photo_base + u'.kml'
        txt_ps = photo_base + u'_photoscan.txt'
        txt_tl = photo_base + u'_telemetry.txt'
        txts = []
        kmls = []
        for photo in os.listdir(photo_dir_path):
            ext = os.path.splitext(photo)[1].lower()
            if ext == u'.txt':
                txts.append(photo)
            elif ext == u'.kml':
                kmls.append(photo)

        txt_exists = False
        for f in txts:
            if f == txt_ps or f == txt_tl:
                txt_exists = True
                txt = f

        kml_exists = False
        for f in kmls:
            if f == kml or f == kml_u:
                kml_exists = True
            else:
                if rename:
                    s = os.path.join(photo_dir_path, f)
                    d = os.path.join(photo_dir_path, kml)
                    os.rename(s, d)
                    kml_exists = True
        message = []

        if not kml_exists:
            message.append(u'Проблема с KML-файлом полетного задания')
        if txt_exists:
            txtpath = os.path.join(photo_dir_path, txt)
            res = check_txt_conformity(txtpath)
            if res:
                message.append(res)
        else:
            message.append(u'Проблема с TXT-файлом навигационных координат')

        if len(txts) > 1:
            message.append(u'В папке находятся несколько TXT-файлов')
        if len(kmls) > 1:
            message.append(u'В папке находятся несколько KML-файлов')
        return message

    def validate(self):
        daydirs = ((p, os.path.join(self.path, p)) for p in os.listdir(self.path))
        daydirs = list(filter(lambda x: os.path.isdir(x[1]), daydirs))
        self.errors[self.path] = []

        total_dirs = len(daydirs)

        counter = 0
        for daydir, daypath in daydirs:
            safe_print(daydir)
            # Проверка на формат папки-даты: "2017_01_30"
            f = re.search(DAY_PATTERN, daydir)
            if f and os.path.isdir(daypath):
                self.current_date = daydir
                self.current_date_dir_path = daypath
                self.validate_date_dir()
            else:
                self.errors[self.path].append(u'Папка или файл "%s" не является папкой-датой' % daydir)
            counter += 1
            self.progress(int(counter*100.0/total_dirs))
            safe_print()

    def validate_date_dir(self):
        path = self.current_date_dir_path

        basest = False

        self.errors[path] = self.errors.get(path, [])
        flightdirs = os.listdir(path)

        for flightdir in flightdirs:
            flightpath = os.path.join(path, flightdir)
            if not os.path.isdir(flightpath):
                self.errors[path].append(u'Файл "%s" не является папкой' % flightdir)
                continue

            if flightdir.lower().startswith(u'basest'):
                basest = True
                if flightdir != u'BaseSt':
                    self.errors[path].append(u'Папка "BaseSt" записана иначе: "%s"' % flightdir)
            else:
                self.current_flight_dir_name = flightdir
                self.current_flight_dir_path = flightpath
                self.validate_flight_folder()

        if not basest:
            self.errors[path].append(u'Папка "BaseSt" не найдена')

    def check_flight_folder_name(self):
        flightdir = self.current_flight_dir_name

        safe_print(flightdir)
        parsed = parse_afsfolder_string(flightdir)
        try:
            newstr = u'_'.join(parsed)
            self.current_fltype = parsed[3]
            self.current_flnum = parsed[1].lower()
            self.current_bortstr = convert_bortstr(parsed[0])
        except TypeError:
            self.errors[self.current_date_dir_path].append(u'Папка "%s" составлена неверно.' % flightdir)
            return False

        message = []
        if newstr[:-1] != flightdir:
            message.append(
                u'Папка "%s" составлена неверно. Возможно, должно быть так: "%s"' % (flightdir, newstr))
        if parsed[4]:
            print('Территории над которыми летали: ', parsed[4:])
        else:
            message.append(u'Не перечислены территории над которыми совершен полет: "%s"' %flightdir)
        if message:
            self.errors[self.current_date_dir_path].append(u', '.join(message))
        return True

    def validate_flight_folder(self):
        success = self.check_flight_folder_name()
        if success:
            flightpath = self.current_flight_dir_path
            dirs = os.listdir(flightpath)
            self.errors[flightpath] = []
            if not dirs:
                self.errors[flightpath].append(u'Пустая папка полета')
                return
            for d in dirs:
                if d in PHOTO_DIRS:
                    self.current_photo_dir_name = d
                    self.current_photo_dir_path = os.path.join(flightpath, d)
                    self.validate_photos_folder()
                elif d == u'GCS':
                    self.current_gcs_dir_path = os.path.join(flightpath, d)
                    self.validate_gcs_folder()
                elif d == u'GNSS_log':
                    self.current_gnss_dir_name = d
                    self.current_gnss_dir_path = os.path.join(flightpath, d)
                    self.validate_gnss_folder()
                else:
                    self.errors[flightpath].append(u'Недопустимое имя для папки с АФС: %s' % d)

    def find_photo(self, path):
        try:
            photo = sorted((i for i in os.listdir(path)[:20]
                            if os.path.splitext(i)[1].lower() in ALLOWED_IMAGES_EXTENSIONS))[9]
            return photo
        except IndexError:
            self.errors[self.current_photo_dir_path] = [u'В папке подозрительно мало снимков']
        return None

    def validate_photos_folder(self):
        ph_dir = self.current_photo_dir_path
        date_dir = self.current_photo_dir_name
        flightpath = self.current_flight_dir_path
        self.errors[ph_dir] = []
        photo = self.find_photo(ph_dir)
        if photo is None:
            return
        parsed_cam = parse_cam_name_string(photo)
        photo_base = u'_'.join(photo.split(u'_')[:-1])
        message = self.check_kml_and_txt_existence(ph_dir, photo_base, self.rename)
        if message:
            messagestr = u', '.join(message)
            self.errors[ph_dir] = [messagestr]

        cam_fltype = parsed_cam[1]
        matched_fltype = MATCH_PHOTOS_FLTYPE.get(cam_fltype)
        cam_flnum = parsed_cam[3]
        cam_bort = parsed_cam[2]
        cam_day = parsed_cam[0]

        if cam_bort and cam_day and cam_flnum and matched_fltype:
            events = self.check_events_existence(
                os.path.join(flightpath, u'GNSS_log'),
                parsed_cam,
                self.rename
            )
            if events:
                self.errors[flightpath].append(events)
        message = []
        fltype_from_phdir = MATCH_FLTYPE_BY_PHOTODIR[date_dir]
        if fltype_from_phdir and self.current_fltype and (fltype_from_phdir != cam_fltype):
            self.errors[ph_dir].append(
                u'Тип полета в названии фотографий "%s" '
                u'не соответствует названию папки "%s" '
                u'или неверно записан' % (cam_fltype, date_dir))
        if cam_bort != self.current_bortstr:
            if cam_bort:
                cam_bort = u'"%s"' % cam_bort
            else:
                cam_bort = u'иной вариант'
            message.append(u'№ борта: "%s", на камерах %s' % (self.current_bortstr, cam_bort))
        if not matched_fltype or (self.current_fltype not in matched_fltype):
            safe_print(parsed_cam)
            safe_print(matched_fltype)
            if matched_fltype:
                matched_fltype_str = u'"%s"' % (u'" или "'.join(matched_fltype))
            else:
                matched_fltype_str = u'иной вариант'
            message.append(u'тип полета: "%s", на камерах %s' % (self.current_fltype, matched_fltype_str))
        if cam_flnum != self.current_flnum:
            message.append(u'№ полета: "%s", на камерах %s' %
                           (self.current_flnum, u"%s" % (cam_flnum or u'иной вариант')))
        if cam_day != self.current_date:
            message.append(u'дата полета: %s, на камерах "%s"' %
                           (self.current_date, u"%s" % (cam_day or u'иной вариант')))

        if message:
            messagestr = u'Несоответствие названия папки и содержимого: '
            messagestr += u', '.join(message)
            self.errors[ph_dir].append(messagestr)

    def check_gcs_project_name(self, string):
        day, fltype, bort, flnum = parse_cam_name_string(string)
        
        if day == self.current_date and bort == self.current_bortstr and flnum == self.current_flnum:
            return
        else:
            self.errors[self.current_gcs_dir_path].append(r'Название проекта АФС (.gcs) некорректно')

    def validate_gcs_folder(self):
        gcs_path = self.current_gcs_dir_path
        self.errors[gcs_path] = []
        gcs_files = os.listdir(gcs_path)
        len_gcs = len(gcs_files)
        if len_gcs > 1:
            self.errors[gcs_path].append(u'Файлов в папке "GCS" больше одного: %s' % len_gcs)
        elif len_gcs < 1:
            self.errors[gcs_path].append(u'Папка "GCS" пуста')
            return
        gcs_exist = False
        for gcs_file in gcs_files:
            name, ext = os.path.splitext(gcs_file)
            if ext.lower() == u'.gcz':
                gcs_exist = True
                self.check_gcs_project_name(gcs_file)

        if not gcs_exist:
            self.errors[gcs_path].append(u'В папке "GCS" нет файла полетного задания')

    def validate_gnss_folder(self):
        gnss_path = self.current_gnss_dir_path
        daydir = self.current_date

        year = daydir[2:4]
        checked = self.check_content_log_dir(gnss_path, year)
        if checked:
            self.errors[gnss_path] = [checked]

    def export_errors(self):
        out = u'Путь\tОшибка\n'
        self.error_counter = 0
        for k, v in self.errors.items():
            if v:
                out += (u'\n'.join([u'\t'.join([k, i]) for i in v]) + u'\n')
                self.error_counter += len(v)
        version_path = os.path.join(
                                os.path.join(
                                    os.path.join(
                                        config.get('Paths', 'local_app_data'),
                                        'scripts'),
                                    ''),
            'version')

        with open(version_path, 'r', encoding='utf-8') as f:
            version = f.read()
        print(f'You are using AFSvalidator Plugin version: {version}')
        with open(self.outpath, 'wb') as f:
            f.write(f'Plugin version: {version}\n'.encode('utf-8'))
            f.write(out.encode('utf-8'))
        return out


def check_txt_conformity(txtpath):
    try:
        rf = ReferenceFile(txtpath)
    except UnicodeError as e:
        return 'Проблема с кодировкой файла: "{}". Сообщение ошибки:"{}"'.format(txtpath, e.message).replace('\n', ' ')

    images = [i for i in os.listdir(os.path.dirname(txtpath))
              if os.path.splitext(i)[1].lower() in ALLOWED_IMAGES_EXTENSIONS]

    errors_lst = []
    if len(images) - len(rf.cam_list) > MAX_UNREFERENCED_IMAGES_NUMBER:
        errors_lst.append('Количество фотографий без привязки в TXT-файле навигационных координат больше {}'.format(
            MAX_UNREFERENCED_IMAGES_NUMBER))

    dirname = os.path.dirname(txtpath)

    correct_paths = True
    for cam in rf.cam_list:
        cam_path = os.path.join(dirname, cam.name)
        if not os.path.isfile(cam_path):
            correct_paths = False
            break
    if not correct_paths:
        errors_lst.append('Не всем именам в TXT-файле навигационных координат найдено соответствие в папке')

    if errors_lst:
        errors_string = '. '.join(errors_lst)
        return errors_string

    return None


def convert_bortstr(string):
    """
    Function convert string like "G10108" to "g101b10108"
    :param string:
    :return string:
    """
    bort_num = string[1:]
    if bort_num.startswith(u'12'):
        btype = u'201'
    elif bort_num.startswith(u'1'):
        btype = u'101'
    elif bort_num.startswith(u'2'):
        btype = u'201'
    elif bort_num.startswith(u'4'):
        btype = u'401'
    elif bort_num.startswith(u'501'):
        btype = u'501'
    elif bort_num.startswith(u'7'):
        btype = u'701'
    elif bort_num.lower() == u'concept':
        btype = u'101'
        bort_num = u'01001'
    else:
        raise Exception(u'Unknown bort type! Bort: %s' % string)

    return u'g%sb%s' % (btype, bort_num)


def _rinex_event_string_to_date(string):
    lst = string.split('  ')[0].split(' ')
    y, mo, d, h, mi = [int(i) for i in lst[:-1]]
    y += 2000
    sec, microsec = [int(i) for i in lst[-1].split('.')]
    microsec = int(microsec / 10)
    date = datetime.datetime(y, mo, d, h, mi, sec, microsec)
    return date


def _rinex_parse_osbservation_start_and_stop(string):
    string = string.strip()
    lst = re.split(r' +', string)
    y, mo, d, h, mi = [int(i) for i in lst[:5]]
    sec, microsec = [int(i) for i in lst[5].split('.')]
    microsec = int(microsec / 10)
    data = datetime.datetime(y, mo, d, h, mi, sec, microsec)
    return data


def check_rinex_file(rinex_path):
    with open(rinex_path) as f:
        raw_data = f.read()

    if len(raw_data) < 10**6:
        return u'RINEX файл содержит подозрительно мало данных'

    header_part = raw_data[:15000]
    events_part = raw_data[(-10**6):]

    try:
        obsstart_template = r'  \d{4} +\d{1,2} +\d{1,2} +\d{1,2} +\d{1,2} +\d{1,2}.\d* +(GPS|GLONASS) +TIME OF FIRST OBS'
        obsstart = _rinex_parse_osbservation_start_and_stop(re.search(obsstart_template, header_part).group())

        obsfinish_template = r'  \d{4} +\d{1,2} +\d{1,2} +\d{1,2} +\d{1,2} +\d{1,2}.\d* +(GPS|GLONASS) +TIME OF LAST OBS'
        obsfinish = _rinex_parse_osbservation_start_and_stop(re.search(obsfinish_template, header_part).group())
    except AttributeError:
        return u'Не удалось найти начало и конец наблюдений в RINEX-файле'

    event_template = r" \d{2} \d{2} \d{2} \d{2} \d{2} \d{2}.\d*  5  0"
    matches = re.finditer(event_template, events_part)

    match_num = 0
    all_good = True
    for match_num, match in enumerate(matches):
        match_num = match_num + 1
        event_str = match.group().strip()
        event = _rinex_event_string_to_date(event_str)
        if event > obsfinish or event < obsstart:
            all_good = False

    if match_num == 0:
        return u'Ивенты (временные метки) не найдены в RINEX-файле'

    if not all_good:
        return u'Не все ивенты находятся внутри обозначенного в заголовке RINEX-файла промежутка'


def validateAFS(path, outpath, rename=False, progress=None):
    return AFSDataValidator(path, outpath, rename=rename, progress=progress).error_counter

def main(trans=None):
    if trans is not None:
        trans.install()
        _ = trans.gettext
    window = StartWindow()
    window.exec_()