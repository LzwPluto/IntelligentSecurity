from wakeup import Wakeup

def main():

    wakeup = Wakeup()

    while True:
        keyword = wakeup.wait()
        print(f"Wakeup: {keyword}")


if __name__ == "__main__":
    main()
