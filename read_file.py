import sys

def read_file(filename):
    try:
        with open(filename, 'r') as f:
            content = f.read()
            print(content)
    except Exception as e:
        print(f"Error reading file {filename}: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        read_file(sys.argv[1])
    else:
        print("Please provide a filename")