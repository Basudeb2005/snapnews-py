import nltk

def download_nltk_packages():
    # Download necessary NLTK packages
    print("Downloading NLTK packages...")
    packages = ['punkt', 'punkt_tab']
    for package in packages:
        try:
            nltk.download(package)
            print(f"Successfully downloaded {package}")
        except Exception as e:
            print(f"Error downloading {package}: {e}")

if __name__ == "__main__":
    download_nltk_packages()
