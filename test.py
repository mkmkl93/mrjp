import sys
import os
import subprocess

dir_path = "lattests/"


def check_dir():
    check_good()
    check_bad()


def check_good():
    for file in os.listdir(dir_path + 'good/'):
        if file.endswith('.lat'):
            good = True
            process = subprocess.run(['./latc_ARCH', dir_path + 'good/' + file], stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, shell=False)
            if process.stdout != b'' or process.stderr != b'OK\n' or process.returncode != 0:
                good = False

            if good:
                print("\033[92m" + file + "\033[0m")
            else:
                print("\033[91m" + file + "\033[0m")
                print(process.stdout.decode("utf-8"))
                print(process.stderr.decode("utf-8"))


def check_bad():
    for file in os.listdir(dir_path + 'bad/'):
        if file.endswith('.lat'):
            good = False
            process = subprocess.run(['./latc_ARCH', dir_path + 'bad/' + file], stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, shell=False)
            if process.returncode == 0:
                good = True

            # print(process.stdout.decode("utf-8"))
            if good:
                print("\033[91m" + file + "\033[0m")
            else:
                print("\033[92m" + file + "\033[0m")


def check_ext():
    pass


def check_specific(choice, number):
    s = list(choice)
    s[-5] = str(number % 10)
    s[-6] = str((number // 10) % 10)
    s[-7] = str((number // 100) % 10)
    basename = ''.join(s)[:-4]
    process = subprocess.run(['cat', dir_path + basename + '.lat'], stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
    print(process.stdout.decode("utf-8"))
    process = subprocess.run(['./latc_ARCH', dir_path + basename + '.lat'], stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, shell=False)
    print('stdout: \n' + process.stdout.decode("utf-8"))
    print('stderr: ' + process.stderr.decode("utf-8"))

    process = subprocess.run(['./' + dir_path + basename], stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, shell=False)
    print('stdout: ' + process.stdout.decode("utf-8"))
    print('stderr: ' + process.stderr.decode("utf-8"))
    print('return code:' + str(process.returncode))

    with open(dir_path + basename + '.output') as file:
        file_content = ''.join([x for x in file])
        process_output = str(process.stdout.decode('utf-8'))

        if file_content != process_output or process.returncode != 0:
            print("\033[91m" + basename + "\033[0m")
        else:
            print("\033[92m" + basename + "\033[0m")


def main(argv):
    if len(argv) == 1:
        check_good()
        check_bad()
        check_ext()
    if len(argv) == 2:
        if argv[1] == 'g':
            check_good()
        elif argv[1] == 'b':
            check_bad()
        else:
            check_ext()
    if len(argv) == 3:
        if argv[1] == 'g':
            check_specific('good/core000.lat', int(argv[2]))
        if argv[1] == 'b':
            check_specific('bad/bad000.lat', int(argv[2]))


if __name__ == '__main__':
    main(sys.argv)
