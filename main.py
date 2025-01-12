import argparse


def parse_args():
    # Create the argument parser
    parser = argparse.ArgumentParser(description="Interpretation of flags and YouTube playlist link.")

    # Define flags
    parser.add_argument('--playlistLink', type=str, required=True, help="The YouTube playlist link.")
    parser.add_argument('--resultFormat', type=str, required=True, choices=['cmd', 'txt', 'json', 'mySQL', 'csv'],
                        help="The report format. Available options: cmd, txt, json, mySQL, csv.")
    parser.add_argument('--listMode', type=str, required=True, choices=['all', 'unavailable', 'available'],
                        help="The work mode. Available options: all, unavailable, available.")

    # Parse arguments
    args = parser.parse_args()

    # Return parsed arguments
    return args

def main():
    # Parse the arguments
    args = parse_args()

    # Interpret the arguments
    print(f"YouTube playlist link: {args.playlistLink}")
    print(f"Report format: {args.resultFormat}")
    print(f"List mode: {args.listMode}")


if __name__ == "__main__":
    main()
