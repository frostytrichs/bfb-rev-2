import os

def list_files():
    """List all files in the current directory"""
    files = os.listdir('.')
    print("Files in current directory:")
    for file in files:
        print(f"- {file}")

def read_file(filename):
    """Read and print the contents of a file"""
    try:
        with open(filename, 'r') as f:
            content = f.read()
            print(f"\n--- Contents of {filename} ---\n")
            print(content)
            print(f"\n--- End of {filename} ---\n")
    except Exception as e:
        print(f"Error reading {filename}: {e}")

if __name__ == "__main__":
    list_files()
    
    # Try to read the uploaded files
    files_to_read = ['requirements.txt', 'config.ini', 'blueflagbot.py', 'bot.log']
    for file in files_to_read:
        read_file(file)