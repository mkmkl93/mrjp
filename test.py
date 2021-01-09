import sys
import os
import subprocess
import re

dir_path = "lattests/"


def check_dir():
    check_good()
    check_bad()


def check_good():
    cwd = os.getcwd()
    path = cwd + '/lattests/good/'
    files = os.listdir(path)
    files.sort(key=lambda f: os.stat(path + f).st_size)
    count = 0
    total_count = 0
    for file in files:
        if file.endswith('.lat'):
            total_count += 1
            m = re.match(r'core(\d*).*', file)

            count += check_specific('good/core000.lat', int(m.groups(1)[0]), 0)

    print("\033[94m" + 'Passes: {}/{}'.format(count, total_count) + "\033[0m")


def check_bad():
    cwd = os.getcwd()
    path = cwd + '/lattests/bad/'
    files = os.listdir(path)
    count = 0
    total_count=0
    for file in files:
        if file.endswith('.lat'):
            total_count += 1
            m = re.match(r'bad(\d*).*', file)

            count += check_specific('bad/bad000.lat', int(m.groups(1)[0]), 0)

    print("\033[94m" + 'Passes: {}/{}'.format(count, total_count) + "\033[0m")


def check_ext():
    pass


def debug(string, verbose):
    if verbose == 1:
        print(string)


def check_specific(choice, number, verbose=0):
    s = list(choice)
    s[-5] = str(number % 10)
    s[-6] = str((number // 10) % 10)
    s[-7] = str((number // 100) % 10)
    basename = ''.join(s)[:-4]
    process = subprocess.run(['cat', dir_path + basename + '.lat'], stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, encoding='utf-8')
    debug(process.stdout, verbose)
    try:
        process = subprocess.run(['./latc_x86_64', dir_path + basename + '.lat'], stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, encoding='utf-8', timeout=2)
    except subprocess.TimeoutExpired:
        return 0
    # debug('stdout: ' + process.stdout, verbose)
    # debug('stderr: ' + process.stderr, verbose)
    if process.returncode != 0 and 'core' in choice:
        debug('stderr: ' + process.stderr, verbose)
        print("\033[91m" + basename + "\033[0m")
        return 0
    debug(process.stderr, verbose)

    if 'good' in choice:
        if os.path.isfile('./' + dir_path + basename + '.input'):
            with open(dir_path + basename + '.input') as file:
                ins = ''.join([x for x in file])
        else:
            ins = ''

        try:
            process = subprocess.run(['./' + dir_path + basename], stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, shell=False, encoding='utf-8', input=ins, timeout=2)
        except subprocess.TimeoutExpired:
            return 0

        debug('stdout: ' + process.stdout, verbose)
        debug('stderr: ' + process.stderr, verbose)
        debug('return code: ' + str(process.returncode), verbose)

        with open(dir_path + basename + '.output') as file:
            file_content = ''.join([x for x in file])
            process_output = str(process.stdout)

            if file_content != process_output or (process.returncode != 0 and not process.stdout.endswith('runtime error\n')):
                print("\033[91m" + basename + "\033[0m")
                return 0
            else:
                print("\033[92m" + basename + "\033[0m")
                return 1
    else:
        with open(dir_path + basename + '.output') as file:
            file_content = ''.join([x for x in file])
            process_output = str(process.stderr)

            if file_content != process_output or (process.returncode == 0 or process.stdout.endswith('runtime error\n')):
                print("\033[91m" + basename + "\033[0m")
                return 0
            else:
                print("\033[92m" + basename + "\033[0m")
                return 1


def clean_test():
    cwd = os.getcwd()
    path = cwd + '/lattests/good/'
    files = os.listdir(path)
    for file in files:
        if file.endswith('.s') or '.' not in file:
            subprocess.run(['rm', path + file])


def main(argv):
    if len(argv) == 1:
        check_good()
        check_bad()
        check_ext()
    elif len(argv) == 2:
        if argv[1] == 'g':
            check_good()
        elif argv[1] == 'b':
            check_bad()
        elif argv[1] == 'clean':
            clean_test()
        else:
            check_ext()
    elif len(argv) == 3:
        if argv[1] == 'g':
            check_specific('good/core000.lat', int(argv[2]), 1)
        elif argv[1] == 'b':
            check_specific('bad/bad000.lat', int(argv[2]), 1)

    return 0

if __name__ == '__main__':
    main(sys.argv)
