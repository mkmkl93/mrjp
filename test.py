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
            process = subprocess.run(['python3', 'Latte.py', dir_path + 'good/' + file], stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE)
            if process.stdout != b'' or process.stderr != b'' or process.returncode != 0:
                good = False

            if good:
                print("\033[92m" + file + "\033[0m")
            else:
                print("\033[91m" + file + "\033[0m")
                print(process.stdout)
                print(process.stderr)


def check_bad():
    for file in os.listdir(dir_path + 'bad/'):
        if file.endswith('.lat'):
            good = False
            process = subprocess.run(['python3', 'Latte.py', dir_path + 'bad/' + file], stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, check=False)
            if process.returncode == 0:
                good = True

            if good:
                print("\033[91m" + file + "\033[0m")
            else:
                print("\033[92m" + file + "\033[0m")


def check_ext():
    pass


def main(argv):
    if len(argv) == 2:
        if argv[1] == 'g':
            check_good()
        elif argv[1] == 'b':
            check_bad()
        else:
            check_ext()
    if len(argv) == 1:
        check_good()
        check_bad()
        check_ext()


if __name__ == '__main__':
    main(sys.argv)
