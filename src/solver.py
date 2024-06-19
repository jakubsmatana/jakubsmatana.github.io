import json
import copy
import time
from typing import Any, Dict, List, TypedDict
import argparse
import os

parser = argparse.ArgumentParser(description='Optional app description')
parser.add_argument('input_folder', type=str,
                    help='Folder name of the maps to be solved.')
parser.add_argument('-m', '--map', type=str, help='Particular name of the map to solve.')
parser.add_argument('-o', '--output', type=str, help='Name of the output file, otherwise output will be printed.')


class NonOptionalPathElement(TypedDict):
    x: int
    y: int

class PathElement(NonOptionalPathElement, total=False):
    orient: str

Players = List['Player']
CellGrid = List[List['Cell']]
FoodSet = set[tuple[int, int]]
Path = List[List[PathElement]]


def load_map(filename: str) -> Any:
    with open(filename, 'r') as file:
        map_data = json.load(file)
    return map_data

directionDic: Dict[str, tuple[int, int]] = {"down": (0, 1), "up": (0, -1), "left": (-1, 0), "right": (1, 0)}
oppositeDirDic: Dict[str, str] = {"down": "up", "up": "down", "left": "right", "right": "left"}


class Solution:
    def __init__(self, players: Players, path: Path, foodSet: FoodSet, switch: bool, always_off_switch: bool):
        self.players = players
        self.path = path
        self.foodSet = foodSet
        self.switch = switch 
        self.always_off_switch = always_off_switch

    def addFood(self, foodItem: tuple[int, int]):
        self.foodSet.add(foodItem)
        self.foodSet = set(sorted(self.foodSet))
    
    def addToPath(self, orient: str):
        self.path.append([{"x": player.x, "y": player.y, "orient": orient} for player in sorted(self.players, key=lambda item: item.id)])

    def get_last_distance(self):
        if len(self.path) < 2:
            return 0
        first = self.path[-1][0]
        second = self.path[-2][0]
        return abs(first["x"] - second["x"]) + abs(first["y"] - second["y"])
   
    def __eq__(self, other):
        if isinstance(other, Solution):
            playersSorted = sorted(self.players, key=lambda item: (item.x, item.y))
            otherSorted = sorted(other.players, key=lambda item: (item.x, item.y))
            return (
                playersSorted == otherSorted and 
                self.foodSet == other.foodSet and
                self.path == other.path and
                self.switch == other.switch)
        
    def __le__(self, other) -> bool:
        if isinstance(other, Solution):
            playersSorted = sorted(self.players, key=lambda item: (item.x, item.y))
            otherSorted = sorted(other.players, key=lambda item: (item.x, item.y))
            return (
                    playersSorted == otherSorted and 
                    self.switch == other.switch and
                    self.foodSet.issubset(other.foodSet))
        return False
    
    def is_equal_or_subset(self, list_of_nodes: set['Solution']) -> bool:
        for item in list_of_nodes:
            if self <= item:
                return True
        return False
    
    def __hash__(self) -> int:
        playersTuple = tuple(sorted((player.x, player.y) for player in self.players))
        return hash((playersTuple, self.switch))
    
    def __repr__(self) -> str:
        arr = [x[0]['orient'] for x in self.path if "orient" in x[0]]
        return f'path:{", ".join(arr)}'
    
    def pathStr(self):
        return [path[0]["orient"] for path in self.path if "orient" in path[0]]


class MyQueue:

    def __init__(self, nodes, food_count):
        self.food_count = food_count
        self.nodes = nodes

    def __bool__(self):
        return not self.is_empty()
    
    def is_empty(self):
        return len(self.nodes) == 0

    def append(self, node):
        self.nodes.append(node)

    def popleft(self) -> Solution:
        self.nodes.sort(key=lambda node: (-len(node.foodSet)))
        return self.nodes.pop(0)   


def createGrid(size: int) -> CellGrid:
    grid = []
    for y in range(size):
        row = []
        for x in range(size):
            row.append(Cell(x, y))
        grid.append(row)
    return grid


def initializeGame(data: Any) -> tuple[CellGrid, Players]:

    grid = createGrid(data["gridSize"])

    # Place the player
    if "players" in data.keys():
        players = [Player(p["x"], p["y"]) for p in data["players"]]
        for index, item in enumerate(players):
            item.id = index

    if "teleports" in data.keys():
        port_one = {
            "x": data["teleports"][0]["x"],
            "y": data["teleports"][0]["y"]
        }
        port_two = {
            "x": data["teleports"][1]["x"],
            "y": data["teleports"][1]["y"]
        }
        grid[data["teleports"][1]["y"]][data["teleports"][1]["x"]].addTeleport(port_one)
        grid[data["teleports"][0]["y"]][data["teleports"][0]["x"]].addTeleport(port_two)
    
    for cell in data["cells"]:
        if "food" in cell.keys() and cell["food"]:
            grid[cell["y"]][cell["x"]].addFood()
        grid[cell["y"]][cell["x"]].addWalls(cell["walls"])

    # Place food, gates, and switches
    if "gate" in data.keys():
        mySwitch = Switch(data["gate"]["switch"]["x"], data["gate"]["switch"]["y"])
        grid[mySwitch.y][mySwitch.x].addSwitch(mySwitch)

        for gate in data['gate']['cells']:
            grid[gate['y']][gate["x"]].addGate(Gate(gate['x'], gate['y'], gate['orientation'], mySwitch))
    
    return grid, players
        

def isAnotherPlayerOnCell(x: int, y: int, player: 'Player', players: Players) -> bool:
    if len(players) > 1:
        filtered_players = [pl for pl in players if pl != player]
        return any(pl.x == x and pl.y == y for pl in filtered_players)
    return False


def sortedPlayers(players: Players, orientation: str) -> Players:
    if orientation == "right":
        return sorted(players, key=lambda player: player.x, reverse=True)
    elif orientation == "left":
        return sorted(players, key=lambda player: player.x)
    elif orientation == "down":
        return sorted(players, key=lambda player: player.y, reverse=True)
    elif orientation == "up":
        return sorted(players, key=lambda player: player.y)
    return players


def movePlayers(solution: Solution, orientation: str, grid: CellGrid) -> Solution:
    sortedPl = sortedPlayers(solution.players, orientation)
    
    for player in sortedPl:
        teleported = False
        while(True):
            newPosition = grid[player.y][player.x].move(player, orientation, teleported, grid, solution)
            if newPosition is not None:
                player.x = newPosition["cell"].x
                player.y = newPosition["cell"].y
                teleported = newPosition["teleported"]
                solution.switch = newPosition['switch']
            else:
                break
    return solution
    

class Cell:
    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y
        self.walls: set[str] = set()
        self.teleport = None
        self.switch = None
        self.gate = None
        self.food = False
        self.color = ""


    def reset_color(self):
        self.color = ""

    def move(self, player: 'Player', orientation: str, teleported: bool, grid: CellGrid, solution: Solution):

        if self.teleport is not None and not teleported:
            newX = self.teleport["x"]
            newY = self.teleport["y"]
            if isAnotherPlayerOnCell(newX, newY, player, solution.players):
                return None
            else:
                return {"cell": grid[newY][newX], "teleported": True, "switch": solution.switch}
            
        if self.gate is not None:
            sw = False if solution.always_off_switch else solution.switch
            orient = self.gate.getGateOrientation(sw)
            if orient and orient == orientation:
                return None
            
        newX = player.x + directionDic[orientation][0]
        newY = player.y + directionDic[orientation][1]

        if isAnotherPlayerOnCell(newX, newY, player, solution.players) or orientation in self.walls:
            return None
        
        nextCell = grid[newY][newX]

        if nextCell.food:
            solution.addFood((newX, newY))
        
        if self.switch is not None:
            solution.switch = not solution.switch

        return {"cell": nextCell, "teleported": False, "switch": solution.switch}

    def addGate(self, gate: 'Gate'):
        self.gate = gate

    def addSwitch(self, switch: 'Switch'):
        self.switch = switch

    def isTeleportActive(self, x: int, y: int) -> bool:
        if self.teleport is not None:
            return x == self.teleport.x and y == self.teleport.y
        
        return False
    

    def addTeleport(self, teleport):
        self.teleport = teleport
    

    def addWalls(self, walls: List[str]):
        if len(walls) == 0:
            return
        for item in walls:
            self.addWall(item)

    def addWall(self, wall: str):
        self.walls.add(wall)
    
    def addFood(self):
        self.food = True

    
class Player:
    def __init__(self, x: int, y: int):
        self.id = 0
        self.x = x
        self.y = y

    def __eq__(self, other):
        if not isinstance(other, Player):
            return NotImplemented
        return self.x == other.x and self.y == other.y

    def __hash__(self) -> int:
        return hash((self.x, self.y))


class Gate:
    def __init__(self, x: int, y: int, orientation: str, mySwitch: 'Switch'):
        self.x = x
        self.y = y
        self.orientation = orientation
        self.switch = mySwitch

    def getGateOrientation(self, switch: bool):
        if switch:
            return None
        
        return self.orientation
    

class Switch:
    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y
        self.isOn = False

    def isOpen(self):
        return self.isOn
    
    def toggleSwitch(self):
        self.isOn = not self.isOn
    

def count_food(grid: CellGrid) -> int:
    return sum([1 if item.food else 0 for row in grid for item in row])


def find_path(players: Players, grid: CellGrid, switch_always_off=False) -> Path | None:
    food_count = count_food(grid)
    path: List[PathElement] = [{"x": player.x, "y": player.y} for player in sorted(players, key=lambda item: item.id)]

    initial_state = Solution(players, [path], set(), False, switch_always_off)
    queue = MyQueue([initial_state], food_count)
    visited:set[Solution] = set()

    while queue:
        node = queue.popleft()

        if node.is_equal_or_subset(visited):
            continue
        visited.add(node)

        if len(node.foodSet) == food_count:
            return node.path

        for direction in ['up', 'down', 'left', 'right']:
            newState = movePlayers(copy.deepcopy(node), direction, grid)
            if newState == node:
                continue
            newState.addToPath(direction)
            queue.append(newState)
            
    return None


def map_path(solution: Path):
    return [item[0]['orient'] for item in solution if 'orient' in item[0]]


def map_solution_to_keys(solution: Path | None) -> List[str]:
    if solution == None:
        return []
    return map_path(solution)


def solveMap(base_path: str, map_name: str) -> List[str]:
    map = load_map(f"./{base_path}/{map_name}")
    grid, players = initializeGame(map)

    solved = find_path(players, grid)

    return map_solution_to_keys(solved)


def solve(base_path: str):
    maps = [file for file in os.listdir(base_path) if ".json" in file]
    result = {}
    for map in maps:
        temp = solveMap(base_path, map)
        result[map] = temp if temp is not None else []

    return result


if __name__ == "__main__":
    args = parser.parse_args()
    if not os.path.exists(args.input_folder):
        parser.error("Input folder does not exist.")
    if args.map:
        if not os.path.exists(f"{args.input_folder}/{args.map}"):
            parser.error("Map does not exist.")
        res = solveMap(args.input_folder, args.map)
        result = {args.map: res}
        if args.output:
            with open(args.output, "w") as f:
                json.dump(result, f)
        else:
            print(result)
    else:
        result = solve(args.input_folder)
        if args.output:
            with open(args.output, "w") as f:
                json.dump(result, f)
        else:
            print(result)


