# coding:utf-8

# 功能: 用于检测ios app中定义但没有使用过的类（只区分系统类和用户自定义的类，第三方库也在扫描范围内）
#      可用于ci，较少包体积
# os version: 10.14.5
# xcode version: Version 10.3
# python version: python 3.7
# author: zhouyong
# date: 2019-08-15

# 使用方法：
# 运行此脚本: python3.7 /your/path/to/find_unused_oc_classes.py /your/path/to/app


import sys
import os
import re
import subprocess
from enum import Enum


class ReadState(Enum):
    Searching = 0x01
    SectionBegin = 0x11
    SectionEnd = 0x12


def read_section_data(txt_lines, section_name):
    class_dict = {}
    state = ReadState.Searching

    for line_index in range(len(txt_lines)):
        # section结束返回
        if state == ReadState.SectionEnd:
            return class_dict

        line = txt_lines[line_index]
        line_strip = line.strip()
        # 空行说明文件结束
        if len(line_strip) == 0:
            return class_dict

        if line.startswith('Contents of '):
            if line.find(section_name) != -1:
                state = ReadState.SectionBegin
                # print('line[%05d]: %s' % (line_index + 1, line))
            elif state == ReadState.SectionBegin:
                state = ReadState.SectionEnd
            continue

        if state != ReadState.SectionBegin:
            continue

        match_obj = re.match(r'^[0-9a-zA-Z]+\s0x[0-9a-zA-Z]+[\s\w]*', line)
        if match_obj:
            items = line_strip.split(' ')
            address = items[1]

            if len(items) < 3:
                # print('item length < 3')
                class_name = address
            else:
                class_name = adjust_class_name(items[2])

            # 0x0表明是系统类，非0x0表明是非系统类
            if address == '0x0':
                pass
            else:
                class_dict[class_name] = '1'
            # print('line[%05d] class_name: %s' %(line_index + 1, class_name))
            continue


# 去掉objc前缀
def adjust_class_name(name):
    if name.startswith('_OBJC_CLASS_$_'):
        return name[len('_OBJC_CLASS_$_'):]

    if name.startswith('_OBJC_METACLASS_$_'):
        return name[len('_OBJC_METACLASS_$_'):]


def createOCInfoFile(app_file_path):
    current_dir, full_file_name = os.path.split(app_file_path)
    file_name, file_ext = os.path.splitext(full_file_name)
    exec_file_path = app_file_path + '/' + file_name
    # print('file_name = %s, file_ext = %s, exec_file_path = %s' % (file_name, file_ext, exec_file_path))

    result = subprocess.Popen(['otool', '-v', '-o', exec_file_path], stdout=subprocess.PIPE)

    # 是b string 数组
    output = result.stdout.readlines()

    new_output = []
    for b_str in output:
        new_item = b_str.decode('ascii')
        new_output.append(new_item)
    # print('new_output = %s' % (new_output))

    output_file_name = file_name + '.txt'
    file = open(output_file_name, 'w', -1, 'utf8')
    file.writelines(new_output)
    file.flush()
    file.close()

    current_path = os.path.split(os.path.realpath(__file__))[0]
    return current_path + '/' + output_file_name


def parse_oc_txt_file(txt_file_path):
    file = open(txt_file_path, 'r')
    lines = file.readlines()
    file.close()

    class_names = read_section_data(lines, '__objc_classlist')
    ref_names = read_section_data(lines, '__objc_classrefs')
    superref_names = read_section_data(lines, '__objc_superrefs')
    all_ref_names = dict(ref_names, **superref_names)

    # print('before delete, class_names = %s' % class_names)
    # print('before delete, ref_names = %s' % all_ref_names)

    keys = list(class_names.keys())
    for key in keys:
        value = all_ref_names.get(key)
        if value is not None:
            del all_ref_names[key]
            del class_names[key]

    # print('after delete, class_names = %s' % class_names)
    # print('after delete, ref_names = %s' % all_ref_names)

    print('声明但未使用的类如下：（可考虑删除）')
    for key in class_names.keys():
        print('\t%s' % key)


if __name__ == '__main__':
    args = sys.argv

    macho_file_path = ''
    if len(args) > 1:
        macho_file_path = args[1]

    exists = os.path.exists(macho_file_path)
    if not exists:
        print('file not exist in path: %s' % exists)
        exit(1)

    file_path = createOCInfoFile(macho_file_path)
    print(file_path)

    parse_oc_txt_file(file_path)
