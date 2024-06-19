from solver import find_path, Cell, Player, Switch, Gate, oppositeDirDic, directionDic, load_map, initializeGame, map_solution_to_keys, Players, CellGrid, Path
from typing import List, Dict, Any, TypedDict
import json
from random import randint, randrange, sample
from PIL import Image, ImageDraw, ImageFont
import copy
import os
import shutil
from itertools import product, combinations
import math

MapsDict = Dict[str, tuple[str, 'Map']]

class NonOptionalPositionElement(TypedDict):
    x: int
    y: int

class PositionElement(NonOptionalPositionElement, total=False):
    wall: str
    otherX: int
    otherY: int


teleport_image_path = './src/teleport.png'
teleport_image = Image.open(teleport_image_path)
cell_size = 120
teleport_img_size = int(cell_size * 0.6)
teleport_image = teleport_image.resize((teleport_img_size, teleport_img_size))
walls = ['up', 'down', 'left', 'right']
improved = ["Longer route", "Same length, different route", "Same route", "Shorter route"]


def input_int(message: str, min: int, max: int) -> int:
    while True:
        inp = input(message)
        if inp == "q":
            return -1
        if inp.isdigit():
            number = int(inp)
            if number >= min and number <= max:
                return number
            else:
                print(f"Number should be between {min} and {max}. \n")


def reset_color(grid: CellGrid):
    for i in range(len(grid)):
        for j in range(len(grid)):
            grid[i][j].reset_color()


def symm(cell: Cell, other_cell: Cell, wall: str, other_wall: str) -> int:
    return 1 if wall in cell.walls and other_wall in other_cell.walls else 0


def rotational_symmetry_score(grid: CellGrid, degrees: int) -> int:
    rotation_map = {'up': 'right', 'right': 'down', 'down': 'left', 'left': 'up'} if degrees == 90 else {'up': 'down', 'down': 'up', 'left': 'right', 'right': 'left'}
    size = len(grid)
    score = 0
    for y in range(1, size - 1):
        for x in range(1, size - 1):
            cell_walls = grid[y][x].walls
            rotated_walls = set(rotation_map[wall] for wall in cell_walls)
            if degrees == 90:
                new_x, new_y = size - y - 1, x
            elif degrees == 180:
                new_x, new_y = size - x - 1, size - y - 1
            
            for wall in rotated_walls:
                if wall in grid[new_y][new_x].walls:
                    score += 1
    return score


def symmetry_score(grid: CellGrid) -> int:
    size = len(grid)
    half = size // 2 if size % 2 == 1 else size // 2 - 1

    vertical_score = sum([
        symm(grid[i][index], grid[-(i + 1)][index], "down", "up") +
        symm(grid[i][index], grid[-(i + 1)][index], "right", "right") if index != size - 1 else 0 for i in range(half) for index in range(size)
    ])
    horizontal_score = sum([
        symm(grid[index][i], grid[index][-(i + 1)], "right", "left") +
        symm(grid[index][i], grid[index][-(i + 1)], "down", "down") if index != size - 1 else 0 for i in range(half) for index in range(size)
    ])

    score_90 = rotational_symmetry_score(grid, 90)

    score_180 = rotational_symmetry_score(grid, 180) // 2

    return horizontal_score + vertical_score + score_90 + score_180


def calculate_distance(p1: tuple[int, int], p2: tuple[int, int]) -> float:
    return math.sqrt((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2)


def food_score(grid: CellGrid) -> int:
    food_items = [(item.x, item.y) for row in grid for item in row if item.food]
    distances = [calculate_distance(p1, p2) for p1, p2 in combinations(food_items, 2)]
    return int(sum(distances) // len(distances)) if len(distances) != 0 else 0


def solvable_with_one_player(grid: CellGrid, players: Players) -> bool:
    for player in players:
        new_players = [player]
        if find_path(new_players, grid) is not None:
            return True
    return False


def prepare_folder(base_path: str, folder: str) -> None:
    path = f'./{base_path}/temp'
    folder_path = f'./{path}/{folder}'

    if os.path.exists(path):
        if os.path.exists(folder_path):
            shutil.rmtree(folder_path)
        os.makedirs(folder_path)
    else:
        os.makedirs(path)
        os.makedirs(folder_path)
    
    if not os.path.exists(f"{path}/combined"):
        os.makedirs(f"{path}/combined")
    

def get_food_position_score(grid: CellGrid, path: Path) -> int:
    for row in grid:
        for cell in row:
            if cell.color == "food":
                positions = [item for player in map_path_to_positions(path, [], True) for item in player]
                return 0 if (cell.x, cell.y) in positions else 1
    return 0


def get_teleport_score(grid: CellGrid) -> int:
    for row in grid:
        for cell in row:
            if cell.teleport is not None:
                return 1 if sorted([oppositeDirDic[item] for item in cell.walls]) == sorted(grid[cell.teleport["y"]][cell.teleport["x"]].walls) else 0
    return 0


def get_priority_score(grid: CellGrid, path: Path, type:str) -> int:
    if type == "food":
        return get_food_position_score(grid, path)
    elif type == "teleport":
        return get_teleport_score(grid)
    return 0


class Map:
    def __init__(self, grid: CellGrid, path: Path, improvement: int, players: Players, priority_score=0):
        self.grid = grid
        self.path = path
        self.improvement = improvement
        self.players = players
        self.priority_score = priority_score
        self.symm_score = symmetry_score(grid)
        self.food_score = food_score(grid)
        self.one_player_solvable = solvable_with_one_player(grid, players) if len(players) == 2 else True
        

    def get_items(self):
        return self.grid, self.path, self.players
    
    def get_grid(self):
        return self.grid
    

def export_players(players: Players):
    res = []
    for player in players:
        res.append({"x": player.x, "y": player.y})
    return res


def export_cells(grid: CellGrid):
    switch_gate = {}
    gate = []
    cells = []
    food_count = 0
    teleports = []

    result = {}

    for cell_row in grid:
        for cell in cell_row:
            new_cell = {"x": cell.x, "y": cell.y, "walls": list(cell.walls)}
            if cell.food:
                new_cell['food'] = True
                food_count += 1
            if cell.switch:
                switch_gate['switch'] = {"x": cell.x, "y": cell.y}
            if cell.gate:
                gate.append({"orientation": cell.gate.orientation, "x": cell.x, "y": cell.y})
            if cell.teleport:
                teleports.append({"x": cell.x, "y": cell.y})
            cells.append(new_cell)
    if len(gate) != 0:
        switch_gate["cells"] = gate
        result['gate'] = switch_gate
    if len(teleports) != 0:
        result['teleports'] = teleports
    
    result['cells'] = cells

    return result


def export_map(map: Any) -> Any:
    grid, _, players = map.get_items()
    exported = export_cells(grid)
    map = {
        "players": export_players(players),
        "gridSize": len(grid),
        "cells": exported['cells']
    }
    if "gate" in exported.keys():
        map["gate"] = exported['gate']
    if "teleports" in exported.keys():
        map["teleports"] = exported['teleports']

    return map


def draw_custom_rectangles(draw, x, y, cell_size):
    bottom_rect_width = cell_size // 5
    bottom_rect_height = cell_size // 12
    bottom_rect_x = (x * cell_size) + (cell_size - bottom_rect_width) // 2
    bottom_rect_y = (y * cell_size) + cell_size - bottom_rect_height - 1

    draw.rectangle([bottom_rect_x, bottom_rect_y, bottom_rect_x + bottom_rect_width, bottom_rect_y + bottom_rect_height], fill="brown")

    top_rect_width = cell_size // 20
    top_rect_height = cell_size // 6
    top_rect_x = bottom_rect_x + (bottom_rect_width - top_rect_width) // 2
    top_rect_y = bottom_rect_y - (top_rect_height)

    draw.rectangle([top_rect_x, top_rect_y, top_rect_x + top_rect_width, top_rect_y + top_rect_height], fill="grey")


def draw_dashed_line(draw, start, end, color, width=1, dash_length=10):
    x1, y1 = start
    x2, y2 = end
    dx = x2 - x1
    dy = y2 - y1
    distance = ((dx ** 2) + (dy ** 2)) ** 0.5
    dash_count = int(distance // dash_length)
    
    for i in range(dash_count):
        segment_start = (x1 + (dx / dash_count) * i, y1 + (dy / dash_count) * i)
        segment_end = (x1 + (dx / dash_count) * (i + 0.5), y1 + (dy / dash_count) * (i + 0.5))
        draw.line([segment_start, segment_end], fill=color, width=width)

    
def save_map_image(file_name: str, map: Map, show_path=True):

    grid, solved_map, players = map.get_items()


    size = len(grid)

    player_path = map_path_to_positions(solved_map, get_teleport_coords(map.get_grid()))


    wall_thickness = 4
    img_size = size * cell_size
    image = Image.new("RGB", (img_size, img_size), "white")
    draw = ImageDraw.Draw(image)


    for cell in [item for sublist in grid for item in sublist]:
        x, y = cell.x, cell.y
        walls = cell.walls
        food = cell.food


        top_left = (x * cell_size, y * cell_size)
        bottom_right = ((x + 1) * cell_size, (y + 1) * cell_size)


        if "left" in walls or x == 0: 
            draw.line([top_left, (top_left[0], bottom_right[1])], fill="orange" if cell.color == "left" else "black", width=wall_thickness)
        if "right" in walls or x == size - 1:  
            draw.line([(bottom_right[0], top_left[1]), bottom_right], fill="orange" if cell.color == "right" else "black", width=wall_thickness)
        if "up" in walls or y == 0:
            draw.line([top_left, (bottom_right[0], top_left[1])], fill="orange" if cell.color == "up" else "black", width=wall_thickness)
        if "down" in walls or y == size - 1:
            draw.line([(top_left[0], bottom_right[1]), bottom_right], fill="orange" if cell.color == "down" else "black", width=wall_thickness)


        if food:
            food_center = (x * cell_size + cell_size // 2, y * cell_size + cell_size // 2)
            draw.ellipse([food_center[0] - 12, food_center[1] - 12, food_center[0] + 12, food_center[1] + 12], fill="orange" if cell.color == "food" else "black")
        
        gate = cell.gate
        if gate:
            gate_orientation = gate.orientation
            if gate_orientation == "left":
                gate_start = (top_left[0], top_left[1])
                gate_end = (top_left[0], bottom_right[1])
            elif gate_orientation == "right":
                gate_start = (bottom_right[0], top_left[1])
                gate_end = (bottom_right[0], bottom_right[1])
            elif gate_orientation == "up":
                gate_start = (top_left[0], top_left[1])
                gate_end = (bottom_right[0], top_left[1])
            elif gate_orientation == "down":
                gate_start = (top_left[0], bottom_right[1])
                gate_end = (bottom_right[0], bottom_right[1])
            draw_dashed_line(draw, gate_start, gate_end, "red", wall_thickness // 2, 12)
        if cell.switch:
            draw_custom_rectangles(draw, x, y, cell_size)
        if cell.teleport:
            paste_x = (x * cell_size) + (cell_size - teleport_img_size) // 2
            paste_y = (y * cell_size) + (cell_size - teleport_img_size) // 2

            image.paste(teleport_image, (paste_x, paste_y), teleport_image)

    if show_path:
        for player in range(len(player_path)):
            for i in range(len(player_path[player]) - 1):
                first_middle = (player_path[player][i][0] * cell_size + cell_size // 2, player_path[player][i][1] * cell_size + cell_size // 2)
                second_middle = (player_path[player][i + 1][0] * cell_size + cell_size // 2, player_path[player][i + 1][1] * cell_size + cell_size // 2)
                wid = int(7 - 7 * (i/len(player_path[player])))
                if first_middle[0] == second_middle[0] or first_middle[1] == second_middle[1]:
                    draw.line([first_middle, second_middle], fill="blue" if player == 0 else "green", width=wid)

    for player in players:
        player_center = (player.x * cell_size + cell_size // 2, player.y * cell_size + cell_size // 2)
        draw.ellipse([player_center[0] - 20, player_center[1] - 20, player_center[0] + 20, player_center[1] + 20], fill="red")

    image.save(file_name)


def map_path_to_coordinates(item: Path, teleport: List[tuple[int, int]]) -> List[List[tuple[int, int]]]:
    teleport_present = len(teleport) == 2
    positions: List[List[tuple[int, int]]] = [[]] 

    if len(item[0]) == 2:
        positions.append([])

    for index in range(len(item) - 1):
        for i in range(len(item[index])):

            fromX = item[index][i]['x']
            fromY = item[index][i]['y']
            toX = item[index + 1][i]['x']
            toY = item[index + 1][i]['y']

            orient = item[index + 1][i].get('orient', '')

            step = 1 if orient == 'down' or orient == 'right' else -1
            if orient == 'down' or orient == 'up':
                if teleport_present:
                    y = fromY
                    if fromX != toX:
                        while (fromX, y) not in teleport:
                            positions[i].append((fromX, y))
                            y += step
                        positions[i].append((fromX, y))
                        (fromX, fromY) = [item for item in teleport if item != (fromX, y)][0]
                for y in range(fromY, toY, step):
                    positions[i].append((fromX, y))                   
            else:
                if teleport_present:
                    x = fromX
                    if fromY != toY:
                        while (x, fromY) not in teleport:
                            positions[i].append((x, fromY))
                            x += step
                        positions[i].append((x, fromY))    
                        (fromX, fromY) = [item for item in teleport if item != (x, fromY)][0]
                for x in range(fromX, toX, step):
                    positions[i].append((x, fromY))
 
    return positions


def map_path_to_positions(path: Path, teleport: List[tuple[int, int]], unique=False) -> List[List[tuple[int, int]]]:
    result = map_path_to_coordinates(path, teleport)

    if unique:
        return [list(set([item for row in result for item in row]))]
    
    for index, item in enumerate(path[-1]):
        result[index].append((item["x"], item["y"]))
    return result


def remove_adjacent_wall(position: PositionElement, positions: List[PositionElement]) -> List[PositionElement]:
    x, y = position.get("x", 0), position.get("y", 0)
    wall = position.get("wall", "")
    newX, newY = x + directionDic[wall][0], y + directionDic[wall][1]

    newWall = oppositeDirDic[wall]

    newPosition = {"x": newX, "y": newY, "wall": newWall}

    if newPosition in positions:
        positions.remove(newPosition)

    return positions


def generate_image(maps: MapsDict, base_path: str, type: str, init_map: bool):
    global map_save_index

    map_images = [Image.open(maps[i][0]) for i in maps.keys()]

    two_players = len(maps["0"][1].players) == 2

    img_width, img_height = map_images[0].size

    font_size = 18 + img_width // 240 * 3
    font = ImageFont.truetype("arial.ttf", font_size)

    combined_img = Image.new('RGB', (img_width * 4, img_height * 2 + 200), 'white')
    draw = ImageDraw.Draw(combined_img)

    for i, map_img in enumerate(map_images):
        x = (i % 4) * img_width
        y = (i // 4) * img_height + 100 if i > 3 else 0 
        combined_img.paste(map_img, (x, y))
        
        if init_map:
            label = f'Map {i}, Food score: {maps[str(i)][1].food_score}'
        elif i == 0:
            label = 'Base Map'
        else:
            label = f'Map {i}, {improved[maps[str(i)][1].improvement]}'
            if type == "food":
                label += f", Food on path score: {maps[str(i)][1].priority_score}"
            elif type == "teleport":
                label += f", Teleport score: {maps[str(i)][1].priority_score}"
        label2 =  f'Symmetry score: {maps[str(i)][1].symm_score}, Length: {len(maps[str(i)][1].path)}'
        if two_players:
            label2 += ", One player solvable: "
            label2 += "yes" if maps[str(i)][1].one_player_solvable else "no"
        text_x = x + 20
        text_y = y + img_height + 5

        draw.text((text_x, text_y), label, fill="black", font=font)
        draw.text((text_x, text_y + 50), label2, fill="black", font=font)

    combined_img.save(f'{base_path}/temp/combined/combined-{type}-{map_save_index}.png')
    combined_img.show()


def make_grid(size: int, prob: int) -> CellGrid:
    grid = [[Cell(x, y) for x in range(size)] for y in range(size)]
    for y in range(size):
        for x in range(size):
            cell = grid[y][x]
            if x == 0:
                cell.addWall("left")
            if x == size - 1:
                cell.addWall("right")
            if y == 0:
                cell.addWall("up")
            if y == size - 1:
                cell.addWall("down")
            for wall in walls:
                if not wall in cell.walls:
                    if randrange(100) < prob:
                        cell.addWall(wall)
                        newX, newY = x + directionDic[wall][0], y + directionDic[wall][1]
                        grid[newY][newX].addWall(oppositeDirDic[wall])
                        
    return grid


def abs_distance(first:tuple[int, int], second: tuple[int, int]) -> tuple[int, int]:
    return (abs(first[0] - second[0]), abs(first[1] - second[1]))


def generate_food_coords(foodSet: set[tuple[int, int]], size) -> tuple[int, int]:
    unique_row = {item[1] for item in foodSet}
    unique_col = {item[0] for item in foodSet}

    cond = len(unique_row) / size < 0.80 and len(unique_col) / size < 0.80
    while True:
        coords = (randint(0, size - 1), randint(0, size - 1))
        if cond:
            if coords[0] in unique_col or coords[1] in unique_row:
                continue
        dist = [abs_distance(item, coords) for item in foodSet]
        if (0, 0) not in dist and (0, 1) not in dist and (1, 0) not in dist:
            return coords


def make_random_map(base_path: str) -> bool:
    global map_save_index
    map_save_index = 1

    size = input_int("Enter a digit for map size (min 4, max 13): \n", 4, 13)
    if size == -1:
        return False
    player_count = input_int("Enter a digit for number of players (min 1, max 2): \n", 1, 2)
    if player_count == -1:
        return False
    food_count = input_int("Enter a digit for food count (min 1, max 20): \n", 1, 20)
    if food_count == -1:
        return False
    probability = input_int("Enter a digit for probability (min 1, max 40): \n", 1, 40)
    if probability == -1:
        return False

    grid = make_grid(size, probability)

    new_maps = []

    grid_backup = copy.deepcopy(grid)

    index = 0

    while len(new_maps) != 50:
        foodSet = set()
        while len(foodSet) != food_count:
            x, y = generate_food_coords(foodSet, len(grid))
            foodSet.add((x,y))
            grid[y][x].addFood()

        players = []

        while len(players) != player_count:
            x, y = randint(0, size - 1), randint(0, size - 1)
            if grid[y][x].food:
                continue
            players.append(Player(x, y))
        
        
        solved_map = find_path(players, grid)

        if solved_map is not None:
            new_maps.append(Map(grid, solved_map, 0, players))
            grid_backup = make_grid(size, probability)
            index = 0
    
        index += 1
        if index == 20:
            grid_backup = make_grid(size, probability)
            index = 0
        grid = copy.deepcopy(grid_backup)

    
    prepare_folder(base_path, "random")

    selected_maps = {}

    for index, value in enumerate(sorted(new_maps, key=lambda item: (len(item.path), item.symm_score + item.food_score), reverse=True)):
        # print(key)
        if index == 8:
            break
        
        grid, solved_map, players = value.get_items()

        path = f"{base_path}/temp/random/img{index}.png"
        selected_maps[str(index)] = (path, value)
        save_map_image(path, value)

    generate_image(selected_maps, base_path, "random", True)
    while True:
        inp = input("Select index of chosen map or press q to quit. \n")

        if inp in selected_maps.keys():
            grid, solved_map, players = selected_maps[inp][1].get_items()
            with open(f"{base_path}/map{map_save_index}.json", "w") as f:
                json.dump(export_map(selected_maps[inp][1]), f, indent=4)
            return True
        elif inp == 'q':
            return False


def init(base_path: str, map_name: str) -> tuple[CellGrid | None, Players | None, Any]:
    global map_save_index

    if not os.path.exists(base_path):
        os.makedirs(f'./{base_path}')
    if not os.path.exists(f"{base_path}/{map_name}"):
        while not make_random_map(f"{base_path}"):
            if input("Press q to quit making new map or any other key to continue. \n") == "q":
                return None, None, None
        

    map = load_map(f"{base_path}/{map_name}")

    grid, players = initializeGame(map)

    solved_map = find_path(players, grid)

    if solved_map is None:
        return None, None, None
    
    save_map_image(f"{base_path}/img{map_save_index}.png", Map(grid, solved_map, 0, players), False)
    map_save_index += 1

    return grid, players, map


def get_teleport_coords(grid: CellGrid) -> List[tuple[int, int]]:
    for row in grid:
        for cell in row:
            if cell.teleport:
                return [(cell.x, cell.y), (cell.teleport["x"], cell.teleport["y"])]
    return []


def has_switch_and_gate(grid:CellGrid) -> bool:
    return any([True for item in grid if any([True for x in item if x.gate])])


def has_teleports(grid:CellGrid) -> bool:
    return any([True for item in grid if any([True for x in item if x.teleport])])


def has_teleport_on_cells(grid: CellGrid, x: int, y: int, otherX: int, otherY: int) -> bool:
    size = len(grid)
    tcell = grid[y][x].teleport is not None
    if otherX >= 0 and otherX < size and otherY >= 0 and otherY < size:
        return tcell or grid[otherY][otherX].teleport is not None
    return tcell


def try_add_teleport(grid: CellGrid, x: int, y: int, otherX: int, otherY: int) -> bool:
    if x == otherX or y == otherY:
        return False
    port_one = {
        "x": x,
        "y": y
    }
    port_two = {
        "x": otherX,
        "y": otherY
    }

    grid[port_two["y"]][port_two["x"]].addTeleport(port_one)
    grid[port_one["y"]][port_one["x"]].addTeleport(port_two)

    return True


def try_add_gate(grid: CellGrid, x: int, y: int, otherX: int, otherY: int, wall: str, players: Players) -> bool:
    backup_grid = copy.deepcopy(grid)

    if try_add_wall(backup_grid, x, y, wall, players, False):
        path = find_path(players, backup_grid)
        if path is None:
            mySwitch = Switch(otherX, otherY)
            grid[mySwitch.y][mySwitch.x].addSwitch(mySwitch)

            grid[y][x].addGate(Gate(x, y, wall, mySwitch))
            newX, newY = x + directionDic[wall][0], y + directionDic[wall][1]
            grid[newY][newX].addGate(Gate(newX, newY, oppositeDirDic[wall], mySwitch))

            new_path = find_path(players, grid)
            return new_path is not None
    return False


def try_add_food(grid: CellGrid, players: Players, x: int, y: int) -> bool:
    if grid[y][x].food or grid[y][x].switch is not None or grid[y][x].teleport is not None:
        return False
    for player in players:
        if player.x == x and player.y == y:
            return False
    grid[y][x].addFood()
    grid[y][x].color = "food"
    return True


def try_add_wall(grid: CellGrid, x: int, y: int, orientation: str, players: Players, has_sg: bool) -> bool:
    shift = directionDic[orientation]
    otherX, otherY = x + shift[0], y + shift[1]

    if has_teleport_on_cells(grid, x, y, otherX, otherY) or orientation in grid[y][x].walls:
        return False

    grid[y][x].walls.add(orientation)
    grid[y][x].color = orientation

    grid[otherY][otherX].walls.add(oppositeDirDic[orientation])
    grid[otherY][otherX].color = oppositeDirDic[orientation]

    if has_sg:
        new_grid = copy.deepcopy(grid)
        return find_path(players, new_grid, True) is None

    return True


def try_add_element(grid: CellGrid, players: Players, type: str, position: PositionElement, has_sg: bool) -> bool:
    x, y = position.get("x", 0), position.get("y", 0)
    if type == "food":
        return try_add_food(grid, players, x, y)
    elif type == "wall":
        wall = position.get("wall", "")
        return try_add_wall(grid, x, y, wall, players, has_sg)
    elif type == "teleport":
        otherX, otherY = position.get("otherX", 0), position.get("otherY", 0)
        return try_add_teleport(grid, x, y, otherX, otherY)
    elif type == "gate":
        wall = position.get("wall", "")
        otherX, otherY = position.get("otherX", 0), position.get("otherY", 0)
        return try_add_gate(grid, x, y, otherX, otherY, wall, players)
    
    return False


def get_positions_for_type(type: str, path: Path, grid: CellGrid, players: Players) -> List[PositionElement]:
    players_coords = [(player.x, player.y) for player in players]
    if type == "food":
        return [{"x" : x, "y": y} for x in range(len(grid)) for y in range(len(grid)) if not grid[y][x].food and (x, y) not in players_coords]
    elif type == "wall":
        positions = map_path_to_positions(path, get_teleport_coords(grid), True)[0]
        temp = list(product(positions, walls))
        return [{"x" : pair[0], "y": pair[1], "wall": element} for pair, element in temp]
    elif type == "teleport":
        path_positions = map_path_to_positions(path, [], True)[0]
        positions = [(x, y) for x in range(len(grid)) for y in range(len(grid)) if not grid[y][x].food and (x, y) not in players_coords]
        temp = {tuple(sorted((first, second))) for first, second in product(positions, repeat=2) if first != second}
        result: List[PositionElement] = [{"x": first[0], "y": first[1], "otherX": second[0], "otherY": second[1]} for first, second in temp if first in path_positions or second in path_positions]
        return sample(result, 500) if len(result) > 500 else result
    elif type == "gate":
        positions = list(product(map_path_to_positions(path, [], True)[0], walls))
        temp = []
        cells_with_down_wall = [cell for row in grid for cell in row if "down" in cell.walls and not cell.food and (cell.x, cell.y) not in players_coords]

        for position in positions:
            temp += sample([{"x": position[0][0], "y": position[0][1], "wall": position[1], "otherX": item.x, "otherY": item.y} for item in cells_with_down_wall ], 5)
        return temp
     
    return []

    
def get_all_map_suggestions(grid:CellGrid, players: Players, base_path: str, type: str) -> MapsDict | None:
    path = find_path(players, grid)

    if path is None:
        return None
    base_map = Map(grid, path, 0, players)

    solved_map = map_solution_to_keys(path)
    global map_save_index
    new_grid = copy.deepcopy(grid)
    result: Dict[int, Map] = {}

    positions = get_positions_for_type(type, path, grid, players)
    priority_score = 0

    has_sg = has_switch_and_gate(grid)

    index = 0
    while positions:
        position = positions.pop()
        if try_add_element(new_grid, players, type, position, has_sg):
            if type == "wall":
                positions = remove_adjacent_wall(position, positions)
            priority_score = get_priority_score(new_grid, path, type)
            new_path = find_path(players, new_grid)
            new_solved_map = map_solution_to_keys(new_path)
            if new_solved_map != solved_map and new_path is not None and len(new_solved_map) >= len(solved_map):
                result[index] = Map(new_grid, new_path, 0 if len(new_solved_map) > len(solved_map) else 1, players, priority_score)
                index += 1
            elif new_path is not None:
                result[index] = Map(new_grid, new_path, 3 if len(new_solved_map) < len(solved_map) else 2, players, priority_score)
                index += 1
        new_grid = copy.deepcopy(grid)

    if not result:
        return None

    prepare_folder(base_path, type)

    selected_maps = {"0" : (f"{base_path}/temp/{type}/img0.png", base_map)}

    save_map_image(selected_maps["0"][0], selected_maps["0"][1])

    for index, (_, value) in enumerate(sorted(result.items(), key=lambda item: (item[1].priority_score, len(item[1].path), item[1].symm_score), reverse=True)):
        if index == 7:
            break
        
        grid, solved_map, players = value.get_items()

        selected_maps[str(index + 1)] = (f"{base_path}/temp/{type}/img{index + 1}.png", value)
        save_map_image(selected_maps[str(index + 1)][0], selected_maps[str(index + 1)][1])

    generate_image(selected_maps, base_path, type, False)
    return selected_maps


def select_map(suggestions: MapsDict, base_path: str, grid: CellGrid, map: Any) -> tuple[CellGrid, Any]:
    global map_save_index
    while True:
        inp = input("Select index of chosen map or press q to quit. \n")

        if inp in suggestions.keys():
            grid = suggestions[inp][1].get_grid()
            save_map_image(f"{base_path}/img{map_save_index}.png", suggestions[inp][1], False)
            reset_color(suggestions[inp][1].grid)
                            
            with open(f"{base_path}/map{map_save_index}.json", "w") as f:
                map = export_map(suggestions[inp][1])
                json.dump(map, f, indent=4)
            map_save_index += 1
            return grid, map
        elif inp == 'q':
            return grid, map


def add_wall(grid: CellGrid, players: Players, map: Any, base_path: str) -> tuple[CellGrid, Any]:
    global map_save_index
    suggestions = get_all_map_suggestions(grid, players, base_path, "wall")

    if suggestions is None:
        print("No more walls can be added to increase difficulty, returning...")
        return grid, map

    return select_map(suggestions, base_path, grid, map)


def add_food(grid: CellGrid, players: Players, map: Any, base_path: str) -> tuple[CellGrid, Any]:
    global map_save_index
    suggestions = get_all_map_suggestions(grid, players, base_path, "food")

    if suggestions is None:
        print("No more food can be added to increase difficulty, returning...")
        return grid, map

    return select_map(suggestions, base_path, grid, map)


def add_manual_wall(grid: CellGrid, players: Players, map: Any, base_path: str) -> CellGrid:
    global map_save_index
    new_grid = copy.deepcopy(grid)
    inp = input("Enter coordinates and wall orientation with spaces between, e.g.: \'0 1 right\' or q to quit. \n")

    inp = inp.split(" ")
    if not inp[0].isdigit() or not inp[1].isdigit() or inp[2] not in walls:
        print("Wrong input")
        return grid
    x = int(inp[0])
    y = int(inp[1])
    wall = inp[2]

    if x < 0 or x >= map["gridSize"] or y < 0 or y >= map["gridSize"]:
        print("Coordinations not in map.")
        return grid
    
    if wall in grid[y][x].walls:
        print("Wall is already present in the map.")
        return grid

    try_add_wall(new_grid, x, y, wall, players, has_switch_and_gate(grid))

    path = find_path(players, new_grid)

    if path is None:
        print("Map is unsolvable, reverting...")
        return grid

    map = Map(new_grid, path, 0, players)
    save_map_image(f"{base_path}/img{map_save_index}.png", map, False)
    reset_color(map.grid)
                    
    with open(f"{base_path}/map{map_save_index}.json", "w") as f:
        json.dump(export_map(map), f, indent=4)
    map_save_index += 1
    return new_grid


def add_teleport(grid: CellGrid, players: Players, map: Any, base_path: str) -> tuple[CellGrid, Any]:
    global map_save_index

    if has_teleports(grid):
        print("This map already contains pair of teleports.")
        return grid, map
    suggestions = get_all_map_suggestions(grid, players, base_path, "teleport")

    if suggestions is None:
        print("No more teleports can be added to increase difficulty, returning...")
        return grid, map

    return select_map(suggestions, base_path, grid, map)


def add_gate(grid: CellGrid, players: Players, map: Any, base_path: str) -> tuple[CellGrid, Any]:
    global map_save_index
    suggestions = get_all_map_suggestions(grid, players, base_path, "gate")

    if suggestions is None:
        print("No more switches and gates can be added to increase difficulty, returning...")
        return grid, map

    return select_map(suggestions, base_path, grid, map)


def set_last_map_number(base_path: str):
    global map_save_index
    if os.path.exists(base_path):
        files = os.listdir(base_path)
        index_list = [int(name.split(".json")[0][3:]) for name in files if ".json" in name]
        if len(index_list) == 0:
            return
        map_save_index = max(index_list)


def generate():
    base_path = input("Input the map folder path: \n")
    global map_save_index
    set_last_map_number(base_path)
    map_name = f"map{map_save_index}.json"
    print(base_path, map_name)
    loaded_map = True

    grid, players, map = init(base_path, map_name)

    while True:
        if grid is None:
            print("There is no map loaded, press n or c to continue")
            loaded_map = False
        else:
            loaded_map = True
        inp = input("Add wall: w, add manual wall: m, add food: f, add teleport: t, add switch and gate: g, show map: s, new map: n, change folder: c, quit: q \n")

        if inp == 'q':
            print("Ending...")
            return
        elif inp == 'm':
            if not loaded_map:
                continue
            if grid is not None and players is not None:
                grid = add_manual_wall(grid, players, map, base_path)
        elif inp == 'w':
            if not loaded_map:
                continue
            if grid is not None and players is not None:
                grid, map = add_wall(grid, players, map, base_path)
            if grid is None:
                return
        elif inp == 't':
            if not loaded_map:
                continue
            if grid is not None and players is not None:
                grid, map = add_teleport(grid, players, map, base_path)
            if grid is None:
                return
        elif inp == 'g':
            if not loaded_map:
                continue
            if grid is not None and players is not None:
                grid, map = add_gate(grid, players, map, base_path)
            if grid is None:
                return
        elif inp == "s":
            if not loaded_map:
                continue
            img = Image.open(f"./{base_path}/img{map_save_index - 1}.png")
            img.show()
            img.close()
        elif inp == "f":
            if not loaded_map:
                continue
            if grid is not None and players is not None:
                grid, map = add_food(grid, players, map, base_path)
        elif inp == "n":
            if input("Do you want to delete folder contains? y/n \n") == 'y':
                shutil.rmtree(base_path)
            map_save_index = 1
            map_name = f"map{map_save_index}.json"
            grid, players, map = init(base_path, map_name)
        elif inp == "c":
            base_path = "./" + input("Input new folder name: \n")
            if os.path.exists(base_path):
                if input(f"Do you want to delete folder: {base_path} contains? y/n \n") == 'y':
                    shutil.rmtree(base_path)
            else:
                os.makedirs(base_path)
            map_save_index = 1
            map_name = f"map{map_save_index}.json"
            grid, players, map = init(base_path, map_name)
        else:
            print("wrong command \n")

map_save_index = 1

if __name__ == "__main__":
    generate()
