import os

if __name__ == '__main__':
    out_path = os.path.join(os.path.abspath('.'), 'package.redirects.conf')
    out_path2 = os.path.join(os.path.abspath('.'), 'package.redirects.conf.comp')

    def produce_lines(file_path, index):
        with open(file_path, 'r') as out_file:
            new_lines = []
            line_num = 0
            for line in out_file:
                line_num += 1
                if line_num < 3:
                    continue
                str = line[index:].split()[0]
                new_lines.append(str)
        return new_lines

    lines1 = produce_lines(out_path, 24)
    lines2 = produce_lines(out_path2, 27)
    print(f'Lines1 length: {len(lines1)}')
    print(f'Lines2 length: {len(lines2)}')
    lines1_cpy = list(lines1)
    lines2_cpy = list(lines2)

    for line in lines1:
        if line in lines2_cpy:
            lines2_cpy.remove(line)

    for line in lines2:
        if line in lines1_cpy:
            lines1_cpy.remove(line)

    print(f'Contained in cliv1 not in cliv2: {lines2_cpy}')
    print(f'Contained in cliv2 not in cliv1: {lines1_cpy}')

    print(f'CreateConfigSet in lines1: {"pinpoint-sms-voice-2018-09-05/CreateConfigurationSet$" in lines1}')


