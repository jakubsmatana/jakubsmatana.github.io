const mapGrid = document.getElementById('mapGrid');
let gridSize = 6; 
let currentPlayers = [];
let currentTeleports = [];
let currentFoods = [];
let currentGates = [];
let switchCell;
const directionDic = {"down": [0,1], "up": [0,-1], "left": [-1,0], "right": [1,0]}
const oppositeDirDic= {"down": "up", "up": "down", "left": "right", "right": "left"}

function createGrid(size) {
    gridSize = size;
    var width = document.getElementById('mapGrid').offsetWidth;
    const cellSize = width / gridSize;
    mapGrid.style.gridTemplateColumns = `repeat(${gridSize}, ${cellSize}px)`;
    mapGrid.style.gridTemplateRows = `repeat(${gridSize}, ${cellSize}px)`;

    for (let y = 0; y < gridSize; y++) {
        for (let x = 0; x < gridSize; x++) {
            const cell = document.createElement('div');
            cell.classList.add('grid-cell');
            cell.dataset.x = x;
            cell.dataset.y = y;

            if (x === 0) cell.classList.add('has-left-wall');
            if (x === gridSize - 1) cell.classList.add('has-right-wall');
            if (y === 0) cell.classList.add('has-up-wall');
            if (y === gridSize - 1) cell.classList.add('has-down-wall');

            mapGrid.appendChild(cell);
        }
    }
}

createGrid(gridSize);

window.updateGridSize = function (){
    const newSize = parseInt(document.getElementById('gridSizeInput').value, 10);
    if (newSize && newSize > 0) {
        gridSize = newSize;
        mapGrid.innerHTML = '';
        createGrid(gridSize);
    }
}

let selectedTool = 'wall'; 
let selectedOrientation = '';
const selectedToolDisplay = document.getElementById('selectedToolDisplay');

function updateSelectedTool(toolName) {
    selectedTool = toolName;
    selectedToolDisplay.textContent = `Selected Tool: ${selectedTool}`;
}

function updateSelectedOrientation(orientation) {
    selectedOrientation = orientation;
    selectedToolDisplay.textContent = `Selected Tool: ${selectedTool}, Orientation: ${selectedOrientation}`;
}

updateSelectedTool('None');

document.getElementById('toolSelector').addEventListener('change', function() {
    updateSelectedTool(this.value);
    const orientationDiv = document.getElementById('orientationSelector');


    if (selectedTool === 'wall' || selectedTool === 'gate') {
        orientationDiv.style.display = 'block';
        updateSelectedOrientation('up');
    } else {
        orientationDiv.style.display = 'none';
    }
});

document.getElementById('orientation').addEventListener('change', function() {
    updateSelectedOrientation(this.value);
});

document.getElementById('importMap').addEventListener('click', () => {
    const fileInput = document.getElementById('jsonFileInput');
    const file = fileInput.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = (e) => {
            try {
                const mapData = JSON.parse(e.target.result);
                loadMap(mapData);
            } catch (e) {
                console.error('Invalid JSON:', e);
            }
        };
        reader.readAsText(file);
    }
});

function loadMap(mapData) {
    mapGrid.innerHTML = '';

    createGrid(mapData.gridSize);
    currentPlayers = [];
    currentTeleports = [];
    currentFoods = [];
    currentGates = [];
    switchCell = null;

    mapData.cells.forEach(cellData => {
        const cell = document.querySelector(`.grid-cell[data-x="${cellData.x}"][data-y="${cellData.y}"]`);
        if (cell) {
            if (cellData.walls.includes('left')) cell.classList.add('has-left-wall');
            if (cellData.walls.includes('right')) cell.classList.add('has-right-wall');
            if (cellData.walls.includes('up')) cell.classList.add('has-up-wall');
            if (cellData.walls.includes('down')) cell.classList.add('has-down-wall');

            if (cellData.food){
                cell.classList.add('has-food');
                currentFoods.push(cell);
            }    

        }
    });

    currentPlayers = [];
    mapData.players.forEach(player => {
        const cell = document.querySelector(`.grid-cell[data-x="${player.x}"][data-y="${player.y}"]`);
        cell.classList.add('has-player');
        currentPlayers.push(cell);
    });

    if(mapData.teleports != null){
        const fromX = mapData.teleports[0].x;
        const fromY = mapData.teleports[0].y;
        const toX = mapData.teleports[1].x;
        const toY = mapData.teleports[1].y;
        const cellFrom = document.querySelector(`.grid-cell[data-x="${fromX}"][data-y="${fromY}"]`);
        const cellTo = document.querySelector(`.grid-cell[data-x="${toX}"][data-y="${toY}"]`);

        cellFrom.classList.add('has-teleport');
        cellTo.classList.add('has-teleport');
        currentTeleports = [cellFrom, cellTo];
    }

    if(mapData.gate != null){
        const cellOne = document.querySelector(`.grid-cell[data-x="${mapData.gate.cells[0].x}"][data-y="${mapData.gate.cells[0].y}"]`);
        const cellTwo = document.querySelector(`.grid-cell[data-x="${mapData.gate.cells[1].x}"][data-y="${mapData.gate.cells[1].y}"]`);
        cellOne.classList.add(`has-${mapData.gate.cells[0].orientation}-gate`);
        cellTwo.classList.add(`has-${mapData.gate.cells[1].orientation}-gate`);
        switchCell = document.querySelector(`.grid-cell[data-x="${mapData.gate.switch.x}"][data-y="${mapData.gate.switch.y}"]`);
        switchCell.classList.add('has-switch');

        currentGates = [cellOne, cellTwo];
    }
}


mapGrid.addEventListener('click', (event) => {
    if (event.target.classList.contains('grid-cell')) {
        const cell = event.target;
        const x = parseInt(cell.dataset.x, 10);
        const y = parseInt(cell.dataset.y, 10);

        switch (selectedTool) {
            case 'wall':
                toggleWall(cell, x, y, selectedOrientation);
                break;
            case 'food':
                if(cell.classList.contains('has-teleport') || cell.classList.contains('has-player') || cell.classList.contains('has-switch')){
                    break;
                }
                if (cell.classList.contains('has-food')) {
                    cell.classList.remove('has-food');
                    currentFoods = currentFoods.filter(p => p !== cell);
                }
                else{
                    cell.classList.add('has-food');
                    currentFoods.push(cell);
                }
                break;
            case 'player':
                if(cell.classList.contains('has-food') || cell.classList.contains('has-teleport') || cell.classList.contains('has-switch')){
                    break;
                }
                if (cell.classList.contains('has-player')) {
                    cell.classList.remove('has-player');
                    currentPlayers = currentPlayers.filter(p => p !== cell);
                } else if (currentPlayers.length < 2) {
                    cell.classList.add('has-player');
                    currentPlayers.push(cell);
                } else {
                    const oldestPlayerCell = currentPlayers.shift();
                    oldestPlayerCell.classList.remove('has-player');
                    cell.classList.add('has-player');
                    currentPlayers.push(cell);
                }
                break;
            case 'teleport':
                if(cell.classList.contains('has-food') || cell.classList.contains('has-player') || cell.classList.contains('has-switch')){
                    break;
                }
                if (cell.classList.contains('has-teleport')) {
                    cell.classList.remove('has-teleport');
                    currentTeleports = currentTeleports.filter(p => p !== cell);
                } else if (currentTeleports.length < 2) {
                    cell.classList.add('has-teleport');
                    currentTeleports.push(cell);
                } else {
                    const oldestTeleportCell = currentTeleports.shift();
                    oldestTeleportCell.classList.remove('has-teleport');
                    cell.classList.add('has-teleport');
                    currentTeleports.push(cell);
                }
                break;
            case 'switch':
                if(cell.classList.contains('has-food') || cell.classList.contains('has-player') || cell.classList.contains('has-teleport')){
                    break;
                }
                if(switchCell == cell){
                    switchCell = null;
                }
                else if (switchCell == null){
                    switchCell = cell;
                }
                else{
                    switchCell.classList.toggle("has-switch");
                    switchCell = cell;
                }
                cell.classList.toggle("has-switch");
                break;
            case 'gate':
                toggleGate(cell, x, y, selectedOrientation);
                break;
    }
    }
});

function toggleGate(cell, x, y, orientation){
    if((x == 0 && orientation == "left") || (x == gridSize - 1 && orientation == "right") || (y == 0 && orientation == "up") || (y == gridSize - 1 && orientation == "down")){
        return;
    }
    if(cell.classList.contains(`has-${orientation}-wall`)){
        return;
    }
    let newX = x + directionDic[orientation][0];
    let newY = y + directionDic[orientation][1];
    const anotherCell = document.querySelector(`.grid-cell[data-x="${newX}"][data-y="${newY}"]`);


    if (currentGates.includes(cell)){
        if(currentGates[0] == cell && currentGates[0].classList == cell.classList && currentGates[1] == anotherCell && currentGates[1].classList == anotherCell.classList){
            currentGates = [];
        }
        else if(currentGates[1] == cell && currentGates[1].classList == cell.classList && currentGates[0] == anotherCell && currentGates[0].classList == anotherCell.classList){
            currentGates = [];
        }else{
            currentGates.forEach(element => {
                element.classList.remove.apply(element.classList, Array.from(element.classList).filter(v=>v.includes("gate")));
            });
            currentGates = [cell, anotherCell];
        }
    }
    else{
        currentGates.forEach(element => {
            element.classList.remove.apply(element.classList, Array.from(element.classList).filter(v=>v.includes("gate")));
        });
        currentGates = [cell, anotherCell];
    }
    cell.classList.toggle(`has-${orientation}-gate`)
    anotherCell.classList.toggle(`has-${oppositeDirDic[orientation]}-gate`)
}

function toggleWall(cell, x, y, orientation) {
    if((x == 0 && orientation == "left") || (x == gridSize - 1 && orientation == "right") || (y == 0 && orientation == "up") || (y == gridSize - 1 && orientation == "down")){
        return;
    }
    if(cell.classList.contains(`has-${orientation}-gate`)){
        return;
    }
    cell.classList.toggle(`has-${orientation}-wall`)
    let newX = x + directionDic[orientation][0];
    let newY = y + directionDic[orientation][1];
    const anotherCell = document.querySelector(`.grid-cell[data-x="${newX}"][data-y="${newY}"]`);
    anotherCell.classList.toggle(`has-${oppositeDirDic[orientation]}-wall`)

}

document.getElementById('displayMapData').addEventListener('click', () => {
    let mapData = getMapData();
    const formattedJSON = formatJSONFirstLevel(mapData);
    const mapDataDisplay = document.getElementById('mapDataDisplay');
    mapDataDisplay.textContent = formattedJSON;
    console.log(formattedJSON);
});


function getMapData(){
    const mapData = {
        gridSize: gridSize,
        players: [],
        cells: []
    };

    
    if(currentFoods.length == 0 || currentPlayers.length == 0){
        return {
            "error": "There has to be at least one player and one food item to display map data."
        };
    }
    if(
     (currentPlayers.length == 2 && currentTeleports.length == 2) ||
     (currentGates.length == 2 && switchCell != null && currentTeleports.length == 2) ||
     (currentPlayers.length == 2 && currentGates.length == 2 && switchCell != null)){
        return {
            "error": "Maximum one of three extensions can be exported."
        };
    }

    let gate = {'cells': [], switch: {}}

    document.querySelectorAll('.grid-cell').forEach(cell => {
        const x = parseInt(cell.dataset.x, 10);
        const y = parseInt(cell.dataset.y, 10);
        let cellWalls = [];
        if(cell.classList.contains('has-left-wall')){
            cellWalls.push("left");
        }
        if(cell.classList.contains('has-right-wall')){
            cellWalls.push("right");
        }
        if(cell.classList.contains('has-up-wall')){
            cellWalls.push("up");
        }
        if(cell.classList.contains('has-down-wall')){
            cellWalls.push("down");
        }

        hasFood = cell.classList.contains('has-food')

        const cellData = {
            x: x,
            y: y,
            walls: cellWalls,
            food: hasFood
        };
        mapData.cells.push(cellData);
    });

    if(currentTeleports.length == 2){
        mapData.teleports = [
            { x: parseInt(currentTeleports[0].dataset.x, 10), y: parseInt(currentTeleports[0].dataset.y, 10) },
            { x: parseInt(currentTeleports[1].dataset.x, 10), y: parseInt(currentTeleports[1].dataset.y, 10) }
        ];
    }

    currentPlayers.forEach(tempCell => {
        mapData.players.push({ x: parseInt(tempCell.dataset.x, 10), y: parseInt(tempCell.dataset.y, 10)});
    });
        


    if(switchCell != null && currentGates.length == 2){
        gate["switch"] = {x: parseInt(switchCell.dataset.x, 10), y: parseInt(switchCell.dataset.y, 10)};
        currentGates.forEach(cell => {
            cell.classList.forEach(className => {
                if (className.includes('gate')){
                    orient = className.split('-')[1];
                    gate['cells'].push({
                        "orientation": orient, "x": parseInt(cell.dataset.x, 10), "y": parseInt(cell.dataset.y, 10)
                    });
                }
            });
        });
        mapData.gate = gate;
    }


    return mapData;
}

function formatJSONFirstLevel(obj) {
    let result = '{\n';
    const keys = Object.keys(obj);
    keys.forEach((key, index) => {
        if (key === 'cells' || key === "players" || key === "teleports") {
            result += `  "${key}": [\n`;
            obj[key].forEach((cell, cellIndex) => {
                result += '      {';
                const cellKeys = Object.keys(cell);
                let comma = false;
                cellKeys.forEach((cellKey, cellKeyIndex) => {
                    if (cellKey === 'food' && !cell[cellKey]) return;
                    if (comma){
                        result += ', ';
                    }
                    result += `"${cellKey}": ${JSON.stringify(cell[cellKey])}`;
                    comma = true;
                });
                result += '}';
                if (cellIndex < obj[key].length - 1) {
                    result += ',';
                }
                result += '\n';
            });
            result += '  ]';
        } 
        else {
            result += `  "${key}": ${JSON.stringify(obj[key], null, 6).replace("}", "  }")}`;
        }
        if (index < keys.length - 1) {
            result += ',';
        }
        result += '\n';
    });
    result += '}';
    return result;
}