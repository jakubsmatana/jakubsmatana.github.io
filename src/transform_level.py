import os
import json
import argparse
parser = argparse.ArgumentParser(description='Optional app description')
parser.add_argument('input_folder', type=str,
                    help='Folder name of the original maps in txt format.')
parser.add_argument('output_folder', type=str,
                    help='Folder name of the output folder.')

def parse_size(line):
    line = line.strip()
    line = line.split(",")
    try:
        number_one = int(line[0])
        number_two = int(line[1])
        return number_one == number_two, number_one
    except:
        return False, 0


def parse_cell(num, x, y):
    features = ['food', 'player', 'left', 'down', 'right', 'up']
    binary_str = bin(num)[2:]
    binary_str = binary_str.zfill(len(features))

    
    cell = {
        "x": x,
        "y": y,
        "walls": []
    }
    player = {}
    for bit, feature in zip(binary_str, features):

        if bit == '1':
            if feature == 'player':
                player = {
                    "x" : x,
                    "y" : y
                }
            elif feature == 'food':
                cell['food'] = True
            else:
                cell['walls'].append(feature)
    
    return cell, player if player else None


def parse_game(size, lines):
    food_count = 0
    game = { "gridSize" : size, "players": []}

    cells = []

    for index_y, y in enumerate(lines):
        line = y.strip().split(",")
        for index_x, x in enumerate(line):
            num = int(x)
            cell, player = parse_cell(num, index_x, index_y)
            if player is not None:
                game["players"].append(player)
            
            if "food" in cell.keys():
                food_count += 1
            cells.append(cell)

    game["cells"] = cells
    return game


if __name__ == "__main__":
    args = parser.parse_args()
    if not os.path.exists(args.input_folder):
        parser.error("Input folder does not exist.")
    if not os.path.exists(args.output_folder):
        os.makedirs(args.output_folder)
    files = os.listdir(args.input_folder)
    index = 1

    for item in [file for file in files if ".txt" in file.lower()]:
        
        with open(f"./{args.input_folder}/{item}", "r") as f:
            lines = f.readlines()
            is_valid_size, size = parse_size(lines[0])
            
            if not is_valid_size:
                continue

            game = parse_game(size, lines[1:size+1])
            pretty_json = json.dumps(game, indent=4)

            with open(f"./{args.output_folder}/map{index}.json", 'w') as json_file:
                json_file.write(pretty_json)

            index += 1
        
        